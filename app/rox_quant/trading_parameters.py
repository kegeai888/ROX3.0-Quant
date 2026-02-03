"""
参数配置系统 - 基于《量化交易从入门到精通》
将书中的所有参数标准化、可配置化
"""

from typing import Dict, Optional
from dataclasses import dataclass, field
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class SignalParameters:
    """交易信号参数"""
    
    # ====== 信号1：唐奇安通道突破 ======
    donchian_period: int = 20  # 书中有20/55/88等
    donchian_breakout_filter: Optional[str] = None  # 'ma'=使用均线过滤
    
    # ====== 信号2：MA专业线系统 ======
    # 短期均线 (2-49)
    ma_short_periods: list = field(default_factory=lambda: [2, 5, 10, 13])
    # 中期均线 (50-99)
    ma_medium_periods: list = field(default_factory=lambda: [50, 60, 70])
    # 长期均线 (>=100)
    ma_long_periods: list = field(default_factory=lambda: [120, 200, 250])
    
    # 双子线战法
    ma_fast_for_entry: int = 28  # 进场均线
    ma_slow_for_defense: int = 48  # 防守均线
    
    # ====== 信号3：自适应均线 (AMA) ======
    ama_efficiency_period: int = 10
    ama_fast_sc: int = 2  # 快速平滑常数周期
    ama_slow_sc: int = 30  # 慢速平滑常数周期
    ama_breakout_period: int = 20  # 结合唐奇安突破的周期
    
    # ====== 信号4：ATR通道 & 金肯特纳 ======
    keltner_ma_period: int = 56  # 书中推荐56
    keltner_atr_period: int = 3
    keltner_atr_multiple: float = 1.0
    
    # ====== 信号4b：布林带 ======
    bollinger_period: int = 48
    bollinger_std: float = 1.8
    bollinger_width_threshold: float = 1.01  # 1%窄化
    
    # ====== 信号5：RSI + 成本线 ======
    rsi_period: int = 5
    rsi_oversold_threshold: int = 20  # RSI<20 为超卖
    cost_ma_period: int = 33  # 或58，根据周期调整
    cost_percentage: float = 0.019  # A股日线约19%
    fat1_deviation: float = 0.009  # 偏离阈值 0.9%
    fat2_momentum: float = 0.0024  # 动能减弱阈值 0.24%
    
    # ====== 信号6：MACD背离 ======
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    macd_divergence_lookback: int = 10  # 向后查看周期
    
    # ====== 信号7：ADX / Aroon ======
    adx_period: int = 14
    adx_weak_to_strong_threshold: int = 20  # ADX < 20 为弱趋势
    aroon_period: int = 25
    aroon_threshold: float = 45.0


@dataclass
class ExitParameters:
    """出场参数"""
    
    # 止损参数
    use_atr_stop: bool = True  # 使用ATR止损
    stop_loss_atr_multiplier: float = 2.0  # ATR的倍数（2-5倍）
    use_ma_stop: bool = True  # 使用均线止损
    ma_stop_type: str = 'ama'  # 'ama'或'kama'自适应均线
    
    # 止盈参数
    use_atr_tp: bool = True
    take_profit_atr_multiplier: float = 3.0
    use_fixed_tp: bool = True
    take_profit_fixed_pct: float = 0.0075  # 0.75%
    
    # 时间止盈
    use_time_stop: bool = True
    time_stop_bars: int = 30  # 持仓超过30个bar
    time_stop_profit_threshold: float = 0.0002  # 收益±0.02%
    
    # 趋势反转止盈
    use_trend_reversal_tp: bool = True
    trend_reversal_type: str = 'macd'  # 'macd'或'ma'


