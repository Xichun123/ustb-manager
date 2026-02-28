"""公共依赖 - 认证、会话等"""
from typing import Optional
from fastapi import Cookie, HTTPException

from .services.session_store import store, Session


def get_authenticated_session(ustb_sid: Optional[str] = Cookie(None)) -> Session:
    """获取已认证的会话，用于需要登录的端点。

    Raises:
        HTTPException 401: 未提供cookie / session不存在 / 未认证
    """
    if not ustb_sid:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = store.get(ustb_sid)
    if not session:
        raise HTTPException(status_code=401, detail="Session not found")

    if not session.authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return session
