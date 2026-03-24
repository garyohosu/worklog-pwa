"""Shared pytest fixtures."""
import sys
import os
import pytest

# Add api/lib to path so tests can import without package prefix
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from lib.db import init_db, get_connection


@pytest.fixture
def db(tmp_path):
    """In-memory (temp file) SQLite DB, fresh for each test."""
    db_path = str(tmp_path / "test.db")
    conn = init_db(db_path)
    yield conn
    conn.close()


@pytest.fixture
def db_path(tmp_path):
    """Return path to a freshly initialised DB."""
    path = str(tmp_path / "test.db")
    init_db(path)
    return path
