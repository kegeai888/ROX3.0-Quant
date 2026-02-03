"""
P3.5 完整集成测试
运行所有Day 1-5的模块，演示完整的量化系统流程
"""

import sys
from pathlib import Path

# 导入所有模块
sys.path.insert(0, str(Path(__file__).parent.parent / 'app' / 'rox_quant'))

from backtest_engine import BacktestEngine, BacktestConfig, create_sample_klines
from performance_metrics import PerformanceMetrics
from factor_analyzer import FactorAnalyzer
from overfitting_detector import OverfittingDetector
from backtest_report_generator import BacktestReportGenerator
import pandas as pd
import numpy as np


def create_advanced_signal(klines_df: pd.DataFrame, current_index: int) -> str:
    """
    高级信号函数：多因子融合策略
    
    因子：
      1. MA 信号 (20日 vs 50日)
      2. RSI 信号 (超卖<30 买入, 超买>70 卖出)
      3. 价格信号 (高位卖，低位买)
    """
    if current_index < 50:
        return 'HOLD'
    
    # 因子1: MA信号
    ma20 = klines_df['close'].iloc[current_index-20:current_index].mean()
    ma50 = klines_df['close'].iloc[current_index-50:current_index].mean()
    ma_signal = 'BUY' if ma20 > ma50 else 'SELL'
    
    # 因子2: RSI信号
    close_prices = klines_df['close'].iloc[current_index-14:current_index].values
    rsi = calculate_rsi(close_prices, 14)
    rsi_signal = 'BUY' if rsi < 30 else ('SELL' if rsi > 70 else 'HOLD')
    
    # 因子3: 价格信号
    recent_prices = klines_df['close'].iloc[current_index-20:current_index]
    current_price = klines_df['close'].iloc[current_index]
    
    if current_price > recent_prices.quantile(0.8):
        price_signal = 'SELL'
    elif current_price < recent_prices.quantile(0.2):
        price_signal = 'BUY'
    else:
        price_signal = 'HOLD'
    
    # 融合信号：多数决
    signals = [ma_signal, rsi_signal, price_signal]
    buy_count = signals.count('BUY')
    sell_count = signals.count('SELL')
    
    if buy_count >= 2:
        return 'BUY'
    elif sell_count >= 2:
        return 'SELL'
    else:
        return 'HOLD'


def calculate_rsi(prices, period=14):
    """计算RSI指标"""
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down > 0 else 0
    rsi = 100 - 100 / (1 + rs)
    return rsi


