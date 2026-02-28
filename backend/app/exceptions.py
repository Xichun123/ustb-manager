"""自定义异常类与全局异常处理器"""
import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class BYYTSessionExpired(Exception):
    """BYYT系统会话已过期，需要重新登录"""
    pass


async def byyt_session_expired_handler(request: Request, exc: BYYTSessionExpired):
    """BYYT 会话过期 → 502"""
    logger.warning(f"BYYT session expired: {exc}")
    return JSONResponse(
        status_code=502,
        content={"detail": "BYYT session expired, please login again"},
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """未捕获的异常 → 500"""
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )
