"""
RiskAnalyst - 风控分析师 Agent
负责风险评估、止损建议、仓位控制
复用现有 RiskManager 模块
"""

import logging
from typing import Dict, Any

from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class RiskAnalyst(BaseAgent):
    """风控分析师 Agent"""
    
    def __init__(self):
        super().__init__(
            name="RiskAnalyst",
            role="风控分析师，专注于风险评估、止损建议和仓位控制",
            timeout=20.0
        )
        self._risk_manager = None
        self._data_provider = None
    
    @property
    def risk_manager(self):
        """懒加载 RiskManager"""
        if self._risk_manager is None:
            from app.rox_quant.risk_management_advanced import RiskManager
            self._risk_manager = RiskManager()
        return self._risk_manager
    
    @property
    def data_provider(self):
        """懒加载 DataProvider"""
        if self._data_provider is None:
            from app.rox_quant.data_provider import DataProvider
            self._data_provider = DataProvider()
        return self._data_provider
    
    async def analyze(self, context: Dict[str, Any]) -> AgentResult:
        """执行风险分析"""
        stock_code = context.get("stock_code", "")
        stock_name = context.get("stock_name", stock_code)
        
        try:
            # 获取价格数据计算波动率
            volatility_data = await self._calculate_volatility(stock_code)
            
            # 计算风险指标
            risk_metrics = self._calculate_risk_metrics(volatility_data)
            
            # 生成仓位建议
            position_advice = self._get_position_advice(risk_metrics)
            
            # 计算风险评分 (高分表示低风险)
            score = self._calculate_risk_score(risk_metrics)
            
            # 确定信号
            signal = self._determine_signal(risk_metrics)
            
            # 生成摘要
            summary = self._generate_summary(stock_name, risk_metrics, position_advice)
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                score=score,
                signal=signal,
                confidence=0.7,
                summary=summary,
                details={
                    "volatility": volatility_data,
                    "risk_metrics": risk_metrics,
                    "position_advice": position_advice,
                }
            )
            
        except Exception as e:
            logger.error(f"RiskAnalyst 分析失败: {e}")
            return AgentResult(
                agent_name=self.name,
                success=False,
                error=str(e)
            )
    
    async def _calculate_volatility(self, stock_code: str) -> Dict[str, float]:
        """计算波动率数据"""
        try:
            # 格式化股票代码
            symbol = stock_code
            if not stock_code.startswith(('sh', 'sz', 'SH', 'SZ')):
                if stock_code.startswith('6'):
                    symbol = f"sh{stock_code}"
                else:
                    symbol = f"sz{stock_code}"
            
            df = self.data_provider.get_kline(symbol, period="daily", count=60)
            
            if df is None or df.empty:
                return {"volatility_20": 0.02, "atr": 0, "max_drawdown": 0}
            
            import numpy as np
            
            # 计算日收益率
            returns = df['close'].pct_change().dropna()
            
            # 20日波动率
            volatility_20 = float(returns.tail(20).std() * np.sqrt(252)) if len(returns) >= 20 else 0.3
            
            # ATR
            if 'high' in df.columns and 'low' in df.columns:
                tr = df['high'] - df['low']
                atr = float(tr.tail(14).mean())
            else:
                atr = float(df['close'].tail(14).std())
            
            # 最大回撤
            cummax = df['close'].cummax()
            drawdown = (df['close'] - cummax) / cummax
            max_drawdown = float(abs(drawdown.min()))
            
            return {
                "volatility_20": volatility_20,
                "atr": atr,
                "max_drawdown": max_drawdown,
                "recent_return": float(returns.tail(5).sum()) if len(returns) >= 5 else 0,
            }
            
        except Exception as e:
            logger.warning(f"计算波动率失败: {e}")
            return {"volatility_20": 0.3, "atr": 0, "max_drawdown": 0.1}
    
    def _calculate_risk_metrics(self, volatility: Dict) -> Dict[str, Any]:
        """计算风险指标"""
        vol = volatility.get('volatility_20', 0.3)
        max_dd = volatility.get('max_drawdown', 0.1)
        
        # 风险等级
        if vol > 0.5 or max_dd > 0.3:
            risk_level = "high"
        elif vol > 0.3 or max_dd > 0.15:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # VaR 估算 (95% 单日)
        var_95 = vol / 16  # 简化计算
        
        return {
            "risk_level": risk_level,
            "var_95": var_95,
            "volatility": vol,
            "max_drawdown": max_dd,
        }
    
    def _get_position_advice(self, risk_metrics: Dict) -> Dict[str, Any]:
        """生成仓位建议"""
        risk_level = risk_metrics.get('risk_level', 'medium')
        
        position_map = {
            "low": {"max_position": 0.5, "suggested": 0.3, "stop_loss_pct": 0.05},
            "medium": {"max_position": 0.3, "suggested": 0.2, "stop_loss_pct": 0.08},
            "high": {"max_position": 0.15, "suggested": 0.1, "stop_loss_pct": 0.10},
        }
        
        return position_map.get(risk_level, position_map["medium"])
    
    def _calculate_risk_score(self, risk_metrics: Dict) -> float:
        """计算风险评分（高分=低风险）"""
        risk_level = risk_metrics.get('risk_level', 'medium')
        
        score_map = {"low": 80, "medium": 55, "high": 30}
        base_score = score_map.get(risk_level, 50)
        
        # 根据波动率微调
        vol = risk_metrics.get('volatility', 0.3)
        if vol < 0.2:
            base_score += 10
        elif vol > 0.4:
            base_score -= 10
        
        return max(0, min(100, base_score))
    
    def _determine_signal(self, risk_metrics: Dict) -> str:
        """确定风险信号"""
        risk_level = risk_metrics.get('risk_level', 'medium')
        
        if risk_level == "low":
            return "bullish"  # 低风险可以做多
        elif risk_level == "high":
            return "bearish"  # 高风险谨慎
        return "neutral"
    
    def _generate_summary(self, stock_name: str, metrics: Dict, advice: Dict) -> str:
        """生成风险摘要"""
        risk_level = metrics.get('risk_level', 'medium')
        risk_text = {"low": "低风险", "medium": "中等风险", "high": "高风险"}.get(risk_level, "中等风险")
        
        vol = metrics.get('volatility', 0.3) * 100
        suggested = advice.get('suggested', 0.2) * 100
        stop_loss = advice.get('stop_loss_pct', 0.08) * 100
        
        return f"{stock_name}{risk_text}，年化波动率{vol:.1f}%。建议仓位{suggested:.0f}%，止损{stop_loss:.0f}%。"
