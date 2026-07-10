import base64
import json
import re
import logging
from fastapi import APIRouter, Response, HTTPException, Cookie
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import asyncio

from ..config import COOKIE_NAME, COOKIE_SECURE, SESSION_TTL, SESSION_MAX_AGE
from ..services.session_store import store, AuthState
from ..services import auth_service
from ..rate_limit import sms_rate_limiter
from ustb_sso._exceptions import APIError

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

_QR_INIT_FAILED_MESSAGE = "二维码登录初始化失败，请稍后重试"
_SMS_INIT_FAILED_MESSAGE = "短信登录初始化失败，请稍后重试"
_SMS_SEND_RATE_LIMITED_MESSAGE = "短信发送过于频繁，请稍后重试"
_SMS_SEND_FAILED_MESSAGE = "短信服务暂时不可用，请稍后重试"
_SMS_VERIFY_INVALID_MESSAGE = "验证码无效或登录状态已失效"
_SMS_VERIFY_FAILED_MESSAGE = "短信登录完成失败，请稍后重试"
_COOKIE_VALIDATION_FAILED_MESSAGE = "Cookie验证失败，请重新登录"
_COOKIE_FORMAT_INVALID_MESSAGE = "Cookie格式不正确"
_COOKIE_LOGIN_FAILED_MESSAGE = "Cookie登录失败，请稍后重试"
_QR_LOGIN_FAILED_MESSAGE = "二维码登录失败，请稍后重试"


# --------------- helpers ---------------


def _set_session_cookie(response: Response, session_id: str, max_age: int) -> None:
    """统一设置 session cookie。"""
    response.set_cookie(
        COOKIE_NAME,
        session_id,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=max_age,
    )


# --------------- models ---------------


class QRInitResponse(BaseModel):
    session_id: str = Field(..., description="会话ID，用于后续轮询")
    qr_image: str = Field(
        ..., description="Base64编码的二维码图片，格式为data:image/png;base64,..."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc123xyz",
                "qr_image": "data:image/png;base64,iVBORw0KGgo...",
            }
        }


class StatusResponse(BaseModel):
    authenticated: bool = Field(..., description="是否已认证")
    state: Optional[str] = Field(None, description="认证状态：init/qr_ready/active等")

    class Config:
        json_schema_extra = {"example": {"authenticated": True, "state": "active"}}


class SimpleResponse(BaseModel):
    status: str = Field(..., description="操作状态")
    session_id: Optional[str] = Field(None, description="更新后的会话ID")

    class Config:
        json_schema_extra = {"example": {"status": "ok"}}


class CookieLoginResponse(BaseModel):
    status: str = Field(..., description="登录状态")
    student_id: str = Field(..., description="学号")
    student_name: Optional[str] = Field(None, description="学生姓名")
    session_id: Optional[str] = Field(None, description="会话ID")

    class Config:
        json_schema_extra = {
            "example": {"status": "success", "student_id": "41234567", "student_name": "张三"}
        }


class SmsRequest(BaseModel):
    phone: str = Field(..., description="手机号码", example="13800138000")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确")
        return v


class SmsVerifyRequest(BaseModel):
    phone: str = Field(..., description="手机号码", example="13800138000")
    code: str = Field(..., description="短信验证码", example="123456")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确")
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not re.match(r"^\d{4,6}$", v):
            raise ValueError("验证码格式不正确，应为4-6位数字")
        return v


class CookieLoginRequest(BaseModel):
    cookies: str = Field(
        ...,
        description="Cookie字符串，格式: 'INCO=xxx; SESSION=yyy'",
        example="INCO=abc123; SESSION=xyz789",
    )


