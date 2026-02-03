"""
P3.5 Day 1: 集成测试
演示如何使用 BacktestEngine 和 PerformanceMetrics

场景：测试一个简单的移动平均策略
  - 当短期MA > 长期MA，发出BUY信号
  - 当短期MA < 长期MA，发出SELL信号
"""

import pandas as pd
import sys
import pytest
from pathlib import Path

# 导入刚刚创建的模块
sys.path.insert(0, str(Path(__file__).parent.parent / 'app' / 'rox_quant'))
from backtest_engine import BacktestEngine, BacktestConfig, create_sample_klines
from performance_metrics import PerformanceMetrics


def simple_ma_signal(klines_df: pd.DataFrame, current_index: int) -> str:
    """
    简单的移动平均策略
    
    逻辑：
      - 计算短期MA(5日) 和 长期MA(20日)
      - 短期 > 长期 → BUY (看涨)
      - 短期 < 长期 → SELL (看跌)
    """
    
    # 需要至少20根K线才能计算长期MA
    if current_index < 20:
        return 'HOLD'
    
    # 计算移动平均
    short_ma = klines_df['close'].iloc[current_index-5:current_index].mean()
    long_ma = klines_df['close'].iloc[current_index-20:current_index].mean()
    
    # 生成信号
    if short_ma > long_ma:
        return 'BUY'
    elif short_ma < long_ma:
        return 'SELL'
    else:
        return 'HOLD'


def test_backtest_engine():
    """测试 BacktestEngine 基本功能"""
    print("\n" + "="*70)
    print("🧪 测试 1: BacktestEngine 基本功能".center(70))
    print("="*70)
    
    # 创建配置
    config = BacktestConfig(
        initial_capital=100000.0,      # 初始资金10万
        commission_rate=0.0003,         # 手续费0.03%
        slippage=0.0001,                # 滑点0.01%
        position_size=0.5               # 每次用50%的资金买入
    )
    
    # 创建引擎
    engine = BacktestEngine(config)
    
    # 加载K线数据（示例数据：100根）
    klines = create_sample_klines(rows=100)
    print(f"\n✓ 创建示例K线数据: {len(klines)} 根")
    print(f"  日期范围: {klines['date'].iloc[0]} ~ {klines['date'].iloc[-1]}")
    print(f"  价格范围: {klines['close'].min():.2f} ~ {klines['close'].max():.2f}")
    
    engine.load_klines(klines)
    
    # 运行回测
    print(f"\n🔄 运行回测 (策略: 简单移动平均)...")
    engine.run(simple_ma_signal)
    
    # 查看交易记录
    trades = engine.get_trades()
    print(f"\n✓ 回测完成")
    print(f"  成交交易: {len(trades)} 笔")
    
    if trades:
        print(f"\n  交易明细:")
        for i, trade in enumerate(trades[:5], 1):  # 显示前5笔
            print(f"    {i}. 买入价={trade.entry_price:.2f}, 卖出价={trade.exit_price:.2f}, " +
                  f"利润={trade.profit:.2f}元 ({trade.profit_pct:.2f}%)")
        if len(trades) > 5:
            print(f"    ... 还有 {len(trades)-5} 笔交易")
    
    # 查看账户状态
    status = engine.get_current_status()
    print(f"\n  最终账户状态:")
    print(f"    现金余额: {status['cash']:,.2f} 元")
    print(f"    持仓数量: {status['position_qty']} 股")
    print(f"    总手续费: {status['total_commission']:,.2f} 元")
    
    return engine


@pytest.fixture
def engine():
    """Create a BacktestEngine instance for testing"""
    config = BacktestConfig(
        initial_capital=100000.0,
        commission_rate=0.0003,
        slippage=0.0001,
        position_size=0.5
    )
    engine = BacktestEngine(config)
    klines = create_sample_klines(rows=100)
    engine.load_klines(klines)
    return engine

def test_performance_metrics(engine: BacktestEngine):
    """测试 PerformanceMetrics 指标计算"""
    print("\n" + "="*70)
    print("🧪 测试 2: PerformanceMetrics 性能指标".center(70))
    print("="*70)
    
    # 获取数据
    trades = engine.get_trades()
    portfolio_values, portfolio_dates = engine.get_portfolio_values()
    initial_capital = engine.config.initial_capital
    
    # 计算指标
    metrics = PerformanceMetrics()
    report = metrics.calculate(
        trades=trades,
        portfolio_values=portfolio_values,
        portfolio_dates=portfolio_dates,
        initial_capital=initial_capital
    )
    
    # 打印报告
    print(report)
    
    # 转换为字典（用于API返回）
    report_dict = metrics.to_dict()
    print("\n📋 指标字典格式 (用于JSON返回):")
    for key, value in report_dict.items():
        print(f"  {key}: {value}")
    
    return report, report_dict


