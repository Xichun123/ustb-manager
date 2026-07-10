import asyncio
import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.dependencies import get_authenticated_session
from app.main import app
from app.services.session_store import AuthState, Session

FIXTURES = Path(__file__).parent / "fixtures"


def test_academic_progress_normalizes_counts_credits_and_rank():
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
                "/api/academic/progress",
                params={"term": "2025-2026-2"},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == {
        "cutoff_term": "2025-2026-2",
        "required_courses": 40,
        "completed_courses": 30,
        "remaining_courses": 10,
        "required_credits": 120.0,
        "completed_credits": 90.0,
        "remaining_credits": 30.0,
        "credit_score": 3.5,
        "major_rank": 12,
        "major_student_count": 100,
    }


def test_academic_progress_modules_normalize_the_requirement_tree():
    profile_fixture = json.loads((FIXTURES / "student_academic_profile.json").read_text())
    modules_fixture = json.loads((FIXTURES / "progress_modules.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/cjgl/cjzhtjcx/cjcx/getXs":
            return httpx.Response(200, json=profile_fixture)
        assert request.url.path == "/cjgl/cjzhtjcx/cjcx/queryMkyq"
        assert json.loads(request.content) == {
            "xjid": "student-internal-1",
            "zyfxdm": "0",
            "fah": "plan-1",
            "pylx": "1",
        }
        return httpx.Response(200, json=modules_fixture)

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
            response = client.get("/api/academic/progress/modules")
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == {
        "is_available": True,
        "items": [
            {
                "id": "TREE_0",
                "parent_id": "",
                "name": "信息管理与信息系统",
                "name_en": "Information Management",
                "module_type": "2",
                "course_category_code": "",
                "course_nature_code": "",
                "required_groups": None,
                "completed_groups": None,
                "required_courses": None,
                "completed_courses": None,
                "required_hours": None,
                "completed_hours": None,
                "required_credits": 120.0,
                "completed_credits": 90.0,
                "passed": False,
                "is_required": None,
                "remark": "",
                "children": [
                    {
                        "id": "module-1",
                        "parent_id": "TREE_0",
                        "name": "专业核心",
                        "name_en": "Major Core",
                        "module_type": "0",
                        "course_category_code": "MAJOR_CORE",
                        "course_nature_code": "REQUIRED",
                        "required_groups": 1,
                        "completed_groups": 1,
                        "required_courses": 8,
                        "completed_courses": 5,
                        "required_hours": 400.0,
                        "completed_hours": 240.0,
                        "required_credits": 25.0,
                        "completed_credits": 15.0,
                        "passed": False,
                        "is_required": True,
                        "remark": "完成培养方案规定课程",
                        "children": [],
                    }
                ],
            }
        ],
    }


def test_academic_progress_courses_normalize_categories_and_course_details():
    profile_fixture = json.loads((FIXTURES / "student_academic_profile.json").read_text())
    courses_fixture = json.loads((FIXTURES / "progress_courses.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/cjgl/cjzhtjcx/cjcx/getXs":
            return httpx.Response(200, json=profile_fixture)
        expected = {
            "current": 1,
            "pageSize": 500,
            "xjid": "student-internal-1",
            "zyfxdm": "0",
            "pylx": "1",
            "fah": "plan-1",
        }
        assert json.loads(request.content) == expected
        if request.url.path == "/cjgl/cjzhtjcx/cjcx/querysfxsxflbyq":
            return httpx.Response(200, json=1)
        assert request.url.path == "/cjgl/cjzhtjcx/cjcx/queryXflbyq1"
        return httpx.Response(200, json=courses_fixture)

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
            response = client.get("/api/academic/progress/courses")
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == {
        "is_available": True,
        "categories": [
            {
                "code": "GENERAL",
                "name": "通识课程",
                "name_en": "",
                "course_nature_code": "",
                "course_nature": "",
                "required_credits": 69.0,
                "completed_credits": 65.0,
                "remaining_credits": 4.0,
                "convertible_credits": 0.0,
                "converted_credits": 0.0,
                "remark": "通识课程",
            }
        ],
        "courses": [
            {
                "id": "course-1",
                "course_code": "CS101",
                "course_name": "程序设计",
                "course_name_en": "Programming",
                "term": "2024-2025-1",
                "credits": 3.0,
                "hours": 48.0,
                "score": "88",
                "passed": True,
                "counts_toward_requirement": True,
                "is_required": True,
                "course_nature_code": "01",
                "course_nature": "必修",
                "course_category_code": "GENERAL",
                "course_category": "通识课程",
                "college": "计算机与通信工程学院",
                "module_id": "module-1",
                "module_name": "专业核心",
                "major_direction_code": "0",
                "major_direction": "无方向",
            }
        ],
    }


def test_academic_progress_modules_treat_an_empty_tree_as_unavailable():
    profile_fixture = json.loads((FIXTURES / "student_academic_profile.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/cjgl/cjzhtjcx/cjcx/getXs":
            return httpx.Response(200, json=profile_fixture)
        assert request.url.path == "/cjgl/cjzhtjcx/cjcx/queryMkyq"
        return httpx.Response(200, json={"code": 200, "content": []})

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
            response = client.get("/api/academic/progress/modules")
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == {"is_available": False, "items": []}


def test_academic_progress_courses_respect_the_upstream_visibility_flag():
    profile_fixture = json.loads((FIXTURES / "student_academic_profile.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/cjgl/cjzhtjcx/cjcx/getXs":
            return httpx.Response(200, json=profile_fixture)
        assert request.url.path == "/cjgl/cjzhtjcx/cjcx/querysfxsxflbyq"
        return httpx.Response(200, json=0)

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
            response = client.get("/api/academic/progress/courses")
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == {
        "is_available": False,
        "categories": [],
        "courses": [],
    }