def test_complete_workflow():
    """完整的量化系统流程测试"""
    
    print("\n" + "█"*80)
    print("P3.5 完整集成测试 - Day 1-5".center(80))
    print("█"*80)
    
    # 1. 创建回测配置和数据
    print("\n▶ Step 1: 准备数据")
    config = BacktestConfig(
        initial_capital=100000.0,
        commission_rate=0.0003,
        slippage=0.0001,
        position_size=0.5
    )
    klines = create_sample_klines(rows=200)
    print(f"  ✓ 创建K线数据: {len(klines)} 根")
    
    # 2. 运行回测 (Day 1)
    print("\n▶ Step 2: 回测引擎 (Day 1)")
    engine = BacktestEngine(config)
    engine.load_klines(klines)
    engine.run(create_advanced_signal)
    
    trades = engine.get_trades()
    portfolio_values, portfolio_dates = engine.get_portfolio_values()
    print(f"  ✓ 回测完成: {len(trades)} 笔交易")
    
    # 3. 计算性能指标 (Day 1)
    print("\n▶ Step 3: 性能指标计算 (Day 1)")
    metrics = PerformanceMetrics()
    perf_report = metrics.calculate(
        trades=trades,
        portfolio_values=portfolio_values,
        portfolio_dates=portfolio_dates,
        initial_capital=config.initial_capital
    )
    print(f"  ✓ 胜率: {perf_report.win_rate:.2f}%")
    print(f"  ✓ 盈亏比: {perf_report.profit_factor:.2f}")
    print(f"  ✓ 净利润: ¥{perf_report.net_profit:,.0f}")
    print(f"  ✓ 最大回撤: {perf_report.max_drawdown:.2f}%")
    
    # 4. 因子分析 (Day 2)
    print("\n▶ Step 4: 因子分析 (Day 2)")
    factor_analyzer = FactorAnalyzer()
    
    # 模拟因子记录（真实环境中需要在交易时记录）
    for i, trade in enumerate(trades):
        factor_name = ['MA策略', 'RSI策略', '价格策略'][i % 3]
        factor_analyzer.record_trade_factor(factor_name, trade)
    
    factor_contributions = factor_analyzer.analyze()
    ranking = factor_analyzer.get_ranking('contribution_pct')
    
    print(f"  ✓ 分析 {len(factor_contributions)} 个因子")
    print(f"  ✓ Top因子: {ranking[0].factor_name} (贡献度 {ranking[0].contribution_pct:.2f}%)")
    
    # 5. 过拟合检测 (Day 3)
    print("\n▶ Step 5: 过拟合检测 (Day 3)")
    overfitting_detector = OverfittingDetector()
    
    # Rolling window 测试
    overfitting_report = overfitting_detector.rolling_window_test(
        klines=klines,
        signal_func=create_advanced_signal,
        window_size=50,
        step=15
    )
    
    print(f"  ✓ Rolling window 测试: {overfitting_report.total_window_tests} 个窗口")
    print(f"  ✓ 胜率平均值: {overfitting_report.win_rate_mean:.2f}%")
    print(f"  ✓ 过拟合指数: {overfitting_report.overfitting_score:.1f}/100")
    print(f"  ✓ 稳定性指数: {overfitting_report.stability_index:.1f}/100")
    
    if overfitting_report.is_overfitted:
        print(f"  ⚠️ 警告: 策略存在过拟合风险!")
    else:
        print(f"  ✓ 策略相对稳健")
    
    # 6. 报告生成 (Day 4)
    print("\n▶ Step 6: 报告生成 (Day 4)")
    generator = BacktestReportGenerator()
    
    # 生成JSON报告
    json_report = generator.generate_json_report(
        performance_report=perf_report,
        factor_analysis=factor_analyzer.to_dict(),
        overfitting_report=overfitting_detector.to_dict()
    )
    
    # 生成HTML报告
    html_report = generator.generate_html_report(
        performance_report=perf_report,
        portfolio_values=portfolio_values,
        portfolio_dates=portfolio_dates,
        trades=trades,
        factor_analysis=factor_analyzer.to_dict(),
        overfitting_report=overfitting_detector.to_dict(),
        filename='backtest_report_p35.html'
    )
    
    print(f"  ✓ 生成JSON报告: {len(json_report)} 字符")
    print(f"  ✓ 生成HTML报告: {len(html_report)} 字符")
    
    # 7. 保存报告到文件 (Day 5)
    print("\n▶ Step 7: 保存报告文件 (Day 5)")
    
    # 保存JSON
    json_path = Path(__file__).parent.parent.parent / 'backtest_report_p35.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        f.write(json_report)
    print(f"  ✓ JSON报告已保存: {json_path}")
    
    # 保存HTML
    html_path = Path(__file__).parent.parent.parent / 'backtest_report_p35.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_report)
    print(f"  ✓ HTML报告已保存: {html_path}")
    
    # 8. 打印完整报告
    print("\n" + "="*80)
    print("完整的性能报告".center(80))
    print("="*80)
    print(perf_report)
    
    print("\n" + "="*80)
    print("因子分析报告".center(80))
    print("="*80)
    print(factor_analyzer.print_report())
    
    print("\n" + "="*80)
    print("过拟合检测报告".center(80))
    print("="*80)
    print(overfitting_report)
    
    print("\n" + "█"*80)
    print("✅ P3.5 Day 1-5 全部完成！".center(80))
    print("█"*80)
    print("\n📊 生成的文件:")
    print(f"  1. {json_path} - JSON格式数据")
    print(f"  2. {html_path} - 可视化HTML报告")
    print("\n🚀 可以直接在浏览器打开HTML文件查看完整报告")


if __name__ == '__main__':
    import numpy as np
    test_complete_workflow()
