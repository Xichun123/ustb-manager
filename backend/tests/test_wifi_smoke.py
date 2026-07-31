from fastapi.testclient import TestClient

from app.api import wifi
from app.main import app
from app.services.wifi_service import WifiSession, _extract_dashboard_user


def test_dashboard_user_json_allows_braces_inside_strings():
    html = """
    <script>
      (function (user) { window.user = user || {}; })({
        "userName": "U202400001",
        "leftMoney": 12.5,
        "useFlow": 1024,
        "leftFlow": 2048,
        "notice": "套餐说明包含 } 字符",
        "serviceDefault": {"defaultName": "学生套餐"}
      });
      window.afterUser = true;
    </script>
    """

    user = _extract_dashboard_user(html)

    assert user is not None
    assert user["userName"] == "U202400001"
    assert user["leftMoney"] == 12.5
    assert user["serviceDefault"]["defaultName"] == "学生套餐"


class FakeAsyncClient:
    def __init__(self):
        self.closed = False

    async def aclose(self):
        self.closed = True


def test_wifi_standalone_status_remains_available_without_academic_login():
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/wifi/standalone-status")

    assert response.status_code == 200
    assert response.json() == {
        "logged_in": False,
        "student_id": None,
        "has_credential": False,
    }


def test_wifi_flow_expires_stale_in_memory_session(monkeypatch):
    student_id = "U202400001"
    client = FakeAsyncClient()
    session = WifiSession(
        client=client,
        student_id=student_id,
        cookie="expired-cookie",
    )
    wifi.wifi_store.set(student_id, session)

    monkeypatch.setattr(wifi, "get_student_id", lambda _request: student_id)

    async def no_flow_data(*_args, **_kwargs):
        return None

    monkeypatch.setattr(wifi, "get_flow_info", no_flow_data)

    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.get("/api/wifi/flow")

        assert response.status_code == 401
        assert wifi.wifi_store.get(student_id) is None
        assert client.closed is True
    finally:
        wifi.wifi_store.delete(student_id)
