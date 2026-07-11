from fastapi.testclient import TestClient

from app.dependencies import get_authenticated_session
from app.main import app


def test_missing_session_uses_auth_required_error_contract():
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/me")

    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "AUTH_REQUIRED"
    assert error["retryable"] is False
    assert error["request_id"]
    assert response.headers["X-Request-ID"] == error["request_id"]


def test_validation_uses_stable_error_contract():
    app.dependency_overrides[get_authenticated_session] = lambda: object()
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/course-selection/courses?semester=4")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    error = response.json()["error"]
    assert error == {
        "code": "VALIDATION_ERROR",
        "message": "请求参数无效",
        "retryable": False,
        "request_id": error["request_id"],
    }
    assert error["request_id"]
