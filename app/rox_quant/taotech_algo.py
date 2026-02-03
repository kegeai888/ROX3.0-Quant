from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import math

from .data_provider import PricePoint, DataProvider
from .knowledge_base import KnowledgeBase


@dataclass
class MacroScanResult:
    direction: str
    position_limit: float
    notes: str


@dataclass
class SelectorResult:
    can_slip: Dict[str, Optional[bool]]
    sector_bias: str
    summary: str


@dataclass
class TimingResult:
    signal: str
    detail: str
    score: float


@dataclass
class RiskResult:
    stop_price: float
    exit_signal: Optional[str]


@dataclass
class StrategyReport:
    macro: MacroScanResult
    selector: SelectorResult
    timing: TimingResult
    risk: RiskResult
    resonance_score: float


def _ema(arr: List[float], period: int) -> List[float]:
    k = 2 / (period + 1)
    ema = []
    s = 0.0
    for i, v in enumerate(arr):
        if i == 0:
            s = v
        else:
            s = v * k + s * (1 - k)
        ema.append(s)
    return ema


def macd(series: List[float]) -> Dict[str, List[float]]:
    ema12 = _ema(series, 12)
    ema26 = _ema(series, 26)
    dif = [a - b for a, b in zip(ema12, ema26)]
    dea = _ema(dif, 9)
    hist = [a - b for a, b in zip(dif, dea)]
    return {"dif": dif, "dea": dea, "hist": hist}


def kdj(closes: List[float], highs: List[float], lows: List[float]) -> Dict[str, List[float]]:
    """
    计算 KDJ 指标 (9, 3, 3)
    RSV = (Close - LowestLow) / (HighestHigh - LowestLow) * 100
    K = 2/3 * PrevK + 1/3 * RSV
    D = 2/3 * PrevD + 1/3 * K
    J = 3 * K - 2 * D
    """
    n = len(closes)
    k_vals = [50.0] * n
    d_vals = [50.0] * n
    j_vals = [50.0] * n
    
    if n < 9: return {"k": k_vals, "d": d_vals, "j": j_vals}

    for i in range(n):
        if i < 8: continue
        
        # Calculate RSV
        start_idx = i - 8
        window_lows = lows[start_idx : i+1]
        window_highs = highs[start_idx : i+1]
        
        lowest_low = min(window_lows)
        highest_high = max(window_highs)
        
        if highest_high == lowest_low:
            rsv = 50.0
        else:
            rsv = (closes[i] - lowest_low) / (highest_high - lowest_low) * 100
            
        # K, D calculation (using EMA logic)
        prev_k = k_vals[i-1]
        prev_d = d_vals[i-1]
        
        k = (2/3) * prev_k + (1/3) * rsv
        d = (2/3) * prev_d + (1/3) * k
        j = 3 * k - 2 * d
        
        k_vals[i] = k
        d_vals[i] = d
        j_vals[i] = j
        
    return {"k": k_vals, "d": d_vals, "j": j_vals}


def rsi(closes: List[float], period: int = 14) -> List[float]:
    """
    计算 RSI 相对强弱指标
    """
    n = len(closes)
    rsi_vals = [0.0] * n
    if n < period + 1: return rsi_vals
    
    changes = [closes[i] - closes[i-1] for i in range(1, n)]
    
    # First RSI
    gains = sum([c for c in changes[:period] if c > 0])
    losses = sum([-c for c in changes[:period] if c < 0])
    
    avg_gain = gains / period
    avg_loss = losses / period
    
    if avg_loss == 0:
        rsi_vals[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi_vals[period] = 100.0 - (100.0 / (1.0 + rs))
        
    # Smoothed RSI
    for i in range(period + 1, n):
        change = changes[i-1]
        gain = change if change > 0 else 0
        loss = -change if change < 0 else 0
        
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        
        if avg_loss == 0:
            rsi_vals[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_vals[i] = 100.0 - (100.0 / (1.0 + rs))
            
    return rsi_vals


def boll(closes: List[float], period: int = 20, k: float = 2.0) -> Dict[str, List[float]]:
    """
    计算 BOLL 布林带
    MB = SMA(Close, 20)
    UP = MB + 2 * STD
    DN = MB - 2 * STD
    """
    n = len(closes)
    mb = [0.0] * n
    up = [0.0] * n
    dn = [0.0] * n
    
    if n < period: return {"mb": mb, "up": up, "dn": dn}
    
    for i in range(period - 1, n):
        window = closes[i - period + 1 : i + 1]
        avg = sum(window) / period
        
        # Standard Deviation
        variance = sum([(x - avg) ** 2 for x in window]) / period
        std = variance ** 0.5
        
        mb[i] = avg
        up[i] = avg + k * std
        dn[i] = avg - k * std
        
    return {"mb": mb, "up": up, "dn": dn}


def detect_buy_signals(closes: List[float]) -> TimingResult:
    m = macd(closes)
    n = len(closes)
    if n < 30:
        return TimingResult(signal="WAIT", detail="样本不足", score=0.0)
    low1 = min(closes[n - 20 : n - 10])
    low2 = min(closes[n - 10 : n])
    hist1 = min(m["hist"][n - 20 : n - 10])
    hist2 = min(m["hist"][n - 10 : n])
    if low2 < low1 and hist2 > hist1:
        return TimingResult(signal="BUY_1B", detail="底背驰成立", score=compute_strength_from_closes(closes))
    recent_low = min(closes[n - 15 : n - 5])
    last_low = min(closes[n - 5 : n])
    if last_low > recent_low:
        return TimingResult(signal="BUY_2B", detail="不破低点确认", score=compute_strength_from_closes(closes))
    high = max(closes[n - 20 : n - 1])
    if closes[-1] > high:
        return TimingResult(signal="BUY_3B", detail="突破近期高点", score=compute_strength_from_closes(closes))
    return TimingResult(signal="WAIT", detail="未触发买点", score=compute_strength_from_closes(closes))


def detect_exit_signals(closes: List[float]) -> Optional[str]:
    m = macd(closes)
    n = len(closes)
    if n < 30:
        return None
    high1 = max(closes[n - 20 : n - 10])
    high2 = max(closes[n - 10 : n])
    hist1 = max(m["hist"][n - 20 : n - 10])
    hist2 = max(m["hist"][n - 10 : n])
    if high2 > high1 and hist2 < hist1:
        return "SELL_1S"
    if closes[-1] < max(closes[n - 10 : n]) and closes[-1] < closes[-2]:
        return "SELL_2S"
    return None


def detect_kline_patterns(opens: List[float], highs: List[float], lows: List[float], closes: List[float]) -> List[Dict[str, str]]:
    """
    识别 K 线形态 (Pattern Recognition) - 纯 Python 实现
    支持识别: 十字星, 锤头线, 吞没形态, 早晨/黄昏之星, 红三兵等
    """
    patterns = []
    n = len(closes)
    if n < 5: return patterns
    
    # 定义基础数据 (最新一天为 -1)
    o, h, l, c = opens, highs, lows, closes
    
    # 辅助函数: 实体长度, 上影线, 下影线
    def body(i): return abs(c[i] - o[i])
    def upper(i): return h[i] - max(c[i], o[i])
    def lower(i): return min(c[i], o[i]) - l[i]
    def is_bull(i): return c[i] > o[i]
    def is_bear(i): return c[i] < o[i]
    def is_doji(i): return body(i) <= (h[i] - l[i]) * 0.1
    
    i = -1 # Check the latest candle
    
    # 1. 十字星 (Doji)
    if is_doji(i):
        patterns.append({"name": "十字星", "type": "neutral", "desc": "变盘信号"})
        
    # 2. 锤头线 (Hammer) - 底部反转
    # 实体小, 下影线长(实体2倍以上), 上影线短
    if body(i) < (h[i] - l[i]) * 0.3 and lower(i) > body(i) * 2 and upper(i) < body(i):
        patterns.append({"name": "锤头线", "type": "buy", "desc": "底部反转信号"})
        
    # 3. 倒锤头 (Inverted Hammer)
    if body(i) < (h[i] - l[i]) * 0.3 and upper(i) > body(i) * 2 and lower(i) < body(i):
        patterns.append({"name": "倒锤头", "type": "buy", "desc": "潜在止跌信号"})

    # 4. 吞没形态 (Engulfing)
    # 阳包阴 (Bullish Engulfing)
    if is_bear(i-1) and is_bull(i) and c[i] > o[i-1] and o[i] < c[i-1]:
        patterns.append({"name": "阳包阴", "type": "buy", "desc": "强烈看涨"})
    # 阴包阳 (Bearish Engulfing)
    if is_bull(i-1) and is_bear(i) and c[i] < o[i-1] and o[i] > c[i-1]:
        patterns.append({"name": "阴包阳", "type": "sell", "desc": "强烈看跌"})
        
    # 5. 早晨之星 (Morning Star) - 3根K线
    # 阴线 -> 跳空十字/小实体 -> 阳线
    if is_bear(i-2) and body(i-2) > (h[i-2]-l[i-2])*0.5 and \
       body(i-1) < body(i-2)*0.3 and \
       is_bull(i) and c[i] > (o[i-2] + c[i-2])/2:
       patterns.append({"name": "早晨之星", "type": "buy", "desc": "见底回升"})
       
    # 6. 黄昏之星 (Evening Star)
    if is_bull(i-2) and body(i-2) > (h[i-2]-l[i-2])*0.5 and \
       body(i-1) < body(i-2)*0.3 and \
       is_bear(i) and c[i] < (o[i-2] + c[i-2])/2:
       patterns.append({"name": "黄昏之星", "type": "sell", "desc": "见顶回落"})
       
    # 7. 红三兵 (Three White Soldiers)
    if is_bull(i) and is_bull(i-1) and is_bull(i-2) and \
       c[i] > c[i-1] > c[i-2] and \
       o[i] > o[i-1] > o[i-2]:
       patterns.append({"name": "红三兵", "type": "buy", "desc": "多头排列"})

    return patterns


def calculate_t_points(closes: List[float], highs: List[float], lows: List[float]) -> Dict[str, float]:
    """
    计算做T点位建议 (T-Trade Points)
    基于布林带和 Pivot Points 算法
    """
    n = len(closes)
    if n < 20:
        return {"buy": 0.0, "sell": 0.0, "space": 0.0}
        
    # 1. BOLL Bands Strategy
    b = boll(closes, 20, 2.0)
    boll_up = b["up"][-1]
    boll_mb = b["mb"][-1]
    boll_dn = b["dn"][-1]
    
    # 2. Pivot Points Strategy (Classic)
    # Using previous day's data to project today's levels
    # But here we are using 'daily' data which includes today (if after close) or real-time snapshot.
    # Assuming the last element is "current/today", we should use previous day for reference if we want strictly predictive,
    # OR if we are intraday, the last bar is forming.
    # Let's use the 'current' BOLL as dynamic resistance, and Pivot based on yesterday.
    
    prev_h = highs[-2]
    prev_l = lows[-2]
    prev_c = closes[-2]
    
    pivot = (prev_h + prev_l + prev_c) / 3
    r1 = 2 * pivot - prev_l
    s1 = 2 * pivot - prev_h
    
    # 3. Combine Logic
    # Resistance (Sell): Conservative is Min of (BOLL UP, R1) but BOLL UP is dynamic.
    # If price is far below BOLL UP, BOLL UP is the ceiling.
    # Let's simply provide BOLL bands as strong reference for T.
    
    # T-Sell: Upper Band or R1, whichever is closer to price but above it? 
    # Usually T-Sell is at resistance.
    t_sell = (boll_up + r1) / 2
    
    # T-Buy: Lower Band or S1
    t_buy = (boll_dn + s1) / 2
    
    # If bandwidth is too narrow, use MA lines
    # ... simplified for now
    
    current_price = closes[-1]
    
    # Correction: ensure sell > buy
    if t_sell <= t_buy:
        t_sell = current_price * 1.02
        t_buy = current_price * 0.98
        
    space = (t_sell - t_buy) / current_price
    
    return {
        "buy": round(t_buy, 2),
        "sell": round(t_sell, 2), 
        "space": round(space * 100, 2), # percentage
        "pivot": round(pivot, 2)
    }


def compute_strength_from_closes(closes: List[float]) -> float:
    n = len(closes)
    if n < 20:
        return 0.0
    m = macd(closes)
    high = max(closes[n - 20 : n - 1])
    breakout = max(0.0, (closes[-1] - high) / max(1e-6, high))
    hist = m["hist"][-1]
    dif_gap = m["dif"][-1] - m["dea"][-1]
    def _sig(x: float) -> float:
        return 1.0 / (1.0 + (2.718281828 ** (-4.0 * x)))
    s = 0.0
    s += 35.0 * breakout
    s += 25.0 * _sig(hist)
    s += 25.0 * _sig(dif_gap)
    win = closes[n - 20 : n]
    avg = sum(win) / len(win)
    var = sum([(x - avg) ** 2 for x in win]) / max(1, len(win) - 1)
    std = var ** 0.5
    vol_inv = 1.0 / (1.0 + std / max(1e-6, avg))
    s += 15.0 * vol_inv
    sma20 = sum(win) / len(win)
    sma19 = sum(closes[n - 21 : n - 1]) / 20 if n >= 21 else sma20
    slope = sma20 - sma19
    s += 5.0 * _sig(slope)
    return max(0.0, min(100.0, s))

def tf_multi_scores(code: str) -> Dict[str, float]:
    provider = DataProvider()
    ds = provider.get_history_k(code, period="daily", limit=120)
    ws = provider.get_history_k(code, period="weekly", limit=80)
    ms = provider.get_history_k(code, period="monthly", limit=60)
    def _score(arr: List[PricePoint]) -> float:
        cs = [p.close for p in arr]
        m = macd(cs)
        n = len(cs)
        if n < 30:
            return 30.0
        s = 0.0
        s += 40.0 if cs[-1] > max(cs[n - 20 : n - 1]) else 0.0
        s += 30.0 if m["hist"][-1] > 0 else 0.0
        s += 30.0 if m["dif"][-1] > m["dea"][-1] else 0.0
        return round(s, 2)
    return {
        "daily": _score(ds),
        "weekly": _score(ws),
        "monthly": _score(ms),
    }


def _kb_analyze(kb: KnowledgeBase) -> Dict[str, float]:
    sector_keywords = {
        "半导体": ["半导体", "芯片", "集成电路", "晶圆", "封测", "EDA"],
        "新能源": ["新能源", "光伏", "储能", "风电", "锂电", "电动车"],
        "算力/AI": ["AI", "人工智能", "算力", "大模型", "GPU", "数据中心"],
        "医药": ["医药", "创新药", "医疗器械", "疫苗", "CXO"],
        "消费": ["消费", "白酒", "家电", "新零售", "食品饮料"],
        "军工": ["军工", "装备", "航天", "航空", "导弹"],
        "金融": ["银行", "保险", "券商", "金融"],
    }
    macro_bull = ["降息", "宽货币", "财政扩张", "基建", "刺激", "稳增长"]
    macro_bear = ["加息", "缩表", "通胀高企", "衰退", "地缘风险"]
    scores: Dict[str, float] = {k: 0.0 for k in sector_keywords.keys()}
    bull = 0
    bear = 0
    for doc in kb.documents:
        text = f"{doc.title}\n{doc.content}".lower()
        for sector, kws in sector_keywords.items():
            for kw in kws:
                if kw.lower() in text:
                    scores[sector] += 1.0
        for kw in macro_bull:
            if kw.lower() in text:
                bull += 1
        for kw in macro_bear:
            if kw.lower() in text:
                bear += 1
    # normalize
    total = sum(scores.values()) or 1.0
    for k in scores:
        scores[k] = scores[k] / total
    pos = 0.5 + 0.1 * bull - 0.1 * bear
    pos = max(0.1, min(0.9, pos))
    return {"position": pos, "scores": scores}


def macro_scan(kb: KnowledgeBase) -> MacroScanResult:
    ana = _kb_analyze(kb) if kb else {"position": 0.6, "scores": {}}
    top_sector = max(ana.get("scores", {"数据资产": 1.0}).items(), key=lambda x: x[1])[0] if ana.get("scores") else "数据资产与新能源"
    return MacroScanResult(direction=top_sector, position_limit=float(ana["position"]), notes="基于知识库语义计分的宏观倾向")


def selector_can_slim(code: str, kb: KnowledgeBase) -> SelectorResult:
    can = {"C": None, "A": None, "N": None, "L": None, "I": None}
    ana = _kb_analyze(kb) if kb else {"scores": {"信息产业化": 1.0}}
    sector_bias = max(ana["scores"].items(), key=lambda x: x[1])[0] if ana.get("scores") else "信息产业化/产业信息化优先"
    summary = "基本面条件待接入，先用技术代理衡量强度"
    return SelectorResult(can_slip=can, sector_bias=sector_bias, summary=summary)


def risk_control_for_price(now_price: float) -> RiskResult:
    stop = round(now_price * 0.92, 2)
    return RiskResult(stop_price=stop, exit_signal=None)


def run_strategy(name: str, code: str, kb: KnowledgeBase = None) -> StrategyReport:
    provider = DataProvider()
    series = provider.get_history(code, days=200)
    closes = [p.close for p in series]
    macro = macro_scan(kb or KnowledgeBase())
    selector = selector_can_slim(code, kb or KnowledgeBase())
    timing = detect_buy_signals(closes)
    exit_sig = detect_exit_signals(closes)
    risk = risk_control_for_price(closes[-1])
    if exit_sig:
        risk.exit_signal = exit_sig
    tfs = tf_multi_scores(code)
    rs = round(tfs["daily"] * 0.4 + tfs["weekly"] * 0.35 + tfs["monthly"] * 0.25, 2)
    return StrategyReport(macro=macro, selector=selector, timing=timing, risk=risk, resonance_score=rs)


class LuQiyuan_Macro_Model:
    """
    基于卢麒元“广义税政”与“资本周转”理论的宏观经济分析模型。
    用于评估一个经济体的健康度，并给出资产配置建议。
    """

    def __init__(
        self,
        country: str,
        years: List[int],
        gdp_series: List[float],
        m2_series: List[float],
        direct_tax_rate: float,
        gini_coefficient: float,
        global_instability_index: float,
    ):
        # 经济体名称，用于报告说明
        self.country = country
        # 年份序列，例如 [2018, 2019, 2020, 2021, 2022]
        self.years = years
        # 名义或实际 GDP，单位可统一为万亿本币
        self.gdp_series = gdp_series
        # 对应年份的 M2 广义货币量
        self.m2_series = m2_series
        # 直接税占全部税收或财政收入的比例（0-1）
        self.direct_tax_rate = direct_tax_rate
        # 基尼系数，衡量收入分配不平等程度
        self.gini = gini_coefficient
        # 全球动荡指数，可以用 VIX 或自定义指标归一化到 0-100
        self.global_instability_index = global_instability_index

    def _compute_turnover_efficiency(self) -> Dict[str, Any]:
        """
        资本周转率因子 (Capital Turnover Factor)
        理论对应：《资本论》第二卷 + 卢麒元“资本必须循环、停滞即危机”的判断。
        计算 GDP/M2 作为货币周转效率，并观察最近三年的斜率。
        """
        if not self.years or len(self.years) != len(self.gdp_series) or len(self.years) != len(self.m2_series):
            return {"factor": None, "trend": None, "slope": None, "warning": "数据长度不一致"}

        ratio = []
        for g, m in zip(self.gdp_series, self.m2_series):
            # 防止除零，若 M2 极大而 GDP 较小，本身就暗含“资本沉淀”
            ratio.append(g / m if m > 0 else 0.0)

        # 只取最近三年做线性趋势估计
        if len(ratio) < 3:
            return {"factor": ratio[-1] if ratio else None, "trend": None, "slope": None, "warning": "样本不足3年"}

        last3 = ratio[-3:]
        x = list(range(3))
        # 简单一元线性回归斜率，刻画周转效率的变化方向
        avg_x = sum(x) / 3.0
        avg_y = sum(last3) / 3.0
        num = sum((xi - avg_x) * (yi - avg_y) for xi, yi in zip(x, last3))
        den = sum((xi - avg_x) ** 2 for xi in x) or 1.0
        slope = num / den

        # 根据斜率判断趋势：负斜率代表周转效率在下降
        trend = "下降" if slope < 0 else "上升或持平"

        # 危机预警条件：
        # 1）最近三年斜率明显为负
        # 2）且降幅超过经验阈值（例如 -0.02）
        threshold = -0.02
        warning = None
        if slope < threshold:
            warning = "资本周转效率连续走弱，存在资本沉淀于食利部门的风险（卢麒元：周转受阻即危机）"

        return {
            "factor": ratio[-1],
            "trend": trend,
            "slope": slope,
            "warning": warning,
            "series": ratio,
        }

    def _compute_fiscal_health(self) -> Dict[str, Any]:
        """
        税政健康度因子 (Fiscal Health / Direct Tax Ratio)
        理论对应：卢麒元“直接税”与共同富裕逻辑：
          - 直接税比重过低 + 基尼系数偏高 => 食利型经济 + 贫富分化。
        """
        status = "中性"
        signal = "观察"
        rationale = []

        if self.direct_tax_rate < 0.3:
            status = "直接税偏低"
            rationale.append("直接税占比 < 30%，对资产阶级与食利阶层的约束不足")

        if self.gini > 0.45:
            rationale.append("基尼系数 > 0.45，收入分配失衡，贫富差距扩大")

        if self.direct_tax_rate < 0.3 and self.gini > 0.45:
            signal = "食利型经济"
            rationale.append("符合“低直接税 + 高不平等”的食利型特征，应警惕资产价格泡沫与社会撕裂")

        return {
            "direct_tax_rate": self.direct_tax_rate,
            "gini": self.gini,
            "status": status,
            "signal": signal,
            "rationale": rationale,
        }

    def check_crisis_signal(self) -> Dict[str, Any]:
        """
        综合输出危机信号。
        把“资本周转效率”与“税政健康度”结合，给出是否进入
        卢麒元意义上的“资本周转受阻 + 食利结构固化”的高风险区。
        """
        turnover = self._compute_turnover_efficiency()
        fiscal = self._compute_fiscal_health()

        level = "正常"
        messages = []

        if turnover.get("warning"):
            messages.append(turnover["warning"])
        if fiscal.get("signal") == "食利型经济":
            messages.append("税政结构偏向食利阶层，直接税不足，难以实现共同富裕（需要房产税等直接税改革）")

        if messages:
            level = "高风险"
        elif turnover.get("trend") == "下降" or fiscal.get("status") != "中性":
            level = "中风险"

        return {
            "country": self.country,
            "level": level,
            "turnover": turnover,
            "fiscal": fiscal,
            "messages": messages,
        }

    def recommend_allocation(self, base_portfolio: Dict[str, float] = None) -> Dict[str, Any]:
        """
        根据卢麒元对动荡期资产的判断，给出资产配置建议。
        逻辑：
          1）在旧秩序破碎、新秩序生成的阶段，应提高硬资产（粮食、军火、金银、现钞、能源）权重。
          2）当全球动荡指数上升时，增加黄金/能源/农业，削弱高估值科技股。
        """
        if base_portfolio is None:
            base_portfolio = {
                "Gold": 0.1,
                "Energy": 0.1,
                "Agriculture": 0.1,
                "Cash": 0.1,
                "Tech_Growth": 0.3,
                "Broad_Equity": 0.3,
            }

        portfolio = dict(base_portfolio)

        # 将动荡指数归一化 0-1，便于插值调整权重
        instability = max(0.0, min(self.global_instability_index / 100.0, 1.0))

        # 当动荡指数高于 0.5，视为进入卢麒元所说“旧秩序破碎期”
        if instability > 0.5:
            portfolio["Gold"] = min(portfolio.get("Gold", 0) + 0.2, 0.5)
            portfolio["Energy"] = min(portfolio.get("Energy", 0) + 0.15, 0.5)
            portfolio["Agriculture"] = min(portfolio.get("Agriculture", 0) + 0.15, 0.5)
            portfolio["Tech_Growth"] = max(portfolio.get("Tech_Growth", 0) - 0.3, 0.0)

        total = sum(portfolio.values()) or 1.0
        normalized = {k: v / total for k, v in portfolio.items()}

        suggestion = "根据卢麒元观点，在全球动荡抬头阶段，应减少虚拟金融资产和高估值科技股配置，增加黄金、能源、农业等硬资产比重，同时保留足够现金以应对极端事件。"

        crisis = self.check_crisis_signal()
        if crisis["level"] == "高风险":
            suggestion += " 当前宏观显示资本周转受阻且税政结构偏向食利阶层，整体建议降低本国股指多头仓位，适度对冲或做空，并加大硬资产与海外现金头寸。"

        return {
            "country": self.country,
            "normalized_allocation": normalized,
            "raw_allocation": portfolio,
            "global_instability_index": self.global_instability_index,
            "suggestion": suggestion,
        }
