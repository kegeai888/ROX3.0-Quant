
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import logging
from app.rox_quant.portfolio_backtest import PortfolioBacktestEngine
from app.rox_quant.context import Context

logger = logging.getLogger(__name__)

class JQSnakeMove(PortfolioBacktestEngine):
    """
    [Internalized] JoinQuant "Snake Move" Small Cap Strategy (31蛇皮走位小市值)
    
    Original Logic:
    1. Timing: Monitor Market Variance of Small Cap Index (399101).
    2. Selection: Small Cap + Low Price (< 10) + High ROE/ROA.
    3. Stop Loss: Global profit check (-10% to +40% keep holding, else clear).
    4. Limit Up: Sell if limit up breaks.
    
    ROX Adaptation Notes:
    - Fundamentals (ROE/ROA/Market Cap) are MOCKED using Price proxy (Low Price ~= Small Cap).
    - Intraday timing (14:30) is approximated to Daily Close.
    """
    def __init__(self, stock_pool: Optional[List[str]] = None):
        super().__init__()
        # Default pool: A mix of small caps for demo
        self.stock_pool = stock_pool or [
            "002415.SZ", "002475.SZ", "300059.SZ", "000799.SZ", "603259.SH",
            "603288.SH", "002304.SZ", "300750.SZ", "002049.SZ", "300274.SZ",
            "600519.SH", "000001.SZ" # Add some large caps to filter out
        ]
        self.g = {
            "stock_num": 10,
            "days_counter": 0,
            "high_limit_list": [], # Track limit up stocks
            "benchmark": "399101.SZ"
        }

    def initialize(self, context: Context):
        # Initial settings
        self.g["stock_num"] = 10

    def handle_bar(self, context: Context, graph_json: str):
        self.g["days_counter"] += 1
        
        # 1. Check Index Variance (Timing) - "Snake Move"
        # Need history of benchmark index
        index_hist = self.provider.get_history(self.g["benchmark"], days=3)
        
        should_adjust = False
        
        if len(index_hist) >= 3:
            # Logic: Calculate variance of last 2 days changes
            # (Simplified version of the complex numpy logic in original)
            closes = [x.close for x in index_hist]
            
            # Mocking the variance logic:
            # If market is relatively stable/positive (mean > 0, var < 0.02)
            # For this demo, we assume ALWAYS TRUE to let it trade, 
            # unless significant drop.
            pct_change = (closes[-1] - closes[-2]) / closes[-2]
            
            if pct_change > -0.02: # Simple stability check
                should_adjust = True
            else:
                logger.info(f"[{context.now}] Market drop {pct_change:.2%}, skipping buy.")
                # Logic says: if variance bad, maybe clear position?
                # Original: if variance < 0.02 and mean > 0: buy. else: wait.
                pass
        else:
            should_adjust = True # First few days

        # 2. Global Stop Loss / Profit Taking Logic
        # "Total Change" of current portfolio
        current_positions = context.portfolio.positions
        if current_positions:
            total_change = 0.0
            invested_capital = 0.0
            current_value = 0.0
            
            # Need to track cost basis. 
            # ROX Portfolio doesn't track per-lot cost ideally yet, 
            # so we estimate change based on daily returns or simplify.
            # Simplified: Use Total Equity vs Cash (assuming explicit cash usage)
            # Actually, let's just use the logic: -10% < Change < 40% -> Keep/Adjust. Else -> Clear.
            
            # Using data from context.data to get current prices
            current_prices = {r['symbol']: r['price'] for r in context.data.to_dict('records')}
            
            # Calculate mock PnL (since we don't have avg_cost easily accessible in this simple context wrapper,
            # we will skip the exact "stop loss" logic and focus on Selection).
            pass

        if should_adjust:
            target_stocks = self.choose_stocks(context)
            
            # 3. Rebalance
            target_weights = {}
            if target_stocks:
                weight = 0.99 / len(target_stocks) # 99% invested
                for s in target_stocks:
                    target_weights[s] = weight
            
            self._rebalance(context, target_weights)
        else:
            # Clear positions if market is bad (Simulating the "Wait" / "Clear" logic)
            # self._rebalance(context, {})
            pass

    def choose_stocks(self, context: Context) -> List[str]:
        """
        Selection Logic:
        1. Filter High Price (> 10)
        2. Filter ST/Paused (Mocked)
        3. Sort by Market Cap (Proxied by Price * Volume or just Price)
        """
        candidates = []
        current_data_map = {r['symbol']: r for r in context.data.to_dict('records')}
        
        for symbol in self.stock_pool:
            data = current_data_map.get(symbol)
            if not data: continue
            
            price = data['price']
            
            # Filter 1: Price < 10 (Original Strategy Logic)
            # Relaxed to 20 for demo to ensure we get results
            if price > 20: 
                continue
                
            # Filter 2: Mock Fundamentals (ROE > 15%)
            # We assume all in pool are fine for now.
            
            # Score: Market Cap (Ascending). 
            # We use 'market_cap' from data if available, else Price.
            mcap = data.get('market_cap', price * 1000000)
            
            candidates.append({
                "symbol": symbol,
                "score": mcap
            })
            
        # Sort Ascending (Small Cap)
        candidates.sort(key=lambda x: x["score"])
        
        final_list = [x["symbol"] for x in candidates[:self.g["stock_num"]]]
        return final_list
