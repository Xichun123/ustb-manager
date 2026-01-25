"""
校园网管理服务 - 校内直连模式（不通过 WebVPN）
适用于部署在校园网内的服务器
"""
import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Optional
import httpx
from bs4 import BeautifulSoup


# 校园网后台管理系统（202.204.60.7:8080）- 直连模式
AUTH_BACKEND_LOGIN_URL = "http://202.204.60.7:8080/nav_login"
AUTH_BACKEND_VERIFY_URL = "http://202.204.60.7:8080/LoginAction.action"
AUTH_BACKEND_REFRESH_URL = "http://202.204.60.7:8080/refreshaccount"

# Self 系统（202.204.60.7）- 直连模式
AUTH_SELF_LOGIN_URL = "http://202.204.60.7/Self/login/"
AUTH_SELF_VERIFY_URL = "http://202.204.60.7/Self/login/verify"
AUTH_SELF_DASHBOARD_URL = "http://202.204.60.7/Self/dashboard"


@dataclass
class WifiSession:
    """校园网会话"""
    client: httpx.AsyncClient
    student_id: str
    session_id: str  # JSESSIONID 或其他 session cookie
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)


class WifiSessionStore:
    """校园网会话存储"""

    def __init__(self):
        self._sessions: dict[str, WifiSession] = {}

    def get(self, student_id: str) -> Optional[WifiSession]:
        session = self._sessions.get(student_id)
        if session:
            session.last_seen = time.time()
        return session

    def set(self, student_id: str, session: WifiSession):
        self._sessions[student_id] = session

    def delete(self, student_id: str):
        session = self._sessions.pop(student_id, None)
        if session:
            pass


# 全局会话存储
wifi_store = WifiSessionStore()


async def login_backend_system(account: str, password: str) -> tuple[Optional[str], Optional[httpx.AsyncClient]]:
    """
    登录 8080 端口的后台管理系统（校内直连）

    Args:
        account: 学号
        password: 校园网密码

    Returns:
        (session_id, client) 成功返回 session ID 和客户端，失败返回 (None, None)
    """
    client = httpx.AsyncClient(follow_redirects=True, timeout=60.0)

    try:
        print(f"[DEBUG] Logging into backend system (port 8080) - Direct mode...")

        # 1. 访问后台管理系统登录页获取 checkcode
        res = await client.get(AUTH_BACKEND_LOGIN_URL)
        print(f"[DEBUG] Backend login page status: {res.status_code}")

        # 提取 checkcode（使用 JavaScript 变量格式）
        checkcode_match = re.search(r'var checkcode="([^"]*)"', res.text)
        if not checkcode_match:
            await client.aclose()
            raise Exception("无法获取 checkcode")
        checkcode = checkcode_match.group(1)
        print(f"[DEBUG] Extracted checkcode: {checkcode}")

        # 2. 登录后台管理系统
        # 密码需要 MD5 哈希
        password_md5 = hashlib.md5(password.encode()).hexdigest()
        print(f"[DEBUG] Password MD5: {password_md5}")

        # 构建登录请求体
        login_body = f"account={account}&password={password_md5}&code=&checkcode={checkcode}&Submit=%E7%99%BB+%E5%BD%95"

        # 发送登录请求
        res = await client.post(
            AUTH_BACKEND_VERIFY_URL,
            content=login_body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Upgrade-Insecure-Requests": "1",
                "Referer": AUTH_BACKEND_LOGIN_URL,
            }
        )

        print(f"[DEBUG] Backend login response status: {res.status_code}")
        response_text = res.text

        # 检查登录结果
        if "账号或密码出现错误" in response_text or "登录密码不正确" in response_text:
            print("[DEBUG] Backend system login FAILED - wrong credentials")
            await client.aclose()
            return None, None

        # 提取 JSESSIONID
        session_id = None
        for cookie in client.cookies.jar:
            if cookie.name == "JSESSIONID":
                session_id = cookie.value
                break

        if not session_id:
            await client.aclose()
            raise Exception("无法获取 JSESSIONID")

        print("[DEBUG] Backend system login successful!")
        print(f"[DEBUG] JSESSIONID: {session_id}")

        return session_id, client

    except Exception as e:
        await client.aclose()
        raise e


async def login_self_system(account: str, password: str) -> tuple[Optional[str], Optional[httpx.AsyncClient]]:
    """
    登录 Self 系统（校内直连）

    Args:
        account: 学号
        password: 校园网密码

    Returns:
        (session_id, client) 成功返回 session ID 和客户端，失败返回 (None, None)
    """
    client = httpx.AsyncClient(follow_redirects=True, timeout=60.0)

    try:
        print(f"[DEBUG] Logging into Self system - Direct mode...")

        # 1. 访问 Self 登录页获取 checkcode
        res = await client.get(AUTH_SELF_LOGIN_URL)
        print(f"[DEBUG] Self login page status: {res.status_code}")

        # 提取 checkcode（使用 HTML input 格式）
        checkcode_match = re.search(r'name="checkcode"\s+value="([^"]*)"', res.text)
        if not checkcode_match:
            await client.aclose()
            raise Exception("无法获取 checkcode")
        checkcode = checkcode_match.group(1)
        print(f"[DEBUG] Extracted checkcode: {checkcode}")

        # 2. 登录 Self 系统
        # 密码需要 MD5 哈希
        password_md5 = hashlib.md5(password.encode()).hexdigest()
        print(f"[DEBUG] Password MD5: {password_md5}")

        # 发送登录请求
        res = await client.post(
            AUTH_SELF_VERIFY_URL,
            data={
                "foo": "",
                "bar": "",
                "checkcode": checkcode,
                "account": account,
                "password": password_md5,
                "code": "",
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": AUTH_SELF_LOGIN_URL,
            }
        )

        print(f"[DEBUG] Self login response status: {res.status_code}")
        print(f"[DEBUG] Self login response URL: {res.url}")

        # 检查是否重定向到 dashboard（登录成功）
        if "/Self/dashboard" in str(res.url):
            print("[DEBUG] Self system login successful!")

            # 提取 session cookie
            session_id = None
            for cookie in client.cookies.jar:
                if cookie.name in ["JSESSIONID", "SESSION"]:
                    session_id = cookie.value
                    break

            if not session_id:
                await client.aclose()
                raise Exception("无法获取 session ID")

            print(f"[DEBUG] Session ID: {session_id}")
            return session_id, client
        else:
            # 登录失败，重定向回登录页
            print("[DEBUG] Self system login FAILED - redirected back to login")
            await client.aclose()
            return None, None

    except Exception as e:
        await client.aclose()
        raise e


