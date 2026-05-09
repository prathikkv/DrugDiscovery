"""Authentication service with register, login, and account lockout."""

import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import bcrypt

from src import config
from src.auth.db import (
    get_user_by_email,
    get_user_by_id,
    init_auth_db,
    insert_user,
    reset_failed_attempts,
    update_failed_attempts,
)
from src.auth.models import Role, User
from src.db import get_connection


class AuthService:
    """Handles user registration, login, and account lockout (REQ-501, REQ-502).

    Each public method creates its own database connection to avoid
    sharing connections across threads (see RESEARCH.md Pitfall 1).
    """

    def __init__(self, db_path: Path = None) -> None:
        self.db_path = db_path or config.AUTH_DB
        self._write_lock = threading.Lock()

        # Ensure schema exists
        conn = get_connection(self.db_path)
        try:
            init_auth_db(conn)
        finally:
            conn.close()

    def register(self, email: str, password: str, role: str) -> dict:
        """Register a new user.

        Returns {"success": True, "user_id": ...} on success,
        or {"success": False, "error": ...} on failure.
        """
        # Validate role
        try:
            Role(role)
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid role: {role}. Must be one of: admin, analyst, reviewer",
            }

        # Validate password length (bcrypt truncates at 72 bytes)
        if len(password.encode("utf-8")) > 72:
            return {
                "success": False,
                "error": "Password must not exceed 72 bytes",
            }

        if not email or not password:
            return {
                "success": False,
                "error": "Email and password are required",
            }

        # Hash the password
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(rounds=config.BCRYPT_ROUNDS),
        ).decode("utf-8")

        user_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        conn = get_connection(self.db_path)
        try:
            with self._write_lock:
                # Check email uniqueness
                existing = get_user_by_email(conn, email)
                if existing is not None:
                    return {
                        "success": False,
                        "error": "Email already registered",
                    }
                insert_user(conn, user_id, email, password_hash, role, created_at)
        finally:
            conn.close()

        return {"success": True, "user_id": user_id}

    def login(self, email: str, password: str) -> dict:
        """Authenticate a user.

        Returns {"success": True, "user_id": ..., "role": ...} on success,
        or {"success": False, "error": ...} on failure.

        Error messages never reveal whether the email exists (security).
        """
        conn = get_connection(self.db_path)
        try:
            row = get_user_by_email(conn, email)

            if row is None:
                return {"success": False, "error": "Invalid credentials"}

            # Check lockout
            if row["locked_until"] is not None:
                locked_until = datetime.fromisoformat(row["locked_until"])
                now = datetime.now(timezone.utc)
                if now < locked_until:
                    remaining = (locked_until - now).total_seconds() / 60
                    return {
                        "success": False,
                        "error": f"Account locked. Try again in {remaining:.0f} minutes",
                    }
                else:
                    # Lockout expired -- reset before proceeding
                    with self._write_lock:
                        reset_failed_attempts(conn, row["user_id"])
                    # Re-fetch to get updated state
                    row = get_user_by_email(conn, email)

            # Verify password (constant-time comparison via bcrypt)
            if bcrypt.checkpw(
                password.encode("utf-8"),
                row["password_hash"].encode("utf-8"),
            ):
                # Success -- reset failed attempts
                if row["failed_attempts"] > 0:
                    with self._write_lock:
                        reset_failed_attempts(conn, row["user_id"])
                return {
                    "success": True,
                    "user_id": row["user_id"],
                    "role": row["role"],
                }
            else:
                # Failed -- increment counter
                new_attempts = row["failed_attempts"] + 1
                locked_until = None

                if new_attempts >= config.LOCKOUT_THRESHOLD:
                    locked_until = (
                        datetime.now(timezone.utc)
                        + timedelta(minutes=config.LOCKOUT_DURATION_MINUTES)
                    ).isoformat()

                with self._write_lock:
                    update_failed_attempts(
                        conn, row["user_id"], new_attempts, locked_until
                    )

                return {"success": False, "error": "Invalid credentials"}
        finally:
            conn.close()

    def get_user(self, user_id: str) -> Optional[User]:
        """Look up a user by ID. Returns User dataclass or None."""
        conn = get_connection(self.db_path)
        try:
            row = get_user_by_id(conn, user_id)
            if row is None:
                return None
            return User(
                user_id=row["user_id"],
                email=row["email"],
                role=Role(row["role"]),
                created_at=row["created_at"],
                is_active=bool(row["is_active"]),
                failed_attempts=row["failed_attempts"],
                locked_until=row["locked_until"],
            )
        finally:
            conn.close()
