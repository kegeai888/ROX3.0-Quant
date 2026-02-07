import sys
import os
import pandas as pd
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rox_quant.backtest.tick_engine import TickEngine, TickGenerator, Tick, OrderBook
from app.rox_quant.algos.twap import TWAPAlgo
from app.rox_quant.algos.grid import GridAlgo

def test_tick_engine():
    print(">>> Testing Tick Engine & TWAP")
    
    # 1. Prepare Data
    dates = pd.date_range(start="2026-01-01 09:30:00", periods=10, freq="1min")
    df = pd.DataFrame({
        "date": dates,
        "open": [100 + i for i in range(10)],
        "high": [101 + i for i in range(10)],
        "low": [99 + i for i in range(10)],
        "close": [100.5 + i for i in range(10)],
        "volume": [1000] * 10
    })
    
    ticks = TickGenerator.from_kline(df, ticks_per_bar=4)
    engine = TickEngine()
    
    # 2. Algo
    algo = TWAPAlgo("TEST", "buy", 1000, dates[0], dates[-1], slices=5)
    
    # Adapter function
    def strategy_adapter(tick, book):
        algo.on_tick(tick, book)
        
    engine.add_strategy(strategy_adapter)
    
    # 3. Run
    count = engine.run(ticks)
    print(f"Processed {count} ticks")
    print(f"TWAP Orders: {len(algo.orders)}")
    if len(algo.orders) == 5:
        print("✅ TWAP: Generated 5 slices")
    else:
        print(f"❌ TWAP Failed: {len(algo.orders)} orders")

def test_grid_algo():
    print("\n>>> Testing Grid Algo")
    # Ticks oscillating around 100
    grid = GridAlgo("TEST", 100, 90, 110, 10, 1000) # Grid step 2.0
    
    # Simulate ticks: 100 -> 97 (Buy) -> 100 (Sell)
    ts = datetime.now()
    ticks = [
        Tick("TEST", ts, 100, 100, 99.5, 100.5, 100, 100),
        Tick("TEST", ts, 97, 100, 96.5, 97.5, 100, 100), # Should trigger Buy at 98, 96? Grid at 90, 92..98, 100..
        # Grids: 90, 92, 94, 96, 98, 100, 102...
        # Price drops to 97. Buys at 98 should fill.
        Tick("TEST", ts, 100, 100, 99.5, 100.5, 100, 100) # Price back to 100. Sell at 100 should fill.
    ]
    
    fake_book = OrderBook()
    for t in ticks:
        fake_book.update(t)
        grid.on_tick(t, fake_book)
        
    print(f"Grid executed {len(grid.orders)} orders")
    if len(grid.orders) >= 1:
        print("✅ Grid: Orders executed")
    else:
         print("❌ Grid: No orders")

if __name__ == "__main__":
    test_tick_engine()
    test_grid_algo()
