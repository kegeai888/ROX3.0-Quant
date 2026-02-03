
import pandas as pd
import numpy as np
from scipy.stats import linregress

def EMA(series: pd.Series, period: int) -> pd.Series:
    """
    Calculates the Exponential Moving Average (EMA).
    """
    return series.ewm(span=period, adjust=False).mean()

def MACD(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """
    Calculates the MACD (Moving Average Convergence Divergence).
    Returns (DIF, DEA, MACD_HIST).
    """
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd_hist = (dif - dea) * 2  # Multiplied by 2 to match standard Chinese software
    return dif, dea, macd_hist

def KDJ(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 9, m1: int = 3, m2: int = 3):
    """
    Calculates the KDJ indicator.
    Returns (K, D, J).
    """
    llv = low.rolling(window=n, min_periods=1).min()
    hhv = high.rolling(window=n, min_periods=1).max()
    
    rsv = ((close - llv) / (hhv - llv) * 100).fillna(50)
    
    # K = SMA(RSV, M1, 1)
    k_vals = []
    k = 50.0
    for r in rsv.values:
        if pd.isna(r): r = 50.0
        k = (m1 - 1) / m1 * k + 1 / m1 * r
        k_vals.append(k)
        
    # D = SMA(K, M2, 1)
    d_vals = []
    d = 50.0
    for kv in k_vals:
        d = (m2 - 1) / m2 * d + 1 / m2 * kv
        d_vals.append(d)
        
    k_series = pd.Series(k_vals, index=close.index)
    d_series = pd.Series(d_vals, index=close.index)
    j_series = 3 * k_series - 2 * d_series
    
    return k_series, d_series, j_series

def RSI(close: pd.Series, n: int = 14) -> pd.Series:
    """
    Calculates the RSI (Relative Strength Index).
    """
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=n).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=n).mean()
    rs = gain / loss.replace(0, 0.0001)
    rsi = (100 - (100 / (1 + rs))).fillna(50)
    return rsi

def BOLL(close: pd.Series, n: int = 20, k: int = 2):
    """
    Calculates Bollinger Bands.
    Returns (UPPER, MID, LOWER).
    """
    mid = close.rolling(window=n).mean()
    std = close.rolling(window=n).std()
    upper = mid + k * std
    lower = mid - k * std
    return upper, mid, lower

