"""自定义异常类与全局异常处理器"""
import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.byyt.errors import BYYTRateLimited, BYYTUpstreamError

logger = logging.getLogger(__name__)


class BYYTSessionExpired(Exception):
    """BYYT系统会话已过期，需要重新登录"""
    pass


async def byyt_session_expired_handler(request: Request, exc: BYYTSessionExpired):
    """BYYT 会话过期 → 401。"""
    logger.warning("BYYT session expired on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=401,
        content={
            "error": {
                "code": "UPSTREAM_SESSION_EXPIRED",
                "message": "教务系统登录已过期，请重新登录",
                "retryable": False,
            }
        },
    )


async def byyt_rate_limited_handler(request: Request, exc: BYYTRateLimited):
    """BYYT 查询频率限制 → 429。"""
    logger.warning("BYYT rate limited %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "UPSTREAM_RATE_LIMITED",
                "message": "教务系统请求过于频繁，请稍后重试",
                "retryable": True,
            }
        },
    )


async def byyt_upstream_error_handler(request: Request, exc: BYYTUpstreamError):
    """BYYT 业务失败响应 → 502。"""
    logger.warning("BYYT bad response on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=502,
        content={
            "error": {
                "code": "UPSTREAM_BAD_RESPONSE",
                "message": "教务系统返回了无法处理的响应",
                "retryable": True,
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """未捕获的异常 → 500，响应中不泄露内部异常。"""
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "retryable": False,
            }
        },
    )
