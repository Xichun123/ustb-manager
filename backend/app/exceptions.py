"""自定义异常类与全局异常处理器。"""

import logging

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.byyt.errors import BYYTRateLimited, BYYTUnavailable, BYYTUpstreamError

logger = logging.getLogger(__name__)


class AuthenticationRequired(Exception):
    """请求缺少有效的项目会话。"""


class BYYTSessionExpired(Exception):
    """BYYT 系统会话已过期，需要重新登录。"""


class CourseConflict(Exception):
    """课程操作被时间冲突阻止。"""


class CourseOperationBlocked(Exception):
    """课程操作被教务系统业务规则阻止。"""

    def __init__(
        self,
        message: str = "",
        *,
        code: str = "COURSE_OPERATION_BLOCKED",
        retryable: bool = False,
    ):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class IdempotencyKeyReused(Exception):
    """同一个幂等键被用于不同的请求。"""


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", ""))


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    retryable: bool,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "retryable": retryable,
                "request_id": _request_id(request),
            }
        },
    )


async def authentication_required_handler(request: Request, exc: AuthenticationRequired):
    return _error_response(
        request,
        status_code=401,
        code="AUTH_REQUIRED",
        message="请先登录",
        retryable=False,
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    codes = {
        400: "BAD_REQUEST",
        401: "AUTH_FAILED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        429: "REQUEST_RATE_LIMITED",
        502: "UPSTREAM_BAD_RESPONSE",
        503: "UPSTREAM_UNAVAILABLE",
    }
    message = exc.detail if isinstance(exc.detail, str) else "请求失败"
    return _error_response(
        request,
        status_code=exc.status_code,
        code=codes.get(exc.status_code, "REQUEST_ERROR"),
        message=message,
        retryable=exc.status_code in {429, 502, 503},
    )


async def validation_error_handler(request: Request, exc: RequestValidationError):
    return _error_response(
        request,
        status_code=422,
        code="VALIDATION_ERROR",
        message="请求参数无效",
        retryable=False,
    )


async def byyt_session_expired_handler(request: Request, exc: BYYTSessionExpired):
    """BYYT 会话过期 → 401。"""
    logger.warning(
        "BYYT session expired request_id=%s method=%s path=%s",
        _request_id(request),
        request.method,
        request.url.path,
    )
    return _error_response(
        request,
        status_code=401,
        code="UPSTREAM_SESSION_EXPIRED",
        message="教务系统登录已过期，请重新登录",
        retryable=False,
    )


async def byyt_rate_limited_handler(request: Request, exc: BYYTRateLimited):
    """BYYT 查询频率限制 → 429。"""
    logger.warning(
        "BYYT rate limited request_id=%s method=%s path=%s",
        _request_id(request),
        request.method,
        request.url.path,
    )
    return _error_response(
        request,
        status_code=429,
        code="UPSTREAM_RATE_LIMITED",
        message="教务系统请求过于频繁，请稍后重试",
        retryable=True,
    )


async def byyt_unavailable_handler(request: Request, exc: BYYTUnavailable):
    """BYYT 网络、超时或服务端临时故障 → 503。"""
    logger.warning(
        "BYYT unavailable request_id=%s method=%s path=%s",
        _request_id(request),
        request.method,
        request.url.path,
    )
    return _error_response(
        request,
        status_code=503,
        code="UPSTREAM_UNAVAILABLE",
        message="教务系统暂时不可用，请稍后重试",
        retryable=True,
    )


async def byyt_upstream_error_handler(request: Request, exc: BYYTUpstreamError):
    """BYYT 业务失败或畸形响应 → 502。"""
    logger.warning(
        "BYYT bad response request_id=%s method=%s path=%s",
        _request_id(request),
        request.method,
        request.url.path,
    )
    return _error_response(
        request,
        status_code=502,
        code="UPSTREAM_BAD_RESPONSE",
        message="教务系统返回了无法处理的响应",
        retryable=True,
    )


async def course_conflict_handler(request: Request, exc: CourseConflict):
    return _error_response(
        request,
        status_code=409,
        code="COURSE_CONFLICT",
        message=str(exc) or "课程时间冲突",
        retryable=False,
    )


async def course_operation_blocked_handler(request: Request, exc: CourseOperationBlocked):
    return _error_response(
        request,
        status_code=409,
        code=exc.code,
        message=str(exc) or "选课操作被阻止",
        retryable=exc.retryable,
    )


async def idempotency_key_reused_handler(request: Request, exc: IdempotencyKeyReused):
    return _error_response(
        request,
        status_code=409,
        code="IDEMPOTENCY_KEY_REUSED",
        message="幂等键已用于不同的选课请求",
        retryable=False,
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """未捕获的异常 → 500，响应和日志均不暴露异常内容。"""
    logger.error(
        "Unhandled exception request_id=%s method=%s path=%s type=%s",
        _request_id(request),
        request.method,
        request.url.path,
        type(exc).__name__,
    )
    return _error_response(
        request,
        status_code=500,
        code="INTERNAL_ERROR",
        message="服务器内部错误",
        retryable=False,
    )
