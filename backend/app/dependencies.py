"""公共依赖 - 认证、会话等。"""

from typing import Optional

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer

from .config import COOKIE_NAME
from .services.session_store import Session, store

_bearer_scheme = HTTPBearer(auto_error=False)
_cookie_scheme = APIKeyCookie(name=COOKIE_NAME, auto_error=False)


def get_optional_session_token(
    bearer: Optional[HTTPAuthorizationCredentials] = Security(_bearer_scheme),
    cookie_token: Optional[str] = Security(_cookie_scheme),
) -> Optional[str]:
    """Resolve the opaque session token from Bearer auth or the browser cookie."""
    if bearer and bearer.scheme.lower() == "bearer" and bearer.credentials:
        return bearer.credentials
    return cookie_token


def get_authenticated_session(
    session_token: Optional[str] = Depends(get_optional_session_token),
) -> Session:
    """获取已认证的 Cookie/Bearer 共用会话。"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = store.get(session_token)
    if not session:
        raise HTTPException(status_code=401, detail="Session not found")

    if not session.authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return session
