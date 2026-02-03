"""
P3.5 Day 2: 因子分析器 - FactorAnalyzer
作用：分析每个信号/因子对最终盈利的贡献度，找出哪些信号真正有效
关键概念：
  - 因子：MACD、MA、RSI、KDJ等单个技术指标
  - 贡献度：如果移除这个信号，盈利会减少多少（百分比）
  - 有效性评分：0-100，越高表示这个信号越有用
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import numpy as np
import pandas as pd


@dataclass
class FactorContribution:
    """单个因子的贡献度"""
    factor_name: str                 # 因子名称
    total_signals: int = 0           # 该因子生成的信号总数
    winning_signals: int = 0         # 导致盈利的信号数
    losing_signals: int = 0          # 导致亏损的信号数
    win_rate: float = 0.0            # 胜率（%）
    avg_profit: float = 0.0          # 平均盈利
    avg_loss: float = 0.0            # 平均亏损
    profit_factor: float = 0.0       # 盈亏比
    total_contribution: float = 0.0  # 总贡献度（元）
    contribution_pct: float = 0.0    # 相对贡献度（%）
    effectiveness_score: float = 0.0 # 有效性评分 (0-100)


class FactorAnalyzer:
    """
    因子分析器
    
    作用：
      1. 追踪每个交易是由哪个信号触发的
      2. 计算各个因子的胜率和收益贡献
      3. 生成因子贡献度排名
    """
    
    def __init__(self):
        self.factor_trades: Dict[str, List] = {}  # {因子名: [交易记录]}
        self.factor_contributions: Dict[str, FactorContribution] = {}
    
    def register_factor(self, factor_name: str) -> None:
        """注册一个新的因子"""
        self.factor_trades[factor_name] = []
        self.factor_contributions[factor_name] = FactorContribution(
            factor_name=factor_name
        )
    
    def record_trade_factor(self, factor_name: str, trade) -> None:
        """
        记录一笔交易是由哪个因子产生的
        
        Args:
            factor_name: 因子名称
            trade: TradeRecord 对象
        """
        if factor_name not in self.factor_trades:
            self.register_factor(factor_name)
        
        self.factor_trades[factor_name].append(trade)
    
    def analyze(self) -> Dict[str, FactorContribution]:
        """
        分析所有因子的贡献度
        
        Returns:
            {因子名: FactorContribution}
        """
        total_profit = 0.0
        
        # 第一遍：计算总利润
        for trades in self.factor_trades.values():
            for trade in trades:
                if trade.is_closed and trade.profit:
                    total_profit += trade.profit
        
        if total_profit == 0:
            total_profit = 1  # 避免除以零
        
        # 第二遍：分析每个因子
        for factor_name, trades in self.factor_trades.items():
            fc = self.factor_contributions[factor_name]
            fc.total_signals = len(trades)
            
            factor_profit = 0.0
            factor_loss = 0.0
            
            for trade in trades:
                if trade.is_closed and trade.profit:
                    if trade.profit > 0:
                        fc.winning_signals += 1
                        factor_profit += trade.profit
                    else:
                        fc.losing_signals += 1
                        factor_loss += abs(trade.profit)
            
            # 计算指标
            if fc.total_signals > 0:
                fc.win_rate = (fc.winning_signals / fc.total_signals) * 100
            
            if fc.winning_signals > 0:
                fc.avg_profit = factor_profit / fc.winning_signals
            
            if fc.losing_signals > 0:
                fc.avg_loss = factor_loss / fc.losing_signals
            
            if factor_loss > 0:
                fc.profit_factor = factor_profit / factor_loss
            elif factor_profit > 0:
                fc.profit_factor = float('inf')
            else:
                fc.profit_factor = 0
            
            # 总贡献度 = 该因子所有交易的净利润
            fc.total_contribution = factor_profit - factor_loss
            
            # 相对贡献度 = 该因子贡献 / 总利润 * 100%
            fc.contribution_pct = (fc.total_contribution / total_profit) * 100
            
            # 有效性评分 (0-100)
            # 综合考虑：胜率(40%), 盈亏比(40%), 信号数(20%)
            score = 0.0
            if fc.total_signals > 0:
                # 胜率分：最高100分
                wr_score = min(fc.win_rate, 100)
                
                # 盈亏比分：最高100分（当盈亏比为2时得100分）
                pf_score = min(fc.profit_factor * 50, 100)
                
                # 信号数分：交易越多越可信（最多10笔算满分100）
                signal_score = min((fc.total_signals / 10) * 100, 100)
                
                score = wr_score * 0.4 + pf_score * 0.4 + signal_score * 0.2
            
            fc.effectiveness_score = max(0, min(score, 100))
        
        return self.factor_contributions
    
    def get_ranking(self, sort_by: str = 'contribution_pct') -> List[FactorContribution]:
        """
        获取因子贡献度排名
        
        Args:
            sort_by: 排序方式
              - 'contribution_pct': 按相对贡献度排序（默认）
              - 'effectiveness_score': 按有效性评分排序
              - 'win_rate': 按胜率排序
              - 'profit_factor': 按盈亏比排序
        
        Returns:
            排序后的 FactorContribution 列表
        """
        factors = list(self.factor_contributions.values())
        
        if sort_by == 'effectiveness_score':
            factors.sort(key=lambda x: x.effectiveness_score, reverse=True)
        elif sort_by == 'win_rate':
            factors.sort(key=lambda x: x.win_rate, reverse=True)
        elif sort_by == 'profit_factor':
            factors.sort(key=lambda x: x.profit_factor, reverse=True)
        else:  # contribution_pct
            factors.sort(key=lambda x: x.contribution_pct, reverse=True)
        
        return factors
    
    def print_report(self) -> str:
        """生成文本格式的因子分析报告"""
        self.analyze()
        
        ranking = self.get_ranking('contribution_pct')
        
        lines = [
            "\n" + "="*80,
            "📊 因子分析报告 - 找出哪些信号真正有效".center(80),
            "="*80,
            f"\n【因子贡献度排名】(按对总利润的贡献从大到小)",
            "-"*80,
            f"{'排名':<5} {'因子名':<15} {'交易数':<8} {'胜率':<8} {'盈亏比':<10} {'贡献度':<12} {'评分':<8}",
            "-"*80
        ]
        
        for rank, fc in enumerate(ranking, 1):
            pf_str = f"{fc.profit_factor:.2f}" if fc.profit_factor != float('inf') else "∞"
            lines.append(
                f"{rank:<5} {fc.factor_name:<15} {fc.total_signals:<8} "
                f"{fc.win_rate:<7.1f}% {pf_str:<10} "
                f"{fc.contribution_pct:>10.2f}% {fc.effectiveness_score:>7.1f}"
            )
        
        lines.extend([
            "-"*80,
            f"\n【有效性评分TOP 3】(综合考虑胜率、盈亏比、交易数)",
            "-"*80
        ])
        
        top_3 = self.get_ranking('effectiveness_score')[:3]
        for i, fc in enumerate(top_3, 1):
            lines.append(
                f"{i}. {fc.factor_name:<15} "
                f"评分: {fc.effectiveness_score:>6.1f}/100  "
                f"胜率: {fc.win_rate:>6.1f}%  "
                f"交易数: {fc.total_signals}"
            )
        
        lines.extend([
            "\n【因子详细数据】",
            "-"*80
        ])
        
        for fc in ranking:
            lines.append(f"\n{fc.factor_name}:")
            lines.append(f"  交易笔数:      {fc.total_signals} 笔")
            lines.append(f"  盈利交易:      {fc.winning_signals} 笔")
            lines.append(f"  亏损交易:      {fc.losing_signals} 笔")
            lines.append(f"  胜率:          {fc.win_rate:.2f}%")
            lines.append(f"  平均盈利:      {fc.avg_profit:,.2f} 元")
            lines.append(f"  平均亏损:      {fc.avg_loss:,.2f} 元")
            lines.append(f"  盈亏比:        {fc.profit_factor:.2f}")
            lines.append(f"  总贡献度:      {fc.total_contribution:,.2f} 元")
            lines.append(f"  相对贡献:      {fc.contribution_pct:.2f}%")
            lines.append(f"  有效性评分:    {fc.effectiveness_score:.1f}/100")
        
        lines.append("\n" + "="*80 + "\n")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        self.analyze()
        
        result = {
            'factors': {},
            'ranking': []
        }
        
        for fc in self.factor_contributions.values():
            result['factors'][fc.factor_name] = {
                'total_signals': fc.total_signals,
                'winning_signals': fc.winning_signals,
                'losing_signals': fc.losing_signals,
                'win_rate': round(fc.win_rate, 2),
                'avg_profit': round(fc.avg_profit, 2),
                'avg_loss': round(fc.avg_loss, 2),
                'profit_factor': round(fc.profit_factor, 2),
                'total_contribution': round(fc.total_contribution, 2),
                'contribution_pct': round(fc.contribution_pct, 2),
                'effectiveness_score': round(fc.effectiveness_score, 1)
            }
        
        for fc in self.get_ranking('contribution_pct'):
            result['ranking'].append({
                'factor_name': fc.factor_name,
                'contribution_pct': round(fc.contribution_pct, 2),
                'effectiveness_score': round(fc.effectiveness_score, 1),
                'win_rate': round(fc.win_rate, 2)
            })
        
        return result
