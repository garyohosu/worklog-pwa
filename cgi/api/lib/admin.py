"""Admin business logic."""
from datetime import datetime, timezone
from .db import get_connection


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class AdminError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _require_admin(actor_role: str):
    if actor_role != "admin":
        raise AdminError("Forbidden", 403)


# ---------------------------------------------------------------------------
# User list
# ---------------------------------------------------------------------------
def list_users(db_path: str, actor_role: str) -> list:
    _require_admin(actor_role)
    conn = get_connection(db_path)
    rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# set_active
# ---------------------------------------------------------------------------
def set_active(db_path: str, target_user_id: int, is_active: int,
               actor_user_id: int, actor_role: str):
    _require_admin(actor_role)
    if target_user_id == actor_user_id and is_active == 0:
        raise AdminError("Cannot deactivate yourself", 400)

    now = _now_utc()
    conn = get_connection(db_path)
    conn.execute(
        "UPDATE users SET is_active=?, updated_at=? WHERE id=?",
        (is_active, now, target_user_id),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# set_role
# ---------------------------------------------------------------------------
def set_role(db_path: str, target_user_id: int, new_role: str,
             actor_user_id: int, actor_role: str):
    _require_admin(actor_role)
    conn = get_connection(db_path)

    # last-admin guard
    if new_role == "user":
        admin_count = conn.execute(
            "SELECT COUNT(*) FROM users WHERE role='admin' AND id!=?", (target_user_id,)
        ).fetchone()[0]
        if admin_count == 0:
            raise AdminError("Cannot demote the last admin", 400)

    now = _now_utc()
    conn.execute(
        "UPDATE users SET role=?, updated_at=? WHERE id=?",
        (new_role, now, target_user_id),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
def get_dashboard(db_path: str, actor_role: str) -> dict:
    _require_admin(actor_role)
    conn = get_connection(db_path)
    today = _today_utc()

    def _count(where="", params=None):
        params = params or []
        return conn.execute(
            f"SELECT COUNT(*) FROM work_logs WHERE deleted_flag=0 {where}", params
        ).fetchone()[0]

    total_today = _count("AND recorded_at>=?", [today + "T00:00:00Z"])
    total_7d = _count("AND recorded_at>=?", [_days_ago(7)])
    total_30d = _count("AND recorded_at>=?", [_days_ago(30)])

    by_status = {}
    for s in ("draft", "open", "in_progress", "done", "pending_parts"):
        by_status[s] = _count("AND status=?", [s])

    by_record_type = {}
    for rt in ("inspection", "repair", "trouble", "maintenance", "memo"):
        by_record_type[rt] = _count("AND record_type=?", [rt])

    followup_overdue = conn.execute(
        "SELECT COUNT(*) FROM work_logs WHERE deleted_flag=0 AND needs_followup=1 "
        "AND followup_due IS NOT NULL AND followup_due<? AND status!='done'",
        (today,),
    ).fetchone()[0]

    return {
        "total_by_period": {
            "today": total_today,
            "last_7_days": total_7d,
            "last_30_days": total_30d,
        },
        "by_status": by_status,
        "by_record_type": by_record_type,
        "followup_overdue": followup_overdue,
    }


def _days_ago(n: int) -> str:
    from datetime import timedelta
    dt = datetime.now(timezone.utc) - timedelta(days=n)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