def test_different_signals():
    """测试不同的交易信号策略"""
    print("\n" + "="*70)
    print("🧪 测试 3: 不同策略对比".center(70))
    print("="*70)
    
    # 准备数据
    klines = create_sample_klines(rows=200)
    
    # 策略1: 简单MA策略
    def ma_signal(df, idx):
        if idx < 20:
            return 'HOLD'
        short_ma = df['close'].iloc[idx-5:idx].mean()
        long_ma = df['close'].iloc[idx-20:idx].mean()
        return 'BUY' if short_ma > long_ma else ('SELL' if short_ma < long_ma else 'HOLD')
    
    # 策略2: 极端价格策略 (高处卖，低处买)
    def extreme_price_signal(df, idx):
        if idx < 20:
            return 'HOLD'
        prices = df['close'].iloc[idx-20:idx]
        recent_price = df['close'].iloc[idx]
        if recent_price > prices.quantile(0.75):
            return 'SELL'  # 高位卖出
        elif recent_price < prices.quantile(0.25):
            return 'BUY'   # 低位买入
        return 'HOLD'
    
    # 策略3: 持有策略 (直接买入持有)
    def buy_hold_signal(df, idx):
        if idx == 20:  # 第21根K线买入
            return 'BUY'
        elif idx == len(df) - 1:  # 最后一根K线卖出
            return 'SELL'
        return 'HOLD'
    
    strategies = [
        ('简单MA策略', ma_signal),
        ('极端价格策略', extreme_price_signal),
        ('买入持有策略', buy_hold_signal)
    ]
    
    config = BacktestConfig(initial_capital=100000.0, position_size=0.5)
    metrics_calc = PerformanceMetrics()
    
    results = []
    
    for name, signal_func in strategies:
        print(f"\n▶ 测试策略: {name}")
        
        engine = BacktestEngine(config)
        engine.load_klines(klines.copy())
        engine.run(signal_func)
        
        trades = engine.get_trades()
        portfolio_values, portfolio_dates = engine.get_portfolio_values()
        
        report = metrics_calc.calculate(trades, portfolio_values, portfolio_dates, config.initial_capital)
        
        print(f"  交易笔数: {report.total_trades}")
        print(f"  胜率: {report.win_rate:.2f}%")
        print(f"  盈亏比: {report.profit_factor:.2f}")
        print(f"  净利润: {report.net_profit:,.2f} 元")
        print(f"  最大回撤: {report.max_drawdown:.2f}%")
        
        results.append({
            'name': name,
            'report': report,
            'trades': trades,
            'portfolio_values': portfolio_values
        })
    
    # 对比结果
    print("\n" + "-"*70)
    print("📊 策略对比汇总".center(70))
    print("-"*70)
    print(f"{'策略名称':<15} {'交易数':<8} {'胜率':<8} {'盈亏比':<8} {'净利润':<15} {'最大回撤':<10}")
    print("-"*70)
    
    for result in results:
        r = result['report']
        print(f"{result['name']:<15} {r.total_trades:<8} {r.win_rate:<7.1f}% {r.profit_factor:<7.2f} " +
              f"{r.net_profit:<14,.0f} {r.max_drawdown:<9.2f}%")
    
    print("-"*70)
    
    return results


def test_edge_cases():
    """测试边界情况"""
    print("\n" + "="*70)
    print("🧪 测试 4: 边界情况处理".center(70))
    print("="*70)
    
    # 情况1: 没有交易
    print("\n▶ 场景1: 没有交易信号")
    config = BacktestConfig(initial_capital=100000.0)
    engine = BacktestEngine(config)
    klines = create_sample_klines(50)
    engine.load_klines(klines)
    
    def no_signal(df, idx):
        return 'HOLD'  # 始终持仓，不交易
    
    engine.run(no_signal)
    trades = engine.get_trades()
    print(f"  交易笔数: {len(trades)} (预期: 0)")
    
    # 情况2: 单笔交易
    print("\n▶ 场景2: 单笔交易")
    engine2 = BacktestEngine(config)
    engine2.load_klines(klines)
    
    def single_trade(df, idx):
        if idx == 10:
            return 'BUY'
        elif idx == 20:
            return 'SELL'
        return 'HOLD'
    
    engine2.run(single_trade)
    trades2 = engine2.get_trades()
    print(f"  交易笔数: {len(trades2)} (预期: 1)")
    if trades2:
        print(f"  利润: {trades2[0].profit:.2f} 元")
    
    # 情况3: 连续交易
    print("\n▶ 场景3: 频繁交易")
    engine3 = BacktestEngine(config)
    engine3.load_klines(klines)
    
    def frequent_signal(df, idx):
        if idx % 3 == 0:
            return 'BUY'
        elif idx % 3 == 2:
            return 'SELL'
        return 'HOLD'
    
    engine3.run(frequent_signal)
    trades3 = engine3.get_trades()
    print(f"  交易笔数: {len(trades3)}")
    
    total_commission = sum(t.commission + abs(t.exit_price * t.exit_qty * 0.0003) 
                          for t in trades3 if t.exit_price)
    print(f"  总手续费: {total_commission:,.2f} 元")
    print(f"  手续费占资金比: {(total_commission/config.initial_capital)*100:.2f}%")


if __name__ == '__main__':
    print("\n" + "█"*70)
    print("P3.5 Day 1: 回测引擎 + 性能指标 - 完整测试".center(70))
    print("█"*70)
    
    # 运行所有测试
    engine = test_backtest_engine()
    report, report_dict = test_performance_metrics(engine)
    results = test_different_signals()
    test_edge_cases()
    
    print("\n" + "█"*70)
    print("✅ 所有测试完成！".center(70))
    print("█"*70)
    print("\n接下来的步骤:")
    print("  1. 用自己的K线数据替换 create_sample_klines()")
    print("  2. 用自己的信号函数替换 simple_ma_signal()")
    print("  3. 运行 engine.run(your_signal_function) 获得性能报告")
    print("  4. 调用 metrics.to_dict() 生成API返回格式\n")