@dataclass
class RiskParameters:
    """风险管理参数"""
    
    # 账户级别
    initial_capital: float = 1000000.0  # 100万（书中常用基数）
    max_drawdown: float = 0.10  # 最大回撤 10%
    acceptable_loss_per_loss_period: float = 0.06  # 连续亏损期可接受损失 6%
    
    # 单笔交易风险
    single_trade_risk: float = 0.03  # 3%
    max_loss_per_trade: float = 0.01  # 单笔最多亏损账户的1%
    
    # 仓位管理
    position_size_method: str = 'kelly'  # 'kelly'或'fixed'
    position_size_fixed: float = 0.05  # 固定5%（可改为1-5%）
    
    # 期货特定
    futures_commision_rate: float = 0.0002  # 万2（书中标准假设）
    futures_slippage: float = 0.00001  # 滑点
    
    # 股票特定
    stock_commission_rate: float = 0.001  # 千1（含印花税/佣金）
    stock_slippage: float = 0.0005
    
    # 并发持仓
    max_concurrent_positions: int = 5
    max_exposure_per_asset: float = 0.10  # 单资产最多10%
    max_correlated_exposure: float = 0.20  # 相关资产最多20%
    
    # 杠杆
    leverage: float = 1.0  # 1.0=无杠杆，>1=有杠杆
    margin_ratio: float = 0.10  # 保证金比例10%（期货）


@dataclass
class BacktestParameters:
    """回测参数"""
    
    # 数据参数
    lookback_period: int = 500  # 回看周期
    min_bars_for_signal: int = 50  # 最少需要的K线数
    
    # 交易参数
    trading_cost_method: str = 'commission'  # 'commission'或'fixed'
    slippage_enabled: bool = True
    
    # 再平衡参数
    rebalance_frequency: str = 'daily'  # 'daily'或'weekly'
    
    # 基准参数
    benchmark_symbol: str = 'HS300'  # 沪深300
    benchmark_data_source: str = 'akshare'  # 数据源


@dataclass
class AssetParameters:
    """资产特定参数"""
    
    symbol: str  # 品种代码
    asset_class: str  # 'stock'/'futures'/'crypto'
    
    # 交易时间
    trading_hours: list = field(default_factory=lambda: ['09:30-11:30', '13:00-15:00'])
    
    # 合约参数（期货）
    contract_multiplier: float = 1.0  # 合约乘数
    tick_size: float = 0.01  # 最小变动单位
    
    # 风险参数
    max_position_size: float = 0.10  # 最大持仓占账户比例
    volatility_adjustment: bool = True  # 是否根据波动率调整仓位
    
    # 信号参数（可针对资产调优）
    signal_weights: Dict[str, float] = field(default_factory=lambda: {
        'donchian': 0.15,
        'ma_system': 0.15,
        'ama': 0.10,
        'keltner': 0.15,
        'rsi_cost': 0.15,
        'macd': 0.15,
        'adx': 0.15
    })


class ParameterSet:
    """参数集合 - 整合所有参数"""
    
    def __init__(self):
        self.signals = SignalParameters()
        self.exits = ExitParameters()
        self.risk = RiskParameters()
        self.backtest = BacktestParameters()
        self.assets: Dict[str, AssetParameters] = {}
        
        logger.info("✓ 参数系统初始化完成")
    
    def add_asset(self, asset_params: AssetParameters) -> None:
        """添加资产特定参数"""
        self.assets[asset_params.symbol] = asset_params
        logger.info(f"✓ 资产参数已添加: {asset_params.symbol}")
    
    def get_asset_params(self, symbol: str) -> Optional[AssetParameters]:
        """获取指定资产的参数"""
        return self.assets.get(symbol)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        result = {
            'signals': self.signals.__dict__,
            'exits': self.exits.__dict__,
            'risk': self.risk.__dict__,
            'backtest': self.backtest.__dict__,
            'assets': {
                symbol: asset.__dict__ 
                for symbol, asset in self.assets.items()
            }
        }
        return result
    
    def to_json(self, filepath: str) -> None:
        """保存为JSON文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"✓ 参数已保存到 {filepath}")
    
    def from_json(self, filepath: str) -> None:
        """从JSON文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 更新信号参数
        for key, value in data.get('signals', {}).items():
            if hasattr(self.signals, key):
                setattr(self.signals, key, value)
        
        # 更新出场参数
        for key, value in data.get('exits', {}).items():
            if hasattr(self.exits, key):
                setattr(self.exits, key, value)
        
        # 更新风险参数
        for key, value in data.get('risk', {}).items():
            if hasattr(self.risk, key):
                setattr(self.risk, key, value)
        
        logger.info(f"✓ 参数已从 {filepath} 加载")


