import asyncio
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi.testclient import TestClient

from app.cache import reference_data_cache
from app.dependencies import get_authenticated_session
from app.main import app
from app.services.session_store import AuthState, Session


TERM_INFO = {
    "p_xn": "2025-2026",
    "p_xq": "2",
    "p_xnxq": "2025-20262",
    "p_dqxn": "2025-2026",
    "p_dqxq": "2",
    "p_dqxnxq": "2025-20262",
}


def _request(path, handler, params=None):
    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(
        client=upstream,
        state=AuthState.ACTIVE,
        authenticated=True,
        lock=asyncio.Lock(),
    )
    app.dependency_overrides[get_authenticated_session] = lambda: session
    reference_data_cache.clear()
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            return client.get(path, params=params)
    finally:
        app.dependency_overrides.clear()
        reference_data_cache.clear()
        upstream.close()


def test_course_selection_context_returns_dynamic_methods_and_references():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(200, json=TERM_INFO)
        if request.url.path == "/Xsxk/queryYxkc":
            return httpx.Response(
                200,
                json={
                    "xkgzszList": [
                        {
                            "xkfsdm": "bx-b-b",
                            "xkfsmc": "必修",
                            "xkfsmc_en": "Required",
                            "xkms": "1",
                        }
                    ]
                },
            )
        if request.url.path == "/component/queryKkyx":
            return httpx.Response(200, json=[{"YXDM": "01", "YXMC": "计算机学院"}])
        if request.url.path == "/component/queryKclb":
            return httpx.Response(200, json={"code": 200, "content": [{"dm": "A", "mc": "专业课"}]})
        assert request.url.path == "/component/queryXiaoqu"
        return httpx.Response(200, json={"code": 200, "content": [{"dm": "1", "mc": "校本部"}]})

    response = _request("/api/course-selection/context", handler)

    assert response.status_code == 200
    assert response.json() == {
        "term": {"year": "2025-2026", "semester": "2", "code": "2025-2026-2"},
        "methods": [{"code": "bx-b-b", "name": "必修", "name_en": "Required", "mode": "1"}],
        "colleges": [{"code": "01", "name": "计算机学院"}],
        "categories": [{"code": "A", "name": "专业课"}],
        "campuses": [{"code": "1", "name": "校本部"}],
        "capabilities": {
            "course_query": True,
            "selected_query": True,
            "cart_query": True,
            "log_query": True,
            "preflight": True,
            "writes_enabled": True,
        },
    }


def test_course_selection_courses_return_a_typed_page():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(200, json=TERM_INFO)
        assert request.url.path == "/Xsxk/queryKxrw"
        form = parse_qs(request.content.decode(), keep_blank_values=True)
        assert form["p_xkfsdm"] == ["bx-b-b"]
        assert form["p_sfmxzj"] == ["1"]
        assert form["pageNum"] == ["2"]
        assert form["pageSize"] == ["10"]
        return httpx.Response(
            200,
            json={
                "kxrwList": {
                    "list": [
                        {
                            "rwh": "task-1",
                            "kcdm": "CS1",
                            "kcmc": "程序设计",
                            "xf": "3",
                            "zrl": "100",
                            "yxzrs": "80",
                            "yxzrlrs": "85",
                            "dnrl": "50",
                            "dnyxrlrs": "35",
                            "dwrl": "50",
                            "dwyxrlrs": "50",
                            "xkzt": "未选",
                        }
                    ],
                    "total": 21,
                }
            },
        )

    response = _request(
        "/api/course-selection/courses",
        handler,
        params={"method": "bx-b-b", "facing": "1", "page": 2, "page_size": 10},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 2
    assert body["page_size"] == 10
    assert body["total"] == 21
    assert body["method"] == "bx-b-b"
    assert body["items"][0] == {
        "course_id": "task-1",
        "selection_id": None,
        "course_code": "CS1",
        "course_name": "程序设计",
        "course_name_en": "",
        "course_nature": "",
        "course_category": "",
        "credits": 3.0,
        "hours": None,
        "method": "",
        "college": "",
        "campus": "",
        "capacity": 100,
        "selected_count": 85,
        "internal_capacity": 50,
        "internal_selected_count": 35,
        "external_capacity": 50,
        "external_selected_count": 50,
        "teacher": "",
        "schedule_time": "",
        "schedule_location": "",
        "selection_status": "未选",
        "is_selected": False,
    }


@pytest.mark.parametrize(
    ("route", "upstream_path", "payload_key"),
    [
        ("/api/course-selection/selected", "/Xsxk/queryYxkc", "yxkcList"),
        ("/api/course-selection/cart", "/Xsxk/queryXkgwc", "gwcList"),
    ],
)
def test_course_selection_selected_and_cart_use_typed_records(route, upstream_path, payload_key):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(200, json=TERM_INFO)
        assert request.url.path == upstream_path
        return httpx.Response(
            200,
            json={
                payload_key: [
                    {
                        "id": "selection-1",
                        "rwh": "task-1",
                        "kcdm": "CS1",
                        "kcmc": "程序设计",
                        "xf": "3",
                    }
                ]
            },
        )

    response = _request(route, handler)

    assert response.status_code == 200
    assert response.json()["items"][0]["course_id"] == "task-1"
    assert response.json()["items"][0]["selection_id"] == "selection-1"
    assert response.json()["total_credits"] == 3.0


def test_course_selection_preflight_returns_conflict_without_writing():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(200, json=TERM_INFO)
        assert request.url.path == "/Xsxk/cxmtctPd"
        return httpx.Response(200, json={"jg": "-9", "message": "课程冲突"})

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(client=upstream, state=AuthState.ACTIVE, authenticated=True)
    app.dependency_overrides[get_authenticated_session] = lambda: session
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/course-selection/preflight",
                json={"course_id": "task-1", "method": "bx-b-b"},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == {
        "allowed": False,
        "status": "conflict",
        "message": "课程冲突",
    }


def test_course_selection_cookie_write_requires_a_trusted_origin():
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, json=TERM_INFO)

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(client=upstream, state=AuthState.ACTIVE, authenticated=True)
    app.dependency_overrides[get_authenticated_session] = lambda: session
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/course-selection/selections",
                headers={"Idempotency-Key": "write-key-123"},
                json={"course_id": "task-1", "method": "bx-b-b"},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 403
    assert request_count == 0