async def get_flow_from_backend(client: httpx.AsyncClient, account: str) -> Optional[dict]:
    """
    从 8080 后台管理系统获取流量信息（校内直连）

    Returns:
        {
            "account": 账号,
            "balance": 余额(元),
            "used_flow": 已用流量(MB),
            "available_flow": 可用流量(MB)
        }
    """
    try:
        # 访问 refreshaccount 页面
        res = await client.get(AUTH_BACKEND_REFRESH_URL)
        print(f"[DEBUG] Refresh account status: {res.status_code}")

        if res.status_code != 200:
            return None

        # 解析 HTML 提取数据
        soup = BeautifulSoup(res.text, "html.parser")

        result = {}

        # 查找表格行
        for row in soup.select("tr"):
            cells = row.select("td")
            if len(cells) >= 2:
                label = cells[0].get_text().strip()
                value = cells[1].get_text().strip()

                if "账号" in label or "帐号" in label:
                    result["account"] = value
                elif "余额" in label:
                    match = re.search(r"([\d.]+)", value)
                    result["balance"] = float(match.group(1)) if match else 0.0
                elif "已用" in label or "使用" in label:
                    match = re.search(r"([\d.]+)", value)
                    result["used_flow"] = float(match.group(1)) if match else 0.0
                elif "可用" in label or "剩余" in label:
                    match = re.search(r"([\d.]+)", value)
                    result["available_flow"] = float(match.group(1)) if match else 0.0

        if result:
            result.setdefault("balance", 0.0)
            result.setdefault("used_flow", 0.0)
            result.setdefault("available_flow", 0.0)
            return result

        return None

    except Exception as e:
        print(f"[DEBUG] Error getting flow from backend: {e}")
        return None


async def get_flow_from_self(client: httpx.AsyncClient, account: str) -> Optional[dict]:
    """
    从 Self 系统获取流量信息（校内直连）

    Returns:
        {
            "account": 账号,
            "balance": 余额(元),
            "used_flow": 已用流量(MB),
            "available_flow": 可用流量(MB)
        }
    """
    try:
        # 访问 dashboard 页面
        res = await client.get(AUTH_SELF_DASHBOARD_URL)
        print(f"[DEBUG] Self dashboard status: {res.status_code}")

        if res.status_code != 200:
            return None

        # 解析 HTML 提取数据
        soup = BeautifulSoup(res.text, "html.parser")

        result = {}

        # 查找用户信息区域
        dls = soup.select(".user-info1 dl")
        for dl in dls:
            dt = dl.select_one("dt")
            dd = dl.select_one("dd")
            if dt and dd:
                value_text = dt.get_text().strip()
                label = dd.get_text().strip()

                if label == "已用流量":
                    match = re.search(r"([\d.]+)", value_text)
                    result["used_flow"] = float(match.group(1)) if match else 0.0
                elif label == "可用流量":
                    match = re.search(r"([\d.]+)", value_text)
                    result["available_flow"] = float(match.group(1)) if match else 0.0
                elif label == "账户余额":
                    match = re.search(r"([\d.]+)", value_text)
                    result["balance"] = float(match.group(1)) if match else 0.0

        # 查找账号信息
        panel_body = soup.select_one(".panel-body")
        if panel_body:
            text = panel_body.get_text()
            account_match = re.search(r"账　　号：\s*(\S+)", text)
            if account_match:
                result["account"] = account_match.group(1)

        if result:
            result.setdefault("account", account)
            result.setdefault("balance", 0.0)
            result.setdefault("used_flow", 0.0)
            result.setdefault("available_flow", 0.0)
            return result

        return None

    except Exception as e:
        print(f"[DEBUG] Error getting flow from Self: {e}")
        return None


# ===== 兼容旧 API 的函数 =====

async def login_via_direct(account: str, password: str, use_self: bool = False) -> Optional[str]:
    """
    登录校园网系统（校内直连）

    Args:
        account: 学号
        password: 校园网密码
        use_self: 是否使用 Self 系统（默认使用 8080 后台系统）

    Returns:
        session_id: 成功返回 session ID，失败返回 None
    """
    if use_self:
        session_id, client = await login_self_system(account, password)
    else:
        session_id, client = await login_backend_system(account, password)

    if client:
        await client.aclose()
    return session_id


async def get_user_flow(session: WifiSession, account: str, use_self: bool = False) -> Optional[dict]:
    """
    获取用户流量信息（校内直连）

    Args:
        session: 会话对象
        account: 学号
        use_self: 是否使用 Self 系统

    Returns:
        流量信息字典
    """
    if use_self:
        result = await get_flow_from_self(session.client, account)
    else:
        result = await get_flow_from_backend(session.client, account)

    if result:
        return {
            "balance": result.get("balance", 0.0),
            "used_flow": result.get("used_flow", 0.0),
            "available_flow": result.get("available_flow", 0.0),
            "update_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    return None
