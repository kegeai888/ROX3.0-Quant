from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


def _parse_yi(s: Any) -> Optional[float]:
    """
    Parse strings like '12.34亿', '-3.2亿', '8000亿', '--' to float in 亿元.
    """
    if s is None:
        return None
    ss = str(s).strip()
    if not ss or ss == "--":
        return None
    try:
        if "亿" in ss:
            return float(ss.replace("亿", ""))
        if "万" in ss:
            return float(ss.replace("万", "")) / 10000.0
        return float(ss)
    except Exception:
        return None


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


@dataclass
class ContradictionItem:
    id: str
    name: str
    strength: float  # 0..100
    direction: float  # -1..1 (负=偏空/风险，正=偏多/机会)
    summary: str
    suggestion: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "strength": round(float(self.strength), 2),
            "direction": round(float(self.direction), 3),
            "summary": self.summary,
            "suggestion": self.suggestion,
        }


class ContradictionAnalyzer:
    """
    一个“主矛盾扫描器”：将市场状态压缩为少量可解释的张力与方向。

    说明：
    - 这是 0→1 的可运行版本（可用、可扩展），不是终版宏观模型。
    - 主要用于给 UI 和 AI 提供稳定的“框架语境”，后续可叠加更多数据源与历史标准化。
    """

    def analyze(self, market_stats: Dict[str, Any], rankings: Dict[str, Any]) -> Dict[str, Any]:
        up = int(market_stats.get("up", 0) or 0)
        down = int(market_stats.get("down", 0) or 0)
        total = max(1, up + down)
        bull_bear = float(market_stats.get("bull_bear", 0.5) or 0.5)  # 上涨占比

        volume_yi = _parse_yi(market_stats.get("volume"))
        north_yi = _parse_yi(market_stats.get("north_fund"))
        main_yi = _parse_yi(market_stats.get("main_flow"))

        breadth = (up - down) / total  # -1..1

        # 1) 量能 vs 赚钱效应（广度）
        # 没有历史分位时，用经验区间粗归一：6000亿~12000亿映射到 0~1
        liq = _clamp(((volume_yi or 0.0) - 6000.0) / 6000.0, 0.0, 1.0)
        br = _clamp(breadth, -1.0, 1.0)
        strength1 = _clamp(liq * abs(br) * 140.0, 0.0, 100.0)
        direction1 = _clamp(liq * br, -1.0, 1.0)

        if liq >= 0.6 and br <= -0.15:
            summary1 = "放量但赚钱效应偏弱，属于“资金活跃却不易赚钱”的分歧市。"
            sug1 = "降低追涨频率，优先高流动性龙头；用更硬的止损/仓位约束。"
        elif liq >= 0.6 and br >= 0.15:
            summary1 = "放量且赚钱效应较强，属于“趋势扩散”的顺风市。"
            sug1 = "顺势为主，控制回撤；适当提高胜率策略权重，减少逆势抄底。"
        elif liq <= 0.3 and br >= 0.10:
            summary1 = "缩量但赚钱效应回暖，可能是“修复反弹/结构行情”。"
            sug1 = "以结构为主，避免重仓博指数；优先强势行业内的强趋势个股。"
        else:
            summary1 = "量能与赚钱效应处于中性区间，行情更依赖结构与个股。"
            sug1 = "降低频繁切换，建立备选池；用纪律与复盘提升胜率。"

        items: List[ContradictionItem] = [
            ContradictionItem(
                id="liquidity_vs_breadth",
                name="量能 vs 赚钱效应",
                strength=strength1,
                direction=direction1,
                summary=summary1,
                suggestion=sug1,
            )
        ]

        # 2) 外资 vs 内资（分歧度）
        if north_yi is not None and main_yi is not None:
            denom = abs(north_yi) + abs(main_yi) + 1e-6
            divergence = abs(north_yi - main_yi) / denom  # 0..1
            strength2 = _clamp(divergence * 100.0, 0.0, 100.0)
            # direction: north stronger => positive, domestic stronger => negative (仅做语义约定)
            direction2 = _clamp((north_yi - main_yi) / max(1.0, denom), -1.0, 1.0)
            if divergence >= 0.45:
                summary2 = "外资与内资出现明显分歧，市场对“定价权”理解不一致。"
                sug2 = "减少纯情绪票，优先能穿越分歧的核心资产/行业龙头；避免高杠杆。"
            else:
                summary2 = "外资与内资相对一致，资金面共识较强。"
                sug2 = "可适度提高趋势/轮动策略权重，但仍需控制单一方向暴露。"
            items.append(
                ContradictionItem(
                    id="foreign_vs_domestic",
                    name="外资 vs 内资分歧",
                    strength=strength2,
                    direction=direction2,
                    summary=summary2,
                    suggestion=sug2,
                )
            )

        # 3) 行业轮动强度（结构张力）
        sectors = rankings.get("sectors") or []
        try:
            pcts = [float(s.get("pct", 0) or 0) for s in sectors if isinstance(s, dict)]
        except Exception:
            pcts = []
        if len(pcts) >= 2:
            spread = max(pcts) - min(pcts)
            strength3 = _clamp((spread / 6.0) * 100.0, 0.0, 100.0)  # 6% 视为较强轮动
            direction3 = _clamp((max(pcts) + min(pcts)) / 10.0, -1.0, 1.0)
            if spread >= 5:
                summary3 = "行业分化较大，结构性行情明显（强者恒强/弱者更弱）。"
                sug3 = "用行业/主题做“先验筛选”，再在行业内选最强个股；避免平均分散。"
            else:
                summary3 = "行业分化不大，更偏“指数/共振”行情。"
                sug3 = "更关注指数趋势与风险偏好，选股难度相对下降。"
            items.append(
                ContradictionItem(
                    id="sector_rotation",
                    name="行业分化 vs 指数共振",
                    strength=strength3,
                    direction=direction3,
                    summary=summary3,
                    suggestion=sug3,
                )
            )

        # 主矛盾：按 strength 最大
        main = max(items, key=lambda x: x.strength) if items else None
        return {
            "main": main.to_dict() if main else None,
            "items": [it.to_dict() for it in sorted(items, key=lambda x: x.strength, reverse=True)],
            "snapshot": {
                "up": up,
                "down": down,
                "bull_bear": bull_bear,
                "volume_yi": volume_yi,
                "north_yi": north_yi,
                "main_yi": main_yi,
            },
        }

