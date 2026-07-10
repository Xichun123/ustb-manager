import hashlib
import sqlite3
import stat

import pytest
from cryptography.fernet import Fernet

from app.services.cookie_store import SessionDatabase


@pytest.mark.parametrize("encryption_key", [None, "not-a-fernet-key"])
def test_session_database_requires_a_valid_encryption_key(tmp_path, encryption_key):
    database_path = tmp_path / "sessions.db"

    with pytest.raises(RuntimeError, match="SESSION_ENCRYPTION_KEY"):
        SessionDatabase(database_path, encryption_key=encryption_key)

    assert not database_path.exists()


def test_session_database_encrypts_cookies_and_hashes_tokens(tmp_path):
    database_path = tmp_path / "private" / "sessions.db"
    database = SessionDatabase(database_path, encryption_key=Fernet.generate_key())
    session_token = "raw-session-token-that-must-not-be-stored"
    cookies = {
        "INCO": "plaintext-cookie-secret",
        "SESSION": "another-cookie-secret",
    }

    database.save(
        session_token=session_token,
        student_id="test-student",
        created_at=1_000.0,
        last_seen=1_005.0,
        cookies=cookies,
    )

    stored = database.load(session_token)
    assert stored is not None
    assert stored.student_id == "test-student"
    assert stored.created_at == 1_000.0
    assert stored.last_seen == 1_005.0
    assert stored.cookies == cookies

    with sqlite3.connect(database_path) as connection:
        stored_token_hash = connection.execute("SELECT token_hash FROM sessions").fetchone()[0]
    assert stored_token_hash == hashlib.sha256(session_token.encode()).digest()

    database_bytes = database_path.read_bytes()
    assert session_token.encode() not in database_bytes
    assert b"plaintext-cookie-secret" not in database_bytes
    assert b"another-cookie-secret" not in database_bytes
    assert stat.S_IMODE(database_path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(database_path.stat().st_mode) == 0o600


def test_session_database_deletes_legacy_json_without_migrating_it(tmp_path):
    data_directory = tmp_path / "private"
    data_directory.mkdir()
    legacy_cookie_path = data_directory / "cookies.json"
    legacy_mapping_path = data_directory / "session_map.json"
    legacy_cookie_path.write_text("not valid json and must not be read", encoding="utf-8")
    legacy_mapping_path.write_bytes(b"legacy-session-token")

    SessionDatabase(
        data_directory / "sessions.db",
        encryption_key=Fernet.generate_key(),
        legacy_paths=(legacy_cookie_path, legacy_mapping_path),
    )

    assert not legacy_cookie_path.exists()
    assert not legacy_mapping_path.exists()


def test_session_database_invalidates_records_encrypted_with_another_key(tmp_path):
    database_path = tmp_path / "sessions.db"
    original_database = SessionDatabase(database_path, encryption_key=Fernet.generate_key())
    original_database.save(
        session_token="session-token",
        student_id="test-student",
        created_at=1_000.0,
        last_seen=1_000.0,
        cookies={"SESSION": "cookie-secret"},
    )

    database_with_new_key = SessionDatabase(
        database_path,
        encryption_key=Fernet.generate_key(),
    )

    assert database_with_new_key.load("session-token") is None
    assert original_database.load("session-token") is None


def test_session_database_touches_and_rotates_a_session(tmp_path):
    database_path = tmp_path / "sessions.db"
    database = SessionDatabase(database_path, encryption_key=Fernet.generate_key())
    old_token = "old-raw-session-token"
    new_token = "new-raw-session-token"
    database.save(
        session_token=old_token,
        student_id="test-student",
        created_at=1_000.0,
        last_seen=1_001.0,
        cookies={"SESSION": "cookie-secret"},
    )

    database.touch(old_token, last_seen=1_004.0)
    database.rotate(old_token, new_token, last_seen=1_006.0)

    assert database.load(old_token) is None
    stored = database.load(new_token)
    assert stored is not None
    assert stored.created_at == 1_000.0
    assert stored.last_seen == 1_006.0
    assert stored.cookies == {"SESSION": "cookie-secret"}
    database_bytes = database_path.read_bytes()
    assert old_token.encode() not in database_bytes
    assert new_token.encode() not in database_bytes


def test_session_database_deletes_expired_and_explicitly_removed_sessions(tmp_path):
    database = SessionDatabase(tmp_path / "sessions.db", encryption_key=Fernet.generate_key())
    records = {
        "idle-token": (950.0, 980.0),
        "absolute-token": (899.0, 999.0),
        "active-token": (950.0, 995.0),
    }
    for token, (created_at, last_seen) in records.items():
        database.save(
            session_token=token,
            student_id="test-student",
            created_at=created_at,
            last_seen=last_seen,
            cookies={"SESSION": f"cookie-for-{token}"},
        )

    database.delete_expired(now=1_000.0, ttl=10, max_age=100)

    assert database.load("idle-token") is None
    assert database.load("absolute-token") is None
    assert database.load("active-token") is not None

    database.delete("active-token")
    assert database.load("active-token") is None
