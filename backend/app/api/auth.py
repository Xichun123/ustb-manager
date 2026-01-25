import base64
import json
from fastapi import APIRouter, Response, HTTPException, Cookie
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from typing import Optional
from pydantic import BaseModel, Field
import asyncio

from ..config import COOKIE_NAME, COOKIE_SECURE, SESSION_TTL, SESSION_MAX_AGE
from ..services.session_store import store, AuthState
from ..services import auth_service
from ustb_sso._exceptions import APIError

router = APIRouter(prefix="/auth", tags=["auth"])


# Response Models
class QRInitResponse(BaseModel):
    session_id: str = Field(..., description="会话ID，用于后续轮询")
    qr_image: str = Field(..., description="Base64编码的二维码图片，格式为data:image/png;base64,...")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc123xyz",
                "qr_image": "data:image/png;base64,iVBORw0KGgo..."
            }
        }


class StatusResponse(BaseModel):
    authenticated: bool = Field(..., description="是否已认证")
    state: Optional[str] = Field(None, description="认证状态：init/qr_ready/active等")
    
    class Config:
        json_schema_extra = {
            "example": {
                "authenticated": True,
                "state": "active"
            }
        }


class SimpleResponse(BaseModel):
    status: str = Field(..., description="操作状态")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok"
            }
        }


class CookieLoginResponse(BaseModel):
    status: str = Field(..., description="登录状态")
    student_id: str = Field(..., description="学号")
    student_name: Optional[str] = Field(None, description="学生姓名")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "student_id": "41234567",
                "student_name": "张三"
            }
        }


class SmsRequest(BaseModel):
    phone: str = Field(..., description="手机号码", example="13800138000")


class SmsVerifyRequest(BaseModel):
    phone: str = Field(..., description="手机号码", example="13800138000")
    code: str = Field(..., description="短信验证码", example="123456")


class CookieLoginRequest(BaseModel):
    cookies: str = Field(
        ..., 
        description="Cookie字符串，格式: 'INCO=xxx; SESSION=yyy'",
        example="INCO=abc123; SESSION=xyz789"
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
    # 检查是否已有有效的 authenticated session
    existing_session = store.get(ustb_sid) if ustb_sid else None
    if existing_session and existing_session.authenticated:
        # 已登录，返回 409 冲突，前端应该跳转到 dashboard 而不是显示二维码
        raise HTTPException(409, "Already authenticated")

    session_id, session = store.create()
    try:
        qr_bytes = await auth_service.init_qr_auth(session)
    except Exception as e:
        store.delete(session_id)
        raise HTTPException(502, str(e))

    response.set_cookie(
        COOKIE_NAME, session_id,
        httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=SESSION_MAX_AGE
    )
    return {
        "session_id": session_id,
        "qr_image": f"data:image/png;base64,{base64.b64encode(qr_bytes).decode()}"
    }


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
    if not session or session.state != AuthState.ACTIVE:
        raise HTTPException(401, "Not authenticated")

    new_id = store.rotate(ustb_sid)
    if new_id:
        response.set_cookie(
            COOKIE_NAME, new_id,
            httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=SESSION_TTL
        )
    return {"status": "ok"}


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
    except Exception as e:
        store.delete(session_id)
        raise HTTPException(502, str(e))

    response.set_cookie(
        COOKIE_NAME, session_id,
        httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=SESSION_MAX_AGE
    )
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

    try:
        await auth_service.send_sms(session, req.phone)
    except APIError as e:
        error_msg = str(e)
        if "201" in error_msg or "发送间隔过短" in error_msg:
            raise HTTPException(429, error_msg)
        raise HTTPException(502, error_msg)
    except Exception as e:
        raise HTTPException(502, str(e))
    return {"status": "sent"}


@router.post("/sms/verify", response_model=SimpleResponse, summary="验证短信验证码")
async def sms_verify(req: SmsVerifyRequest, response: Response, ustb_sid: Optional[str] = Cookie(None)):
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
    except Exception as e:
        raise HTTPException(401, str(e))

    new_id = store.rotate(ustb_sid)
    if new_id:
        response.set_cookie(
            COOKIE_NAME, new_id,
            httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=SESSION_MAX_AGE
        )
    return {"status": "ok"}


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
    - 验证成功后会保存Cookie到本地，支持后端重启后恢复
    - 会自动设置session cookie
    
    ## 安全提示
    - Cookie包含敏感信息，请勿分享给他人
    - 建议定期更换Cookie
    """
    from ..services import cookie_store
    import httpx
    
    try:
        # 解析Cookie字符串
        cookie_dict = {}
        for item in req.cookies.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookie_dict[key.strip()] = value.strip()
        
        # 创建新的session
        session_id, session = store.create()
        
        # 设置cookies到httpx client
        for key, value in cookie_dict.items():
            session.client.cookies.set(key, value, domain=".ustb.edu.cn")
        
        # 验证Cookie是否有效 - 尝试获取学生信息
        try:
            resp = session.client.post("https://byyt.ustb.edu.cn/UserManager/queryxsxx")
            resp.raise_for_status()
            data = resp.json()

            # API直接返回学生信息，不包装在code/content结构中
            # 如果返回空或包含错误信息则认为Cookie无效
            if not data or "XH" not in data:
                store.delete(session_id)
                raise HTTPException(401, "Cookie无效或已过期")

            student_info = data
            student_id = student_info.get("XH")
            
            if not student_id:
                store.delete(session_id)
                raise HTTPException(401, "无法获取学生信息")
            
            # 更新session状态
            session.state = AuthState.ACTIVE
            session.authenticated = True
            session.student_id = student_id

            # 保存Cookie到本地
            cookie_store.save_cookies(student_id, cookie_dict)

            # 持久化session映射，支持后端重启后恢复
            store.persist(session_id, student_id)

            # 设置session cookie
            response.set_cookie(
                COOKIE_NAME, session_id,
                httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=SESSION_MAX_AGE
            )
            
            return {
                "status": "success",
                "student_id": student_id,
                "student_name": student_info.get("XM")
            }
            
        except httpx.HTTPError as e:
            store.delete(session_id)
            raise HTTPException(401, f"Cookie验证失败: {str(e)}")
            
    except Exception as e:
        raise HTTPException(400, f"Cookie格式错误: {str(e)}")