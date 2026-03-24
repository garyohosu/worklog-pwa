"""Tests for lib/admin.py — TC-ADMIN-* test cases."""
import pytest
from lib.auth import register_user, login_user
from lib.admin import (
    list_users,
    set_active,
    set_role,
    get_dashboard,
    AdminError,
)


def _reg(db_path, login_id, pw="pass1234", name=None, role="user"):
    register_user(db_path, login_id, pw, name or login_id)
    if role == "admin":
        from lib.db import get_connection
        get_connection(db_path).execute(
            "UPDATE users SET role='admin' WHERE login_id=?", (login_id,)
        ).connection.commit()
    return login_user(db_path, login_id, pw, ip="127.0.0.1")


def _get_user(db_path, login_id):
    from lib.db import get_connection
    return get_connection(db_path).execute(
        "SELECT * FROM users WHERE login_id=?", (login_id,)
    ).fetchone()


# ---------------------------------------------------------------------------
# TC-ADMIN-U: ユーザー管理
# ---------------------------------------------------------------------------
class TestUserManagement:
    def test_admin_can_list_users(self, db_path):
        sa = _reg(db_path, "admin1", role="admin")
        _reg(db_path, "u1")
        users = list_users(db_path, actor_role="admin")
        assert len(users) >= 2

    def test_user_cannot_list_users(self, db_path):
        with pytest.raises(AdminError) as exc:
            list_users(db_path, actor_role="user")
        assert exc.value.status_code == 403

    def test_set_active_false(self, db_path):
        sa = _reg(db_path, "admin1", role="admin")
        _reg(db_path, "u1")
        u1 = _get_user(db_path, "u1")
        set_active(db_path, target_user_id=u1["id"], is_active=0,
                   actor_user_id=sa["user_id"], actor_role="admin")
        assert _get_user(db_path, "u1")["is_active"] == 0

    def test_set_active_true(self, db_path):
        sa = _reg(db_path, "admin1", role="admin")
        _reg(db_path, "u1")
        u1 = _get_user(db_path, "u1")
        set_active(db_path, u1["id"], 0, sa["user_id"], "admin")
        set_active(db_path, u1["id"], 1, sa["user_id"], "admin")
        assert _get_user(db_path, "u1")["is_active"] == 1

    def test_admin_cannot_deactivate_self(self, db_path):
        sa = _reg(db_path, "admin1", role="admin")
        with pytest.raises(AdminError) as exc:
            set_active(db_path, sa["user_id"], 0, sa["user_id"], "admin")
        assert exc.value.status_code == 400

    def test_user_cannot_set_active(self, db_path):
        _reg(db_path, "u1")
        _reg(db_path, "u2")
        u2 = _get_user(db_path, "u2")
        u1 = _get_user(db_path, "u1")
        with pytest.raises(AdminError) as exc:
            set_active(db_path, u2["id"], 0, u1["id"], "user")
        assert exc.value.status_code == 403

    def test_promote_to_admin(self, db_path):
        sa = _reg(db_path, "admin1", role="admin")
        _reg(db_path, "u1")
        u1 = _get_user(db_path, "u1")
        set_role(db_path, u1["id"], "admin", sa["user_id"], "admin")
        assert _get_user(db_path, "u1")["role"] == "admin"

    def test_demote_admin_to_user(self, db_path):
        sa1 = _reg(db_path, "admin1", role="admin")
        sa2 = _reg(db_path, "admin2", role="admin")
        a2 = _get_user(db_path, "admin2")
        set_role(db_path, a2["id"], "user", sa1["user_id"], "admin")
        assert _get_user(db_path, "admin2")["role"] == "user"

    def test_cannot_demote_last_admin(self, db_path):
        sa = _reg(db_path, "admin1", role="admin")
        with pytest.raises(AdminError) as exc:
            set_role(db_path, sa["user_id"], "user", sa["user_id"], "admin")
        assert exc.value.status_code == 400

    def test_user_cannot_change_role(self, db_path):
        _reg(db_path, "u1")
        _reg(db_path, "u2")
        u1 = _get_user(db_path, "u1")
        u2 = _get_user(db_path, "u2")
        with pytest.raises(AdminError) as exc:
            set_role(db_path, u2["id"], "admin", u1["id"], "user")
        assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# TC-ADMIN-DASH: ダッシュボード
# ---------------------------------------------------------------------------
class TestDashboard:
    def test_admin_gets_dashboard(self, db_path):
        _reg(db_path, "admin1", role="admin")
        data = get_dashboard(db_path, actor_role="admin")
        assert "total_by_period" in data
        assert "by_status" in data
        assert "by_record_type" in data
        assert "followup_overdue" in data

    def test_user_cannot_get_dashboard(self, db_path):
        with pytest.raises(AdminError) as exc:
            get_dashboard(db_path, actor_role="user")
        assert exc.value.status_code == 403

    def test_dashboard_counts_are_integers(self, db_path):
        _reg(db_path, "admin1", role="admin")
        data = get_dashboard(db_path, actor_role="admin")
        assert isinstance(data["total_by_period"]["today"], int)
        assert isinstance(data["followup_overdue"], int)
