import binascii
import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from cryptography.fernet import Fernet, InvalidToken

from ..config import SESSION_ENCRYPTION_KEY

DATA_DIRECTORY = Path.home() / ".ustb_manager"
SESSION_DATABASE_PATH = DATA_DIRECTORY / "sessions.db"
LEGACY_COOKIE_PATH = DATA_DIRECTORY / "cookies.json"
LEGACY_SESSION_MAP_PATH = DATA_DIRECTORY / "session_map.json"


@dataclass(frozen=True)
class StoredSession:
    student_id: str
    created_at: float
    last_seen: float
    cookies: dict[str, str]


class SessionDatabase:
    def __init__(
        self,
        database_path: Path,
        encryption_key: str | bytes | None,
        legacy_paths: Iterable[Path] = (),
    ):
        if not encryption_key:
            raise RuntimeError("SESSION_ENCRYPTION_KEY is required")
        key = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
        try:
            self._fernet = Fernet(key)
        except (binascii.Error, TypeError, ValueError) as exc:
            raise RuntimeError("SESSION_ENCRYPTION_KEY must be a valid Fernet key") from exc
        self._database_path = Path(database_path)
        self._legacy_paths = tuple(Path(path) for path in legacy_paths)
        self._initialize()

    @staticmethod
    def _token_hash(session_token: str) -> bytes:
        return hashlib.sha256(session_token.encode()).digest()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    def _initialize(self) -> None:
        self._database_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self._database_path.parent, 0o700)
        for legacy_path in self._legacy_paths:
            try:
                legacy_path.unlink()
            except FileNotFoundError:
                pass
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash BLOB PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_seen REAL NOT NULL,
                    encrypted_cookies BLOB NOT NULL
                )
                """
            )
        os.chmod(self._database_path, 0o600)

    def healthcheck(self) -> None:
        with self._connect() as connection:
            connection.execute("SELECT 1").fetchone()

    def save(
        self,
        session_token: str,
        student_id: str,
        created_at: float,
        last_seen: float,
        cookies: dict[str, str],
    ) -> None:
        cookie_payload = json.dumps(cookies, sort_keys=True, separators=(",", ":")).encode()
        encrypted_cookies = self._fernet.encrypt(cookie_payload)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    token_hash, student_id, created_at, last_seen, encrypted_cookies
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(token_hash) DO UPDATE SET
                    student_id = excluded.student_id,
                    created_at = excluded.created_at,
                    last_seen = excluded.last_seen,
                    encrypted_cookies = excluded.encrypted_cookies
                """,
                (
                    self._token_hash(session_token),
                    student_id,
                    created_at,
                    last_seen,
                    encrypted_cookies,
                ),
            )

    def load(self, session_token: str) -> Optional[StoredSession]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT student_id, created_at, last_seen, encrypted_cookies
                FROM sessions
                WHERE token_hash = ?
                """,
                (self._token_hash(session_token),),
            ).fetchone()
        if not row:
            return None

        student_id, created_at, last_seen, encrypted_cookies = row
        try:
            cookies = json.loads(self._fernet.decrypt(encrypted_cookies))
        except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError):
            self.delete(session_token)
            return None
        return StoredSession(
            student_id=student_id,
            created_at=created_at,
            last_seen=last_seen,
            cookies=cookies,
        )

    def touch(self, session_token: str, last_seen: float) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE sessions SET last_seen = ? WHERE token_hash = ?",
                (last_seen, self._token_hash(session_token)),
            )

    def rotate(self, old_token: str, new_token: str, last_seen: float) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE sessions
                SET token_hash = ?, last_seen = ?
                WHERE token_hash = ?
                """,
                (
                    self._token_hash(new_token),
                    last_seen,
                    self._token_hash(old_token),
                ),
            )

    def delete(self, session_token: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM sessions WHERE token_hash = ?",
                (self._token_hash(session_token),),
            )

    def delete_expired(self, now: float, ttl: int, max_age: int) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM sessions
                WHERE last_seen <= ? OR created_at <= ?
                """,
                (now - ttl, now - max_age),
            )


def create_session_database() -> SessionDatabase:
    return SessionDatabase(
        SESSION_DATABASE_PATH,
        encryption_key=SESSION_ENCRYPTION_KEY,
        legacy_paths=(LEGACY_COOKIE_PATH, LEGACY_SESSION_MAP_PATH),
    )
