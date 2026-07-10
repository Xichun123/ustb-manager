import json

import pytest

from app.config import SESSION_MAX_AGE, SESSION_TTL
from app.services import cookie_store, session_store as session_store_module
from app.services.session_store import SessionStore, store as production_store


class ManualClock:
    def __init__(self, now: float = 1_000.0):
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1


@pytest.fixture
def session_store(monkeypatch, tmp_path):
    monkeypatch.setattr(session_store_module, "SESSION_MAP_PATH", tmp_path / "session_map.json")
    monkeypatch.setattr(session_store_module.httpx, "Client", FakeClient)
    clock = ManualClock()
    return SessionStore(ttl=10, max_age=100, clock=clock), clock


def test_get_refreshes_idle_deadline_for_an_active_session(session_store):
    store, clock = session_store
    session_id, session = store.create()

    clock.advance(9)
    assert store.get(session_id) is session
    assert session.last_seen == 1_009.0

    clock.advance(9)
    assert store.get(session_id) is session
    assert session.last_seen == 1_018.0
    assert session.client.close_calls == 0


def test_get_expires_an_idle_session_and_closes_it_once(session_store):
    store, clock = session_store
    session_id, session = store.create()

    clock.advance(11)

    assert store.get(session_id) is None
    assert session.client.close_calls == 1
    assert store.get(session_id) is None
    assert session.client.close_calls == 1


def test_get_enforces_absolute_ttl_despite_continued_activity(session_store):
    _, clock = session_store
    store = SessionStore(ttl=10, max_age=20, clock=clock)
    session_id, session = store.create()

    clock.advance(9)
    assert store.get(session_id) is session
    clock.advance(9)
    assert store.get(session_id) is session

    clock.advance(3)

    assert store.get(session_id) is None
    assert session.client.close_calls == 1


def test_rotate_preserves_absolute_age_while_refreshing_activity(session_store):
    _, clock = session_store
    store = SessionStore(ttl=20, max_age=10, clock=clock)
    old_id, session = store.create()

    clock.advance(4)
    new_id = store.rotate(old_id)

    assert new_id is not None
    assert new_id != old_id
    assert session.session_id == new_id
    assert session.created_at == 1_000.0
    assert session.last_seen == 1_004.0
    assert store.get(old_id) is None

    clock.advance(7)

    assert store.get(new_id) is None
    assert session.client.close_calls == 1


def test_single_cleanup_closes_the_removed_session_once(session_store):
    store, clock = session_store
    session_id, session = store.create()

    clock.advance(11)
    store.cleanup_expired()

    assert store.get(session_id) is None
    assert session.client.close_calls == 1

    store.cleanup_expired()
    assert session.client.close_calls == 1


def test_production_store_uses_configured_lifetimes():
    assert production_store.ttl == SESSION_TTL
    assert production_store.max_age == SESSION_MAX_AGE


def test_idle_expiration_invalidates_the_persisted_mapping(session_store, monkeypatch):
    store, clock = session_store
    session_id, _ = store.create()
    store.persist(session_id, "test-student")

    clock.advance(11)
    assert store.get(session_id) is None

    restarted_store = SessionStore(ttl=10, max_age=100, clock=clock)

    def fail_if_cookies_are_loaded(student_id):
        pytest.fail(f"expired mapping attempted cookie recovery for {student_id}")

    monkeypatch.setattr(cookie_store, "load_cookies", fail_if_cookies_are_loaded)
    assert restarted_store.get(session_id) is None


def test_loading_expired_mapping_removes_it_from_persistent_storage(session_store):
    _, clock = session_store
    mapping_path = session_store_module.SESSION_MAP_PATH
    mapping_path.write_text(
        json.dumps({"expired-session": {"student_id": "test-student", "created_at": 900.0}}),
        encoding="utf-8",
    )

    SessionStore(ttl=10, max_age=50, clock=clock)

    assert json.loads(mapping_path.read_text(encoding="utf-8")) == {}


def test_get_rejects_a_mapping_that_expires_after_store_start(session_store, monkeypatch):
    store, clock = session_store
    session_id, _ = store.create()
    store.persist(session_id, "test-student")
    restarted_store = SessionStore(ttl=10, max_age=50, clock=clock)

    clock.advance(51)

    def fail_if_cookies_are_loaded(student_id):
        pytest.fail(f"expired mapping attempted cookie recovery for {student_id}")

    monkeypatch.setattr(cookie_store, "load_cookies", fail_if_cookies_are_loaded)

    assert restarted_store.get(session_id) is None
    assert json.loads(session_store_module.SESSION_MAP_PATH.read_text(encoding="utf-8")) == {}
