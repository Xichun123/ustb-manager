import asyncio
from types import SimpleNamespace

import httpx
import pytest

from app.byyt.client import BYYTClient
from app.byyt.errors import BYYTRateLimited, BYYTUpstreamError
from app.exceptions import BYYTSessionExpired


@pytest.mark.asyncio
async def test_request_json_allows_an_empty_success_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/Xsxk/queryXkggZx"
        return httpx.Response(200, content=b"")

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    session = SimpleNamespace(client=http_client, lock=asyncio.Lock())

    try:
        result = await BYYTClient(session).request_json(
            "POST",
            "/Xsxk/queryXkggZx",
            allow_empty=True,
        )
    finally:
        http_client.close()

    assert result is None


@pytest.mark.asyncio
async def test_request_json_reports_an_expired_session_for_html_login_pages():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text="<html>login</html>",
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    session = SimpleNamespace(client=http_client, lock=asyncio.Lock())

    try:
        with pytest.raises(BYYTSessionExpired):
            await BYYTClient(session).request_json("POST", "/component/queryXnxq")
    finally:
        http_client.close()


@pytest.mark.asyncio
async def test_request_json_reports_an_expired_session_for_unauthorized_responses():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "unauthorized"})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    session = SimpleNamespace(client=http_client, lock=asyncio.Lock())

    try:
        with pytest.raises(BYYTSessionExpired):
            await BYYTClient(session).request_json("POST", "/UserManager/queryxsxx")
    finally:
        http_client.close()


@pytest.mark.asyncio
async def test_request_json_can_unwrap_the_standard_content_envelope():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"code": 200, "content": [{"dm": "01", "mc": "必修"}]},
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    session = SimpleNamespace(client=http_client, lock=asyncio.Lock())

    try:
        result = await BYYTClient(session).request_json(
            "POST",
            "/component/queryKclb",
            unwrap_content=True,
        )
    finally:
        http_client.close()

    assert result == [{"dm": "01", "mc": "必修"}]


@pytest.mark.asyncio
async def test_request_json_classifies_the_upstream_frequency_limit():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 500, "msg": "查询请求频率过高"})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    session = SimpleNamespace(client=http_client, lock=asyncio.Lock())

    try:
        with pytest.raises(BYYTRateLimited):
            await BYYTClient(session).request_json("POST", "/Xsxk/queryKxrw")
    finally:
        http_client.close()


@pytest.mark.asyncio
async def test_request_json_rejects_non_success_byyt_envelopes():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 500, "msg": "上游处理失败"})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    session = SimpleNamespace(client=http_client, lock=asyncio.Lock())

    try:
        with pytest.raises(BYYTUpstreamError):
            await BYYTClient(session).request_json("POST", "/component/queryKclb")
    finally:
        http_client.close()


@pytest.mark.asyncio
async def test_request_json_rejects_unexpected_empty_responses():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"")

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    session = SimpleNamespace(client=http_client, lock=asyncio.Lock())

    try:
        with pytest.raises(BYYTUpstreamError):
            await BYYTClient(session).request_json("POST", "/component/queryKclb")
    finally:
        http_client.close()
