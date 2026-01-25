"""
校园网管理服务 - 通过 WebVPN 模式访问校园网信息
使用API接口获取数据，避免HTML解析

注意: zifuwu 登录使用 Playwright 模拟浏览器，因为 WebVPN 依赖 JavaScript 管理 session cookie
"""
import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Optional, List
import httpx
from .webvpn_converter import convert_to_webvpn, VPN_HOST as WEBVPN_HOST
from .wifi_playwright import login_zifuwu_with_playwright

# VPN 配置
VPN_HOST = WEBVPN_HOST
VPN_COOKIE_NAME = "wengine_vpn_ticketelib_ustb_edu_cn"

# 校园网后台管理系统（202.204.60.7:8080）- 使用http-8080端口
# 这个系统比Self系统更容易通过WebVPN访问
AUTH_BACKEND_LOGIN_URL = "http://202.204.60.7:8080/nav_login"  # 登录页
AUTH_BACKEND_VERIFY_URL = "http://202.204.60.7:8080/LoginAction.action"  # 登录验证
AUTH_BACKEND_REFRESH_URL = "http://202.204.60.7:8080/refreshaccount"  # 用户信息页

# 校园网自助服务系统（zifuwu.ustb.edu.cn）
SELF_DASHBOARD_URL = "https://zifuwu.ustb.edu.cn/Self/dashboard"
SELF_GET_LOGIN_HISTORY_URL = "https://zifuwu.ustb.edu.cn/Self/dashboard/getLoginHistory"
SELF_GET_ONLINE_LIST_URL = "https://zifuwu.ustb.edu.cn/Self/dashboard/getOnlineList"
SELF_REFRESH_ACCOUNT_URL = "https://zifuwu.ustb.edu.cn/Self/dashboard/refreshaccount"
SELF_GET_MAC_LIST_URL = "https://zifuwu.ustb.edu.cn/Self/service/getMacList"
SELF_UNBIND_MAC_URL = "https://zifuwu.ustb.edu.cn/Self/service/unbindmac"
SELF_GET_MONTH_PAY_URL = "https://zifuwu.ustb.edu.cn/Self/bill/getMonthPay"
SELF_GET_PAYMENT_URL = "https://zifuwu.ustb.edu.cn/Self/bill/getPayMent"

# 转换为WebVPN URL
AUTH_BACKEND_LOGIN_WEBVPN_URL = convert_to_webvpn(AUTH_BACKEND_LOGIN_URL)
AUTH_BACKEND_VERIFY_WEBVPN_URL = convert_to_webvpn(AUTH_BACKEND_VERIFY_URL)
AUTH_BACKEND_REFRESH_WEBVPN_URL = convert_to_webvpn(AUTH_BACKEND_REFRESH_URL)
SELF_DASHBOARD_WEBVPN_URL = convert_to_webvpn(SELF_DASHBOARD_URL)
SELF_GET_LOGIN_HISTORY_WEBVPN_URL = convert_to_webvpn(SELF_GET_LOGIN_HISTORY_URL)
SELF_GET_ONLINE_LIST_WEBVPN_URL = convert_to_webvpn(SELF_GET_ONLINE_LIST_URL)
SELF_REFRESH_ACCOUNT_WEBVPN_URL = convert_to_webvpn(SELF_REFRESH_ACCOUNT_URL)
SELF_GET_MAC_LIST_WEBVPN_URL = convert_to_webvpn(SELF_GET_MAC_LIST_URL)
SELF_UNBIND_MAC_WEBVPN_URL = convert_to_webvpn(SELF_UNBIND_MAC_URL)
SELF_GET_MONTH_PAY_WEBVPN_URL = convert_to_webvpn(SELF_GET_MONTH_PAY_URL)
SELF_GET_PAYMENT_WEBVPN_URL = convert_to_webvpn(SELF_GET_PAYMENT_URL)


@dataclass
class WifiSession:
    """校园网会话"""
    client: httpx.AsyncClient
    student_id: str
    cookie: str  # VPN cookie
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)


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


def _extract_vpn_cookie(client: httpx.AsyncClient) -> Optional[str]:
    """从 httpx 客户端的 cookie jar 中提取 VPN cookie"""
    for cookie in client.cookies.jar:
        if cookie.name == VPN_COOKIE_NAME:
            return cookie.value
    return None


