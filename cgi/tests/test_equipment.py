"""Tests for lib/equipment.py — TC-EQ-* test cases."""
import pytest
from lib.auth import register_user, login_user
from lib.equipment import (
    list_equipment,
    search_equipment,
    get_by_qr,
    create_equipment,
    update_equipment,
    sync_pull_equipment,
    EquipmentError,
)


def _reg_login(db_path, login_id="u1", pw="pass1234", name="U", role="user"):
    register_user(db_path, login_id, pw, name)
    if role == "admin":
        from lib.db import get_connection
        get_connection(db_path).execute(
            "UPDATE users SET role='admin' WHERE login_id=?", (login_id,)
        ).connection.commit()
    return login_user(db_path, login_id, pw, ip="127.0.0.1")


def _insert_equipment(db_path, code="MC-001", name="Machine1", is_active=1, qr_value=None):
    from lib.db import get_connection
    now = "2026-01-01T00:00:00Z"
    qr = qr_value or code
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO equipment (equipment_code, equipment_name, qr_value, is_active, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?)",
        (code, name, qr, is_active, now, now),
    )
    conn.commit()
    return conn.execute("SELECT * FROM equipment WHERE equipment_code=?", (code,)).fetchone()


# ---------------------------------------------------------------------------
# TC-EQ-QR: QR scan
# ---------------------------------------------------------------------------
class TestQR:
    def test_qr_cache_hit_active(self, db_path):
        _insert_equipment(db_path, "MC-001", is_active=1)
        eq = get_by_qr(db_path, "MC-001")
        assert eq["equipment_code"] == "MC-001"
        assert eq["is_active"] == 1

    def test_qr_cache_hit_inactive(self, db_path):
        _insert_equipment(db_path, "MC-002", is_active=0)
        with pytest.raises(EquipmentError) as exc:
            get_by_qr(db_path, "MC-002")
        assert exc.value.status_code == 422  # found but inactive

    def test_qr_not_found(self, db_path):
        with pytest.raises(EquipmentError) as exc:
            get_by_qr(db_path, "NOTEXIST")
        assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# TC-EQ-MASTER: 設備マスタ
# ---------------------------------------------------------------------------
class TestEquipmentMaster:
    def test_admin_can_create(self, db_path):
        _reg_login(db_path, "admin1", role="admin")
        eq = create_equipment(db_path, actor_role="admin", data={
            "equipment_code": "MC-001",
            "equipment_name": "Machine 1",
        })
        assert eq["equipment_code"] == "MC-001"

    def test_user_cannot_create(self, db_path):
        with pytest.raises(EquipmentError) as exc:
            create_equipment(db_path, actor_role="user", data={
                "equipment_code": "MC-001",
                "equipment_name": "Machine 1",
            })
        assert exc.value.status_code == 403

    def test_duplicate_code_raises_409(self, db_path):
        _insert_equipment(db_path, "MC-001")
        with pytest.raises(EquipmentError) as exc:
            create_equipment(db_path, actor_role="admin", data={
                "equipment_code": "MC-001",
                "equipment_name": "Dup",
            })
        assert exc.value.status_code == 409

    def test_empty_code_raises_400(self, db_path):
        with pytest.raises(EquipmentError) as exc:
            create_equipment(db_path, actor_role="admin", data={
                "equipment_code": "",
                "equipment_name": "X",
            })
        assert exc.value.status_code == 400

    def test_update_sets_is_active_false(self, db_path):
        _insert_equipment(db_path, "MC-001")
        eq = update_equipment(db_path, "MC-001", actor_role="admin", data={"is_active": 0})
        assert eq["is_active"] == 0

    def test_user_cannot_update(self, db_path):
        _insert_equipment(db_path, "MC-001")
        with pytest.raises(EquipmentError) as exc:
            update_equipment(db_path, "MC-001", actor_role="user", data={"is_active": 0})
        assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# TC-EQ-SYNC: 設備同期
# ---------------------------------------------------------------------------
class TestEquipmentSync:
    def test_list_all(self, db_path):
        _insert_equipment(db_path, "A1")
        _insert_equipment(db_path, "A2")
        items = list_equipment(db_path)
        assert len(items) == 2

    def test_sync_pull_no_token_returns_all(self, db_path):
        _insert_equipment(db_path, "A1", name="N1")
        items, next_token = sync_pull_equipment(db_path, since_token=None)
        assert len(items) == 1
        assert next_token is not None

    def test_sync_pull_includes_inactive(self, db_path):
        _insert_equipment(db_path, "A1", is_active=1)
        _insert_equipment(db_path, "A2", is_active=0)
        items, _ = sync_pull_equipment(db_path, since_token=None)
        assert len(items) == 2
        inactive = [i for i in items if i["is_active"] == 0]
        assert len(inactive) == 1

    def test_search_by_name(self, db_path):
        _insert_equipment(db_path, "MC-001", "プレス機")
        _insert_equipment(db_path, "MC-002", "旋盤")
        results = search_equipment(db_path, q="プレス")
        assert len(results) == 1
        assert results[0]["equipment_code"] == "MC-001"
