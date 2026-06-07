"""Auth database schema and query functions."""

import sqlite3


# ── Schema ───────────────────────────────────────────────────────────

AUTH_SCHEMA = """\
CREATE TABLE IF NOT EXISTS users (
    user_id         TEXT PRIMARY KEY,
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL CHECK(role IN ('admin', 'analyst', 'reviewer')),
    created_at      TEXT NOT NULL,
    is_active       INTEGER NOT NULL DEFAULT 1,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    TEXT
);
"""


def init_auth_db(conn: sqlite3.Connection) -> None:
    """Create the users table if it does not exist."""
    conn.executescript(AUTH_SCHEMA)


# ── Queries ──────────────────────────────────────────────────────────

def insert_user(
    conn: sqlite3.Connection,
    user_id: str,
    email: str,
    password_hash: str,
    role: str,
    created_at: str,
) -> None:
    """Insert a new user with parameterized query."""
    conn.execute(
        "INSERT INTO users (user_id, email, password_hash, role, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, email, password_hash, role, created_at),
    )
    conn.commit()


def get_user_by_email(
    conn: sqlite3.Connection,
    email: str,
) -> sqlite3.Row | None:
    """Look up a user by email. Returns Row or None."""
    cursor = conn.execute(
        "SELECT * FROM users WHERE email = ? COLLATE NOCASE",
        (email,),
    )
    return cursor.fetchone()


def get_user_by_id(
    conn: sqlite3.Connection,
    user_id: str,
) -> sqlite3.Row | None:
    """Look up a user by user_id. Returns Row or None."""
    cursor = conn.execute(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,),
    )
    return cursor.fetchone()


def update_failed_attempts(
    conn: sqlite3.Connection,
    user_id: str,
    attempts: int,
    locked_until: str | None = None,
) -> None:
    """Update failed_attempts and optionally locked_until.

    Uses BEGIN IMMEDIATE for write atomicity under WAL mode
    (see RESEARCH.md Pitfall 7).
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            "UPDATE users SET failed_attempts = ?, locked_until = ? "
            "WHERE user_id = ?",
            (attempts, locked_until, user_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def count_users(conn: sqlite3.Connection) -> int:
    """Return the total number of registered users."""
    return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def reset_failed_attempts(
    conn: sqlite3.Connection,
    user_id: str,
) -> None:
    """Reset failed_attempts to 0 and clear locked_until."""
    conn.execute(
        "UPDATE users SET failed_attempts = 0, locked_until = NULL "
        "WHERE user_id = ?",
        (user_id,),
    )
    conn.commit()
