"""
专业风险管理框架 - 基于《量化交易从入门到精通》
包含止损、止盈、时间止盈、仓位管理、回撤约束等
"""

import logging
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RiskParams:
    """风险管理参数"""
    max_drawdown: float = 0.10  # 最大回撤（10%）
    single_trade_risk: float = 0.03  # 单笔交易风险（3%）
    position_size_pct: float = 0.05  # 仓位大小（每次买入占总资金比例）
    
    # 止损参数
    stop_loss_atr_multiplier: float = 2.0  # 止损幅度（ATR倍数，通常2-5）
    stop_loss_fixed_pct: float = 0.01  # 固定百分比止损（1%）
    
    # 止盈参数
    take_profit_atr_multiplier: float = 3.0  # 止盈幅度（ATR倍数）
    take_profit_fixed_pct: float = 0.0075  # 固定百分比止盈（0.75%）
    
    # 时间止盈
    time_stop_bars: int = 30  # 持仓超过N个bar且收益接近0时平仓
    time_stop_profit_threshold: float = 0.0002  # 0.02% 收益阈值
    
    # 策略组合参数
    max_concurrent_positions: int = 5  # 最多并发持仓数
    correlated_asset_max_exposure: float = 0.20  # 相关资产的最大敞口（20%）
    
    # 杠杆参数
    leverage: float = 1.0  # 杠杆倍数（1.0=无杠杆）
    acceptable_loss_pct: float = 0.10  # 可接受的最大损失占保证金比例


