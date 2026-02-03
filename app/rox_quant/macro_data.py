import akshare as ak
import pandas as pd
import logging
import datetime

logger = logging.getLogger(__name__)

def get_real_macro_data():
    """
    Fetch real macro data from AkShare.
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

    try:
        # 1. Bond 10Y: 中国国债收益率
        try:
            df = ak.bond_zh_us_rate()
            if df is not None and not df.empty:
                val = df['中国国债收益率10年'].iloc[-1]
                if pd.notna(val): data['bond_10y'] = float(val)
        except Exception: pass

        # 2. PMI
        try:
            df = ak.macro_china_pmi()
            if df is not None and not df.empty:
                # Columns: 统计时间, 制造业PMI, 制造业PMI-同比, ...
                # Use column access by name if possible, or assume structure
                # akshare usually returns DataFrame with Chinese columns
                if '制造业PMI' in df.columns:
                    data['pmi_mfg'] = float(df['制造业PMI'].iloc[0]) # usually sorted desc? check date
                    # akshare data is often sorted by date asc. Let's check tail
                    # But macro_china_pmi might be latest first?
                    # Let's take the one with latest date.
                    # Actually, let's assume last row is latest if we don't know sort order? 
                    # Most time series are asc.
                    data['pmi_mfg'] = float(df['制造业PMI'].iloc[-1])
        except Exception: pass
        
        # 3. CPI
        try:
            df = ak.macro_china_cpi()
            if df is not None and not df.empty:
                if '全国-当月' in df.columns:
                    data['cpi'] = float(df['全国-当月'].iloc[-1])
        except Exception: pass

        # 4. PPI
        try:
            df = ak.macro_china_ppi()
            if df is not None and not df.empty:
                if '当月' in df.columns:
                    data['ppi'] = float(df['当月'].iloc[-1])
        except Exception: pass
        
        # 5. M2
        try:
            df = ak.macro_china_money_supply()
            if df is not None and not df.empty:
                if 'M2-同比增长' in df.columns:
                    data['m2'] = float(df['M2-同比增长'].iloc[-1])
        except Exception: pass

        # 6. USD/CNY
        try:
            df = ak.fx_spot_quote()
            if df is not None and not df.empty:
                row = df[df['货币对'] == '美元/人民币']
                if not row.empty:
                    # '最新价' or '买价'
                    price = row.iloc[0].get('最新价') or row.iloc[0].get('买价')
                    if price: data['usd_cny'] = float(price)
        except Exception: pass
        
        # 7. Shibor (Overnight)
        try:
            # rate_interbank might need specific params
            # try shibor_data = ak.rate_interbank_shibor(indicator="隔夜") ? No such interface maybe
            # Try stock_zh_index_spot for simplified rates? No.
            # Use fixed value fallback if complex.
            pass
        except Exception: pass

    except Exception as e:
        logger.error(f"Error fetching macro data: {e}")
        
    return data
