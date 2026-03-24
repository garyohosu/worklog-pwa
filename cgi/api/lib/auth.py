"""Authentication business logic."""
import bcrypt
import secrets
import string
from datetime import datetime, timezone, timedelta

from .db import get_connection
from .validator import validate_login_id, validate_password, validate_display_name

SESSION_DAYS = 7
LOCK_THRESHOLD = 5       # failures before lock
LOCK_MINUTES = 15        # lock duration


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _expires_at() -> str:
    dt = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------
def register_user(db_path: str, login_id: str, password: str, display_name: str,
                  email: str = None) -> dict:
    errors = []
    for err in [
        validate_login_id(login_id),
        validate_password(password),
        validate_display_name(display_name),
    ]:
        if err:
            errors.append(err)
    if errors:
        raise AuthError("; ".join(errors), 400)

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    now = _now_utc()
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO users (login_id, password_hash, display_name, email, role, is_active, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (login_id, pw_hash, display_name, email, "user", 1, now, now),
        )
        conn.commit()
    except Exception:
        raise AuthError(f"login_id '{login_id}' already exists", 409)

    row = conn.execute("SELECT * FROM users WHERE login_id=?", (login_id,)).fetchone()
    return dict(row)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
def _is_locked(conn, login_id: str, ip: str) -> bool:
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=LOCK_MINUTES)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    # login_id 単位
    cnt_id = conn.execute(
        "SELECT COUNT(*) FROM login_attempts WHERE login_id=? AND success=0 AND attempted_at>=?",
        (login_id, cutoff),
    ).fetchone()[0]
    if cnt_id >= LOCK_THRESHOLD:
        return True
    # IP 単位
    cnt_ip = conn.execute(
        "SELECT COUNT(*) FROM login_attempts WHERE ip_address=? AND success=0 AND attempted_at>=?",
        (ip, cutoff),
    ).fetchone()[0]
    return cnt_ip >= LOCK_THRESHOLD


def login_user(db_path: str, login_id: str, password: str, ip: str) -> dict:
    if err := validate_login_id(login_id):
        raise AuthError(err, 400)

    conn = get_connection(db_path)
    now = _now_utc()

    if _is_locked(conn, login_id, ip):
        raise AuthError("Too many login attempts. Try again later.", 429)

    row = conn.execute("SELECT * FROM users WHERE login_id=?", (login_id,)).fetchone()

    def _record_attempt(success: int):
        conn.execute(
            "INSERT INTO login_attempts (login_id, ip_address, attempted_at, success) VALUES (?,?,?,?)",
            (login_id, ip, now, success),
        )
        conn.commit()

    if row is None or not bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        _record_attempt(0)
        raise AuthError("Invalid login_id or password", 401)

    if not row["is_active"]:
        raise AuthError("Account is disabled", 403)

    # Success
    _record_attempt(1)

    token = secrets.token_urlsafe(32)
    expires = _expires_at()
    conn.execute(
        "INSERT INTO sessions (user_id, session_token, expires_at, created_at, last_access_at) VALUES (?,?,?,?,?)",
        (row["id"], token, expires, now, now),
    )
    conn.execute(
        "UPDATE users SET last_login_at=? WHERE id=?", (now, row["id"])
    )
    conn.commit()

    return {
        "session_token": token,
        "user_id": row["id"],
        "display_name": row["display_name"],
        "role": row["role"],
    }


# ---------------------------------------------------------------------------
# Session check (also slides expiry)
# ---------------------------------------------------------------------------
def check_session(db_path: str, token: str) -> dict:
    conn = get_connection(db_path)
    now = _now_utc()
    row = conn.execute(
        "SELECT s.*, u.login_id, u.display_name, u.role, u.is_active "
        "FROM sessions s JOIN users u ON s.user_id=u.id "
        "WHERE s.session_token=?",
        (token,),
    ).fetchone()
    if row is None:
        raise AuthError("Invalid session token", 401)
    if row["expires_at"] < now:
        raise AuthError("Session expired", 401)
    if not row["is_active"]:
        raise AuthError("Account is disabled", 403)

    # Slide expiry
    new_expires = _expires_at()
    conn.execute(
        "UPDATE sessions SET expires_at=?, last_access_at=? WHERE session_token=?",
        (new_expires, now, token),
    )
    conn.commit()
    return dict(row)


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------
def logout_user(db_path: str, token: str):
    conn = get_connection(db_path)
    conn.execute("DELETE FROM sessions WHERE session_token=?", (token,))
    conn.commit()


# ---------------------------------------------------------------------------
# Change password
# ---------------------------------------------------------------------------
def change_password(db_path: str, token: str, old_password: str, new_password: str):
    user = check_session(db_path, token)
    if err := validate_password(new_password):
        raise AuthError(err, 400)

    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT password_hash FROM users WHERE id=?", (user["user_id"],)
    ).fetchone()
    if row is None:
        raise AuthError("User not found", 404)
    if not bcrypt.checkpw(old_password.encode(), row["password_hash"].encode()):
        raise AuthError("Old password is incorrect", 401)

    new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    now = _now_utc()
    conn.execute(
        "UPDATE users SET password_hash=?, updated_at=? WHERE id=?",
        (new_hash, now, user["user_id"]),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Reset password (admin operation)
# ---------------------------------------------------------------------------
def reset_password(db_path: str, login_id: str) -> str:
    """Generate a random temporary password, store hash, and return the plain text."""
    alphabet = string.ascii_letters + string.digits
    new_pw = "".join(secrets.choice(alphabet) for _ in range(16))
    new_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
    now = _now_utc()
    conn = get_connection(db_path)
    conn.execute(
        "UPDATE users SET password_hash=?, updated_at=? WHERE login_id=?",
        (new_hash, now, login_id),
    )
    conn.commit()
    return new_pw
