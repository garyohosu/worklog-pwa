"""WorkLog business logic."""
from datetime import datetime, timezone
from .db import get_connection
from .validator import (
    validate_title,
    validate_record_type,
    validate_status,
    validate_priority,
    validate_uuid,
    validate_base_revision,
    validate_forbidden_fields,
    collect_errors,
)

WORKLOG_DTO_FIELDS = (
    "log_uuid", "user_id", "equipment_id", "record_type", "status", "title",
    "symptom", "work_detail", "result", "priority", "recorded_at",
    "needs_followup", "followup_due", "revision", "server_updated_at",
    "created_by", "updated_by", "deleted_flag", "deleted_at", "deleted_by",
)


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_dto(row) -> dict:
    return {k: row[k] for k in WORKLOG_DTO_FIELDS if k in row.keys()}


class WorkLogError(Exception):
    def __init__(self, message: str, status_code: int = 400, server_entity: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.server_entity = server_entity


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
def create_worklog(db_path: str, user_id: int, fields: dict) -> dict:
    # Forbidden field check
    if err := validate_forbidden_fields(fields):
        raise WorkLogError(err, 400)

    errors = collect_errors(
        uuid=validate_uuid(fields.get("log_uuid")),
        title=validate_title(fields.get("title")),
        record_type=validate_record_type(fields.get("record_type")),
        status=validate_status(fields.get("status")),
        priority=validate_priority(fields.get("priority")),
    )
    if errors:
        raise WorkLogError("; ".join(errors), 400)

    now = _now_utc()
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO work_logs ("
            "log_uuid, user_id, equipment_id, record_type, status, title, "
            "symptom, work_detail, result, priority, recorded_at, "
            "needs_followup, followup_due, server_updated_at, revision, "
            "created_by, updated_by, deleted_flag"
            ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                fields["log_uuid"],
                user_id,
                fields.get("equipment_id"),
                fields["record_type"],
                fields["status"],
                fields["title"],
                fields.get("symptom"),
                fields.get("work_detail"),
                fields.get("result"),
                fields.get("priority"),
                fields["recorded_at"],
                int(fields.get("needs_followup", 0)),
                fields.get("followup_due"),
                now,
                1,
                user_id,
                user_id,
                0,
            ),
        )
        conn.commit()
    except Exception as e:
        raise WorkLogError(str(e), 409)

    row = conn.execute(
        "SELECT * FROM work_logs WHERE log_uuid=?", (fields["log_uuid"],)
    ).fetchone()
    return _row_to_dto(row)


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------
def get_worklogs(
    db_path: str, user_id: int, role: str,
    include_deleted: bool = False, page: int = 1, page_size: int = 50,
) -> tuple:
    if include_deleted and role != "admin":
        raise WorkLogError("Forbidden: only admin can include deleted records", 403)

    conn = get_connection(db_path)
    conditions = []
    params = []

    if role != "admin":
        conditions.append("user_id=?")
        params.append(user_id)

    if not include_deleted:
        conditions.append("deleted_flag=0")

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    total = conn.execute(f"SELECT COUNT(*) FROM work_logs {where}", params).fetchone()[0]

    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT * FROM work_logs {where} ORDER BY recorded_at DESC LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()

    items = [_row_to_dto(r) for r in rows]
    has_next = (offset + page_size) < total
    return items, total, has_next


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------
def get_worklog_detail(db_path: str, log_uuid: str, user_id: int, role: str) -> dict:
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT * FROM work_logs WHERE log_uuid=?", (log_uuid,)
    ).fetchone()
    if row is None:
        raise WorkLogError("Not found", 404)
    if role != "admin" and row["user_id"] != user_id:
        raise WorkLogError("Forbidden", 403)
    return _row_to_dto(row)


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------
def update_worklog(
    db_path: str, log_uuid: str, base_revision: int,
    fields: dict, actor_id: int, actor_role: str = "user",
) -> dict:
    if err := validate_forbidden_fields(fields):
        raise WorkLogError(err, 400)

    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT * FROM work_logs WHERE log_uuid=?", (log_uuid,)
    ).fetchone()
    if row is None:
        raise WorkLogError("Not found", 404)
    if actor_role != "admin" and row["user_id"] != actor_id:
        raise WorkLogError("Forbidden", 403)
    if row["revision"] != base_revision:
        raise WorkLogError("Conflict", 409, server_entity=_row_to_dto(row))

    # Build SET clause from allowed fields
    allowed = {
        "record_type", "status", "title", "symptom", "work_detail",
        "result", "priority", "recorded_at", "needs_followup", "followup_due",
        "equipment_id",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}

    # Validate any provided values
    errors = collect_errors(
        title=validate_title(updates["title"]) if "title" in updates else None,
        record_type=validate_record_type(updates["record_type"]) if "record_type" in updates else None,
        status=validate_status(updates["status"]) if "status" in updates else None,
        priority=validate_priority(updates.get("priority")) if "priority" in updates else None,
    )
    if errors:
        raise WorkLogError("; ".join(errors), 400)

    now = _now_utc()
    updates["updated_by"] = actor_id
    updates["revision"] = row["revision"] + 1
    updates["server_updated_at"] = now

    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [log_uuid]
    conn.execute(f"UPDATE work_logs SET {set_clause} WHERE log_uuid=?", values)
    conn.commit()

    row = conn.execute("SELECT * FROM work_logs WHERE log_uuid=?", (log_uuid,)).fetchone()
    return _row_to_dto(row)


