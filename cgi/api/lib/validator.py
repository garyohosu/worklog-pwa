"""Input validation utilities."""
import re
import uuid

VALID_RECORD_TYPES = {"inspection", "repair", "trouble", "maintenance", "memo"}
VALID_STATUSES = {"draft", "open", "in_progress", "done", "pending_parts"}
VALID_PRIORITIES = {"low", "medium", "high", "critical"}
VALID_ROLES = {"user", "admin"}

FORBIDDEN_FIELDS = {
    "user_id",
    "created_by",
    "updated_by",
    "deleted_by",
    "deleted_flag",
    "deleted_at",
    "server_updated_at",
    "revision",
    "sync_state",
}


def validate_login_id(value) -> str | None:
    """Return error message or None if valid."""
    if not value or not str(value).strip():
        return "login_id is required"
    return None


def validate_password(value) -> str | None:
    """Return error message or None if valid."""
    if not value:
        return "password is required"
    if len(str(value)) < 8:
        return "password must be at least 8 characters"
    return None


def validate_display_name(value) -> str | None:
    if not value or not str(value).strip():
        return "display_name is required"
    return None


def validate_title(value) -> str | None:
    if not value or not str(value).strip():
        return "title is required"
    return None


def validate_record_type(value) -> str | None:
    if value not in VALID_RECORD_TYPES:
        return f"record_type must be one of {sorted(VALID_RECORD_TYPES)}"
    return None


def validate_status(value) -> str | None:
    if value not in VALID_STATUSES:
        return f"status must be one of {sorted(VALID_STATUSES)}"
    return None


def validate_priority(value) -> str | None:
    """priority is optional (None allowed)."""
    if value is None:
        return None
    if value not in VALID_PRIORITIES:
        return f"priority must be one of {sorted(VALID_PRIORITIES)} or null"
    return None


def validate_role(value) -> str | None:
    if value not in VALID_ROLES:
        return f"role must be one of {sorted(VALID_ROLES)}"
    return None


def validate_uuid(value) -> str | None:
    if not value:
        return "log_uuid is required"
    try:
        uuid.UUID(str(value))
    except ValueError:
        return "log_uuid must be a valid UUID"
    return None


def validate_base_revision(value) -> str | None:
    if value is None:
        return "base_revision is required"
    try:
        v = int(value)
    except (TypeError, ValueError):
        return "base_revision must be an integer"
    if v < 1:
        return "base_revision must be >= 1"
    return None


def validate_forbidden_fields(fields: dict) -> str | None:
    """Return error if any forbidden field is present."""
    found = FORBIDDEN_FIELDS & set(fields.keys())
    if found:
        return f"forbidden fields: {sorted(found)}"
    return None


def collect_errors(**kwargs) -> list:
    """Run multiple validators and collect all error messages."""
    return [msg for msg in kwargs.values() if msg is not None]
