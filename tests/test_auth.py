"""Auth module tests -- register, login, lockout, and security properties."""

import pytest

from src.auth.models import Role
from src.db import get_connection


# ── Registration ─────────────────────────────────────────────────────

def test_register_success(auth_service):
    """Register a new user successfully."""
    result = auth_service.register("alice@example.com", "password123", "analyst")
    assert result["success"] is True
    assert "user_id" in result
    assert len(result["user_id"]) > 0


def test_register_duplicate_email(auth_service):
    """Second registration with same email should fail."""
    auth_service.register("bob@example.com", "password123", "analyst")
    result = auth_service.register("bob@example.com", "other456", "reviewer")
    assert result["success"] is False
    assert "already registered" in result["error"].lower()


# ── Login ────────────────────────────────────────────────────────────

def test_login_success(auth_service):
    """Login with correct credentials should succeed."""
    auth_service.register("carol@example.com", "correct_pass", "admin")
    result = auth_service.login("carol@example.com", "correct_pass")
    assert result["success"] is True
    assert "user_id" in result
    assert result["role"] == "admin"


def test_login_wrong_password(auth_service):
    """Login with wrong password should fail."""
    auth_service.register("dave@example.com", "realpass", "analyst")
    result = auth_service.login("dave@example.com", "wrongpass")
    assert result["success"] is False
    assert "invalid" in result["error"].lower()


def test_login_nonexistent_email(auth_service):
    """Login with unregistered email should return same error as wrong password."""
    result = auth_service.login("nobody@example.com", "somepass")
    assert result["success"] is False
    # Should NOT reveal whether email exists (security)
    assert "invalid" in result["error"].lower()


# ── Lockout ──────────────────────────────────────────────────────────

def test_lockout_after_5_failures(auth_service):
    """Account should be locked after 5 failed login attempts."""
    auth_service.register("eve@example.com", "goodpass", "reviewer")

    # Fail 5 times
    for _ in range(5):
        result = auth_service.login("eve@example.com", "badpass")
        assert result["success"] is False

    # 6th attempt with correct password should still fail (locked)
    result = auth_service.login("eve@example.com", "goodpass")
    assert result["success"] is False
    assert "locked" in result["error"].lower()


# ── Security Properties ─────────────────────────────────────────────

def test_password_hash_stored_not_plaintext(auth_service, tmp_auth_db):
    """Password should be stored as bcrypt hash, not plaintext."""
    auth_service.register("frank@example.com", "myplainpass", "analyst")

    conn = get_connection(tmp_auth_db)
    try:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE email = ?",
            ("frank@example.com",),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row["password_hash"] != "myplainpass"
    assert row["password_hash"].startswith("$2b$")


def test_role_enum_values():
    """Role enum should have admin, analyst, reviewer."""
    assert Role.ADMIN.value == "admin"
    assert Role.ANALYST.value == "analyst"
    assert Role.REVIEWER.value == "reviewer"
    assert len(Role) == 3
