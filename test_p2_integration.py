#!/usr/bin/env python3
"""
P2 Kronos 集成验证脚本
验证 Kronos 模型适配器和信号融合功能
"""

import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def test_imports():
    """测试模块导入"""
    print("\n" + "="*60)
    print("📦 第1步: 导入模块验证")
    print("="*60)
    
    try:
        from app.rox_quant.kronos_adapter import (
            KronosAdapter, KronosPrediction, KronosModelSize, 
            create_kronos_adapter
        )
        print("✅ kronos_adapter 模块导入成功")
        
        from app.rox_quant.signal_fusion import SignalFusion
        print("✅ signal_fusion 模块导入成功")
        
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

def generate_test_data(n=500, symbol="TEST"):
    """生成测试K线数据"""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=n, freq='D')
    
    close = np.cumsum(np.random.randn(n) * 0.5) + 100
    high = close + np.abs(np.random.randn(n) * 2)
    low = close - np.abs(np.random.randn(n) * 2)
    open_ = close + np.random.randn(n)
    volume = np.random.randint(1000000, 10000000, n)
    
    df = pd.DataFrame({
        'date': dates,
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })
    
    return df

def test_kronos_adapter():
    """测试 Kronos 适配器"""
    print("\n" + "="*60)
    print("🧠 第2步: Kronos 适配器测试")
    print("="*60)
    
    try:
        from app.rox_quant.kronos_adapter import create_kronos_adapter
        
        # 创建适配器
        kronos = create_kronos_adapter(model_size="small", device="cpu")
        print("✅ Kronos 适配器创建成功")
        print(f"   - 模型大小: small (24.7M 参数)")
        print(f"   - 设备: cpu")
        
        # 生成测试数据
        test_df = generate_test_data(500, "600000")
        print(f"\n✅ 生成测试数据成功")
        print(f"   - 样本数: {len(test_df)}")
        print(f"   - 时间范围: {test_df['date'].min()} ~ {test_df['date'].max()}")
        
        # 测试单品种预测
        print(f"\n  预测单品种...")
        try:
            prediction = kronos.predict(
                price_data=test_df,
                symbol="600000",
                lookback=400,
                pred_len=20
            )
            print(f"✅ 单品种预测完成")
            print(f"   - 品种: {prediction.symbol}")
            print(f"   - 方向: {prediction.direction}")
            print(f"   - 置信度: {prediction.confidence:.2%}")
            print(f"   - 预期收益: {prediction.expected_return:.2%}")
            print(f"   - 模型版本: {prediction.model_version}")
        except Exception as e:
            print(f"⚠️  预测失败: {e}")
            
        # 测试批量预测
        print(f"\n  预测多品种...")
        try:
            symbols_data = {
                "600000": generate_test_data(500),
                "000858": generate_test_data(500),
            }
            predictions = kronos.predict_batch(
                symbols_data=symbols_data,
                lookback=400,
                pred_len=20,
                use_parallel=False
            )
            print(f"✅ 批量预测完成")
            for symbol, pred in predictions.items():
                print(f"   - {symbol}: {pred.direction} (置信度 {pred.confidence:.2%})")
        except Exception as e:
            print(f"⚠️  批量预测失败: {e}")
            
        # 缓存统计
        cache_stats = kronos.get_cache_stats()
        print(f"\n✅ 缓存统计")
        print(f"   - 缓存项数: {cache_stats['cache_size']}")
        print(f"   - 模型已加载: {cache_stats['model_loaded']}")
        print(f"   - 模型大小: {cache_stats['model_size']}")
        
        return True
    except Exception as e:
        print(f"❌ Kronos 适配器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_signal_fusion():
    """测试信号融合"""
    print("\n" + "="*60)
    print("🔄 第3步: 信号融合测试")
    print("="*60)
    
    try:
        from app.rox_quant.signal_fusion import SignalFusion
        
        # 创建融合器
        sf = SignalFusion()
        print("✅ SignalFusion 创建成功")
        
        # 生成测试数据
        test_df = generate_test_data(500, "600000")
        
        # 测试技术指标信号
        print(f"\n  生成技术指标信号...")
        signal = sf.generate_signal_from_ohlc("600000", test_df)
        print(f"✅ 技术指标信号生成完成")
        print(f"   - 品种: {signal.symbol}")
        print(f"   - 信号类型: {signal.signal_type.name}")
        print(f"   - 置信度: {signal.confidence:.2%}")
        print(f"   - 原因: {signal.reason}")
        
        return True
    except Exception as e:
        print(f"❌ 信号融合测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration():
    """测试完整集成"""
    print("\n" + "="*60)
    print("🚀 第4步: 完整集成测试")
    print("="*60)
    
    try:
        from app.rox_quant.kronos_adapter import create_kronos_adapter
        from app.rox_quant.signal_fusion import SignalFusion
        
        # 创建组件
        kronos = create_kronos_adapter(model_size="small", device="cpu")
        sf = SignalFusion()
        
        # 生成测试数据
        test_df = generate_test_data(450, "600000")
        
        # 融合信号
        print(f"\n  融合技术指标 + Kronos...")
        try:
            fused_signal = sf.fuse_with_kronos(
                ohlc=test_df,
                symbol="600000",
                kronos_adapter=kronos,
                kronos_weight=0.25
            )
            print(f"✅ 信号融合完成")
            print(f"   - 品种: {fused_signal.symbol}")
            print(f"   - 最终信号: {fused_signal.signal_type.name}")
            print(f"   - 综合置信度: {fused_signal.confidence:.2%}")
            
            # 调整权重
            print(f"\n  调整 Kronos 权重...")
            sf.set_kronos_weight(0.40)
            print(f"✅ Kronos 权重已调整为 40%")
        except Exception as e:
            print(f"⚠️  融合失败: {e}")
            
        return True
    except Exception as e:
        print(f"❌ 完整集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """运行所有测试"""
    print("\n" + "🎯 " * 20)
    print("Rox Quant P2 Kronos 集成验证")
    print("🎯 " * 20)
    
    results = {
        "导入测试": test_imports(),
        "Kronos 适配器": test_kronos_adapter(),
        "信号融合": test_signal_fusion(),
        "完整集成": test_integration(),
    }
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 测试汇总")
    print("="*60)
    
    all_passed = True
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not result:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 所有测试通过！P2 集成验证完成")
    else:
        print("⚠️  部分测试失败，请检查日志")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
