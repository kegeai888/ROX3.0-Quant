
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict
import logging
from app.services.kb_service import KBService

logger = logging.getLogger("kb-api")
router = APIRouter()
kb_service = KBService()

def format_results(results: List[Dict]) -> List[Dict]:
    """Format results for the frontend."""
    formatted = []
    for item in results:
        formatted.append({
            "title": item.get("title", ""),
            "snippet": item.get("summary", ""),
            "source": item.get("source", "Rox 知识库")
        })
    return formatted

@router.get("/search", summary="搜索知识库")
async def search_kb(query: str = Query(..., description="搜索关键词"),
                    mode: str = Query("mixed", description="搜索模式: local, web, mixed")):
    """
    根据关键词和模式搜索知识库。
    """
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="搜索关键词不能为空")
    
    # 1. Local Search
    local_results = []
    if mode in ["local", "mixed"]:
        raw_local = kb_service.search_local(query)
        local_results = format_results(raw_local)
        
        # If local-only or if we found good enough local results, we might return early?
        # For now, let's stick to the requested mode logic.
        if mode == "local":
            return local_results

    # 2. Web Search
    web_results = []
    if mode in ["web", "mixed"]:
        raw_web = kb_service.search_web(query)
        web_results = format_results(raw_web)

    # 3. Combine
    # If mixed, prioritize local results on top if they exist
    combined = local_results + web_results
    
    return combined

@router.post("/refresh", summary="刷新本地文档索引")
async def refresh_kb():
    """强制重新扫描文档目录"""
    kb_service.refresh_cache()
    return {"status": "ok", "message": "知识库索引已刷新"}