class RiskManager:
    """
    专业风险管理器
    
    核心职责：
    1. 止损/止盈管理
    2. 仓位管理
    3. 回撤控制
    4. 杠杆管理
    """
    
    def __init__(self, risk_params: Optional[RiskParams] = None):
        self.params = risk_params or RiskParams()
        self.open_positions = {}
        self.cumulative_drawdown = 0.0
        self.peak_equity = 1000000.0  # 初始资本
        
        logger.info(f"✓ 风险管理器初始化，最大回撤={self.params.max_drawdown:.2%}")
    
    # ============ 止损/止盈管理 ============
    
    def calculate_stops(self, 
                       entry_price: float,
                       atr: float,
                       direction: str = 'long',
                       method: str = 'atr') -> Dict[str, float]:
        """
        计算止损和止盈价位
        
        Args:
            entry_price: 进场价格
            atr: 平均真实波幅
            direction: 'long' 或 'short'
            method: 'atr'（ATR倍数）或 'fixed'（固定百分比）
        
        Returns:
            {'stop_loss': 止损价, 'take_profit': 止盈价}
        """
        if method == 'atr':
            # 从 params 中获取止损止盈参数
            # 优先使用 ExitParameters（如果有），否则使用 RiskParameters
            if hasattr(self.params, 'stop_loss_atr_multiplier'):
                sl_multiplier = self.params.stop_loss_atr_multiplier
            else:
                sl_multiplier = 2.0  # 默认值
            
            if hasattr(self.params, 'take_profit_atr_multiplier'):
                tp_multiplier = self.params.take_profit_atr_multiplier
            else:
                tp_multiplier = 3.0  # 默认值
            
            sl_distance = atr * sl_multiplier
            tp_distance = atr * tp_multiplier
        else:  # fixed
            if hasattr(self.params, 'stop_loss_fixed_pct'):
                sl_pct = self.params.stop_loss_fixed_pct
            else:
                sl_pct = 0.01
            
            if hasattr(self.params, 'take_profit_fixed_pct'):
                tp_pct = self.params.take_profit_fixed_pct
            else:
                tp_pct = 0.0075
            
            sl_distance = entry_price * sl_pct
            tp_distance = entry_price * tp_pct
        
        if direction == 'long':
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + tp_distance
        else:  # short
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - tp_distance
        
        return {
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'sl_distance': sl_distance,
            'tp_distance': tp_distance
        }
    
    def should_stop_loss(self,
                        current_price: float,
                        stop_loss: float,
                        direction: str = 'long') -> bool:
        """判断是否触发止损"""
        if direction == 'long':
            return current_price <= stop_loss
        else:
            return current_price >= stop_loss
    
    def should_take_profit(self,
                          current_price: float,
                          take_profit: float,
                          direction: str = 'long') -> bool:
        """判断是否触发止盈"""
        if direction == 'long':
            return current_price >= take_profit
        else:
            return current_price <= take_profit
    
    def should_time_stop(self,
                        bars_held: int,
                        unrealized_pnl_pct: float) -> bool:
        """
        时间止盈：持仓超过N个bar且收益接近0时平仓
        
        Args:
            bars_held: 持仓的bar数
            unrealized_pnl_pct: 未实现盈利率
        
        Returns:
            是否应该执行时间止盈
        """
        return (bars_held >= self.params.time_stop_bars and 
                abs(unrealized_pnl_pct) <= self.params.time_stop_profit_threshold)
    
    # ============ 仓位管理 ============
    
    def calculate_position_size(self,
                               account_balance: float,
                               entry_price: float,
                               stop_loss: float,
                               method: str = 'kelly') -> float:
        """
        计算仓位大小
        
        Args:
            account_balance: 账户余额
            entry_price: 进场价格
            stop_loss: 止损价格
            method: 'kelly'（Kelly公式）或 'fixed'（固定比例）
        
        Returns:
            仓位大小（以账户余额的百分比表示）
        """
        if method == 'fixed':
            # 固定百分比仓位管理
            return self.params.position_size_pct
        
        elif method == 'kelly':
            # Kelly公式：f = (b*p - q) / b
            # 其中 p=胜率, q=败率, b=平均盈亏比
            # 这里使用保守版本
            win_rate = 0.55  # 假设历史胜率
            profit_factor = 1.5  # 平均盈亏比
            
            per_trade_risk = (entry_price - stop_loss) / entry_price
            position_size = (win_rate - (1 - win_rate) / profit_factor) / 2  # 保守系数 /2
            
            # 限制在 1-5% 范围内
            position_size = max(0.01, min(position_size, 0.05))
            
            return position_size
        
        else:
            return self.params.position_size_pct
    
    def calculate_optimal_lot_size(self,
                                  account_balance: float,
                                  entry_price: float,
                                  stop_loss: float,
                                  risk_per_trade: Optional[float] = None) -> Dict[str, float]:
        """
        计算最优手数（量化公式）
        
        理论仓位公式：
        开单仓位 ≈ [胜率 - (1-胜率)/平均盈亏比] / 2
        
        实战中：从此公式结果的 50-70% 起步
        
        Args:
            account_balance: 账户总资金
            entry_price: 进场价格
            stop_loss: 止损价格
            risk_per_trade: 单笔最大风险金额（可选）
        
        Returns:
            {
                'theoretical_position_pct': 理论仓位比例,
                'practical_position_pct': 实战建议仓位(50-70%),
                'num_lots': 建议手数,
                'risk_amount': 该仓位的最大风险金额
            }
        """
        # 假设历史数据
        win_rate = 0.55
        avg_profit_factor = 1.5
        
        # 理论公式
        theoretical = (win_rate - (1 - win_rate) / avg_profit_factor) / 2
        theoretical = max(0, min(theoretical, 0.10))  # 限制在0-10%
        
        # 实战建议：50-70%
        practical = theoretical * 0.60  # 60% 作为折中
        
        # 计算最大风险
        loss_per_unit = entry_price - stop_loss
        max_risk = account_balance * practical / loss_per_unit if loss_per_unit > 0 else 0
        
        risk_amount = risk_per_trade or (account_balance * practical)
        
        return {
            'theoretical_position_pct': theoretical,
            'practical_position_pct': practical,
            'num_lots': int(max_risk),
            'risk_amount': risk_amount
        }
    
    # ============ 回撤管理 ============
    
    def check_drawdown_limit(self, current_equity: float) -> Tuple[bool, float]:
        """
        检查是否超过最大回撤限制
        
        Returns:
            (是否超限, 当前回撤比例)
        """
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
            current_drawdown = 0.0
        else:
            current_drawdown = (self.peak_equity - current_equity) / self.peak_equity
        
        exceeded = current_drawdown > self.params.max_drawdown
        
        if exceeded:
            logger.warning(
                f"⚠️  超过最大回撤限制！"
                f"当前回撤={current_drawdown:.2%}, "
                f"限制={self.params.max_drawdown:.2%}"
            )
        
        return exceeded, current_drawdown
    
    def get_exposure_limit(self, current_equity: float) -> float:
        """
        根据当前回撤动态调整敞口限额
        
        回撤越大→敞口越小（风险规避）
        """
        _, drawdown = self.check_drawdown_limit(current_equity)
        
        # 线性衰减：0%回撤→100%敞口，10%回撤→0%敞口
        exposure_limit = max(0.0, 1.0 - drawdown / self.params.max_drawdown)
        
        return exposure_limit
    
    # ============ 策略组合管理 ============
    
    def can_open_position(self, 
                         current_positions: int,
                         current_equity: float) -> bool:
        """
        检查是否可以开仓
        
        Returns:
            True 如果满足开仓条件
        """
        # 检查并发持仓数
        if current_positions >= self.params.max_concurrent_positions:
            logger.warning(
                f"达到最大并发持仓数 ({self.params.max_concurrent_positions})"
            )
            return False
        
        # 检查回撤限制
        exceeded, _ = self.check_drawdown_limit(current_equity)
        if exceeded:
            logger.warning("超过最大回撤限制，停止开仓")
            return False
        
        return True
    
    def check_correlated_exposure(self,
                                 positions: Dict[str, float],
                                 correlation_matrix: pd.DataFrame) -> Dict[str, float]:
        """
        检查相关资产的敞口
        
        Args:
            positions: 持仓字典 {品种: 占比}
            correlation_matrix: 相关系数矩阵
        
        Returns:
            超限的相关资产及其总敞口
        """
        over_exposure = {}
        
        for symbol, exposure in positions.items():
            if symbol not in correlation_matrix.columns:
                continue
            
            # 找所有高相关的资产（>0.7）
            correlated = correlation_matrix[symbol][
                (correlation_matrix[symbol] > 0.7) & 
                (correlation_matrix[symbol] != 1.0)
            ]
            
            total_correlated_exposure = sum(
                positions.get(sym, 0) for sym in correlated.index
            )
            
            if total_correlated_exposure > self.params.correlated_asset_max_exposure:
                over_exposure[symbol] = total_correlated_exposure
        
        return over_exposure
    
    # ============ 杠杆管理 ============
    
    def calculate_margin_requirement(self,
                                    position_size: float,
                                    contract_price: float,
                                    margin_ratio: float = 0.1) -> float:
        """
        计算保证金需求
        
        Args:
            position_size: 持仓数量
            contract_price: 合约价格
            margin_ratio: 保证金比例（默认10%）
        
        Returns:
            所需保证金
        """
        return position_size * contract_price * margin_ratio
    
    def is_leverage_safe(self,
                        account_balance: float,
                        total_margin_used: float) -> bool:
        """
        检查杠杆是否安全
        
        判断标准：保证金使用 ≤ 账户的 80%
        """
        margin_ratio = total_margin_used / account_balance if account_balance > 0 else 0
        
        is_safe = margin_ratio <= 0.8
        
        if not is_safe:
            logger.warning(
                f"⚠️  杠杆过高！保证金占比={margin_ratio:.2%}，建议≤80%"
            )
        
        return is_safe


