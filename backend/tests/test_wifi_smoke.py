from fastapi.testclient import TestClient

from app.main import app


def test_wifi_standalone_status_remains_available_without_academic_login():
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/wifi/standalone-status")

    assert response.status_code == 200
    assert response.json() == {
        "logged_in": False,
        "student_id": None,
        "has_credential": False,
    }
