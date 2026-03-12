"""
校园网管理服务

优先通过 zifuwu 直连接口获取和维护校园网会话。
保留部分 WebVPN URL 仅用于兼容旧 cookie 和 portal 回退。
"""
import base64
import json
import hashlib
import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Optional, List
from urllib.parse import urljoin
import httpx
from .webvpn_converter import convert_to_webvpn, VPN_HOST as WEBVPN_HOST

# VPN 配置
VPN_HOST = WEBVPN_HOST
VPN_COOKIE_NAME = "wengine_vpn_ticketelib_ustb_edu_cn"

# 校园网后台管理系统（202.204.60.7:8080）- 仅保留历史兼容常量
AUTH_BACKEND_LOGIN_URL = "http://202.204.60.7:8080/nav_login"  # 登录页
AUTH_BACKEND_VERIFY_URL = "http://202.204.60.7:8080/LoginAction.action"  # 登录验证
AUTH_BACKEND_REFRESH_URL = "http://202.204.60.7:8080/refreshaccount"  # 用户信息页

# 校园网自助服务系统（zifuwu.ustb.edu.cn）
SELF_LOGIN_URL = "https://zifuwu.ustb.edu.cn/Self/login/"
SELF_VERIFY_URL = "https://zifuwu.ustb.edu.cn/Self/login/verify"
SELF_RANDOM_CODE_URL = "https://zifuwu.ustb.edu.cn/Self/login/randomCode"
SELF_DASHBOARD_URL = "https://zifuwu.ustb.edu.cn/Self/dashboard"
SELF_GET_LOGIN_HISTORY_URL = "https://zifuwu.ustb.edu.cn/Self/dashboard/getLoginHistory"
SELF_GET_ONLINE_LIST_URL = "https://zifuwu.ustb.edu.cn/Self/dashboard/getOnlineList"
SELF_REFRESH_ACCOUNT_URL = "https://zifuwu.ustb.edu.cn/Self/dashboard/refreshaccount"
SELF_GET_MAC_LIST_URL = "https://zifuwu.ustb.edu.cn/Self/service/getMacList"
SELF_MY_MAC_URL = "https://zifuwu.ustb.edu.cn/Self/service/myMac"
SELF_UNBIND_MAC_URL = "https://zifuwu.ustb.edu.cn/Self/service/unbindmac"
SELF_GET_MONTH_PAY_URL = "https://zifuwu.ustb.edu.cn/Self/bill/getMonthPay"
SELF_GET_PAYMENT_URL = "https://zifuwu.ustb.edu.cn/Self/bill/getPayMent"
PORTAL_LOAD_USER_FLOW_URL = "http://202.204.48.66:801/eportal/portal/visitor/loadUserFlow"

# 转换为WebVPN URL
AUTH_BACKEND_LOGIN_WEBVPN_URL = convert_to_webvpn(AUTH_BACKEND_LOGIN_URL)
AUTH_BACKEND_VERIFY_WEBVPN_URL = convert_to_webvpn(AUTH_BACKEND_VERIFY_URL)
AUTH_BACKEND_REFRESH_WEBVPN_URL = convert_to_webvpn(AUTH_BACKEND_REFRESH_URL)
SELF_LOGIN_WEBVPN_URL = convert_to_webvpn(SELF_LOGIN_URL)
SELF_VERIFY_WEBVPN_URL = convert_to_webvpn(SELF_VERIFY_URL)
SELF_RANDOM_CODE_WEBVPN_URL = convert_to_webvpn(SELF_RANDOM_CODE_URL)
SELF_DASHBOARD_WEBVPN_URL = convert_to_webvpn(SELF_DASHBOARD_URL)
SELF_GET_LOGIN_HISTORY_WEBVPN_URL = convert_to_webvpn(SELF_GET_LOGIN_HISTORY_URL)
SELF_GET_ONLINE_LIST_WEBVPN_URL = convert_to_webvpn(SELF_GET_ONLINE_LIST_URL)
SELF_REFRESH_ACCOUNT_WEBVPN_URL = convert_to_webvpn(SELF_REFRESH_ACCOUNT_URL)
SELF_GET_MAC_LIST_WEBVPN_URL = convert_to_webvpn(SELF_GET_MAC_LIST_URL)
SELF_UNBIND_MAC_WEBVPN_URL = convert_to_webvpn(SELF_UNBIND_MAC_URL)
SELF_GET_MONTH_PAY_WEBVPN_URL = convert_to_webvpn(SELF_GET_MONTH_PAY_URL)
SELF_GET_PAYMENT_WEBVPN_URL = convert_to_webvpn(SELF_GET_PAYMENT_URL)
PORTAL_LOAD_USER_FLOW_WEBVPN_URL = convert_to_webvpn(PORTAL_LOAD_USER_FLOW_URL)


