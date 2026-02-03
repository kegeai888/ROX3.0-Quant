
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
from app.rox_quant.data_provider import DataProvider

logger = logging.getLogger(__name__)

class RankingStrategy:
    """
    Ranking / Rotation Strategy (BigQuant Logic Adapter)
    
    Logic:
    1. Select Top N stocks from a pool based on a Score (e.g., AI Prediction, Momentum).
    2. Rebalance daily/weekly.
    3. Sell stocks that fall out of Top N.
    4. Buy new stocks entering Top N.
    5. Equal weight distribution.
    """
    
    def __init__(self, initial_capital=1000000, top_n=5, change_num=1):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {} # {symbol: shares}
        self.history = []
        self.top_n = top_n
        self.change_num = change_num # Max turnover per day
        self.provider = DataProvider()
        
    def _fetch_data(self, pool: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical data for all stocks in pool.
        Returns: {symbol: DataFrame(date, close, volume, ...)}
        """
        data_map = {}
        # Convert string dates to datetime for calculation
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        days_needed = (end_dt - start_dt).days + 60 # Buffer for indicators
        
        logger.info(f"Fetching data for {len(pool)} stocks...")
        for symbol in pool:
            try:
                # Use DataProvider to get history
                # Note: get_history returns list of PricePoint(date, close, volume)
                points = self.provider.get_history(symbol, days=days_needed)
                if not points:
                    continue
                    
                df = pd.DataFrame([vars(p) for p in points])
                if df.empty: continue
                
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date').set_index('date')
                
                # Filter for backtest range
                mask = (df.index >= start_dt) & (df.index <= end_dt)
                if mask.sum() > 0:
                    data_map[symbol] = df
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
                
        return data_map

    def _calculate_scores(self, data_map: Dict[str, pd.DataFrame], current_date: datetime) -> Dict[str, float]:
        """
        Calculate ranking scores for available stocks on current_date.
        Default: Momentum (20-day return).
        In BigQuant, this would be the AI model output.
        """
        scores = {}
        for symbol, df in data_map.items():
            if current_date not in df.index:
                continue
            
            # Simple Momentum Factor: (Close / Close_20_days_ago) - 1
            # We need to look back
            try:
                # Get location of current_date
                loc = df.index.get_loc(current_date)
                if loc < 20: continue
                
                curr_price = df.iloc[loc]['close']
                prev_price = df.iloc[loc-20]['close']
                
                if prev_price > 0:
                    score = (curr_price / prev_price) - 1.0
                    scores[symbol] = score
            except Exception:
                pass
                
        return scores

    def run_backtest(self, stock_pool: List[str], start_date: str, end_date: str):
        """
        Run the rotation backtest.
        """
        # 1. Prepare Data
        data_map = self._fetch_data(stock_pool, start_date, end_date)
        if not data_map:
            return {"error": "No data found for stock pool"}
            
        # 2. Generate Trading Calendar (Union of all dates)
        all_dates = set()
        for df in data_map.values():
            all_dates.update(df.index)
        trading_dates = sorted(list(all_dates))
        
        # Filter dates within range
        s_dt = datetime.strptime(start_date, "%Y-%m-%d")
        e_dt = datetime.strptime(end_date, "%Y-%m-%d")
        trading_dates = [d for d in trading_dates if s_dt <= d <= e_dt]
        
        equity_curve = []
        logs = []
        
        logger.info(f"Running backtest on {len(trading_dates)} trading days...")
        
        for date in trading_dates:
            date_str = date.strftime("%Y-%m-%d")
            
            # --- 1. Update Portfolio Value (Mark to Market) ---
            current_prices = {}
            portfolio_value = self.cash
            
            for symbol, shares in self.positions.items():
                if symbol in data_map and date in data_map[symbol].index:
                    price = data_map[symbol].loc[date]['close']
                    current_prices[symbol] = price
                    portfolio_value += shares * price
                else:
                    # If suspended/missing, use last known price? 
                    # For simplicity, skip value update if missing (or assume 0 change)
                    pass 
            
            equity_curve.append({"time": date_str, "value": portfolio_value})
            
            # --- 2. Rank & Select ---
            # Simulate "AI Prediction"
            scores = self._calculate_scores(data_map, date)
            
            # Sort descending
            sorted_stocks = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            
            # Top N Candidates
            candidates = [s[0] for s in sorted_stocks[:self.top_n]]
            
            # --- 3. Rebalance Logic (BigQuant Style) ---
            
            # A. Sell Logic
            # Sell stocks not in candidates (or low rank)
            current_symbols = list(self.positions.keys())
            sell_count = 0
            
            # Identify stocks to sell (those no longer in top N)
            to_sell = [s for s in current_symbols if s not in candidates]
            
            # Also if we have too many positions (more than N), sell the worst ones
            # (Though logic above covers it mostly)
            
            for symbol in to_sell:
                if sell_count >= self.change_num:
                    break
                    
                # Execute Sell
                if symbol in current_prices:
                    price = current_prices[symbol]
                    revenue = self.positions[symbol] * price
                    self.cash += revenue
                    
                    logs.append({
                        "date": date_str, "action": "Sell", "symbol": symbol,
                        "price": price, "shares": self.positions[symbol],
                        "reason": f"Dropped from Top {self.top_n}"
                    })
                    
                    del self.positions[symbol]
                    sell_count += 1
            
            # B. Buy Logic
            # Buy stocks in candidates that we don't own
            current_symbols = list(self.positions.keys()) # Refresh
            if len(current_symbols) < self.top_n:
                to_buy = [s for s in candidates if s not in current_symbols]
                
                # Available slots
                slots_open = self.top_n - len(current_symbols)
                
                # Capital per slot
                # Equal weight strategy: Total Equity / N
                # Or just use available cash?
                # BigQuant code: context.stock_weights = 1/context.stock_count
                target_per_stock = portfolio_value / self.top_n
                
                for symbol in to_buy:
                    if len(self.positions) >= self.top_n:
                        break
                        
                    if symbol in current_prices:
                        price = current_prices[symbol]
                        
                        # Calculate buy amount
                        # Use min(cash, target)
                        budget = min(self.cash, target_per_stock)
                        shares = int(budget / price / 100) * 100
                        
                        if shares > 0:
                            cost = shares * price
                            self.cash -= cost
                            self.positions[symbol] = shares
                            
                            logs.append({
                                "date": date_str, "action": "Buy", "symbol": symbol,
                                "price": price, "shares": shares,
                                "reason": f"Entered Top {self.top_n}"
                            })
                            
        # --- Metrics ---
        metrics = self._calculate_metrics(equity_curve)
        
        return {
            "logs": logs,
            "equity": equity_curve,
            "metrics": metrics,
            "summary": {
                "initial": self.initial_capital,
                "final": equity_curve[-1]['value'] if equity_curve else 0
            }
        }

    def _calculate_metrics(self, equity_curve):
        if not equity_curve: return {}
        df = pd.DataFrame(equity_curve)
        df['returns'] = df['value'].pct_change().fillna(0)
        
        total_ret = (df['value'].iloc[-1] / df['value'].iloc[0]) - 1
        ann_ret = (1 + total_ret) ** (252 / len(df)) - 1 if len(df) > 0 else 0
        vol = df['returns'].std() * np.sqrt(252)
        sharpe = (ann_ret - 0.03) / vol if vol > 0 else 0
        
        df['cummax'] = df['value'].cummax()
        max_dd = ((df['value'] - df['cummax']) / df['cummax']).min()
        
        return {
            "annualized_return": round(ann_ret * 100, 2),
            "volatility": round(vol * 100, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown": round(max_dd * 100, 2)
        }
