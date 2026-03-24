"""Equipment business logic."""
from datetime import datetime, timezone
from .db import get_connection


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_dict(row) -> dict:
    return dict(row)


class EquipmentError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def list_equipment(db_path: str) -> list:
    conn = get_connection(db_path)
    rows = conn.execute("SELECT * FROM equipment ORDER BY equipment_code").fetchall()
    return [_row_to_dict(r) for r in rows]


def search_equipment(db_path: str, q: str) -> list:
    conn = get_connection(db_path)
    pattern = f"%{q}%"
    rows = conn.execute(
        "SELECT * FROM equipment WHERE equipment_name LIKE ? OR equipment_code LIKE ? ORDER BY equipment_code",
        (pattern, pattern),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_by_qr(db_path: str, qr_value: str) -> dict:
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT * FROM equipment WHERE qr_value=?", (qr_value,)
    ).fetchone()
    if row is None:
        raise EquipmentError("Equipment not found", 404)
    if not row["is_active"]:
        raise EquipmentError("Equipment is inactive", 422)
    return _row_to_dict(row)


def create_equipment(db_path: str, actor_role: str, data: dict) -> dict:
    if actor_role != "admin":
        raise EquipmentError("Forbidden", 403)

    code = data.get("equipment_code", "").strip()
    if not code:
        raise EquipmentError("equipment_code is required", 400)

    now = _now_utc()
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO equipment (equipment_code, equipment_name, location, line_name, model, maker, "
            "qr_value, is_active, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                code,
                data.get("equipment_name", ""),
                data.get("location"),
                data.get("line_name"),
                data.get("model"),
                data.get("maker"),
                data.get("qr_value", code),
                int(data.get("is_active", 1)),
                now,
                now,
            ),
        )
        conn.commit()
    except Exception:
        raise EquipmentError(f"equipment_code '{code}' already exists", 409)

    row = conn.execute("SELECT * FROM equipment WHERE equipment_code=?", (code,)).fetchone()
    return _row_to_dict(row)


def update_equipment(db_path: str, equipment_code: str, actor_role: str, data: dict) -> dict:
    if actor_role != "admin":
        raise EquipmentError("Forbidden", 403)

    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT * FROM equipment WHERE equipment_code=?", (equipment_code,)
    ).fetchone()
    if row is None:
        raise EquipmentError("Not found", 404)

    allowed = {"equipment_name", "location", "line_name", "model", "maker", "qr_value", "is_active"}
    updates = {k: v for k, v in data.items() if k in allowed}
    now = _now_utc()
    updates["updated_at"] = now

    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [equipment_code]
    conn.execute(f"UPDATE equipment SET {set_clause} WHERE equipment_code=?", values)
    conn.commit()

    row = conn.execute("SELECT * FROM equipment WHERE equipment_code=?", (equipment_code,)).fetchone()
    return _row_to_dict(row)


def sync_pull_equipment(db_path: str, since_token: str = None) -> tuple:
    conn = get_connection(db_path)
    if since_token:
        rows = conn.execute(
            "SELECT * FROM equipment WHERE updated_at>=? ORDER BY updated_at ASC",
            (since_token,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM equipment ORDER BY updated_at ASC").fetchall()

    items = [_row_to_dict(r) for r in rows]
    if items:
        next_token = max(r["updated_at"] for r in items)
    else:
        next_token = since_token or _now_utc()

    return items, next_token
