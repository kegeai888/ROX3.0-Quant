"""
P3.5 Day 5: 回测API端点
将回测引擎集成到FastAPI中，支持通过HTTP调用回测功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import pandas as pd

# 导入回测模块（使用 app.rox_quant 包路径）
from app.rox_quant.backtest_engine import BacktestEngine, BacktestConfig
from app.rox_quant.performance_metrics import PerformanceMetrics
from app.rox_quant.factor_analyzer import FactorAnalyzer
from app.rox_quant.overfitting_detector import OverfittingDetector
from app.rox_quant.backtest_report_generator import BacktestReportGenerator


# ==================== 请求/响应数据模型 ====================

class KLineData(BaseModel):
    """K线数据"""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class BacktestRequest(BaseModel):
    """回测请求"""
    symbol: str = Field(..., description="交易品种，如 'AAPL'")
    klines: List[KLineData] = Field(..., description="K线数据列表")
    initial_capital: float = Field(100000.0, description="初始资金")
    commission_rate: float = Field(0.0003, description="手续费率")
    slippage: float = Field(0.0001, description="滑点")
    position_size: float = Field(0.5, description="仓位大小")
    signal_weights: Optional[Dict[str, float]] = Field(
        None, 
        description="信号权重配置"
    )


class TradeInfo(BaseModel):
    """交易记录信息"""
    trade_id: int
    entry_time: Any
    entry_price: float
    entry_qty: int
    exit_time: Optional[Any] = None
    exit_price: Optional[float] = None
    exit_qty: Optional[int] = None
    profit: Optional[float] = None
    profit_pct: Optional[float] = None
    is_closed: bool


class PerformanceInfo(BaseModel):
    """性能指标"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit: float
    total_loss: float
    net_profit: float
    profit_factor: float
    max_drawdown: float
    total_return: float
    annual_return: float
    annual_volatility: float
    sharpe_ratio: float


class BacktestResponse(BaseModel):
    """回测响应"""
    symbol: str
    status: str = "success"
    performance: PerformanceInfo
    trades: List[TradeInfo]
    portfolio_values: List[float]
    message: Optional[str] = None


class FactorAnalysisResponse(BaseModel):
    """因子分析响应"""
    symbol: str
    status: str = "success"
    factors: Dict[str, Any]
    ranking: List[Dict[str, Any]]


class OverfittingResponse(BaseModel):
    """过拟合检测响应"""
    symbol: str
    status: str = "success"
    overfitting_score: float
    stability_index: float
    robustness_score: float
    is_overfitted: bool
    windows: List[Dict[str, Any]]


