"""
数据导出 API 端点
支持导出自选股、诊断报告、回测结果为 Excel/CSV
"""
import io
import csv
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Response, Query
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/export", tags=["数据导出"])


@router.get("/watchlist")
async def export_watchlist(format: str = Query("csv", enum=["csv", "xlsx"])):
    """
    导出自选股列表
    """
    from app.db import get_db
    
    db = get_db()
    cursor = db.execute("""
        SELECT code, name, added_at, group_name 
        FROM watchlist 
        ORDER BY added_at DESC
    """)
    rows = cursor.fetchall()
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["代码", "名称", "添加时间", "分组"])
        for row in rows:
            writer.writerow([row[0], row[1], row[2], row[3] or "默认"])
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=watchlist_{datetime.now().strftime('%Y%m%d')}.csv"
            }
        )
    else:
        # Excel 格式需要 openpyxl
        try:
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "自选股"
            ws.append(["代码", "名称", "添加时间", "分组"])
            for row in rows:
                ws.append([row[0], row[1], row[2], row[3] or "默认"])
            
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            
            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename=watchlist_{datetime.now().strftime('%Y%m%d')}.xlsx"
                }
            )
        except ImportError:
            # 回退到 CSV
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["代码", "名称", "添加时间", "分组"])
            for row in rows:
                writer.writerow([row[0], row[1], row[2], row[3] or "默认"])
            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=watchlist_{datetime.now().strftime('%Y%m%d')}.csv"}
            )


@router.get("/market-data/{code}")
async def export_market_data(
    code: str,
    days: int = Query(60, ge=1, le=365),
    format: str = Query("csv", enum=["csv", "xlsx"])
):
    """
    导出个股历史数据
    """
    import akshare as ak
    
    try:
        # 获取历史数据
        if code.startswith("6"):
            symbol = f"sh{code}"
        else:
            symbol = f"sz{code}"
        
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
        df = df.tail(days)
        
        if format == "csv":
            output = io.StringIO()
            df.to_csv(output, index=False, encoding="utf-8-sig")
            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename={code}_history_{datetime.now().strftime('%Y%m%d')}.csv"
                }
            )
        else:
            output = io.BytesIO()
            df.to_excel(output, index=False, engine="openpyxl")
            output.seek(0)
            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename={code}_history_{datetime.now().strftime('%Y%m%d')}.xlsx"
                }
            )
    except Exception as e:
        return {"error": str(e)}


@router.get("/dragon-tiger")
async def export_dragon_tiger(
    date: Optional[str] = None,
    format: str = Query("csv", enum=["csv", "xlsx"])
):
    """
    导出龙虎榜数据
    """
    import akshare as ak
    
    try:
        if date:
            df = ak.stock_lhb_detail_em(date=date)
        else:
            df = ak.stock_lhb_detail_em()
        
        if format == "csv":
            output = io.StringIO()
            df.to_csv(output, index=False, encoding="utf-8-sig")
            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=dragon_tiger_{datetime.now().strftime('%Y%m%d')}.csv"
                }
            )
        else:
            output = io.BytesIO()
            df.to_excel(output, index=False, engine="openpyxl")
            output.seek(0)
            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename=dragon_tiger_{datetime.now().strftime('%Y%m%d')}.xlsx"
                }
            )
    except Exception as e:
        return {"error": str(e)}
