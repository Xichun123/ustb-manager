"""
校园网管理 API 路由
使用API接口获取数据，避免HTML解析
"""

import logging
import re
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field, field_validator
import httpx

from ..services.wifi_service import (
    create_authenticated_client,
    create_login_challenge,
    login_with_captcha,
    get_flow_info,
    get_bound_devices,
    unbind_mac,
    get_month_pay,
    get_payments,
    WifiSession,
    wifi_store,
)
from ..services.wifi_store import wifi_credential_store
from ..services.session_store import store as session_store

router = APIRouter(prefix="/wifi", tags=["校园网管理"])
logger = logging.getLogger(__name__)


class WifiLoginRequest(BaseModel):
    password: str
    challenge_token: Optional[str] = None
    captcha_code: Optional[str] = None


class WifiStandaloneLoginRequest(BaseModel):
    student_id: str = Field(..., min_length=8, max_length=13, pattern=r"^[Uu]?\d{8,12}$")
    password: str
    challenge_token: Optional[str] = None
    captcha_code: Optional[str] = None


class WifiLoginChallengeRequest(BaseModel):
    student_id: Optional[str] = Field(
        default=None, min_length=8, max_length=13, pattern=r"^[Uu]?\d{8,12}$"
    )
    password: Optional[str] = None


class UnbindMacRequest(BaseModel):
    mac_address: str

    @field_validator("mac_address")
    @classmethod
    def validate_mac(cls, v: str) -> str:
        # 支持 XX:XX:XX:XX:XX:XX / XX-XX-XX-XX-XX-XX / XXXXXXXXXXXX
        cleaned = re.sub(r"[:\-]", "", v).upper()
        if not re.match(r"^[0-9A-F]{12}$", cleaned):
            raise ValueError("MAC地址格式不正确")
        return v


def get_student_id(request: Request) -> str:
    """从教务系统 session 或独立模式 cookie 获取学号"""
    session_id = request.cookies.get("ustb_sid")
    if session_id:
        session = session_store.get(session_id)
        if session and session.student_id:
            return session.student_id

    wifi_student_id = request.cookies.get("wifi_student_id")
    if wifi_student_id:
        return wifi_student_id

    raise HTTPException(status_code=401, detail="请先登录")


async def get_or_create_wifi_session(student_id: str) -> WifiSession:
    """获取或创建校园网会话"""
    session = wifi_store.get(student_id)
    if session:
        return session

    cred = wifi_credential_store.get(student_id)
    if not cred or not cred.get_password():
        raise HTTPException(status_code=401, detail="请先登录校园网")

    if cred.vpn_cookie:
        logger.debug("Trying saved cookie for %s", student_id)
        login_mode = getattr(cred, "login_mode", "webvpn") or "webvpn"
        client = create_authenticated_client(cred.vpn_cookie, login_mode)

        try:
            result = await get_flow_info(client, cred.vpn_cookie, login_mode)
            if result:
                logger.debug("Saved cookie is valid!")
                session = WifiSession(
                    client=client,
                    student_id=student_id,
                    cookie=cred.vpn_cookie,
                    mode=login_mode,
                )
                wifi_store.set(student_id, session)
                return session
            else:
                logger.debug("Saved cookie returned no data")
                await client.aclose()
        except Exception as e:
            logger.debug("Saved cookie failed: %s", e)
            await client.aclose()

    raise HTTPException(status_code=401, detail="校园网会话已过期，请重新输入验证码登录")


@router.get("/standalone-status")
async def get_standalone_status(request: Request):
    """
    获取独立模式校园网登录状态（不需要教务系统登录）

    Returns:
        {
            "logged_in": 是否已登录,
            "student_id": 学号（如果已登录）,
            "has_credential": 是否有保存的凭据
        }
    """
    wifi_student_id = request.cookies.get("wifi_student_id")
    if not wifi_student_id:
        return {"logged_in": False, "student_id": None, "has_credential": False}

    session = wifi_store.get(wifi_student_id)
    if session:
        return {"logged_in": True, "student_id": wifi_student_id, "has_credential": True}

    has_credential = wifi_credential_store.has_credential(wifi_student_id)
    return {"logged_in": False, "student_id": wifi_student_id, "has_credential": has_credential}


@router.get("/status")
async def get_wifi_status(request: Request):
    """
    获取校园网登录状态

    Returns:
        {
            "logged_in": 是否已登录,
            "has_credential": 是否有保存的凭据
        }
    """
    student_id = get_student_id(request)

    session = wifi_store.get(student_id)
    if session:
        return {"logged_in": True, "has_credential": True}

    has_credential = wifi_credential_store.has_credential(student_id)
    return {"logged_in": False, "has_credential": has_credential}


