"""
统一 API 错误响应格式，便于前端与监控解析
"""
from typing import Optional, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

def error_response(
    error: str,
    code: Optional[str] = None,
    status_code: int = 400,
    details: Optional[Any] = None,
) -> JSONResponse:
    """统一错误体：{ "error": str, "code"?: str, "details"?: any }"""
    body = {"error": error}
    if code:
        body["code"] = code
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app):
    """注册全局异常处理器"""
    from fastapi import HTTPException

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return error_response(
            error=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            code=f"HTTP_{exc.status_code}",
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return error_response(
            error="请求参数校验失败",
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        import logging
        logging.getLogger("rox-backend").exception("Unhandled exception: %s", exc)
        return error_response(
            error="服务器内部错误",
            code="INTERNAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
