"""
AgentOrchestrator - 多智能体协调器
负责并行调度所有分析 Agent 并收集结果
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from .base_agent import AgentResult
from .technical_analyst import TechnicalAnalyst
from .market_analyst import MarketAnalyst
from .fundamental_analyst import FundamentalAnalyst
from .news_analyst import NewsAnalyst
from .risk_analyst import RiskAnalyst
from .synthesizer import Synthesizer

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    多智能体协调器
    
    功能：
    1. 并行执行所有分析 Agent
    2. 收集和汇总结果
    3. 调用 Synthesizer 生成最终报告
    """
    
    def __init__(self):
        self.agents = {
            "technical": TechnicalAnalyst(),
            "market": MarketAnalyst(),
            "fundamental": FundamentalAnalyst(),
            "news": NewsAnalyst(),
            "risk": RiskAnalyst(),
        }
        self.synthesizer = Synthesizer()
    
    async def analyze_stock(self, stock_code: str, stock_name: str = "") -> Dict[str, Any]:
        """
        对单只股票进行多智能体分析
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称（可选）
            
        Returns:
            综合分析结果
        """
        context = {
            "stock_code": stock_code,
            "stock_name": stock_name or stock_code,
        }
        
        logger.info(f"开始多智能体分析: {stock_code} {stock_name}")
        
        # 并行执行所有 Agent
        tasks = {
            name: agent.safe_analyze(context) 
            for name, agent in self.agents.items()
        }
        
        # 等待所有任务完成
        results = {}
        task_items = list(tasks.items())
        task_futures = [task for _, task in task_items]
        
        completed = await asyncio.gather(*task_futures, return_exceptions=True)
        
        for (name, _), result in zip(task_items, completed):
            if isinstance(result, Exception):
                logger.error(f"Agent {name} 执行异常: {result}")
                results[name] = AgentResult(
                    agent_name=name,
                    success=False,
                    error=str(result)
                )
            else:
                results[name] = result
        
        # 综合分析
        final_result = await self.synthesizer.synthesize(results, context)
        
        logger.info(f"多智能体分析完成: {stock_code}, 评分: {final_result.get('final_score', 'N/A')}")
        
        return final_result
    
    async def analyze_batch(self, stocks: list, max_concurrent: int = 3) -> list:
        """
        批量分析多只股票
        
        Args:
            stocks: 股票列表 [{"code": "600519", "name": "贵州茅台"}, ...]
            max_concurrent: 最大并发数
            
        Returns:
            分析结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_limit(stock: dict):
            async with semaphore:
                return await self.analyze_stock(
                    stock.get("code", ""),
                    stock.get("name", "")
                )
        
        tasks = [analyze_with_limit(stock) for stock in stocks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for stock, result in zip(stocks, results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "stock_code": stock.get("code", ""),
                    "error": str(result),
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def analyze_single_agent(self, stock_code: str, agent_name: str, 
                                   stock_name: str = "") -> AgentResult:
        """
        使用单个 Agent 进行分析（用于调试或快速分析）
        
        Args:
            stock_code: 股票代码
            agent_name: Agent 名称 (technical, market, fundamental, news, risk)
            stock_name: 股票名称（可选）
            
        Returns:
            单个 Agent 的分析结果
        """
        agent = self.agents.get(agent_name)
        if not agent:
            return AgentResult(
                agent_name=agent_name,
                success=False,
                error=f"未知的 Agent: {agent_name}"
            )
        
        context = {
            "stock_code": stock_code,
            "stock_name": stock_name or stock_code,
        }
        
        return await agent.safe_analyze(context)
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取所有 Agent 的信息"""
        return {
            name: {
                "name": agent.name,
                "role": agent.role,
                "timeout": agent.timeout,
            }
            for name, agent in self.agents.items()
        }
