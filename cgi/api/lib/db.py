"""SQLite database connection and schema management."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "inspection_app.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login_id TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    email TEXT,
    role TEXT NOT NULL DEFAULT 'user',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_token TEXT UNIQUE NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_access_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login_id TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    attempted_at TEXT NOT NULL,
    success INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS equipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_code TEXT UNIQUE NOT NULL,
    equipment_name TEXT NOT NULL,
    location TEXT,
    line_name TEXT,
    model TEXT,
    maker TEXT,
    qr_value TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS work_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_uuid TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    equipment_id INTEGER,
    record_type TEXT NOT NULL,
    status TEXT NOT NULL,
    title TEXT NOT NULL,
    symptom TEXT,
    work_detail TEXT,
    result TEXT,
    priority TEXT,
    recorded_at TEXT NOT NULL,
    needs_followup INTEGER NOT NULL DEFAULT 0,
    followup_due TEXT,
    server_updated_at TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    created_by INTEGER NOT NULL,
    updated_by INTEGER NOT NULL,
    deleted_flag INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT,
    deleted_by INTEGER
);

CREATE TABLE IF NOT EXISTS work_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_uuid TEXT NOT NULL,
    photo_path TEXT NOT NULL,
    caption TEXT,
    taken_at TEXT,
    created_at TEXT NOT NULL
);
"""


def get_connection(db_path=None):
    """Return a sqlite3 connection with row_factory set."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path=None):
    """Create all tables if they don't exist."""
    conn = get_connection(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn
