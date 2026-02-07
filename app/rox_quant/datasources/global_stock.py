import yfinance as yf
import pandas as pd
from typing import List, Dict, Any
from .base import BaseDataProvider, PricePoint
import logging
from datetime import datetime

logger = logging.getLogger("rox-global")

class GlobalStockProvider(BaseDataProvider):
    """
    US/HK/Global Stock Provider using YFinance
    """
    def get_history(self, symbol: str, days: int = 120, period: str = "daily") -> List[PricePoint]:
        try:
            # Period mapping
            p = "1d"
            if period == 'weekly': p = '1wk'
            elif period == 'monthly': p = '1mo'
            elif period == 'hourly': p = '1h'
            
            # YFinance uses 'period' for duration (e.g. "1y", "5d") or start/end
            # We can use start date based on days
            # Or just fetch a safe amount like "2y" and slice
            
            ticker = yf.Ticker(symbol)
            # data = ticker.history(period="2y", interval=p) # simpler
            
            # Dynamic period calculation
            yf_period = "1y"
            if days > 300: yf_period = "2y"
            if days > 700: yf_period = "5y"
            if days > 1800: yf_period = "10y"
            
            df = ticker.history(period=yf_period, interval=p)
            
            if df is None or df.empty:
                return []
                
            df = df.tail(days)
            res = []
            # Index is DatetimeIndex usually
            for idx, row in df.iterrows():
                dt = str(idx)
                if isinstance(idx, pd.Timestamp):
                    dt = idx.strftime('%Y-%m-%d')
                    
                res.append(PricePoint(
                    date=dt,
                    open=float(row.get('Open', 0)),
                    high=float(row.get('High', 0)),
                    low=float(row.get('Low', 0)),
                    close=float(row.get('Close', 0)),
                    volume=float(row.get('Volume', 0))
                ))
            return res
        except Exception as e:
            logger.error(f"Global stock history failed for {symbol}: {e}")
            return []

    def get_realtime_quote(self, symbol: str) -> Dict[str, Any]:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            # info keys vary: 'currentPrice', 'regularMarketOpen', 'regularMarketDayHigh', etc.
            
            price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('ask') or 0.0
            prev = info.get('previousClose') or 0.0
            
            change = 0.0
            change_pct = 0.0
            if price and prev:
                change = price - prev
                change_pct = (change / prev) * 100
                
            return {
                "price": float(price),
                "open": float(info.get('regularMarketOpen') or info.get('open') or 0),
                "high": float(info.get('regularMarketDayHigh') or info.get('dayHigh') or 0),
                "low": float(info.get('regularMarketDayLow') or info.get('dayLow') or 0),
                "volume": float(info.get('regularMarketVolume') or info.get('volume') or 0),
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), # Approximate
                "change": float(change),
                "change_pct": float(change_pct)
            }
        except Exception as e:
            logger.error(f"Global quote failed for {symbol}: {e}")
            return {}

    def search_symbols(self, query: str) -> List[Dict[str, str]]:
        # YFinance doesn't have a good search API built-in without extra libs.
        # We can simulate or use a hardcoded common list, or try to hit Yahoo search API directly.
        # For now, return empty or simple echo
        return []
