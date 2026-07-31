import asyncio
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_authenticated_session
from app.main import app
from app.services.session_store import AuthState, Session


TERM_INFO = {
    "p_xn": "2026-2027",
    "p_xq": "1",
    "p_xnxq": "2026-20271",
    "p_dqxn": "2026-2027",
    "p_dqxq": "1",
    "p_dqxnxq": "2026-20271",
}


def test_multi_course_snatch_task_runs_until_every_course_succeeds():
    selected_ids = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(200, json=TERM_INFO)
        form = parse_qs(request.content.decode(), keep_blank_values=True)
        assert request.url.path == "/Xsxk/addGouwuche"
        selected_ids.append(form["p_id"][0])
        return httpx.Response(200, json={"jg": "1", "message": "选课成功"})

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(
        client=upstream,
        state=AuthState.ACTIVE,
        authenticated=True,
        lock=asyncio.Lock(),
    )
    app.dependency_overrides[get_authenticated_session] = lambda: session
    headers = {
        "Authorization": "Bearer test-session",
        "Idempotency-Key": "snatch-create-123",
    }
    payload = {
        "start_at": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
        "retry_interval_seconds": 0.1,
        "courses": [
            {
                "course_id": "task-1",
                "selection_id": "internal-task-1",
                "course_code": "CS1",
                "course_name": "课程一",
                "method": "zytzk-b-b",
            },
            {
                "course_id": "task-2",
                "selection_id": "internal-task-2",
                "course_code": "CS2",
                "course_name": "课程二",
                "method": "zytzk-b-b",
            },
        ],
    }

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            created = client.post("/api/course-selection/snatch-tasks", headers=headers, json=payload)
            assert created.status_code == 200, created.text
            task_id = created.json()["task_id"]

            deadline = time.monotonic() + 2
            body = created.json()
            while body["status"] not in {"completed", "completed_with_errors", "stopped", "failed"}:
                assert time.monotonic() < deadline, body
                time.sleep(0.02)
                response = client.get(f"/api/course-selection/snatch-tasks/{task_id}")
                assert response.status_code == 200, response.text
                body = response.json()
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert body["status"] == "completed"
    assert [(item["course_id"], item["status"], item["attempts"]) for item in body["items"]] == [
        ("task-1", "success", 1),
        ("task-2", "success", 1),
    ]
    assert selected_ids == ["internal-task-1", "internal-task-2"]


def test_scheduled_snatch_task_can_be_stopped_before_it_writes():
    upstream_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        upstream_requests.append(request.url.path)
        return httpx.Response(200, json=TERM_INFO)

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(
        client=upstream,
        state=AuthState.ACTIVE,
        authenticated=True,
        lock=asyncio.Lock(),
    )
    app.dependency_overrides[get_authenticated_session] = lambda: session
    headers = {
        "Authorization": "Bearer test-session",
        "Idempotency-Key": "snatch-stop-123",
    }
    payload = {
        "start_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "retry_interval_seconds": 1,
        "courses": [{"course_id": "task-1", "course_name": "课程一", "method": "zytzk-b-b"}],
    }

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            created = client.post("/api/course-selection/snatch-tasks", headers=headers, json=payload)
            assert created.status_code == 200, created.text
            task_id = created.json()["task_id"]
            active = client.get("/api/course-selection/snatch-tasks/active")
            assert active.status_code == 200, active.text
            assert active.json()["task_id"] == task_id
            stopped = client.delete(
                f"/api/course-selection/snatch-tasks/{task_id}",
                headers={"Authorization": "Bearer test-session"},
            )
            assert stopped.status_code == 200, stopped.text
            current = client.get(f"/api/course-selection/snatch-tasks/{task_id}")
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert stopped.json()["status"] == "stopped"
    assert current.json()["status"] == "stopped"
    assert upstream_requests == []


