"""
Playwright-based login for WebVPN and zifuwu system.

WebVPN uses JavaScript to manage session cookies, which httpx cannot handle.
Playwright simulates a real browser to complete the login process.

Key insight: The zifuwu login must be done via XHR request to properly establish
the session. Regular form submission fails due to WebVPN's JavaScript handling.
"""
import hashlib
from playwright.async_api import async_playwright

VPN_HOST = "elib.ustb.edu.cn"
ZIFUWU_LOGIN_URL = f"https://{VPN_HOST}/https/77726476706e69737468656265737421eafe4789302526456d1c8be29d51367b8ada/Self/login"
ZIFUWU_VERIFY_URL = "/https/77726476706e69737468656265737421eafe4789302526456d1c8be29d51367b8ada/Self/login/verify"
ZIFUWU_DASHBOARD_URL = f"https://{VPN_HOST}/https/77726476706e69737468656265737421eafe4789302526456d1c8be29d51367b8ada/Self/dashboard"


async def login_zifuwu_with_playwright(account: str, password: str) -> tuple[str | None, dict | None, bool]:
    """
    Use Playwright to login to VPN and zifuwu system.

    Args:
        account: Student ID
        password: Campus network password

    Returns:
        (vpn_cookie, all_cookies, success) - VPN cookie value, all cookies dict, and whether login succeeded
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            print(f"[Playwright] Starting login for account: {account}")

            # 1. Navigate to VPN login page
            print("[Playwright] Step 1: Accessing VPN login page...")
            await page.goto(f"https://{VPN_HOST}/login", wait_until="networkidle", timeout=30000)

            # 2. Fill VPN login form
            print("[Playwright] Step 2: Filling VPN credentials...")
            await page.fill('input[name="username"]', account)
            await page.fill('input[name="password"]', password)

            # 3. Submit VPN login (use the correct button selector)
            print("[Playwright] Step 3: Submitting VPN login...")
            await page.click('button.el-button-login, button:has-text("登录")')

            # 4. Wait for VPN login to complete
            try:
                await page.wait_for_url(lambda url: "/login" not in url or "portal" in url, timeout=15000)
                print(f"[Playwright] VPN login completed, current URL: {page.url}")
            except Exception as e:
                page_content = await page.content()
                if "用户名或密码错误" in page_content or "密码错误" in page_content:
                    print("[Playwright] VPN login failed: wrong credentials")
                    return None, None, False
                print(f"[Playwright] VPN login wait timeout, continuing... ({e})")

            # 5. Extract VPN cookie
            cookies = await context.cookies()
            vpn_cookie = None
            for cookie in cookies:
                if "wengine_vpn_ticket" in cookie["name"]:
                    vpn_cookie = cookie["value"]
                    break

            if not vpn_cookie:
                print("[Playwright] Warning: VPN cookie not found")
                return None, None, False

            print(f"[Playwright] VPN cookie obtained: {vpn_cookie[:20]}...")

            # 6. Navigate to zifuwu login page to get checkcode
            print("[Playwright] Step 4: Accessing zifuwu login page...")
            await page.goto(ZIFUWU_LOGIN_URL, wait_until="networkidle", timeout=30000)

            # Small delay to ensure page is fully loaded
            import asyncio
            await asyncio.sleep(1)

            # 7. Get checkcode from the hidden input
            checkcode = await page.evaluate('document.querySelector("input[name=checkcode]")?.value || ""')
            if not checkcode:
                print("[Playwright] Warning: Could not get checkcode, trying anyway...")
                checkcode = "0000"

            print(f"[Playwright] Got checkcode: {checkcode}")

            # 8. Login to zifuwu via XHR (this is the key - form submission doesn't work!)
            print("[Playwright] Step 5: Logging into zifuwu via XHR...")
            password_md5 = hashlib.md5(password.encode()).hexdigest()

            # Use XHR to submit login - this properly establishes the session
            xhr_result = await page.evaluate(f'''async () => {{
                return new Promise((resolve) => {{
                    const xhr = new XMLHttpRequest();
                    xhr.open('POST', '{ZIFUWU_VERIFY_URL}', true);
                    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
                    xhr.onreadystatechange = function() {{
                        if (xhr.readyState === 4) {{
                            resolve({{
                                status: xhr.status,
                                url: xhr.responseURL
                            }});
                        }}
                    }};
                    xhr.send('foo=&bar=&checkcode={checkcode}&account={account}&password={password_md5}&code=');
                }});
            }}''')

            print(f"[Playwright] XHR result: status={xhr_result.get('status')}")

            # 9. Navigate to dashboard to verify login
            print("[Playwright] Step 6: Verifying login by accessing dashboard...")
            await page.goto(ZIFUWU_DASHBOARD_URL, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(1)

            # Check if we're on the dashboard (not redirected to login)
            current_url = page.url.lower()
            if "dashboard" in current_url and "login" not in current_url:
                # Try to get user data to confirm
                user_data = await page.evaluate("window.user || null")

                # Extract all cookies for httpx to use
                all_cookies_raw = await context.cookies()
                all_cookies = {}
                for c in all_cookies_raw:
                    all_cookies[c["name"]] = c["value"]

                if user_data:
                    print(f"[Playwright] Login successful! User: {user_data.get('userName', 'Unknown')}")
                    return vpn_cookie, all_cookies, True
                else:
                    print("[Playwright] Dashboard loaded but no user data")
                    return vpn_cookie, all_cookies, True  # Still consider it a success
            else:
                print(f"[Playwright] Login may have failed, URL: {page.url}")
                # Check for error message
                page_content = await page.content()
                if "账号或密码错误" in page_content or "密码错误" in page_content:
                    print("[Playwright] Zifuwu login failed: wrong credentials")
                return None, None, False

        except Exception as e:
            print(f"[Playwright] Login failed with error: {e}")
            import traceback
            traceback.print_exc()
            return None, None, False

        finally:
            await browser.close()
            print("[Playwright] Browser closed")


async def get_zifuwu_session_with_playwright(account: str, password: str) -> tuple[str | None, dict | None]:
    """
    Use Playwright to login and extract both VPN cookie and zifuwu session cookies.

    Returns:
        (vpn_cookie, all_cookies_dict) - VPN cookie and all cookies as a dict
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            # 1. Login to VPN
            await page.goto(f"https://{VPN_HOST}/login", wait_until="networkidle", timeout=30000)
            await page.fill('input[name="username"]', account)
            await page.fill('input[name="password"]', password)
            await page.click('button.el-button-login, button:has-text("登录")')

            try:
                await page.wait_for_url(lambda url: "/login" not in url, timeout=15000)
            except:
                page_content = await page.content()
                if "用户名或密码错误" in page_content:
                    return None, None

            # 2. Get VPN cookie
            cookies = await context.cookies()
            vpn_cookie = None
            for c in cookies:
                if "wengine_vpn_ticket" in c["name"]:
                    vpn_cookie = c["value"]
                    break

            if not vpn_cookie:
                return None, None

            # 3. Login to zifuwu via XHR
            await page.goto(ZIFUWU_LOGIN_URL, wait_until="networkidle", timeout=30000)

            import asyncio
            await asyncio.sleep(1)

            checkcode = await page.evaluate('document.querySelector("input[name=checkcode]")?.value || "0000"')
            password_md5 = hashlib.md5(password.encode()).hexdigest()

            await page.evaluate(f'''async () => {{
                return new Promise((resolve) => {{
                    const xhr = new XMLHttpRequest();
                    xhr.open('POST', '{ZIFUWU_VERIFY_URL}', true);
                    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
                    xhr.onreadystatechange = function() {{
                        if (xhr.readyState === 4) resolve(true);
                    }};
                    xhr.send('foo=&bar=&checkcode={checkcode}&account={account}&password={password_md5}&code=');
                }});
            }}''')

            # 4. Verify by going to dashboard
            await page.goto(ZIFUWU_DASHBOARD_URL, wait_until="networkidle", timeout=30000)

            if "dashboard" not in page.url.lower() or "login" in page.url.lower():
                return None, None

            # 5. Extract all cookies
            cookies = await context.cookies()
            all_cookies = {}
            for cookie in cookies:
                all_cookies[cookie["name"]] = cookie["value"]

            return vpn_cookie, all_cookies

        except Exception as e:
            print(f"[Playwright] Session extraction failed: {e}")
            return None, None

        finally:
            await browser.close()
