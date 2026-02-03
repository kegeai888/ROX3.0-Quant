import asyncio
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
import logging
from app.utils.retry import run_with_retry
from app.utils.ashare_fallback import get_daily_kline_ashare

logger = logging.getLogger("rox-stock-data")

def _symbol_prefix(code: str) -> str:
    c = str(code).zfill(6)
    if c.startswith(("6", "5", "9")) or c.startswith("688"):
        return "sh" + c
    return "sz" + c

def _is_index_code(code: str) -> bool:
    """常见指数代码"""
    c = str(code).strip()[:6].zfill(6)
    return c in ("000001", "999999", "399001", "399006", "000688", "399300")

def _index_symbol(code: str) -> str:
    c = str(code).strip()[:6].zfill(6)
    if c in ("000001", "999999", "000688"):
        return "sh" + c
    return "sz" + c

def _normalize_kline_df(df: pd.DataFrame) -> pd.DataFrame:
    """统一为 date, open, close, high, low, volume"""
    if df is None or df.empty:
        return df
    if "日期" in df.columns:
        df = df.rename(columns={"日期": "date", "开盘": "open", "收盘": "close", "最高": "high", "最低": "low", "成交量": "volume"})
    if "time" in df.columns and "date" not in df.columns:
        df["date"] = df["time"]
    for col in ["open", "close", "high", "low", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df

async def get_stock_kline(code: str, period: str = "daily", limit: int = 500) -> tuple[pd.DataFrame, bool]:
    """
    Fetch K-Line data with multi-layer fallback.
    Returns: (DataFrame, is_fallback)
    """
    code = str(code).strip()[:6].zfill(6)
    ak_period = "daily"
    if period == "weekly": ak_period = "weekly"
    elif period == "monthly": ak_period = "monthly"
    
    end_d = datetime.now()
    # Fetch enough history for MA250
    start_d = end_d - timedelta(days=365 * 2) 
    start_date = start_d.strftime("%Y%m%d")
    end_date = end_d.strftime("%Y%m%d")

    df = None
    is_fallback = False
    is_index = _is_index_code(code)

    loop = asyncio.get_event_loop()

    # 1. Primary Source: AkShare
    try:
        if is_index:
            sym = _index_symbol(code)
            def _fetch_index():
                # Try with prefix first (sh000001)
                try:
                    return run_with_retry(lambda: ak.stock_zh_index_daily_em(symbol=sym))
                except:
                    # Try without prefix (000001) if prefix fails
                    raw_code = code[-6:]
                    return run_with_retry(lambda: ak.stock_zh_index_daily_em(symbol=raw_code))
            
            raw = await loop.run_in_executor(None, _fetch_index)
            if raw is not None and not raw.empty:
                raw = _normalize_kline_df(raw)
                raw = raw.sort_values("date")
                if ak_period != "daily":
                    # Resample if needed
                    raw = raw.set_index("date").resample("W" if ak_period == "weekly" else "M").agg(
                        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
                    ).dropna().reset_index()
                df = raw
        else:
            def _fetch_kline():
                return run_with_retry(lambda: ak.stock_zh_a_hist(symbol=code, period=ak_period, start_date=start_date, end_date=end_date, adjust="qfq"))
            df = await loop.run_in_executor(None, _fetch_kline)
    except Exception as e:
        logger.warning(f"AkShare fetch failed for {code}: {e}")

    # 2. Secondary Source: Ashare (Sina/Tencent)
    if df is None or df.empty:
        try:
            df = await loop.run_in_executor(
                None, lambda: get_daily_kline_ashare(code, count=limit, period=ak_period)
            )
            if df is not None and not df.empty:
                logger.info(f"Loaded {code} via Ashare fallback")
        except Exception as e2:
            logger.warning(f"Ashare fallback failed for {code}: {e2}")

    # 3. Synthetic Fallback (Last Resort)
    if df is None or df.empty:
        is_fallback = True
        logger.warning(f"All sources failed for {code}, generating synthetic data")
        import random
        n = 60
        base = 3200.0 if is_index else 10.0
        dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n, 0, -1)]
        
        o = [base]
        for _ in range(n - 1):
            change = (random.random() - 0.5) * 0.02
            o.append(o[-1] * (1 + change))
        
        h = [val * (1 + random.random() * 0.01) for val in o]
        l_ = [val * (1 - random.random() * 0.01) for val in o]
        c = [o[i+1] if i+1 < n else o[-1] for i in range(n)]
        
        df = pd.DataFrame({
            "date": pd.to_datetime(dates),
            "open": o, "high": h, "low": l_, "close": c,
            "volume": [1000000 + random.randint(-100000, 100000) for _ in range(n)]
        })

    df = _normalize_kline_df(df)
    if df is not None and not df.empty:
        df = df.sort_values("date")
        if limit > 0:
            df = df.tail(limit)
    
    return df, is_fallback
