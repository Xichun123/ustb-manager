"""
校园网管理 API 路由
使用API接口获取数据，避免HTML解析
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
import httpx

from ..services.wifi_service import (
    login_vpn_only,
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


class WifiLoginRequest(BaseModel):
    password: str


class WifiStandaloneLoginRequest(BaseModel):
    student_id: str
    password: str


def get_student_id(request: Request) -> str:
    """从教务系统 session 或独立模式 cookie 获取学号"""
    # 优先从教务系统 session 获取
    session_id = request.cookies.get("ustb_sid")
    if session_id:
        session = session_store.get(session_id)
        if session and session.student_id:
            return session.student_id

    # 尝试从独立模式 cookie 获取
    wifi_student_id = request.cookies.get("wifi_student_id")
    if wifi_student_id:
        return wifi_student_id

    raise HTTPException(status_code=401, detail="请先登录")


async def get_or_create_wifi_session(student_id: str) -> WifiSession:
    """获取或创建校园网会话"""
    # 1. 检查现有会话（内存中）
    session = wifi_store.get(student_id)
    if session:
        return session

    # 2. 检查是否有保存的凭据
    cred = wifi_credential_store.get(student_id)
    if not cred or not cred.password:
        raise HTTPException(status_code=401, detail="请先登录校园网")

    # 3. 如果有保存的 cookie，先尝试用它创建会话（快速路径）
    if cred.vpn_cookie:
        print(f"[DEBUG] Trying saved cookie for {student_id}")
        client = httpx.AsyncClient(follow_redirects=True, timeout=60.0)
        client.cookies.set("wengine_vpn_ticketelib_ustb_edu_cn", cred.vpn_cookie, domain="elib.ustb.edu.cn")

        # 验证 cookie 是否有效：尝试获取流量信息
        try:
            result = await get_flow_info(client, cred.vpn_cookie)
            if result:
                print(f"[DEBUG] Saved cookie is valid!")
                session = WifiSession(
                    client=client,
                    student_id=student_id,
                    cookie=cred.vpn_cookie,
                )
                wifi_store.set(student_id, session)
                return session
            else:
                print(f"[DEBUG] Saved cookie returned no data, will re-login")
                await client.aclose()
        except Exception as e:
            print(f"[DEBUG] Saved cookie failed: {e}, will re-login")
            await client.aclose()

    # 4. Cookie 无效或不存在，使用 Playwright 重新登录（慢速路径）
    print(f"[DEBUG] Using Playwright to login for {student_id}")
    try:
        vpn_cookie, client = await login_vpn_only(student_id, cred.password)
        if not vpn_cookie or not client:
            raise HTTPException(status_code=401, detail="校园网密码错误，请重新登录")

        # 创建新会话
        session = WifiSession(
            client=client,
            student_id=student_id,
            cookie=vpn_cookie,
        )
        wifi_store.set(student_id, session)
        wifi_credential_store.update_cookie(student_id, vpn_cookie)
        return session
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


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

    # 检查是否有有效会话
    session = wifi_store.get(wifi_student_id)
    if session:
        return {"logged_in": True, "student_id": wifi_student_id, "has_credential": True}

    # 检查是否有保存的凭据
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

    # 检查是否有有效会话
    session = wifi_store.get(student_id)
    if session:
        return {"logged_in": True, "has_credential": True}

    # 检查是否有保存的凭据
    has_credential = wifi_credential_store.has_credential(student_id)

    return {"logged_in": False, "has_credential": has_credential}


@router.post("/login")
async def wifi_login(request: Request, body: WifiLoginRequest):
    """
    登录校园网（使用学号 + 校园网密码）

    学号从教务系统 session 获取，只需要提供密码
    """
    student_id = get_student_id(request)

    try:
        vpn_cookie, client = await login_vpn_only(student_id, body.password)
        if not vpn_cookie or not client:
            raise HTTPException(status_code=401, detail="校园网密码错误")

        # 保存凭据
        wifi_credential_store.save_credential(student_id, body.password, vpn_cookie)

        # 创建会话
        session = WifiSession(
            client=client,
            student_id=student_id,
            cookie=vpn_cookie,
        )
        wifi_store.set(student_id, session)

        return {"success": True, "message": "登录成功"}
    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="校园网服务响应超时，请稍后重试")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


@router.post("/standalone-login")
async def wifi_standalone_login(response: Response, body: WifiStandaloneLoginRequest):
    """
    独立登录校园网（不需要教务系统登录）

    需要提供学号和密码，登录成功后设置 wifi_student_id cookie
    """
    try:
        vpn_cookie, client = await login_vpn_only(body.student_id, body.password)
        if not vpn_cookie or not client:
            raise HTTPException(status_code=401, detail="学号或密码错误")

        # 保存凭据
        wifi_credential_store.save_credential(body.student_id, body.password, vpn_cookie)

        # 创建会话
        session = WifiSession(
            client=client,
            student_id=body.student_id,
            cookie=vpn_cookie,
        )
        wifi_store.set(body.student_id, session)

        # 设置 cookie 用于独立模式
        response.set_cookie(
            key="wifi_student_id",
            value=body.student_id,
            httponly=True,
            max_age=30 * 24 * 60 * 60,  # 30天
            samesite="lax",
        )

        return {"success": True, "message": "登录成功", "student_id": body.student_id}
    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="校园网服务响应超时，请稍后重试")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


@router.post("/logout")
async def wifi_logout(request: Request):
    """登出校园网（清除保存的凭据）"""
    student_id = get_student_id(request)

    # 关闭客户端
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
        result = await get_flow_info(session.client, session.cookie)
        if not result:
            raise HTTPException(status_code=500, detail="获取流量信息失败")

        import time
        return {
            "account": result.get("account", student_id),
            "balance": result.get("balance", 0.0),
            "used_flow": result.get("used_flow", 0.0),
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
        devices = await get_bound_devices(session.client, session.cookie)
        return {
            "total": len(devices),
            "devices": devices
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取设备列表失败: {str(e)}")


class UnbindMacRequest(BaseModel):
    mac_address: str


@router.get("/mac-vendor")
async def get_mac_vendor(mac: str):
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
        success = await unbind_mac(session.client, session.cookie, body.mac_address)
        if success:
            return {"success": True, "message": "解绑成功"}
        else:
            raise HTTPException(status_code=500, detail="解绑失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解绑失败: {str(e)}")


@router.get("/bills")
async def get_bills(request: Request, year: int = None):
    """
    获取历史账单

    Args:
        year: 年份（可选，默认当前年份）

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
        result = await get_month_pay(session.client, session.cookie, year)
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
        result = await get_payments(session.client, session.cookie, start_date, end_date)
        if not result:
            raise HTTPException(status_code=500, detail="获取充值明细失败")

        return {"start_date": start_date, "end_date": end_date, **result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取充值明细失败: {str(e)}")
