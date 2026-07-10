import asyncio
import secrets
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

import httpx

from ..byyt.client import BYYTClient
from ..config import SESSION_MAX_AGE, SESSION_TTL
from ..exceptions import BYYTSessionExpired
from .cookie_store import SessionDatabase, create_session_database


class AuthState(str, Enum):
    INIT = "init"
    OPENED = "opened"
    QR_READY = "qr_ready"
    SMS_READY = "sms_ready"
    SMS_SENT = "sms_sent"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    EXPIRED = "expired"


@dataclass
class Session:
    client: httpx.Client
    state: AuthState = AuthState.INIT
    lck: Optional[str] = None
    sid: Optional[str] = None
    phone: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    singleflight_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    inflight_queries: dict[str, asyncio.Task[Any]] = field(default_factory=dict)
    query_cache: dict[str, tuple[float, Any]] = field(default_factory=dict)
    qr_image: Optional[bytes] = None
    procedure: Optional[object] = None
    closing: bool = False
    authenticated: bool = False
    student_id: Optional[str] = None
    session_id: Optional[str] = None
    qr_monitor_started: bool = False
    last_error: Optional[str] = None


class SessionStore:
    def __init__(
        self,
        ttl: int = 1800,
        max_age: int = 86400,
        clock: Callable[[], float] = time.time,
        persistence: Optional[SessionDatabase] = None,
        persistence_factory: Optional[Callable[[], SessionDatabase]] = None,
    ):
        self._sessions: dict[str, Session] = {}
        self._ttl = ttl
        self._max_age = max_age
        self._clock = clock
        self._persistence = persistence
        self._persistence_factory = persistence_factory
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()

    @property
    def ttl(self) -> int:
        return self._ttl

    @property
    def max_age(self) -> int:
        return self._max_age

    def initialize(self) -> None:
        with self._lock:
            if self._persistence is None and self._persistence_factory is not None:
                self._persistence = self._persistence_factory()

    def _require_persistence(self) -> SessionDatabase:
        self.initialize()
        if self._persistence is None:
            raise RuntimeError("Session persistence is not configured")
        return self._persistence

    def _is_expired(self, session: Session, now: float) -> bool:
        return now - session.last_seen >= self._ttl or now - session.created_at >= self._max_age

    @staticmethod
    def _close_session(session: Session) -> None:
        if session.closing:
            return
        session.closing = True
        session.client.close()

    def _restore_session(self, session_id: str) -> Optional[Session]:
        if self._persistence is None:
            return None

        stored = self._persistence.load(session_id)
        if not stored:
            return None

        now = self._clock()
        if now - stored.last_seen >= self._ttl or now - stored.created_at >= self._max_age:
            self._persistence.delete(session_id)
            return None

        session = Session(
            client=httpx.Client(follow_redirects=True, timeout=60.0),
            created_at=stored.created_at,
            last_seen=now,
        )
        for key, value in stored.cookies.items():
            session.client.cookies.set(key, value, domain=".ustb.edu.cn")

        try:
            BYYTClient(session).validate_session_sync()
        except BYYTSessionExpired:
            try:
                self._persistence.delete(session_id)
            finally:
                self._close_session(session)
            return None
        except Exception:
            # Temporary network/upstream faults must not permanently destroy login.
            self._close_session(session)
            return None

        session.state = AuthState.ACTIVE
        session.authenticated = True
        session.student_id = stored.student_id
        session.session_id = session_id
        self._sessions[session_id] = session
        self._persistence.touch(session_id, last_seen=now)
        return session

    def create(self) -> tuple[str, Session]:
        session_id = secrets.token_urlsafe(24)
        now = self._clock()
        session = Session(
            client=httpx.Client(follow_redirects=True, timeout=60.0),
            created_at=now,
            last_seen=now,
            session_id=session_id,
        )
        with self._lock:
            self._sessions[session_id] = session
        return session_id, session

    def persist(self, session_id: str, student_id: str, cookies: dict[str, str]) -> None:
        persistence = self._require_persistence()
        with self._lock:
            session = self._sessions.get(session_id)
            if not session or session.closing:
                return
            persistence.save(
                session_token=session_id,
                student_id=student_id,
                created_at=session.created_at,
                last_seen=session.last_seen,
                cookies=cookies,
            )

    def get(self, session_id: str) -> Optional[Session]:
        expired_session = None
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                if session.closing:
                    return None
                now = self._clock()
                if self._is_expired(session, now):
                    expired_session = self._sessions.pop(session_id)
                    if self._persistence is not None:
                        self._persistence.delete(session_id)
                else:
                    session.last_seen = now
                    if self._persistence is not None:
                        self._persistence.touch(session_id, last_seen=now)
                    return session
            else:
                return self._restore_session(session_id)

        if expired_session:
            self._close_session(expired_session)
        return None

    def delete(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if self._persistence is not None:
                self._persistence.delete(session_id)
        if session:
            self._close_session(session)

    def rotate(self, old_id: str) -> Optional[str]:
        expired_session = None
        with self._lock:
            session = self._sessions.get(old_id)
            if not session or session.closing:
                return None

            now = self._clock()
            if self._is_expired(session, now):
                expired_session = self._sessions.pop(old_id)
                if self._persistence is not None:
                    self._persistence.delete(old_id)
                new_id = None
            else:
                new_id = secrets.token_urlsafe(24)
                if self._persistence is not None:
                    self._persistence.rotate(old_id, new_id, last_seen=now)
                self._sessions.pop(old_id)
                session.last_seen = now
                session.session_id = new_id
                self._sessions[new_id] = session

        if expired_session:
            self._close_session(expired_session)
        return new_id

    def cleanup_expired(self) -> None:
        now = self._clock()
        with self._lock:
            expired_ids = [
                session_id
                for session_id, session in self._sessions.items()
                if self._is_expired(session, now)
            ]
            if self._persistence is not None:
                self._persistence.delete_expired(now, self._ttl, self._max_age)
            removed_sessions = []
            for session_id in expired_ids:
                session = self._sessions.pop(session_id, None)
                if session:
                    removed_sessions.append(session)

        for session in removed_sessions:
            self._close_session(session)

    async def cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(60)
            self.cleanup_expired()

    def start_cleanup(self) -> None:
        self.initialize()
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self.cleanup_loop())

    def stop_cleanup(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            self._close_session(session)


store = SessionStore(
    ttl=SESSION_TTL,
    max_age=SESSION_MAX_AGE,
    persistence_factory=create_session_database,
)
