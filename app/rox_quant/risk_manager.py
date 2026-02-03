"""
风险管理模块
根据讲座 coolfairy 的理念实现：基于波动率的仓位管理、"三之道"实现
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    """风险指标"""
    atr: float = 0.0  # Average True Range (真实波幅)
    volatility: float = 0.0  # 波动率
    value_at_risk: float = 0.0  # 风险价值 (95%置信度)
    expected_shortfall: float = 0.0  # 期望缺口 (ES)
    
    def __repr__(self) -> str:
        return (f"RiskMetrics(ATR={self.atr:.4f}, Vol={self.volatility:.4f}, "
                f"VaR={self.value_at_risk:.4f}, ES={self.expected_shortfall:.4f})")


class RiskManager:
    """
    风险管理器
    
    讲座理念应用：
    1. "三之道" - 能涨多少、能跌多少、周期是多长
    2. 基于波动率的仓位管理 - 波动大的品种少仓位，波动小的多仓位
    3. 按年不亏本、按月极少回撤 - 风险控制目标
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        初始化风险管理器
        
        Args:
            risk_free_rate: 无风险利率（年化）
        """
        self.risk_free_rate = risk_free_rate
        logger.info(f"初始化风险管理器，无风险利率={risk_free_rate:.2%}")
    
    # ============ 三之道实现 ============
    
    def calculate_three_dimensions(self, price_history: pd.Series, 
                                  period: int = 20) -> Dict[str, float]:
        """
        计算"三之道"：能涨多少、能跌多少、多长时间达到
        
        Args:
            price_history: 历史价格序列
            period: 回看周期（天）
        
        Returns:
            {
                "upside_potential": 上涨潜力 (%)
                "downside_risk": 下跌风险 (%)
                "expected_timeframe": 预期周期 (天)
            }
        """
        if len(price_history) < period:
            logger.warning(f"数据不足，需要至少{period}天的数据")
            return {
                "upside_potential": 0.0,
                "downside_risk": 0.0,
                "expected_timeframe": 0,
            }
        
        recent_prices = price_history.tail(period)
        
        # 能涨多少：最高价相对当前价的涨幅
        current_price = recent_prices.iloc[-1]
        max_price = recent_prices.max()
        upside_potential = (max_price - current_price) / current_price
        
        # 能跌多少：最低价相对当前价的跌幅
        min_price = recent_prices.min()
        downside_risk = (current_price - min_price) / current_price
        
        # 多长时间达到：以交易日计算
        max_idx = recent_prices.idxmax()
        min_idx = recent_prices.idxmin()
        
        if isinstance(max_idx, pd.Timestamp) and isinstance(min_idx, pd.Timestamp):
            timeframe = max(
                abs((max_idx - recent_prices.index[0]).days),
                abs((min_idx - recent_prices.index[0]).days)
            )
        else:
            timeframe = max(
                abs(recent_prices.index.get_loc(max_idx)),
                abs(recent_prices.index.get_loc(min_idx))
            )
        
        result = {
            "upside_potential": float(upside_potential),
            "downside_risk": float(downside_risk),
            "expected_timeframe": int(timeframe),
        }
        
        logger.debug(f"三之道: {result}")
        return result
    
    # ============ 波动率计算 ============
    
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                     period: int = 14) -> float:
        """
        计算平均真实波幅 (ATR)
        
        用于衡量价格波动性，是仓位管理的关键指标
        """
        # 计算真实波幅
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # 计算平均
        atr = tr.rolling(window=period).mean().iloc[-1]
        return float(atr)
    
    def calculate_volatility(self, returns: pd.Series, period: int = 20) -> float:
        """
        计算波动率 (std of returns)
        
        Args:
            returns: 收益率序列
            period: 计算周期
        
        Returns:
            年化波动率
        """
        if len(returns) < period:
            return 0.0
        
        volatility = returns.rolling(window=period).std().iloc[-1] * np.sqrt(252)
        return float(volatility)
    
    def calculate_risk_metrics(self, price_data: pd.DataFrame) -> RiskMetrics:
        """
        计算完整的风险指标
        
        Args:
            price_data: OHLC数据框
                columns: ['open', 'high', 'low', 'close']
        """
        metrics = RiskMetrics()
        
        if price_data.empty:
            return metrics
        
        # 计算ATR
        if 'high' in price_data.columns and 'low' in price_data.columns and 'close' in price_data.columns:
            metrics.atr = self.calculate_atr(
                price_data['high'], 
                price_data['low'], 
                price_data['close']
            )
        
        # 计算波动率
        if 'close' in price_data.columns:
            returns = price_data['close'].pct_change()
            metrics.volatility = self.calculate_volatility(returns)
        
        # 计算VaR (95% 置信度)
        if 'close' in price_data.columns:
            returns = price_data['close'].pct_change().dropna()
            if len(returns) > 0:
                metrics.value_at_risk = float(returns.quantile(0.05))  # 负数
        
        # 计算期望缺口
        if 'close' in price_data.columns:
            returns = price_data['close'].pct_change().dropna()
            if len(returns) > 0:
                var_threshold = returns.quantile(0.05)
                metrics.expected_shortfall = float(returns[returns <= var_threshold].mean())
        
        return metrics
    
    # ============ 仓位管理 ============
    
    def calculate_position_size_by_volatility(self, 
                                             account_value: float,
                                             max_risk_per_trade: float,
                                             atr: float,
                                             entry_price: float) -> float:
        """
        基于波动率计算仓位大小
        讲座理念: "敢握硬的低风险投资才是好投资"
        
        仓位 = 账户价值 * 风险率 / (ATR * 入场价)
        
        Args:
            account_value: 账户价值
            max_risk_per_trade: 每笔交易最大风险 (0.01 = 1%)
            atr: 平均真实波幅
            entry_price: 入场价格
        
        Returns:
            推荐仓位手数
        """
        if atr == 0 or entry_price == 0:
            logger.warning("ATR 或 入场价为0，无法计算仓位")
            return 0
        
        # 风险金额
        risk_amount = account_value * max_risk_per_trade
        
        # 仓位 = 风险金额 / (ATR * 乘数)
        # 假设1手对应100股
        position_size = risk_amount / (atr * entry_price * 100)
        
        return float(position_size)
    
    def calculate_position_size_by_kelly(self, 
                                        win_rate: float,
                                        profit_loss_ratio: float,
                                        max_leverage: float = 0.25) -> float:
        """
        凯利公式计算仓位
        Kelly Formula: f = (p * b - q) / b
        其中 p=胜率, q=负率, b=盈亏比
        
        讲座理念: 正期望交易才能上仓位
        
        Args:
            win_rate: 胜率 (0-1)
            profit_loss_ratio: 盈亏比
            max_leverage: 最大杠杆倍数（安全考虑）
        
        Returns:
            建议的资金使用比例
        """
        loss_rate = 1.0 - win_rate
        
        # Kelly 公式
        b = profit_loss_ratio
        kelly_fraction = (win_rate * b - loss_rate) / b
        
        # 限制最大杠杆
        if kelly_fraction > max_leverage:
            kelly_fraction = max_leverage
            logger.warning(f"Kelly仓位 {kelly_fraction:.2%} 超过最大杠杆限制，已调整为 {max_leverage:.2%}")
        elif kelly_fraction < 0:
            kelly_fraction = 0
            logger.warning("负期望策略，建议不交易")
        
        return float(kelly_fraction)
    
    # ============ 风险警告 ============
    
    def check_yearly_loss(self, returns: List[float], target_min_return: float = 0.0) -> bool:
        """
        检查年度收益是否为负 (讲座理念: 按年不要亏本)
        """
        yearly_return = (1 + np.prod(returns)) - 1 if returns else 0
        is_ok = yearly_return >= target_min_return
        
        if not is_ok:
            logger.warning(f"年度收益 {yearly_return:.2%} 低于目标 {target_min_return:.2%}")
        
        return is_ok
    
    def check_monthly_drawdown(self, returns: List[float], 
                              max_acceptable_drawdown: float = 0.02) -> bool:
        """
        检查月度回撤是否过大 (讲座理念: 按月要极少回撤)
        """
        if not returns:
            return True
        
        cum_returns = np.cumprod(1 + np.array(returns))
        running_max = np.maximum.accumulate(cum_returns)
        drawdown = (cum_returns - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        is_ok = max_drawdown >= -max_acceptable_drawdown
        
        if not is_ok:
            logger.warning(f"月度最大回撤 {max_drawdown:.2%} 超过限制 {-max_acceptable_drawdown:.2%}")
        
        return is_ok
    
    def get_risk_alert(self, metrics: RiskMetrics, 
                      position_size: float,
                      account_value: float) -> Dict[str, str]:
        """
        生成风险警告
        """
        alerts = {}
        
        # 高波动性预警
        if metrics.volatility > 0.3:
            alerts["high_volatility"] = f"波动率 {metrics.volatility:.2%} 较高，建议降低仓位"
        
        # 高风险预警
        if metrics.value_at_risk < -0.05:
            alerts["high_var"] = f"VaR (95%) {metrics.value_at_risk:.2%}，风险较大"
        
        # 过度杠杆预警
        if position_size * account_value > account_value * 2:
            alerts["over_leverage"] = f"杠杆过高 {position_size:.2f}x，风险过大"
        
        return alerts
    
    def generate_risk_report(self, metrics: RiskMetrics, 
                            position_size: float,
                            account_value: float) -> str:
        """
        生成风险报告
        """
        alerts = self.get_risk_alert(metrics, position_size, account_value)
        
        report = f"""
╔════════════════════════════════════════╗
║        风险管理报告 (Rox Quant)         ║
╚════════════════════════════════════════╝

【风险指标】
- 平均真实波幅 (ATR): {metrics.atr:.4f}
- 波动率 (年化): {metrics.volatility:.2%}
- 风险价值 (VaR 95%): {metrics.value_at_risk:.2%}
- 期望缺口 (ES): {metrics.expected_shortfall:.2%}

【仓位信息】
- 建议仓位: {position_size:.2f}
- 账户价值: ¥{account_value:.2f}
- 风险敞口: ¥{position_size * account_value:.2f}

【风险警告】
{chr(10).join(f"⚠️  {k}: {v}" for k, v in alerts.items()) if alerts else "✓ 无风险警告"}

【建议】
- 按年不要亏本（设定年度目标收益率 ≥ 0%）
- 按月极少回撤（月度回撤限制 ≤ 2%）
- 敢握硬的低风险投资策略
        """
        
        return report
