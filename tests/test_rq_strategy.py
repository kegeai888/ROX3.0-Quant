
import sys
import os
sys.path.append(os.getcwd())

import pandas as pd
from app.rox_quant.rq_adapter import RQAdapter, order_percent

# 1. Prepare Mock Data
dates = pd.date_range(start="2023-01-01", periods=100, freq="B")
prices = [10 + i * 0.1 for i in range(100)] # Steady uptrend
df = pd.DataFrame({
    "close": prices,
    "open": prices,
    "high": prices,
    "low": prices,
    "volume": [1000] * 100
}, index=dates)

data_map = {"000001.XSHE": df}

# 2. Define Strategy (Ricequant Style)
def init(context):
    print("Initialize Strategy...")
    context.s1 = "000001.XSHE"
    context.fired = False

def handle_bar(context, bar_dict):
    # Buy and Hold Logic
    if not context.fired:
        # Buy 100% of portfolio
        order_percent(context.s1, 1.0)
        context.fired = True
        print(f"[{context.now.date()}] Ordered 100% of {context.s1}")

# 3. Run Backtest
print("Starting Backtest...")
adapter = RQAdapter(data_map, initial_capital=100000.0)
result = adapter.run(init, handle_bar)

# 4. Show Results
print("\n--- Backtest Result ---")
print("Final Value:", result['equity'][-1]['value'])
print("Total Return:", f"{(result['equity'][-1]['value']/100000 - 1)*100:.2f}%")
print("Metrics:", result['metrics'])
print("Logs:", len(result['logs']), "trades executed")
