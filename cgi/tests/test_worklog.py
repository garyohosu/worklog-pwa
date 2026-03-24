"""Tests for lib/worklog.py — TC-WLOG-* test cases."""
import uuid
import pytest
from lib.auth import register_user, login_user
from lib.worklog import (
    create_worklog,
    get_worklogs,
    get_worklog_detail,
    update_worklog,
    delete_worklog,
    sync_push,
    sync_pull,
    WorkLogError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _reg_login(db_path, login_id="u1", pw="pass1234", name="U", role="user"):
    register_user(db_path, login_id, pw, name)
    if role == "admin":
        from lib.db import get_connection
        get_connection(db_path).execute(
            "UPDATE users SET role='admin' WHERE login_id=?", (login_id,)
        ).connection.commit()
    return login_user(db_path, login_id, pw, ip="127.0.0.1")


def _new_uuid():
    return str(uuid.uuid4())


def _base_fields(**overrides):
    fields = {
        "log_uuid": _new_uuid(),
        "record_type": "inspection",
        "status": "open",
        "title": "点検記録",
        "recorded_at": "2026-01-01T09:00:00Z",
    }
    fields.update(overrides)
    return fields


# ---------------------------------------------------------------------------
# TC-WLOG-C: 新規作成（オンライン）
# ---------------------------------------------------------------------------
class TestCreateWorklog:
    def test_normal_create_with_equipment(self, db_path):
        sess = _reg_login(db_path)
        from lib.db import get_connection
        now = "2026-01-01T00:00:00Z"
        get_connection(db_path).execute(
            "INSERT INTO equipment (equipment_code, equipment_name, is_active, created_at, updated_at) VALUES (?,?,?,?,?)",
            ("MC-001", "Machine 1", 1, now, now),
        ).connection.commit()
        eq_id = get_connection(db_path).execute("SELECT id FROM equipment WHERE equipment_code='MC-001'").fetchone()["id"]

        fields = _base_fields(equipment_id=eq_id)
        result = create_worklog(db_path, user_id=sess["user_id"], fields=fields)
        assert result["log_uuid"] == fields["log_uuid"]
        assert result["revision"] == 1
        assert result["user_id"] == sess["user_id"]

    def test_equipment_id_null_allowed(self, db_path):
        sess = _reg_login(db_path)
        fields = _base_fields(record_type="memo")
        result = create_worklog(db_path, user_id=sess["user_id"], fields=fields)
        assert result["equipment_id"] is None

    def test_user_id_in_fields_rejected(self, db_path):
        sess = _reg_login(db_path)
        fields = _base_fields()
        fields["user_id"] = 99
        with pytest.raises(WorkLogError) as exc:
            create_worklog(db_path, user_id=sess["user_id"], fields=fields)
        assert exc.value.status_code == 400

    def test_revision_in_fields_rejected(self, db_path):
        sess = _reg_login(db_path)
        fields = _base_fields()
        fields["revision"] = 5
        with pytest.raises(WorkLogError) as exc:
            create_worklog(db_path, user_id=sess["user_id"], fields=fields)
        assert exc.value.status_code == 400

    def test_empty_title_raises_400(self, db_path):
        sess = _reg_login(db_path)
        fields = _base_fields(title="")
        with pytest.raises(WorkLogError) as exc:
            create_worklog(db_path, user_id=sess["user_id"], fields=fields)
        assert exc.value.status_code == 400

    def test_invalid_record_type_raises_400(self, db_path):
        sess = _reg_login(db_path)
        fields = _base_fields(record_type="unknown")
        with pytest.raises(WorkLogError) as exc:
            create_worklog(db_path, user_id=sess["user_id"], fields=fields)
        assert exc.value.status_code == 400

    def test_invalid_status_raises_400(self, db_path):
        sess = _reg_login(db_path)
        fields = _base_fields(status="archived")
        with pytest.raises(WorkLogError) as exc:
            create_worklog(db_path, user_id=sess["user_id"], fields=fields)
        assert exc.value.status_code == 400

    def test_priority_null_allowed(self, db_path):
        sess = _reg_login(db_path)
        fields = _base_fields()
        result = create_worklog(db_path, user_id=sess["user_id"], fields=fields)
        assert result["priority"] is None

    def test_priority_critical(self, db_path):
        sess = _reg_login(db_path)
        fields = _base_fields(priority="critical")
        result = create_worklog(db_path, user_id=sess["user_id"], fields=fields)
        assert result["priority"] == "critical"

    def test_priority_invalid_raises_400(self, db_path):
        sess = _reg_login(db_path)
        fields = _base_fields(priority="urgent")
        with pytest.raises(WorkLogError) as exc:
            create_worklog(db_path, user_id=sess["user_id"], fields=fields)
        assert exc.value.status_code == 400

    def test_created_by_set_to_caller(self, db_path):
        sess = _reg_login(db_path)
        fields = _base_fields()
        result = create_worklog(db_path, user_id=sess["user_id"], fields=fields)
        assert result["created_by"] == sess["user_id"]
        assert result["updated_by"] == sess["user_id"]


# ---------------------------------------------------------------------------
# TC-WLOG-LST: 一覧
# ---------------------------------------------------------------------------
class TestListWorklog:
    def test_user_sees_own_records_only(self, db_path):
        s1 = _reg_login(db_path, "u1")
        s2 = _reg_login(db_path, "u2")
        create_worklog(db_path, s1["user_id"], _base_fields(title="U1 record"))
        create_worklog(db_path, s2["user_id"], _base_fields(title="U2 record"))
        items, total, _ = get_worklogs(db_path, user_id=s1["user_id"], role="user")
        assert all(r["user_id"] == s1["user_id"] for r in items)
        assert total == 1

    def test_admin_sees_all_records(self, db_path):
        s1 = _reg_login(db_path, "u1")
        s2 = _reg_login(db_path, "u2")
        sa = _reg_login(db_path, "admin1", role="admin")
        create_worklog(db_path, s1["user_id"], _base_fields(title="U1"))
        create_worklog(db_path, s2["user_id"], _base_fields(title="U2"))
        items, total, _ = get_worklogs(db_path, user_id=sa["user_id"], role="admin")
        assert total == 2

    def test_deleted_excluded_by_default(self, db_path):
        sess = _reg_login(db_path)
        f = _base_fields()
        create_worklog(db_path, sess["user_id"], f)
        delete_worklog(db_path, f["log_uuid"], sess["user_id"])
        items, total, _ = get_worklogs(db_path, sess["user_id"], "user")
        assert total == 0

    def test_admin_can_include_deleted(self, db_path):
        s1 = _reg_login(db_path, "u1")
        sa = _reg_login(db_path, "admin1", role="admin")
        f = _base_fields()
        create_worklog(db_path, s1["user_id"], f)
        delete_worklog(db_path, f["log_uuid"], s1["user_id"])
        items, total, _ = get_worklogs(
            db_path, sa["user_id"], "admin", include_deleted=True
        )
        assert total == 1

    def test_user_cannot_include_deleted(self, db_path):
        sess = _reg_login(db_path)
        with pytest.raises(WorkLogError) as exc:
            get_worklogs(db_path, sess["user_id"], "user", include_deleted=True)
        assert exc.value.status_code == 403

    def test_pagination_page_size(self, db_path):
        sess = _reg_login(db_path)
        for i in range(55):
            create_worklog(db_path, sess["user_id"], _base_fields(title=f"T{i}"))
        items, total, has_next = get_worklogs(
            db_path, sess["user_id"], "user", page=1, page_size=50
        )
        assert len(items) == 50
        assert total == 55
        assert has_next is True

    def test_pagination_second_page(self, db_path):
        sess = _reg_login(db_path)
        for i in range(55):
            create_worklog(db_path, sess["user_id"], _base_fields(title=f"T{i}"))
        items, total, has_next = get_worklogs(
            db_path, sess["user_id"], "user", page=2, page_size=50
        )
        assert len(items) == 5
        assert has_next is False


# ---------------------------------------------------------------------------
# TC-WLOG-ED: 編集
# ---------------------------------------------------------------------------
class TestUpdateWorklog:
    def test_normal_update(self, db_path):
        sess = _reg_login(db_path)
        f = _base_fields()
        create_worklog(db_path, sess["user_id"], f)
        result = update_worklog(
            db_path, f["log_uuid"], base_revision=1,
            fields={"title": "更新後"},
            actor_id=sess["user_id"], actor_role="user",
        )
        assert result["title"] == "更新後"
        assert result["revision"] == 2
        assert result["updated_by"] == sess["user_id"]

    def test_admin_can_edit_others_record(self, db_path):
        s1 = _reg_login(db_path, "u1")
        sa = _reg_login(db_path, "admin1", role="admin")
        f = _base_fields()
        create_worklog(db_path, s1["user_id"], f)
        result = update_worklog(
            db_path, f["log_uuid"], base_revision=1,
            fields={"title": "Admin edit"},
            actor_id=sa["user_id"], actor_role="admin",
        )
        assert result["updated_by"] == sa["user_id"]

    def test_user_cannot_edit_others_record(self, db_path):
        s1 = _reg_login(db_path, "u1")
        s2 = _reg_login(db_path, "u2")
        f = _base_fields()
        create_worklog(db_path, s1["user_id"], f)
        with pytest.raises(WorkLogError) as exc:
            update_worklog(
                db_path, f["log_uuid"], base_revision=1,
                fields={"title": "hack"},
                actor_id=s2["user_id"], actor_role="user",
            )
        assert exc.value.status_code == 403

    def test_forbidden_field_in_update_rejected(self, db_path):
        sess = _reg_login(db_path)
        f = _base_fields()
        create_worklog(db_path, sess["user_id"], f)
        with pytest.raises(WorkLogError) as exc:
            update_worklog(
                db_path, f["log_uuid"], base_revision=1,
                fields={"updated_by": 99, "title": "x"},
                actor_id=sess["user_id"], actor_role="user",
            )
        assert exc.value.status_code == 400

    def test_offline_edit_state_not_in_fields(self, db_path):
        """sync_state in fields is rejected."""
        sess = _reg_login(db_path)
        f = _base_fields()
        create_worklog(db_path, sess["user_id"], f)
        with pytest.raises(WorkLogError) as exc:
            update_worklog(
                db_path, f["log_uuid"], base_revision=1,
                fields={"sync_state": "dirty", "title": "x"},
                actor_id=sess["user_id"], actor_role="user",
            )
        assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# TC-WLOG-CF: 競合 (409)
# ---------------------------------------------------------------------------
class TestConflict:
    def test_revision_mismatch_raises_409(self, db_path):
        sess = _reg_login(db_path)
        f = _base_fields()
        create_worklog(db_path, sess["user_id"], f)
        with pytest.raises(WorkLogError) as exc:
            update_worklog(
                db_path, f["log_uuid"], base_revision=99,
                fields={"title": "conflict attempt"},
                actor_id=sess["user_id"], actor_role="user",
            )
        assert exc.value.status_code == 409
        assert exc.value.server_entity is not None

    def test_correct_revision_after_conflict(self, db_path):
        sess = _reg_login(db_path)
        f = _base_fields()
        create_worklog(db_path, sess["user_id"], f)
        # revision is 1
        result = update_worklog(
            db_path, f["log_uuid"], base_revision=1,
            fields={"title": "ok"},
            actor_id=sess["user_id"], actor_role="user",
        )
        assert result["revision"] == 2


# ---------------------------------------------------------------------------
# TC-WLOG-DEL: 論理削除
# ---------------------------------------------------------------------------
class TestDeleteWorklog:
    def test_logical_delete(self, db_path):
        sess = _reg_login(db_path)
        f = _base_fields()
        create_worklog(db_path, sess["user_id"], f)
        result = delete_worklog(db_path, f["log_uuid"], actor_id=sess["user_id"])
        assert result["deleted_flag"] == 1
        assert result["deleted_at"] is not None
        assert result["deleted_by"] == sess["user_id"]
        assert result["revision"] == 2

    def test_record_still_exists_in_db(self, db_path):
        sess = _reg_login(db_path)
        f = _base_fields()
        create_worklog(db_path, sess["user_id"], f)
        delete_worklog(db_path, f["log_uuid"], sess["user_id"])
        from lib.db import get_connection
        row = get_connection(db_path).execute(
            "SELECT * FROM work_logs WHERE log_uuid=?", (f["log_uuid"],)
        ).fetchone()
        assert row is not None
        assert row["deleted_flag"] == 1

    def test_admin_can_delete_others(self, db_path):
        s1 = _reg_login(db_path, "u1")
        sa = _reg_login(db_path, "admin1", role="admin")
        f = _base_fields()
        create_worklog(db_path, s1["user_id"], f)
        result = delete_worklog(db_path, f["log_uuid"], actor_id=sa["user_id"], actor_role="admin")
        assert result["deleted_by"] == sa["user_id"]

    def test_user_cannot_delete_others(self, db_path):
        s1 = _reg_login(db_path, "u1")
        s2 = _reg_login(db_path, "u2")
        f = _base_fields()
        create_worklog(db_path, s1["user_id"], f)
        with pytest.raises(WorkLogError) as exc:
            delete_worklog(db_path, f["log_uuid"], actor_id=s2["user_id"])
        assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# TC-SYNC-PUSH: Sync Push
# ---------------------------------------------------------------------------
class TestSyncPush:
    def test_create_operation(self, db_path):
        sess = _reg_login(db_path)
        log_uuid = _new_uuid()
        items = [{
            "operation": "create",
            "entity": {
                "log_uuid": log_uuid,
                "fields": {
                    "record_type": "inspection",
                    "status": "open",
                    "title": "Pushed",
                    "recorded_at": "2026-01-01T09:00:00Z",
                },
            },
        }]
        results = sync_push(db_path, items, sess["user_id"])
        assert results[0]["status"] == "ok"
        assert results[0]["revision"] >= 1

    def test_update_operation_success(self, db_path):
        sess = _reg_login(db_path)
        f = _base_fields()
        create_worklog(db_path, sess["user_id"], f)
        items = [{
            "operation": "update",
            "entity": {
                "log_uuid": f["log_uuid"],
                "base_revision": 1,
                "fields": {"status": "done"},
            },
        }]
        results = sync_push(db_path, items, sess["user_id"])
        assert results[0]["status"] == "ok"
        assert results[0]["revision"] == 2

    def test_update_operation_conflict(self, db_path):
        sess = _reg_login(db_path)
        f = _base_fields()
        create_worklog(db_path, sess["user_id"], f)
        items = [{
            "operation": "update",
            "entity": {
                "log_uuid": f["log_uuid"],
                "base_revision": 99,
                "fields": {"status": "done"},
            },
        }]
        results = sync_push(db_path, items, sess["user_id"])
        assert results[0]["status"] == "conflict"
        assert results[0]["server_revision"] == 1

    def test_delete_operation(self, db_path):
        sess = _reg_login(db_path)
        f = _base_fields()
        create_worklog(db_path, sess["user_id"], f)
        items = [{
            "operation": "delete",
            "entity": {"log_uuid": f["log_uuid"], "base_revision": 1},
        }]
        results = sync_push(db_path, items, sess["user_id"])
        assert results[0]["status"] == "ok"

    def test_create_with_forbidden_field_rejected(self, db_path):
        sess = _reg_login(db_path)
        items = [{
            "operation": "create",
            "entity": {
                "log_uuid": _new_uuid(),
                "fields": {
                    "record_type": "inspection",
                    "status": "open",
                    "title": "test",
                    "recorded_at": "2026-01-01T09:00:00Z",
                    "user_id": 99,
                },
            },
        }]
        results = sync_push(db_path, items, sess["user_id"])
        assert results[0]["status"] == "error"

    def test_update_missing_base_revision_rejected(self, db_path):
        sess = _reg_login(db_path)
        f = _base_fields()
        create_worklog(db_path, sess["user_id"], f)
        items = [{
            "operation": "update",
            "entity": {"log_uuid": f["log_uuid"], "fields": {"status": "done"}},
        }]
        results = sync_push(db_path, items, sess["user_id"])
        assert results[0]["status"] == "error"

    def test_delete_missing_base_revision_rejected(self, db_path):
        sess = _reg_login(db_path)
        f = _base_fields()
        create_worklog(db_path, sess["user_id"], f)
        items = [{"operation": "delete", "entity": {"log_uuid": f["log_uuid"]}}]
        results = sync_push(db_path, items, sess["user_id"])
        assert results[0]["status"] == "error"

    def test_bulk_push_multiple_items(self, db_path):
        sess = _reg_login(db_path)
        items = []
        for _ in range(3):
            items.append({
                "operation": "create",
                "entity": {
                    "log_uuid": _new_uuid(),
                    "fields": {
                        "record_type": "memo",
                        "status": "open",
                        "title": "Bulk",
                        "recorded_at": "2026-01-01T09:00:00Z",
                    },
                },
            })
        results = sync_push(db_path, items, sess["user_id"])
        assert len(results) == 3
        assert all(r["status"] == "ok" for r in results)


# ---------------------------------------------------------------------------
# TC-SYNC-PULL: Sync Pull
# ---------------------------------------------------------------------------
class TestSyncPull:
    def test_initial_pull_returns_all(self, db_path):
        sess = _reg_login(db_path)
        create_worklog(db_path, sess["user_id"], _base_fields(title="A"))
        create_worklog(db_path, sess["user_id"], _base_fields(title="B"))
        items, next_token = sync_pull(db_path, sess["user_id"], "user", since_token=None)
        assert len(items) == 2
        assert next_token is not None

    def test_pull_includes_tombstone(self, db_path):
        sess = _reg_login(db_path)
        f = _base_fields()
        create_worklog(db_path, sess["user_id"], f)
        delete_worklog(db_path, f["log_uuid"], sess["user_id"])
        items, _ = sync_pull(db_path, sess["user_id"], "user", since_token=None)
        deleted_items = [i for i in items if i["deleted_flag"] == 1]
        assert len(deleted_items) == 1

    def test_user_pulls_only_own_records(self, db_path):
        s1 = _reg_login(db_path, "u1")
        s2 = _reg_login(db_path, "u2")
        create_worklog(db_path, s1["user_id"], _base_fields(title="U1"))
        create_worklog(db_path, s2["user_id"], _base_fields(title="U2"))
        items, _ = sync_pull(db_path, s1["user_id"], "user", since_token=None)
        assert all(r["user_id"] == s1["user_id"] for r in items)

    def test_admin_pulls_all_records(self, db_path):
        s1 = _reg_login(db_path, "u1")
        s2 = _reg_login(db_path, "u2")
        sa = _reg_login(db_path, "admin1", role="admin")
        create_worklog(db_path, s1["user_id"], _base_fields(title="U1"))
        create_worklog(db_path, s2["user_id"], _base_fields(title="U2"))
        items, _ = sync_pull(db_path, sa["user_id"], "admin", since_token=None)
        assert len(items) == 2

    def test_pull_dto_has_no_local_fields(self, db_path):
        sess = _reg_login(db_path)
        create_worklog(db_path, sess["user_id"], _base_fields())
        items, _ = sync_pull(db_path, sess["user_id"], "user", since_token=None)
        for item in items:
            assert "local_updated_at" not in item
            assert "sync_state" not in item
