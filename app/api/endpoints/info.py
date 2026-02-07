from fastapi import APIRouter, HTTPException, Query
import akshare as ak
import pandas as pd
from typing import Dict, List, Any
import logging

router = APIRouter(prefix="/info", tags=["Info"])
logger = logging.getLogger("rox-info")

@router.get("/news")
async def get_market_news(limit: int = 20):
    """
    Get 7x24 global financial news.
    Source: EastMoney / Sina via AkShare
    """
    try:
        # stock_info_global_cls -> Global major finance news
        news_df = ak.stock_info_global_cls()
        
        # Standardize columns: title, content, time, url
        news_list = []
        for _, row in news_df.head(limit).iterrows():
            news_list.append({
                "title": row['标题'],
                "time": row['发布时间'],
                "url": row['链接'] if '链接' in row else "",
                "tag": "Global"
            })
            
        return news_list
    except Exception as e:
        logger.error(f"News API Error: {e}")
        return []

@router.get("/notices/{symbol}")
async def get_stock_notices(symbol: str, limit: int = 10):
    """
    Get specific stock announcements.
    Source: CNINFO proxy via EastMoney
    """
    try:
        # Easy cleaner: standard symbol (e.g. 600519)
        code = symbol
        if "." in code:
            code = code.split(".")[0]
            
        # ak.stock_notice_report(symbol="600519") returns PDF titles
        notice_df = ak.stock_notice_report(symbol=code)
        
        notices = []
        for _, row in notice_df.head(limit).iterrows():
             notices.append({
                "title": row['公告标题'],
                "type": row['公告类型'],
                "date": row['公告日期'],
                "url": row['公告链接'] if '公告链接' in row else ""
            })
        return notices
        
    except Exception as e:
        logger.error(f"Notice API Error: {e}")
        # Return empty list
        return []