def WR(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """
    Calculates Williams %R.
    """
    hhv = high.rolling(window=n).max()
    llv = low.rolling(window=n).min()
    wr = (hhv - close) / (hhv - llv) * 100
    return -wr  # Usually negative, e.g. -20 to -80

def CCI(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """
    Calculates CCI (Commodity Channel Index).
    """
    tp = (high + low + close) / 3
    ma = tp.rolling(window=n).mean()
    md = tp.rolling(window=n).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
    cci = (tp - ma) / (0.015 * md.replace(0, 0.0001))
    return cci


def MA(series: pd.Series, period: int) -> pd.Series:
    """
    Calculates the Simple Moving Average (MA).
    """
    return series.rolling(window=period).mean()

def WMA(series: pd.Series, period: int) -> pd.Series:
    """
    Calculates the Weighted Moving Average (WMA).
    """
    weights = np.arange(1, period + 1)
    return series.rolling(window=period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

def SLOPE(series: pd.Series, period: int) -> pd.Series:
    """
    Calculates the slope of the linear regression line for a series over a given period.
    This is a Python equivalent for the SLOPE function in trading platforms.
    """
    # Create a rolling window
    rolling_window = series.rolling(window=period)
    
    # Function to apply to each window
    def get_slope(window):
        if len(window) < period:
            return np.nan
        # x-values are simply the sequence of numbers
        x = np.arange(len(window))
        # y-values are the window's data
        y = window.values
        # Perform linear regression
        slope, _, _, _, _ = linregress(x, y)
        return slope

    # Apply the function to each window
    slopes = rolling_window.apply(get_slope, raw=False)
    return slopes

def DMA(series: pd.Series, weights: pd.Series) -> pd.Series:
    """
    Calculates the Dynamic Moving Average (DMA).
    Formula: DMA(X, A) = A*X + (1-A)*DMA', where DMA' is the previous DMA value.
    This is a recursive calculation.
    """
    dma = pd.Series(index=series.index, dtype='float64')
    # Ensure weights are between 0 and 1
    weights = weights.clip(0, 1)
    
    # Initialize the first value
    dma.iloc[0] = series.iloc[0]
    
    # Recursive calculation
    for i in range(1, len(series)):
        # If weight is NaN, carry forward the last dma value
        if pd.isna(weights.iloc[i]):
            dma.iloc[i] = dma.iloc[i-1]
        else:
            dma.iloc[i] = weights.iloc[i] * series.iloc[i] + (1 - weights.iloc[i]) * dma.iloc[i-1]
            
    return dma

def CROSS(series1: pd.Series, series2: pd.Series) -> pd.Series:
    """
    Returns a boolean series indicating where series1 crosses above series2.
    """
    prev_s1 = series1.shift(1)
    prev_s2 = series2.shift(1)
    
    condition = (series1 > series2) & (prev_s1 <= prev_s2)
    return condition

def HHV(series: pd.Series, period: int) -> pd.Series:
    """
    Calculates the Highest High Value (HHV) over a given period.
    """
    return series.rolling(window=period).max()

def LLV(series: pd.Series, period: int) -> pd.Series:
    """
    Calculates the Lowest Low Value (LLV) over a given period.
    """
    return series.rolling(window=period).min()

def SMA(series: pd.Series, n: int, m: int) -> pd.Series:
    """
    Calculates the Smoothed Moving Average (SMA).
    Formula: SMA(X, N, M) = (M * X + (N - M) * SMA') / N
    This is a recursive calculation.
    """
    sma = pd.Series(index=series.index, dtype='float64')
    
    # Initialize the first value
    sma.iloc[0] = series.iloc[0]
    
    # Recursive calculation
    for i in range(1, len(series)):
        sma.iloc[i] = (m * series.iloc[i] + (n - m) * sma.iloc[i-1]) / n
            
    return sma

def AVEDEV(series: pd.Series, period: int) -> pd.Series:
    """
    Calculates the Average Absolute Deviation over a given period for each window.
    """
    def avedev_window(window):
        if len(window) < period:
            return np.nan
        return (window - window.mean()).abs().mean()

    return series.rolling(window=period).apply(avedev_window, raw=True)

def BARSLAST(condition: pd.Series) -> pd.Series:
    """
    Calculates the number of bars since the condition was last true.
    Returns 0 on the bar where the condition is true.
    For the initial period before the first True, it returns the number of bars since the start.
    """
    condition = condition.astype(bool)
    # Create a grouping key that increments each time the condition is True
    groups = condition.cumsum()
    # For each group, count the members. This resets the count when the group changes.
    bars_since = groups.groupby(groups).cumcount()
    return bars_since

def FILTER(condition: pd.Series, n: int) -> pd.Series:
    """
    Keeps the signal true for n bars after the condition is met.
    If condition is true at bar `i`, the output is true from bar `i` to `i+n-1`.
    This is implemented by checking if the condition was true in the last `n` bars.
    """
    return condition.rolling(window=n, min_periods=1).max().astype(bool)

def BACKSET(condition: pd.Series, n: int) -> pd.Series:
    """
    If condition is true at bar `i`, the output is true for bars from `i-n+1` to `i`.
    This is a look-ahead function for visual marking, checking if the condition will be true in the next `n` bars.
    """
    return condition.shift(-(n - 1)).rolling(window=n, min_periods=1).max().fillna(0).astype(bool)

def COUNT(condition: pd.Series, period: int) -> pd.Series:
    """
    Counts the number of times the condition was true in the last `period` bars.
    """
    return condition.astype(bool).rolling(window=period, min_periods=1).sum()

def SUM(series: pd.Series, period: int) -> pd.Series:
    """
    Calculates the sum of a series over a rolling period.
    """
    return series.rolling(window=period).sum()

def BARSCOUNT(series: pd.Series) -> pd.Series:
    """
    Returns a series with the count of bars up to that point.
    Equivalent to BARSCOUNT(C) in some platforms.
    """
    return pd.Series(np.arange(1, len(series) + 1), index=series.index)

def ZIG(series: pd.Series, pct_change: float) -> pd.Series:
    """
    Calculates the Zigzag indicator, returning an interpolated series.
    `pct_change` is the percentage move to define a pivot.
    This is a common implementation of the Zigzag indicator.
    """
    if series.empty or len(series) < 2:
        return pd.Series(dtype='float64', index=series.index)

    pivots = {}
    trend = 0
    last_pivot_price = series.iloc[0]
    last_pivot_idx = 0
    
    pivots[series.index[0]] = series.iloc[0]

    # Find initial trend
    for i in range(1, len(series)):
        ret = (series.iloc[i] / last_pivot_price) - 1.0
        if abs(ret) * 100.0 > pct_change:
            trend = np.sign(ret)
            last_pivot_price = series.iloc[i]
            last_pivot_idx = i
            break
    
    if trend == 0:
        return pd.Series(series.iloc[0], index=series.index)

    extreme_price = last_pivot_price
    extreme_idx = last_pivot_idx

    for i in range(last_pivot_idx + 1, len(series)):
        current_price = series.iloc[i]
        
        if trend == 1: # Uptrend, looking for a peak
            if current_price >= extreme_price:
                extreme_price = current_price
                extreme_idx = i
            else:
                ret = (extreme_price - current_price) / extreme_price
                if ret * 100.0 > pct_change:
                    pivots[series.index[extreme_idx]] = extreme_price
                    trend = -1
                    extreme_price = current_price
                    extreme_idx = i
        
        elif trend == -1: # Downtrend, looking for a trough
            if current_price <= extreme_price:
                extreme_price = current_price
                extreme_idx = i
            else:
                ret = (current_price - extreme_price) / extreme_price
                if ret * 100.0 > pct_change:
                    pivots[series.index[extreme_idx]] = extreme_price
                    trend = 1
                    extreme_price = current_price
                    extreme_idx = i

    # Add the last extreme point
    pivots[series.index[extreme_idx]] = extreme_price
    
    zig_series = pd.Series(pivots, index=series.index)
    # Interpolate to create the continuous Zigzag line
    return zig_series.interpolate(method='index')

def _find_pivots(series: pd.Series, pct_change: float) -> pd.Series:
    """
    Internal helper to find Zigzag pivot points.
    Returns a series with 1 for peaks, -1 for troughs, and 0 otherwise.
    """
    if series.empty or len(series) < 2:
        return pd.Series(0, index=series.index)

    pivots = pd.Series(0, index=series.index)
    trend = 0
    last_pivot_price = series.iloc[0]
    last_pivot_idx = 0
    
    # Find initial trend
    for i in range(1, len(series)):
        ret = (series.iloc[i] / last_pivot_price) - 1.0
        if abs(ret) * 100.0 >= pct_change:
            pivots.iloc[last_pivot_idx] = -np.sign(ret)
            trend = np.sign(ret)
            last_pivot_price = series.iloc[i]
            last_pivot_idx = i
            break
    
    if trend == 0:
        return pd.Series(0, index=series.index)

    extreme_price = last_pivot_price
    extreme_idx = last_pivot_idx

    for i in range(last_pivot_idx + 1, len(series)):
        current_price = series.iloc[i]
        
        if trend == 1: # Uptrend, looking for a peak
            if current_price >= extreme_price:
                extreme_price = current_price
                extreme_idx = i
            else:
                ret = (extreme_price - current_price) / extreme_price
                if ret * 100.0 >= pct_change:
                    pivots.iloc[extreme_idx] = 1 # Peak found
                    trend = -1
                    extreme_price = current_price
                    extreme_idx = i
        
        elif trend == -1: # Downtrend, looking for a trough
            if current_price <= extreme_price:
                extreme_price = current_price
                extreme_idx = i
            else:
                ret = (current_price - extreme_price) / extreme_price
                if ret * 100.0 >= pct_change:
                    pivots.iloc[extreme_idx] = -1 # Trough found
                    trend = 1
                    extreme_price = current_price
                    extreme_idx = i

    pivots.iloc[extreme_idx] = trend
    
    return pivots

def TROUGH(series: pd.Series, pct_change: float) -> pd.Series:
    """
    Returns a boolean series that is True at Zigzag troughs.
    """
    return _find_pivots(series, pct_change) == -1

def PEAK(series: pd.Series, pct_change: float) -> pd.Series:
    """
    Returns a boolean series that is True at Zigzag peaks.
    """
    return _find_pivots(series, pct_change) == 1

def TROUGHBARS(series: pd.Series, pct_change: float) -> pd.Series:
    """
    Calculates the number of bars since the last Zigzag trough.
    """
    troughs = TROUGH(series, pct_change)
    return BARSLAST(troughs)

def PEAKBARS(series: pd.Series, pct_change: float) -> pd.Series:
    """
    Calculates the number of bars since the last Zigzag peak.
    """
    peaks = PEAK(series, pct_change)
    return BARSLAST(peaks)