@dataclass
class WifiSession:
    """校园网会话"""
    client: httpx.AsyncClient
    student_id: str
    cookie: str  # WebVPN cookie 或直连模式的 JSESSIONID
    mode: str = "webvpn"
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)


@dataclass
class WifiLoginChallenge:
    """校园网验证码登录挑战"""
    token: str
    session_id: str  # 直连时为 JSESSIONID，WebVPN 时为 VPN ticket
    checkcode: str
    captcha_image: str
    mode: str = "direct"
    verify_url: str = SELF_VERIFY_URL
    referer_url: str = SELF_LOGIN_URL
    created_at: float = field(default_factory=time.time)


class WifiSessionStore:
    """校园网会话存储（独立于教务系统）"""

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


class WifiLoginChallengeStore:
    """校园网登录挑战存储"""

    def __init__(self):
        self._challenges: dict[str, WifiLoginChallenge] = {}

    def set(self, challenge: WifiLoginChallenge):
        self.cleanup()
        self._challenges[challenge.token] = challenge

    def get(self, token: str) -> Optional[WifiLoginChallenge]:
        self.cleanup()
        return self._challenges.get(token)

    def pop(self, token: str) -> Optional[WifiLoginChallenge]:
        self.cleanup()
        return self._challenges.pop(token, None)

    def cleanup(self):
        now = time.time()
        expired = [
            token
            for token, challenge in self._challenges.items()
            if now - challenge.created_at > 300
        ]
        for token in expired:
            self._challenges.pop(token, None)


login_challenge_store = WifiLoginChallengeStore()


def create_authenticated_client(cookie: str, mode: str = "webvpn") -> httpx.AsyncClient:
    """根据登录模式创建已带认证 cookie 的客户端。"""
    client = httpx.AsyncClient(follow_redirects=True, timeout=60.0)
    if mode == "direct":
        client.cookies.set("JSESSIONID", cookie, domain="zifuwu.ustb.edu.cn")
    else:
        client.cookies.set(VPN_COOKIE_NAME, cookie, domain=VPN_HOST)
    return client


def _self_url(direct_url: str, webvpn_url: str, mode: str) -> str:
    return direct_url if mode == "direct" else webvpn_url


def _self_request_params(params: Optional[dict], mode: str) -> dict:
    request_params = dict(params or {})
    if mode != "direct":
        request_params.setdefault("vpn-12-o2-zifuwu.ustb.edu.cn", "")
    return request_params


def _self_request_headers(
    cookie: str,
    mode: str,
    *,
    accept: str = "application/json, text/javascript, */*; q=0.01",
    xhr: bool = True,
    extra: Optional[dict] = None,
) -> dict:
    headers = {"Accept": accept}
    if xhr:
        headers["X-Requested-With"] = "XMLHttpRequest"
    if mode != "direct":
        headers["Cookie"] = f"show_vpn=0; show_faq=0; {VPN_COOKIE_NAME}={cookie}"
    if extra:
        headers.update(extra)
    return headers


def _extract_cookie_value(client: httpx.AsyncClient, name: str) -> Optional[str]:
    for cookie in client.cookies.jar:
        if cookie.name == name:
            return cookie.value
    return None


def _parse_jsonp_payload(text: str) -> Optional[dict]:
    """解析 JSONP 响应体，提取其中的 JSON 数据。"""
    if not text:
        return None

    match = re.search(r"^[^(]+\((.*)\);?\s*$", text.strip(), re.DOTALL)
    if not match:
        return None

    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None

    return payload if isinstance(payload, dict) else None


def _error_text(exc: Exception) -> str:
    """把 httpx 等空消息异常转换为可读文本。"""
    return str(exc) or exc.__class__.__name__


def _extract_verify_url(html: str, base_url: str) -> Optional[str]:
    match = re.search(r'<form[^>]+action="([^"]+?/Self/login/verify[^"]*)"', html)
    if not match:
        return None
    return urljoin(base_url, match.group(1))


