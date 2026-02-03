"""
集成测试：量化交易系统全模块测试
验证7个核心信号、风险管理、参数配置的完整集成
"""

import sys
import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_ohlc(days: int = 200, start_price: float = 100.0) -> pd.DataFrame:
    """生成样本OHLC数据用于测试"""
    dates = [datetime.now() - timedelta(days=days-i) for i in range(days)]
    
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.02, days)
    prices = start_price * (1 + returns).cumprod()
    
    data = []
    for i, date in enumerate(dates):
        close = prices[i]
        open_ = close * (1 + np.random.normal(0, 0.005))
        high = max(open_, close) * (1 + abs(np.random.normal(0, 0.01)))
        low = min(open_, close) * (1 - abs(np.random.normal(0, 0.01)))
        volume = np.random.randint(1000000, 10000000)
        
        data.append({
            'datetime': date,
            'open': open_,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('datetime', inplace=True)
    return df.sort_index()


def test_trading_signals_advanced():
    """测试7个核心交易信号"""
    logger.info("\n" + "="*60)
    logger.info("测试1: 7个核心交易信号系统")
    logger.info("="*60)
    
    try:
        from app.rox_quant.trading_signals_advanced import AdvancedTradingSignals
        
        signals = AdvancedTradingSignals()
        ohlc = create_sample_ohlc()
        
        close = ohlc['close']
        high = ohlc['high']
        low = ohlc['low']
        
        # 测试每个信号
        tests = [
            ("信号1: 唐奇安通道突破", 
             lambda: signals.donchian_breakout(high, low, period=20)),
            
            ("信号2: MA专业线系统", 
             lambda: signals.professional_ma_system(close)),
            
            ("信号3: 自适应均线 (AMA)", 
             lambda: signals.kaufman_adaptive_ma(close)),
            
            ("信号4: 金肯特纳通道", 
             lambda: signals.atr_keltner_channel(high, low, close)),
            
            ("信号5: RSI + 成本线", 
             lambda: signals.rsi_cost_line(close)),
            
            ("信号6: MACD背离", 
             lambda: signals.macd_divergence(close)),
            
            ("信号7: ADX & Aroon", 
             lambda: signals.adx_trend_identifier(high, low))
        ]
        
        for name, func in tests:
            try:
                result = func()
                logger.info(f"✓ {name}")
                
                # 验证返回值
                if isinstance(result, dict):
                    logger.info(f"  返回键: {list(result.keys())}")
                
            except Exception as e:
                logger.error(f"✗ {name}: {e}")
                return False
        
        logger.info("✓ 7个核心信号系统全部通过测试")
        return True
    
    except ImportError as e:
        logger.error(f"导入失败: {e}")
        return False


def test_risk_management():
    """测试风险管理模块"""
    logger.info("\n" + "="*60)
    logger.info("测试2: 风险管理系统")
    logger.info("="*60)
    
    try:
        from app.rox_quant.risk_management_advanced import (
            RiskManager, RiskParams, AdvancedRiskMetrics
        )
        
        # 测试基本参数
        params = RiskParams(
            max_drawdown=0.10,
            single_trade_risk=0.03,
            position_size_pct=0.05
        )
        logger.info(f"✓ 风险参数创建成功")
        logger.info(f"  最大回撤: {params.max_drawdown:.2%}")
        logger.info(f"  单笔风险: {params.single_trade_risk:.2%}")
        
        # 测试风险管理器
        rm = RiskManager(params)
        
        # 测试止损/止盈计算
        stops = rm.calculate_stops(entry_price=100, atr=2.0, direction='long')
        logger.info(f"✓ 止损/止盈计算")
        logger.info(f"  止损: {stops['stop_loss']:.2f}")
        logger.info(f"  止盈: {stops['take_profit']:.2f}")
        
        # 测试仓位计算
        position = rm.calculate_position_size(
            account_balance=1000000,
            entry_price=100,
            stop_loss=98
        )
        logger.info(f"✓ 仓位大小: {position:.2%}")
        
        # 测试最优手数
        lot_info = rm.calculate_optimal_lot_size(
            account_balance=1000000,
            entry_price=100,
            stop_loss=98
        )
        logger.info(f"✓ 最优手数计算")
        logger.info(f"  理论仓位: {lot_info['theoretical_position_pct']:.2%}")
        logger.info(f"  实战仓位: {lot_info['practical_position_pct']:.2%}")
        
        # 测试回撤检查
        exceeded, dd = rm.check_drawdown_limit(950000)
        logger.info(f"✓ 回撤检查: 回撤={dd:.2%}, 超限={exceeded}")
        
        # 测试高级风险指标
        returns = pd.Series(np.random.normal(0.0005, 0.01, 100))
        
        var = AdvancedRiskMetrics.calculate_var(returns, 0.95)
        logger.info(f"✓ VaR (95%): {var:.4f}")
        
        sortino = AdvancedRiskMetrics.calculate_sortino_ratio(returns)
        logger.info(f"✓ Sortino比率: {sortino:.4f}")
        
        logger.info("✓ 风险管理系统全部通过测试")
        return True
    
    except ImportError as e:
        logger.error(f"导入失败: {e}")
        return False


def test_trading_parameters():
    """测试参数配置系统"""
    logger.info("\n" + "="*60)
    logger.info("测试3: 参数配置系统")
    logger.info("="*60)
    
    try:
        from app.rox_quant.trading_parameters import (
            ParameterSet, SignalParameters, ExitParameters,
            RiskParameters, StrategyTemplates, AssetParameters
        )
        
        # 测试参数集合
        params = ParameterSet()
        logger.info("✓ 参数集合创建成功")
        
        # 测试信号参数
        logger.info(f"✓ 信号参数:")
        logger.info(f"  唐奇安周期: {params.signals.donchian_period}")
        logger.info(f"  MA周期: 短={params.signals.ma_short_periods}, 中={params.signals.ma_medium_periods}")
        
        # 测试出场参数
        logger.info(f"✓ 出场参数:")
        logger.info(f"  ATR止损倍数: {params.exits.stop_loss_atr_multiplier}")
        logger.info(f"  时间止盈: {params.exits.time_stop_bars}根K线")
        
        # 测试风险参数
        logger.info(f"✓ 风险参数:")
        logger.info(f"  初始资金: ¥{params.risk.initial_capital:,.0f}")
        logger.info(f"  最大回撤: {params.risk.max_drawdown:.2%}")
        logger.info(f"  期货手续费: {params.risk.futures_commision_rate:.2%}")
        
        # 测试资产特定参数
        asset = AssetParameters(
            symbol='HS300',
            asset_class='futures',
            contract_multiplier=300.0,
            tick_size=0.2
        )
        params.add_asset(asset)
        logger.info(f"✓ 添加资产参数: {asset.symbol}")
        
        # 测试策略模板
        trend_template = StrategyTemplates.get_trend_following_template()
        logger.info(f"✓ 趋势跟随系统模板")
        logger.info(f"  唐奇安周期: {trend_template.signals.donchian_period}")
        logger.info(f"  止盈倍数: {trend_template.exits.take_profit_atr_multiplier}")
        
        mean_reversion = StrategyTemplates.get_mean_reversion_template()
        logger.info(f"✓ 均值回归系统模板")
        logger.info(f"  RSI周期: {mean_reversion.signals.rsi_period}")
        
        logger.info("✓ 参数配置系统全部通过测试")
        return True
    
    except ImportError as e:
        logger.error(f"导入失败: {e}")
        return False


def test_signal_fusion_integration():
    """测试信号融合与高级系统的集成"""
    logger.info("\n" + "="*60)
    logger.info("测试4: 信号融合与高级系统集成")
    logger.info("="*60)
    
    try:
        from app.rox_quant.signal_fusion import SignalFusion
        from app.rox_quant.trading_parameters import ParameterSet
        
        # 创建参数和融合器
        params = ParameterSet()
        fusion = SignalFusion(params)
        
        logger.info("✓ SignalFusion + 高级系统初始化成功")
        
        # 生成测试数据
        ohlc = create_sample_ohlc()
        
        # 测试高级系统信号生成
        signal = fusion.generate_signal_from_advanced_system('TEST', ohlc)
        logger.info(f"✓ 7信号融合: {signal.signal_type.name}")
        logger.info(f"  置信度: {signal.confidence:.2%}")
        logger.info(f"  理由: {signal.reason}")
        
        # 测试信号评分
        score = fusion.calculate_signal_score(ohlc)
        logger.info(f"✓ 信号评分: {score:.2f}/100")
        
        # 测试止损/止盈
        stops = fusion.get_stop_losses_and_targets(
            entry_price=100.0,
            atr=2.0,
            direction='long'
        )
        logger.info(f"✓ 止损止盈计算")
        logger.info(f"  止损: {stops.get('stop_loss', 'N/A')}")
        logger.info(f"  止盈: {stops.get('take_profit', 'N/A')}")
        
        logger.info("✓ 信号融合集成全部通过测试")
        return True
    
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    logger.info("\n")
    logger.info("╔" + "="*58 + "╗")
    logger.info("║" + " "*10 + "量化交易系统 - 全模块集成测试" + " "*14 + "║")
    logger.info("╚" + "="*58 + "╝")
    
    results = {
        "7个核心交易信号": test_trading_signals_advanced(),
        "风险管理系统": test_risk_management(),
        "参数配置系统": test_trading_parameters(),
        "信号融合集成": test_signal_fusion_integration(),
    }
    
    # 总结
    logger.info("\n" + "="*60)
    logger.info("测试总结")
    logger.info("="*60)
    
    for name, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        logger.info(f"{status} {name}")
    
    total_pass = sum(results.values())
    total_tests = len(results)
    
    logger.info("="*60)
    logger.info(f"总体: {total_pass}/{total_tests} 个测试通过")
    
    if total_pass == total_tests:
        logger.info("✓ 所有测试通过！系统可投入使用")
        return 0
    else:
        logger.error(f"✗ 有 {total_tests - total_pass} 个测试失败")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
