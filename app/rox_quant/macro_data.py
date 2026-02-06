import akshare as ak
import pandas as pd
import logging
import datetime
import concurrent.futures

logger = logging.getLogger(__name__)

def _fetch_bond():
    df = ak.bond_zh_us_rate()
    if df is not None and not df.empty:
        val = df['中国国债收益率10年'].iloc[-1]
        if pd.notna(val): return float(val)
    return None

def _fetch_pmi():
    df = ak.macro_china_pmi()
    if df is not None and not df.empty:
        if '制造业PMI' in df.columns:
            return float(df['制造业PMI'].iloc[-1])
    return None

def _fetch_cpi():
    df = ak.macro_china_cpi()
    if df is not None and not df.empty:
        if '全国-当月' in df.columns:
            return float(df['全国-当月'].iloc[-1])
    return None

def _fetch_ppi():
    df = ak.macro_china_ppi()
    if df is not None and not df.empty:
        if '当月' in df.columns:
            return float(df['当月'].iloc[-1])
    return None

def _fetch_m2():
    df = ak.macro_china_money_supply()
    if df is not None and not df.empty:
        if 'M2-同比增长' in df.columns:
            return float(df['M2-同比增长'].iloc[-1])
    return None

def _fetch_fx():
    df = ak.fx_spot_quote()
    if df is not None and not df.empty:
        row = df[df['货币对'] == '美元/人民币']
        if not row.empty:
            price = row.iloc[0].get('最新价') or row.iloc[0].get('买价')
            if price: return float(price)
    return None

def get_real_macro_data():
    """
    Fetch real macro data from AkShare in parallel with timeouts.
    Returns a dictionary of indicators.
    """
    # Default fallback values (Simulation)
    data = {
        "bond_10y": 2.15,
        "pmi_mfg": 49.5,
        "pmi_svc": 50.2,
        "cpi": 0.3,
        "ppi": -2.5,
        "shibor": 1.70,
        "gdp_growth": 5.0,
        "m2": 8.7,
        "soc_fin": 9.5,
        "usd_cny": 7.25,
        "crb": 280.0
    }

    # Map fetch functions to keys
    tasks = {
        "bond_10y": _fetch_bond,
        "pmi_mfg": _fetch_pmi,
        "cpi": _fetch_cpi,
        "ppi": _fetch_ppi,
        "m2": _fetch_m2,
        "usd_cny": _fetch_fx
    }

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        future_to_key = {executor.submit(func): key for key, func in tasks.items()}
        for future in concurrent.futures.as_completed(future_to_key):
            key = future_to_key[future]
            try:
                # 3s timeout for each individual fetch
                val = future.result(timeout=3)
                if val is not None:
                    data[key] = val
                    logger.info(f"Fetched macro {key}: {val}")
            except concurrent.futures.TimeoutError:
                logger.warning(f"Macro fetch timeout: {key}")
            except Exception as e:
                logger.warning(f"Macro fetch failed {key}: {e}")

    return data

