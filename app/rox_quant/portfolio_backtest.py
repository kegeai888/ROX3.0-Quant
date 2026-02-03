from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import re
from app.rox_quant.graph_runner import StrategyGraphRunner
from app.rox_quant.context import Context
from app.rox_quant.data_provider import DataProvider

logger = logging.getLogger(__name__)

class PortfolioBacktestEngine:
    def __init__(self):
        self.runner = StrategyGraphRunner()
        self.results = {
            "dates": [],
            "equity_curve": [],
            "positions": [], # List of {symbol: weight}
            "trades": []
        }
        self.context = None
        self.price_history = {} # For mock data / last price cache
        self.provider = DataProvider()
        self.active_symbols = []
        self.history_cache = {} # {symbol: {date: PricePoint}}
        
    def run(self, graph_json: str, start_date: str, end_date: str, initial_capital: float = 100000.0) -> Dict:
        """
        运行回测 (Main Loop)
        遵循 init -> before_trading -> handle_bar -> after_trading 的生命周期
        """
        logger.info(f"Starting backtest from {start_date} to {end_date}")
        
        # Initialize Context
        self.context = Context(initial_capital)
        
        # 0. Prepare Data
        self.active_symbols = self._extract_symbols(graph_json)
        if not self.active_symbols:
             # Fallback defaults
             self.active_symbols = ["600519", "000001", "300750", "601318", "000858"]
        self._preload_history(start_date, end_date)
        
        # 1. Initialize Strategy
        self.initialize(self.context)
        
        # 2. Generate Trading Calendar
        dates = self._generate_trading_dates(start_date, end_date)
        
        # 清空价格缓存
        if not self.price_history:
            self.price_history = {}
            
        for date in dates:
            date_str = date.strftime("%Y-%m-%d")
            self.context.now = date_str
            
            # 3. Before Trading (Data Preparation)
            self.before_trading(self.context)
            
            # 4. Handle Bar (Strategy Execution & Trading)
            self.handle_bar(self.context, graph_json)
            
            # 5. After Trading (Settlement & Reporting)
            self.after_trading(self.context)
            
        self.results["metrics"] = self._calculate_metrics()
        return self.results

    def _calculate_metrics(self) -> Dict[str, Any]:
        equity_curve = self.results["equity_curve"]
        if not equity_curve:
            return {}
        
        # Convert to Series
        df_equity = pd.Series(equity_curve)
        
        # 1. Total Return
        total_return = (df_equity.iloc[-1] / df_equity.iloc[0]) - 1
        
        # 2. Daily Returns
        daily_returns = df_equity.pct_change().dropna()
        
        # 3. Annualized Return (CAGR)
        days = len(equity_curve)
        if days > 1:
            years = days / 252.0
            # Handle negative equity or zero
            start_val = df_equity.iloc[0]
            end_val = df_equity.iloc[-1]
            if start_val > 0 and end_val > 0:
                cagr = (end_val / start_val) ** (1 / max(years, 0.001)) - 1
            else:
                cagr = -1.0 # Ruined
        else:
            cagr = 0.0
            
        # 4. Volatility (Annualized)
        volatility = daily_returns.std() * np.sqrt(252)
        
        # 5. Sharpe Ratio (Assume Rf = 2%)
        rf = 0.02
        if volatility > 0:
            sharpe = (cagr - rf) / volatility
        else:
            sharpe = 0.0
            
        # 6. Sortino Ratio (Downside Deviation)
        negative_returns = daily_returns[daily_returns < 0]
        downside_std = negative_returns.std() * np.sqrt(252)
        if downside_std > 0:
            sortino = (cagr - rf) / downside_std
        else:
            sortino = 0.0
            
        # 7. Max Drawdown
        rolling_max = df_equity.cummax()
        drawdown = (df_equity - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        return {
            "total_return": round(total_return * 100, 2),
            "cagr": round(cagr * 100, 2),
            "volatility": round(volatility * 100, 2),
            "sharpe": round(sharpe, 2),
            "sortino": round(sortino, 2),
            "max_drawdown": round(max_drawdown * 100, 2)
        }

    def initialize(self, context: Context):
        """策略初始化"""
        logger.info("Initializing strategy...")
        # Future: Run 'init' nodes from graph if any

    def before_trading(self, context: Context):
        """盘前准备"""
        # Fetch Data (Real or Mock)
        snapshot_df = self._get_snapshot(context.now)
        context.data = snapshot_df

    def handle_bar(self, context: Context, graph_json: str):
        """每日逻辑"""
        # 1. Run Graph Strategy
        # Pass context.data to graph runner
        run_ctx = {"data": context.data, "date": context.now}
        
        try:
            result = self.runner.run(graph_json, run_ctx)
        except Exception as e:
            logger.error(f"Error running strategy on {context.now}: {e}")
            return

        # 2. Parse Signals (Target Weights)
        target_weights = {}
        if result.get("status") == "success":
            for node_id, res in result.get("results", {}).items():
                # 假设字典类型的即为权重结果
                if isinstance(res, dict) and len(res) > 0:
                    target_weights = res
                    break
        
        # 3. Execute Rebalance (Order Execution)
        self._rebalance(context, target_weights)

    def after_trading(self, context: Context):
        """盘后结算"""
        # Record results
        self.results["dates"].append(context.now)
        self.results["equity_curve"].append(context.portfolio.total_value)
        self.results["positions"].append(context.portfolio.positions.copy())

    def _rebalance(self, context: Context, target_weights: Dict[str, float]):
        """执行调仓"""
        if context.data is None or context.data.empty:
            return

        current_prices = context.data.set_index("symbol")["price"].to_dict()
        
        # Update current portfolio value based on today's close prices
        context.portfolio.update(current_prices)
        total_equity = context.portfolio.total_value
        
        # Calculate new positions
        new_positions = {}
        used_cash = 0.0
        
        for symbol, weight in target_weights.items():
            price = current_prices.get(symbol, 0.0)
            if price > 0:
                target_value = total_equity * weight
                shares = int(target_value / price)
                if shares > 0:
                    new_positions[symbol] = shares
                    used_cash += shares * price
        
        # Update portfolio state
        context.portfolio.positions = new_positions
        context.portfolio.cash = total_equity - used_cash
        context.portfolio.update(current_prices) # Re-calc to be precise

    def _generate_trading_dates(self, start_date: str, end_date: str) -> List[datetime]:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        dates = []
        curr = start
        while curr <= end:
            if curr.weekday() < 5: # Mon-Fri
                dates.append(curr)
            curr += timedelta(days=1)
        return dates

    def _extract_symbols(self, graph_json: str) -> List[str]:
        try:
            # Simple regex to find 6-digit codes
            codes = re.findall(r'\d{6}', graph_json)
            # Filter valid codes roughly
            valid = [c for c in codes if c.startswith('6') or c.startswith('0') or c.startswith('3')]
            return list(set(valid))
        except:
            return []

    def _preload_history(self, start_date: str, end_date: str):
        # Extend range slightly
        days = 365 * 2 # Load enough history
        logger.info(f"Preloading history for {len(self.active_symbols)} symbols...")
        for sym in self.active_symbols:
            if sym not in self.history_cache:
                try:
                    data = self.provider.get_history(sym, days=days)
                    if data:
                        self.history_cache[sym] = {d.date: d for d in data}
                except Exception as e:
                    logger.error(f"Failed to preload {sym}: {e}")

    def _get_snapshot(self, date_str: str) -> pd.DataFrame:
        data = []
        for sym in self.active_symbols:
            hist = self.history_cache.get(sym, {})
            point = hist.get(date_str)
            
            price = 0.0
            change = 0.0
            prev_price = self.price_history.get(sym)
            
            if point:
                price = point.close
                # Calculate change from previous simulation step
                if prev_price and prev_price > 0:
                    change = (price - prev_price) / prev_price
                else:
                    change = 0.0
                    
                pe, pb, cap = 20.0, 2.0, 1000.0
            else:
                # Fallback to Mock (Random Walk)
                if not prev_price: prev_price = 100.0
                change = np.random.normal(0, 0.02)
                price = prev_price * (1 + change)
                pe, pb, cap = 20.0, 2.0, 1000.0
            
            if price <= 0: price = 10.0 # Safety
            
            self.price_history[sym] = price
            
            data.append({
                "symbol": sym,
                "name": sym,
                "price": round(price, 2),
                "pe_ratio": pe,
                "pb_ratio": pb,
                "market_cap": cap,
                "return_rate": round(change * 100, 2)
            })
            
        return pd.DataFrame(data)
