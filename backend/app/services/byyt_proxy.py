import asyncio
from typing import Optional
from .session_store import Session, AuthState

BYYT_BASE = "https://byyt.ustb.edu.cn"


async def proxy_request(session: Session, path: str, params: Optional[dict] = None) -> dict:
    if session.state != AuthState.ACTIVE:
        raise PermissionError("Not authenticated")

    allowed_paths = set()

    def _sync():
        url = f"{BYYT_BASE}{path}"
        resp = session.client.get(url, params=params or {}, follow_redirects=True)
        resp.raise_for_status()
        return resp.json()

    async with session.lock:
        return await asyncio.to_thread(_sync)


async def get_grades(session: Session, semester: Optional[str] = None) -> dict:
    params = {}
    if semester:
        params["XNXQDM"] = semester
    return await proxy_request(session, "/jwapp/sys/wdcj/modules/wdcj/xscjcx.do", params)


async def get_profile(session: Session) -> dict:
    return await proxy_request(session, "/jwapp/sys/emappagelog/config/index.do")