@router.post("/qr/init", response_model=QRInitResponse, summary="初始化二维码登录")
async def qr_init(response: Response, ustb_sid: Optional[str] = Cookie(None)):
    """
    ## 业务说明
    初始化微信扫码登录流程，生成登录二维码。

    ## 使用流程
    1. 调用此接口获取二维码图片和session_id
    2. 前端展示二维码供用户扫描
    3. 使用返回的session_id调用 `/qr/status` 轮询登录状态
    4. 登录成功后调用 `/qr/complete` 完成认证

    ## 注意事项
    - 二维码有效期约5分钟
    - 接口会自动设置session cookie (ustb_sid)
    - 二维码图片为Base64编码，可直接用于img标签的src属性
    - 如果已有有效的authenticated session，会复用该session
    """
    existing_session = store.get(ustb_sid) if ustb_sid else None
    if existing_session and existing_session.authenticated:
        raise HTTPException(409, "Already authenticated")

    session_id, session = store.create()
    try:
        qr_bytes = await auth_service.init_qr_auth(session)
    except Exception:
        store.delete(session_id)
        raise HTTPException(502, _QR_INIT_FAILED_MESSAGE)

    _set_session_cookie(response, session_id, SESSION_MAX_AGE)
    return {
        "session_id": session_id,
        "qr_image": f"data:image/png;base64,{base64.b64encode(qr_bytes).decode()}",
    }


@router.get("/qr/poll", summary="轮询二维码登录状态（非SSE）")
async def qr_poll(ustb_sid: Optional[str] = Cookie(None)):
    """
    ## 业务说明
    非SSE方式轮询二维码扫码状态，适用于不支持SSE的客户端（如微信小程序）。

    ## 使用流程
    1. 调用 `/qr/init` 获取二维码后
    2. 每隔2秒调用此接口轮询状态
    3. 收到 success 后调用 `/qr/complete` 完成登录

    ## 状态说明
    - `waiting`: 等待扫码
    - `scanned`: 已扫码，等待确认
    - `success`: 登录成功
    - `expired`: 二维码已过期
    """
    if not ustb_sid:
        raise HTTPException(401, "No session")
    session = store.get(ustb_sid)
    if not session:
        raise HTTPException(401, "Session expired")

    if session.last_error:
        return {"status": "error", "message": _QR_LOGIN_FAILED_MESSAGE}

    if session.state == AuthState.QR_READY:
        await auth_service.start_qr_background_monitor(session)

    state = session.state
    if state == AuthState.ACTIVE:
        return {"status": "success"}
    elif state == AuthState.CONFIRMED:
        return {"status": "scanned"}
    elif state == AuthState.EXPIRED:
        return {"status": "expired"}
    else:
        return {"status": "waiting"}


@router.get("/qr/status", summary="轮询二维码登录状态")
async def qr_status(ustb_sid: Optional[str] = Cookie(None)):
    """
    ## 业务说明
    使用Server-Sent Events (SSE)实时推送二维码扫码状态。

    ## 使用流程
    1. 前端使用EventSource连接此接口
    2. 服务器会持续推送状态更新
    3. 收到success状态后，调用 `/qr/complete` 完成登录

    ## 状态说明
    - `waiting`: 等待扫码
    - `scanned`: 已扫码，等待确认
    - `success`: 登录成功
    - `expired`: 二维码已过期
    - `error`: 发生错误

    ## 注意事项
    - 需要携带 ustb_sid cookie
    - 使用SSE协议，前端需使用EventSource API
    - 连接会在收到终态(success/expired/error)后自动关闭
    """
    if not ustb_sid:
        raise HTTPException(401, "No session")
    session = store.get(ustb_sid)
    if not session:
        raise HTTPException(401, "Session expired")

    async def event_generator():
        async for event in auth_service.poll_qr_status(session):
            yield {"event": "status", "data": json.dumps(event)}
            if event.get("status") in ("success", "expired", "error"):
                break
            await asyncio.sleep(0.1)

    return EventSourceResponse(event_generator())


@router.post("/qr/complete", response_model=SimpleResponse, summary="完成二维码登录")
async def qr_complete(response: Response, ustb_sid: Optional[str] = Cookie(None)):
    """
    ## 业务说明
    完成二维码登录流程，刷新session并设置长期cookie。

    ## 使用流程
    1. 在 `/qr/status` 收到success状态后调用此接口
    2. 服务器会轮换session ID（安全措施）
    3. 设置新的session cookie

    ## 注意事项
    - 必须在认证成功后调用
    - 会自动更新cookie，前端无需处理
    - 调用后即可访问需要认证的API
    """
    if not ustb_sid:
        raise HTTPException(401, "No session")
    session = store.get(ustb_sid)
    if session:
        logger.info(
            "QR login completion requested: state=%s authenticated=%s",
            session.state,
            session.authenticated,
        )
    if not session or session.state != AuthState.ACTIVE:
        raise HTTPException(401, "Not authenticated")

    new_id = store.rotate(ustb_sid)
    if new_id:
        _set_session_cookie(response, new_id, SESSION_TTL)
    return {"status": "ok", "session_id": new_id or ustb_sid}