@router.post("/login/challenge")
async def wifi_login_challenge(request: Request, body: Optional[WifiLoginChallengeRequest] = None):
    """获取校园网验证码挑战。"""
    try:
        student_id = None
        if body and body.student_id:
            student_id = body.student_id.upper()
        else:
            try:
                student_id = get_student_id(request)
            except HTTPException:
                student_id = None

        challenge = await create_login_challenge(
            student_id,
            body.password if body else None,
        )
        return {
            "challenge_token": challenge.token,
            "captcha_image": challenge.captcha_image,
            "mode": challenge.mode,
            "expires_in": 300,
        }
    except RuntimeError as e:
        detail = str(e) or e.__class__.__name__
        raise HTTPException(status_code=400, detail=f"获取验证码失败: {detail}")
    except Exception as e:
        logger.exception("WiFi challenge init failed")
        detail = str(e) or e.__class__.__name__
        raise HTTPException(status_code=500, detail=f"获取验证码失败: {detail}")


@router.post("/login")
async def wifi_login(request: Request, body: WifiLoginRequest):
    """
    登录校园网（使用学号 + 校园网密码）

    学号从教务系统 session 获取，只需要提供密码
    """
    student_id = get_student_id(request)

    try:
        if not body.challenge_token or not body.captcha_code:
            raise HTTPException(status_code=400, detail="请先获取并输入验证码")

        auth_cookie, client, login_mode = await login_with_captcha(
            student_id,
            body.password,
            body.challenge_token,
            body.captcha_code,
        )

        if not auth_cookie or not client:
            raise HTTPException(status_code=401, detail="验证码错误或校园网密码错误")

        wifi_credential_store.save_credential(
            student_id,
            body.password,
            auth_cookie,
            login_mode=login_mode,
        )

        session = WifiSession(
            client=client,
            student_id=student_id,
            cookie=auth_cookie,
            mode=login_mode,
        )
        wifi_store.set(student_id, session)

        return {"success": True, "message": "登录成功"}
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="校园网服务响应超时，请稍后重试")
    except Exception as e:
        logger.exception("WiFi login failed for %s", student_id)
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


@router.post("/standalone-login")
async def wifi_standalone_login(response: Response, body: WifiStandaloneLoginRequest):
    """
    独立登录校园网（不需要教务系统登录）

    需要提供学号和密码，登录成功后设置 wifi_student_id cookie
    """
    student_id = body.student_id.upper()
    try:
        if not body.challenge_token or not body.captcha_code:
            raise HTTPException(status_code=400, detail="请先获取并输入验证码")

        auth_cookie, client, login_mode = await login_with_captcha(
            student_id,
            body.password,
            body.challenge_token,
            body.captcha_code,
        )

        if not auth_cookie or not client:
            raise HTTPException(status_code=401, detail="验证码错误或学号密码错误")

        wifi_credential_store.save_credential(
            student_id,
            body.password,
            auth_cookie,
            login_mode=login_mode,
        )

        session = WifiSession(
            client=client,
            student_id=student_id,
            cookie=auth_cookie,
            mode=login_mode,
        )
        wifi_store.set(student_id, session)

        response.set_cookie(
            key="wifi_student_id",
            value=student_id,
            httponly=True,
            max_age=30 * 24 * 60 * 60,
            samesite="lax",
        )

        return {"success": True, "message": "登录成功", "student_id": student_id}
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="校园网服务响应超时，请稍后重试")
    except Exception as e:
        logger.exception("WiFi standalone login failed for %s", student_id)
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


@router.post("/logout")
async def wifi_logout(request: Request):
    """登出校园网（清除保存的凭据）"""
    student_id = get_student_id(request)

    session = wifi_store.get(student_id)
    if session and session.client:
        try:
            await session.client.aclose()
        except Exception:
            pass

    wifi_store.delete(student_id)
    wifi_credential_store.delete(student_id)

    return {"success": True, "message": "已退出校园网"}


@router.get("/flow")
async def get_flow(request: Request):
    """
    获取流量信息（包含账户信息、在线设备、历史记录）

    Returns:
        {
            "account": 账号,
            "balance": 余额(元),
            "used_flow": 已用流量(MB),
            "available_flow": 可用流量(MB),
            "status": 状态,
            "package": 套餐,
            "expire_date": 到期日期,
            "online_devices": 在线设备列表,
            "recent_history": 最近上网记录,
            "update_time": 更新时间
        }
    """
    student_id = get_student_id(request)
    session = await get_or_create_wifi_session(student_id)

    try:
        result = await get_flow_info(session.client, session.cookie, session.mode)
        if not result:
            raise HTTPException(status_code=500, detail="获取流量信息失败")

        import time

        return {
            "account": result.get("account", student_id),
            "balance": result.get("balance", 0.0),
            "used_flow": result.get("used_flow", 0.0),
            "used_flow_v4": result.get("used_flow_v4", 0.0),
            "used_flow_v6": result.get("used_flow_v6", 0.0),
            "available_flow": result.get("available_flow", 0.0),
            "status": result.get("status", "未知"),
            "package": result.get("package", ""),
            "expire_date": result.get("expire_date", ""),
            "online_devices": result.get("online_devices", []),
            "recent_history": result.get("recent_history", []),
            "update_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取流量信息失败: {str(e)}")


