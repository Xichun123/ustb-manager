import logging

import httpx
import pytest
from fastapi.testclient import TestClient
from ustb_sso._exceptions import APIError

from app.api import auth
from app.main import app
from app.services import auth_service
from app.services import session_store as session_store_module
from app.services.session_store import AuthState, SessionStore


SECRET_UPSTREAM_DETAIL = "SECRET_UPSTREAM_DETAIL"


class CapturingSessionStore(SessionStore):
    def __init__(self):
        super().__init__()
        self.created_session_id = None
        self.created_session = None

    def create(self):
        session_id, session = super().create()
        self.created_session_id = session_id
        self.created_session = session
        return session_id, session


def test_qr_init_hides_upstream_error_and_removes_the_new_session(monkeypatch):
    session_store = CapturingSessionStore()
    monkeypatch.setattr(auth, "store", session_store)

    async def fail_qr_init(session):
        raise RuntimeError(SECRET_UPSTREAM_DETAIL)

    monkeypatch.setattr(auth.auth_service, "init_qr_auth", fail_qr_init)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/auth/qr/init")

    assert response.status_code == 502
    assert response.json() == {"detail": "二维码登录初始化失败，请稍后重试"}
    assert SECRET_UPSTREAM_DETAIL not in response.text
    assert session_store.get(session_store.created_session_id) is None
    assert session_store.created_session.client.is_closed


def test_sms_init_hides_upstream_error_and_removes_the_new_session(monkeypatch):
    session_store = CapturingSessionStore()
    monkeypatch.setattr(auth, "store", session_store)

    async def fail_sms_init(session):
        raise RuntimeError(SECRET_UPSTREAM_DETAIL)

    monkeypatch.setattr(auth.auth_service, "init_sms_auth", fail_sms_init)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/auth/sms/init")

    assert response.status_code == 502
    assert response.json() == {"detail": "短信登录初始化失败，请稍后重试"}
    assert SECRET_UPSTREAM_DETAIL not in response.text
    assert session_store.get(session_store.created_session_id) is None
    assert session_store.created_session.client.is_closed


def test_sms_send_masks_upstream_rate_limit_detail(monkeypatch):
    session_store = CapturingSessionStore()
    monkeypatch.setattr(auth, "store", session_store)
    session_id, session = session_store.create()
    session.state = AuthState.SMS_READY
    monkeypatch.setattr(auth.sms_rate_limiter, "check", lambda key: None)

    async def fail_sms_send(session, phone):
        raise APIError(f"201 发送间隔过短 {SECRET_UPSTREAM_DETAIL}")

    monkeypatch.setattr(auth.auth_service, "send_sms", fail_sms_send)

    with TestClient(app, raise_server_exceptions=False) as client:
        client.cookies.set("ustb_sid", session_id)
        response = client.post("/api/auth/sms/send", json={"phone": "13800138000"})

    assert response.status_code == 429
    assert response.json() == {"detail": "短信发送过于频繁，请稍后重试"}
    assert SECRET_UPSTREAM_DETAIL not in response.text


@pytest.mark.parametrize("exception_type", [APIError, RuntimeError])
def test_sms_send_hides_non_rate_limit_failures(monkeypatch, exception_type):
    session_store = CapturingSessionStore()
    monkeypatch.setattr(auth, "store", session_store)
    session_id, session = session_store.create()
    session.state = AuthState.SMS_READY
    monkeypatch.setattr(auth.sms_rate_limiter, "check", lambda key: None)

    async def fail_sms_send(session, phone):
        raise exception_type(SECRET_UPSTREAM_DETAIL)

    monkeypatch.setattr(auth.auth_service, "send_sms", fail_sms_send)

    with TestClient(app, raise_server_exceptions=False) as client:
        client.cookies.set("ustb_sid", session_id)
        response = client.post("/api/auth/sms/send", json={"phone": "13800138000"})

    assert response.status_code == 502
    assert response.json() == {"detail": "短信服务暂时不可用，请稍后重试"}
    assert SECRET_UPSTREAM_DETAIL not in response.text


