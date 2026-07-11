import asyncio
import json
from pathlib import Path
from urllib.parse import parse_qs

import httpx
from fastapi.testclient import TestClient

from app.cache import reference_data_cache
from app.dependencies import get_authenticated_session
from app.main import app
from app.services.session_store import AuthState, Session

FIXTURES = Path(__file__).parent / "fixtures"


def test_categories_use_the_current_byyt_endpoint_and_normalize_items():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/component/queryKclb"
        assert parse_qs(request.content.decode()) == {"pylb": ["1"]}
        return httpx.Response(
            200,
            json={
                "code": 200,
                "content": [
                    {"dm": "01", "mc": "必修"},
                    {"dm": "02", "mc": "选修"},
                ],
            },
        )

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(
        client=upstream,
        state=AuthState.ACTIVE,
        authenticated=True,
        lock=asyncio.Lock(),
    )
    reference_data_cache.clear()
    app.dependency_overrides[get_authenticated_session] = lambda: session

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/courses/categories")
    finally:
        app.dependency_overrides.clear()
        reference_data_cache.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == [
        {"code": "01", "name": "必修"},
        {"code": "02", "name": "选修"},
    ]


def test_announcements_normalize_an_empty_success_response_to_an_empty_list():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(
                200,
                json={
                    "p_xn": "2025-2026",
                    "p_xq": "2",
                    "p_xnxq": "2025-20262",
                    "p_dqxn": "2025-2026",
                    "p_dqxq": "2",
                    "p_dqxnxq": "2025-20262",
                },
            )
        assert request.url.path == "/Xsxk/queryXkggZx"
        return httpx.Response(200, content=b"")

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(
        client=upstream,
        state=AuthState.ACTIVE,
        authenticated=True,
        lock=asyncio.Lock(),
    )
    app.dependency_overrides[get_authenticated_session] = lambda: session

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(
                "/api/courses/announcements",
                params={"xn": "2025-2026", "xq": "2"},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == []


def test_conflict_check_treats_jg_one_as_clear():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(
                200,
                json={
                    "p_xn": "2025-2026",
                    "p_xq": "2",
                    "p_xnxq": "2025-20262",
                    "p_dqxn": "2025-2026",
                    "p_dqxq": "2",
                    "p_dqxnxq": "2025-20262",
                },
            )
        assert request.url.path == "/Xsxk/cxmtctPd"
        return httpx.Response(200, json={"jg": "1", "message": "无冲突"})

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(
        client=upstream,
        state=AuthState.ACTIVE,
        authenticated=True,
        lock=asyncio.Lock(),
    )
    app.dependency_overrides[get_authenticated_session] = lambda: session

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/courses/check-conflict",
                json={"course_id": "task-1", "method": "bx-b-b"},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json()["has_conflict"] is False


def test_conflict_check_marks_jg_minus_nine_as_conflict():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(
                200,
                json={
                    "p_xn": "2025-2026",
                    "p_xq": "2",
                    "p_xnxq": "2025-20262",
                    "p_dqxn": "2025-2026",
                    "p_dqxq": "2",
                    "p_dqxnxq": "2025-20262",
                },
            )
        assert request.url.path == "/Xsxk/cxmtctPd"
        return httpx.Response(200, json={"jg": "-9", "message": "与已选课程冲突"})

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(
        client=upstream,
        state=AuthState.ACTIVE,
        authenticated=True,
        lock=asyncio.Lock(),
    )
    app.dependency_overrides[get_authenticated_session] = lambda: session

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/courses/check-conflict",
                json={"course_id": "task-2", "method": "bx-b-b"},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == {
        "has_conflict": True,
        "allowed": False,
        "status": "conflict",
        "message": "与已选课程冲突",
    }


def test_upstream_frequency_limits_are_exposed_as_a_retryable_429():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 500, "msg": "查询请求频率过高"})

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(
        client=upstream,
        state=AuthState.ACTIVE,
        authenticated=True,
        lock=asyncio.Lock(),
    )
    reference_data_cache.clear()
    app.dependency_overrides[get_authenticated_session] = lambda: session

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/courses/categories")
    finally:
        app.dependency_overrides.clear()
        reference_data_cache.clear()
        upstream.close()

    assert response.status_code == 429
    error = response.json()["error"]
    request_id = error.pop("request_id")
    assert request_id
    assert response.headers["x-request-id"] == request_id
    assert error == {
        "code": "UPSTREAM_RATE_LIMITED",
        "message": "教务系统请求过于频繁，请稍后重试",
        "retryable": True,
    }


def test_unavailable_upstream_is_exposed_as_retryable_503_with_request_id():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="maintenance")

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(
        client=upstream,
        state=AuthState.ACTIVE,
        authenticated=True,
        lock=asyncio.Lock(),
    )
    reference_data_cache.clear()
    app.dependency_overrides[get_authenticated_session] = lambda: session

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/courses/categories")
    finally:
        app.dependency_overrides.clear()
        reference_data_cache.clear()
        upstream.close()

    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "UPSTREAM_UNAVAILABLE"
    assert error["retryable"] is True
    assert error["request_id"]
    assert response.headers["x-request-id"] == error["request_id"]


def test_expired_upstream_sessions_are_exposed_as_401():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text="<html>login</html>",
        )

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(
        client=upstream,
        state=AuthState.ACTIVE,
        authenticated=True,
        lock=asyncio.Lock(),
    )
    reference_data_cache.clear()
    app.dependency_overrides[get_authenticated_session] = lambda: session

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/courses/categories")
    finally:
        app.dependency_overrides.clear()
        reference_data_cache.clear()
        upstream.close()

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UPSTREAM_SESSION_EXPIRED"


def test_upstream_failure_envelopes_are_exposed_as_502():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 500, "msg": "上游处理失败"})

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(
        client=upstream,
        state=AuthState.ACTIVE,
        authenticated=True,
        lock=asyncio.Lock(),
    )
    reference_data_cache.clear()
    app.dependency_overrides[get_authenticated_session] = lambda: session

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/courses/categories")
    finally:
        app.dependency_overrides.clear()
        reference_data_cache.clear()
        upstream.close()

    assert response.status_code == 502
    error = response.json()["error"]
    request_id = error.pop("request_id")
    assert request_id
    assert response.headers["x-request-id"] == request_id
    assert error == {
        "code": "UPSTREAM_BAD_RESPONSE",
        "message": "教务系统返回了无法处理的响应",
        "retryable": True,
    }


def test_legacy_selected_courses_use_the_byyt_adapter():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(
                200,
                json={
                    "p_xn": "2025-2026",
                    "p_xq": "2",
                    "p_xnxq": "2025-20262",
                    "p_dqxn": "2025-2026",
                    "p_dqxq": "2",
                    "p_dqxnxq": "2025-20262",
                },
            )
        assert request.url.path == "/Xsxk/queryYxkc"
        return httpx.Response(
            200,
            json={"yxkcList": [{"rwh": "task-1", "kcdm": "CS1", "kcmc": "程序设计", "xf": "3"}]},
        )

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(client=upstream, state=AuthState.ACTIVE, authenticated=True)
    app.dependency_overrides[get_authenticated_session] = lambda: session
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/courses/selected")
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json()["courses"][0]["task_id"] == "task-1"
    assert response.json()["total_credits"] == 3.0


def test_legacy_course_write_uses_the_byyt_adapter_without_real_network():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(
                200,
                json={
                    "p_xn": "2025-2026",
                    "p_xq": "2",
                    "p_xnxq": "2025-20262",
                    "p_dqxn": "2025-2026",
                    "p_dqxq": "2",
                    "p_dqxnxq": "2025-20262",
                },
            )
        if request.url.path == "/Xsxk/cxmtctPd":
            return httpx.Response(200, json={"jg": "1", "message": "无冲突"})
        assert request.url.path == "/Xsxk/addGouwuche"
        form = parse_qs(request.content.decode(), keep_blank_values=True)
        assert form["p_id"] == ["task-1"]
        assert form["p_xktjz"] == ["rwtjzyx"]
        return httpx.Response(200, json={"jg": "1", "message": "成功"})

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(client=upstream, state=AuthState.ACTIVE, authenticated=True)
    app.dependency_overrides[get_authenticated_session] = lambda: session
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/courses/select",
                headers={
                    "Origin": "http://localhost:5173",
                    "Idempotency-Key": "legacy-write-123",
                },
                json={"course_id": "task-1", "method": "bx-b-b"},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "成功"}


def test_legacy_course_reference_data_classifies_malformed_json():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/component/queryKkyx"
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b"not-json",
        )

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(
        client=upstream,
        state=AuthState.ACTIVE,
        authenticated=True,
        lock=asyncio.Lock(),
    )
    reference_data_cache.clear()
    app.dependency_overrides[get_authenticated_session] = lambda: session

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/courses/colleges")
    finally:
        app.dependency_overrides.clear()
        reference_data_cache.clear()
        upstream.close()

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_BAD_RESPONSE"


def test_course_context_returns_the_dynamic_selection_methods():
    term_fixture = json.loads((FIXTURES / "course_term_info.json").read_text())
    context_fixture = json.loads((FIXTURES / "course_selection_context.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(200, json=term_fixture)
        assert request.url.path == "/Xsxk/queryYxkc"
        form = parse_qs(request.content.decode(), keep_blank_values=True)
        assert form["p_xkfsdm"] == ["yixuan"]
        assert form["p_xn"] == ["2025-2026"]
        assert form["p_xq"] == ["2"]
        return httpx.Response(200, json=context_fixture)

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(
        client=upstream,
        state=AuthState.ACTIVE,
        authenticated=True,
        lock=asyncio.Lock(),
    )
    app.dependency_overrides[get_authenticated_session] = lambda: session

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/courses/context")
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == {
        "term": {
            "year": "2025-2026",
            "semester": "2",
            "code": "2025-2026-2",
        },
        "methods": [
            {
                "code": "bx-b-b",
                "name": "必修",
                "name_en": "Required",
                "mode": "1",
            },
            {
                "code": "sztzk-b-b",
                "name": "素质拓展选课",
                "name_en": "Quality Development",
                "mode": "1",
            },
            {
                "code": "zytzk-b-b",
                "name": "专业拓展选课",
                "name_en": "Major Development",
                "mode": "1",
            },
        ],
    }
