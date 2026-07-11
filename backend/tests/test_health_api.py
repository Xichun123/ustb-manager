from fastapi.testclient import TestClient

from app.main import app
from app.services.session_store import store


def test_requests_emit_sanitized_observability_fields(caplog):
    with caplog.at_level("INFO", logger="app.main"):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/health/live?student_id=must-not-log")

    request_id = response.headers["X-Request-ID"]
    assert "request_complete" in caplog.text
    assert f"request_id={request_id}" in caplog.text
    assert "path=/api/health/live" in caplog.text
    assert "status=200" in caplog.text
    assert "duration_ms=" in caplog.text
    assert "must-not-log" not in caplog.text


def test_liveness_does_not_depend_on_session_storage(monkeypatch):
    monkeypatch.setattr(store, "check_persistence", lambda: (_ for _ in ()).throw(RuntimeError()))

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_checks_session_storage(monkeypatch):
    checked = False

    def check():
        nonlocal checked
        checked = True

    monkeypatch.setattr(store, "check_persistence", check)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/health/ready")

    assert checked is True
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_is_unavailable_when_session_storage_fails(monkeypatch):
    def check():
        raise RuntimeError("sensitive storage detail")

    monkeypatch.setattr(store, "check_persistence", check)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert "sensitive" not in response.text