class StrategyTemplates:
    """策略模板集合（来自书中案例）"""
    
    @staticmethod
    def get_trend_following_template() -> ParameterSet:
        """
        趋势跟随系统（书中"海龟"/"唐奇安"类）
        - 通道突破为主
        - ATR止损
        - 让利润奔跑
        """
        params = ParameterSet()
        
        params.signals.donchian_period = 20
        params.exits.use_atr_stop = True
        params.exits.stop_loss_atr_multiplier = 2.0
        params.exits.use_atr_tp = True
        params.exits.take_profit_atr_multiplier = 4.0  # 让利润奔跑
        
        params.risk.position_size_fixed = 0.03  # 3%仓位
        
        logger.info("✓ 趋势跟随系统模板已加载")
        return params
    
    @staticmethod
    def get_mean_reversion_template() -> ParameterSet:
        """
        均值回归系统（书中"RSI成本线"TOP3）
        - 低位低速买入
        - 固定止盈止损
        - 时间止盈
        """
        params = ParameterSet()
        
        params.signals.rsi_period = 5
        params.exits.use_fixed_tp = True
        params.exits.take_profit_fixed_pct = 0.0075  # 0.75%
        params.exits.use_time_stop = True
        params.exits.time_stop_bars = 30
        
        params.risk.position_size_fixed = 0.05  # 5%仓位
        
        logger.info("✓ 均值回归系统模板已加载")
        return params
    
    @staticmethod
    def get_box_breakout_template() -> ParameterSet:
        """
        箱体突破系统（书中"碧空之歌"）
        - 盘整后突破
        - 通道等宽延展
        """
        params = ParameterSet()
        
        params.signals.bollinger_period = 48
        params.signals.bollinger_std = 1.8
        params.exits.use_ma_stop = True
        
        logger.info("✓ 箱体突破系统模板已加载")
        return params
    
    @staticmethod
    def get_wave_trading_template() -> ParameterSet:
        """
        波浪交易系统（书中第3浪操作）
        - 用浪1约束浪3
        - 精确止损止盈
        """
        params = ParameterSet()
        
        params.exits.use_atr_stop = True
        params.exits.use_ma_stop = True
        
        logger.info("✓ 波浪交易系统模板已加载")
        return params


# 预设配置示例

DEFAULT_FUTURES_PARAMS = ParameterSet()
DEFAULT_FUTURES_PARAMS.risk.futures_commision_rate = 0.0002
DEFAULT_FUTURES_PARAMS.risk.position_size_fixed = 0.032  # 书中"剑宗入门"使用3.2%

DEFAULT_STOCK_PARAMS = ParameterSet()
DEFAULT_STOCK_PARAMS.risk.stock_commission_rate = 0.001
DEFAULT_STOCK_PARAMS.risk.position_size_fixed = 0.02  # 2%

# 专业金价参数（基于书中黄金案例）
GOLD_PARAMS = ParameterSet()
GOLD_PARAMS.signals.ma_short_periods = [3, 5, 12, 21, 25, 43]
GOLD_PARAMS.signals.ma_medium_periods = [64, 86, 99]
GOLD_PARAMS.signals.ma_long_periods = [120, 840, 888]

# 沪深300波动率策略参数（书中附录一）
HS300_VOLATILITY_PARAMS = ParameterSet()
HS300_VOLATILITY_PARAMS.backtest.benchmark_symbol = 'HS300'
HS300_VOLATILITY_PARAMS.risk.position_size_fixed = 0.025  # 2.5%