@pytest.mark.parametrize("exception_type", [APIError, ValueError])
def test_sms_verify_hides_invalid_login_detail(monkeypatch, exception_type):
    session_store = CapturingSessionStore()
    monkeypatch.setattr(auth, "store", session_store)
    session_id, session = session_store.create()
    session.state = AuthState.SMS_SENT

    async def fail_sms_verify(session, phone, code):
        raise exception_type(SECRET_UPSTREAM_DETAIL)

    monkeypatch.setattr(auth.auth_service, "verify_sms", fail_sms_verify)

    with TestClient(app, raise_server_exceptions=False) as client:
        client.cookies.set("ustb_sid", session_id)
        response = client.post(
            "/api/auth/sms/verify",
            json={"phone": "13800138000", "code": "123456"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "验证码无效或登录状态已失效"}
    assert SECRET_UPSTREAM_DETAIL not in response.text


def test_sms_verify_hides_unexpected_failure_and_logs_only_the_exception_type(monkeypatch, caplog):
    session_store = CapturingSessionStore()
    monkeypatch.setattr(auth, "store", session_store)
    session_id, session = session_store.create()
    session.state = AuthState.SMS_SENT

    async def fail_sms_verify(session, phone, code):
        raise RuntimeError(SECRET_UPSTREAM_DETAIL)

    monkeypatch.setattr(auth.auth_service, "verify_sms", fail_sms_verify)
    caplog.set_level(logging.ERROR, logger=auth.__name__)

    with TestClient(app, raise_server_exceptions=False) as client:
        client.cookies.set("ustb_sid", session_id)
        response = client.post(
            "/api/auth/sms/verify",
            json={"phone": "13800138000", "code": "123456"},
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "短信登录完成失败，请稍后重试"}
    assert SECRET_UPSTREAM_DETAIL not in response.text
    assert SECRET_UPSTREAM_DETAIL not in caplog.text
    assert "RuntimeError" in caplog.text


def test_cookie_login_preserves_invalid_cookie_401(monkeypatch):
    session_store = CapturingSessionStore()
    monkeypatch.setattr(auth, "store", session_store)

    def handler(request):
        assert request.url.path == "/UserManager/queryxsxx"
        return httpx.Response(200, json={})

    original_create = session_store.create

    def create_with_mock_upstream():
        session_id, session = original_create()
        session.client.close()
        session.client = httpx.Client(transport=httpx.MockTransport(handler))
        return session_id, session

    monkeypatch.setattr(session_store, "create", create_with_mock_upstream)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/auth/cookie/login", json={"cookies": "SESSION=value"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Cookie无效或已过期"}


def test_cookie_login_hides_upstream_http_failure_detail(monkeypatch):
    session_store = CapturingSessionStore()
    monkeypatch.setattr(auth, "store", session_store)

    def handler(request):
        raise httpx.ConnectError(
            f"{SECRET_UPSTREAM_DETAIL} https://private.example/?cookie=TOP_SECRET_COOKIE",
            request=request,
        )

    original_create = session_store.create

    def create_with_mock_upstream():
        session_id, session = original_create()
        session.client.close()
        session.client = httpx.Client(transport=httpx.MockTransport(handler))
        return session_id, session

    monkeypatch.setattr(session_store, "create", create_with_mock_upstream)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/auth/cookie/login", json={"cookies": "SESSION=value"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Cookie验证失败，请重新登录"}
    assert SECRET_UPSTREAM_DETAIL not in response.text
    assert "TOP_SECRET_COOKIE" not in response.text


def test_cookie_login_rejects_malformed_input_without_upstream_detail(monkeypatch):
    session_store = CapturingSessionStore()
    monkeypatch.setattr(auth, "store", session_store)

    def handler(request):
        raise RuntimeError(SECRET_UPSTREAM_DETAIL)

    original_create = session_store.create

    def create_with_mock_upstream():
        session_id, session = original_create()
        session.client.close()
        session.client = httpx.Client(transport=httpx.MockTransport(handler))
        return session_id, session

    monkeypatch.setattr(session_store, "create", create_with_mock_upstream)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/auth/cookie/login",
            json={"cookies": f"malformed-{SECRET_UPSTREAM_DETAIL}"},
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Cookie格式不正确"}
    assert SECRET_UPSTREAM_DETAIL not in response.text


def test_cookie_login_hides_unexpected_failure_and_logs_only_the_exception_type(
    monkeypatch, caplog
):
    session_store = CapturingSessionStore()
    monkeypatch.setattr(auth, "store", session_store)

    def handler(request):
        raise RuntimeError(f"{SECRET_UPSTREAM_DETAIL} TOP_SECRET_COOKIE")

    original_create = session_store.create

    def create_with_mock_upstream():
        session_id, session = original_create()
        session.client.close()
        session.client = httpx.Client(transport=httpx.MockTransport(handler))
        return session_id, session

    monkeypatch.setattr(session_store, "create", create_with_mock_upstream)
    caplog.set_level(logging.ERROR, logger=auth.__name__)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/auth/cookie/login", json={"cookies": "SESSION=value"})

    assert response.status_code == 502
    assert response.json() == {"detail": "Cookie登录失败，请稍后重试"}
    assert SECRET_UPSTREAM_DETAIL not in response.text
    assert "TOP_SECRET_COOKIE" not in response.text
    assert SECRET_UPSTREAM_DETAIL not in caplog.text
    assert "TOP_SECRET_COOKIE" not in caplog.text
    assert "RuntimeError" in caplog.text


