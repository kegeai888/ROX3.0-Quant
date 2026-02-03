import pandas as pd
import numpy as np
from typing import Dict, Any

def calculate_technical_score(df: pd.DataFrame) -> tuple[int, dict]:
    """
    Calculate a technical score (0-100) and return detailed analysis.
    """
    if df is None or len(df) < 30:
        return 50, {"summary": "数据不足，无法精确诊断", "tech": "无数据", "trend": "未知"}

    df = df.copy()
    close = df['close']
    ma5 = close.rolling(5).mean()
    ma10 = close.rolling(10).mean()
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    
    current_price = close.iloc[-1]
    
    score = 50
    details = []
    
    # 1. Trend Analysis (40 points)
    # Long Term Trend (MA60)
    if current_price > ma60.iloc[-1]:
        score += 10
        details.append("股价站上60日均线，中线趋势向好")
    else:
        score -= 10
        details.append("股价跌破60日均线，中线趋势走弱")
        
    # Short Term Trend (MA5 > MA10 > MA20)
    if ma5.iloc[-1] > ma10.iloc[-1] > ma20.iloc[-1]:
        score += 15
        details.append("短期均线呈多头排列，上涨动能强劲")
    elif ma5.iloc[-1] < ma10.iloc[-1] < ma20.iloc[-1]:
        score -= 15
        details.append("短期均线呈空头排列，下跌压力较大")
        
    # 2. Momentum Analysis (30 points)
    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    macd = (dif - dea) * 2
    
    if dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-1] > 0:
        score += 10
        details.append("MACD处于零轴上方金叉区域，属于强势拉升期")
    elif dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-1] < 0:
        score += 5
        details.append("MACD水下金叉，存在反弹需求")
    elif dif.iloc[-1] < dea.iloc[-1]:
        score -= 10
        details.append("MACD死叉向下，注意回调风险")
        
    # KDJ
    low_min = df['low'].rolling(9).min()
    high_max = df['high'].rolling(9).max()
    rsv = (close - low_min) / (high_max - low_min) * 100
    k = rsv.ewm(alpha=1/3, adjust=False).mean()
    d = k.ewm(alpha=1/3, adjust=False).mean()
    j = 3 * k - 2 * d
    
    j_val = j.iloc[-1]
    if j_val > 100:
        score -= 5
        details.append("KDJ指标严重超买，短期可能回调")
    elif j_val < 0:
        score += 10
        details.append("KDJ指标严重超卖，随时可能反弹")
    elif k.iloc[-1] > d.iloc[-1]:
        score += 5
        details.append("KDJ金叉向上")
        
    # 3. Volume Analysis (20 points)
    vol_ma5 = df['volume'].rolling(5).mean()
    if df['volume'].iloc[-1] > vol_ma5.iloc[-1] * 1.5:
        if current_price > df['open'].iloc[-1]:
            score += 10
            details.append("放量上涨，资金介入明显")
        else:
            score -= 10
            details.append("放量下跌，恐慌盘涌出")
            
    # 4. Position Relative to History (10 points)
    high_250 = df['high'].rolling(250, min_periods=60).max().iloc[-1]
    low_250 = df['low'].rolling(250, min_periods=60).min().iloc[-1]
    position = (current_price - low_250) / (high_250 - low_250 + 1e-6) * 100
    
    if position < 20:
        score += 10
        details.append("股价处于年内低位区，安全边际较高")
    elif position > 80:
        score -= 5
        details.append("股价处于年内高位区，注意追高风险")
        
    # Cap Score
    score = max(10, min(98, score))
    
    return score, details

def diagnose_stock(code: str, name: str, df: pd.DataFrame, is_fallback: bool = False) -> Dict[str, Any]:
    """
    Generate a complete diagnosis report.
    """
    if is_fallback or df is None or df.empty:
        return {
            "score": 50,
            "summary": "由于数据源暂时不可用，无法进行精准诊断。当前展示为模拟评分。",
            "technicals": "数据缺失",
            "fundamentals": "数据缺失",
            "capital": "数据缺失",
            "is_fallback": True
        }

    score, tech_details = calculate_technical_score(df)
    
    # Generate Summary
    if score >= 80:
        summary = f"{name}({code}) 目前处于极强多头趋势，技术指标共振向上，资金运作积极，建议坚定持有或逢低积极做多。"
        rating = "强力买入"
    elif score >= 60:
        summary = f"{name}({code}) 走势稳健，多头略占优势，但上涨动能需进一步确认，建议持股观望或轻仓试探。"
        rating = "增持/持有"
    elif score >= 40:
        summary = f"{name}({code}) 处于震荡整理阶段，方向不明，多空博弈激烈，建议多看少动，等待方向选择。"
        rating = "中性观望"
    else:
        summary = f"{name}({code}) 处于弱势下跌通道，技术面破位，资金流出迹象明显，建议规避风险或逢高减仓。"
        rating = "卖出/规避"
        
    # Capital Analysis (Mocked or derived from Volume/HF)
    # If we had HF indicators computed, we could use them. 
    # For now, derive simple volume analysis.
    vol_trend = "资金流入" if df['volume'].iloc[-1] > df['volume'].shift(1).iloc[-1] and df['close'].iloc[-1] > df['open'].iloc[-1] else "资金流出"
    capital_text = f"近期{vol_trend}迹象明显。"
    if score > 70:
        capital_text += " 主力资金控盘度较高，筹码锁定良好。"
    elif score < 40:
        capital_text += " 主力资金呈现净流出态势，抛压较重。"
        
    return {
        "score": int(score),
        "rating": rating,
        "summary": summary,
        "technicals": "；".join(tech_details[:4]), # Top 4 points
        "fundamentals": "基本面数据需结合财报分析 (暂未接入深度财报数据)", # Placeholder
        "capital": capital_text,
        "is_fallback": False
    }