async def get_portal_flow_breakdown(
    client: httpx.AsyncClient,
    account: str,
    vpn_cookie: Optional[str] = None,
) -> Optional[dict]:
    """
    通过校园网 portal 的 loadUserFlow 接口获取 V4/V6 流量分项。

    该接口来自 http://202.204.48.66:801/eportal/portal/visitor/loadUserFlow。
    如果当前环境无法直连 portal，则静默回退，不影响原有自服务数据。
    """
    if not account:
        return None

    callback_name = f"codexFlow{int(time.time() * 1000)}"

    attempts = [
        {
            "url": PORTAL_LOAD_USER_FLOW_URL,
            "headers": {
                "Accept": "*/*",
                "Referer": "http://202.204.48.66/",
            },
        }
    ]

    if vpn_cookie:
        attempts.append(
            {
                "url": PORTAL_LOAD_USER_FLOW_WEBVPN_URL,
                "headers": {
                    "Accept": "*/*",
                    "Referer": f"https://{VPN_HOST}/",
                    "Cookie": f"{VPN_COOKIE_NAME}={vpn_cookie}",
                },
            }
        )

    for attempt in attempts:
        try:
            res = await client.get(
                attempt["url"],
                params={
                    "callback": callback_name,
                    "account": account,
                    "jsVersion": "4.1",
                    "v": int(time.time() * 1000) % 10000,
                    "lang": "zh",
                },
                headers=attempt["headers"],
                timeout=10.0,
            )
        except Exception as e:
            print(f"[DEBUG] Error requesting portal flow breakdown via {attempt['url']}: {e}")
            continue

        if res.status_code != 200:
            print(f"[DEBUG] Portal flow breakdown status via {attempt['url']}: {res.status_code}")
            continue

        payload = _parse_jsonp_payload(res.text)
        if not payload or payload.get("result") not in (1, "1", "ok"):
            print(f"[DEBUG] Portal flow breakdown payload invalid via {attempt['url']}: {res.text[:200]}")
            continue

        data = payload.get("data")
        if not isinstance(data, dict):
            continue

        try:
            return {
                "used_flow_v4": float(data.get("v4", 0) or 0),
                "used_flow_v6": float(data.get("v6", 0) or 0),
            }
        except (TypeError, ValueError):
            continue

    return None


async def _create_direct_login_challenge() -> WifiLoginChallenge:
    """创建 zifuwu 直连验证码挑战。"""
    client = httpx.AsyncClient(
        follow_redirects=True,
        timeout=httpx.Timeout(30.0, connect=5.0),
    )
    try:
        res = await client.get(SELF_LOGIN_URL)
        if res.status_code != 200:
            raise RuntimeError(f"获取登录页失败: {res.status_code}")

        checkcode_match = re.search(r'name="checkcode"\s+value="([^"]+)"', res.text)
        if not checkcode_match:
            raise RuntimeError("无法获取 checkcode")

        session_id = _extract_cookie_value(client, "JSESSIONID")
        if not session_id:
            raise RuntimeError("无法获取 JSESSIONID")

        captcha_res = await client.get(
            SELF_RANDOM_CODE_URL,
            params={"t": str(time.time())},
            headers={"Referer": SELF_LOGIN_URL},
        )
        if captcha_res.status_code != 200 or not captcha_res.content:
            raise RuntimeError("无法获取验证码图片")

        content_type = captcha_res.headers.get("content-type", "image/png")
        challenge = WifiLoginChallenge(
            token=secrets.token_urlsafe(24),
            session_id=session_id,
            checkcode=checkcode_match.group(1),
            captcha_image=f"data:{content_type};base64,{base64.b64encode(captcha_res.content).decode()}",
            mode="direct",
            verify_url=SELF_VERIFY_URL,
            referer_url=SELF_LOGIN_URL,
        )
        login_challenge_store.set(challenge)
        return challenge
    finally:
        await client.aclose()


