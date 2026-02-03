"""
P3.5 Day 1: 性能指标计算 - PerformanceMetrics
作用：从交易记录和账户净值曲线，计算关键的交易绩效指标
关键指标解读：
  - 胜率 (Win Rate): 盈利交易数 / 总交易数。越高越好，>50% 表示大多数交易盈利
  - 盈亏比 (Profit Factor): 总盈利 / 总亏损。>1 表示赚得多，亏得少
  - 最大回撤 (Max Drawdown): 从高点到低点的最大跌幅。越小越好，反映风险大小
  - 夏普比 (Sharpe Ratio): 年化收益 / 年化波动率。衡量风险调整后收益，>1 较好
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import numpy as np
import pandas as pd
from datetime import datetime


@dataclass
class PerformanceReport:
    """性能指标报告"""
    # 基础指标
    total_trades: int = 0                    # 总交易笔数
    winning_trades: int = 0                  # 盈利交易数
    losing_trades: int = 0                   # 亏损交易数
    
    # 收益指标
    total_profit: float = 0.0                # 总利润（元）
    total_loss: float = 0.0                  # 总亏损（元）
    net_profit: float = 0.0                  # 净利润（元）
    win_rate: float = 0.0                    # 胜率（%）
    profit_factor: float = 0.0               # 盈亏比 (总盈利/总亏损)
    
    # 风险指标
    max_drawdown: float = 0.0                # 最大回撤（%）
    max_drawdown_amount: float = 0.0         # 最大回撤（元）
    average_profit: float = 0.0              # 平均盈利（元）
    average_loss: float = 0.0                # 平均亏损（元）
    profit_loss_ratio: float = 0.0           # 平均盈利/平均亏损
    
    # 收益率指标
    initial_capital: float = 0.0             # 初始资金
    final_capital: float = 0.0               # 最终资金
    total_return: float = 0.0                # 总收益率（%）
    
    # 时间指标
    sharpe_ratio: float = 0.0                # 夏普比
    annual_return: float = 0.0               # 年化收益率（%）
    annual_volatility: float = 0.0           # 年化波动率（%）
    
    # 其他指标
    consecutive_wins: int = 0                # 最大连胜数
    consecutive_losses: int = 0              # 最大连败数
    recovery_factor: float = 0.0             # 恢复因子 (净利润/最大回撤)
    
    def __str__(self) -> str:
        """格式化输出性能报告"""
        lines = [
            "\n" + "="*60,
            "📊 回测性能报告".center(60),
            "="*60,
            f"\n【基本统计】",
            f"  总交易笔数:     {self.total_trades:>6} 笔",
            f"  盈利交易:       {self.winning_trades:>6} 笔",
            f"  亏损交易:       {self.losing_trades:>6} 笔",
            f"  胜率:           {self.win_rate:>6.2f} %",
            
            f"\n【收益分析】",
            f"  初始资金:       {self.initial_capital:>12,.0f} 元",
            f"  最终资金:       {self.final_capital:>12,.0f} 元",
            f"  总利润:         {self.total_profit:>12,.0f} 元",
            f"  总亏损:         {-self.total_loss:>12,.0f} 元",
            f"  净利润:         {self.net_profit:>12,.0f} 元",
            f"  总收益率:       {self.total_return:>12.2f} %",
            f"  盈亏比:         {self.profit_factor:>12.2f} (越高越好)",
            
            f"\n【风险分析】",
            f"  最大回撤:       {self.max_drawdown:>12.2f} % (越小越好)",
            f"  最大回撤额:     {-self.max_drawdown_amount:>12,.0f} 元",
            f"  平均单笔盈利:   {self.average_profit:>12,.0f} 元",
            f"  平均单笔亏损:   {-self.average_loss:>12,.0f} 元",
            f"  盈亏比率:       {self.profit_loss_ratio:>12.2f} (>1较好)",
            f"  恢复因子:       {self.recovery_factor:>12.2f} (越高越好)",
            
            f"\n【收益质量】",
            f"  年化收益率:     {self.annual_return:>12.2f} %",
            f"  年化波动率:     {self.annual_volatility:>12.2f} %",
            f"  夏普比:         {self.sharpe_ratio:>12.2f} (>1较好)",
            
            f"\n【连续性】",
            f"  最大连胜:       {self.consecutive_wins:>6} 笔",
            f"  最大连败:       {self.consecutive_losses:>6} 笔",
            
            "="*60 + "\n"
        ]
        return "\n".join(lines)


class PerformanceMetrics:
    """
    性能指标计算器
    
    使用方式：
      metrics = PerformanceMetrics()
      report = metrics.calculate(trades, portfolio_values, portfolio_dates, initial_capital)
      print(report)
    """
    
    def __init__(self):
        self.report = PerformanceReport()
    
    def calculate(self, 
                  trades: List,  # 来自 BacktestEngine.get_trades()
                  portfolio_values: List[float],  # 来自 BacktestEngine.get_portfolio_values()[0]
                  portfolio_dates: List,  # 来自 BacktestEngine.get_portfolio_values()[1]
                  initial_capital: float) -> PerformanceReport:
        """
        计算所有性能指标
        
        Args:
            trades: 交易记录列表（BacktestEngine.get_trades() 返回）
            portfolio_values: 账户净值曲线
            portfolio_dates: 净值对应的日期
            initial_capital: 初始资金
        
        Returns:
            PerformanceReport: 完整的性能报告对象
        """
        
        # 重置报告对象
        self.report = PerformanceReport()
        
        # 设置基础数据
        self.report.initial_capital = initial_capital
        self.report.final_capital = portfolio_values[-1] if portfolio_values else initial_capital
        
        # 如果没有交易，返回空报告
        if not trades:
            self.report.total_trades = 0
            self.report.total_return = ((self.report.final_capital - initial_capital) / initial_capital) * 100
            return self.report
        
        # 计算基础交易统计
        self._calculate_trade_stats(trades)
        
        # 计算收益指标
        self._calculate_profit_metrics(trades)
        
        # 计算风险指标
        self._calculate_risk_metrics(portfolio_values, initial_capital)
        
        # 计算时间序列指标
        if len(portfolio_dates) > 1:
            self._calculate_time_based_metrics(portfolio_values, portfolio_dates)
        
        # 计算连续性指标
        self._calculate_consecutive_metrics(trades)
        
        # 计算恢复因子
        if self.report.max_drawdown_amount != 0:
            self.report.recovery_factor = abs(self.report.net_profit / self.report.max_drawdown_amount)
        
        return self.report
    
    def _calculate_trade_stats(self, trades: List) -> None:
        """计算基础交易统计"""
        self.report.total_trades = len(trades)
        
        for trade in trades:
            if trade.is_closed:  # 只计算已平仓的交易
                if trade.profit and trade.profit > 0:
                    self.report.winning_trades += 1
                elif trade.profit and trade.profit < 0:
                    self.report.losing_trades += 1
        
        # 计算胜率
        if self.report.total_trades > 0:
            self.report.win_rate = (self.report.winning_trades / self.report.total_trades) * 100
    
    def _calculate_profit_metrics(self, trades: List) -> None:
        """计算收益相关指标"""
        total_profit = 0.0
        total_loss = 0.0
        
        for trade in trades:
            if trade.is_closed and trade.profit:
                if trade.profit > 0:
                    total_profit += trade.profit
                    self.report.total_profit += trade.profit
                else:
                    total_loss += abs(trade.profit)
                    self.report.total_loss += abs(trade.profit)
        
        # 净利润
        self.report.net_profit = self.report.total_profit - self.report.total_loss
        
        # 总收益率
        self.report.total_return = (self.report.net_profit / self.report.initial_capital) * 100
        
        # 盈亏比 (总盈利 / 总亏损)
        if self.report.total_loss > 0:
            self.report.profit_factor = self.report.total_profit / self.report.total_loss
        else:
            self.report.profit_factor = float('inf') if self.report.total_profit > 0 else 0
        
        # 平均盈利/亏损
        if self.report.winning_trades > 0:
            self.report.average_profit = self.report.total_profit / self.report.winning_trades
        if self.report.losing_trades > 0:
            self.report.average_loss = self.report.total_loss / self.report.losing_trades
        
        # 平均盈亏比
        if self.report.average_loss > 0:
            self.report.profit_loss_ratio = self.report.average_profit / self.report.average_loss
    
    def _calculate_risk_metrics(self, portfolio_values: List[float], initial_capital: float) -> None:
        """计算风险指标（最大回撤）"""
        if not portfolio_values:
            return
        
        # 寻找最大回撤
        # 方法：从所有历史最高点到当前点的最大下跌幅度
        cummax = np.maximum.accumulate(portfolio_values)  # 从左到右的最大值
        drawdowns = (np.array(portfolio_values) - cummax) / cummax  # 相对回撤
        
        # 找到最大回撤
        max_dd_idx = np.argmin(drawdowns)
        self.report.max_drawdown = abs(drawdowns[max_dd_idx]) * 100
        self.report.max_drawdown_amount = cummax[max_dd_idx] - portfolio_values[max_dd_idx]
    
    def _calculate_time_based_metrics(self, 
                                      portfolio_values: List[float], 
                                      portfolio_dates: List) -> None:
        """计算基于时间的指标（年化收益、波动率、夏普比）"""
        
        # 计算日收益率
        pv = np.array(portfolio_values)
        returns = np.diff(pv) / pv[:-1]  # 逐日收益率
        
        if len(returns) == 0:
            return
        
        # 年化参数（假设252个交易日）
        annual_factor = 252
        
        # 年化收益率
        total_days = len(portfolio_values)
        if total_days > 1:
            total_return = (portfolio_values[-1] / portfolio_values[0]) ** (annual_factor / total_days) - 1
            self.report.annual_return = total_return * 100
        
        # 年化波动率
        daily_volatility = np.std(returns)
        self.report.annual_volatility = daily_volatility * np.sqrt(annual_factor) * 100
        
        # 夏普比 (无风险利率假设为0)
        if self.report.annual_volatility > 0:
            self.report.sharpe_ratio = self.report.annual_return / self.report.annual_volatility
    
    def _calculate_consecutive_metrics(self, trades: List) -> None:
        """计算连续胜负统计"""
        if not trades:
            return
        
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in trades:
            if trade.is_closed and trade.profit:
                if trade.profit > 0:
                    current_wins += 1
                    current_losses = 0
                    max_wins = max(max_wins, current_wins)
                else:
                    current_losses += 1
                    current_wins = 0
                    max_losses = max(max_losses, current_losses)
        
        self.report.consecutive_wins = max_wins
        self.report.consecutive_losses = max_losses
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'total_trades': self.report.total_trades,
            'winning_trades': self.report.winning_trades,
            'losing_trades': self.report.losing_trades,
            'win_rate': round(self.report.win_rate, 2),
            'total_profit': round(self.report.total_profit, 2),
            'total_loss': round(self.report.total_loss, 2),
            'net_profit': round(self.report.net_profit, 2),
            'profit_factor': round(self.report.profit_factor, 2),
            'max_drawdown': round(self.report.max_drawdown, 2),
            'total_return': round(self.report.total_return, 2),
            'annual_return': round(self.report.annual_return, 2),
            'annual_volatility': round(self.report.annual_volatility, 2),
            'sharpe_ratio': round(self.report.sharpe_ratio, 2),
            'average_profit': round(self.report.average_profit, 2),
            'average_loss': round(self.report.average_loss, 2),
            'profit_loss_ratio': round(self.report.profit_loss_ratio, 2),
            'consecutive_wins': self.report.consecutive_wins,
            'consecutive_losses': self.report.consecutive_losses,
            'recovery_factor': round(self.report.recovery_factor, 2),
        }
