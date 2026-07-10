import asyncio
import json
from pathlib import Path
from urllib.parse import parse_qs

import httpx
from fastapi.testclient import TestClient

from app.dependencies import get_authenticated_session
from app.main import app
from app.services.session_store import AuthState, Session

FIXTURES = Path(__file__).parent / "fixtures"


def test_academic_context_distinguishes_administrative_and_summer_terms():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/component/querydangqianxnxq":
            return httpx.Response(
                200,
                json={
                    "XN": "2025-2026",
                    "XQ": "2",
                    "XNXQ": "2025-2026-2",
                },
            )
        assert request.url.path == "/component/getXnxqByRq"
        assert request.url.params["rq"] == "2026-07-10"
        return httpx.Response(
            200,
            json={
                "code": 200,
                "content": {
                    "rqxnxq": {
                        "xn": "2025-2026",
                        "xq": "3",
                        "xqmc_en": "Summer",
                        "zc": "1",
                    }
                },
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
                "/api/academic/context",
                params={"date": "2026-07-10"},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == {
        "date": "2026-07-10",
        "administrative_term": {
            "year": "2025-2026",
            "semester": "2",
            "code": "2025-2026-2",
        },
        "teaching_term": {
            "year": "2025-2026",
            "semester": "3",
            "code": "2025-2026-3",
        },
        "week": 1,
        "is_in_teaching_week": True,
    }


def test_legacy_current_term_route_defaults_to_the_date_aware_teaching_term():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/component/querydangqianxnxq":
            return httpx.Response(
                200,
                json={
                    "XN": "2025-2026",
                    "XQ": "2",
                    "XNXQ": "2025-2026-2",
                },
            )
        assert request.url.path == "/component/getXnxqByRq"
        assert request.url.params["rq"] == "2026-07-10"
        return httpx.Response(
            200,
            json={
                "code": 200,
                "content": {
                    "rqxnxq": {
                        "xn": "2025-2026",
                        "xq": "3",
                        "zc": "1",
                    }
                },
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
                "/api/schedule/current-term",
                params={"date": "2026-07-10"},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == {
        "XN": "2025-2026",
        "XQ": "3",
        "XNXQ": "2025-2026-3",
        "ZC": 1,
    }


def test_academic_terms_unwrap_and_normalize_the_current_term_list():
    fixture = json.loads((FIXTURES / "academic_terms.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/component/queryXnxq"
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
            response = client.get("/api/academic/terms")
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == [
        {
            "year": "2025-2026",
            "semester": "3",
            "code": "2025-2026-3",
            "name": "夏季学期",
            "name_en": "Summer",
            "is_current": True,
        },
        {
            "year": "2025-2026",
            "semester": "2",
            "code": "2025-2026-2",
            "name": "第二学期",
            "name_en": "Spring",
            "is_current": False,
        },
    ]


def test_academic_warnings_are_read_only_and_split_earned_course_status():
    fixture = json.loads((FIXTURES / "academic_warning.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/xjgl/xyyj/queryxsXxcj_xs"
        assert parse_qs(request.content.decode()) == {
            "xn": ["2025-2026"],
            "xq": ["2"],
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
            response = client.get(
                "/api/academic/warnings",
                params={"term": "2025-2026-2"},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == {
        "term": "2025-2026-2",
        "has_warning": True,
        "is_published": True,
        "is_acknowledged": False,
        "acknowledged_at": None,
        "counted_credits": 12.5,
        "earned_courses": [
            {
                "course_code": "CS101",
                "course_name": "程序设计",
                "hours": 48.0,
                "credits": 3.0,
                "term": "2025-2026-2",
                "score": "78",
                "course_category": "专业基础课",
                "course_nature": "必修",
                "exam_attempt": "正考",
            }
        ],
        "unearned_courses": [
            {
                "course_code": "MATH001",
                "course_name": "高等数学",
                "hours": 64.0,
                "credits": 4.0,
                "term": "2025-2026-2",
                "score": "55",
                "course_category": "公共基础课",
                "course_nature": "必修",
                "exam_attempt": "正考",
            }
        ],
    }


def test_academic_calendar_uses_role_context_and_normalizes_month_dates():
    fixture = json.loads((FIXTURES / "calendar_month.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/Xiaoli/queryMonthList"
        assert request.headers["RoleCode"] == "01"
        assert parse_qs(request.content.decode()) == {
            "xn": ["2025-2026"],
            "xq": ["3"],
            "yf": ["7"],
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
            response = client.get(
                "/api/academic/calendar",
                params={"term": "2025-2026-3", "month": 7},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == {
        "term": "2025-2026-3",
        "month": {
            "year": 2026,
            "month": 7,
            "label": "July 2026",
            "days_in_month": 31,
        },
        "dates": [
            {"date": "2026-07-01", "week": 1},
            {"date": "2026-07-02", "week": 1},
        ],
    }
