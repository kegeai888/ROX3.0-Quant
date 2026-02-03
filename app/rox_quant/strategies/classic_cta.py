import pandas as pd
import numpy as np
from app.analysis.indicators import BOLL, MACD

class CTAStrategies:
    """
    Classic CTA (Commodity Trading Advisor) Strategies Implementation
    Includes:
    1. Dual Thrust (Trend Following)
    2. R-Breaker (Intraday Reversal)
    3. Bollinger Mean Reversion (Statistical Arbitrage)
    """

    def __init__(self, initial_capital=1000000):
        self.initial_capital = initial_capital

    def run_dual_thrust(self, df: pd.DataFrame, n=4, k1=0.5, k2=0.5):
        """
        Dual Thrust Strategy
        Logic:
        - Range = Max(HH - LC, HC - LL)
        - Buy Trigger = Open + K1 * Range
        - Sell Trigger = Open - K2 * Range
        """
        if df.empty: return {}
        
        df = df.copy()
        cash = self.initial_capital
        position = 0
        equity_curve = []
        logs = []

        # Calculate Range
        # HH: N-day High, LC: N-day Close Low, etc.
        # Note: We need to shift 1 day because signals are based on previous N days
        df['hh'] = df['high'].rolling(n).max().shift(1)
        df['hc'] = df['close'].rolling(n).max().shift(1)
        df['ll'] = df['low'].rolling(n).min().shift(1)
        df['lc'] = df['close'].rolling(n).min().shift(1)
        
        df['range'] = np.maximum(df['hh'] - df['lc'], df['hc'] - df['ll'])
        df['buy_trigger'] = df['open'] + k1 * df['range']
        df['sell_trigger'] = df['open'] - k2 * df['range']

        for i in range(n, len(df)):
            curr = df.iloc[i]
            date_str = str(curr['date'])
            price = curr['close']
            
            # Buy Signal
            if position == 0 and curr['high'] > curr['buy_trigger']:
                shares = int(cash / price / 100) * 100
                if shares > 0:
                    cash -= shares * price
                    position = shares
                    logs.append({
                        "date": date_str, "action": "Buy (Dual Thrust)", 
                        "price": price, "shares": shares, "reason": "Price broke above upper range"
                    })

            # Sell Signal (Stop Loss or Reverse) - Simplified here as Exit
            elif position > 0 and curr['low'] < curr['sell_trigger']:
                cash += position * price
                logs.append({
                    "date": date_str, "action": "Sell (Dual Thrust)", 
                    "price": price, "shares": position, "reason": "Price fell below lower range"
                })
                position = 0

            equity_curve.append({"time": date_str, "value": cash + position * price})

        return self._format_result(logs, equity_curve)

    def run_r_breaker(self, df: pd.DataFrame):
        """
        R-Breaker Strategy (Simplified for Daily bars, originally Intraday)
        Pivot Points based logic.
        """
        if df.empty: return {}
        
        df = df.copy()
        cash = self.initial_capital
        position = 0
        equity_curve = []
        logs = []

        # Pivot Points Calculation (based on previous day)
        # Pivot = (H + L + C) / 3
        prev = df.shift(1)
        df['pivot'] = (prev['high'] + prev['low'] + prev['close']) / 3
        df['r1'] = 2 * df['pivot'] - prev['low']  # Resistance 1
        df['s1'] = 2 * df['pivot'] - prev['high'] # Support 1
        df['r2'] = df['pivot'] + (prev['high'] - prev['low']) # Resistance 2
        df['s2'] = df['pivot'] - (prev['high'] - prev['low']) # Support 2
        df['r3'] = prev['high'] + 2 * (df['pivot'] - prev['low']) # Resistance 3
        df['s3'] = prev['low'] - 2 * (prev['high'] - df['pivot']) # Support 3

        for i in range(1, len(df)):
            curr = df.iloc[i]
            date_str = str(curr['date'])
            price = curr['close']
            
            # Trend Mode: Break R3 (Buy) or Break S3 (Sell)
            # Reversal Mode: High > R2 but Close < R1 (Sell), Low < S2 but Close > S1 (Buy)
            
            action = None
            
            # Buy Conditions
            if position == 0:
                # Trend Buy
                if curr['high'] > curr['r3']:
                    action = "buy_trend"
                # Reversal Buy
                elif curr['low'] < curr['s2'] and curr['close'] > curr['s1']:
                    action = "buy_reversal"
                
                if action:
                    shares = int(cash / price / 100) * 100
                    if shares > 0:
                        cash -= shares * price
                        position = shares
                        logs.append({
                            "date": date_str, "action": "Buy", 
                            "price": price, "shares": shares, 
                            "reason": f"R-Breaker Signal: {action}"
                        })

            # Sell Conditions
            elif position > 0:
                # Trend Sell (Stop Loss logic effectively)
                if curr['low'] < curr['s3']:
                    action = "sell_trend"
                # Reversal Sell
                elif curr['high'] > curr['r2'] and curr['close'] < curr['r1']:
                    action = "sell_reversal"
                
                if action:
                    cash += position * price
                    logs.append({
                        "date": date_str, "action": "Sell", 
                        "price": price, "shares": position, 
                        "reason": f"R-Breaker Signal: {action}"
                    })
                    position = 0

            equity_curve.append({"time": date_str, "value": cash + position * price})

        return self._format_result(logs, equity_curve)

    def run_bollinger_reversion(self, df: pd.DataFrame, window=20, num_std=2):
        """
        Bollinger Bands Mean Reversion
        Buy when price < Lower Band
        Sell when price > Upper Band
        """
        if df.empty: return {}
        
        df = df.copy()
        cash = self.initial_capital
        position = 0
        equity_curve = []
        logs = []

        # Use shared indicator library
        df['upper'], df['ma'], df['lower'] = BOLL(df['close'], n=window, k=num_std)

        for i in range(window, len(df)):
            curr = df.iloc[i]
            date_str = str(curr['date'])
            price = curr['close']
            
            # Buy Signal: Price crosses below Lower Band
            if position == 0 and curr['close'] < curr['lower']:
                shares = int(cash / price / 100) * 100
                if shares > 0:
                    cash -= shares * price
                    position = shares
                    logs.append({
                        "date": date_str, "action": "Buy", 
                        "price": price, "shares": shares, 
                        "reason": "Price below Bollinger Lower Band"
                    })

            # Sell Signal: Price crosses above Upper Band (or MA for quicker exit)
            elif position > 0 and curr['close'] > curr['upper']:
                cash += position * price
                logs.append({
                    "date": date_str, "action": "Sell", 
                    "price": price, "shares": position, 
                    "reason": "Price above Bollinger Upper Band"
                })
                position = 0

            equity_curve.append({"time": date_str, "value": cash + position * price})

        return self._format_result(logs, equity_curve)

    def run_macd_trend(self, df: pd.DataFrame, fast=12, slow=26, signal=9):
        """
        MACD Trend Following Strategy
        Buy when DIF crosses above DEA (Golden Cross)
        Sell when DIF crosses below DEA (Death Cross)
        """
        if df.empty: return {}
        
        df = df.copy()
        cash = self.initial_capital
        position = 0
        equity_curve = []
        logs = []

        # Use shared indicator library
        df['dif'], df['dea'], df['macd_hist'] = MACD(df['close'], fast=fast, slow=slow, signal=signal)

        # Start from the point where we have valid data
        start_idx = slow + signal 
        
        for i in range(start_idx, len(df)):
            curr = df.iloc[i]
            prev = df.iloc[i-1]
            date_str = str(curr['date'])
            price = curr['close']
            
            # Buy Signal: Golden Cross (DIF crosses above DEA)
            if position == 0 and prev['dif'] < prev['dea'] and curr['dif'] > curr['dea']:
                shares = int(cash / price / 100) * 100
                if shares > 0:
                    cash -= shares * price
                    position = shares
                    logs.append({
                        "date": date_str, "action": "Buy (MACD)", 
                        "price": price, "shares": shares, 
                        "reason": "MACD Golden Cross"
                    })

            # Sell Signal: Death Cross (DIF crosses below DEA)
            elif position > 0 and prev['dif'] > prev['dea'] and curr['dif'] < curr['dea']:
                cash += position * price
                logs.append({
                    "date": date_str, "action": "Sell (MACD)", 
                    "price": price, "shares": position, 
                    "reason": "MACD Death Cross"
                })
                position = 0

            equity_curve.append({"time": date_str, "value": cash + position * price})

        return self._format_result(logs, equity_curve)

    def _format_result(self, logs, equity_curve):
        final_val = equity_curve[-1]['value'] if equity_curve else self.initial_capital
        ret = ((final_val / self.initial_capital) - 1) * 100
        
        # Calculate metrics
        metrics = {}
        if equity_curve:
            import pandas as pd
            import numpy as np
            
            df_eq = pd.DataFrame(equity_curve)
            if not df_eq.empty and "value" in df_eq.columns:
                df_eq["returns"] = df_eq["value"].pct_change().fillna(0)
                
                total_return = (df_eq["value"].iloc[-1] / df_eq["value"].iloc[0]) - 1
                days = len(df_eq)
                annual_return = 0.0
                if days > 1:
                    annual_return = (1 + total_return) ** (252 / days) - 1
                
                volatility = df_eq["returns"].std() * np.sqrt(252)
                risk_free_rate = 0.03
                sharpe = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0
                
                df_eq["cum_max"] = df_eq["value"].cummax()
                df_eq["drawdown"] = (df_eq["value"] - df_eq["cum_max"]) / df_eq["cum_max"]
                max_drawdown = df_eq["drawdown"].min()
                
                metrics = {
                    "annualized_return": round(annual_return * 100, 2),
                    "volatility": round(volatility * 100, 2),
                    "sharpe_ratio": round(sharpe, 2),
                    "max_drawdown": round(max_drawdown * 100, 2)
                }

        return {
            "logs": logs,
            "equity": equity_curve,
            "metrics": metrics,
            "summary": {
                "initial": self.initial_capital,
                "final": final_val,
                "return": f"{ret:.2f}%"
            }
        }