# ---------------------------------------------------------------------------
# Delete (logical / tombstone)
# ---------------------------------------------------------------------------
def delete_worklog(
    db_path: str, log_uuid: str, actor_id: int, actor_role: str = "user"
) -> dict:
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT * FROM work_logs WHERE log_uuid=?", (log_uuid,)
    ).fetchone()
    if row is None:
        raise WorkLogError("Not found", 404)
    if actor_role != "admin" and row["user_id"] != actor_id:
        raise WorkLogError("Forbidden", 403)

    now = _now_utc()
    conn.execute(
        "UPDATE work_logs SET deleted_flag=1, deleted_at=?, deleted_by=?, "
        "revision=revision+1, server_updated_at=? WHERE log_uuid=?",
        (now, actor_id, now, log_uuid),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM work_logs WHERE log_uuid=?", (log_uuid,)).fetchone()
    return _row_to_dto(row)


# ---------------------------------------------------------------------------
# Sync Push
# ---------------------------------------------------------------------------
def sync_push(db_path: str, items: list, actor_id: int) -> list:
    results = []
    for item in items:
        operation = item.get("operation")
        entity = item.get("entity", {})
        log_uuid = entity.get("log_uuid")
        try:
            if operation == "create":
                _validate_no_base_revision_in_create(entity)
                fields = dict(entity.get("fields", {}))
                fields["log_uuid"] = log_uuid
                dto = create_worklog(db_path, actor_id, fields)
                results.append({"log_uuid": log_uuid, "status": "ok", "revision": dto["revision"]})

            elif operation == "update":
                base_rev = entity.get("base_revision")
                if err := validate_base_revision(base_rev):
                    raise WorkLogError(err, 400)
                fields = entity.get("fields", {})
                dto = update_worklog(
                    db_path, log_uuid, int(base_rev), fields,
                    actor_id=actor_id, actor_role="user",
                )
                results.append({"log_uuid": log_uuid, "status": "ok", "revision": dto["revision"]})

            elif operation == "delete":
                if entity.get("fields") is not None:
                    raise WorkLogError("delete operation must not include fields", 400)
                base_rev = entity.get("base_revision")
                if err := validate_base_revision(base_rev):
                    raise WorkLogError(err, 400)
                delete_worklog(db_path, log_uuid, actor_id)
                results.append({"log_uuid": log_uuid, "status": "ok"})

            else:
                results.append({"log_uuid": log_uuid, "status": "error", "message": "unknown operation"})

        except WorkLogError as e:
            if e.status_code == 409:
                results.append({
                    "log_uuid": log_uuid,
                    "status": "conflict",
                    "server_revision": e.server_entity["revision"] if e.server_entity else None,
                })
            else:
                results.append({"log_uuid": log_uuid, "status": "error", "message": e.message})

    return results


def _validate_no_base_revision_in_create(entity: dict):
    if "base_revision" in entity:
        raise WorkLogError("create operation must not include base_revision", 400)


# ---------------------------------------------------------------------------
# Sync Pull
# ---------------------------------------------------------------------------
def sync_pull(
    db_path: str, user_id: int, role: str, since_token: str = None
) -> tuple:
    conn = get_connection(db_path)
    conditions = []
    params = []

    if role != "admin":
        conditions.append("user_id=?")
        params.append(user_id)

    if since_token:
        conditions.append("server_updated_at>=?")
        params.append(since_token)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    rows = conn.execute(
        f"SELECT * FROM work_logs {where} ORDER BY server_updated_at ASC",
        params,
    ).fetchall()

    items = [_row_to_dto(r) for r in rows]
    if items:
        next_token = max(r["server_updated_at"] for r in items)
    else:
        next_token = since_token or _now_utc()

    return items, next_token
