
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import logging
import os

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None  # 可选依赖，未安装时知识库仅本地搜索

logger = logging.getLogger("kb-api")
router = APIRouter()

# 缓存：从 app/data/documents 加载的文档列表（首次搜索时加载）
_documents_dir_cache: Optional[List[Dict[str, Any]]] = None

# --- 内置本地知识库数据 ---
KNOWLEDGE_BASE_DATA: List[Dict] = [
    {
        "id": "k_001",
        "title": "什么是K线？",
        "summary": "K线图（Candlestick Charts）又称蜡烛图、日本线、阴阳线、棒线、红黑线等，常用说法是“K线”。它是以每个分析周期的开盘价、最高价、最低价和收盘价绘制而成。",
        "tags": ["基础", "图表", "技术分析"],
        "source": "Rox 本地知识库"
    },
    {
        "id": "k_002",
        "title": "MACD指标详解",
        "summary": "MACD称为异同移动平均线，是从双指数移动平均线发展而来的。由快的指数移动平均线（EMA12）减去慢的指数移动平均线（EMA26）得到快线DIF，再用DIF的9日加权移动均线DEA，最后用DIF减DEA得到MACD柱。",
        "tags": ["技术分析", "指标", "MACD"],
        "source": "Rox 本地知识库"
    },
    {
        "id": "k_003",
        "title": "RSI指标的应用",
        "summary": "相对强弱指数（RSI）是通过比较一段时期内的平均收盘涨数和平均收盘跌数来分析市场买卖盘强弱的技术分析指标。RSI值在0-100之间，通常认为超过70为超买，低于30为超卖。",
        "tags": ["技术分析", "指标", "RSI", "超买超卖"],
        "source": "Rox 本地知识库"
    },
    {
        "id": "k_004",
        "title": "市盈率（PE Ratio）是什么？",
        "summary": "市盈率（Price-to-Earnings Ratio）是公司股价与每股收益的比率。它是评估股票估值水平最常用的指标之一。PE越低，理论上投资回收期越短，风险越小。",
        "tags": ["基本面分析", "估值", "PE"],
        "source": "Rox 本地知识库"
    }
]

def _get_embedded_docs() -> List[Dict[str, Any]]:
    """尝试加载 rox_quant 的 embedded_kb.json，返回 [{title, summary, source}]"""
    try:
        from app.rox_quant.knowledge_base import KnowledgeBase
        kb = KnowledgeBase()
        n = kb.load_embedded()
        if n == 0:
            return []
        out = []
        for doc in kb.documents:
            snippet = (doc.content or "")[:300] + ("..." if len(doc.content or "") > 300 else "")
            out.append({
                "title": doc.title or "",
                "summary": snippet,
                "tags": [],
                "source": "Rox 本地知识库"
            })
        return out
    except Exception as e:
        logger.debug(f"加载 embedded_kb 失败: {e}")
        return []


def _extract_text_snippet(fp: str, ext: str, max_chars: int = 600) -> str:
    """轻量提取文档前 max_chars 字，用于关键词搜索。"""
    content = ""
    try:
        if ext in [".txt", ".md"]:
            with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                content = (fh.read() or "")[:max_chars]
        elif ext == ".docx":
            try:
                from docx import Document
                d = Document(fp)
                content = ("\n".join([p.text for p in d.paragraphs]) or "")[:max_chars]
            except Exception:
                content = ""
        elif ext == ".pdf":
            try:
                from pdfminer.high_level import extract_text as _pdf_extract
                content = (_pdf_extract(fp) or "")[:max_chars]
            except Exception:
                try:
                    import fitz
                    d = fitz.open(fp)
                    content = "\n".join([p.get_text() or "" for p in d[:3]])[:max_chars]
                except Exception:
                    content = ""
        else:
            content = ""
    except Exception:
        content = ""
    return content.strip() + ("..." if len(content) >= max_chars else "")


