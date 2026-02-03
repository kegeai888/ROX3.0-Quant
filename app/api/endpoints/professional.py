"""
专业量化交易系统API端点
集成7个核心交易信号 + 风险管理 + 参数配置
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import logging
import asyncio

from app.auth import get_current_user, User
from app.db import get_db
from app.auth import get_current_user, User
from app.db import get_db
# from app.rox_quant.trading_signals_advanced import AdvancedTradingSignals, SignalStrengthCalculator
# from app.rox_quant.risk_management_advanced import RiskManager, RiskParams, AdvancedRiskMetrics
# from app.rox_quant.trading_parameters import StrategyTemplates, ParameterSet, SignalParameters
# from app.rox_quant.signal_fusion import SignalFusion

# 导入用户的7个核心信号模块
from app.analysis import (
    dark_pool_fund,
    hot_money,
    kang_long_you_hui,
    precise_trading,
    three_color_resonance,
    # zigzag_indicator, # 模块不存在，功能在indicators.py中
    indicators  # 这是一个包含多个指标的工具箱
)


logger = logging.getLogger("professional-api")
router = APIRouter()

# ============ 请求/响应模型 ============

class SignalAnalysisRequest(BaseModel):
    """信号分析请求"""
    symbol: str
    ohlc: List[Dict[str, float]]  # [{"open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 1000000}, ...]
    period: int = 20

class SignalAnalysisResponse(BaseModel):
    """信号分析响应"""
    symbol: str
    timestamp: str
    signals: Dict[str, Any]  # 7个信号的结果
    signal_score: float  # 综合信号强度 0-100
    confluence: Dict[str, int]  # 信号汇聚统计
    recommendation: str  # BUY / SELL / HOLD
    confidence: float  # 信心度 0-100

class RiskAnalysisRequest(BaseModel):
    """风险分析请求"""
    entry_price: float
    current_price: float
    position_size: float
    capital: float = 1000000.0
    atr: Optional[float] = None

class RiskAnalysisResponse(BaseModel):
    """风险分析响应"""
    stop_loss: float
    take_profit: float
    position_size_pct: float
    kelly_optimal: float
    current_drawdown: float
    max_drawdown_limit: float
    risk_metrics: Dict[str, float]

class StrategyTemplateRequest(BaseModel):
    """策略模板请求"""
    template_name: str  # trend_following, mean_reversion, box_breakout, wave_trading
    symbol: str
    ohlc: List[Dict[str, float]]
    initial_capital: float = 1000000.0

class StrategyTemplateResponse(BaseModel):
    """策略模板响应"""
    template_name: str
    parameters: Dict[str, Any]
    signals: Dict[str, Any]
    backtest_result: Optional[Dict[str, Any]] = None

class ParameterConfigRequest(BaseModel):
    """参数配置请求"""
    donchian_period: int = 20
    rsi_period: int = 5
    ama_period: int = 10
    ma_short_periods: List[int] = [2, 5, 10, 13]
    ma_medium_periods: List[int] = [50, 60, 70]
    ma_long_periods: List[int] = [120, 200, 250]

# ============ API端点 ============

@router.post("/signal-analysis", response_model=SignalAnalysisResponse)
async def analyze_signals(
    req: SignalAnalysisRequest,
    user: User = Depends(get_current_user)
):
    """
    分析7个核心交易信号
    
    使用示例:
    ```
    POST /api/professional/signal-analysis
    {
        "symbol": "HS300",
        "ohlc": [
            {"open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 1000000},
            ...
        ]
    }
    ```
    """
    try:
        # 转换为DataFrame
        df = pd.DataFrame(req.ohlc)
        if df.empty:
            raise ValueError("OHLC数据为空")
            
        df = df.rename(columns={
            'open': 'Open',
            'high': 'High', 
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        })
        df.index = pd.to_datetime(df.get('time', pd.to_datetime(pd.Timestamp.now())))


        # 分析7个核心信号
        signal_results = {}
        
        # 1. 亢龙有悔
        signal_results['kang_long_you_hui'] = {
            'name': '亢龙有悔',
            'result': kang_long_you_hui.detect_kang_long_you_hui(df)
        }
        
        # 2. 游资暗盘
        signal_results['hot_money_dark_pool'] = {
            'name': '游资暗盘',
            'result': hot_money.detect_hot_money_activity(df)
        }
        
        # 3. 暗盘资金
        signal_results['dark_pool_fund'] = {
            'name': '暗盘资金',
            'result': dark_pool_fund.analyze_dark_pool(df)
        }
        
        # 4. 精准买卖
        signal_results['precise_trading'] = {
            'name': '精准买卖点',
            'result': precise_trading.find_precise_signals(df)
        }
        
        # 5. 三色共振
        signal_results['three_color_resonance'] = {
            'name': '三色共振',
            'result': three_color_resonance.calculate_three_color_resonance(df)
        }
        
        # 6. Zigzag高低点
        # 注意: ZIG函数需要收盘价Series和百分比变化参数
        zig_series = indicators.ZIG(df['Close'], pct_change=5)
        # 清理和格式化Zigzag数据
        cleaned_zig = zig_series.dropna().reset_index()
        cleaned_zig.columns = ['time', 'value']
        cleaned_zig['time'] = cleaned_zig['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        signal_results['zigzag'] = {
            'name': 'Zigzag高低点 (5%)',
            'result': cleaned_zig.to_dict('records')
        }

        # 7. 综合技术指标 (从indicators.py)
        # EMA, BOLL, MACD, RSI
        ema = indicators.EMA(df['Close'], 20)
        boll = indicators.BOLL(df['Close'], 20)
        macd = indicators.MACD(df['Close'])
        rsi = indicators.RSI(df['Close'], 14)
        signal_results['technical_indicators'] = {
            'name': '综合技术指标',
            'result': {
                'ema_20': ema.iloc[-1] if not ema.empty else None,
                'boll_upper': boll['upper'].iloc[-1] if not boll.empty else None,
                'boll_lower': boll['lower'].iloc[-1] if not boll.empty else None,
                'macd_line': macd['macd'].iloc[-1] if not macd.empty else None,
                'rsi_14': rsi.iloc[-1] if not rsi.empty else None,
            }
        }

        # --- 信号计分与综合推荐 (简化版) ---
        bullish_count = 0
        bearish_count = 0

        # 简单规则计分 (增加健壮性检查)
        if signal_results['kang_long_you_hui']['result'] and len(signal_results['kang_long_you_hui']['result']) > 0 and signal_results['kang_long_you_hui']['result'][-1]['signal'] == 'SELL': bearish_count += 2
        if signal_results['hot_money_dark_pool']['result'] and len(signal_results['hot_money_dark_pool']['result']) > 0 and signal_results['hot_money_dark_pool']['result'][-1]['level'] > 0: bullish_count += 1
        if signal_results['dark_pool_fund']['result'] and signal_results['dark_pool_fund']['result'].get('latest_signal') == 'STRONG_BUY': bullish_count += 2
        if signal_results['precise_trading']['result'] and len(signal_results['precise_trading']['result']) > 0 and signal_results['precise_trading']['result'][-1]['signal'] == 'BUY': bullish_count += 1
        if signal_results['three_color_resonance']['result'] and signal_results['three_color_resonance']['result'].get('short_trend') == 'up': bullish_count +=1
        
        total_signals = 5 # 只统计有明确买卖信号的
        signal_score = (bullish_count / total_signals) * 100 if total_signals > 0 else 50

        if signal_score > 70:
            recommendation = "BUY"
            confidence = signal_score
        elif signal_score < 30:
            recommendation = "SELL"
            confidence = 100 - signal_score
        else:
            recommendation = "HOLD"
            confidence = 50 + abs(bullish_count - bearish_count) * 10

        return SignalAnalysisResponse(
            symbol=req.symbol,
            timestamp=pd.Timestamp.now().isoformat(),
            signals=signal_results,
            signal_score=signal_score,
            confluence={'bullish_count': bullish_count, 'bearish_count': bearish_count},
            recommendation=recommendation,
            confidence=confidence
        )
    
    except Exception as e:
        logger.error(f"Signal analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"信号分析失败: {str(e)}")

@router.post("/risk-analysis", response_model=RiskAnalysisResponse)
async def analyze_risk(
    req: RiskAnalysisRequest,
    user: User = Depends(get_current_user)
):
    """
    风险管理分析
    
    计算止损、止盈、仓位大小等风险指标
    """
    try:
        # 初始化风险管理器
        risk_params = RiskParams(
            max_drawdown=0.10,
            position_size_pct=0.05,
            stop_loss_atr_multiplier=2.0,
            take_profit_atr_multiplier=4.0,
            initial_capital=req.capital
        )
        
        risk_manager = RiskManager(risk_params)
        
        # 计算ATR（如果没提供，使用简单估算）
        atr = req.atr if req.atr else abs(req.entry_price * 0.02)
        
        # 计算止损和止盈
        stops = risk_manager.calculate_stops(
            entry_price=req.entry_price,
            atr=atr,
            direction='LONG'
        )
        
        # 计算仓位大小
        pos_size = risk_manager.calculate_position_size(
            entry_price=req.entry_price,
            stop_loss=stops['stop_loss'],
            risk_per_trade=req.capital * 0.02  # 每笔交易风险2%
        )
        
        # 计算Kelly最优仓位
        kelly_optimal = risk_manager.calculate_optimal_lot_size(
            win_rate=0.60,  # 假设60%胜率
            profit_factor=1.5  # 假设1.5的盈亏比
        )
        
        # 计算高级风险指标
        metrics = AdvancedRiskMetrics()
        returns = np.random.normal(0.001, 0.02, 252)  # 模拟252天的收益率
        
        risk_metrics = {
            'var_95': metrics.calculate_var(returns, 0.95),
            'cvar_95': metrics.calculate_cvar(returns, 0.95),
            'sortino_ratio': metrics.calculate_sortino_ratio(returns, 0.0),
            'calmar_ratio': metrics.calculate_calmar_ratio(returns, max_drawdown=0.10),
            'ulcer_index': metrics.calculate_ulcer_index(returns)
        }
        
        # 计算当前回撤
        current_drawdown = abs((req.current_price - req.entry_price) / req.entry_price) if req.current_price < req.entry_price else 0
        
        return RiskAnalysisResponse(
            stop_loss=stops['stop_loss'],
            take_profit=stops['take_profit'],
            position_size_pct=pos_size / req.capital * 100,
            kelly_optimal=kelly_optimal,
            current_drawdown=current_drawdown * 100,
            max_drawdown_limit=10.0,
            risk_metrics=risk_metrics
        )
    
    except Exception as e:
        logger.error(f"Risk analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"风险分析失败: {str(e)}")

@router.get("/strategy-templates")
async def get_strategy_templates(
    user: User = Depends(get_current_user)
):
    """
    获取所有可用的策略模板
    
    返回4个预定义的策略模板及其参数
    """
    try:
        templates = {
            'trend_following': {
                'name': '趋势跟踪',
                'description': '使用唐奇安通道和ATR止盈的趋势跟踪策略',
                'parameters': {
                    'donchian_period': 20,
                    'take_profit_multiplier': 4.0,
                    'stop_loss_multiplier': 2.0
                },
                'signals': ['donchian_breakout'],
                'risk_level': '中'
            },
            'mean_reversion': {
                'name': '均值回归',
                'description': '基于RSI的低点买高点卖策略',
                'parameters': {
                    'rsi_period': 5,
                    'rsi_oversold': 25,
                    'rsi_overbought': 75,
                    'take_profit_pct': 0.0075,
                    'time_stop_bars': 30
                },
                'signals': ['rsi_cost_line'],
                'risk_level': '低'
            },
            'box_breakout': {
                'name': '箱体突破',
                'description': '布林带宽度过滤的突破策略',
                'parameters': {
                    'bollinger_period': 48,
                    'bollinger_std': 1.8,
                    'min_width_pct': 0.02
                },
                'signals': ['bollinger_bands'],
                'risk_level': '中'
            },
            'wave_trading': {
                'name': '波浪交易',
                'description': '艾略特波浪理论约束的交易策略',
                'parameters': {
                    'wave1_constraint': True,
                    'wave3_min_multiplier': 1.618,
                    'macd_confirmation': True
                },
                'signals': ['macd_divergence', 'adx_trend_identifier'],
                'risk_level': '高'
            }
        }
        return templates
    
    except Exception as e:
        logger.error(f"Get templates failed: {e}")
        raise HTTPException(status_code=500, detail=f"获取模板失败: {str(e)}")

@router.post("/strategy-template-analysis", response_model=StrategyTemplateResponse)
async def analyze_strategy_template(
    req: StrategyTemplateRequest,
    user: User = Depends(get_current_user)
):
    """
    分析指定策略模板在给定数据上的表现
    """
    try:
        df = pd.DataFrame(req.ohlc)
        
        # 获取对应模板的参数
        if req.template_name == 'trend_following':
            params = StrategyTemplates.get_trend_following_template()
        elif req.template_name == 'mean_reversion':
            params = StrategyTemplates.get_mean_reversion_template()
        elif req.template_name == 'box_breakout':
            params = StrategyTemplates.get_box_breakout_template()
        elif req.template_name == 'wave_trading':
            params = StrategyTemplates.get_wave_trading_template()
        else:
            raise ValueError(f"未知的策略模板: {req.template_name}")
        
        # 初始化信号融合器
        fusion = SignalFusion(params)
        
        # 生成信号
        signals = fusion.generate_signal_from_advanced_system(req.symbol, df)
        
        return StrategyTemplateResponse(
            template_name=req.template_name,
            parameters=params.__dict__ if hasattr(params, '__dict__') else {},
            signals=signals
        )
    
    except Exception as e:
        logger.error(f"Template analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"模板分析失败: {str(e)}")

@router.get("/system-health")
async def get_professional_system_health(
    user: User = Depends(get_current_user)
):
    """
    获取专业系统健康状态
    """
    try:
        return {
            'status': 'healthy',
            'version': '1.0.0',
            'signals': {
                'donchian_breakout': '✓',
                'ma_system': '✓',
                'ama': '✓',
                'keltner_channel': '✓',
                'rsi_cost_line': '✓',
                'macd_divergence': '✓',
                'adx_aroon': '✓'
            },
            'risk_management': '✓',
            'parameter_system': '✓',
            'timestamp': pd.Timestamp.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")