async def _login_webvpn(account: str, password: str) -> httpx.AsyncClient:
    """先通过通用 WebVPN 登录页建立 VPN 会话。"""
    client = httpx.AsyncClient(follow_redirects=True, timeout=30.0)
    try:
        login_res = await client.get(SELF_LOGIN_WEBVPN_URL)
        if login_res.status_code != 200:
            raise RuntimeError(f"获取 WebVPN 登录页失败: {login_res.status_code}")

        res = await client.post(
            f"https://{VPN_HOST}/do-login",
            data={
                "auth_type": "local",
                "username": account,
                "password": password,
                "remember_cookie": "on",
            },
            headers={
                "Origin": f"https://{VPN_HOST}",
                "Referer": str(login_res.url),
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        if res.status_code != 200:
            raise RuntimeError(f"WebVPN 登录失败: {res.status_code}")

        try:
            payload = res.json()
        except json.JSONDecodeError as exc:
            raise RuntimeError("WebVPN 登录响应不是有效 JSON") from exc

        if not payload.get("success"):
            if payload.get("error") == "NEED_CONFIRM":
                confirm_res = await client.post(f"https://{VPN_HOST}/do-confirm-login")
                if confirm_res.status_code != 200:
                    raise RuntimeError(f"WebVPN 确认登录失败: {confirm_res.status_code}")
                try:
                    confirm_payload = confirm_res.json()
                except json.JSONDecodeError as exc:
                    raise RuntimeError("WebVPN 确认登录响应不是有效 JSON") from exc
                if not confirm_payload.get("success"):
                    raise RuntimeError(
                        confirm_payload.get("message")
                        or confirm_payload.get("error")
                        or "WebVPN 确认登录失败"
                    )
            else:
                raise RuntimeError(payload.get("message") or payload.get("error") or "WebVPN 登录失败")

        vpn_cookie = _extract_cookie_value(client, VPN_COOKIE_NAME)
        if not vpn_cookie:
            raise RuntimeError("无法获取 WebVPN ticket")

        return client
    except Exception:
        await client.aclose()
        raise


async def _create_webvpn_login_challenge(account: str, password: str) -> WifiLoginChallenge:
    """通过 WebVPN 登录后访问 zifuwu 包装页，创建验证码挑战。"""
    client = await _login_webvpn(account, password)
    try:
        res = await client.get(SELF_LOGIN_WEBVPN_URL)
        if res.status_code != 200:
            raise RuntimeError(f"获取 WebVPN 包装登录页失败: {res.status_code}")

        checkcode_match = re.search(r'name="checkcode"\s+value="([^"]+)"', res.text)
        if not checkcode_match:
            raise RuntimeError("WebVPN 包装登录页缺少 checkcode")

        verify_url = _extract_verify_url(res.text, f"https://{VPN_HOST}")
        if not verify_url:
            raise RuntimeError("WebVPN 包装登录页缺少 verify 地址")

        vpn_cookie = _extract_cookie_value(client, VPN_COOKIE_NAME)
        if not vpn_cookie:
            raise RuntimeError("无法获取 WebVPN ticket")

        captcha_res = await client.get(
            SELF_RANDOM_CODE_WEBVPN_URL,
            params={"t": str(time.time())},
            headers={"Referer": str(res.url)},
        )
        content_type = captcha_res.headers.get("content-type", "")
        if (
            captcha_res.status_code != 200
            or not captcha_res.content
            or not content_type.startswith("image/")
        ):
            raise RuntimeError("无法获取 WebVPN 验证码图片")
        captcha_image = (
            f"data:{content_type};base64,{base64.b64encode(captcha_res.content).decode()}"
        )

        challenge = WifiLoginChallenge(
            token=secrets.token_urlsafe(24),
            session_id=vpn_cookie,
            checkcode=checkcode_match.group(1),
            captcha_image=captcha_image,
            mode="webvpn",
            verify_url=verify_url,
            referer_url=str(res.url),
        )
        login_challenge_store.set(challenge)
        return challenge
    finally:
        await client.aclose()


async def create_login_challenge(
    account: Optional[str] = None,
    password: Optional[str] = None,
) -> WifiLoginChallenge:
    """默认通过 WebVPN 包装页创建验证码挑战。"""
    if not account or not password:
        if account:
            raise RuntimeError("当前环境需先输入校园网密码后获取验证码")
        raise RuntimeError("当前环境需先输入学号和校园网密码后获取验证码")

    try:
        return await _create_webvpn_login_challenge(account, password)
    except Exception as webvpn_exc:
        raise RuntimeError(f"WebVPN 获取验证码失败({_error_text(webvpn_exc)})") from webvpn_exc


async def login_with_captcha(
    account: str,
    password: str,
    challenge_token: str,
    captcha_code: str,
) -> tuple[Optional[str], Optional[httpx.AsyncClient], str]:
    """使用 challenge 登录 zifuwu，自动兼容直连和 WebVPN。"""
    challenge = login_challenge_store.pop(challenge_token)
    if not challenge:
        raise RuntimeError("验证码已过期，请刷新后重试")

    if not captcha_code.strip():
        raise RuntimeError("请输入验证码")

    client = create_authenticated_client(challenge.session_id, mode=challenge.mode)
    try:
        password_md5 = hashlib.md5(password.encode()).hexdigest()
        res = await client.post(
            challenge.verify_url,
            data={
                "foo": "",
                "bar": "",
                "checkcode": challenge.checkcode,
                "account": account,
                "password": password_md5,
                "code": captcha_code.strip(),
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": f"https://{VPN_HOST}" if challenge.mode == "webvpn" else "https://zifuwu.ustb.edu.cn",
                "Referer": challenge.referer_url,
            },
        )

        if res.status_code != 200:
            await client.aclose()
            raise RuntimeError(f"登录失败: {res.status_code}")

        session_cookie = (
            _extract_cookie_value(client, VPN_COOKIE_NAME)
            if challenge.mode == "webvpn"
            else _extract_cookie_value(client, "JSESSIONID")
        ) or challenge.session_id

        dashboard_res = await client.get(
            _self_url(SELF_DASHBOARD_URL, SELF_DASHBOARD_WEBVPN_URL, challenge.mode),
            headers=_self_request_headers(
                session_cookie,
                challenge.mode,
                accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                xhr=False,
            ),
        )

        current_url = str(dashboard_res.url)
        if "/Self/dashboard" not in current_url or "/Self/login" in current_url:
            await client.aclose()
            raise RuntimeError("验证码错误或校园网密码错误")

        if not session_cookie:
            await client.aclose()
            raise RuntimeError("登录成功但未获取到会话")

        return session_cookie, client, challenge.mode
    except Exception:
        await client.aclose()
        raise


async def get_account_info_from_dashboard(
    client: httpx.AsyncClient,
    auth_cookie: str,
    mode: str = "webvpn",
) -> Optional[dict]:
    """
    从dashboard页面提取账户信息（从JavaScript变量window.user中提取）

    Returns:
        {
            "account": 账号,
            "balance": 余额(元),
            "used_flow": 已用流量(MB),
            "available_flow": 可用流量(MB),
            "status": 状态,
            "package": 套餐,
            "expire_date": 到期日期
        }
    """
    try:
        # 访问dashboard页面
        # 注意：不要显式设置Cookie header，让httpx客户端自动处理cookie
        # 登录后zifuwu系统会在客户端cookie jar中设置JSESSIONID
        res = await client.get(
            _self_url(SELF_DASHBOARD_URL, SELF_DASHBOARD_WEBVPN_URL, mode),
            headers=_self_request_headers(
                auth_cookie,
                mode,
                accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                xhr=False,
            ),
        )

        print(f"[DEBUG] Dashboard response status: {res.status_code}")
        print(f"[DEBUG] Dashboard URL: {res.url}")

        if res.status_code != 200 or "wengine-vpn/failed" in str(res.url):
            print("[DEBUG] Failed to access dashboard")
            return None

        # 检查是否被重定向到登录页（会话过期）
        if "/login" in str(res.url):
            print("[DEBUG] Session expired - redirected to login page")
            return None

        html = res.text
        print(f"[DEBUG] Dashboard HTML length: {len(html)}")
        print(f"[DEBUG] Contains window.user: {'window.user' in html}")
        print(f"[DEBUG] Contains 欢迎登录: {'欢迎登录' in html}")
        result = {}

        # 方法1：从JavaScript变量 window.user 中提取数据（最可靠）
        # 页面中有: (function (user) { window.user = user || {}; })({JSON数据});
        import json

        # 使用更精确的方式提取 JSON：找到 })({ 后的内容直到 });
        start_marker = '})({'
        end_marker = '});'
        start_idx = html.find(start_marker)
        if start_idx != -1:
            json_start = start_idx + len(start_marker) - 1  # 包含 {
            # 找到匹配的结束 });
            brace_count = 0
            json_end = json_start
            for i in range(json_start, len(html)):
                if html[i] == '{':
                    brace_count += 1
                elif html[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break

            if json_end > json_start:
                try:
                    user_json = html[json_start:json_end]
                    user_data = json.loads(user_json)
                    print(f"[DEBUG] Extracted user data from window.user")
                    print(f"[DEBUG] leftFlow: {user_data.get('leftFlow')}, useFlow: {user_data.get('useFlow')}")

                    # 从user对象提取数据
                    result["account"] = user_data.get("userName", "")
                    result["balance"] = float(user_data.get("leftMoney", 0))
                    result["used_flow"] = float(user_data.get("useFlow", 0))
                    result["available_flow"] = float(user_data.get("leftFlow", 0))

                    # 提取状态
                    use_flag = user_data.get("useFlag", 0)
                    result["status"] = "正常" if use_flag == 1 else "异常"

                    # 提取套餐
                    service_default = user_data.get("serviceDefault", {})
                    result["package"] = service_default.get("defaultName", "")

                    # 提取到期日期
                    invalid_date = user_data.get("invalidDate")
                    if invalid_date:
                        result["expire_date"] = time.strftime("%Y-%m-%d", time.localtime(invalid_date / 1000))

                    return result
                except json.JSONDecodeError as e:
                    print(f"[DEBUG] Failed to parse user JSON: {e}")

        # 方法2：回退到正则表达式提取（如果JavaScript变量不可用）
        print("[DEBUG] Falling back to regex extraction")

        # 提取账号
        match = re.search(r'账　　号：\s*</label>\s*</div>\s*<div[^>]*>\s*<span>([^<]+)</span>', html, re.DOTALL)
        if match:
            result["account"] = match.group(1).strip()

        # 提取状态
        match = re.search(r'<span class="label label-success">([^<]+)</span>', html)
        if match:
            result["status"] = match.group(1).strip()

        # 提取套餐
        match = re.search(r'套　　餐：\s*</label>\s*</div>\s*<div[^>]*>\s*<span>\s*([^\n<]+)', html, re.DOTALL)
        if match:
            result["package"] = match.group(1).strip()

        # 提取到期日期
        match = re.search(r'到期日期：\s*</label>\s*<div[^>]*>\s*<span>\s*(\d{4}-\d{2}-\d{2})', html, re.DOTALL)
        if match:
            result["expire_date"] = match.group(1)

        # 提取流量和余额（从页面的数字显示中提取）
        # HTML结构: <dt>\n  数字\n  <small class="unit">单位</small>\n</dt>\n<dd>标签</dd>

        # 已用流量
        match = re.search(r'<dt>\s*(\d+(?:\.\d+)?)\s*<small[^>]*>M</small>\s*</dt>\s*<dd>已用流量</dd>', html, re.DOTALL)
        if match:
            result["used_flow"] = float(match.group(1))

        # 可用流量
        match = re.search(r'<dt>\s*(\d+(?:\.\d+)?)\s*<small[^>]*>M</small>\s*</dt>\s*<dd>可用流量</dd>', html, re.DOTALL)
        if match:
            result["available_flow"] = float(match.group(1))

        # 账户余额
        match = re.search(r'<dt>\s*(\d+(?:\.\d+)?)\s*<small[^>]*>\s*元</small>\s*</dt>\s*<dd>账户余额</dd>', html, re.DOTALL)
        if match:
            result["balance"] = float(match.group(1))

        # 设置默认值
        result.setdefault("balance", 0.0)
        result.setdefault("used_flow", 0.0)
        result.setdefault("available_flow", 0.0)

        return result if result else None

    except Exception as e:
        print(f"[DEBUG] Error getting account info: {e}")
        import traceback
        traceback.print_exc()
        return None


async def get_login_history(
    client: httpx.AsyncClient,
    auth_cookie: str,
    limit: int = 10,
    mode: str = "webvpn",
) -> List[dict]:
    """
    获取上网历史记录（使用API接口）

    Returns:
        [
            {
                "login_time": 上线时间,
                "logout_time": 注销时间,
                "ip_address": IP地址,
                "mac_address": MAC地址,
                "duration_minutes": 使用时长（分钟）,
                "used_flow_mb": 使用流量（MB）,
                "cost": 费用,
                "device_type": 设备类型
            }
        ]
    """
    try:
        res = await client.get(
            _self_url(SELF_GET_LOGIN_HISTORY_URL, SELF_GET_LOGIN_HISTORY_WEBVPN_URL, mode),
            params=_self_request_params({
                "t": time.time(),
                "order": "asc",
                "_": int(time.time() * 1000)
            }, mode),
            headers=_self_request_headers(auth_cookie, mode),
        )

        if res.status_code != 200:
            return []

        data = res.json()
        if not isinstance(data, list):
            return []

        # 解析数组格式的响应
        history = []
        for record in data[:limit]:
            if len(record) >= 11:
                history.append({
                    "login_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record[0] / 1000)),
                    "logout_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record[1] / 1000)) if record[1] else None,
                    "ip_address": record[2],
                    "mac_address": record[3],
                    "duration_minutes": record[4],
                    "used_flow_mb": record[5],
                    "cost": record[7],
                    "device_type": record[10]
                })

        return history

    except Exception as e:
        print(f"[DEBUG] Error getting login history: {e}")
        return []


async def get_online_devices(
    client: httpx.AsyncClient,
    auth_cookie: str,
    mode: str = "webvpn",
) -> List[dict]:
    """
    获取在线设备列表（使用API接口）

    Returns:
        [
            {
                "login_time": 上线时间,
                "ip_address": IP地址,
                "mac_address": MAC地址,
                "duration_minutes": 已使用时长（分钟）,
                "used_flow_mb": 已使用流量（MB）,
                "device_type": 设备类型
            }
        ]
    """
    try:
        res = await client.get(
            _self_url(SELF_GET_ONLINE_LIST_URL, SELF_GET_ONLINE_LIST_WEBVPN_URL, mode),
            params=_self_request_params({
                "t": time.time(),
                "order": "asc",
                "_": int(time.time() * 1000)
            }, mode),
            headers=_self_request_headers(auth_cookie, mode),
        )

        if res.status_code != 200:
            return []

        data = res.json()
        if not isinstance(data, list):
            return []

        devices = []
        for record in data:
            if isinstance(record, dict):
                mac = str(record.get("mac", "") or "")
                formatted_mac = "-".join([mac[i:i+2] for i in range(0, len(mac), 2)]) if mac else ""
                used_flow_mb = 0.0
                try:
                    used_flow_mb = float(record.get("downFlow", 0) or 0) + float(record.get("upFlow", 0) or 0)
                except (TypeError, ValueError):
                    used_flow_mb = 0.0

                try:
                    duration_minutes = int(record.get("useTime", 0) or 0)
                except (TypeError, ValueError):
                    duration_minutes = 0

                terminal_type = str(record.get("terminalType", "") or "").lstrip("#")
                devices.append({
                    "login_time": record.get("loginTime", "") or "",
                    "ip_address": record.get("ip", "") or "",
                    "mac_address": formatted_mac or mac,
                    "duration_minutes": duration_minutes,
                    "used_flow_mb": used_flow_mb,
                    "device_type": terminal_type or "Unknown",
                })
            elif len(record) >= 11:
                devices.append({
                    "login_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record[0] / 1000)),
                    "ip_address": record[2],
                    "mac_address": record[3],
                    "duration_minutes": record[4],
                    "used_flow_mb": record[5],
                    "device_type": record[10]
                })

        return devices

    except Exception as e:
        print(f"[DEBUG] Error getting online devices: {e}")
        return []


async def get_bound_devices(
    client: httpx.AsyncClient,
    auth_cookie: str,
    mode: str = "webvpn",
) -> List[dict]:
    """
    获取绑定设备列表（我的设备）

    Returns:
        [
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
    """
    try:
        print(f"[DEBUG] get_bound_devices called with mode={mode}")
        print(f"[DEBUG] Request URL: {_self_url(SELF_GET_MAC_LIST_URL, SELF_GET_MAC_LIST_WEBVPN_URL, mode)}")
        res = await client.get(
            _self_url(SELF_GET_MAC_LIST_URL, SELF_GET_MAC_LIST_WEBVPN_URL, mode),
            params=_self_request_params({
                "pageSize": 100,
                "pageNumber": 1,
                "sortName": 2,
                "sortOrder": "DESC",
                "_": int(time.time() * 1000)
            }, mode),
            headers=_self_request_headers(
                auth_cookie,
                mode,
                extra={"Content-Type": "application/json"},
            ),
        )

        if res.status_code != 200:
            print(f"[DEBUG] getMacList status: {res.status_code}")
            print(f"[DEBUG] getMacList response text: {res.text[:500]}")
            return []

        data = res.json()
        print(f"[DEBUG] getMacList response: {data}")

        if not isinstance(data, dict) or "rows" not in data:
            return []

        # 解析数组格式的响应
        # 格式: ["在线状态", "MAC地址", "终端信息", "最近登录时间", "最近登录IP", "是否哑终端", "终端名称"]
        devices = []
        for record in data["rows"]:
            if len(record) >= 7:
                # 格式化MAC地址（添加分隔符）
                raw_mac = record[1]
                formatted_mac = "-".join([raw_mac[i:i+2] for i in range(0, len(raw_mac), 2)]) if raw_mac else ""

                devices.append({
                    "online": record[0] == "1",
                    "mac_address": formatted_mac,
                    "terminal_info": record[2] or "",
                    "last_login_time": record[3] or "",
                    "last_login_ip": record[4] or "",
                    "is_dumb_terminal": record[5] == "是",
                    "terminal_name": record[6] or ""
                })

        return devices

    except Exception as e:
        print(f"[DEBUG] Error getting bound devices: {e}")
        import traceback
        traceback.print_exc()
        return []


async def unbind_mac(
    client: httpx.AsyncClient,
    auth_cookie: str,
    mac_address: str,
    mode: str = "webvpn",
) -> bool:
    """
    解绑指定的MAC地址

    Args:
        client: httpx客户端
        vpn_cookie: VPN cookie
        mac_address: 要解绑的MAC地址（格式：XX-XX-XX-XX-XX-XX 或 XXXXXXXXXXXX）

    Returns:
        是否解绑成功
    """
    try:
        raw_mac = mac_address.replace("-", "").replace(":", "").upper()
        print(f"[DEBUG] Unbinding MAC: {raw_mac}")

        # 先访问 myMac 页面获取 CSRF token
        my_mac_url = _self_url(SELF_MY_MAC_URL, convert_to_webvpn(SELF_MY_MAC_URL), mode)
        page_res = await client.get(
            my_mac_url,
            headers=_self_request_headers(
                auth_cookie,
                mode,
                accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                xhr=False,
            ),
        )

        # 从页面提取 ajaxCsrfToken
        csrf_match = re.search(r"ajaxCsrfToken=\" \+ '([^']+)'", page_res.text)
        if not csrf_match:
            print("[DEBUG] Failed to extract CSRF token")
            return False
        csrf_token = csrf_match.group(1)
        print(f"[DEBUG] Got CSRF token: {csrf_token}")

        res = await client.get(
            _self_url(SELF_UNBIND_MAC_URL, SELF_UNBIND_MAC_WEBVPN_URL, mode),
            params=_self_request_params({
                "mac": raw_mac,
                "ajaxCsrfToken": csrf_token,
            }, mode),
            headers=_self_request_headers(auth_cookie, mode, xhr=False, accept="*/*"),
        )

        print(f"[DEBUG] Unbind response status: {res.status_code}")
        print(f"[DEBUG] Unbind response text: {res.text[:200] if res.text else 'empty'}")

        if res.status_code == 200:
            return True

        return False

    except Exception as e:
        print(f"[DEBUG] Error unbinding MAC: {e}")
        import traceback
        traceback.print_exc()
        return False


async def get_month_pay(
    client: httpx.AsyncClient,
    auth_cookie: str,
    year: int,
    mode: str = "webvpn",
) -> Optional[dict]:
    """
    获取指定年份的历史账单

    Args:
        year: 年份，如 2025

    Returns:
        {
            "summary": {"total_time": 分钟, "total_flow": MB, "base_fee": 元, "usage_fee": 元},
            "bills": [{
                "start_time": 开始时间,
                "end_time": 结束时间,
                "package": 套餐,
                "base_fee": 基本月租,
                "usage_fee": 时长/流量计费,
                "duration_minutes": 使用时长,
                "used_flow_mb": 使用流量,
                "bill_time": 出账时间
            }]
        }
    """
    try:
        res = await client.get(
            _self_url(SELF_GET_MONTH_PAY_URL, SELF_GET_MONTH_PAY_WEBVPN_URL, mode),
            params=_self_request_params({
                "pageSize": 100,
                "pageNumber": 1,
                "sortName": 0,
                "sortOrder": "DESC",
                "year": year,
                "_": int(time.time() * 1000)
            }, mode),
            headers=_self_request_headers(auth_cookie, mode, accept="application/json"),
        )

        if res.status_code != 200:
            return None

        data = res.json()
        summary = data.get("summary", {})
        rows = data.get("rows", [])

        bills = []
        for row in rows:
            if len(row) >= 8:
                bills.append({
                    "start_time": time.strftime("%Y-%m-%d", time.localtime(row[0] / 1000)),
                    "end_time": time.strftime("%Y-%m-%d", time.localtime(row[1] / 1000)),
                    "package": row[2],
                    "base_fee": row[3],
                    "usage_fee": row[4],
                    "duration_minutes": int(row[5]),
                    "used_flow_mb": row[6],
                    "bill_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[7] / 1000))
                })

        return {
            "summary": {
                "total_time": int(summary.get("USETIME", 0)),
                "total_flow": summary.get("USEFLOW", 0),
                "base_fee": summary.get("USEBASEMONEY", 0),
                "usage_fee": summary.get("USEDMONEY", 0)
            },
            "bills": bills
        }

    except Exception as e:
        print(f"[DEBUG] Error getting month pay: {e}")
        return None


async def get_payments(
    client: httpx.AsyncClient,
    auth_cookie: str,
    start_date: str,
    end_date: str,
    mode: str = "webvpn",
) -> Optional[dict]:
    """
    获取充值明细

    Args:
        start_date: 开始日期，格式 YYYY-MM-DD
        end_date: 结束日期，格式 YYYY-MM-DD

    Returns:
        {
            "total_amount": 充值总金额,
            "payments": [{
                "pay_time": 交费时间,
                "amount": 金额,
                "pay_type": 交费类型,
                "terminal": 受理终端,
                "remark": 备注
            }]
        }
    """
    try:
        res = await client.get(
            _self_url(SELF_GET_PAYMENT_URL, SELF_GET_PAYMENT_WEBVPN_URL, mode),
            params=_self_request_params({
                "pageSize": 100,
                "pageNumber": 1,
                "sortName": 0,
                "sortOrder": "DESC",
                "startTime": start_date,
                "endTime": end_date,
                "_": int(time.time() * 1000)
            }, mode),
            headers=_self_request_headers(auth_cookie, mode, accept="application/json"),
        )

        if res.status_code != 200:
            return None

        data = res.json()
        summary = data.get("summary", {})
        rows = data.get("rows", [])

        payments = []
        for row in rows:
            if len(row) >= 5:
                payments.append({
                    "pay_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[0] / 1000)) if row[0] else "",
                    "amount": row[1],
                    "pay_type": row[2],
                    "terminal": row[3],
                    "remark": row[4] or ""
                })

        return {
            "total_amount": summary.get("MONEY", 0),
            "payments": payments
        }

    except Exception as e:
        print(f"[DEBUG] Error getting payments: {e}")
        return None


async def get_flow_info(
    client: httpx.AsyncClient,
    auth_cookie: str,
    mode: str = "webvpn",
) -> Optional[dict]:
    """
    获取流量信息（整合账户信息、历史记录和在线设备）

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
            "recent_history": 最近上网记录
        }
    """
    # 获取账户信息
    account_info = await get_account_info_from_dashboard(client, auth_cookie, mode)
    if not account_info:
        return None

    portal_flow = await get_portal_flow_breakdown(
        client,
        account_info.get("account", ""),
        auth_cookie if mode == "webvpn" else None,
    )

    # 获取在线设备
    online_devices = await get_online_devices(client, auth_cookie, mode)

    # 获取最近历史记录（最多5条）
    recent_history = await get_login_history(client, auth_cookie, limit=5, mode=mode)

    return {
        **account_info,
        **(portal_flow or {}),
        "online_devices": online_devices,
        "recent_history": recent_history
    }


async def get_user_flow(session: WifiSession, account: str) -> Optional[dict]:
    """
    获取用户流量信息（使用API接口）
    """
    result = await get_flow_info(session.client, session.cookie, session.mode)
    if result:
        return {
            "account": result.get("account", account),
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
    return None
