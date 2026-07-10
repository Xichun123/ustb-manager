import asyncio
import secrets
import time
import threading
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional
import httpx

from ..config import SESSION_MAX_AGE, SESSION_TTL


SESSION_MAP_PATH = Path.home() / ".ustb_manager" / "session_map.json"


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
    qr_image: Optional[bytes] = None
    procedure: Optional[object] = None
    closing: bool = False
    authenticated: bool = False
    student_id: Optional[str] = None
    session_id: Optional[str] = None  # 存储 session_id 以便持久化
    qr_monitor_started: bool = False
    last_error: Optional[str] = None


class SessionStore:
    def __init__(
        self,
        ttl: int = 1800,
        max_age: int = 86400,
        clock: Callable[[], float] = time.time,
    ):
        self._sessions: dict[str, Session] = {}
        self._ttl = ttl
        self._max_age = max_age
        self._clock = clock
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()
        self._session_map: dict[str, dict] = self._load_session_map()

    @property
    def ttl(self) -> int:
        return self._ttl

    @property
    def max_age(self) -> int:
        return self._max_age

    def _load_session_map(self) -> dict[str, dict]:
        """Load session_id -> student_id mapping from file"""
        if not SESSION_MAP_PATH.exists():
            return {}
        try:
            with open(SESSION_MAP_PATH, "r") as f:
                data = json.load(f)
            now = self._clock()
            active_mappings = {
                key: value
                for key, value in data.items()
                if now - value.get("created_at", 0) < self._max_age
            }
            if active_mappings != data:
                # Cookie cleanup stays in the SQLite migration; removing the mapping prevents recovery.
                self._write_session_map(active_mappings)
            return active_mappings
        except Exception:
            return {}

    def _write_session_map(self, session_map: dict[str, dict]) -> None:
        SESSION_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(SESSION_MAP_PATH, "w") as f:
                json.dump(session_map, f)
        except Exception:
            pass

    def _save_session_map(self) -> None:
        """Save session_id -> student_id mapping to file"""
        self._write_session_map(self._session_map)

    def _restore_session(self, session_id: str) -> Optional[Session]:
        """Try to restore session from persisted cookies"""
        from . import cookie_store

        mapping = self._session_map.get(session_id)
        if not mapping:
            return None

        if self._clock() - mapping.get("created_at", 0) >= self._max_age:
            # Cookie cleanup stays in the SQLite migration; removing the mapping prevents recovery.
            self._session_map.pop(session_id, None)
            self._save_session_map()
            return None

        student_id = mapping.get("student_id")
        if not student_id:
            self._session_map.pop(session_id, None)
            self._save_session_map()
            return None

        cookies = cookie_store.load_cookies(student_id)
        if not cookies:
            del self._session_map[session_id]
            self._save_session_map()
            return None

        session = Session(client=httpx.Client(follow_redirects=True, timeout=60.0))
        for key, value in cookies.items():
            session.client.cookies.set(key, value, domain=".ustb.edu.cn")

        # Verify cookies are still valid by making a test request
        try:
            resp = session.client.post(
                "https://byyt.ustb.edu.cn/UserManager/queryxsxx", timeout=5.0
            )
            resp.raise_for_status()
            data = resp.json()

            # If the response doesn't contain student info, cookies are invalid
            if not data or "XH" not in data:
                # Cookies expired, clean up
                del self._session_map[session_id]
                self._save_session_map()
                cookie_store.delete_cookies(student_id)
                session.client.close()
                return None

        except Exception:
            # Verification failed, cookies are invalid
            del self._session_map[session_id]
            self._save_session_map()
            cookie_store.delete_cookies(student_id)
            session.client.close()
            return None

        session.state = AuthState.ACTIVE
        session.authenticated = True
        session.student_id = student_id
        session.session_id = session_id  # 恢复时也要设置 session_id
        session.created_at = mapping.get("created_at", self._clock())

        self._sessions[session_id] = session
        return session

    def create(self) -> tuple[str, Session]:
        session_id = secrets.token_urlsafe(24)
        now = self._clock()
        # 增加超时时间，避免 SSO 服务器响应慢导致超时
        session = Session(
            client=httpx.Client(follow_redirects=True, timeout=60.0),
            created_at=now,
            last_seen=now,
        )
        session.session_id = session_id  # 存储 session_id
        with self._lock:
            self._sessions[session_id] = session
        return session_id, session

    def persist(self, session_id: str, student_id: str) -> None:
        """Persist session mapping for recovery after restart"""
        with self._lock:
            session = self._sessions.get(session_id)
            existing_mapping = self._session_map.get(session_id)
            if existing_mapping:
                created_at = existing_mapping.get("created_at", self._clock())
            elif session:
                created_at = session.created_at
            else:
                created_at = self._clock()
            self._session_map[session_id] = {
                "student_id": student_id,
                "created_at": created_at,
            }
            self._save_session_map()

    def _is_expired(self, session: Session, now: float) -> bool:
        return now - session.last_seen >= self._ttl or now - session.created_at >= self._max_age

    @staticmethod
    def _close_session(session: Session) -> None:
        if session.closing:
            return
        session.closing = True
        session.client.close()

    def get(self, session_id: str) -> Optional[Session]:
        expired_session = None
        with self._lock:
            session = self._sessions.get(session_id)
            if session and not session.closing:
                now = self._clock()
                if self._is_expired(session, now):
                    expired_session = self._sessions.pop(session_id)
                    if self._session_map.pop(session_id, None) is not None:
                        self._save_session_map()
                else:
                    session.last_seen = now
                    return session
            else:
                session = self._restore_session(session_id)
                if not session:
                    return None
                session.last_seen = self._clock()
                return session

        if expired_session:
            self._close_session(expired_session)
        return None

    def delete(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.pop(session_id, None)
            self._session_map.pop(session_id, None)
            self._save_session_map()
        if session:
            self._close_session(session)

    def rotate(self, old_id: str) -> Optional[str]:
        with self._lock:
            session = self._sessions.pop(old_id, None)
            old_mapping = self._session_map.pop(old_id, None)
            if not session or session.closing:
                return None
            new_id = secrets.token_urlsafe(24)
            session.last_seen = self._clock()
            session.session_id = new_id  # 更新 session 对象中的 session_id
            self._sessions[new_id] = session
            if old_mapping:
                self._session_map[new_id] = old_mapping
                self._save_session_map()
            return new_id

    def cleanup_expired(self) -> None:
        now = self._clock()
        removed_sessions = []
        mapping_changed = False
        with self._lock:
            expired_ids = [
                session_id
                for session_id, session in self._sessions.items()
                if self._is_expired(session, now)
            ]
            for session_id in expired_ids:
                session = self._sessions.pop(session_id, None)
                if session:
                    removed_sessions.append(session)
                if self._session_map.pop(session_id, None) is not None:
                    mapping_changed = True
            if mapping_changed:
                self._save_session_map()

        for session in removed_sessions:
            self._close_session(session)

    async def cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(60)
            self.cleanup_expired()

    def start_cleanup(self) -> None:
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self.cleanup_loop())

    def stop_cleanup(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
        with self._lock:
            sessions = list(self._sessions.items())
            self._sessions.clear()
        for _, session in sessions:
            self._close_session(session)


store = SessionStore(ttl=SESSION_TTL, max_age=SESSION_MAX_AGE)
