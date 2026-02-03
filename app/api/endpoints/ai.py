from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
from app.auth import get_current_user, User
from app.rox_quant.llm import AIClient
from app.db import get_db, list_prompt_templates, get_prompt_template, save_prompt_template

router = APIRouter()
logger = logging.getLogger("rox-ai")

# Initialize AI Client
try:
    ai_client = AIClient()
except Exception as e:
    logger.error(f"Failed to initialize AI Client: {e}")
    ai_client = None

class ChatRequest(BaseModel):
    message: str
    context: str = ""
    model: Optional[str] = None
    provider: Optional[str] = None

class AnalysisRequest(BaseModel):
    stock_name: str
    stock_code: str
    price: float
    indicators: Dict[str, Any] = {}
    model: Optional[str] = None
    provider: Optional[str] = None


@router.get("/providers")
async def list_ai_providers():
    """
    返回可用 AI 后端列表（多模型/多平台，参考 go-stock）。
    """
    if not ai_client:
        return {"current": "default", "list": []}
    return ai_client.list_providers()


@router.post("/chat")
async def chat(req: ChatRequest, current_user: User = Depends(get_current_user)):
    """
    AI Chat Endpoint；支持 provider/model 切换。
    """
    if not ai_client:
        return {"response": "AI 服务初始化失败，请检查服务端配置。"}

    try:
        user_context = f"用户: {current_user.username}\n{req.context}"
        response = await ai_client.chat_with_search(
            message=req.message,
            context=user_context,
            model=req.model,
            provider=req.provider,
        )
        return {"response": response}
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        return {"response": "AI 思考过程中发生了错误，请稍后再试。"}


@router.post("/analyze")
async def analyze_stock(req: AnalysisRequest, current_user: User = Depends(get_current_user)):
    """
    Deep Stock Analysis Endpoint；支持 provider/model 切换。
    """
    if not ai_client:
        raise HTTPException(status_code=503, detail="AI Service Unavailable")

    try:
        result = await ai_client.analyze_stock(
            stock_name=req.stock_name,
            stock_code=req.stock_code,
            price=req.price,
            indicators=req.indicators,
            model=req.model,
            provider=req.provider,
        )
        return result
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- AI 模板（参考 go-stock） ----------
class TemplateCreate(BaseModel):
    name: str
    key: str
    content: str
    scope: str = "user"


@router.get("/templates")
async def api_list_templates(
    scope: Optional[str] = Query(None, description="system | user"),
    current_user: User = Depends(get_current_user),
    conn = Depends(get_db),
):
    """返回 AI 提示词模板列表（可配置分析/选股模板）。"""
    items = list_prompt_templates(conn, user_id=current_user.id, scope=scope)
    return {"items": items}


@router.get("/templates/{key}")
async def api_get_template(
    key: str,
    current_user: User = Depends(get_current_user),
    conn = Depends(get_db),
):
    """按 key 获取单个模板内容。"""
    row = get_prompt_template(conn, key=key, user_id=current_user.id)
    if not row:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"key": row["key"], "name": row["name"], "content": row["content"], "scope": row["scope"]}


@router.post("/templates")
async def api_create_template(
    req: TemplateCreate,
    current_user: User = Depends(get_current_user),
    conn = Depends(get_db),
):
    """新建用户 AI 提示词模板。"""
    tid = save_prompt_template(conn, current_user.id, req.name, req.key, req.content, req.scope)
    if tid is None:
        raise HTTPException(status_code=500, detail="保存失败")
    return {"id": tid, "key": req.key, "name": req.name}

