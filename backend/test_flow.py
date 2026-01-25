"""Test script to debug flow retrieval"""
import asyncio
import httpx
import re
from bs4 import BeautifulSoup

VPN_HOST = "elib.ustb.edu.cn"
VPN_COOKIE_NAME = "wengine_vpn_ticketelib_ustb_edu_cn"
AUTH_PATH = "77726476706e69737468656265737421a2a713d275603c1e2a50c7face"

async def test_flow():
    # First login to VPN
    account = "U202440984"  # From the session
    password = input("Enter campus network password: ")

    client = httpx.AsyncClient(follow_redirects=True, timeout=60.0)

    try:
        # 1. Get login page
        print(f"[1] Accessing VPN login page...")
        res = await client.get(f"https://{VPN_HOST}/login")
        print(f"    Status: {res.status_code}")

        # Extract captcha_id
        match = re.search(r'name="captcha_id" value="([^"]*)"', res.text)
        if not match:
            print("    ERROR: Cannot find captcha_id")
            return
        captcha_id = match.group(1)
        print(f"    captcha_id: {captcha_id}")

        # 2. Login
        print(f"\n[2] Logging in as {account}...")
        res = await client.post(
            f"https://{VPN_HOST}/do-login",
            data={
                "auth_type": "local",
                "username": account,
                "sms_code": "",
                "password": password,
                "captcha": "",
                "needCaptcha": "false",
                "captcha_id": captcha_id,
            },
            headers={"Referer": f"https://{VPN_HOST}/login"},
        )
        print(f"    Status: {res.status_code}")
        print(f"    Response: {res.text[:200]}")

        # Check VPN cookie
        vpn_cookie = None
        for cookie in client.cookies.jar:
            if cookie.name == VPN_COOKIE_NAME:
                vpn_cookie = cookie.value
                break

        if not vpn_cookie:
            print("    ERROR: No VPN cookie found")
            return
        print(f"    VPN cookie: {vpn_cookie[:20]}...")

        # 3. Access logout page
        url = f"https://{VPN_HOST}/http/{AUTH_PATH}/"
        print(f"\n[3] Accessing logout page: {url}")
        res = await client.get(url)
        print(f"    Final URL: {res.url}")
        print(f"    Status: {res.status_code}")
        print(f"    Response length: {len(res.text)}")

        # Save response for analysis
        with open("/tmp/logout_page.html", "w") as f:
            f.write(res.text)
        print(f"    Saved response to /tmp/logout_page.html")

        # Parse
        soup = BeautifulSoup(res.text, "html.parser")

        # Try table parsing
        print("\n[4] Parsing table rows...")
        for row in soup.select("tr"):
            cells = row.select("td")
            if len(cells) >= 2:
                label = cells[0].get_text().strip()
                value = cells[1].get_text().strip()
                print(f"    {label}: {value}")

        # Try text parsing
        print("\n[5] Full page text:")
        print(soup.get_text()[:1000])

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.aclose()

if __name__ == "__main__":
    asyncio.run(test_flow())