@router.get("/devices")
async def get_devices(request: Request):
    """
    获取绑定设备列表（我的设备）

    Returns:
        {
            "total": 设备总数,
            "devices": [
                {
                    "online": 是否在线,
                    "mac_address": MAC地址,
                    "terminal_info": 终端信息,
                    "last_login_time": 最近登录时间,
                    "last_login_ip": 最近登录IP,
                    "is_dumb_terminal": 是否哑终端,
                    "terminal_name": 终端名称
                }
            ]
        }
    """
    student_id = get_student_id(request)
    session = await get_or_create_wifi_session(student_id)

    try:
        devices = await get_bound_devices(session.client, session.cookie, session.mode)
        return {"total": len(devices), "devices": devices}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取设备列表失败: {str(e)}")


@router.get("/mac-vendor")
async def get_mac_vendor(
    mac: str = Query(..., description="MAC地址"),
):
    """
    查询MAC地址厂商（离线数据库）

    使用IEEE OUI数据库（约38000条记录）查询MAC地址对应的设备厂商。
    自动识别随机MAC地址（iOS/Android隐私保护功能生成的本地管理地址）。

    Args:
        mac: MAC地址，支持多种格式（XX-XX-XX-XX-XX-XX 或 XX:XX:XX:XX:XX:XX 或 XXXXXXXXXXXX）

    Returns:
        {
            "vendor": 厂商名称（随机MAC返回"随机MAC"）,
            "is_random": 是否为随机MAC地址
        }
    """
    # 验证 MAC 地址格式
    cleaned = re.sub(r"[:\-]", "", mac).upper()
    if not re.match(r"^[0-9A-F]{12}$", cleaned):
        raise HTTPException(status_code=422, detail="MAC地址格式不正确")

    from ..services.mac_vendor import get_vendor

    return get_vendor(mac)


@router.post("/unbind-mac")
async def unbind_mac_address(request: Request, body: UnbindMacRequest):
    """
    解绑指定的MAC地址

    Args:
        mac_address: 要解绑的MAC地址（格式：XX-XX-XX-XX-XX-XX 或 XXXXXXXXXXXX）

    Returns:
        {
            "success": 是否成功,
            "message": 消息
        }
    """
    student_id = get_student_id(request)
    session = await get_or_create_wifi_session(student_id)

    try:
        success = await unbind_mac(session.client, session.cookie, body.mac_address, session.mode)
        if success:
            return {"success": True, "message": "解绑成功"}
        else:
            raise HTTPException(status_code=500, detail="解绑失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解绑失败: {str(e)}")


@router.get("/bills")
async def get_bills(
    request: Request,
    year: int = Query(None, ge=2000, le=2100, description="年份"),
):
    """
    获取历史账单

    Args:
        year: 年份（可选，默认当前年份，范围2000-2100）

    Returns:
        {
            "year": 查询年份,
            "summary": {
                "total_time": 总使用时长(分钟),
                "total_flow": 总使用流量(MB),
                "base_fee": 基本月租(元),
                "usage_fee": 时长/流量计费(元)
            },
            "bills": [{
                "start_time": 账单开始时间,
                "end_time": 账单结束时间,
                "package": 套餐,
                "base_fee": 基本月租,
                "usage_fee": 时长/流量计费,
                "duration_minutes": 使用时长,
                "used_flow_mb": 使用流量,
                "bill_time": 出账时间
            }]
        }
    """
    student_id = get_student_id(request)
    session = await get_or_create_wifi_session(student_id)

    if year is None:
        year = datetime.now().year

    try:
        result = await get_month_pay(session.client, session.cookie, year, session.mode)
        if not result:
            raise HTTPException(status_code=500, detail="获取账单失败")

        return {"year": year, **result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取账单失败: {str(e)}")


@router.get("/payments")
async def get_payment_records(request: Request, start_date: str = None, end_date: str = None):
    """
    获取充值明细

    Args:
        start_date: 开始日期（可选，默认一年前，格式 YYYY-MM-DD）
        end_date: 结束日期（可选，默认今天，格式 YYYY-MM-DD）

    Returns:
        {
            "start_date": 开始日期,
            "end_date": 结束日期,
            "total_amount": 充值总金额(元),
            "payments": [{
                "pay_time": 交费时间,
                "amount": 金额,
                "pay_type": 交费类型,
                "terminal": 受理终端,
                "remark": 备注
            }]
        }
    """
    student_id = get_student_id(request)
    session = await get_or_create_wifi_session(student_id)

    today = datetime.now()
    if end_date is None:
        end_date = today.strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (today.replace(year=today.year - 1)).strftime("%Y-%m-%d")

    try:
        result = await get_payments(
            session.client, session.cookie, start_date, end_date, session.mode
        )
        if not result:
            raise HTTPException(status_code=500, detail="获取充值明细失败")

        return {"start_date": start_date, "end_date": end_date, **result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取充值明细失败: {str(e)}")