def test_course_selection_bearer_write_is_idempotent_and_calls_selection_directly():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(200, json=TERM_INFO)
        assert request.url.path == "/Xsxk/addGouwuche"
        return httpx.Response(200, json={"jg": "1", "message": "选课成功"})

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(client=upstream, state=AuthState.ACTIVE, authenticated=True)
    app.dependency_overrides[get_authenticated_session] = lambda: session
    headers = {
        "Authorization": "Bearer test-session",
        "Idempotency-Key": "write-key-123",
    }
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            first = client.post(
                "/api/course-selection/selections",
                headers=headers,
                json={"course_id": "task-1", "method": "bx-b-b"},
            )
            second = client.post(
                "/api/course-selection/selections",
                headers=headers,
                json={"course_id": "task-1", "method": "bx-b-b"},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert first.status_code == second.status_code == 200
    assert (
        first.json()
        == second.json()
        == {
            "success": True,
            "status": "success",
            "message": "选课成功",
        }
    )
    assert requests == [
        "/Xsxk/queryXkdqXnxq",
        "/Xsxk/addGouwuche",
    ]


def test_course_selection_classifies_a_direct_conflict_rejection():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(200, json=TERM_INFO)
        assert request.url.path == "/Xsxk/addGouwuche"
        return httpx.Response(200, json={"jg": "0", "message": "课程冲突"})

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(client=upstream, state=AuthState.ACTIVE, authenticated=True)
    app.dependency_overrides[get_authenticated_session] = lambda: session
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/course-selection/selections",
                headers={
                    "Authorization": "Bearer test-session",
                    "Idempotency-Key": "write-key-123",
                },
                json={"course_id": "task-1", "method": "bx-b-b"},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "COURSE_CONFLICT"
    assert response.json()["error"]["message"] == "课程冲突"
    assert response.json()["error"]["retryable"] is False
    assert response.json()["error"]["request_id"]
    assert requests == ["/Xsxk/queryXkdqXnxq", "/Xsxk/addGouwuche"]


def test_course_selection_uses_internal_id_and_enriches_a_generic_conflict():
    requests = []
    detailed_message = (
        "上课时间冲突，当前课程：德国国情(排课)，"
        "冲突课程：信息系统开发实践II(排课)"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(200, json=TERM_INFO)
        form = parse_qs(request.content.decode(), keep_blank_values=True)
        assert form["p_id"] == ["internal-task-id"]
        if request.url.path == "/Xsxk/addGouwuche":
            return httpx.Response(200, json={"jg": "0", "message": "操作失败"})
        assert request.url.path == "/Xsxk/cxmtctPd"
        return httpx.Response(200, json={"jg": "-9", "message": detailed_message})

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(client=upstream, state=AuthState.ACTIVE, authenticated=True)
    app.dependency_overrides[get_authenticated_session] = lambda: session
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/course-selection/selections",
                headers={
                    "Authorization": "Bearer test-session",
                    "Idempotency-Key": "detailed-conflict-key",
                },
                json={
                    "course_id": "task-1",
                    "selection_id": "internal-task-id",
                    "method": "sztzk-b-b",
                },
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "COURSE_CONFLICT"
    assert response.json()["error"]["message"] == detailed_message
    assert requests == [
        "/Xsxk/queryXkdqXnxq",
        "/Xsxk/addGouwuche",
        "/Xsxk/cxmtctPd",
    ]


@pytest.mark.parametrize(
    ("upstream_message", "expected_code", "retryable"),
    [
        ("该课程容量已满", "COURSE_FULL", True),
        ("当前未到选课时间", "COURSE_NOT_OPEN", True),
        ("该课程不面向您所在专业", "COURSE_NOT_ELIGIBLE", False),
        ("操作失败", "COURSE_OPERATION_BLOCKED", False),
    ],
)
def test_course_selection_classifies_direct_business_rejections(
    upstream_message,
    expected_code,
    retryable,
):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(200, json=TERM_INFO)
        assert request.url.path == "/Xsxk/addGouwuche"
        return httpx.Response(200, json={"jg": "0", "message": upstream_message})

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(client=upstream, state=AuthState.ACTIVE, authenticated=True)
    app.dependency_overrides[get_authenticated_session] = lambda: session
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/course-selection/selections",
                headers={
                    "Authorization": "Bearer test-session",
                    "Idempotency-Key": f"write-{expected_code}",
                },
                json={"course_id": "task-1", "method": "bx-b-b"},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 409
    assert response.json()["error"]["code"] == expected_code
    assert response.json()["error"]["message"] == upstream_message
    assert response.json()["error"]["retryable"] is retryable


def test_course_selection_confirms_an_already_selected_course():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(200, json=TERM_INFO)
        if request.url.path == "/Xsxk/addGouwuche":
            return httpx.Response(200, json={"jg": "0", "message": "您已经选择该课程"})
        assert request.url.path == "/Xsxk/queryYxkc"
        return httpx.Response(200, json={"yxkcList": [{"rwh": "task-1"}]})

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(client=upstream, state=AuthState.ACTIVE, authenticated=True)
    app.dependency_overrides[get_authenticated_session] = lambda: session
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/course-selection/selections",
                headers={
                    "Authorization": "Bearer test-session",
                    "Idempotency-Key": "already-selected-key",
                },
                json={"course_id": "task-1", "method": "bx-b-b"},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "status": "success",
        "message": "您已经选择该课程",
    }
    assert requests == [
        "/Xsxk/queryXkdqXnxq",
        "/Xsxk/addGouwuche",
        "/Xsxk/queryYxkc",
    ]


def test_course_selection_announcements_do_not_expose_raw_fields():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(200, json=TERM_INFO)
        assert request.url.path == "/Xsxk/queryXkggZx"
        return httpx.Response(
            200,
            json=[
                {
                    "id": "notice-1",
                    "ggbt": "选课通知",
                    "ggnr": "请按时选课",
                    "fbsj": "2026-07-10",
                    "raw_secret": "must-not-leak",
                }
            ],
        )

    response = _request("/api/course-selection/announcements", handler)

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "notice-1",
            "title": "选课通知",
            "content": "请按时选课",
            "published_at": "2026-07-10",
        }
    ]
    assert "raw_secret" not in response.text


def test_course_selection_logs_do_not_expose_raw_upstream_fields():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(200, json=TERM_INFO)
        assert request.url.path == "/Xsxk/queryXsxkrzList"
        return httpx.Response(
            200,
            json=[
                {
                    "id": "log-1",
                    "kcdm": "CS1",
                    "kcmc": "程序设计",
                    "czlxmc": "选课",
                    "czsj": "2026-07-10 10:00:00",
                    "jg": "1",
                    "message": "成功",
                    "secret_raw": "must-not-leak",
                }
            ],
        )

    response = _request("/api/course-selection/logs", handler)

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "log-1",
            "course_code": "CS1",
            "course_name": "程序设计",
            "operation": "选课",
            "operated_at": "2026-07-10 10:00:00",
            "status": "1",
            "message": "成功",
        }
    ]
    assert "secret_raw" not in response.text
