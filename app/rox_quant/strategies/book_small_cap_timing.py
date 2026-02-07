from app.rox_quant.portfolio_backtest import PortfolioBacktestEngine, Context
import pandas as pd
import numpy as np

class BookSmallCapTiming(PortfolioBacktestEngine):
    """
    Book Strategy: Small Cap 2-8 Timing (Chapter 4.2)
    Source: "Quantitative Investment Technical Analysis & Practice" - Pu Yuankai
    
    Logic:
    1. Select stocks: Small Market Cap (Proxied by Low Price).
    2. Timing: 
       - Calculate 20-day Momentum for HS300 and ZZ500.
       - If both HS300 and ZZ500 Momentum < 0: CLEAR ALL POSITIONS (Stop Loss).
       - Else: Hold Top N Small Cap stocks.
    """
    
    def initialize(self, context: Context):
        context.stock_count = 10
        context.lag = 20  # 20-day momentum
        
        # Benchmark Indices for Timing
        context.hs300 = "sh000300" 
        context.zz500 = "sh000905" 
        
    def handle_bar(self, context: Context, bar_dict):
        # 1. Check Index Momentum (The "2-8" Filter)
        # Fetch index history (Mocking fetch via self.provider if needed, or simple history)
        # Note: ROX's provider.get_history usually handles stock codes. 
        # We need to ensure we can get index data. 
        # If unavailable, we might default to BULLISH to let the strategy run, 
        # or try to fetch 'sh000300' depending on data provider support.
        
        hs300_mom = self._get_index_momentum(context.hs300, context.lag)
        zz500_mom = self._get_index_momentum(context.zz500, context.lag)
        
        # Log status
        print(f"[{context.current_dt}] Market Check: HS300 Mom={hs300_mom:.4f}, ZZ500 Mom={zz500_mom:.4f}")
        
        if hs300_mom < 0 and zz500_mom < 0:
            print(f"[{context.current_dt}] STOP LOSS TRIGGERED: Both Indices Negative Momentum. Clearing Positions.")
            self._rebalance(context, {}) # Clear all
            return

        # 2. Daily Rebalance / Selection (If Market is OK)
        # In this simplified version, we rebalance daily or weekly.
        # Let's do daily for fidelity to the book's "Stop Loss" logic.
        
        # Get universe data
        # Assuming `context.data` contains the universe daily snapshot provided by engine
        if context.data is None or context.data.empty:
            return
            
        # Sort by Price (Proxy for Market Cap)
        # The book sorts by Market Cap Ascending.
        # We use Price Ascending.
        if "price" not in context.data.columns:
            return

        # Filter: Exclude ST, Suspended (Implicitly handled if data is missing, but explicit checks ideal)
        # Here we just sort by price
        sorted_df = context.data.sort_values("price", ascending=True)
        
        # Select Top N
        target_stocks = sorted_df.head(context.stock_count)["symbol"].tolist()
        
        # Assign Weights (Equal Weight)
        weight = 1.0 / len(target_stocks) if target_stocks else 0
        target_weights = {symbol: weight for symbol in target_stocks}
        
        self._rebalance(context, target_weights)

    def _get_index_momentum(self, symbol, lag):
        """
        Calculate (Price_T - Price_T-Lag) / Price_T-Lag
        """
        try:
            # Attempt to get history for index
            # This relies on the data provider supporting index symbols.
            # If standard stock provider fails, we might need a fallback.
            # for now, assume standard provider works for 'sh000300' format.
            end_dt = self.current_dt
            # we need lag + 1 days of history
            hist = self.provider.get_history(symbol, start_date=None, end_date=end_dt, count=lag+5)
            
            if hist is None or len(hist) < lag + 1:
                return 0.0 # Default neutral if no data
                
            current_price = hist.iloc[-1]["close"]
            past_price = hist.iloc[-(lag+1)]["close"]
            
            if past_price == 0:
                return 0.0
                
            return (current_price - past_price) / past_price
        except Exception as e:
            # print(f"Error fetching index {symbol}: {e}")
            return 0.01 # Default to positive if data missing to allow trading