class AdvancedRiskMetrics:
    """高级风险指标计算"""
    
    @staticmethod
    def calculate_var(returns: pd.Series, confidence_level: float = 0.95) -> float:
        """
        计算 Value at Risk (VaR)
        
        Args:
            returns: 收益率序列
            confidence_level: 置信度（默认95%）
        
        Returns:
            VaR 值（表示在该置信度下的最大可能损失）
        """
        return returns.quantile(1 - confidence_level)
    
    @staticmethod
    def calculate_cvar(returns: pd.Series, confidence_level: float = 0.95) -> float:
        """
        计算 Conditional Value at Risk (CVaR，也叫 Expected Shortfall）
        
        在VaR的基础上，计算超过VaR的平均损失
        """
        var = AdvancedRiskMetrics.calculate_var(returns, confidence_level)
        cvar = returns[returns <= var].mean()
        
        return cvar
    
    @staticmethod
    def calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """
        Sortino 比率：只考虑下跌风险的调整收益
        
        相比夏普比率，Sortino 只将负收益波动当作风险，对有利的波动不惩罚
        """
        excess_returns = returns - risk_free_rate / 252  # 日化无风险收益
        downside_returns = excess_returns[excess_returns < 0]
        downside_std = downside_returns.std()
        
        return excess_returns.mean() / downside_std if downside_std > 0 else 0
    
    @staticmethod
    def calculate_calmar_ratio(returns: pd.Series, initial_value: float = 1.0) -> float:
        """
        Calmar 比率 = 年化收益 / 最大回撤
        
        值越高越好（年化收益相对回撤越大）
        """
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown_series = (cumulative - running_max) / running_max
        max_drawdown = drawdown_series.min()
        
        annual_return = returns.mean() * 252
        
        return annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
    
    @staticmethod
    def calculate_ulcer_index(returns: pd.Series, lookback: int = 14) -> float:
        """
        溃疡指数：对持续低迷时期的处罚
        
        相比简单的最大回撤，更关注回撤的深度和持续性
        """
        cumulative = (1 + returns).cumprod()
        rolling_max = cumulative.rolling(window=lookback).max()
        drawdown = (cumulative - rolling_max) / rolling_max * 100
        
        ulcer_index = np.sqrt((drawdown ** 2).mean())
        
        return ulcer_index
    
    @staticmethod
    def calculate_monthly_returns(returns: pd.Series) -> pd.Series:
        """计算月收益率"""
        return (1 + returns).resample('M').prod() - 1
    
    @staticmethod
    def calculate_best_worst_month(returns: pd.Series) -> Dict[str, float]:
        """计算最好和最坏的月份收益"""
        monthly = AdvancedRiskMetrics.calculate_monthly_returns(returns)
        
        return {
            'best_month': monthly.max(),
            'worst_month': monthly.min(),
            'avg_month': monthly.mean(),
            'month_std': monthly.std()
        }
