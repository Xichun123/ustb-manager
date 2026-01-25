#!/usr/bin/env python
"""
测试 Playwright 登录功能

使用方法:
    uv run python test_playwright_login.py <学号> <校园网密码>
"""
import asyncio
import sys

from app.services.wifi_playwright import login_zifuwu_with_playwright


async def main():
    if len(sys.argv) < 3:
        print("Usage: uv run python test_playwright_login.py <学号> <校园网密码>")
        sys.exit(1)

    account = sys.argv[1]
    password = sys.argv[2]

    print(f"Testing Playwright login for account: {account}")
    print("=" * 50)

    vpn_cookie, success = await login_zifuwu_with_playwright(account, password)

    print("=" * 50)
    print(f"Result: {'SUCCESS' if success else 'FAILED'}")
    if vpn_cookie:
        print(f"VPN Cookie: {vpn_cookie[:30]}...")
    else:
        print("VPN Cookie: None")


if __name__ == "__main__":
    asyncio.run(main())
