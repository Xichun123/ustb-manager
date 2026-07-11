"""公共依赖 - 认证、会话等。"""

from typing import Optional
from urllib.parse import urlsplit

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer

from .config import COOKIE_NAME, CORS_ORIGINS
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


def require_trusted_write_origin(request: Request) -> None:
    """Bearer is not ambient; browser Cookie writes require a trusted Origin/Referer."""
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return

    origin = request.headers.get("origin")
    if not origin:
        referer = request.headers.get("referer")
        if referer:
            parsed = urlsplit(referer)
            origin = f"{parsed.scheme}://{parsed.netloc}"
    allowed = {value.strip().rstrip("/") for value in CORS_ORIGINS if value.strip()}
    if not origin or origin.rstrip("/") not in allowed:
        raise HTTPException(status_code=403, detail="Untrusted write origin")


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
