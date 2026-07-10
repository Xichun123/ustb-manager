import asyncio
import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.dependencies import get_authenticated_session
from app.main import app
from app.services.session_store import AuthState, Session

FIXTURES = Path(__file__).parent / "fixtures"


def test_grades_query_uses_the_current_json_endpoint_and_returns_stable_fields():
    fixture = json.loads((FIXTURES / "grades_new_list.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/cjgl/grcjcx/grcjcx"
        assert json.loads(request.content) == {
            "xn": "2025-2026",
            "xq": "2",
            "kcmc": None,
            "cxbj": "-1",
            "pylx": "1",
            "current": 1,
            "pageSize": 20,
            "xscjlb": None,
            "sffx": None,
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
                "/api/grades",
                params={"term": "2025-2026-2", "page": 1, "page_size": 20},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": "grade-1",
                "term": "2025-2026-2",
                "course_code": "MATH001",
                "course_name": "高等数学",
                "course_name_en": "Advanced Mathematics",
                "credit": 4.0,
                "hours": 64.0,
                "score": "92",
                "score_en": "92",
                "score_numeric": 92.0,
                "course_nature": "必修",
                "course_category": "专业基础课",
                "college": "理学院",
                "exam_attempt": "正考",
                "passed": True,
                "rank": 3,
            },
            {
                "id": "grade-2",
                "term": "2025-2026-2",
                "course_code": "PE001",
                "course_name": "体育",
                "course_name_en": "Physical Education",
                "credit": 1.0,
                "hours": 32.0,
                "score": "合格",
                "score_en": "Pass",
                "score_numeric": None,
                "course_nature": "必修",
                "course_category": "公共基础课",
                "college": "体育部",
                "exam_attempt": "正考",
                "passed": True,
                "rank": None,
            },
        ],
        "page": 1,
        "page_size": 20,
        "total": 2,
    }


def test_grade_summary_combines_official_and_estimated_values():
    grades_fixture = json.loads((FIXTURES / "grades_new_list.json").read_text())
    official_fixture = json.loads((FIXTURES / "grades_gpa_summary.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/cjgl/grcjcx/getgpa":
            assert request.method == "POST"
            assert request.content == b""
            return httpx.Response(200, json=official_fixture)

        assert request.url.path == "/cjgl/grcjcx/grcjcx"
        assert json.loads(request.content) == {
            "xn": None,
            "xq": None,
            "kcmc": None,
            "cxbj": "-1",
            "pylx": "1",
            "current": 1,
            "pageSize": 1000,
            "xscjlb": None,
            "sffx": None,
        }
        return httpx.Response(200, json=grades_fixture)

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
            response = client.get("/api/grades/summary")
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == {
        "official_gpa": 3.42,
        "estimated_gpa": 4.0,
        "earned_credits": 118.5,
        "passed_courses": 42,
        "failed_courses": 0,
    }


def test_legacy_grades_list_route_uses_the_current_endpoint():
    fixture = json.loads((FIXTURES / "grades_new_list.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/cjgl/grcjcx/grcjcx"
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
                "/api/grades/list",
                params={
                    "page_num": 1,
                    "page_size": 20,
                    "xn": "2025-2026",
                    "xq": "2",
                },
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["grades"][0] == {
        "xnxq": "2025-2026-2",
        "kcdm": "MATH001",
        "kcmc": "高等数学",
        "kcmc_en": "Advanced Mathematics",
        "xf": "4.0",
        "xs": "64.0",
        "xscj": "92",
        "zpcj": "92",
        "kcxzmc": "必修",
        "kclbmc": "专业基础课",
        "jsxm": "",
        "kkdw": "理学院",
        "bkcxbj": "正考",
    }
    assert body["gpa_stats"] == {
        "gpa": 4.0,
        "total_credits": 4.0,
        "passed_credits": 4.0,
        "failed_count": 0,
    }


def test_legacy_grades_term_list_unwraps_the_standard_envelope():
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
            response = client.get("/api/grades/term-list")
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json()[0] == {
        "year": "2025-2026",
        "semester": "3",
        "code": "2025-2026-3",
        "name": "夏季学期",
        "name_en": "Summer",
        "is_current": True,
    }


def test_required_course_status_uses_profile_ids_and_profile_year():
    profile_fixture = json.loads((FIXTURES / "student_academic_profile.json").read_text())
    status_fixture = json.loads((FIXTURES / "required_course_status.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/cjgl/cjzhtjcx/cjcx/getXs":
            assert json.loads(request.content) == {
                "xjidorxh": "U000000000",
                "pylx": "1",
            }
            return httpx.Response(200, json=profile_fixture)
        assert request.url.path == "/cjgl/cjzhtjcx/cjcx/queryBxkqk"
        assert json.loads(request.content) == {
            "xh": "U000000000",
            "pylx": "1",
            "nj": "2024",
            "jzxnxq": "2025-20262",
            "xjid": "student-internal-1",
            "zyfxdm": "0",
            "fah": "plan-1",
        }
        return httpx.Response(200, json=status_fixture)

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(
        client=upstream,
        state=AuthState.ACTIVE,
        authenticated=True,
        student_id="U000000000",
        lock=asyncio.Lock(),
    )
    app.dependency_overrides[get_authenticated_session] = lambda: session

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(
                "/api/grades/required-course-status",
                params={"jzxnxq": "2025-20262"},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == status_fixture["content"]
