import pytest
from cryptography.fernet import Fernet

from app.config import SESSION_MAX_AGE, SESSION_TTL
from app.services import session_store as session_store_module
from app.services.cookie_store import SessionDatabase
from app.services.session_store import SessionStore, store as production_store


class ManualClock:
    def __init__(self, now: float = 1_000.0):
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeCookies:
    def __init__(self):
        self.values = {}

    def set(self, key, value, domain=None):
        self.values[key] = value


class FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"XH": "test-student"}


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.close_calls = 0
        self.cookies = FakeCookies()
        self.post_calls = 0

    def post(self, *args, **kwargs):
        self.post_calls += 1
        return FakeResponse()

    def close(self) -> None:
        self.close_calls += 1


@pytest.fixture
def session_store(monkeypatch):
    monkeypatch.setattr(session_store_module.httpx, "Client", FakeClient)
    clock = ManualClock()
    return SessionStore(ttl=10, max_age=100, clock=clock), clock


def test_persisted_session_is_restored_from_encrypted_sqlite(session_store, tmp_path):
    _, clock = session_store
    database = SessionDatabase(tmp_path / "sessions.db", encryption_key=Fernet.generate_key())
    first_store = SessionStore(ttl=10, max_age=100, clock=clock, persistence=database)
    session_id, session = first_store.create()
    first_store.persist(session_id, "test-student", {"SESSION": "cookie-secret"})

    restarted_store = SessionStore(ttl=10, max_age=100, clock=clock, persistence=database)
    restored = restarted_store.get(session_id)

    assert restored is not None
    assert restored is not session
    assert restored.authenticated is True
    assert restored.student_id == "test-student"
    assert restored.created_at == 1_000.0
    assert restored.last_seen == 1_000.0
    assert restored.client.cookies.values == {"SESSION": "cookie-secret"}
    assert restored.client.post_calls == 1


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


def test_get_persists_the_refreshed_idle_deadline_across_restart(session_store, tmp_path):
    _, clock = session_store
    database = SessionDatabase(tmp_path / "sessions.db", encryption_key=Fernet.generate_key())
    first_store = SessionStore(ttl=10, max_age=100, clock=clock, persistence=database)
    session_id, session = first_store.create()
    first_store.persist(session_id, "test-student", {"SESSION": "cookie-secret"})

    clock.advance(9)
    assert first_store.get(session_id) is session

    restarted_store = SessionStore(ttl=10, max_age=100, clock=clock, persistence=database)
    clock.advance(9)

    assert restarted_store.get(session_id) is not None


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


def test_rotate_preserves_absolute_age_while_refreshing_activity(session_store, tmp_path):
    _, clock = session_store
    database = SessionDatabase(tmp_path / "sessions.db", encryption_key=Fernet.generate_key())
    store = SessionStore(ttl=20, max_age=10, clock=clock, persistence=database)
    old_id, session = store.create()
    store.persist(old_id, "test-student", {"SESSION": "cookie-secret"})

    clock.advance(4)
    new_id = store.rotate(old_id)

    assert new_id is not None
    assert new_id != old_id
    assert session.session_id == new_id
    assert session.created_at == 1_000.0
    assert session.last_seen == 1_004.0
    assert store.get(old_id) is None
    assert database.load(old_id) is None
    stored = database.load(new_id)
    assert stored is not None
    assert stored.created_at == 1_000.0
    assert stored.last_seen == 1_004.0

    clock.advance(7)

    assert store.get(new_id) is None
    assert session.client.close_calls == 1
    assert database.load(new_id) is None


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


def test_session_store_initialization_rejects_a_missing_encryption_key(tmp_path):
    store = SessionStore(
        persistence_factory=lambda: SessionDatabase(
            tmp_path / "sessions.db",
            encryption_key=None,
        )
    )

    with pytest.raises(RuntimeError, match="SESSION_ENCRYPTION_KEY"):
        store.initialize()


def test_idle_expiration_invalidates_the_persisted_session(session_store, tmp_path):
    _, clock = session_store
    database = SessionDatabase(tmp_path / "sessions.db", encryption_key=Fernet.generate_key())
    store = SessionStore(ttl=10, max_age=100, clock=clock, persistence=database)
    session_id, _ = store.create()
    store.persist(session_id, "test-student", {"SESSION": "cookie-secret"})

    clock.advance(11)

    assert store.get(session_id) is None
    assert database.load(session_id) is None


def test_cleanup_removes_database_only_expired_sessions(session_store, tmp_path):
    _, clock = session_store
    database = SessionDatabase(tmp_path / "sessions.db", encryption_key=Fernet.generate_key())
    database.save(
        session_token="expired-session",
        student_id="test-student",
        created_at=900.0,
        last_seen=999.0,
        cookies={"SESSION": "cookie-secret"},
    )
    store = SessionStore(ttl=10, max_age=50, clock=clock, persistence=database)

    store.cleanup_expired()

    assert database.load("expired-session") is None


def test_get_rejects_a_persisted_session_that_expires_after_store_start(session_store, tmp_path):
    _, clock = session_store
    database = SessionDatabase(tmp_path / "sessions.db", encryption_key=Fernet.generate_key())
    first_store = SessionStore(ttl=10, max_age=50, clock=clock, persistence=database)
    session_id, _ = first_store.create()
    first_store.persist(session_id, "test-student", {"SESSION": "cookie-secret"})
    restarted_store = SessionStore(ttl=10, max_age=50, clock=clock, persistence=database)

    clock.advance(51)

    assert restarted_store.get(session_id) is None
    assert database.load(session_id) is None