def test_qr_poll_hides_session_error_detail(monkeypatch):
    session_store = CapturingSessionStore()
    monkeypatch.setattr(auth, "store", session_store)
    session_id, session = session_store.create()
    session.last_error = SECRET_UPSTREAM_DETAIL

    with TestClient(app, raise_server_exceptions=False) as client:
        client.cookies.set("ustb_sid", session_id)
        response = client.get("/api/auth/qr/poll")

    assert response.status_code == 200
    assert response.json() == {"status": "error", "message": "二维码登录失败，请稍后重试"}
    assert SECRET_UPSTREAM_DETAIL not in response.text


def test_qr_complete_does_not_log_session_token_or_student_id(monkeypatch, caplog):
    session_store = CapturingSessionStore()
    monkeypatch.setattr(auth, "store", session_store)
    tokens = iter(["SESSION_TOKEN_SECRET", "ROTATED_SESSION_TOKEN"])
    monkeypatch.setattr(session_store_module.secrets, "token_urlsafe", lambda size: next(tokens))
    session_id, session = session_store.create()
    session.state = AuthState.ACTIVE
    session.authenticated = True
    session.student_id = "STUDENT_ID_SECRET"
    caplog.set_level(logging.INFO, logger=auth.__name__)

    with TestClient(app, raise_server_exceptions=False) as client:
        client.cookies.set("ustb_sid", session_id)
        response = client.post("/api/auth/qr/complete")

    assert response.status_code == 200
    assert "SESSION_TOKEN_SECRET" not in caplog.text
    assert "STUDENT_ID_SECRET" not in caplog.text


def test_qr_status_does_not_log_student_id_or_pass_code(monkeypatch, caplog):
    session_store = CapturingSessionStore()
    monkeypatch.setattr(auth, "store", session_store)
    session_id, session = session_store.create()
    session.client.close()

    class CompletedQrProcedure:
        def wait_for_pass_code(self):
            return "QR_PASS_CODE_SECRET"

        def complete_auth(self, pass_code):
            assert pass_code == "QR_PASS_CODE_SECRET"

    class StudentInfoResponse:
        status_code = 200
        url = "https://byyt.ustb.edu.cn/UserManager/queryxsxx"

        def raise_for_status(self):
            pass

        def json(self):
            return {"XH": "STUDENT_ID_SECRET"}

    class StudentInfoClient:
        class Cookies:
            jar = ()

        cookies = Cookies()

        def post(self, url, data):
            assert url == "https://byyt.ustb.edu.cn/UserManager/queryxsxx"
            assert data == ""
            return StudentInfoResponse()

        def close(self):
            pass

    session.client = StudentInfoClient()
    session.state = AuthState.QR_READY
    session.procedure = CompletedQrProcedure()
    caplog.set_level(logging.INFO, logger=auth_service.__name__)

    with TestClient(app, raise_server_exceptions=False) as client:
        client.cookies.set("ustb_sid", session_id)
        response = client.get("/api/auth/qr/status")

    assert response.status_code == 200
    assert "success" in response.text
    assert "STUDENT_ID_SECRET" not in caplog.text
    assert "QR_PASS_CODE_SECRET" not in caplog.text


def test_qr_status_hides_completion_failure_from_logs(monkeypatch, caplog):
    session_store = CapturingSessionStore()
    monkeypatch.setattr(auth, "store", session_store)
    session_id, session = session_store.create()

    class FailingQrProcedure:
        def wait_for_pass_code(self):
            return "pass-code"

        def complete_auth(self, pass_code):
            raise RuntimeError(SECRET_UPSTREAM_DETAIL)

    session.state = AuthState.QR_READY
    session.procedure = FailingQrProcedure()
    caplog.set_level(logging.ERROR, logger=auth_service.__name__)

    with TestClient(app, raise_server_exceptions=False) as client:
        client.cookies.set("ustb_sid", session_id)
        response = client.get("/api/auth/qr/status")

    assert response.status_code == 200
    assert "Auth completion failed" in response.text
    assert SECRET_UPSTREAM_DETAIL not in response.text
    assert SECRET_UPSTREAM_DETAIL not in caplog.text
    assert "RuntimeError" in caplog.text