async def login_vpn_only(account: str, password: str) -> tuple[Optional[str], Optional[httpx.AsyncClient]]:
    """
    登录 VPN 并登录校园网自助服务系统 (zifuwu.ustb.edu.cn)

    使用 Playwright 模拟浏览器完成登录，因为 WebVPN 依赖 JavaScript 管理 session cookie。
    httpx 无法执行 JavaScript，导致登录失败。

    Args:
        account: 学号
        password: 校园网密码

    Returns:
        (vpn_cookie, client) 成功返回 cookie 和客户端，失败返回 (None, None)
    """
    print(f"[DEBUG] Starting Playwright-based login for account: {account}")

    # 使用 Playwright 完成登录
    vpn_cookie, all_cookies, success = await login_zifuwu_with_playwright(account, password)

    if not success or not vpn_cookie:
        print("[DEBUG] Playwright login failed")
        return None, None

    print(f"[DEBUG] Playwright login successful, VPN cookie: {vpn_cookie[:20]}...")

    # 创建 httpx 客户端，设置获取的所有 cookie
    client = httpx.AsyncClient(follow_redirects=True, timeout=60.0)

    # 设置所有 cookies（包括 VPN cookie 和 JSESSIONID）
    if all_cookies:
        for name, value in all_cookies.items():
            # 根据 cookie 名称设置到正确的 domain
            if "vpn" in name.lower():
                client.cookies.set(name, value, domain=VPN_HOST)
            else:
                # 其他 cookies（如 JSESSIONID）也设置到 VPN host
                client.cookies.set(name, value, domain=VPN_HOST)
        print(f"[DEBUG] httpx client created with {len(all_cookies)} cookies")
    else:
        # 兼容旧模式
        client.cookies.set(VPN_COOKIE_NAME, vpn_cookie, domain=VPN_HOST)
        print(f"[DEBUG] httpx client created with VPN cookie only")

    return vpn_cookie, client


async def get_account_info_from_dashboard(client: httpx.AsyncClient, vpn_cookie: str) -> Optional[dict]:
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
        res = await client.get(SELF_DASHBOARD_WEBVPN_URL)

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


async def get_login_history(client: httpx.AsyncClient, vpn_cookie: str, limit: int = 10) -> List[dict]:
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
            SELF_GET_LOGIN_HISTORY_WEBVPN_URL,
            params={
                "vpn-12-o2-zifuwu.ustb.edu.cn": "",  # WebVPN cookie injection marker
                "t": time.time(),
                "order": "asc",
                "_": int(time.time() * 1000)
            },
            headers={
                "Cookie": f"show_vpn=0; show_faq=0; wengine_vpn_ticketelib_ustb_edu_cn={vpn_cookie}",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01"
            }
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


async def get_online_devices(client: httpx.AsyncClient, vpn_cookie: str) -> List[dict]:
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
            SELF_GET_ONLINE_LIST_WEBVPN_URL,
            params={
                "vpn-12-o2-zifuwu.ustb.edu.cn": "",  # WebVPN cookie injection marker
                "t": time.time(),
                "order": "asc",
                "_": int(time.time() * 1000)
            },
            headers={
                "Cookie": f"show_vpn=0; show_faq=0; wengine_vpn_ticketelib_ustb_edu_cn={vpn_cookie}",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01"
            }
        )

        if res.status_code != 200:
            return []

        data = res.json()
        if not isinstance(data, list):
            return []

        # 解析数组格式的响应
        devices = []
        for record in data:
            if len(record) >= 11:
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


