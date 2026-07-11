import asyncio
import threading
from types import SimpleNamespace

import httpx
import pytest

from app.byyt.client import BYYTClient
from app.byyt.errors import BYYTRateLimited, BYYTUnavailable, BYYTUpstreamError
from app.exceptions import BYYTSessionExpired


def _session_with_transport(handler, *, follow_redirects=False):
    http_client = httpx.Client(
        transport=httpx.MockTransport(handler),
        follow_redirects=follow_redirects,
    )
    return SimpleNamespace(client=http_client, lock=asyncio.Lock()), http_client


def test_validate_session_sync_reports_an_expired_session_for_unauthorized_responses():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/UserManager/queryxsxx"
        return httpx.Response(401, json={"detail": "unauthorized"})

    session, http_client = _session_with_transport(handler)
    try:
        with pytest.raises(BYYTSessionExpired):
            BYYTClient(session).validate_session_sync()
    finally:
        http_client.close()


@pytest.mark.asyncio
async def test_request_json_and_validate_session_sync_share_html_login_classification():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text="<html>login</html>",
        )

    session, http_client = _session_with_transport(handler)
    client = BYYTClient(session)
    try:
        with pytest.raises(BYYTSessionExpired):
            client.validate_session_sync()
        with pytest.raises(BYYTSessionExpired):
            await client.request_json("POST", "/UserManager/queryxsxx")
    finally:
        http_client.close()


def test_validate_session_sync_reports_an_expired_session_for_auth_redirects():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"location": "/authentication/login"},
        )

    session, http_client = _session_with_transport(handler, follow_redirects=True)
    try:
        with pytest.raises(BYYTSessionExpired):
            BYYTClient(session).validate_session_sync()
    finally:
        http_client.close()


def test_validate_session_sync_keeps_unrecognized_html_as_an_ambiguous_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text="<html>temporarily unavailable</html>",
        )

    session, http_client = _session_with_transport(handler)
    try:
        with pytest.raises(BYYTUpstreamError):
            BYYTClient(session).validate_session_sync()
    finally:
        http_client.close()


def test_validate_session_sync_treats_html_5xx_as_temporary_upstream_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503,
            headers={"content-type": "text/html; charset=utf-8"},
            text="<html>maintenance</html>",
        )

    session, http_client = _session_with_transport(handler)
    try:
        with pytest.raises(BYYTUnavailable):
            BYYTClient(session).validate_session_sync()
    finally:
        http_client.close()


@pytest.mark.asyncio
async def test_request_json_classifies_network_timeouts_as_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    session, http_client = _session_with_transport(handler)
    try:
        with pytest.raises(BYYTUnavailable):
            await BYYTClient(session).request_json("POST", "/component/queryXnxq")
    finally:
        http_client.close()


@pytest.mark.asyncio
async def test_request_json_retries_only_when_an_idempotent_query_opts_in():
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(200, json={"value": "ok"})

    session, http_client = _session_with_transport(handler)
    try:
        result = await BYYTClient(session).request_json(
            "POST",
            "/component/queryXnxq",
            retry_attempts=2,
            retry_delay=0,
        )
    finally:
        http_client.close()

    assert result == {"value": "ok"}
    assert request_count == 2


@pytest.mark.asyncio
async def test_request_json_does_not_retry_by_default():
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        raise httpx.ReadTimeout("timed out", request=request)

    session, http_client = _session_with_transport(handler)
    try:
        with pytest.raises(BYYTUnavailable):
            await BYYTClient(session).request_json("POST", "/Xsxk/addGouwuche")
    finally:
        http_client.close()

    assert request_count == 1


@pytest.mark.asyncio
async def test_request_json_classifies_5xx_as_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="maintenance")

    session, http_client = _session_with_transport(handler)
    try:
        with pytest.raises(BYYTUnavailable):
            await BYYTClient(session).request_json("POST", "/component/queryXnxq")
    finally:
        http_client.close()


@pytest.mark.asyncio
async def test_request_json_coalesces_matching_inflight_queries():
    started = threading.Event()
    release = threading.Event()
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        started.set()
        release.wait(timeout=2)
        return httpx.Response(200, json={"value": "ok"})

    session, http_client = _session_with_transport(handler)
    session.singleflight_lock = asyncio.Lock()
    session.inflight_queries = {}
    session.query_cache = {}
    client = BYYTClient(session)
    try:
        first = asyncio.create_task(
            client.request_json("POST", "/Xsxk/queryKxrw", single_flight_key="same")
        )
        await asyncio.to_thread(started.wait, 2)
        second = asyncio.create_task(
            client.request_json("POST", "/Xsxk/queryKxrw", single_flight_key="same")
        )
        await asyncio.sleep(0)
        release.set()
        assert await asyncio.gather(first, second) == [
            {"value": "ok"},
            {"value": "ok"},
        ]
    finally:
        release.set()
        http_client.close()

    assert request_count == 1


@pytest.mark.asyncio
async def test_request_json_uses_a_short_query_cache():
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, json={"value": request_count})

    session, http_client = _session_with_transport(handler)
    session.singleflight_lock = asyncio.Lock()
    session.inflight_queries = {}
    session.query_cache = {}
    client = BYYTClient(session)
    try:
        first = await client.request_json(
            "POST",
            "/Xsxk/queryKxrw",
            single_flight_key="same",
            cache_ttl=2,
        )
        second = await client.request_json(
            "POST",
            "/Xsxk/queryKxrw",
            single_flight_key="same",
            cache_ttl=2,
        )
    finally:
        http_client.close()

    assert first == second == {"value": 1}
    assert request_count == 1


@pytest.mark.asyncio
async def test_request_json_allows_an_empty_success_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/Xsxk/queryXkggZx"
        return httpx.Response(200, content=b"")

    session, http_client = _session_with_transport(handler)

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

    session, http_client = _session_with_transport(handler)

    try:
        with pytest.raises(BYYTSessionExpired):
            await BYYTClient(session).request_json("POST", "/component/queryXnxq")
    finally:
        http_client.close()


@pytest.mark.asyncio
async def test_request_json_reports_an_expired_session_for_unauthorized_responses():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "unauthorized"})

    session, http_client = _session_with_transport(handler)

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

    session, http_client = _session_with_transport(handler)

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

    session, http_client = _session_with_transport(handler)

    try:
        with pytest.raises(BYYTRateLimited):
            await BYYTClient(session).request_json("POST", "/Xsxk/queryKxrw")
    finally:
        http_client.close()


@pytest.mark.asyncio
async def test_request_json_rejects_non_success_byyt_envelopes():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 500, "msg": "上游处理失败"})

    session, http_client = _session_with_transport(handler)

    try:
        with pytest.raises(BYYTUpstreamError):
            await BYYTClient(session).request_json("POST", "/component/queryKclb")
    finally:
        http_client.close()


@pytest.mark.asyncio
async def test_request_json_rejects_unexpected_empty_responses():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"")

    session, http_client = _session_with_transport(handler)

    try:
        with pytest.raises(BYYTUpstreamError):
            await BYYTClient(session).request_json("POST", "/component/queryKclb")
    finally:
        http_client.close()
