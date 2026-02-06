"""
BaseAgent - 多智能体分析框架基类
所有分析 Agent 的基础类，定义通用接口和行为
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Agent 分析结果"""
    agent_name: str
    success: bool
    score: float = 0.0  # 0-100 评分
    signal: str = "neutral"  # bullish, bearish, neutral
    confidence: float = 0.0  # 0-1 置信度
    summary: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "success": self.success,
            "score": self.score,
            "signal": self.signal,
            "confidence": self.confidence,
            "summary": self.summary,
            "details": self.details,
            "error": self.error,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class BaseAgent(ABC):
    """
    Agent 基类
    
    所有分析 Agent 都继承此类，实现 analyze 方法。
    支持：
    - 超时控制
    - 错误处理
    - 日志记录
    - LLM 调用
    """
    
    def __init__(self, name: str, role: str, timeout: float = 30.0):
        self.name = name
        self.role = role
        self.timeout = timeout
        self._ai_client = None
    
    @property
    def ai_client(self):
        """懒加载 AI 客户端"""
        if self._ai_client is None:
            from app.rox_quant.llm import AIClient
            self._ai_client = AIClient()
        return self._ai_client
    
    def get_system_prompt(self) -> str:
        """获取 Agent 专属的系统提示词"""
        return f"""你是 {self.name}，一位专业的 {self.role}。

职责：根据提供的数据进行专业分析，给出结构化的分析结果。

输出要求：
1. 给出 0-100 的评分
2. 给出信号: bullish(看多), bearish(看空), neutral(中性)
3. 给出简短的分析摘要
4. 提供详细的分析依据

请用中文回答，保持专业和客观。"""
    
    @abstractmethod
    async def analyze(self, context: Dict[str, Any]) -> AgentResult:
        """
        执行分析
        
        Args:
            context: 分析上下文，包含 stock_code, stock_name 等
            
        Returns:
            AgentResult: 分析结果
        """
        pass
    
    async def safe_analyze(self, context: Dict[str, Any]) -> AgentResult:
        """
        带超时和错误处理的分析方法
        """
        try:
            result = await asyncio.wait_for(
                self.analyze(context),
                timeout=self.timeout
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Agent {self.name} 分析超时")
            return AgentResult(
                agent_name=self.name,
                success=False,
                error=f"分析超时 (>{self.timeout}s)"
            )
        except Exception as e:
            logger.error(f"Agent {self.name} 分析失败: {e}")
            return AgentResult(
                agent_name=self.name,
                success=False,
                error=str(e)
            )
    
    async def call_llm(self, prompt: str, context: str = "") -> str:
        """
        调用 LLM 进行分析
        """
        try:
            response = await self.ai_client.chat_with_search(
                message=prompt,
                context=context
            )
            return response
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise
    
    def parse_score(self, text: str) -> float:
        """从文本中解析评分"""
        import re
        patterns = [
            r'评分[：:]\s*(\d+)',
            r'(\d+)\s*分',
            r'score[：:]\s*(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                score = float(match.group(1))
                return min(max(score, 0), 100)  # 限制在 0-100
        return 50.0  # 默认中性分数
    
    def parse_signal(self, text: str) -> str:
        """从文本中解析信号"""
        text_lower = text.lower()
        bullish_keywords = ['看多', '买入', '上涨', 'bullish', 'buy', '强烈推荐']
        bearish_keywords = ['看空', '卖出', '下跌', 'bearish', 'sell', '规避']
        
        bullish_count = sum(1 for kw in bullish_keywords if kw in text_lower)
        bearish_count = sum(1 for kw in bearish_keywords if kw in text_lower)
        
        if bullish_count > bearish_count:
            return "bullish"
        elif bearish_count > bullish_count:
            return "bearish"
        return "neutral"
    
    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name}>"
