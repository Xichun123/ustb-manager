import asyncio
import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app import dependencies
from app.dependencies import get_authenticated_session
from app.main import app
from app.services.session_store import AuthState, Session, SessionStore

FIXTURES = Path(__file__).parent / "fixtures"


def test_me_combines_student_profile_and_normalized_roles():
    student_fixture = json.loads((FIXTURES / "profile_student.json").read_text())
    user_fixture = json.loads((FIXTURES / "profile_user.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.content == b""
        if request.url.path == "/UserManager/queryxsxx":
            return httpx.Response(200, json=student_fixture)
        assert request.url.path == "/user/me"
        return httpx.Response(200, json=user_fixture)

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
            response = client.get("/api/me")
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == {
        "student_id": "U000000000",
        "name": "测试学生",
        "name_en": "Test Student",
        "college": "计算机与通信工程学院",
        "college_en": "School of Computer and Communication Engineering",
        "major": "计算机科学与技术",
        "major_en": "Computer Science and Technology",
        "class_name": "计科2401",
        "class_name_en": "CS 2401",
        "grade": "2024级",
        "grade_en": "Grade 2024",
        "email": "student@example.edu",
        "phone": "13800000000",
        "photo_url": "/files/avatar/student-internal-1",
        "training_type": "1",
        "roles": [
            {
                "code": "01",
                "name": "学生",
                "name_en": "Student",
            }
        ],
    }


def test_me_accepts_the_same_session_as_a_bearer_token(monkeypatch):
    student_fixture = json.loads((FIXTURES / "profile_student.json").read_text())
    user_fixture = json.loads((FIXTURES / "profile_user.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/UserManager/queryxsxx":
            return httpx.Response(200, json=student_fixture)
        return httpx.Response(200, json=user_fixture)

    session_store = SessionStore()
    session_id, session = session_store.create()
    session.client.close()
    session.client = httpx.Client(transport=httpx.MockTransport(handler))
    session.state = AuthState.ACTIVE
    session.authenticated = True
    monkeypatch.setattr(dependencies, "store", session_store)

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(
                "/api/me",
                headers={"Authorization": f"Bearer {session_id}"},
            )
    finally:
        session_store.stop_cleanup()

    assert response.status_code == 200
    assert response.json()["student_id"] == "U000000000"