def _get_documents_from_data_dir() -> List[Dict[str, Any]]:
    """从 app/data/documents 加载书籍/文档列表（仅标题+摘要，用于关键词搜索）。首次调用时扫描并缓存。"""
    global _documents_dir_cache
    if _documents_dir_cache is not None:
        return _documents_dir_cache
    try:
        from app.core.config import settings
        doc_dir = os.path.join(settings.BASE_DIR, "app", "data", "documents")
        if not os.path.isdir(doc_dir):
            _documents_dir_cache = []
            return []
        out = []
        for root, _, files in os.walk(doc_dir):
            for f in files:
                if f.startswith("~$") or f.startswith("."):
                    continue
                fp = os.path.join(root, f)
                ext = os.path.splitext(fp)[1].lower()
                title = os.path.splitext(os.path.basename(fp))[0]
                if ext not in [".txt", ".md", ".docx", ".pdf"]:
                    continue
                snippet = _extract_text_snippet(fp, ext)
                out.append({
                    "title": title,
                    "summary": snippet,
                    "tags": [],
                    "source": "app/data/documents"
                })
        _documents_dir_cache = out
        logger.info(f"已从 app/data/documents 加载 {len(out)} 个文档供知识库搜索")
        return out
    except Exception as e:
        logger.warning(f"加载 app/data/documents 失败: {e}")
        _documents_dir_cache = []
        return []

def format_local_results(results: List[Dict]) -> List[Dict]:
    """将本地知识库数据格式化为标准输出"""
    formatted = []
    for item in results:
        formatted.append({
            "title": item.get("title", ""),
            "snippet": item.get("summary", item.get("snippet", "")),
            "source": item.get("source", "Rox 本地知识库")
        })
    return formatted

@router.get("/search", summary="搜索知识库")
async def search_kb(query: str = Query(..., description="搜索关键词"),
                    mode: str = Query("mixed", description="搜索模式: local, web, mixed")):
    """
    根据关键词和模式搜索知识库。
    - **query**: 搜索查询字符串。
    - **mode**: local=仅本地, web=仅联网, mixed=先本地后联网。
    """
    logger.info(f"收到知识库搜索请求: query='{query}', mode='{mode}'")

    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="搜索关键词不能为空")
    if len(query.strip()) > 500:
        raise HTTPException(status_code=400, detail="搜索关键词长度不能超过 500 字符")
    if mode not in ("local", "web", "mixed"):
        raise HTTPException(status_code=400, detail="搜索模式需为 local / web / mixed")

    q_lower = query.strip().lower()
    local_sources: List[Dict] = list(KNOWLEDGE_BASE_DATA)
    embedded = _get_embedded_docs()
    for e in embedded:
        if e not in local_sources:
            local_sources.append(e)
    docs_from_dir = _get_documents_from_data_dir()
    for d in docs_from_dir:
        local_sources.append(d)

    # --- 本地搜索（内置 + embedded_kb + app/data/documents）---
    if mode in ["local", "mixed"]:
        local_results = []
        for entry in local_sources:
            title = (entry.get("title") or "").lower()
            summary = (entry.get("summary") or "").lower()
            tags = " ".join(entry.get("tags") or []).lower()
            if q_lower in title or q_lower in summary or q_lower in tags:
                local_results.append(entry)
        if local_results:
            logger.info(f"在本地找到 {len(local_results)} 条结果。")
            return format_local_results(local_results)
        if mode == "local":
            return []

    # --- 网络搜索：失败时返回空并打日志，不抛 500 ---
    if mode in ["web", "mixed"]:
        if DDGS is None:
            logger.warning("未安装 duckduckgo_search，无法联网搜索。请 pip install duckduckgo-search")
            return JSONResponse(content=[], headers={"X-KB-Web-Unavailable": "1"})
        try:
            logger.info("开始网络搜索...")
            web_results = []
            with DDGS() as ddgs:
                search_query = f"{query} 股票 财经 解释"
                for r in ddgs.text(search_query, region='cn-zh', safesearch='Moderate', max_results=5):
                    web_results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "source": r.get("href", "网络")
                    })
            logger.info(f"网络搜索完成，找到 {len(web_results)} 条结果。")
            return web_results
        except Exception as e:
            logger.warning(f"网络搜索失败，降级返回空: {e}")
            return JSONResponse(
                content=[],
                headers={"X-KB-Web-Unavailable": "1"}
            )

    raise HTTPException(status_code=400, detail="无效的搜索模式")
