import pandas as pd
import logging
from typing import Dict, Any, List, Optional
import datetime

logger = logging.getLogger(__name__)

class Context:
    def __init__(self):
        self.portfolio = {
            "cash": 100000.0,
            "total_value": 100000.0,
            "positions": {} # code -> qty
        }
        self.universe = []
        # Dynamic attributes allowed
        self.model = None
        self.model_weights = {}
        self.holding_period = 0
        self.max_position_pct = 1.0
        
        # Internal state for the engine to use during execution
        self._current_date = None
        self._data_provider = None
        self._engine = None

    def order_target_value(self, code: str, target_value: float):
        if self._engine:
            self._engine.order_target_value(code, target_value)

    def order_target(self, code: str, amount: int):
        if self._engine:
            self._engine.order_target(code, amount)

class QuantEngine:
    def __init__(self, data_provider):
        self.provider = data_provider
        self.context = Context()
        self.context._data_provider = data_provider
        self.context._engine = self
        
        self.strategy_initialize = None
        self.strategy_handle_data = None
        
        self.history = [] # List of portfolio snapshots

    def load_strategy(self, strategy_module):
        if hasattr(strategy_module, 'initialize'):
            self.strategy_initialize = strategy_module.initialize
        if hasattr(strategy_module, 'handle_data'):
            self.strategy_handle_data = strategy_module.handle_data
            
        # Run initialize immediately
        if self.strategy_initialize:
            self.strategy_initialize(self.context)

    def order_target_value(self, code: str, target_value: float):
        """
        Adjust position to reach target value.
        """
        current_price = self._get_current_price(code)
        if current_price <= 0:
            return

        current_qty = self.context.portfolio["positions"].get(code, 0)
        current_val = current_qty * current_price
        
        diff_val = target_value - current_val
        
        if abs(diff_val) < current_price:
            return # Change too small
            
        qty_to_trade = int(diff_val / current_price)
        
        if qty_to_trade == 0:
            return

        self._execute_trade(code, qty_to_trade, current_price)

    def order_target(self, code: str, target_qty: int):
        """
        Adjust position to reach target quantity.
        """
        current_qty = self.context.portfolio["positions"].get(code, 0)
        qty_to_trade = int(target_qty - current_qty)
        
        if qty_to_trade == 0:
            return
            
        current_price = self._get_current_price(code)
        if current_price <= 0:
            return
            
        self._execute_trade(code, qty_to_trade, current_price)

    def _execute_trade(self, code: str, qty: int, price: float):
        cost = qty * price
        commission = abs(cost) * 0.0003 # 0.03% commission estimate
        
        # Check cash if buying
        if qty > 0:
            if self.context.portfolio["cash"] < cost + commission:
                # Adjust qty
                qty = int((self.context.portfolio["cash"] - commission) / price)
                if qty <= 0:
                    return
                cost = qty * price
                commission = abs(cost) * 0.0003

        self.context.portfolio["cash"] -= (cost + commission)
        
        old_qty = self.context.portfolio["positions"].get(code, 0)
        new_qty = old_qty + qty
        
        if new_qty == 0:
            if code in self.context.portfolio["positions"]:
                del self.context.portfolio["positions"][code]
        else:
            self.context.portfolio["positions"][code] = new_qty
            
        # logger.info(f"Trade: {code} Qty:{qty} Price:{price} Cash:{self.context.portfolio['cash']:.2f}")

    def _get_current_price(self, code: str) -> float:
        # Helper to get price from the current bar in the loop
        # Since run_backtest iterates, we assume we have access to the current bar data
        # But order_* methods are called from handle_data which receives `data`.
        # However, for simplicity, we can also look it up from the data provider or cache if needed.
        # But simpler: the order is executed at the CLOSE of the current bar (or OPEN of next).
        # For simplicity here, we execute at current CLOSE price available in context.
        return self.context._current_prices.get(code, 0.0)

    def run_backtest(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Run the backtest loop.
        """
        logger.info(f"Starting backtest from {start_date} to {end_date}")
        
        # 1. Generate trading days
        # For simplicity, just iterate calendar days or use provider to get index dates
        # Using a simple date loop for now
        s_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        e_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        
        current_date = s_date
        
        # Pre-fetch history for universe to optimize
        universe_data = {}
        for code in self.context.universe:
            hist = self.provider.get_history(code, start_date, end_date)
            # Convert to dict keyed by date string
            universe_data[code] = {d['date']: d for d in hist}
            
        while current_date <= e_date:
            date_str = current_date.strftime("%Y-%m-%d")
            
            # Prepare 'data' dict for handle_data
            bar_data = {}
            self.context._current_prices = {}
            
            has_data = False
            for code in self.context.universe:
                if date_str in universe_data[code]:
                    row = universe_data[code][date_str]
                    bar_data[code] = row
                    self.context._current_prices[code] = row['close']
                    has_data = True
            
            if has_data:
                self.context._current_date = current_date
                
                # Call Strategy
                if self.strategy_handle_data:
                    self.strategy_handle_data(self.context, bar_data)
                
                # Update Portfolio Value
                position_val = 0.0
                for code, qty in self.context.portfolio["positions"].items():
                    price = self.context._current_prices.get(code, 0.0)
                    # If no price today, use last known? For now 0 or skip
                    # In real engine, we'd keep last price.
                    # Assuming universe_data is complete or we handle gaps.
                    if price == 0 and code in universe_data:
                         # Fallback to previous close if today missing? 
                         # Simplifying: just use 0 if missing today (harsh but simple)
                         pass
                    position_val += qty * price
                
                self.context.portfolio["total_value"] = self.context.portfolio["cash"] + position_val
                
                # Record History
                self.history.append({
                    "date": date_str,
                    "value": self.context.portfolio["total_value"],
                    "cash": self.context.portfolio["cash"],
                    "positions": self.context.portfolio["positions"].copy()
                })
            
            current_date += datetime.timedelta(days=1)
            
        return self.history
