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
            "writes_enabled": False,
        },
    }


def test_course_selection_courses_return_a_typed_page():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(200, json=TERM_INFO)
        assert request.url.path == "/Xsxk/queryKxrw"
        form = parse_qs(request.content.decode(), keep_blank_values=True)
        assert form["p_xkfsdm"] == ["bx-b-b"]
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
        params={"method": "bx-b-b", "page": 2, "page_size": 10},
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
        "selected_count": 80,
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
