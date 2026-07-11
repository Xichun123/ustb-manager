import asyncio
import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from urllib.parse import parse_qs

from app.cache import reference_data_cache
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
                "task_id": "task-1",
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
                "rank_total": 67,
            },
            {
                "id": "grade-2",
                "task_id": "task-2",
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
                "rank_total": None,
            },
        ],
        "page": 1,
        "page_size": 20,
        "total": 2,
    }


def test_grade_components_query_returns_normalized_breakdown():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/cjgl/grcjcx/seeFx"
        assert parse_qs(request.content.decode()) == {
            "rwid": ["task-1"],
            "cjid": ["grade-1"],
        }
        return httpx.Response(
            200,
            json=[
                {"FXMC": "平时成绩", "DF": "90", "MF": "100", "LJFXBZ": "30"},
                {"FXMC": "期末考试", "DF": "82", "MF": "100", "LJFXBZ": "70"},
            ],
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
                "/api/grades/grade-1/components",
                params={"task_id": "task-1"},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == [
        {"name": "平时成绩", "score": 90.0, "max_score": 100.0, "weight": 30.0},
        {"name": "期末考试", "score": 82.0, "max_score": 100.0, "weight": 70.0},
    ]


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


def _get_legacy_grades_route(path, handler):
    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(
        client=upstream,
        state=AuthState.ACTIVE,
        authenticated=True,
        student_id="test-student",
        lock=asyncio.Lock(),
    )
    app.dependency_overrides[get_authenticated_session] = lambda: session
    reference_data_cache.clear()
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            return client.get(path)
    finally:
        app.dependency_overrides.clear()
        reference_data_cache.clear()
        upstream.close()


def test_legacy_student_and_user_info_use_byyt_adapters():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path == "/UserManager/queryxsxx":
            return httpx.Response(200, json={"XH": "test-student", "XM": "Test"})
        assert request.url.path == "/user/me"
        return httpx.Response(200, json={"userId": "test-student", "role": []})

    student_response = _get_legacy_grades_route("/api/grades/student-info", handler)
    user_response = _get_legacy_grades_route("/api/grades/user-info", handler)

    assert student_response.status_code == 200
    assert student_response.json() == {"XH": "test-student", "XM": "Test"}
    assert user_response.status_code == 200
    assert user_response.json() == {"userId": "test-student", "role": []}
    assert requests == ["/UserManager/queryxsxx", "/user/me"]


def test_legacy_available_grade_terms_use_the_byyt_boundary():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/cjgl/cjzhtjcx/cjcx/queryqxnxq"
        return httpx.Response(200, json={"xnlist": ["2025-2026"], "xqlist": ["2"]})

    response = _get_legacy_grades_route("/api/grades/available-terms", handler)

    assert response.status_code == 200
    assert response.json() == {"xnlist": ["2025-2026"], "xqlist": ["2"]}


def test_legacy_student_plan_uses_byyt_progress_adapters():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path.endswith("/getXss"):
            return httpx.Response(200, json={"code": 200, "content": [{"fah": "plan-1"}]})
        if request.url.path.endswith("/queryGrjhKcList1"):
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "content": [
                        {
                            "kclbmc": "专业课",
                            "kcxzmc": "必修",
                            "xf": "3",
                            "kcdm": "CS1",
                        }
                    ],
                },
            )
        assert request.url.path.endswith("/queryXflbyq1")
        return httpx.Response(
            200,
            json={"xflbyqkc": [{"kcdm": "CS1", "xscj": "90", "xf": "3"}]},
        )

    response = _get_legacy_grades_route("/api/grades/student-plan", handler)

    assert response.status_code == 200
    assert response.json()[0]["kclb_list"] == [
        {
            "kclbmc": "专业课",
            "kcxzmc": "必修",
            "yqxdxf": 3.0,
            "wcxf": 3.0,
            "wwcxf": 0.0,
        }
    ]
    assert requests == [
        "/cjgl/cjzhtjcx/cjcx/getXss",
        "/xspyyjsfasq/queryGrjhKcList1",
        "/cjgl/cjzhtjcx/cjcx/queryXflbyq1",
    ]


def test_legacy_credit_completion_uses_byyt_progress_adapters():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/getXs"):
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "content": [
                        {
                            "fah": "plan-1",
                            "kclb_list": [{"dm": "A", "mc": "专业课"}],
                        }
                    ],
                },
            )
        assert request.url.path.endswith("/queryXflbyq1")
        return httpx.Response(
            200,
            json={
                "xflbyqkc": [
                    {
                        "kclbdm": "A",
                        "xf": "3",
                        "xs": "48",
                        "xscj": "90",
                        "kcdm": "CS1",
                        "kcmc": "程序设计",
                    }
                ]
            },
        )

    response = _get_legacy_grades_route("/api/grades/credit-completion-status", handler)

    assert response.status_code == 200
    category = response.json()["categories"][0]
    assert category["category_code"] == "A"
    assert category["category_name"] == "专业课"
    assert category["required_credits"] == 3.0
    assert category["completed_credits"] == 3.0
    assert category["remaining_credits"] == 0.0


def test_legacy_available_grade_terms_classify_malformed_json():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b"not-json",
        )

    response = _get_legacy_grades_route("/api/grades/available-terms", handler)

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_BAD_RESPONSE"
