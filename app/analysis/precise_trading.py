import pandas as pd
import numpy as np
from app.analysis import indicators

def get_precise_trading_signals(df: pd.DataFrame, zig_pct: float = 5.0):
    """
    Calculates the "Precise Trading" signals based on the Tongdaxin formula.

    Formula Breakdown:
    A1:=TROUGH(C,5);
    A2:=PEAK(C,5);
    A3:=TROUGHBARS(C,5);
    A4:=PEAKBARS(C,5);
    A5:=IF(A2>REF(A2,1),A2,DRAWNULL);
    A6:=IF(A1<REF(A1,1),A1,DRAWNULL);
    DRAWICON(A3=0,A6,1); {Buy Signal}
    DRAWICON(A4=0,A5,2); {Sell Signal}

    Args:
        df (pd.DataFrame): DataFrame with at least a 'close' column.
        zig_pct (float): The percentage change for the ZIGZAG calculation.

    Returns:
        pd.DataFrame: A DataFrame with 'buy_signal' and 'sell_signal' columns.
                      The columns contain the price at which a signal occurs,
                      otherwise NaN.
    """
    close = df['close']

    # Calculate intermediate values using the indicators library
    # ZIG returns the interpolated zigzag line, but we need peaks and troughs logic
    # Using PEAK and TROUGH functions from indicators which return boolean masks
    
    is_trough = indicators.TROUGH(close, zig_pct)
    is_peak = indicators.PEAK(close, zig_pct)
    
    # Get prices only at peaks/troughs, others NaN
    # Note: TROUGH/PEAK return boolean Series where True indicates the turning point
    trough_points_price = close.where(is_trough)
    peak_points_price = close.where(is_peak)
    
    trough_bars = indicators.TROUGHBARS(close, zig_pct)
    peak_bars = indicators.PEAKBARS(close, zig_pct)

    # A5: New higher peaks
    # Find where peak prices are greater than the previous peak price
    # We need to compare the current peak price with the *previous* peak price.
    # We can forward fill the peak prices to compare current vs prev.
    last_peak_prices = peak_points_price.ffill()
    # Shift to compare with previous value in the filled series
    # But wait, we only care about the moments when is_peak is True
    
    # Logic from formula: A5:=IF(A2>REF(A2,1),A2,DRAWNULL); where A2 is PEAK(C,5) value?
    # Actually PEAK(C,5) in Tongdaxin returns the VALUE of the peak.
    # Our indicators.PEAK returns boolean. 
    # So we need a series that holds the value of the most recent peak.
    
    current_peak_val = close.where(is_peak).ffill()
    current_trough_val = close.where(is_trough).ffill()
    
    # Check if current peak is higher than the *previous* confirmed peak
    # We need to shift current_peak_val, but we need to shift it by the duration of the peak?
    # No, A2 (Peak Value) changes only when a new peak is confirmed.
    # So valid comparison is current_peak_val > current_peak_val.shift(1) ?
    # If A2 is a step function (constant until next peak), then shift(1) is the previous bar's view of the peak.
    # If today is a new peak, A2 changes.
    
    new_higher_peaks = np.where((is_peak) & (current_peak_val > current_peak_val.shift(1)), current_peak_val, np.nan)
    
    # A6: New lower troughs
    new_lower_troughs = np.where((is_trough) & (current_trough_val < current_trough_val.shift(1)), current_trough_val, np.nan)

    # Create signals
    # Buy Signal: When TROUGHBARS=0 (is_trough is True) AND it's a new lower trough (A6 has value)
    buy_signal = pd.Series(new_lower_troughs, index=df.index)
    
    # Sell Signal: When PEAKBARS=0 (is_peak is True) AND it's a new higher peak (A5 has value)
    sell_signal = pd.Series(new_higher_peaks, index=df.index)

    return pd.DataFrame({
        'buy_signal': buy_signal,
        'sell_signal': sell_signal
    }, index=df.index)
