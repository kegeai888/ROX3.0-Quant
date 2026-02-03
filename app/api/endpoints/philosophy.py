from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
import pandas as pd
import logging

from app.services.market_data import get_market_stats_data
from app.db import get_market_rankings, get_all_stocks_spot
from app.rox_quant.philosophy.contradiction import ContradictionAnalyzer

logger = logging.getLogger("rox-philosophy-api")
router = APIRouter()


@router.get("/contradictions")
async def api_contradictions():
    """
    主矛盾扫描器：把市场压缩为少量“张力 + 方向 + 建议”。
    """
    try:
        stats = await get_market_stats_data()
        rankings = await get_market_rankings()
        analyzer = ContradictionAnalyzer()
        return analyzer.analyze(stats, rankings)
    except Exception as e:
        logger.error(f"contradictions failed: {e}", exc_info=True)
        return JSONResponse({"error": "contradictions_failed", "detail": str(e)}, status_code=500)


def _coerce_float(x) -> float:
    try:
        if x is None:
            return 0.0
        s = str(x).strip().replace("%", "")
        return float(s)
    except Exception:
        return 0.0


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


@router.get("/value-scatter")
async def api_value_scatter(
    limit: int = Query(600, ge=50, le=2000),
    sort: str = Query("mv", description="mv|abs_dev"),
):
    """
    价值散点图数据：用全市场快照近似计算“内在价值/偏离度/剩余价值能力”。
    """
    try:
        df = await get_all_stocks_spot()
        if df is None or df.empty:
            return {"items": []}

        cols = df.columns.tolist()
        code_col = next((c for c in cols if "代码" in c or "证券代码" in c), "代码")
        name_col = next((c for c in cols if "名称" in c or "简称" in c), "名称")
        price_col = next((c for c in cols if "最新价" in c or "现价" in c), None)
        pe_col = next((c for c in cols if "市盈率" in c and "静" not in c), None) or next((c for c in cols if "市盈率" in c), None)
        pb_col = next((c for c in cols if "市净率" in c), None)
        roe_col = next((c for c in cols if "净资产收益率" in c or "ROE" in c.upper()), None)
        mv_col = next((c for c in cols if "总市值" in c), None)

        if not price_col or not pe_col:
            return {"items": []}

        d = df.copy()
        d[code_col] = d[code_col].astype(str).str.zfill(6)
        d["_price"] = pd.to_numeric(d[price_col], errors="coerce").fillna(0.0)
        d["_pe"] = pd.to_numeric(d[pe_col], errors="coerce").fillna(0.0)
        d["_pb"] = pd.to_numeric(d[pb_col], errors="coerce").fillna(0.0) if pb_col else 0.0
        d["_roe"] = d[roe_col].apply(_coerce_float) if roe_col else 0.0
        d["_mv"] = pd.to_numeric(d[mv_col], errors="coerce").fillna(0.0) if mv_col else 0.0

        # 基础过滤：价格/PE 有效
        d = d[(d["_price"] > 0) & (d["_pe"] > 0)]
        if d.empty:
            return {"items": []}

        # 估算 EPS & 内在价值（价值锚：ROE 分档决定目标 PE）
        eps = d["_price"] / d["_pe"]

        def target_pe(roe: float) -> float:
            if roe >= 25:
                return 22.0
            if roe >= 20:
                return 18.0
            if roe >= 15:
                return 15.0
            if roe >= 10:
                return 12.0
            if roe > 0:
                return 8.0
            return 12.0

        d["_tpe"] = d["_roe"].apply(target_pe)
        d["_intrinsic"] = (eps * d["_tpe"]).replace([pd.NA, float("inf"), float("-inf")], 0.0).fillna(0.0)
        d = d[d["_intrinsic"] > 0]
        if d.empty:
            return {"items": []}

        d["_dev"] = (d["_price"] - d["_intrinsic"]) / d["_intrinsic"]

        # 剩余价值能力评分（0-100）
        def surplus_score(row) -> int:
            roe = float(row["_roe"])
            pb = float(row["_pb"])
            s = 50
            if roe >= 25:
                s += 30
            elif roe >= 15:
                s += 20
            elif roe >= 8:
                s += 10
            elif roe < 5:
                s -= 10
            if pb and pb < 2:
                s += 5
            elif pb and pb > 5:
                s -= 5
            return int(_clamp(s, 0, 100))

        d["_surplus"] = d.apply(surplus_score, axis=1)

        def label_signal(dev: float) -> str:
            if dev < -0.30:
                return "strong_buy"
            if dev < -0.15:
                return "buy"
            if dev > 0.30:
                return "strong_sell"
            if dev > 0.15:
                return "sell"
            return "hold"

        d["_signal"] = d["_dev"].apply(label_signal)

        if sort == "abs_dev":
            d = d.assign(_abs=d["_dev"].abs()).sort_values("_abs", ascending=False)
        else:
            d = d.sort_values("_mv", ascending=False)

        d = d.head(int(limit))

        items = []
        for _, row in d.iterrows():
            items.append(
                {
                    "code": str(row[code_col]),
                    "name": str(row[name_col]),
                    "price": float(row["_price"]),
                    "intrinsic": float(row["_intrinsic"]),
                    "deviation": float(row["_dev"]),
                    "surplus_score": int(row["_surplus"]),
                    "roe": float(row["_roe"]),
                    "pe": float(row["_pe"]),
                    "pb": float(row["_pb"]),
                    "mv_yi": float(row["_mv"]) / 100000000.0 if row["_mv"] else 0.0,
                    "signal": str(row["_signal"]),
                }
            )

        return {"items": items, "count": len(items)}
    except Exception as e:
        logger.error(f"value-scatter failed: {e}", exc_info=True)
        return JSONResponse({"error": "value_scatter_failed", "detail": str(e)}, status_code=500)

