"""Tests for lib/validator.py — TC-ENUM and TC-PAYLOAD."""
import pytest
from lib.validator import (
    validate_login_id,
    validate_password,
    validate_display_name,
    validate_title,
    validate_record_type,
    validate_status,
    validate_priority,
    validate_role,
    validate_uuid,
    validate_base_revision,
    validate_forbidden_fields,
    collect_errors,
)


# ---------------------------------------------------------------------------
# TC-ENUM-RT: RecordType
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("v", ["inspection", "repair", "trouble", "maintenance", "memo"])
def test_record_type_valid(v):
    assert validate_record_type(v) is None


@pytest.mark.parametrize("v", ["other", "Inspection", "", "unknown"])
def test_record_type_invalid(v):
    assert validate_record_type(v) is not None


# ---------------------------------------------------------------------------
# TC-ENUM-ST: WorkStatus
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("v", ["draft", "open", "in_progress", "done", "pending_parts"])
def test_status_valid(v):
    assert validate_status(v) is None


@pytest.mark.parametrize("v", ["closed", "in-progress", "archived", ""])
def test_status_invalid(v):
    assert validate_status(v) is not None


# ---------------------------------------------------------------------------
# TC-ENUM-PRI: Priority (NULL allowed)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("v", ["low", "medium", "high", "critical"])
def test_priority_valid(v):
    assert validate_priority(v) is None


def test_priority_null_allowed():
    assert validate_priority(None) is None


@pytest.mark.parametrize("v", ["urgent", "normal", "extreme", ""])
def test_priority_invalid(v):
    assert validate_priority(v) is not None


# ---------------------------------------------------------------------------
# TC-ENUM-ROLE: Role
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("v", ["user", "admin"])
def test_role_valid(v):
    assert validate_role(v) is None


@pytest.mark.parametrize("v", ["superadmin", "guest", ""])
def test_role_invalid(v):
    assert validate_role(v) is not None


# ---------------------------------------------------------------------------
# Password validation (TC-AUTH-REG)
# ---------------------------------------------------------------------------
def test_password_min_length_7_fails():
    assert validate_password("1234567") is not None


def test_password_min_length_8_passes():
    assert validate_password("12345678") is None


def test_password_none_fails():
    assert validate_password(None) is not None


# ---------------------------------------------------------------------------
# TC-PAYLOAD: Forbidden fields
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("field", [
    "user_id", "created_by", "updated_by", "deleted_by",
    "deleted_flag", "deleted_at", "server_updated_at", "revision", "sync_state",
])
def test_forbidden_field_detected(field):
    err = validate_forbidden_fields({field: "anything", "title": "ok"})
    assert err is not None


def test_no_forbidden_fields_passes():
    err = validate_forbidden_fields({
        "title": "test",
        "record_type": "inspection",
        "status": "open",
    })
    assert err is None


# ---------------------------------------------------------------------------
# base_revision validation (TC-PLD-U / TC-PLD-D)
# ---------------------------------------------------------------------------
def test_base_revision_valid():
    assert validate_base_revision(1) is None
    assert validate_base_revision(99) is None


def test_base_revision_zero_invalid():
    assert validate_base_revision(0) is not None


def test_base_revision_none_invalid():
    assert validate_base_revision(None) is not None


def test_base_revision_negative_invalid():
    assert validate_base_revision(-1) is not None


# ---------------------------------------------------------------------------
# UUID validation
# ---------------------------------------------------------------------------
def test_uuid_valid():
    import uuid
    assert validate_uuid(str(uuid.uuid4())) is None


def test_uuid_none_invalid():
    assert validate_uuid(None) is not None


def test_uuid_garbage_invalid():
    assert validate_uuid("not-a-uuid") is not None


# ---------------------------------------------------------------------------
# collect_errors helper
# ---------------------------------------------------------------------------
def test_collect_errors_no_errors():
    result = collect_errors(a=None, b=None)
    assert result == []


def test_collect_errors_with_errors():
    result = collect_errors(a="error1", b=None, c="error2")
    assert "error1" in result
    assert "error2" in result
    assert len(result) == 2
