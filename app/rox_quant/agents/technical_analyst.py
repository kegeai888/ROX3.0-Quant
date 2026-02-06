"""
TechnicalAnalyst - 技术分析师 Agent
负责 K 线形态、技术指标、趋势判断
复用现有 SignalFusion 模块
"""

import logging
from typing import Dict, Any
import pandas as pd

from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class TechnicalAnalyst(BaseAgent):
    """技术分析师 Agent"""
    
    def __init__(self):
        super().__init__(
            name="TechnicalAnalyst",
            role="技术分析师，专注于 K 线形态、技术指标和趋势判断",
            timeout=25.0
        )
        self._signal_fusion = None
        self._data_provider = None
    
    @property
    def signal_fusion(self):
        """懒加载 SignalFusion"""
        if self._signal_fusion is None:
            from app.rox_quant.signal_fusion import SignalFusion
            self._signal_fusion = SignalFusion()
        return self._signal_fusion
    
    @property
    def data_provider(self):
        """懒加载 DataProvider"""
        if self._data_provider is None:
            from app.rox_quant.data_provider import DataProvider
            self._data_provider = DataProvider()
        return self._data_provider
    
    async def analyze(self, context: Dict[str, Any]) -> AgentResult:
        """执行技术分析"""
        stock_code = context.get("stock_code", "")
        stock_name = context.get("stock_name", stock_code)
        
        try:
            # 获取 OHLCV 数据
            ohlc = await self._get_ohlc_data(stock_code)
            if ohlc is None or ohlc.empty:
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    error="无法获取行情数据"
                )
            
            # 使用 SignalFusion 计算信号
            signal_result = self.signal_fusion.generate_signal_from_ohlc(stock_code, ohlc)
            
            # 计算综合评分
            score = self.signal_fusion.calculate_signal_score(ohlc)
            
            # 计算技术指标
            indicators = self._calculate_indicators(ohlc)
            
            # 确定信号方向
            signal_type = signal_result.signal_type if signal_result else None
            if signal_type:
                if signal_type.value >= 1:
                    signal = "bullish"
                elif signal_type.value <= -1:
                    signal = "bearish"
                else:
                    signal = "neutral"
            else:
                signal = "neutral"
            
            # 生成摘要
            summary = self._generate_summary(stock_name, score, signal, indicators)
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                score=score,
                signal=signal,
                confidence=min(score / 100, 1.0),
                summary=summary,
                details={
                    "indicators": indicators,
                    "signal_reason": signal_result.reason if signal_result else "",
                    "latest_close": float(ohlc['close'].iloc[-1]) if 'close' in ohlc.columns else None,
                }
            )
            
        except Exception as e:
            logger.error(f"TechnicalAnalyst 分析失败: {e}")
            return AgentResult(
                agent_name=self.name,
                success=False,
                error=str(e)
            )
    
    async def _get_ohlc_data(self, stock_code: str, days: int = 120) -> pd.DataFrame:
        """获取 OHLCV 数据"""
        try:
            # 格式化股票代码
            symbol = stock_code
            if not stock_code.startswith(('sh', 'sz', 'SH', 'SZ')):
                if stock_code.startswith('6'):
                    symbol = f"sh{stock_code}"
                else:
                    symbol = f"sz{stock_code}"
            
            df = self.data_provider.get_kline(symbol, period="daily", count=days)
            return df
        except Exception as e:
            logger.error(f"获取行情数据失败: {e}")
            return pd.DataFrame()
    
    def _calculate_indicators(self, ohlc: pd.DataFrame) -> Dict[str, Any]:
        """计算技术指标"""
        indicators = {}
        
        try:
            close = ohlc['close']
            
            # MACD
            macd_result = self.signal_fusion.calculate_macd(close)
            indicators['macd'] = {
                'macd': float(macd_result['macd'].iloc[-1]) if not macd_result['macd'].empty else 0,
                'signal': float(macd_result['signal'].iloc[-1]) if not macd_result['signal'].empty else 0,
                'histogram': float(macd_result['histogram'].iloc[-1]) if not macd_result['histogram'].empty else 0,
            }
            
            # RSI
            rsi = self.signal_fusion.calculate_rsi(close)
            indicators['rsi'] = float(rsi.iloc[-1]) if not rsi.empty else 50
            
            # MA
            ma_result = self.signal_fusion.calculate_moving_averages(close)
            indicators['ma5'] = float(ma_result['short_ma'].iloc[-1]) if not ma_result['short_ma'].empty else 0
            indicators['ma20'] = float(ma_result['long_ma'].iloc[-1]) if not ma_result['long_ma'].empty else 0
            
            # 布林带
            bb = self.signal_fusion.calculate_bollinger_bands(close)
            indicators['bollinger'] = {
                'upper': float(bb['upper'].iloc[-1]) if not bb['upper'].empty else 0,
                'middle': float(bb['middle'].iloc[-1]) if not bb['middle'].empty else 0,
                'lower': float(bb['lower'].iloc[-1]) if not bb['lower'].empty else 0,
            }
            
            # 趋势
            trend = self.signal_fusion.detect_trend(close)
            indicators['trend'] = trend
            
        except Exception as e:
            logger.warning(f"计算指标失败: {e}")
        
        return indicators
    
    def _generate_summary(self, stock_name: str, score: float, signal: str, indicators: Dict) -> str:
        """生成分析摘要"""
        signal_text = {"bullish": "看多", "bearish": "看空", "neutral": "中性"}.get(signal, "中性")
        
        rsi = indicators.get('rsi', 50)
        rsi_status = "超买" if rsi > 70 else ("超卖" if rsi < 30 else "正常")
        
        trend = indicators.get('trend', {})
        trend_text = "上升趋势" if trend.get('trend') == 'bullish' else (
            "下降趋势" if trend.get('trend') == 'bearish' else "震荡"
        )
        
        return f"{stock_name} 技术评分 {score:.0f}/100，{signal_text}。RSI {rsi:.1f}({rsi_status})，{trend_text}。"
