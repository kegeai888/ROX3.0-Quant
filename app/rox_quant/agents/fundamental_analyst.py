"""
FundamentalAnalyst - 基本面分析师 Agent
负责财务数据、估值分析、行业对比
"""

import logging
from typing import Dict, Any

from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class FundamentalAnalyst(BaseAgent):
    """基本面分析师 Agent"""
    
    def __init__(self):
        super().__init__(
            name="FundamentalAnalyst",
            role="基本面分析师，专注于财务数据、估值分析和行业对比",
            timeout=25.0
        )
        self._data_provider = None
    
    @property
    def data_provider(self):
        """懒加载 DataProvider"""
        if self._data_provider is None:
            from app.rox_quant.data_provider import DataProvider
            self._data_provider = DataProvider()
        return self._data_provider
    
    async def analyze(self, context: Dict[str, Any]) -> AgentResult:
        """执行基本面分析"""
        stock_code = context.get("stock_code", "")
        stock_name = context.get("stock_name", stock_code)
        
        try:
            # 获取基本面数据
            fundamentals = await self._get_fundamentals(stock_code)
            
            if not fundamentals:
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    error="无法获取基本面数据"
                )
            
            # 计算基本面评分
            score = self._calculate_fundamental_score(fundamentals)
            
            # 确定信号
            signal = self._determine_signal(fundamentals)
            
            # 生成摘要
            summary = self._generate_summary(stock_name, fundamentals)
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                score=score,
                signal=signal,
                confidence=0.75,
                summary=summary,
                details=fundamentals
            )
            
        except Exception as e:
            logger.error(f"FundamentalAnalyst 分析失败: {e}")
            return AgentResult(
                agent_name=self.name,
                success=False,
                error=str(e)
            )
    
    async def _get_fundamentals(self, stock_code: str) -> Dict[str, Any]:
        """获取基本面数据"""
        try:
            # 尝试获取财务数据
            data = self.data_provider.get_stock_financials(stock_code)
            if data:
                return data
        except Exception as e:
            logger.warning(f"获取财务数据失败: {e}")
        
        # 尝试从股票信息获取
        try:
            info = self.data_provider.get_stock_info(stock_code)
            if info:
                return {
                    "pe": info.get("pe", None),
                    "pb": info.get("pb", None),
                    "roe": info.get("roe", None),
                    "market_cap": info.get("market_cap", None),
                    "revenue_growth": info.get("revenue_growth", None),
                    "net_profit_growth": info.get("net_profit_growth", None),
                }
        except Exception as e:
            logger.warning(f"获取股票信息失败: {e}")
        
        return {}
    
    def _calculate_fundamental_score(self, data: Dict) -> float:
        """计算基本面评分"""
        score = 50.0  # 基础分
        
        # PE 评分 (低 PE 加分)
        pe = data.get('pe')
        if pe is not None and pe > 0:
            if pe < 15:
                score += 15
            elif pe < 25:
                score += 10
            elif pe < 40:
                score += 0
            else:
                score -= 10
        
        # PB 评分 (低 PB 加分)
        pb = data.get('pb')
        if pb is not None and pb > 0:
            if pb < 1:
                score += 10
            elif pb < 2:
                score += 5
            elif pb < 5:
                score += 0
            else:
                score -= 5
        
        # ROE 评分 (高 ROE 加分)
        roe = data.get('roe')
        if roe is not None:
            if roe > 20:
                score += 15
            elif roe > 15:
                score += 10
            elif roe > 10:
                score += 5
            elif roe < 5:
                score -= 10
        
        # 营收增长评分
        rev_growth = data.get('revenue_growth')
        if rev_growth is not None:
            if rev_growth > 30:
                score += 10
            elif rev_growth > 15:
                score += 5
            elif rev_growth < 0:
                score -= 5
        
        # 净利润增长评分
        profit_growth = data.get('net_profit_growth')
        if profit_growth is not None:
            if profit_growth > 30:
                score += 10
            elif profit_growth > 15:
                score += 5
            elif profit_growth < 0:
                score -= 10
        
        return max(0, min(100, score))
    
    def _determine_signal(self, data: Dict) -> str:
        """确定基本面信号"""
        pe = data.get('pe')
        roe = data.get('roe')
        profit_growth = data.get('net_profit_growth')
        
        positive_factors = 0
        negative_factors = 0
        
        # PE
        if pe and pe > 0:
            if pe < 20:
                positive_factors += 1
            elif pe > 50:
                negative_factors += 1
        
        # ROE
        if roe:
            if roe > 15:
                positive_factors += 1
            elif roe < 5:
                negative_factors += 1
        
        # 利润增长
        if profit_growth:
            if profit_growth > 20:
                positive_factors += 1
            elif profit_growth < -10:
                negative_factors += 1
        
        if positive_factors > negative_factors:
            return "bullish"
        elif negative_factors > positive_factors:
            return "bearish"
        return "neutral"
    
    def _generate_summary(self, stock_name: str, data: Dict) -> str:
        """生成基本面摘要"""
        parts = [f"{stock_name}基本面分析："]
        
        pe = data.get('pe')
        if pe:
            pe_status = "低估" if pe < 20 else ("合理" if pe < 40 else "偏高")
            parts.append(f"PE {pe:.1f}({pe_status})")
        
        pb = data.get('pb')
        if pb:
            pb_status = "低估" if pb < 1.5 else ("合理" if pb < 3 else "偏高")
            parts.append(f"PB {pb:.2f}({pb_status})")
        
        roe = data.get('roe')
        if roe:
            roe_status = "优秀" if roe > 15 else ("良好" if roe > 10 else "一般")
            parts.append(f"ROE {roe:.1f}%({roe_status})")
        
        profit_growth = data.get('net_profit_growth')
        if profit_growth:
            growth_text = f"利润增长{profit_growth:+.1f}%"
            parts.append(growth_text)
        
        return "，".join(parts) + "。"