def test_snatch_task_rejects_duplicate_course_ids():
    upstream = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(500)))
    session = Session(client=upstream, state=AuthState.ACTIVE, authenticated=True)
    app.dependency_overrides[get_authenticated_session] = lambda: session
    payload = {
        "start_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "courses": [
            {"course_id": "task-1", "course_name": "课程一", "method": "zytzk-b-b"},
            {"course_id": "task-1", "course_name": "课程一", "method": "zytzk-b-b"},
        ],
    }
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/course-selection/snatch-tasks",
                headers={
                    "Authorization": "Bearer test-session",
                    "Idempotency-Key": "snatch-duplicate-123",
                },
                json=payload,
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_snatch_task_retries_the_direct_selection_endpoint_until_success():
    write_attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal write_attempts
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(200, json=TERM_INFO)
        assert request.url.path == "/Xsxk/addGouwuche"
        write_attempts += 1
        if write_attempts == 1:
            return httpx.Response(200, json={"jg": "0", "message": "该课程容量已满"})
        return httpx.Response(200, json={"jg": "1", "message": "选课成功"})

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(client=upstream, state=AuthState.ACTIVE, authenticated=True)
    app.dependency_overrides[get_authenticated_session] = lambda: session
    payload = {
        "start_at": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
        "retry_interval_seconds": 0.1,
        "courses": [{"course_id": "task-1", "course_name": "课程一", "method": "zytzk-b-b"}],
    }
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            created = client.post(
                "/api/course-selection/snatch-tasks",
                headers={
                    "Authorization": "Bearer test-session",
                    "Idempotency-Key": "snatch-retry-123",
                },
                json=payload,
            )
            task_id = created.json()["task_id"]
            deadline = time.monotonic() + 2
            body = created.json()
            while body["status"] not in {"completed", "completed_with_errors", "failed"}:
                assert time.monotonic() < deadline, body
                time.sleep(0.02)
                body = client.get(f"/api/course-selection/snatch-tasks/{task_id}").json()
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert body["status"] == "completed"
    assert body["items"][0]["status"] == "success"
    assert body["items"][0]["attempts"] == 2
    assert body["items"][0]["error_type"] is None
    assert write_attempts == 2


@pytest.mark.parametrize(
    ("upstream_message", "error_type"),
    [
        ("与已选课程时间冲突", "conflict"),
        ("该课程不面向您所在专业", "not_eligible"),
    ],
)
def test_snatch_task_stops_retrying_permanent_business_rejections(
    upstream_message,
    error_type,
):
    write_attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal write_attempts
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(200, json=TERM_INFO)
        assert request.url.path == "/Xsxk/addGouwuche"
        write_attempts += 1
        return httpx.Response(200, json={"jg": "0", "message": upstream_message})

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(client=upstream, state=AuthState.ACTIVE, authenticated=True)
    app.dependency_overrides[get_authenticated_session] = lambda: session
    payload = {
        "start_at": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
        "retry_interval_seconds": 0.1,
        "courses": [{"course_id": "task-1", "course_name": "课程一", "method": "zytzk-b-b"}],
    }
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            created = client.post(
                "/api/course-selection/snatch-tasks",
                headers={
                    "Authorization": "Bearer test-session",
                    "Idempotency-Key": f"snatch-{error_type}",
                },
                json=payload,
            )
            task_id = created.json()["task_id"]
            deadline = time.monotonic() + 1
            body = created.json()
            while body["status"] not in {"completed_with_errors", "failed"}:
                assert time.monotonic() < deadline, body
                time.sleep(0.02)
                body = client.get(f"/api/course-selection/snatch-tasks/{task_id}").json()
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert body["status"] == "completed_with_errors"
    assert body["items"][0]["status"] == "failed"
    assert body["items"][0]["error_type"] == error_type
    assert body["items"][0]["message"] == upstream_message
    assert write_attempts == 1


def test_snatch_task_confirms_an_already_selected_course():
    upstream_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        upstream_paths.append(request.url.path)
        if request.url.path == "/Xsxk/queryXkdqXnxq":
            return httpx.Response(200, json=TERM_INFO)
        if request.url.path == "/Xsxk/addGouwuche":
            return httpx.Response(200, json={"jg": "0", "message": "您已经选择该课程"})
        assert request.url.path == "/Xsxk/queryYxkc"
        return httpx.Response(200, json={"yxkcList": [{"rwh": "task-1"}]})

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(client=upstream, state=AuthState.ACTIVE, authenticated=True)
    app.dependency_overrides[get_authenticated_session] = lambda: session
    payload = {
        "start_at": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
        "retry_interval_seconds": 0.1,
        "courses": [{"course_id": "task-1", "course_name": "课程一", "method": "zytzk-b-b"}],
    }
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            created = client.post(
                "/api/course-selection/snatch-tasks",
                headers={
                    "Authorization": "Bearer test-session",
                    "Idempotency-Key": "snatch-already-selected",
                },
                json=payload,
            )
            task_id = created.json()["task_id"]
            deadline = time.monotonic() + 1
            body = created.json()
            while body["status"] not in {"completed", "failed"}:
                assert time.monotonic() < deadline, body
                time.sleep(0.02)
                body = client.get(f"/api/course-selection/snatch-tasks/{task_id}").json()
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert body["status"] == "completed"
    assert body["items"][0]["status"] == "success"
    assert body["items"][0]["error_type"] is None
    assert body["items"][0]["attempts"] == 1
    assert upstream_paths == [
        "/Xsxk/queryXkdqXnxq",
        "/Xsxk/addGouwuche",
        "/Xsxk/queryYxkc",
    ]