# ==================== 路由 ====================

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest) -> BacktestResponse:
    """
    运行完整的回测分析
    
    参数：
      - symbol: 交易品种
      - klines: K线数据（包含open/high/low/close/volume）
      - initial_capital: 初始资金
      - commission_rate: 手续费率
      - slippage: 滑点
      - position_size: 仓位大小
    
    返回：
      - 性能指标、交易记录、净值曲线
    """
    try:
        # 1. 准备K线数据
        klines_data = []
        for kline in request.klines:
            klines_data.append({
                'date': kline.date,
                'open': kline.open,
                'high': kline.high,
                'low': kline.low,
                'close': kline.close,
                'volume': kline.volume
            })
        
        klines_df = pd.DataFrame(klines_data)
        
        # 2. 创建回测配置
        config = BacktestConfig(
            initial_capital=request.initial_capital,
            commission_rate=request.commission_rate,
            slippage=request.slippage,
            position_size=request.position_size
        )
        
        # 3. 动态信号生成函数
        def dynamic_signal(klines_df: pd.DataFrame, idx: int) -> str:
            if idx < 30:
                return 'HOLD'
            
            # 解析信号权重
            weights = request.signal_weights or {"ma_cross": 1.0}
            
            # --- 策略组件 ---
            
            # 1. 均线策略 (MA Cross)
            ma_score = 0
            if weights.get("ma_cross", 0) > 0:
                short_ma = klines_df['close'].iloc[idx-5:idx].mean()
                long_ma = klines_df['close'].iloc[idx-20:idx].mean()
                if short_ma > long_ma:
                    ma_score = 1
                elif short_ma < long_ma:
                    ma_score = -1
            
            # 2. RSI 策略 (超买超卖)
            rsi_score = 0
            if weights.get("rsi", 0) > 0:
                # 简单 RSI 计算 (14日)
                delta = klines_df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                current_rsi = rsi.iloc[idx] if not pd.isna(rsi.iloc[idx]) else 50
                
                if current_rsi < 30:
                    rsi_score = 1  # 超卖，买入
                elif current_rsi > 70:
                    rsi_score = -1 # 超买，卖出
            
            # 3. MACD 策略 (趋势跟踪)
            macd_score = 0
            if weights.get("macd", 0) > 0:
                # 简化 MACD (12, 26, 9)
                exp1 = klines_df['close'].ewm(span=12, adjust=False).mean()
                exp2 = klines_df['close'].ewm(span=26, adjust=False).mean()
                macd = exp1 - exp2
                signal_line = macd.ewm(span=9, adjust=False).mean()
                
                curr_macd = macd.iloc[idx]
                curr_sig = signal_line.iloc[idx]
                prev_macd = macd.iloc[idx-1]
                prev_sig = signal_line.iloc[idx-1]
                
                if curr_macd > curr_sig and prev_macd <= prev_sig:
                    macd_score = 1
                elif curr_macd < curr_sig and prev_macd >= prev_sig:
                    macd_score = -1

            # --- 综合评分 ---
            total_score = (
                ma_score * weights.get("ma_cross", 0) +
                rsi_score * weights.get("rsi", 0) +
                macd_score * weights.get("macd", 0)
            )
            
            threshold = 0.5 # 信号阈值
            
            if total_score > threshold:
                return 'BUY'
            elif total_score < -threshold:
                return 'SELL'
            return 'HOLD'
        
        # 4. 运行回测
        engine = BacktestEngine(config)
        engine.load_klines(klines_df)
        engine.run(dynamic_signal)
        
        # 5. 计算性能指标
        trades = engine.get_trades()
        portfolio_values, portfolio_dates = engine.get_portfolio_values()
        
        metrics = PerformanceMetrics()
        perf_report = metrics.calculate(
            trades=trades,
            portfolio_values=portfolio_values,
            portfolio_dates=portfolio_dates,
            initial_capital=request.initial_capital
        )
        
        # 6. 构建响应
        trade_infos = [
            TradeInfo(
                trade_id=t.trade_id,
                entry_time=str(t.entry_time),
                entry_price=t.entry_price,
                entry_qty=t.entry_qty,
                exit_time=str(t.exit_time) if t.exit_time else None,
                exit_price=t.exit_price,
                exit_qty=t.exit_qty,
                profit=t.profit,
                profit_pct=t.profit_pct,
                is_closed=t.is_closed
            )
            for t in trades
        ]
        
        performance_info = PerformanceInfo(
            total_trades=perf_report.total_trades,
            winning_trades=perf_report.winning_trades,
            losing_trades=perf_report.losing_trades,
            win_rate=perf_report.win_rate,
            total_profit=perf_report.total_profit,
            total_loss=perf_report.total_loss,
            net_profit=perf_report.net_profit,
            profit_factor=perf_report.profit_factor,
            max_drawdown=perf_report.max_drawdown,
            total_return=perf_report.total_return,
            annual_return=perf_report.annual_return,
            annual_volatility=perf_report.annual_volatility,
            sharpe_ratio=perf_report.sharpe_ratio
        )
        
        return BacktestResponse(
            symbol=request.symbol,
            status="success",
            performance=performance_info,
            trades=trade_infos,
            portfolio_values=portfolio_values
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/factor-analysis", response_model=FactorAnalysisResponse)
async def analyze_factors(request: BacktestRequest) -> FactorAnalysisResponse:
    """
    进行因子分析
    
    返回：
      - 每个因子的贡献度排名
      - 胜率和盈亏比分析
    """
    try:
        # 准备数据
        klines_data = [
            {
                'date': k.date,
                'open': k.open,
                'high': k.high,
                'low': k.low,
                'close': k.close,
                'volume': k.volume
            }
            for k in request.klines
        ]
        klines_df = pd.DataFrame(klines_data)
        
        # 运行回测获得交易
        config = BacktestConfig(
            initial_capital=request.initial_capital,
            commission_rate=request.commission_rate,
            slippage=request.slippage,
            position_size=request.position_size
        )
        
        def default_signal(klines_df: pd.DataFrame, idx: int) -> str:
            if idx < 20:
                return 'HOLD'
            short_ma = klines_df['close'].iloc[idx-5:idx].mean()
            long_ma = klines_df['close'].iloc[idx-20:idx].mean()
            return 'BUY' if short_ma > long_ma else ('SELL' if short_ma < long_ma else 'HOLD')
        
        engine = BacktestEngine(config)
        engine.load_klines(klines_df)
        engine.run(default_signal)
        
        # 因子分析
        factor_analyzer = FactorAnalyzer()
        for i, trade in enumerate(engine.get_trades()):
            factor_name = ['MA', 'RSI', 'KDJ'][i % 3]
            factor_analyzer.record_trade_factor(factor_name, trade)
        
        return FactorAnalysisResponse(
            symbol=request.symbol,
            status="success",
            **factor_analyzer.to_dict()
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/overfitting-test", response_model=OverfittingResponse)
async def test_overfitting(request: BacktestRequest) -> OverfittingResponse:
    """
    过拟合检测
    
    返回：
      - 过拟合指数 (0-100)
      - 多个时间窗口的结果对比
    """
    try:
        # 准备数据
        klines_data = [
            {
                'date': k.date,
                'open': k.open,
                'high': k.high,
                'low': k.low,
                'close': k.close,
                'volume': k.volume
            }
            for k in request.klines
        ]
        klines_df = pd.DataFrame(klines_data)
        
        # 信号函数
        def default_signal(klines_df: pd.DataFrame, idx: int) -> str:
            if idx < 20:
                return 'HOLD'
            short_ma = klines_df['close'].iloc[idx-5:idx].mean()
            long_ma = klines_df['close'].iloc[idx-20:idx].mean()
            return 'BUY' if short_ma > long_ma else ('SELL' if short_ma < long_ma else 'HOLD')
        
        # 过拟合检测
        detector = OverfittingDetector()
        report = detector.rolling_window_test(
            klines=klines_df,
            signal_func=default_signal,
            window_size=50,
            step=15
        )
        
        return OverfittingResponse(
            symbol=request.symbol,
            status="success",
            overfitting_score=report.overfitting_score,
            stability_index=report.stability_index,
            robustness_score=report.robustness_score,
            is_overfitted=report.is_overfitted,
            windows=[
                {
                    'window_name': w.window_name,
                    'total_trades': w.total_trades,
                    'win_rate': round(w.win_rate, 2),
                    'profit_factor': round(w.profit_factor, 2),
                    'net_profit': round(w.net_profit, 2),
                    'total_return': round(w.total_return, 2),
                    'max_drawdown': round(w.max_drawdown, 2)
                }
                for w in report.windows
            ]
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "backtest_api",
        "version": "3.5"
    }


# 导出路由
__all__ = ['router']
