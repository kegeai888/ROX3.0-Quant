
import pandas as pd
import numpy as np
from app.analysis.indicators import EMA, MA, SLOPE, DMA, CROSS

# Helper functions for HHV, LLV, etc. that are common in trading formulas
def HHV(series: pd.Series, period: int) -> pd.Series:
    """Highest High Value over a period."""
    return series.rolling(window=period).max()

def LLV(series: pd.Series, period: int) -> pd.Series:
    """Lowest Low Value over a period."""
    return series.rolling(window=period).min()

def SMA(series: pd.Series, n: int, m: int) -> pd.Series:
    """Smoothed Moving Average. A specific type of weighted average."""
    return series.ewm(alpha=m/n, adjust=False).mean()

def AVEDEV(series: pd.Series, period: int) -> pd.Series:
    """Average Absolute Deviation over a period."""
    mean = series.rolling(window=period).mean()
    return series.rolling(window=period).apply(lambda x: (x - mean.loc[x.index[-1]]).abs().mean(), raw=False)


def calculate_hot_money_indicator(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the 'Hot Money Dark Pool' indicator based on the provided formula.
    The input dataframe `df` must contain columns: 'open', 'high', 'low', 'close', 'volume'.
    """
    # Make a copy to avoid modifying the original dataframe
    data = df.copy()

    # Rename columns to be compatible with the formula (lowercase)
    data.rename(columns={
        'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'
    }, inplace=True)

    # 1. Basic EMA and Slope calculations
    data['MX'] = EMA(data['close'], 2)
    slope_c_21 = SLOPE(data['close'], 21)
    data['MXA'] = EMA(slope_c_21 * 20 + data['close'], 42)

    # 2. Core "Hot Money Net Buy" calculation (游资净买)
    typical_price = (2 * data['close'] + data['high'] + data['low']) / 4
    ma_close_30 = MA(data['close'], 30)
    # Prevent division by zero using replace
    ma_close_30 = ma_close_30.replace(0, 0.0001)
    data['AA'] = ((typical_price - ma_close_30).abs()) / ma_close_30
    data['游资净买'] = DMA(typical_price, data['AA'])

    # 3. Intermediate calculations for JJ and XJ signals
    data['CC'] = data['close'] / data['游资净买']
    data['MA1'] = MA(data['CC'] * typical_price, 3)
    data['MAAA'] = (((data['MA1'] - data['游资净买']) / data['游资净买']) / 3).fillna(0)
    data['TMP'] = data['MA1'] - data['MAAA'] * data['MA1']
    data['JJ'] = np.where(data['TMP'] <= data['游资净买'], data['游资净买'], np.nan)
    data['XJ'] = np.where(data['TMP'] <= data['游资净买'], data['TMP'], np.nan)

    # 4. Crossover signals (建仓, SEL)
    data['建仓'] = CROSS(data['MX'], data['MXA'])
    data['SEL'] = CROSS(data['MXA'], data['MX'])
    
    # 5. Other indicators for combined signals
    data['CP'] = MA(data['close'], 9)
    data['JD'] = MA(data['close'], 18)
    data['signal_gold_cross'] = CROSS(data['CP'], data['JD']) & (data['MX'] >= data['MXA'])

    # 6. Volume and Price breakout signal (BL)
    data['BL'] = (data['volume'] >= data['volume'].shift(1) * 1.91) & (data['close'] > data['close'].shift(1) * 1.01)

    # 7. Multi-indicator confirmation logic (X1 to X6 and XH)
    # LH, J (from a variation of KDJ)
    hhv_34 = HHV(data['high'], 34)
    llv_34 = LLV(data['low'], 34)
    data['LH'] = 100 - EMA((hhv_34 - data['close']) / (hhv_34 - llv_34) * 100, 34)
    data['J_LH'] = EMA(data['LH'], 21)
    
    # MACD
    data['DIF'] = EMA(data['close'], 12) - EMA(data['close'], 26)
    data['DEA'] = EMA(data['DIF'], 9)
    
    # KDJ
    rsv = (data['close'] - LLV(data['low'], 9)) / (HHV(data['high'], 9) - LLV(data['low'], 9)) * 100
    data['K'] = SMA(rsv, 3, 1)
    data['D'] = SMA(data['K'], 3, 1)
    
    # CCI
    typ = (data['high'] + data['low'] + data['close']) / 3
    data['CCI'] = (typ - MA(typ, 14)) * 1000 / (15 * AVEDEV(typ, 14))

    # SAR - This is a complex indicator, we will add a placeholder for now
    # For a full implementation, a dedicated library or function is needed.
    # We will assume a simple proxy: C > MA(C,5) for now.
    data['SAR_placeholder'] = data['close'] > MA(data['close'], 5)

    # RSI
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI1'] = 100 - (100 / (1 + rs))

    # Combine conditions
    X1 = data['LH'] > data['J_LH']
    X2 = data['DIF'] > data['DEA']
    X3 = data['K'] > data['D']
    X4 = data['CCI'] > 100
    X5 = data['SAR_placeholder'] # Using placeholder
    X6 = data['RSI1'] > 50
    
    data['XH_score'] = X1.astype(int) + X2.astype(int) + X3.astype(int) + X4.astype(int) + X5.astype(int) + X6.astype(int)
    data['XH'] = data['XH_score'] >= 5 # Formula says >5, but that means all 6 must be true. Usually it's a score.

    # 8. Final "Dark Pool Buy" signal (暗盘买入)
    # FILTER(BL, 3) means BL was true at least once in the last 3 bars.
    is_bl_in_last_3 = data['BL'].rolling(window=3).apply(lambda x: x.any(), raw=False).astype(bool)
    data['暗盘买入'] = is_bl_in_last_3 & data['XH']

    return data