@router.post("/sms/init", response_model=dict, summary="初始化短信登录")
async def sms_init(response: Response):
    """
    ## 业务说明
    初始化短信验证码登录流程。

    ## 使用流程
    1. 调用此接口初始化session
    2. 调用 `/sms/send` 发送验证码
    3. 调用 `/sms/verify` 验证验证码

    ## 注意事项
    - 接口会自动设置session cookie
    - session有效期24小时
    """
    session_id, session = store.create()
    try:
        await auth_service.init_sms_auth(session)
    except Exception:
        store.delete(session_id)
        raise HTTPException(502, _SMS_INIT_FAILED_MESSAGE)

    _set_session_cookie(response, session_id, SESSION_MAX_AGE)
    return {"session_id": session_id}


@router.post("/sms/send", response_model=SimpleResponse, summary="发送短信验证码")
async def sms_send(req: SmsRequest, ustb_sid: Optional[str] = Cookie(None)):
    """
    ## 业务说明
    向指定手机号发送短信验证码。

    ## 使用流程
    1. 先调用 `/sms/init` 初始化
    2. 调用此接口发送验证码到手机
    3. 用户收到验证码后，调用 `/sms/verify` 验证

    ## 注意事项
    - 手机号必须是已在教务系统注册的号码
    - 验证码有效期通常为5分钟
    - 发送间隔限制：60秒内只能发送一次
    - 如果频繁发送会返回429错误
    """
    if not ustb_sid:
        raise HTTPException(401, "No session")
    session = store.get(ustb_sid)
    if not session:
        raise HTTPException(401, "Session expired")

    # 频率限制
    sms_rate_limiter.check(f"sms:{req.phone}")

    try:
        await auth_service.send_sms(session, req.phone)
    except APIError as exc:
        error_message = str(exc)
        if "201" in error_message or "发送间隔过短" in error_message:
            raise HTTPException(429, _SMS_SEND_RATE_LIMITED_MESSAGE)
        raise HTTPException(502, _SMS_SEND_FAILED_MESSAGE)
    except Exception:
        raise HTTPException(502, _SMS_SEND_FAILED_MESSAGE)
    return {"status": "sent"}


@router.post("/sms/verify", response_model=SimpleResponse, summary="验证短信验证码")
async def sms_verify(
    req: SmsVerifyRequest, response: Response, ustb_sid: Optional[str] = Cookie(None)
):
    """
    ## 业务说明
    验证短信验证码并完成登录。

    ## 使用流程
    1. 用户输入收到的验证码
    2. 调用此接口验证
    3. 验证成功后即可访问需要认证的API

    ## 注意事项
    - 验证码错误会返回401错误
    - 验证成功后会自动轮换session ID
    - 会设置新的session cookie
    """
    if not ustb_sid:
        raise HTTPException(401, "No session")
    session = store.get(ustb_sid)
    if not session:
        raise HTTPException(401, "Session expired")

    try:
        await auth_service.verify_sms(session, req.phone, req.code)
    except (APIError, ValueError):
        raise HTTPException(401, _SMS_VERIFY_INVALID_MESSAGE)
    except Exception as exc:
        logger.error("SMS verification failed: %s", type(exc).__name__)
        raise HTTPException(502, _SMS_VERIFY_FAILED_MESSAGE)

    new_id = store.rotate(ustb_sid)
    if new_id:
        _set_session_cookie(response, new_id, SESSION_MAX_AGE)
    return {"status": "ok", "session_id": new_id or ustb_sid}


@router.get("/status", response_model=StatusResponse, summary="检查认证状态")
async def auth_status(ustb_sid: Optional[str] = Cookie(None)):
    """
    ## 业务说明
    检查当前用户的认证状态，用于判断是否需要登录。

    ## 使用场景
    - 页面加载时检查登录状态
    - 路由守卫判断是否需要跳转登录页
    - 定期检查session是否过期

    ## 返回说明
    - `authenticated: true` - 已登录，可以访问受保护的API
    - `authenticated: false` - 未登录或session已过期
    - `state` - 当前认证状态（仅在已登录时返回）

    ## 注意事项
    - 此接口不会抛出401错误，始终返回200
    - 即使没有cookie也会返回 `authenticated: false`
    """
    if not ustb_sid:
        return {"authenticated": False}
    session = store.get(ustb_sid)
    if not session:
        return {"authenticated": False}
    return {"authenticated": session.state == AuthState.ACTIVE, "state": session.state.value}


