import pandas as pd
import numpy as np
from app.analysis.indicators import LLV, HHV, SMA, EMA

def calculate_three_color_resonance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the "Three-Color Fund Resonance" indicator, which includes Main Force Money,
    Hot Money, and Retail Money.
    """
    # Parameters from the formula
    N = 35
    M = 35
    N1 = 1
    NX = 42
    N1X = 21

    # Make a copy to avoid modifying the original dataframe
    data = df.copy()
    close = data['close']
    low = data['low']
    high = data['high']

    # Replace infinite values with NaN to prevent calculation errors
    data.replace([np.inf, -np.inf], np.nan, inplace=True)

    # --- Indicator Calculations ---

    # 主力资金 (Main Force Money)
    var1_divisor = (HHV(high, N) - LLV(low, N))
    var1 = (close - LLV(low, N)) / var1_divisor.replace(0, np.nan) * 100
    var2 = SMA(var1.fillna(0), M, N1)
    var3 = SMA(var2.fillna(0), M, N1)
    var4 = SMA(var3.fillna(0), M, N1)
    data['main_force_money'] = EMA(var4.fillna(0), N)

    # 游资资金 (Hot Money)
    var5_divisor = (HHV(high, NX) - LLV(low, NX))
    var5 = (close - LLV(low, NX)) / var5_divisor.replace(0, np.nan) * 100
    var6 = SMA(var5.fillna(0), N1X, N1)
    var7 = SMA(var6.fillna(0), N1X, N1)
    var8 = SMA(var7.fillna(0), N1X, N1)
    data['hot_money'] = EMA(var8.fillna(0), N)

    # 散户资金 (Retail Money)
    retail_divisor = (HHV(high, 21) - LLV(low, 21))
    data['retail_money'] = (close - LLV(low, 21)) / retail_divisor.replace(0, np.nan) * 100

    # --- Estimation Lines ---
    data['main_force_estimation'] = EMA(data['main_force_money'].fillna(0), 5)
    data['hot_money_estimation'] = EMA(data['hot_money'].fillna(0), 5)
    data['retail_money_estimation'] = EMA(data['retail_money'].fillna(0), 5)

    # --- STICKLINE Logic for Frontend Plotting ---
    # The STICKLINE function in the original formula is for plotting.
    # We will create corresponding data series that the frontend can use to draw colored bars.

    # Main Force Money Lines
    main_force_money_ref = data['main_force_money'].shift(1)
    data['main_force_red'] = data['main_force_money'].where((data['main_force_money'] > main_force_money_ref) & (data['main_force_money'] > 0), 0)
    data['main_force_cyan'] = data['main_force_money'].where((data['main_force_money'] < main_force_money_ref) & (data['main_force_money'] > 0), 0)
    data['main_force_white'] = data['main_force_money'].where(data['main_force_money'] < 0, 0)

    # Hot Money Lines
    hot_money_ref = data['hot_money'].shift(1)
    data['hot_money_magenta'] = data['hot_money'].where((data['hot_money'] > hot_money_ref) & (data['hot_money'] > 0), 0)
    data['hot_money_green'] = data['hot_money'].where((data['hot_money'] < hot_money_ref) & (data['hot_money'] > 0), 0)
    data['hot_money_white'] = data['hot_money'].where(data['hot_money'] < 0, 0)

    # Retail Money Lines
    retail_money_ref = data['retail_money'].shift(1)
    data['retail_yellow'] = data['retail_money'].where((data['retail_money'] > retail_money_ref) & (data['retail_money'] > 0), 0)
    data['retail_blue'] = data['retail_money'].where((data['retail_money'] < retail_money_ref) & (data['retail_money'] > 0), 0)
    data['retail_white'] = data['retail_money'].where(data['retail_money'] < 0, 0)
    
    # Fill NaN values at the beginning of the series with 0 for a cleaner output
    data.fillna(0, inplace=True)

    return data
