"""
NewsAnalyst - 新闻分析师 Agent
负责新闻情绪、公告解读、舆情监控
"""

import logging
from typing import Dict, Any, List

from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class NewsAnalyst(BaseAgent):
    """新闻分析师 Agent"""
    
    def __init__(self):
        super().__init__(
            name="NewsAnalyst",
            role="新闻分析师，专注于新闻情绪分析、公告解读和舆情监控",
            timeout=30.0  # 新闻分析需要 LLM，给更多时间
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
        """执行新闻分析"""
        stock_code = context.get("stock_code", "")
        stock_name = context.get("stock_name", stock_code)
        
        try:
            # 获取新闻数据
            news_list = await self._get_news(stock_code, stock_name)
            
            if not news_list:
                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    score=50,
                    signal="neutral",
                    confidence=0.3,
                    summary=f"{stock_name}近期无重大新闻。",
                    details={"news_count": 0, "news": []}
                )
            
            # 分析新闻情绪
            sentiment_score, sentiment_signal = await self._analyze_sentiment(news_list, stock_name)
            
            # 生成摘要
            summary = self._generate_summary(stock_name, news_list, sentiment_score)
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                score=sentiment_score,
                signal=sentiment_signal,
                confidence=0.6,
                summary=summary,
                details={
                    "news_count": len(news_list),
                    "news": news_list[:5],  # 最多返回5条
                    "sentiment_score": sentiment_score,
                }
            )
            
        except Exception as e:
            logger.error(f"NewsAnalyst 分析失败: {e}")
            return AgentResult(
                agent_name=self.name,
                success=False,
                error=str(e)
            )
    
    async def _get_news(self, stock_code: str, stock_name: str) -> List[Dict]:
        """获取新闻数据"""
        try:
            news = self.data_provider.get_stock_news(stock_code, limit=10)
            if news:
                return news
        except Exception as e:
            logger.warning(f"获取股票新闻失败: {e}")
        
        # 尝试获取市场新闻
        try:
            market_news = self.data_provider.get_market_news(limit=5)
            return market_news or []
        except Exception as e:
            logger.warning(f"获取市场新闻失败: {e}")
        
        return []
    
    async def _analyze_sentiment(self, news_list: List[Dict], stock_name: str) -> tuple:
        """分析新闻情绪"""
        if not news_list:
            return 50, "neutral"
        
        # 简单关键词情绪分析
        positive_keywords = ['利好', '增长', '突破', '上涨', '盈利', '签约', '中标', '创新高', '业绩预增', '回购']
        negative_keywords = ['利空', '下跌', '亏损', '减持', '违规', '处罚', '下滑', '风险', '暴跌', '退市']
        
        positive_count = 0
        negative_count = 0
        
        for news in news_list:
            title = news.get('title', '') + news.get('content', '')
            for kw in positive_keywords:
                if kw in title:
                    positive_count += 1
            for kw in negative_keywords:
                if kw in title:
                    negative_count += 1
        
        # 计算情绪分数 (0-100)
        total = positive_count + negative_count
        if total == 0:
            return 50, "neutral"
        
        sentiment_ratio = positive_count / total
        score = 30 + sentiment_ratio * 40  # 范围 30-70
        
        # 调整基于新闻数量
        if len(news_list) >= 5:
            if positive_count > negative_count * 2:
                score += 15
            elif negative_count > positive_count * 2:
                score -= 15
        
        score = max(0, min(100, score))
        
        if score >= 60:
            signal = "bullish"
        elif score <= 40:
            signal = "bearish"
        else:
            signal = "neutral"
        
        return score, signal
    
    def _generate_summary(self, stock_name: str, news_list: List[Dict], score: float) -> str:
        """生成新闻摘要"""
        news_count = len(news_list)
        
        if score >= 65:
            sentiment_desc = "舆情偏正面"
        elif score <= 35:
            sentiment_desc = "舆情偏负面"
        else:
            sentiment_desc = "舆情中性"
        
        # 提取最新新闻标题
        if news_list:
            latest = news_list[0].get('title', '')[:30]
            return f"{stock_name}近期{news_count}条新闻，{sentiment_desc}。最新：{latest}..."
        
        return f"{stock_name}{sentiment_desc}，近期无重大消息。"