@router.post("/logout", response_model=SimpleResponse, summary="退出登录")
async def logout(response: Response, ustb_sid: Optional[str] = Cookie(None)):
    """
    ## 业务说明
    退出登录，清除session和cookie。

    ## 使用流程
    1. 用户点击退出按钮
    2. 调用此接口
    3. 前端跳转到登录页

    ## 注意事项
    - 会清除服务器端的session数据
    - 会删除客户端的cookie
    - 即使没有有效session也会返回成功
    """
    if ustb_sid:
        store.delete(ustb_sid)
    response.delete_cookie(COOKIE_NAME)
    return {"status": "ok"}


@router.post("/cookie/login", response_model=CookieLoginResponse, summary="使用Cookie登录")
async def cookie_login(req: CookieLoginRequest, response: Response):
    """
    ## 业务说明
    使用从浏览器复制的USTB教务系统Cookie直接登录，适合高级用户快速登录。

    ## 使用流程
    1. 用户在浏览器中登录USTB教务系统
    2. 从浏览器开发者工具复制Cookie字符串
    3. 粘贴到登录表单并提交
    4. 系统验证Cookie有效性
    5. 验证成功后创建session

    ## Cookie格式
    ```
    INCO=abc123; SESSION=xyz789
    ```

    ## 验证机制
    - 系统会使用提供的Cookie访问教务系统API
    - 尝试获取学生信息以验证Cookie有效性
    - 如果能成功获取学号和姓名，则认为Cookie有效

    ## 注意事项
    - Cookie必须包含USTB教务系统的认证信息
    - Cookie过期会返回401错误
    - 验证成功后会加密保存Cookie，支持后端重启后恢复
    - 会自动设置session cookie

    ## 安全提示
    - Cookie包含敏感信息，请勿分享给他人
    - 建议定期更换Cookie
    """
    import httpx

    session_id: Optional[str] = None
    try:
        cookie_dict = {}
        for item in req.cookies.split(";"):
            item = item.strip()
            if not item:
                continue
            if "=" not in item:
                raise HTTPException(400, _COOKIE_FORMAT_INVALID_MESSAGE)
            key, value = item.split("=", 1)
            key = key.strip()
            if not key:
                raise HTTPException(400, _COOKIE_FORMAT_INVALID_MESSAGE)
            cookie_dict[key] = value.strip()

        if not cookie_dict:
            raise HTTPException(400, _COOKIE_FORMAT_INVALID_MESSAGE)

        session_id, session = store.create()

        for key, value in cookie_dict.items():
            session.client.cookies.set(key, value, domain=".ustb.edu.cn")

        try:
            resp = session.client.post("https://byyt.ustb.edu.cn/UserManager/queryxsxx")
            resp.raise_for_status()
            data = resp.json()

            if not data or "XH" not in data:
                store.delete(session_id)
                raise HTTPException(401, "Cookie无效或已过期")

            student_info = data
            student_id = student_info.get("XH")

            if not student_id:
                store.delete(session_id)
                raise HTTPException(401, "无法获取学生信息")

            session.state = AuthState.ACTIVE
            session.authenticated = True
            session.student_id = student_id

            store.persist(session_id, student_id, cookie_dict)

            _set_session_cookie(response, session_id, SESSION_MAX_AGE)

            return {
                "status": "success",
                "student_id": student_id,
                "student_name": student_info.get("XM"),
                "session_id": session_id,
            }

        except httpx.HTTPError:
            store.delete(session_id)
            raise HTTPException(401, _COOKIE_VALIDATION_FAILED_MESSAGE)

    except HTTPException:
        raise
    except Exception as exc:
        if session_id:
            store.delete(session_id)
        logger.error("Cookie login failed: %s", type(exc).__name__)
        raise HTTPException(502, _COOKIE_LOGIN_FAILED_MESSAGE)
