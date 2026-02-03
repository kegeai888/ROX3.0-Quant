import pandas as pd
import numpy as np
from app.analysis.indicators import (
    HHV, LLV, CROSS, BARSLAST, FILTER, BACKSET, SMA, MA, EMA, COUNT, WMA
)

def calculate_kang_long_you_hui(df: pd.DataFrame) -> pd.DataFrame:
    """
    Translates the 'Kang Long You Hui' (亢龙有悔) indicator logic into Python.
    """
    data = df.copy()
    c, h, l, o, v = data['close'], data['high'], data['low'], data['open'], data['volume']

    # --- Signal 1: 强庄 (Qiang Zhuang) ---
    sr1 = (h.shift(10) == HHV(h, 2 * 10 + 1))
    sr2 = FILTER(sr1, 10)
    sr3 = BACKSET(sr2, 10 + 1)
    hdd = FILTER(sr3, 10)
    prev_high_h = h.shift(BARSLAST(hdd).astype(int))
    volume_spike_strong = (v / v.shift(1)) >= 1.9
    breakout_strong = CROSS(c, prev_high_h)
    data['signal_qiang_zhuang'] = volume_spike_strong & breakout_strong

    # --- Signal 2: XG (Xuan Gu) ---
    a = (h.shift(9) == HHV(h, 2 * 9 + 1))
    b = FILTER(a, 9)
    ab = BACKSET(b, 9 + 1)
    hd = FILTER(ab, 9)
    prev_high = h.shift(BARSLAST(hd).astype(int))
    volume_spike = (v / v.shift(1)) >= 1.1
    breakout = CROSS(c, prev_high)
    data['signal_xg'] = volume_spike & breakout

    # --- Signal 3: 重点 (Zhong Dian) ---
    data['signal_zhong_dian'] = data['signal_xg'] & data['signal_qiang_zhuang']
    data['signal_zhong_dian_repeated'] = (data['signal_zhong_dian']) & (COUNT(data['signal_zhong_dian'], 10) >= 2)

    # --- Main Indicator Lines ---
    mid = (3 * c + l + o + h) / 6
    # The formula is a specific type of WMA over 20 periods.
    # (20*MID + 19*REF(MID,1) + ... + REF(MID,20)) / 210
    # Note: The formula in the description has REF(MID,20) which means 21 terms.
    # We will use a 21-period WMA to approximate this.
    weights = np.arange(1, 22)[::-1] # 21, 20, ..., 1
    data['line_zhuli'] = mid.rolling(window=21).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

    # --- Bollinger-like Bands ---
    mid1 = MA(c, 15) * 1.005
    vart1 = (c - mid1) ** 2
    vart2 = MA(vart1, 15)
    vart3 = np.sqrt(vart2)
    upper = mid1 + 2 * vart3
    # lower = mid1 - 2 * vart3 # Lower band is not used in signals
    data['line_qiming'] = mid1.shift(1)
    data['line_lanyue'] = upper.shift(1)

    # --- Band Signals ---
    data['signal_cross_lanyue'] = c > data['line_lanyue']
    data['signal_fallback_lanyue'] = (c.shift(1) > data['line_lanyue'].shift(1)) & (c < data['line_lanyue'])

    # --- RSI and Final Signal ---
    lc = c.shift(2)
    rsi_sma1 = SMA(pd.Series(np.where(c - lc > 0, c - lc, 0), index=c.index), 3, 1)
    rsi_sma2 = SMA(abs(c - lc), 3, 1)
    rsi = (rsi_sma1 / rsi_sma2.replace(0, np.nan)) * 80
    data['rsi'] = rsi
    data['signal_kang_long_you_hui'] = CROSS(pd.Series(68, index=c.index), rsi)

    # --- Other lines for plotting ---
    data['line_ff'] = EMA(c, 3)
    data['line_ma15'] = EMA(c, 21)
    
    # Clean up NaN/inf values for JSON compatibility
    data.replace([np.inf, -np.inf], np.nan, inplace=True)
    data.fillna(0, inplace=True)

    return data
