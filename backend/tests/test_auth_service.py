import asyncio

import httpx
import pytest

from app.byyt.errors import BYYTUnavailable
from app.services import auth_service
from app.services.session_store import AuthState, Session


class RecordingStore:
    def __init__(self):
        self.persist_calls = []

    def persist(self, session_id, student_id, cookies):
        self.persist_calls.append((session_id, student_id, cookies))


class CompletedQrProcedure:
    def __init__(self):
        self.wait_calls = 0
        self.complete_calls = 0

    def wait_for_pass_code(self):
        self.wait_calls += 1
        return "pass-code"

    def complete_auth(self, pass_code):
        assert pass_code == "pass-code"
        self.complete_calls += 1


class CompletedSmsProcedure:
    def __init__(self):
        self.submit_calls = 0
        self.complete_calls = 0

    def submit_sms_code(self, phone, code):
        assert phone == "13800138000"
        assert code == "123456"
        self.submit_calls += 1
        return "sms-token"

    def complete_sms_auth(self, token):
        assert token == "sms-token"
        self.complete_calls += 1


def _response_handler(responses, requests):
    remaining = iter(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        response = next(remaining)
        if isinstance(response, Exception):
            raise response
        return response

    return handler


def _make_session(flow, responses):
    requests = []
    client = httpx.Client(
        transport=httpx.MockTransport(_response_handler(responses, requests)),
        follow_redirects=True,
    )
    client.cookies.set("SESSION", "cookie-secret", domain=".ustb.edu.cn")
    if flow == "sms":
        procedure = CompletedSmsProcedure()
        state = AuthState.SMS_SENT
    else:
        procedure = CompletedQrProcedure()
        state = AuthState.QR_READY
    session = Session(
        client=client,
        state=state,
        procedure=procedure,
        session_id="test-session",
    )
    return session, procedure, requests


async def _run_flow(flow, session, monkeypatch):
    if flow == "background":
        tasks = []
        real_create_task = asyncio.create_task

        def capture_task(coroutine):
            task = real_create_task(coroutine)
            tasks.append(task)
            return task

        monkeypatch.setattr(auth_service.asyncio, "create_task", capture_task)
        await auth_service.start_qr_background_monitor(session)
        await auth_service.start_qr_background_monitor(session)
        await asyncio.gather(*tasks)
        return []
    if flow == "sse":
        return [event async for event in auth_service.poll_qr_status(session)]
    await auth_service.verify_sms(session, "13800138000", "123456")
    return []


@pytest.mark.asyncio
@pytest.mark.parametrize("flow", ["background", "sse", "sms"])
async def test_auth_completion_activates_and_persists_each_login_flow(monkeypatch, flow):
    session, procedure, requests = _make_session(
        flow,
        [httpx.Response(200, json={"content": {"XH": "test-student", "XM": "Test"}})],
    )
    recording_store = RecordingStore()
    monkeypatch.setattr(auth_service, "store", recording_store)

    try:
        events = await _run_flow(flow, session, monkeypatch)
    finally:
        session.client.close()

    assert session.state == AuthState.ACTIVE
    assert session.authenticated is True
    assert session.student_id == "test-student"
    assert len(requests) == 1
    assert requests[0].url.path == "/UserManager/queryxsxx"
    assert recording_store.persist_calls == [
        ("test-session", "test-student", {"SESSION": "cookie-secret"})
    ]
    if flow == "background":
        assert session.qr_monitor_started is False
        assert procedure.wait_calls == 1
        assert procedure.complete_calls == 1
    elif flow == "sse":
        assert session.qr_monitor_started is False
        assert events == [
            {"status": "pending"},
            {"status": "scanned"},
            {"status": "success"},
        ]
        assert procedure.wait_calls == 1
        assert procedure.complete_calls == 1
    else:
        assert procedure.submit_calls == 1
        assert procedure.complete_calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("flow", ["background", "sse", "sms"])
async def test_auth_completion_retries_temporary_identity_failures_without_blocking(
    monkeypatch, flow
):
    session, _, requests = _make_session(
        flow,
        [
            httpx.Response(302, headers={"location": "/authentication/login"}),
            httpx.Response(503, text="not ready"),
            httpx.Response(200, json={"XH": "test-student"}),
        ],
    )
    recording_store = RecordingStore()
    sleep_delays = []

    async def fake_sleep(delay):
        sleep_delays.append(delay)

    monkeypatch.setattr(auth_service, "store", recording_store)
    monkeypatch.setattr(auth_service.asyncio, "sleep", fake_sleep)

    try:
        events = await _run_flow(flow, session, monkeypatch)
    finally:
        session.client.close()

    assert len(requests) == 3
    assert sleep_delays == [1, 1]
    assert session.state == AuthState.ACTIVE
    assert session.authenticated is True
    assert len(recording_store.persist_calls) == 1
    if flow == "sse":
        assert events[-1] == {"status": "success"}


@pytest.mark.asyncio
@pytest.mark.parametrize("flow", ["background", "sse", "sms"])
async def test_auth_completion_stops_after_three_identity_failures(monkeypatch, flow):
    session, _, requests = _make_session(
        flow,
        [
            httpx.Response(503, text="not ready"),
            httpx.Response(503, text="not ready"),
            httpx.Response(503, text="not ready"),
        ],
    )
    recording_store = RecordingStore()
    sleep_delays = []

    async def fake_sleep(delay):
        sleep_delays.append(delay)

    monkeypatch.setattr(auth_service, "store", recording_store)
    monkeypatch.setattr(auth_service.asyncio, "sleep", fake_sleep)

    try:
        if flow == "sms":
            with pytest.raises(BYYTUnavailable):
                await _run_flow(flow, session, monkeypatch)
            events = []
        else:
            events = await _run_flow(flow, session, monkeypatch)
    finally:
        session.client.close()

    assert len(requests) == 3
    assert sleep_delays == [1, 1]
    assert session.authenticated is False
    assert recording_store.persist_calls == []
    if flow == "background":
        assert session.qr_monitor_started is False
        assert session.last_error == "QR login failed"
    elif flow == "sse":
        assert session.qr_monitor_started is False
        assert events[-1] == {"status": "error", "message": "Auth completion failed"}


@pytest.mark.asyncio
async def test_qr_sse_does_not_duplicate_an_active_background_monitor(monkeypatch):
    session, procedure, _ = _make_session(
        "background",
        [httpx.Response(200, json={"XH": "test-student"})],
    )
    recording_store = RecordingStore()
    background_coroutines = []

    def capture_coroutine(coroutine):
        background_coroutines.append(coroutine)
        return None

    monkeypatch.setattr(auth_service, "store", recording_store)
    monkeypatch.setattr(auth_service.asyncio, "create_task", capture_coroutine)

    try:
        await auth_service.start_qr_background_monitor(session)
        events = [event async for event in auth_service.poll_qr_status(session)]
        await background_coroutines[0]
    finally:
        session.client.close()

    assert events == [{"status": "error", "message": "Invalid state"}]
    assert procedure.wait_calls == 1
    assert procedure.complete_calls == 1
    assert len(recording_store.persist_calls) == 1
