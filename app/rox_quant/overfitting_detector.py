"""
P3.5 Day 3: 过拟合检测器 - OverfittingDetector
作用：检测策略是否过度优化，只在特定数据集上表现好
关键概念：
  - 过拟合：在历史数据上表现完美，但在新数据上失效
  - Rolling Window: 用不同时间段的数据分别回测，看结果是否一致
  - Walk-forward: 用前段数据参数优化，用后段数据验证
  - 过拟合指数：0-100，越低越好（<30 表示策略稳定）
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Callable
import numpy as np
import pandas as pd


@dataclass
class WindowResult:
    """单个时间窗口的回测结果"""
    window_name: str           # 窗口名称 (如 "Q1 2024")
    start_idx: int             # 开始索引
    end_idx: int               # 结束索引
    total_trades: int = 0      # 交易数
    win_rate: float = 0.0      # 胜率
    profit_factor: float = 0.0 # 盈亏比
    net_profit: float = 0.0    # 净利润
    total_return: float = 0.0  # 总收益率 (%)
    max_drawdown: float = 0.0  # 最大回撤 (%)


@dataclass
class OverfittingReport:
    """过拟合检测报告"""
    total_window_tests: int = 0              # 总窗口数
    windows: List[WindowResult] = field(default_factory=list)
    
    # 统计指标
    win_rate_mean: float = 0.0               # 平均胜率
    win_rate_std: float = 0.0                # 胜率标准差
    win_rate_cv: float = 0.0                 # 胜率变异系数 (std/mean)
    
    profit_factor_mean: float = 0.0          # 平均盈亏比
    profit_factor_std: float = 0.0           # 盈亏比标准差
    profit_factor_cv: float = 0.0            # 盈亏比变异系数
    
    return_mean: float = 0.0                 # 平均收益率
    return_std: float = 0.0                  # 收益率标准差
    return_cv: float = 0.0                   # 收益率变异系数
    
    # 过拟合检测
    is_overfitted: bool = False              # 是否过拟合
    overfitting_score: float = 0.0           # 过拟合指数 (0-100, 越低越好)
    stability_index: float = 0.0             # 稳定性指数 (0-100, 越高越好)
    robustness_score: float = 0.0            # 鲁棒性评分 (0-100)
    
    def __str__(self) -> str:
        """格式化输出"""
        lines = [
            "\n" + "="*70,
            "⚠️  过拟合检测报告".center(70),
            "="*70,
            f"\n【时间窗口结果】共 {self.total_window_tests} 个窗口",
            "-"*70,
            f"{'窗口':<15} {'交易数':<8} {'胜率':<10} {'盈亏比':<10} {'收益率':<10}",
            "-"*70
        ]
        
        for w in self.windows:
            pf_str = f"{w.profit_factor:.2f}" if w.profit_factor != float('inf') else "∞"
            lines.append(
                f"{w.window_name:<15} {w.total_trades:<8} {w.win_rate:<9.1f}% "
                f"{pf_str:<10} {w.total_return:<9.2f}%"
            )
        
        lines.extend([
            "-"*70,
            f"\n【统计分析】（检测结果的一致性）",
            f"  胜率:      均值={self.win_rate_mean:.2f}%, 标准差={self.win_rate_std:.2f}%, 变异系数={self.win_rate_cv:.4f}",
            f"  盈亏比:    均值={self.profit_factor_mean:.2f}, 标准差={self.profit_factor_std:.2f}, 变异系数={self.profit_factor_cv:.4f}",
            f"  收益率:    均值={self.return_mean:.2f}%, 标准差={self.return_std:.2f}%, 变异系数={self.return_cv:.4f}",
            f"\n【过拟合评估】",
            f"  过拟合指数:  {self.overfitting_score:>6.1f}/100 ⚠️ (越低越好, <30 表示稳定)",
            f"  稳定性指数:  {self.stability_index:>6.1f}/100 ✓ (越高越好)",
            f"  鲁棒性评分:  {self.robustness_score:>6.1f}/100 ✓ (越高越好)",
            f"  过拟合判断:  {'⚠️ 策略已过拟合!' if self.is_overfitted else '✓ 策略相对稳健'}",
            "="*70 + "\n"
        ])
        
        return "\n".join(lines)


class OverfittingDetector:
    """
    过拟合检测器
    
    方法：
      1. Rolling Window: 固定窗口大小，滑动分析
      2. Walk-forward: 前段优化，后段验证
      3. 统计指标：计算参数一致性
    """
    
    def __init__(self):
        self.report = OverfittingReport()
    
    def rolling_window_test(self, 
                           klines: pd.DataFrame,
                           signal_func: Callable,
                           window_size: int = 50,
                           step: int = 10) -> OverfittingReport:
        """
        Rolling Window 测试
        
        方法：
          1. 将数据分成多个窗口（例如50根K线一个窗口）
          2. 在每个窗口内运行回测
          3. 比较不同窗口的结果，看是否一致
        
        Args:
            klines: K线数据
            signal_func: 信号函数 (klines_df, idx) -> 'BUY'/'SELL'/'HOLD'
            window_size: 窗口大小（K线数）
            step: 滑动步长（K线数）
        
        Returns:
            OverfittingReport: 检测报告
        """
        from backtest_engine import BacktestEngine, BacktestConfig
        from performance_metrics import PerformanceMetrics
        
        self.report = OverfittingReport()
        config = BacktestConfig()
        metrics = PerformanceMetrics()
        
        # 执行 rolling window 回测
        for start_idx in range(0, len(klines) - window_size, step):
            end_idx = min(start_idx + window_size, len(klines))
            window_klines = klines.iloc[start_idx:end_idx].reset_index(drop=True)
            
            # 在该窗口内运行回测
            engine = BacktestEngine(config)
            engine.load_klines(window_klines)
            engine.run(signal_func)
            
            # 计算性能指标
            trades = engine.get_trades()
            portfolio_values, portfolio_dates = engine.get_portfolio_values()
            perf_report = metrics.calculate(trades, portfolio_values, portfolio_dates, config.initial_capital)
            
            # 记录结果
            window_name = f"[{start_idx}-{end_idx}]"
            wr = WindowResult(
                window_name=window_name,
                start_idx=start_idx,
                end_idx=end_idx,
                total_trades=perf_report.total_trades,
                win_rate=perf_report.win_rate,
                profit_factor=perf_report.profit_factor,
                net_profit=perf_report.net_profit,
                total_return=perf_report.total_return,
                max_drawdown=perf_report.max_drawdown
            )
            self.report.windows.append(wr)
        
        self.report.total_window_tests = len(self.report.windows)
        
        # 计算统计指标
        self._calculate_statistics()
        
        return self.report
    
    def walk_forward_test(self,
                         klines: pd.DataFrame,
                         signal_func: Callable,
                         test_ratio: float = 0.3) -> OverfittingReport:
        """
        Walk-forward 测试
        
        方法：
          1. 将数据分为多个阶段
          2. 每个阶段：前70%用来参数优化，后30%用来验证
          3. 看优化参数在验证数据上是否仍然有效
        
        Args:
            klines: K线数据
            signal_func: 信号函数
            test_ratio: 测试集占比 (0.3 = 30%)
        
        Returns:
            OverfittingReport: 检测报告
        """
        from backtest_engine import BacktestEngine, BacktestConfig
        from performance_metrics import PerformanceMetrics
        
        self.report = OverfittingReport()
        config = BacktestConfig()
        metrics = PerformanceMetrics()
        
        # 分成4个阶段
        phase_size = len(klines) // 4
        
        for phase in range(4):
            phase_start = phase * phase_size
            phase_end = (phase + 1) * phase_size if phase < 3 else len(klines)
            
            # 分割为训练集和测试集
            train_size = int((phase_end - phase_start) * (1 - test_ratio))
            train_end = phase_start + train_size
            
            # 在训练集上运行回测（理想情况下这里会参数优化，但简化处理）
            train_klines = klines.iloc[phase_start:train_end].reset_index(drop=True)
            test_klines = klines.iloc[train_end:phase_end].reset_index(drop=True)
            
            # 在测试集上验证
            engine = BacktestEngine(config)
            engine.load_klines(test_klines)
            engine.run(signal_func)
            
            # 计算性能指标
            trades = engine.get_trades()
            portfolio_values, portfolio_dates = engine.get_portfolio_values()
            perf_report = metrics.calculate(trades, portfolio_values, portfolio_dates, config.initial_capital)
            
            # 记录结果
            window_name = f"Phase {phase+1}"
            wr = WindowResult(
                window_name=window_name,
                start_idx=train_end,
                end_idx=phase_end,
                total_trades=perf_report.total_trades,
                win_rate=perf_report.win_rate,
                profit_factor=perf_report.profit_factor,
                net_profit=perf_report.net_profit,
                total_return=perf_report.total_return,
                max_drawdown=perf_report.max_drawdown
            )
            self.report.windows.append(wr)
        
        self.report.total_window_tests = len(self.report.windows)
        self._calculate_statistics()
        
        return self.report
    
    def _calculate_statistics(self) -> None:
        """计算统计指标"""
        if not self.report.windows:
            return
        
        win_rates = [w.win_rate for w in self.report.windows]
        profit_factors = [w.profit_factor for w in self.report.windows if w.profit_factor != float('inf')]
        returns = [w.total_return for w in self.report.windows]
        
        # 胜率统计
        self.report.win_rate_mean = np.mean(win_rates)
        self.report.win_rate_std = np.std(win_rates)
        if self.report.win_rate_mean > 0:
            self.report.win_rate_cv = self.report.win_rate_std / self.report.win_rate_mean
        
        # 盈亏比统计
        if profit_factors:
            self.report.profit_factor_mean = np.mean(profit_factors)
            self.report.profit_factor_std = np.std(profit_factors)
            if self.report.profit_factor_mean > 0:
                self.report.profit_factor_cv = self.report.profit_factor_std / self.report.profit_factor_mean
        
        # 收益率统计
        self.report.return_mean = np.mean(returns)
        self.report.return_std = np.std(returns)
        if abs(self.report.return_mean) > 0.01:
            self.report.return_cv = abs(self.report.return_std / self.report.return_mean)
        
        # 计算过拟合指数
        # 指数越高表示越不稳定（过拟合）
        # 综合考虑三个指标的变异系数
        self.report.overfitting_score = (
            self.report.win_rate_cv * 30 +
            self.report.profit_factor_cv * 40 +
            self.report.return_cv * 30
        ) * 100
        self.report.overfitting_score = min(100, self.report.overfitting_score)
        
        # 稳定性指数 = 100 - 过拟合指数
        self.report.stability_index = 100 - self.report.overfitting_score
        
        # 鲁棒性评分：看是否所有窗口都盈利
        profitable_windows = sum(1 for w in self.report.windows if w.net_profit > 0)
        self.report.robustness_score = (profitable_windows / len(self.report.windows)) * 100
        
        # 过拟合判断：如果过拟合指数 > 50，认为过拟合
        self.report.is_overfitted = self.report.overfitting_score > 50
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'total_window_tests': self.report.total_window_tests,
            'windows': [
                {
                    'window_name': w.window_name,
                    'total_trades': w.total_trades,
                    'win_rate': round(w.win_rate, 2),
                    'profit_factor': round(w.profit_factor, 2),
                    'net_profit': round(w.net_profit, 2),
                    'total_return': round(w.total_return, 2),
                    'max_drawdown': round(w.max_drawdown, 2)
                }
                for w in self.report.windows
            ],
            'win_rate_mean': round(self.report.win_rate_mean, 2),
            'win_rate_std': round(self.report.win_rate_std, 2),
            'profit_factor_mean': round(self.report.profit_factor_mean, 2),
            'profit_factor_std': round(self.report.profit_factor_std, 2),
            'return_mean': round(self.report.return_mean, 2),
            'return_std': round(self.report.return_std, 2),
            'overfitting_score': round(self.report.overfitting_score, 1),
            'stability_index': round(self.report.stability_index, 1),
            'robustness_score': round(self.report.robustness_score, 1),
            'is_overfitted': self.report.is_overfitted
        }
