"""
多策略投资组合管理模块
根据讲座 coolfairy 的理念实现：多策略、正期望、低相关、再平衡
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class Strategy:
    """策略定义"""
    name: str  # 策略名称
    symbol: str  # 交易品种 (e.g., "600000", "IF2403", "510050")
    description: str = ""  # 策略描述
    
    # 期望收益率
    expected_return: float = 0.0  # 年化期望收益率
    expected_win_rate: float = 0.5  # 胜率
    expected_profit_loss_ratio: float = 1.0  # 盈亏比
    
    # 风险管理
    max_drawdown: float = 0.15  # 最大回撤容限
    volatility: float = 0.2  # 预期波动率
    
    # 分配配置
    weight: float = 0.1  # 权重 (0-1)
    position_size: float = 0.0  # 实际仓位
    
    # 标签和分类
    strategy_type: str = "trend"  # trend, mean_reversion, arbitrage, etc.
    tags: List[str] = field(default_factory=list)  # e.g., ["momentum", "multi-factor"]
    
    is_active: bool = True  # 是否激活
    created_at: datetime = field(default_factory=datetime.now)
    
    def calculate_expectancy(self) -> float:
        """计算期望价值 = 胜率×盈利 - 负率×亏损"""
        loss_rate = 1.0 - self.expected_win_rate
        return (self.expected_win_rate * self.expected_profit_loss_ratio 
                - loss_rate * 1.0)
    
    def is_positive_expectancy(self) -> bool:
        """是否为正期望策略"""
        return self.calculate_expectancy() > 0
    
    def __repr__(self) -> str:
        return (f"Strategy({self.name}, {self.symbol}, weight={self.weight:.2%}, "
                f"expectancy={self.calculate_expectancy():.4f})")


@dataclass
class PortfolioMetrics:
    """投资组合指标"""
    total_value: float = 0.0  # 总市值
    cash: float = 0.0  # 现金
    
    # 收益指标
    daily_return: float = 0.0  # 日收益率
    cumulative_return: float = 0.0  # 累计收益率
    annual_return: float = 0.0  # 年化收益率
    
    # 风险指标
    volatility: float = 0.0  # 波动率
    sharpe_ratio: float = 0.0  # 夏普比率
    max_drawdown: float = 0.0  # 最大回撤
    correlation_matrix: Optional[np.ndarray] = None  # 品种相关性矩阵
    
    # 仓位指标
    gross_leverage: float = 0.0  # 总杠杆
    net_leverage: float = 0.0  # 净杠杆
    
    timestamp: datetime = field(default_factory=datetime.now)


class PortfolioManager:
    """
    多策略投资组合管理器
    
    核心功能：
    1. 多策略框架 - 管理多个策略，支持不同品种
    2. 正期望验证 - 基于数学期望筛选策略
    3. 低相关性 - 监测品种间相关性
    4. 再平衡 - 定期调整仓位
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.strategies: Dict[str, Strategy] = {}
        self.history: List[Dict[str, Any]] = []
        self.metrics = PortfolioMetrics(total_value=initial_capital, cash=initial_capital)
        logger.info(f"初始化投资组合管理器: 初始资本={initial_capital:.2f}")
    
    # ============ 策略管理 ============
    
    def add_strategy(self, strategy: Strategy) -> bool:
        """添加策略到组合"""
        if strategy.name in self.strategies:
            logger.warning(f"策略 {strategy.name} 已存在，将被覆盖")
        
        if not strategy.is_positive_expectancy():
            logger.warning(f"策略 {strategy.name} 不是正期望 (expectancy={strategy.calculate_expectancy():.4f})")
        
        self.strategies[strategy.name] = strategy
        logger.info(f"策略已添加: {strategy}")
        return True
    
    def remove_strategy(self, strategy_name: str) -> bool:
        """移除策略"""
        if strategy_name in self.strategies:
            del self.strategies[strategy_name]
            logger.info(f"策略已移除: {strategy_name}")
            return True
        return False
    
    def get_active_strategies(self) -> List[Strategy]:
        """获取所有活跃策略"""
        return [s for s in self.strategies.values() if s.is_active]
    
    def get_positive_expectancy_strategies(self) -> List[Strategy]:
        """获取所有正期望策略"""
        return [s for s in self.get_active_strategies() if s.is_positive_expectancy()]
    
    def list_strategies(self) -> pd.DataFrame:
        """策略列表"""
        data = []
        for strategy in self.strategies.values():
            data.append({
                "策略名": strategy.name,
                "品种": strategy.symbol,
                "权重": strategy.weight,
                "仓位": strategy.position_size,
                "期望收益": strategy.expected_return,
                "胜率": strategy.expected_win_rate,
                "盈亏比": strategy.expected_profit_loss_ratio,
                "期望价值": strategy.calculate_expectancy(),
                "状态": "激活" if strategy.is_active else "禁用",
            })
        return pd.DataFrame(data) if data else pd.DataFrame()
    
    # ============ 仓位管理 ============
    
    def allocate_positions(self) -> Dict[str, float]:
        """
        根据权重和期望分配仓位
        讲座理念: "敢握硬的低风险投资才是好投资"
        """
        active_strategies = self.get_active_strategies()
        
        if not active_strategies:
            logger.warning("没有活跃策略")
            return {}
        
        # 标准化权重
        total_weight = sum(s.weight for s in active_strategies)
        if total_weight == 0:
            logger.warning("权重总和为0，使用等权配置")
            total_weight = len(active_strategies)
            for s in active_strategies:
                s.weight = 1.0 / len(active_strategies)
        
        # 分配仓位
        positions = {}
        for strategy in active_strategies:
            # 可用资金 = 现金（暂时不考虑融资）
            position_size = self.current_capital * (strategy.weight / total_weight)
            strategy.position_size = position_size
            positions[strategy.name] = position_size
            logger.debug(f"{strategy.name}: 仓位={position_size:.2f}")
        
        return positions
    
    def set_weight(self, strategy_name: str, weight: float) -> bool:
        """设置策略权重"""
        if strategy_name not in self.strategies:
            logger.error(f"策略 {strategy_name} 不存在")
            return False
        
        if weight < 0 or weight > 1:
            logger.error(f"权重必须在0-1之间，当前值={weight}")
            return False
        
        self.strategies[strategy_name].weight = weight
        logger.info(f"更新权重: {strategy_name}={weight:.2%}")
        return True
    
    # ============ 风险管理 ============
    
    def calculate_correlation_matrix(self, price_data: Dict[str, pd.Series]) -> np.ndarray:
        """
        计算品种相关性矩阵
        讲座理念: "低相关性提高组合稳定性"
        """
        if not price_data:
            return np.array([])
        
        # 将价格数据转换为DataFrame
        df = pd.DataFrame(price_data)
        
        # 计算收益率
        returns = df.pct_change().dropna()
        
        # 计算相关性矩阵
        corr_matrix = returns.corr().values
        
        logger.info(f"相关性矩阵计算完成，形状={corr_matrix.shape}")
        return corr_matrix
    
    def get_correlation_analysis(self) -> Dict[str, float]:
        """获取相关性分析报告"""
        if self.metrics.correlation_matrix is None:
            return {}
        
        corr = self.metrics.correlation_matrix
        n = corr.shape[0]
        
        if n < 2:
            return {"message": "品种数不足"}
        
        # 计算平均相关性
        avg_corr = np.mean(np.abs(corr[np.triu_indices_from(corr, k=1)]))
        
        # 计算最大相关性
        max_corr = np.max(np.abs(corr[np.triu_indices_from(corr, k=1)]))
        
        # 计算最小相关性
        min_corr = np.min(np.abs(corr[np.triu_indices_from(corr, k=1)]))
        
        return {
            "average_correlation": float(avg_corr),
            "max_correlation": float(max_corr),
            "min_correlation": float(min_corr),
            "is_low_correlation": avg_corr < 0.5,  # 平均相关性 < 0.5 认为是低相关
        }
    
    # ============ 再平衡 ============
    
    def rebalance(self, method: str = "weight") -> Dict[str, float]:
        """
        再平衡投资组合
        讲座理念: "年度再平衡，动态调整仓位"
        
        Args:
            method: "weight" (按权重再平衡) 或 "performance" (按表现再平衡)
        """
        if method == "weight":
            return self._rebalance_by_weight()
        elif method == "performance":
            return self._rebalance_by_performance()
        else:
            logger.error(f"未知的再平衡方法: {method}")
            return {}
    
    def _rebalance_by_weight(self) -> Dict[str, float]:
        """按权重再平衡"""
        logger.info("执行权重再平衡...")
        positions = self.allocate_positions()
        
        self.history.append({
            "timestamp": datetime.now(),
            "method": "weight",
            "positions": positions.copy(),
            "total_value": self.current_capital,
        })
        
        return positions
    
    def _rebalance_by_performance(self) -> Dict[str, float]:
        """按表现再平衡：表现好的策略增加权重，表现差的减少权重"""
        logger.info("执行表现再平衡...")
        
        active_strategies = self.get_active_strategies()
        if not active_strategies:
            return {}

        # 简单的启发式算法：根据期望收益率调整权重
        # 注意：实际生产环境应使用真实的历史回测收益率或实盘收益率
        total_score = sum(max(0, s.expected_return) for s in active_strategies)
        
        if total_score > 0:
            for strategy in active_strategies:
                # 动态调整逻辑：原始权重占50%，基于期望收益的权重占50%
                performance_weight = max(0, strategy.expected_return) / total_score
                new_weight = 0.5 * strategy.weight + 0.5 * performance_weight
                strategy.weight = new_weight
                logger.info(f"策略 {strategy.name} 权重调整为 {new_weight:.2%}")
        
        positions = self.allocate_positions()
        
        self.history.append({
            "timestamp": datetime.now(),
            "method": "performance",
            "positions": positions.copy(),
            "total_value": self.current_capital,
        })
        
        return positions
    
    # ============ 报告 ============
    
    def get_summary(self) -> Dict[str, Any]:
        """获取投资组合摘要"""
        active_strategies = self.get_active_strategies()
        positive_expectancy = self.get_positive_expectancy_strategies()
        
        return {
            "总策略数": len(self.strategies),
            "活跃策略数": len(active_strategies),
            "正期望策略数": len(positive_expectancy),
            "初始资本": self.initial_capital,
            "当前资本": self.current_capital,
            "现金": self.metrics.cash,
            "总市值": self.metrics.total_value,
            "累计收益率": self.metrics.cumulative_return,
            "年化收益率": self.metrics.annual_return,
            "波动率": self.metrics.volatility,
            "夏普比率": self.metrics.sharpe_ratio,
            "最大回撤": self.metrics.max_drawdown,
            "相关性分析": self.get_correlation_analysis(),
        }
    
    def generate_report(self) -> str:
        """生成文本报告"""
        summary = self.get_summary()
        
        report = """
╔════════════════════════════════════════╗
║      投资组合管理报告 (Rox Quant)       ║
╚════════════════════════════════════════╝

【基本信息】
- 初始资本: ¥{:.2f}
- 当前资本: ¥{:.2f}
- 现金: ¥{:.2f}

【收益指标】
- 累计收益率: {:.2%}
- 年化收益率: {:.2%}
- 波动率: {:.2%}
- 夏普比率: {:.4f}
- 最大回撤: {:.2%}

【策略信息】
- 总策略数: {}
- 活跃策略数: {}
- 正期望策略数: {}

【相关性分析】
- 平均相关性: {:.4f}
- 最大相关性: {:.4f}
- 最小相关性: {:.4f}
- 低相关性评估: {}

【策略列表】
{}
        """.format(
            summary["初始资本"],
            summary["当前资本"],
            summary["现金"],
            summary["累计收益率"],
            summary["年化收益率"],
            summary["波动率"],
            summary["夏普比率"],
            summary["最大回撤"],
            summary["总策略数"],
            summary["活跃策略数"],
            summary["正期望策略数"],
            summary["相关性分析"].get("average_correlation", 0),
            summary["相关性分析"].get("max_correlation", 0),
            summary["相关性分析"].get("min_correlation", 0),
            "是" if summary["相关性分析"].get("is_low_correlation", False) else "否",
            self.list_strategies().to_string(),
        )
        
        return report
