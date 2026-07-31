import asyncio
import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app import dependencies
from app.api import auth
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


def test_upstream_expiration_invalidates_the_project_session(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/UserManager/queryxsxx"
        return httpx.Response(401, json={"detail": "unauthorized"})

    session_store = SessionStore()
    session_id, session = session_store.create()
    session.client.close()
    session.client = httpx.Client(transport=httpx.MockTransport(handler))
    session.state = AuthState.ACTIVE
    session.authenticated = True
    monkeypatch.setattr(dependencies, "store", session_store)
    monkeypatch.setattr(auth, "store", session_store)

    async def init_qr(_session):
        return b"qr-image"

    monkeypatch.setattr(auth.auth_service, "init_qr_auth", init_qr)
    headers = {"Authorization": f"Bearer {session_id}"}

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            expired_response = client.get("/api/me", headers=headers)
            status_response = client.get("/api/auth/status", headers=headers)
            qr_response = client.post("/api/auth/qr/init", headers=headers)
    finally:
        session_store.stop_cleanup()

    assert expired_response.status_code == 401
    assert expired_response.json()["error"]["code"] == "UPSTREAM_SESSION_EXPIRED"
    assert status_response.status_code == 200
    assert status_response.json() == {"authenticated": False, "state": None}
    assert session.state == AuthState.EXPIRED
    assert session.authenticated is False
    assert qr_response.status_code == 200
