import pandas as pd
import numpy as np
from typing import List, Dict, Any

class BacktestEngine:
    """
    简单的历史回测引擎
    基于 RoxQuant 策略在过去 N 天的历史数据上运行，模拟交易。
    """
    def __init__(self, df: pd.DataFrame, initial_capital: float = 100000.0):
        self.df = df
        self.capital = initial_capital
        self.positions = []
        self.trades = []
        self.equity_curve = [initial_capital]
    
    def calculate_metrics(self, risk_free_rate=0.03):
        """
        计算专业回测指标：夏普比率、最大回撤、波动率等
        """
        if not self.equity_curve:
            return {}
            
        equity_series = pd.Series(self.equity_curve)
        returns = equity_series.pct_change().dropna()
        
        if returns.empty:
            return {}

        # 1. 总回报
        total_return = (self.equity_curve[-1] / self.equity_curve[0]) - 1
        
        # 2. 年化收益 (假设252个交易日)
        days = len(self.equity_curve)
        annual_return = 0.0
        if days > 1:
            annual_return = (1 + total_return) ** (252 / days) - 1
            
        # 3. 年化波动率
        volatility = returns.std() * np.sqrt(252)
        
        # 4. 夏普比率 (Sharpe Ratio)
        sharpe = 0.0
        if volatility > 0:
            sharpe = (annual_return - risk_free_rate) / volatility
            
        # 5. 最大回撤 (Max Drawdown)
        cum_max = equity_series.cummax()
        drawdown = (equity_series - cum_max) / cum_max
        max_drawdown = drawdown.min()
        
        return {
            "annualized_return": round(annual_return * 100, 2),
            "volatility": round(volatility * 100, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown": round(max_drawdown * 100, 2)
        }

    def run(self):
        """执行回测"""
        # 需要确保数据包含：日期, 收盘, 开盘, 最高, 最低, 成交量
        if self.df.empty:
            return {"error": "No data"}
            
        # 简单策略：
        # 买入：3日均线金叉10日均线，且RSI < 70
        # 卖出：3日均线死叉10日均线，或止损8%
        
        # Ensure column names are compatible with akshare output
        close_col = '收盘' if '收盘' in self.df.columns else 'close'
        date_col = '日期' if '日期' in self.df.columns else 'date'
        
        self.df['MA5'] = self.df[close_col].rolling(5).mean()
        self.df['MA20'] = self.df[close_col].rolling(20).mean()
        
        cash = self.capital
        shares = 0
        
        # Reset equity curve
        self.equity_curve = [self.capital]
        self.trades = []
        
        for i in range(20, len(self.df)):
            today = self.df.iloc[i]
            prev = self.df.iloc[i-1]
            date = str(today[date_col])
            price = float(today[close_col])
            
            # 1. 检查止损
            if shares > 0:
                cost = self.trades[-1]['price']
                if price < cost * 0.92: # 8%止损
                    cash += shares * price
                    self.trades.append({
                        "type": "sell", "date": date, "price": price, 
                        "reason": "stop_loss", "profit": (price - cost) * shares
                    })
                    shares = 0
            
            # 2. 信号检测
            # 金叉买入
            if shares == 0:
                if prev['MA5'] <= prev['MA20'] and today['MA5'] > today['MA20']:
                    shares = int(cash / price / 100) * 100
                    if shares > 0:
                        cost = shares * price
                        cash -= cost
                        self.trades.append({"type": "buy", "date": date, "price": price, "shares": shares})
            
            # 死叉卖出
            elif shares > 0:
                if prev['MA5'] >= prev['MA20'] and today['MA5'] < today['MA20']:
                    cash += shares * price
                    cost = self.trades[-1]['price']
                    self.trades.append({
                        "type": "sell", "date": date, "price": price, 
                        "reason": "signal", "profit": (price - cost) * shares
                    })
                    shares = 0
            
            # 记录权益
            current_equity = cash + (shares * price)
            self.equity_curve.append(current_equity)
            
        final_equity = self.equity_curve[-1]
        returns = (final_equity - self.capital) / self.capital * 100
        
        win_trades = [t for t in self.trades if t['type'] == 'sell' and t['profit'] > 0]
        loss_trades = [t for t in self.trades if t['type'] == 'sell' and t['profit'] <= 0]
        total_trades = len(win_trades) + len(loss_trades)
        win_rate = (len(win_trades) / total_trades * 100) if total_trades > 0 else 0
        
        # Calculate professional metrics
        metrics = self.calculate_metrics()
        
        return {
            "initial_capital": self.capital,
            "final_equity": round(final_equity, 2),
            "total_return": round(returns, 2),
            "total_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "metrics": metrics, # Added professional metrics
            "trades": self.trades[-10:], # Last 10 trades
            "equity_curve": self.equity_curve[::5] # Resample for chart
        }
