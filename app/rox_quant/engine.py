"""
Rox Quant 交易引擎
集成讲座 coolfairy 的量化交易理念：
1. 多策略支持
2. 正期望验证
3. 风险管理（三之道）
4. 信号融合
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class StrategyMode(Enum):
    """策略模式"""
    SINGLE = "single"  # 单策略
    MULTI = "multi"    # 多策略
    ENSEMBLE = "ensemble"  # 集成


@dataclass
class Anchors:
    """讲座"三之道"的实现"""
    p_now: float
    p_stop: float
    p_target: float
    chips_profit_pct: float
    volume_status: str
    k_shape: str
    resonance_grade: str
    ta_signal: str = "WAIT" # 新增技术面信号
    volatility: float = 0.02 # 新增波动率（如 ATR/Price），默认为 2%

@dataclass
class RoxEngineResult:
    p_final: float
    b_value: float
    f_final: float
    p_stop: float
    p_target: float
    p_now: float
    risk_tip: str
    chips_judgement: str
    stars: str = ""
    p_details: Dict[str, float] = field(default_factory=dict)
    thinking_logic: Optional[Dict[str, Any]] = None # 新增思考逻辑字段
    suggest_stop_loss: Optional[float] = None # 建议止损价
    risk_per_share: Optional[float] = None # 每股风险

@dataclass
class EngineConfig:
    # 筹码调整
    CHIPS_LOW_THRESHOLD: float = 10.0
    CHIPS_MID_THRESHOLD: float = 50.0
    CHIPS_HIGH_THRESHOLD: float = 80.0
    ADJ_CHIPS_LOW: float = -0.30
    ADJ_CHIPS_MID: float = -0.10
    ADJ_CHIPS_HIGH: float = 0.20
    
    # 量能调整
    ADJ_VOL_STRICT: float = -0.20
    
    # 共振调整
    ADJ_RESONANCE_S: float = 0.20
    ADJ_RESONANCE_C: float = -0.30
    
    # 概率限制
    PROB_MIN: float = 0.10
    PROB_MAX: float = 0.90
    PROB_BASE: float = 0.50

    # 技术面信号调整 (TA)
    ADJ_TA_BULL: float = 0.15
    ADJ_TA_BEAR: float = -0.15

    # 风险控制
    MAX_POSITION_LIMIT: float = 0.80 # 最大总仓位限制
    ATR_MULTIPLIER: float = 2.0      # ATR 止损倍数（预留）

def ta_adjust(signal: str, config: EngineConfig = EngineConfig()) -> float:
    if "BUY" in signal or "BULL" in signal:
        return config.ADJ_TA_BULL
    if "SELL" in signal or "BEAR" in signal:
        return config.ADJ_TA_BEAR
    return 0.0

def chips_adjust(pct: float, config: EngineConfig = EngineConfig()) -> float:
    if pct < config.CHIPS_LOW_THRESHOLD:
        return config.ADJ_CHIPS_LOW
    if config.CHIPS_LOW_THRESHOLD <= pct <= config.CHIPS_MID_THRESHOLD:
        return config.ADJ_CHIPS_MID
    if pct > config.CHIPS_HIGH_THRESHOLD:
        return config.ADJ_CHIPS_HIGH
    return 0.0

def volume_adjust(status: str, config: EngineConfig = EngineConfig()) -> float:
    s = status.strip()
    if s == "达标":
        return 0.0
    if s == "萎缩":
        return config.ADJ_VOL_STRICT
    return 0.0

def resonance_adjust(grade: str, config: EngineConfig = EngineConfig()) -> float:
    g = grade.strip().upper()
    if g == "S":
        return config.ADJ_RESONANCE_S
    if g == "C":
        return config.ADJ_RESONANCE_C
    return 0.0

def clamp_probability(p: float, config: EngineConfig = EngineConfig()) -> float:
    if p < config.PROB_MIN:
        return config.PROB_MIN
    if p > config.PROB_MAX:
        return config.PROB_MAX
    return p

def final_probability_details(anchors: Anchors, config: EngineConfig = EngineConfig()) -> Dict[str, float]:
    base = config.PROB_BASE
    chips = chips_adjust(anchors.chips_profit_pct, config)
    volume = volume_adjust(anchors.volume_status, config)
    resonance = resonance_adjust(anchors.resonance_grade, config)
    ta = ta_adjust(anchors.ta_signal, config)
    
    p_final = clamp_probability(base + chips + volume + resonance + ta, config)
    
    return {
        "p_final": p_final,
        "base": base,
        "chips": chips,
        "volume": volume,
        "resonance": resonance,
        "ta": ta
    }

def final_probability(anchors: Anchors, config: EngineConfig = EngineConfig()) -> float:
    details = final_probability_details(anchors, config)
    return details["p_final"]

def b_ratio(p_now: float, p_stop: float, p_target: float) -> float:
    denom = p_now - p_stop
    num = p_target - p_now
    if denom <= 0:
        return 0.0
    return max(num / denom, 0.0)

def kelly_f(p_final: float, b: float) -> float:
    if b <= 0:
        return 0.0
    return ((p_final * (b + 1)) - 1) / b

def risk_control(f: float, chips_pct: float, volatility: float = 0.02, config: EngineConfig = EngineConfig()) -> float:
    # 1. 凯利公式初步结果
    f_final = f
    
    # 2. 基于筹码获利盘的信心调节
    if chips_pct < 20:
        f_final *= 0.5 # 获利盘极低，仓位减半
    elif chips_pct > 80:
        f_final *= 1.2 # 获利盘极高，增加信心
        
    # 3. 基于波动率的仓位缩放 (波动率越大，仓位越保守)
    # 假设基准波动率为 2%，如果波动率翻倍，仓位减半
    vol_adj = 0.02 / max(volatility, 0.01)
    f_final *= min(vol_adj, 1.2) # 最高允许 1.2 倍增强，不设下限

    # 4. 硬性上限约束
    f_final = min(f_final, config.MAX_POSITION_LIMIT)
    
    # 5. 极端情况清仓
    if f_final < 0.10:
        return 0.0
        
    return f_final

def chips_level(pct: float) -> str:
    if pct < 10:
        return "高危"
    if pct > 80:
        return "安全"
    return "关注"

def rating_stars(p_final: float) -> str:
    p = p_final * 100
    if p >= 75:
        return "⭐⭐⭐⭐⭐"
    if p >= 65:
        return "⭐⭐⭐⭐"
    if p >= 55:
        return "⭐⭐⭐"
    if p >= 45:
        return "⭐⭐"
    return "⭐"

class RoxEngine:
    def __init__(self, p_now: float, p_stop: float, p_target: float, chips_pct: float, volume_status: str, k_shape: str, resonance_rating: str, ta_signal: str = "WAIT", config: EngineConfig = EngineConfig()):
        self.config = config
        self.anchors = Anchors(
            p_now=p_now,
            p_stop=p_stop,
            p_target=p_target,
            chips_profit_pct=chips_pct,
            volume_status=volume_status,
            k_shape=k_shape,
            resonance_grade=resonance_rating,
            ta_signal=ta_signal
        )

    def analyze(self) -> RoxEngineResult:
        p_info = final_probability_details(self.anchors, self.config)
        p_final = p_info["p_final"]
        b = b_ratio(self.anchors.p_now, self.anchors.p_stop, self.anchors.p_target)
        f = kelly_f(p_final, b)
        f_final = risk_control(f, self.anchors.chips_profit_pct, self.anchors.volatility, self.config)
        
        # 计算动态止损建议 (基于 ATR/波动率)
        # 建议止损价 = 现价 * (1 - 波动率 * ATR倍数)
        suggest_stop = self.anchors.p_now * (1 - self.anchors.volatility * self.config.ATR_MULTIPLIER)
        risk_per_share = self.anchors.p_now - self.anchors.p_stop

        # 深度思考逻辑生成
        thinking = {
            "reason": self._generate_reason(p_final, b),
            "logic": self._generate_logic(),
            "results": self._generate_results(p_final, f_final)
        }

        # Risk Tip Logic
        if self.anchors.chips_profit_pct < 10:
            risk_tip = "获利盘过低，不具备博弈价值"
        elif b < 1.0:
            risk_tip = "盈亏比偏弱，谨慎控制仓位"
        elif self.anchors.p_stop > suggest_stop * 1.02: # 用户止损设得太窄
            risk_tip = f"注意：当前止损线 {self.anchors.p_stop} 严于技术建议位 {suggest_stop:.2f}，易被震荡出局。"
        else:
            risk_tip = "注意量能持续性与防守线执行"

        return RoxEngineResult(
            p_final=p_final,
            b_value=b,
            f_final=f_final,
            p_stop=self.anchors.p_stop,
            p_target=self.anchors.p_target,
            p_now=self.anchors.p_now,
            risk_tip=risk_tip,
            chips_judgement=chips_level(self.anchors.chips_profit_pct),
            stars=rating_stars(p_final),
            p_details={
                "chips": p_info["chips"],
                "volume": p_info["volume"],
                "resonance": p_info["resonance"],
                "ta": p_info["ta"]
            },
            thinking_logic=thinking,
            suggest_stop_loss=round(suggest_stop, 2),
            risk_per_share=round(risk_per_share, 2)
        )

    def _generate_reason(self, p: float, b: float) -> str:
        reasons = []
        if self.anchors.chips_profit_pct > 80:
            reasons.append("筹码结构高度锁定，上方抛压极轻，具备主升浪潜力。")
        elif self.anchors.chips_profit_pct < 20:
            reasons.append("筹码高度套牢，反弹压力巨大，资金共振不足。")
            
        if self.anchors.resonance_grade == "S":
            reasons.append("大盘与个股处于极强共振周期，属于概率极高的顺风局。")
        
        if b > 2.0:
            reasons.append(f"盈亏比高达 {b:.1f}，属于典型的‘以小博大’机会。")
        
        if p > 0.65:
             reasons.append("胜率评估处于优势区间，数学期望值显著为正。")
        
        if "BUY" in self.anchors.ta_signal:
             reasons.append(f"技术面触发【{self.anchors.ta_signal}】信号，多头动能正在释放。")
        
        return " ".join(reasons) if reasons else "当前处于中性博弈区间，建议按部就班执行网格或波段操作。"

    def _generate_logic(self) -> str:
        logic = [
            f"1. 技术面：基于【{self.anchors.k_shape}】判定，当前信号【{self.anchors.ta_signal}】，价格处于防守线 {self.anchors.p_stop} 之上。",
            f"2. 筹码面：当前获利比例为 {self.anchors.chips_profit_pct}%，{chips_level(self.anchors.chips_profit_pct)}状态。",
            f"3. 量能面：量能状态【{self.anchors.volume_status}】，支撑力度{'稳固' if self.anchors.volume_status == '达标' else '存疑'}。"
        ]
        return "\n".join(logic)

    def _generate_results(self, p: float, f: float) -> str:
        if f <= 0:
            return "结果预测：由于胜率或盈亏比不足以支撑长期正期望，强行操作大概率导致本金磨损。建议空仓等待。"
        
        prob_str = "高" if p > 0.6 else "中"
        return f"结果预测：本次操作胜率评估为{prob_str}，凯利建议仓位 {f*100:.1f}%。若严格执行止损，预期收益风险比具备数学正期望。"
