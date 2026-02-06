"""
Synthesizer - 综合决策器 Agent
负责汇总各 Agent 意见，生成最终决策和报告
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class Synthesizer(BaseAgent):
    """综合决策器 Agent"""
    
    def __init__(self):
        super().__init__(
            name="Synthesizer",
            role="综合决策器，汇总各分析师意见，生成最终投资建议",
            timeout=30.0
        )
        
        # Agent 权重配置
        self.weights = {
            "technical": 0.25,
            "market": 0.15,
            "fundamental": 0.25,
            "news": 0.15,
            "risk": 0.20,
        }
    
    async def analyze(self, context: Dict[str, Any]) -> AgentResult:
        """综合分析（通常不直接调用，而是通过 synthesize）"""
        return await self.synthesize({}, context)
    
    async def synthesize(self, agent_results: Dict[str, AgentResult], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        综合各 Agent 的分析结果
        
        Args:
            agent_results: 各 Agent 的分析结果 {name: AgentResult}
            context: 分析上下文
            
        Returns:
            综合分析报告
        """
        stock_code = context.get("stock_code", "")
        stock_name = context.get("stock_name", stock_code)
        
        # 收集有效结果
        valid_results = {}
        failed_agents = []
        
        for name, result in agent_results.items():
            if isinstance(result, AgentResult):
                if result.success:
                    valid_results[name] = result
                else:
                    failed_agents.append(name)
            elif isinstance(result, dict):
                if result.get('success', False):
                    valid_results[name] = result
                else:
                    failed_agents.append(name)
        
        if not valid_results:
            return {
                "success": False,
                "error": "所有分析师都返回失败",
                "failed_agents": failed_agents,
            }
        
        # 计算加权综合评分
        total_weight = 0
        weighted_score = 0
        
        for name, result in valid_results.items():
            weight = self.weights.get(name, 0.1)
            score = result.score if isinstance(result, AgentResult) else result.get('score', 50)
            weighted_score += score * weight
            total_weight += weight
        
        final_score = weighted_score / total_weight if total_weight > 0 else 50
        
        # 综合信号投票
        signal_votes = {"bullish": 0, "bearish": 0, "neutral": 0}
        for name, result in valid_results.items():
            weight = self.weights.get(name, 0.1)
            signal = result.signal if isinstance(result, AgentResult) else result.get('signal', 'neutral')
            signal_votes[signal] = signal_votes.get(signal, 0) + weight
        
        # 确定最终信号
        final_signal = max(signal_votes, key=signal_votes.get)
        
        # 生成操作建议
        action = self._get_action_advice(final_score, final_signal)
        
        # 汇总各 Agent 摘要
        agent_summaries = {}
        for name, result in valid_results.items():
            summary = result.summary if isinstance(result, AgentResult) else result.get('summary', '')
            agent_summaries[name] = summary
        
        # 生成综合报告
        report = self._generate_report(
            stock_name, final_score, final_signal, action, 
            agent_summaries, valid_results, failed_agents
        )
        
        return {
            "success": True,
            "stock_code": stock_code,
            "stock_name": stock_name,
            "final_score": round(final_score, 1),
            "final_signal": final_signal,
            "action": action,
            "confidence": self._calculate_confidence(valid_results, failed_agents),
            "agent_results": {
                name: (r.to_dict() if isinstance(r, AgentResult) else r)
                for name, r in valid_results.items()
            },
            "failed_agents": failed_agents,
            "report": report,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _get_action_advice(self, score: float, signal: str) -> str:
        """生成操作建议"""
        if score >= 75 and signal == "bullish":
            return "强烈买入"
        elif score >= 60 and signal == "bullish":
            return "适度买入"
        elif score >= 55:
            return "观望"
        elif score >= 45:
            return "持有不动"
        elif score >= 35:
            return "减仓"
        elif signal == "bearish":
            return "卖出"
        else:
            return "观望"
    
    def _calculate_confidence(self, valid_results: Dict, failed_agents: List) -> float:
        """计算置信度"""
        # 基础置信度
        base_confidence = len(valid_results) / (len(valid_results) + len(failed_agents))
        
        # 根据各 Agent 置信度加权
        if valid_results:
            avg_confidence = sum(
                (r.confidence if isinstance(r, AgentResult) else r.get('confidence', 0.5))
                for r in valid_results.values()
            ) / len(valid_results)
            return round((base_confidence + avg_confidence) / 2, 2)
        
        return round(base_confidence, 2)
    
    def _generate_report(self, stock_name: str, score: float, signal: str, 
                        action: str, summaries: Dict, results: Dict, failed: List) -> str:
        """生成综合报告"""
        signal_text = {"bullish": "看多", "bearish": "看空", "neutral": "中性"}.get(signal, "中性")
        
        report_lines = [
            f"## 📊 {stock_name} 多智能体综合分析报告",
            "",
            f"**综合评分**: {score:.0f}/100 | **信号**: {signal_text} | **建议**: {action}",
            "",
            "---",
            "",
            "### 各分析师观点",
            "",
        ]
        
        # Agent 图标映射
        icons = {
            "technical": "📈",
            "market": "🌍",
            "fundamental": "💰",
            "news": "📰",
            "risk": "🛡️",
        }
        
        names_cn = {
            "technical": "技术分析师",
            "market": "市场分析师",
            "fundamental": "基本面分析师",
            "news": "新闻分析师",
            "risk": "风控分析师",
        }
        
        for name, summary in summaries.items():
            icon = icons.get(name, "📋")
            name_cn = names_cn.get(name, name)
            result = results.get(name)
            if result:
                result_score = result.score if isinstance(result, AgentResult) else result.get('score', 50)
                report_lines.append(f"- {icon} **{name_cn}** ({result_score:.0f}分): {summary}")
        
        if failed:
            report_lines.append("")
            report_lines.append(f"⚠️ 以下分析师未能完成分析: {', '.join(failed)}")
        
        report_lines.extend([
            "",
            "---",
            "",
            f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        ])
        
        return "\n".join(report_lines)
