import asyncio
from typing import Any

from app.byyt.errors import BYYTRateLimited, BYYTUpstreamError
from app.exceptions import BYYTSessionExpired
from app.services.session_store import Session


BYYT_BASE_URL = "https://byyt.ustb.edu.cn"


class BYYTClient:
    """Single request boundary for the BYYT upstream system."""

    def __init__(self, session: Session, base_url: str = BYYT_BASE_URL):
        self._session = session
        self._base_url = base_url.rstrip("/")

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        allow_empty: bool = False,
        unwrap_content: bool = False,
        **kwargs: Any,
    ) -> Any:
        url = f"{self._base_url}/{path.lstrip('/')}"

        async with self._session.lock:
            response = await asyncio.to_thread(
                self._session.client.request,
                method,
                url,
                **kwargs,
            )

        if response.status_code == 401 or "authentication" in str(response.url).lower():
            raise BYYTSessionExpired("BYYT session expired")

        if "text/html" in response.headers.get("content-type", "").lower():
            raise BYYTSessionExpired("BYYT session expired")

        response.raise_for_status()

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
