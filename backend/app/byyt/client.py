import asyncio
from typing import Any, Protocol

from app.byyt.errors import BYYTRateLimited, BYYTUpstreamError
from app.exceptions import BYYTSessionExpired


BYYT_BASE_URL = "https://byyt.ustb.edu.cn"


class SupportsBYYTSession(Protocol):
    """Minimal session surface needed by BYYTClient (avoids importing SessionStore)."""

    client: Any
    lock: Any


class BYYTClient:
    """Single request boundary for the BYYT upstream system."""

    def __init__(self, session: SupportsBYYTSession, base_url: str = BYYT_BASE_URL):
        self._session = session
        self._base_url = base_url.rstrip("/")

    def validate_session_sync(self) -> None:
        """Validate an unpublished restore candidate without using an event loop."""
        data = self._request_json_sync(
            "POST",
            "/UserManager/queryxsxx",
            timeout=5.0,
            follow_redirects=False,
        )
        if not isinstance(data, dict) or "XH" not in data:
            raise BYYTUpstreamError("BYYT returned invalid student information")

    def _request_json_sync(
        self,
        method: str,
        path: str,
        *,
        allow_empty: bool = False,
        unwrap_content: bool = False,
        **kwargs: Any,
    ) -> Any:
        url = f"{self._base_url}/{path.lstrip('/')}"
        response = self._session.client.request(method, url, **kwargs)
        return self._classify_json_response(
            response,
            allow_empty=allow_empty,
            unwrap_content=unwrap_content,
        )

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        allow_empty: bool = False,
        unwrap_content: bool = False,
        **kwargs: Any,
    ) -> Any:
        async with self._session.lock:
            return await asyncio.to_thread(
                self._request_json_sync,
                method,
                path,
                allow_empty=allow_empty,
                unwrap_content=unwrap_content,
                **kwargs,
            )

    @staticmethod
    def _classify_json_response(
        response: Any,
        *,
        allow_empty: bool = False,
        unwrap_content: bool = False,
    ) -> Any:
        location = response.headers.get("location", "")
        is_auth_redirect = (
            300 <= response.status_code < 400 and "authentication" in location.lower()
        )
        if (
            response.status_code == 401
            or "authentication" in str(response.url).lower()
            or is_auth_redirect
        ):
            raise BYYTSessionExpired("BYYT session expired")

        response.raise_for_status()

        if "text/html" in response.headers.get("content-type", "").lower():
            html = response.text.lower()
            if "login" in html or "authentication" in html or "统一身份认证" in html:
                raise BYYTSessionExpired("BYYT session expired")
            raise BYYTUpstreamError("BYYT returned unexpected HTML")

        if not response.content:
            if allow_empty:
                return None
            raise BYYTUpstreamError("BYYT returned an empty response")

        try:
            data = response.json()
        except ValueError as exc:
            raise BYYTUpstreamError("BYYT returned invalid JSON") from exc
        if isinstance(data, dict):
            message = " ".join(str(data.get(key, "")) for key in ("msg", "msg_en", "message"))
            if "请求频率过高" in message:
                raise BYYTRateLimited("BYYT query rate limit exceeded")
            if "code" in data and str(data.get("code")) != "200":
                raise BYYTUpstreamError("BYYT returned a failure response")

        if unwrap_content and isinstance(data, dict) and str(data.get("code")) == "200":
            return data.get("content")
        return data
