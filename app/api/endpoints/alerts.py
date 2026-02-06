"""
价格预警 API 端点
支持创建、查询、删除预警规则
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.db import get_db_context

router = APIRouter(prefix="/alerts", tags=["价格预警"])


class AlertCreate(BaseModel):
    symbol: str
    name: str = ""
    alert_type: str  # price_above | price_below | change_pct_above | change_pct_below
    value: float
    note: str = ""


class AlertResponse(BaseModel):
    id: int
    symbol: str
    name: str
    alert_type: str
    value: float
    note: str
    created_at: str
    triggered: bool
    triggered_at: Optional[str] = None


def _ensure_table(db):
    """确保预警表存在"""
    db.execute("""
        CREATE TABLE IF NOT EXISTS price_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            name TEXT,
            alert_type TEXT NOT NULL,
            value REAL NOT NULL,
            note TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            triggered INTEGER DEFAULT 0,
            triggered_at TEXT
        )
    """)


@router.post("/create")
async def create_alert(alert: AlertCreate):
    """
    创建价格预警
    alert_type: 
      - price_above: 价格突破上限
      - price_below: 价格跌破下限
      - change_pct_above: 涨幅超过
      - change_pct_below: 跌幅超过
    """
    with get_db_context() as db:
        _ensure_table(db)
        
        cursor = db.execute("""
            INSERT INTO price_alerts (symbol, name, alert_type, value, note)
            VALUES (?, ?, ?, ?, ?)
        """, (alert.symbol, alert.name, alert.alert_type, alert.value, alert.note))
        
        return {"success": True, "id": cursor.lastrowid, "message": "预警创建成功"}


@router.get("/list")
async def list_alerts(symbol: Optional[str] = None, include_triggered: bool = False):
    """
    获取预警列表
    """
    with get_db_context() as db:
        _ensure_table(db)
        
        if symbol:
            if include_triggered:
                cursor = db.execute(
                    "SELECT * FROM price_alerts WHERE symbol = ? ORDER BY created_at DESC",
                    (symbol,)
                )
            else:
                cursor = db.execute(
                    "SELECT * FROM price_alerts WHERE symbol = ? AND triggered = 0 ORDER BY created_at DESC",
                    (symbol,)
                )
        else:
            if include_triggered:
                cursor = db.execute("SELECT * FROM price_alerts ORDER BY created_at DESC")
            else:
                cursor = db.execute("SELECT * FROM price_alerts WHERE triggered = 0 ORDER BY created_at DESC")
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        result = []
        for row in rows:
            item = dict(zip(columns, row))
            item["triggered"] = bool(item.get("triggered", 0))
            result.append(item)
        
        return {"data": result}


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int):
    """
    删除预警
    """
    with get_db_context() as db:
        db.execute("DELETE FROM price_alerts WHERE id = ?", (alert_id,))
        return {"success": True, "message": "预警已删除"}


@router.post("/check")
async def check_alerts():
    """
    检查并触发预警
    由前端定时调用或后端调度器调用
    """
    from app.db import get_all_stocks_spot
    
    with get_db_context() as db:
        _ensure_table(db)
        
        # 获取未触发的预警
        cursor = db.execute("SELECT * FROM price_alerts WHERE triggered = 0")
        alerts = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        if not alerts:
            return {"triggered": []}
        
        # 获取实时行情
        try:
            spot_df = await get_all_stocks_spot()
        except:
            return {"triggered": [], "error": "获取行情失败"}
        
        if spot_df is None or spot_df.empty:
            return {"triggered": [], "error": "行情数据为空"}
        
        triggered = []
        
        for row in alerts:
            alert = dict(zip(columns, row))
            symbol = alert["symbol"]
            alert_type = alert["alert_type"]
            value = alert["value"]
            
            # 查找股票行情
            code_col = next((c for c in spot_df.columns if "代码" in c), "代码")
            price_col = next((c for c in spot_df.columns if "最新价" in c), "最新价")
            pct_col = next((c for c in spot_df.columns if "涨跌幅" in c), None)
            
            stock_row = spot_df[spot_df[code_col].astype(str) == symbol]
            if stock_row.empty:
                continue
            
            current_price = float(stock_row.iloc[0][price_col] or 0)
            current_pct = float(stock_row.iloc[0][pct_col] or 0) if pct_col else 0
            
            should_trigger = False
            
            if alert_type == "price_above" and current_price >= value:
                should_trigger = True
            elif alert_type == "price_below" and current_price <= value:
                should_trigger = True
            elif alert_type == "change_pct_above" and current_pct >= value:
                should_trigger = True
            elif alert_type == "change_pct_below" and current_pct <= value:
                should_trigger = True
            
            if should_trigger:
                # 标记为已触发
                db.execute(
                    "UPDATE price_alerts SET triggered = 1, triggered_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), alert["id"])
                )
                
                alert["current_price"] = current_price
                alert["current_pct"] = current_pct
                triggered.append(alert)
        
        return {"triggered": triggered}