async def get_bound_devices(client: httpx.AsyncClient, vpn_cookie: str) -> List[dict]:
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
        print(f"[DEBUG] get_bound_devices called with cookie: {vpn_cookie[:10]}...")
        print(f"[DEBUG] Request URL: {SELF_GET_MAC_LIST_WEBVPN_URL}")
        # WebVPN 需要添加 vpn-12-o2-zifuwu.ustb.edu.cn 标记来注入 session cookies
        res = await client.get(
            SELF_GET_MAC_LIST_WEBVPN_URL,
            params={
                "vpn-12-o2-zifuwu.ustb.edu.cn": "",  # WebVPN cookie injection marker
                "pageSize": 100,
                "pageNumber": 1,
                "sortName": 2,
                "sortOrder": "DESC",
                "_": int(time.time() * 1000)
            },
            headers={
                "Cookie": f"show_vpn=0; show_faq=0; wengine_vpn_ticketelib_ustb_edu_cn={vpn_cookie}",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Content-Type": "application/json"
            }
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


async def unbind_mac(client: httpx.AsyncClient, vpn_cookie: str, mac_address: str) -> bool:
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
        my_mac_url = convert_to_webvpn("https://zifuwu.ustb.edu.cn/Self/service/myMac")
        page_res = await client.get(
            my_mac_url,
            headers={"Cookie": f"show_vpn=0; show_faq=0; wengine_vpn_ticketelib_ustb_edu_cn={vpn_cookie}"}
        )

        # 从页面提取 ajaxCsrfToken
        csrf_match = re.search(r"ajaxCsrfToken=\" \+ '([^']+)'", page_res.text)
        if not csrf_match:
            print("[DEBUG] Failed to extract CSRF token")
            return False
        csrf_token = csrf_match.group(1)
        print(f"[DEBUG] Got CSRF token: {csrf_token}")

        res = await client.get(
            SELF_UNBIND_MAC_WEBVPN_URL,
            params={
                "vpn-12-o2-zifuwu.ustb.edu.cn": "",
                "mac": raw_mac,
                "ajaxCsrfToken": csrf_token,
            },
            headers={
                "Cookie": f"show_vpn=0; show_faq=0; wengine_vpn_ticketelib_ustb_edu_cn={vpn_cookie}",
            }
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


async def get_month_pay(client: httpx.AsyncClient, vpn_cookie: str, year: int) -> Optional[dict]:
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
            SELF_GET_MONTH_PAY_WEBVPN_URL,
            params={
                "vpn-12-o2-zifuwu.ustb.edu.cn": "",
                "pageSize": 100,
                "pageNumber": 1,
                "sortName": 0,
                "sortOrder": "DESC",
                "year": year,
                "_": int(time.time() * 1000)
            },
            headers={
                "Cookie": f"show_vpn=0; show_faq=0; wengine_vpn_ticketelib_ustb_edu_cn={vpn_cookie}",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json"
            }
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


async def get_payments(client: httpx.AsyncClient, vpn_cookie: str, start_date: str, end_date: str) -> Optional[dict]:
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
            SELF_GET_PAYMENT_WEBVPN_URL,
            params={
                "vpn-12-o2-zifuwu.ustb.edu.cn": "",
                "pageSize": 100,
                "pageNumber": 1,
                "sortName": 0,
                "sortOrder": "DESC",
                "startTime": start_date,
                "endTime": end_date,
                "_": int(time.time() * 1000)
            },
            headers={
                "Cookie": f"show_vpn=0; show_faq=0; wengine_vpn_ticketelib_ustb_edu_cn={vpn_cookie}",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json"
            }
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


async def get_flow_info(client: httpx.AsyncClient, vpn_cookie: str) -> Optional[dict]:
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
    account_info = await get_account_info_from_dashboard(client, vpn_cookie)
    if not account_info:
        return None

    # 获取在线设备
    online_devices = await get_online_devices(client, vpn_cookie)

    # 获取最近历史记录（最多5条）
    recent_history = await get_login_history(client, vpn_cookie, limit=5)

    return {
        **account_info,
        "online_devices": online_devices,
        "recent_history": recent_history
    }


# ===== 兼容旧 API 的函数 =====

async def login_via_vpn(account: str, password: str) -> Optional[str]:
    """
    登录 VPN 并返回 cookie（简化版，不登录后台）
    """
    vpn_cookie, client = await login_vpn_only(account, password)
    if client:
        await client.aclose()
    return vpn_cookie


async def get_user_flow(session: WifiSession, account: str) -> Optional[dict]:
    """
    获取用户流量信息（使用API接口）
    """
    result = await get_flow_info(session.client, session.cookie)
    if result:
        return {
            "account": result.get("account", account),
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
    return None
