"""Tests for lib/auth.py — TC-AUTH-* test cases."""
import pytest
from datetime import datetime, timezone, timedelta
from lib.auth import (
    register_user,
    login_user,
    logout_user,
    check_session,
    change_password,
    reset_password,
    AuthError,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _now_plus(days=0, minutes=0) -> str:
    dt = datetime.now(timezone.utc) + timedelta(days=days, minutes=minutes)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# TC-AUTH-REG: 新規登録
# ---------------------------------------------------------------------------
class TestRegister:
    def test_normal_registration(self, db_path):
        result = register_user(db_path, "user01", "pass1234", "田中")
        assert result["login_id"] == "user01"
        assert result["is_active"] == 1
        assert result["role"] == "user"

    def test_password_stored_as_bcrypt_hash(self, db_path):
        import bcrypt
        register_user(db_path, "user01", "pass1234", "田中")
        from lib.db import get_connection
        row = get_connection(db_path).execute(
            "SELECT password_hash FROM users WHERE login_id='user01'"
        ).fetchone()
        assert row["password_hash"].startswith("$2b$")
        assert bcrypt.checkpw(b"pass1234", row["password_hash"].encode())

    def test_duplicate_login_id_raises(self, db_path):
        register_user(db_path, "user01", "pass1234", "田中")
        with pytest.raises(AuthError) as exc:
            register_user(db_path, "user01", "other123", "別人")
        assert exc.value.status_code == 409

    def test_password_too_short_raises(self, db_path):
        with pytest.raises(AuthError) as exc:
            register_user(db_path, "user02", "1234567", "名前")
        assert exc.value.status_code == 400

    def test_password_8_chars_is_accepted(self, db_path):
        result = register_user(db_path, "user03", "12345678", "名前")
        assert result["login_id"] == "user03"

    def test_empty_login_id_raises(self, db_path):
        with pytest.raises(AuthError) as exc:
            register_user(db_path, "", "pass1234", "名前")
        assert exc.value.status_code == 400

    def test_empty_display_name_raises(self, db_path):
        with pytest.raises(AuthError) as exc:
            register_user(db_path, "user04", "pass1234", "")
        assert exc.value.status_code == 400

    def test_email_is_optional(self, db_path):
        result = register_user(db_path, "user05", "pass1234", "名前")
        assert result["login_id"] == "user05"

    def test_email_stored_when_provided(self, db_path):
        register_user(db_path, "user06", "pass1234", "名前", email="a@b.com")
        from lib.db import get_connection
        row = get_connection(db_path).execute(
            "SELECT email FROM users WHERE login_id='user06'"
        ).fetchone()
        assert row["email"] == "a@b.com"

    def test_default_role_is_user(self, db_path):
        result = register_user(db_path, "user07", "pass1234", "名前")
        assert result["role"] == "user"


# ---------------------------------------------------------------------------
# TC-AUTH-LOGIN: ログイン
# ---------------------------------------------------------------------------
class TestLogin:
    def test_normal_login(self, db_path):
        register_user(db_path, "user01", "pass1234", "田中")
        result = login_user(db_path, "user01", "pass1234", ip="127.0.0.1")
        assert "session_token" in result
        assert len(result["session_token"]) >= 40  # ~43 chars
        assert result["user_id"] > 0
        assert result["display_name"] == "田中"

    def test_session_token_is_urlsafe(self, db_path):
        import re
        register_user(db_path, "u1", "pass1234", "U")
        result = login_user(db_path, "u1", "pass1234", ip="127.0.0.1")
        token = result["session_token"]
        assert re.match(r'^[A-Za-z0-9_\-]+$', token)

    def test_wrong_password_raises_401(self, db_path):
        register_user(db_path, "u1", "pass1234", "U")
        with pytest.raises(AuthError) as exc:
            login_user(db_path, "u1", "wrongpass", ip="127.0.0.1")
        assert exc.value.status_code == 401

    def test_five_failures_lock_by_login_id(self, db_path):
        register_user(db_path, "u1", "pass1234", "U")
        for _ in range(5):
            try:
                login_user(db_path, "u1", "bad", ip="1.2.3.4")
            except AuthError:
                pass
        with pytest.raises(AuthError) as exc:
            login_user(db_path, "u1", "pass1234", ip="1.2.3.4")
        assert exc.value.status_code == 429

    def test_locked_user_cannot_login_with_correct_password(self, db_path):
        register_user(db_path, "u1", "pass1234", "U")
        for _ in range(5):
            try:
                login_user(db_path, "u1", "bad", ip="9.9.9.9")
            except AuthError:
                pass
        with pytest.raises(AuthError) as exc:
            login_user(db_path, "u1", "pass1234", ip="9.9.9.9")
        assert exc.value.status_code == 429

    def test_inactive_user_cannot_login(self, db_path):
        register_user(db_path, "u1", "pass1234", "U")
        from lib.db import get_connection
        get_connection(db_path).execute(
            "UPDATE users SET is_active=0 WHERE login_id='u1'"
        ).connection.commit()
        with pytest.raises(AuthError) as exc:
            login_user(db_path, "u1", "pass1234", ip="127.0.0.1")
        assert exc.value.status_code == 403

    def test_last_login_at_updated(self, db_path):
        register_user(db_path, "u1", "pass1234", "U")
        login_user(db_path, "u1", "pass1234", ip="127.0.0.1")
        from lib.db import get_connection
        row = get_connection(db_path).execute(
            "SELECT last_login_at FROM users WHERE login_id='u1'"
        ).fetchone()
        assert row["last_login_at"] is not None

    def test_empty_login_id_raises_400(self, db_path):
        with pytest.raises(AuthError) as exc:
            login_user(db_path, "", "pass", ip="127.0.0.1")
        assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# TC-AUTH-SES: セッション確認
# ---------------------------------------------------------------------------
class TestSession:
    def test_valid_session(self, db_path):
        register_user(db_path, "u1", "pass1234", "U")
        res = login_user(db_path, "u1", "pass1234", ip="127.0.0.1")
        user = check_session(db_path, res["session_token"])
        assert user["login_id"] == "u1"

    def test_invalid_token_raises_401(self, db_path):
        with pytest.raises(AuthError) as exc:
            check_session(db_path, "invalid_token_xyz")
        assert exc.value.status_code == 401

    def test_expired_session_raises_401(self, db_path):
        register_user(db_path, "u1", "pass1234", "U")
        res = login_user(db_path, "u1", "pass1234", ip="127.0.0.1")
        # Expire the token
        from lib.db import get_connection
        conn = get_connection(db_path)
        conn.execute(
            "UPDATE sessions SET expires_at='2020-01-01T00:00:00Z' WHERE session_token=?",
            (res["session_token"],),
        )
        conn.commit()
        with pytest.raises(AuthError) as exc:
            check_session(db_path, res["session_token"])
        assert exc.value.status_code == 401

    def test_sliding_expiry_updated_on_check(self, db_path):
        register_user(db_path, "u1", "pass1234", "U")
        res = login_user(db_path, "u1", "pass1234", ip="127.0.0.1")
        from lib.db import get_connection
        before = get_connection(db_path).execute(
            "SELECT expires_at FROM sessions WHERE session_token=?",
            (res["session_token"],),
        ).fetchone()["expires_at"]
        check_session(db_path, res["session_token"])
        after = get_connection(db_path).execute(
            "SELECT expires_at FROM sessions WHERE session_token=?",
            (res["session_token"],),
        ).fetchone()["expires_at"]
        # expires_at should be >= before (renewed)
        assert after >= before


# ---------------------------------------------------------------------------
# TC-AUTH-LGT: ログアウト
# ---------------------------------------------------------------------------
class TestLogout:
    def test_logout_removes_session(self, db_path):
        register_user(db_path, "u1", "pass1234", "U")
        res = login_user(db_path, "u1", "pass1234", ip="127.0.0.1")
        logout_user(db_path, res["session_token"])
        with pytest.raises(AuthError) as exc:
            check_session(db_path, res["session_token"])
        assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# TC-AUTH-CHPW: パスワード変更
# ---------------------------------------------------------------------------
class TestChangePassword:
    def test_normal_change(self, db_path):
        register_user(db_path, "u1", "pass1234", "U")
        res = login_user(db_path, "u1", "pass1234", ip="127.0.0.1")
        change_password(db_path, res["session_token"], "pass1234", "newpass99")
        # New password works
        res2 = login_user(db_path, "u1", "newpass99", ip="127.0.0.1")
        assert "session_token" in res2

    def test_old_password_no_longer_works(self, db_path):
        register_user(db_path, "u1", "pass1234", "U")
        res = login_user(db_path, "u1", "pass1234", ip="127.0.0.1")
        change_password(db_path, res["session_token"], "pass1234", "newpass99")
        with pytest.raises(AuthError) as exc:
            login_user(db_path, "u1", "pass1234", ip="127.0.0.1")
        assert exc.value.status_code == 401

    def test_wrong_old_password_raises_401(self, db_path):
        register_user(db_path, "u1", "pass1234", "U")
        res = login_user(db_path, "u1", "pass1234", ip="127.0.0.1")
        with pytest.raises(AuthError) as exc:
            change_password(db_path, res["session_token"], "wrongold", "newpass99")
        assert exc.value.status_code == 401

    def test_new_password_too_short_raises_400(self, db_path):
        register_user(db_path, "u1", "pass1234", "U")
        res = login_user(db_path, "u1", "pass1234", ip="127.0.0.1")
        with pytest.raises(AuthError) as exc:
            change_password(db_path, res["session_token"], "pass1234", "short")
        assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# TC-ADMIN-U-09: Admin reset_password
# ---------------------------------------------------------------------------
class TestResetPassword:
    def test_reset_password_allows_new_login(self, db_path):
        register_user(db_path, "u1", "pass1234", "U")
        new_pw = reset_password(db_path, login_id="u1")
        assert len(new_pw) >= 12
        res = login_user(db_path, "u1", new_pw, ip="127.0.0.1")
        assert "session_token" in res

    def test_reset_password_invalidates_old(self, db_path):
        register_user(db_path, "u1", "pass1234", "U")
        reset_password(db_path, login_id="u1")
        with pytest.raises(AuthError):
            login_user(db_path, "u1", "pass1234", ip="127.0.0.1")
