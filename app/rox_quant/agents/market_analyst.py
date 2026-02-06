"""
MarketAnalyst - 市场分析师 Agent
负责分析大盘环境、板块轮动、市场情绪
"""

import logging
from typing import Dict, Any, List
import pandas as pd

from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class MarketAnalyst(BaseAgent):
    """市场分析师 Agent"""
    
    def __init__(self):
        super().__init__(
            name="MarketAnalyst",
            role="市场分析师，专注于大盘环境、板块轮动和市场情绪分析",
            timeout=20.0
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
        """执行市场分析"""
        stock_code = context.get("stock_code", "")
        
        try:
            # 获取市场数据
            indices = await self._get_indices()
            market_stats = await self._get_market_stats()
            sector_info = await self._get_sector_info(stock_code)
            
            # 计算市场评分
            score = self._calculate_market_score(indices, market_stats)
            
            # 确定市场信号
            signal = self._determine_signal(score, indices)
            
            # 生成摘要
            summary = self._generate_summary(indices, market_stats, sector_info)
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                score=score,
                signal=signal,
                confidence=0.7,
                summary=summary,
                details={
                    "indices": indices,
                    "market_stats": market_stats,
                    "sector": sector_info,
                }
            )
            
        except Exception as e:
            logger.error(f"MarketAnalyst 分析失败: {e}")
            return AgentResult(
                agent_name=self.name,
                success=False,
                error=str(e)
            )
    
    async def _get_indices(self) -> Dict[str, Any]:
        """获取主要指数数据"""
        try:
            indices_data = self.data_provider.get_indices()
            if indices_data:
                return indices_data
        except Exception as e:
            logger.warning(f"获取指数数据失败: {e}")
        
        # 返回默认值
        return {
            "sh": {"name": "上证指数", "price": 0, "pct_change": 0},
            "sz": {"name": "深证成指", "price": 0, "pct_change": 0},
            "cyb": {"name": "创业板指", "price": 0, "pct_change": 0},
        }
    
    async def _get_market_stats(self) -> Dict[str, Any]:
        """获取市场统计数据"""
        try:
            stats = self.data_provider.get_market_stats()
            if stats:
                return stats
        except Exception as e:
            logger.warning(f"获取市场统计失败: {e}")
        
        return {
            "up_count": 0,
            "down_count": 0,
            "limit_up": 0,
            "limit_down": 0,
        }
    
    async def _get_sector_info(self, stock_code: str) -> Dict[str, Any]:
        """获取个股所属板块信息"""
        try:
            # 尝试获取板块信息
            sector = self.data_provider.get_stock_sector(stock_code)
            return sector or {"name": "未知", "pct_change": 0}
        except Exception as e:
            logger.warning(f"获取板块信息失败: {e}")
            return {"name": "未知", "pct_change": 0}
    
    def _calculate_market_score(self, indices: Dict, stats: Dict) -> float:
        """计算市场综合评分"""
        score = 50.0  # 基础分
        
        # 指数涨跌幅贡献
        for key in ['sh', 'sz', 'cyb']:
            idx = indices.get(key, {})
            pct = idx.get('pct_change', 0) or 0
            score += pct * 5  # 每涨 1% 加 5 分
        
        # 涨跌家数贡献
        up = stats.get('up_count', 0) or 0
        down = stats.get('down_count', 0) or 0
        if up + down > 0:
            up_ratio = up / (up + down)
            score += (up_ratio - 0.5) * 30  # 涨跌比影响
        
        # 涨停跌停贡献
        limit_up = stats.get('limit_up', 0) or 0
        limit_down = stats.get('limit_down', 0) or 0
        score += limit_up * 0.5 - limit_down * 0.5
        
        return max(0, min(100, score))
    
    def _determine_signal(self, score: float, indices: Dict) -> str:
        """确定市场信号"""
        if score >= 65:
            return "bullish"
        elif score <= 35:
            return "bearish"
        return "neutral"
    
    def _generate_summary(self, indices: Dict, stats: Dict, sector: Dict) -> str:
        """生成市场分析摘要"""
        # 指数表现
        sh = indices.get('sh', {})
        sh_pct = sh.get('pct_change', 0) or 0
        
        if sh_pct > 1:
            market_desc = "大盘强势上涨"
        elif sh_pct > 0:
            market_desc = "大盘小幅上涨"
        elif sh_pct > -1:
            market_desc = "大盘小幅下跌"
        else:
            market_desc = "大盘明显下跌"
        
        # 涨跌家数
        up = stats.get('up_count', 0) or 0
        down = stats.get('down_count', 0) or 0
        
        if up > down * 2:
            breadth = "市场人气高涨"
        elif up > down:
            breadth = "市场情绪偏暖"
        elif down > up * 2:
            breadth = "市场情绪低迷"
        else:
            breadth = "市场情绪一般"
        
        # 板块
        sector_name = sector.get('name', '未知')
        sector_pct = sector.get('pct_change', 0) or 0
        sector_desc = f"所属{sector_name}板块{'上涨' if sector_pct > 0 else '下跌'}{abs(sector_pct):.1f}%"
        
        return f"{market_desc}，{breadth}。{sector_desc}。"
