import asyncio
import json
import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.rox_quant.strategies.book_small_cap_timing import BookSmallCapTiming
from app.rox_quant.context import Context, Portfolio
from app.rox_quant.data_provider import DataProvider
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_run_strategy():
    """
    Test running the Book Small Cap strategy directly.
    """
    logger.info("Starting BookSmallCapTiming Strategy Test...")
    
    # 1. Initialize Strategy
    try:
        strategy = BookSmallCapTiming()
        logger.info("Strategy instance created.")
    except Exception as e:
        logger.error(f"Failed to create strategy instance: {e}")
        return

    # 2. Mock Context & Provider
    # We need a context with a data provider that works
    class MockProvider(DataProvider):
        def get_history(self, symbol, start_date=None, end_date=None, count=None):
            # Mock historical data for Index Momentum Check
            # Need strict format: DataFrame with 'close' column
            import pandas as pd
            import numpy as np
            
            # Create dummy history
            dates = pd.date_range(end=datetime.now(), periods=count or 30)
            
            # Scenario 1: Bullish Index (Should ALLOW trading)
            # Scenario 2: Bearish Index (Should STOP trading)
            # Let's mock a Bullish trend for HS300 and Bearish for ZZ500 to test mixed condition (Should ALLOW)
            
            if "000300" in symbol:
                prices = np.linspace(3000, 3100, len(dates))  # Up
            elif "0905" in symbol:
                prices = np.linspace(5000, 4800, len(dates))  # Down
            else:
                prices = np.random.rand(len(dates)) * 10 + 10 # Random stock prices
                
            df = pd.DataFrame({
                "time": dates,
                "close": prices,
                "open": prices,
                "high": prices,
                "low": prices,
                "volume": 1000
            })
            return df

    strategy.provider = MockProvider()
    
    # 3. Create Context
    context = Context(initial_capital=100000)
    context.portfolio = Portfolio(100000)
    context.current_dt = datetime.now()
    
    # 4. Initialize Strategy Logic
    strategy.initialize(context)
    logger.info(f"Strategy Initialized. Params: StockCount={context.stock_count}, Lag={context.lag}")
    
    # 5. Handle Bar (Backtest Step)
    # Mock Data Universe Snapshot
    import pandas as pd
    mock_universe = pd.DataFrame({
        "symbol": ["stock_A", "stock_B", "stock_C", "stock_D", "stock_E", "stock_F"],
        "price": [10.0, 5.0, 20.0, 2.0, 8.0, 15.0] # Sort by price: D(2.0), B(5.0), E(8.0), A(10.0)...
    })
    market_snapshot = mock_universe # This would be passed as bar_dict or context.data usually depending on engine
    context.data = market_snapshot
    
    logger.info("Running handle_bar...")
    strategy.handle_bar(context, None)
    
    # 6. Check Results (Did it buy Stock D?)
    positions = context.portfolio.positions
    logger.info(f"Positions after run: {positions.keys()}")
    
    if "stock_D" in positions:
        logger.info("SUCCESS: Strategy bought 'stock_D' (Lowest Price).")
    else:
        logger.error("FAILURE: Strategy did not buy the lowest price stock.")
        
    logger.info("Test Complete.")

if __name__ == "__main__":
    asyncio.run(test_run_strategy())
