"""Tests for lib/db.py — schema creation and basic connectivity."""
import sqlite3
import pytest
from lib.db import init_db, get_connection


def test_init_db_creates_all_tables(tmp_path):
    path = str(tmp_path / "test.db")
    conn = init_db(path)
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    required = {"users", "sessions", "login_attempts", "equipment", "work_logs", "work_photos"}
    assert required.issubset(tables)
    conn.close()


def test_init_db_idempotent(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    # Should not raise on second call
    conn = init_db(path)
    conn.close()


def test_get_connection_row_factory(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    conn = get_connection(path)
    conn.execute("INSERT INTO users (login_id, password_hash, display_name, role, is_active, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                 ("u1", "hash", "User One", "user", 1, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"))
    conn.commit()
    row = conn.execute("SELECT * FROM users WHERE login_id='u1'").fetchone()
    # Row factory should allow dict-like access
    assert row["login_id"] == "u1"
    conn.close()


def test_users_table_has_unique_login_id(db):
    db.execute(
        "INSERT INTO users (login_id, password_hash, display_name, role, is_active, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?)",
        ("duplicate", "hash", "A", "user", 1, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
    )
    db.commit()
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO users (login_id, password_hash, display_name, role, is_active, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?)",
            ("duplicate", "hash2", "B", "user", 1, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
        )


def test_sessions_table_has_unique_token(db):
    db.execute(
        "INSERT INTO users (login_id, password_hash, display_name, role, is_active, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?)",
        ("u1", "h", "U", "user", 1, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
    )
    db.commit()
    uid = db.execute("SELECT id FROM users WHERE login_id='u1'").fetchone()["id"]
    db.execute(
        "INSERT INTO sessions (user_id, session_token, expires_at, created_at, last_access_at) VALUES (?,?,?,?,?)",
        (uid, "tok123", "2026-02-01T00:00:00Z", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
    )
    db.commit()
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO sessions (user_id, session_token, expires_at, created_at, last_access_at) VALUES (?,?,?,?,?)",
            (uid, "tok123", "2026-02-01T00:00:00Z", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
        )


def test_work_logs_unique_log_uuid(db):
    db.execute(
        "INSERT INTO users (login_id, password_hash, display_name, role, is_active, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?)",
        ("u1", "h", "U", "user", 1, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
    )
    db.commit()
    uid = db.execute("SELECT id FROM users WHERE login_id='u1'").fetchone()["id"]
    import uuid
    luuid = str(uuid.uuid4())
    now = "2026-01-01T00:00:00Z"
    db.execute(
        "INSERT INTO work_logs (log_uuid, user_id, record_type, status, title, recorded_at, "
        "server_updated_at, revision, created_by, updated_by) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (luuid, uid, "inspection", "open", "Test", now, now, 1, uid, uid),
    )
    db.commit()
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO work_logs (log_uuid, user_id, record_type, status, title, recorded_at, "
            "server_updated_at, revision, created_by, updated_by) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (luuid, uid, "repair", "open", "Dup", now, now, 1, uid, uid),
        )


def test_equipment_unique_code(db):
    now = "2026-01-01T00:00:00Z"
    db.execute(
        "INSERT INTO equipment (equipment_code, equipment_name, is_active, created_at, updated_at) "
        "VALUES (?,?,?,?,?)",
        ("MC-001", "Machine 1", 1, now, now),
    )
    db.commit()
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO equipment (equipment_code, equipment_name, is_active, created_at, updated_at) "
            "VALUES (?,?,?,?,?)",
            ("MC-001", "Machine 2", 1, now, now),
        )
