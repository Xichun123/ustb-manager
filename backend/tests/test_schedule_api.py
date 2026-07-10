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


def test_schedule_query_uses_the_detailed_endpoint_and_normalizes_time_slots():
    fixture = json.loads((FIXTURES / "schedule_new_list.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/Xskbcx/queryXskbcxList"
        assert parse_qs(request.content.decode(), keep_blank_values=True) == {
            "sfmrdqxq": ["true"],
            "xn": ["2025-2026"],
            "xq": ["2"],
            "bs": ["2"],
            "xskb": ["1"],
            "bjkb": ["0"],
            "gwckb": ["0"],
            "tabs": ["1"],
            "sfxsgwc": ["1"],
            "sxbj": [""],
        }
        return httpx.Response(200, json=fixture)

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
            response = client.get("/api/schedule", params={"term": "2025-2026-2"})
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    body = response.json()
    assert body["term"] == "2025-2026-2"
    assert body["week"] is None
    assert body["dates"] == {}
    assert body["items"][0] == {
        "course_id": "schedule-1",
        "course_code": "CS101",
        "course_name": "程序设计",
        "course_name_en": "Programming",
        "teacher": "张老师",
        "weekday": 1,
        "start_period": 1,
        "end_period": 2,
        "weeks": [1, 2, 3, 4, 5, 6, 7, 8],
        "week_text": "1-8周",
        "location": "教学楼101",
        "campus": "校本部",
        "period_text": "第1-2节",
        "task_code": "",
    }
    assert len(body["items"]) == 3


def test_schedule_week_filters_courses_and_includes_dates():
    fixture = json.loads((FIXTURES / "schedule_new_list.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/Xskbcx/queryXskbcxList":
            return httpx.Response(200, json=fixture)
        assert request.url.path == "/component/queryRlZcSj"
        assert parse_qs(request.content.decode()) == {
            "xn": ["2025-2026"],
            "xq": ["2"],
            "djz": ["3"],
        }
        return httpx.Response(
            200,
            json={
                "code": 200,
                "content": [
                    {"xqj": "1", "rq": "2026-03-09"},
                    {"xqj": "2", "rq": "2026-03-10"},
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
    app.dependency_overrides[get_authenticated_session] = lambda: session

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(
                "/api/schedule",
                params={"term": "2025-2026-2", "week": 3},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    body = response.json()
    assert body["dates"] == {"1": "2026-03-09", "2": "2026-03-10"}
    assert [item["course_id"] for item in body["items"]] == ["schedule-1", "schedule-3"]


def test_legacy_full_schedule_route_also_uses_the_detailed_endpoint():
    fixture = json.loads((FIXTURES / "schedule_new_list.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/Xskbcx/queryXskbcxList"
        return httpx.Response(200, json=fixture)

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
                "/api/schedule/full",
                params={"xn": "2025-2026", "xq": "2"},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    first = response.json()["schedule"][0]
    assert first["key"] == "xq1_jc1"
    assert first["weekday"] == 1
    assert first["start_period"] == 1
    assert first["end_period"] == 2
    assert first["course_name"] == "程序设计"


def _get_legacy_schedule_route(path, handler, params=None):
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


def test_legacy_schedule_term_list_uses_the_byyt_boundary():
    fixture = json.loads((FIXTURES / "academic_terms.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/component/queryXnxq"
        assert request.content == b""
        return httpx.Response(200, json=fixture)

    response = _get_legacy_schedule_route("/api/schedule/term-list", handler)

    assert response.status_code == 200
    assert response.json()[0] == {
        "xn": "2025-2026",
        "xq": "3",
        "xnxq": "2025-2026-3",
        "xqmc": "夏季学期",
        "xqmc_en": "Summer",
        "sfdqxq": "1",
        "dm": "2025-20263",
        "mc": "2025-2026学年第3学期",
    }


def test_legacy_schedule_week_list_uses_the_byyt_boundary():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/component/queryzclist"
        assert parse_qs(request.content.decode()) == {
            "xn": ["2025-2026"],
            "xq": ["2"],
        }
        return httpx.Response(200, json=[{"ZC": 1}, {"ZC": 2}])

    response = _get_legacy_schedule_route(
        "/api/schedule/week-list",
        handler,
        params={"xn": "2025-2026", "xq": "2"},
    )

    assert response.status_code == 200
    assert response.json() == [{"ZC": 1}, {"ZC": 2}]


def test_legacy_schedule_exam_list_uses_the_byyt_boundary():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/component/queryKsxxByXs"
        return httpx.Response(
            200,
            json=[
                {
                    "KCDM": "CS101",
                    "KCMC": "程序设计",
                    "KSRQ": "2026-06-20",
                    "KSJTSJ": "09:00-11:00",
                    "JXCDMC": "101",
                }
            ],
        )

    response = _get_legacy_schedule_route("/api/schedule/exams", handler)

    assert response.status_code == 200
    assert response.json()[0]["course_code"] == "CS101"
    assert response.json()[0]["course_name"] == "程序设计"
    assert response.json()[0]["exam_date"] == "2026-06-20"
    assert response.json()[0]["room"] == "101"


def test_legacy_schedule_term_list_classifies_malformed_json():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b"not-json",
        )

    response = _get_legacy_schedule_route("/api/schedule/term-list", handler)

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_BAD_RESPONSE"
