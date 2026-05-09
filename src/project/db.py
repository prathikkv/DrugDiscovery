"""Project database schema and query functions (REQ-605)."""

import sqlite3
from typing import Optional


# ── Schema ───────────────────────────────────────────────────────────

PROJECT_SCHEMA = """\
CREATE TABLE IF NOT EXISTS projects (
    project_id  TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    created_by  TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active'
                CHECK(status IN ('active', 'archived', 'deleted')),
    config_json TEXT NOT NULL DEFAULT '{}'
);
"""


def init_project_db(conn: sqlite3.Connection) -> None:
    """Create the projects table if it does not exist."""
    conn.executescript(PROJECT_SCHEMA)


# ── Queries ──────────────────────────────────────────────────────────

def insert_project(
    conn: sqlite3.Connection,
    project_id: str,
    name: str,
    description: Optional[str],
    created_by: str,
    created_at: str,
    updated_at: str,
    status: str,
    config_json: str,
) -> None:
    """Insert a new project with parameterized query."""
    conn.execute(
        "INSERT INTO projects "
        "(project_id, name, description, created_by, created_at, "
        "updated_at, status, config_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (project_id, name, description, created_by, created_at,
         updated_at, status, config_json),
    )
    conn.commit()


def get_project(
    conn: sqlite3.Connection,
    project_id: str,
) -> Optional[sqlite3.Row]:
    """Look up a project by project_id. Returns Row or None."""
    cursor = conn.execute(
        "SELECT * FROM projects WHERE project_id = ?",
        (project_id,),
    )
    return cursor.fetchone()


def list_projects(
    conn: sqlite3.Connection,
    status: str = "active",
) -> list[sqlite3.Row]:
    """List projects filtered by status. Default: active only."""
    cursor = conn.execute(
        "SELECT * FROM projects WHERE status = ? ORDER BY created_at DESC",
        (status,),
    )
    return cursor.fetchall()


def update_project_status(
    conn: sqlite3.Connection,
    project_id: str,
    status: str,
    updated_at: str,
) -> int:
    """Update project status (soft-delete or archive).

    Returns number of rows affected (0 if project not found).
    """
    cursor = conn.execute(
        "UPDATE projects SET status = ?, updated_at = ? "
        "WHERE project_id = ?",
        (status, updated_at, project_id),
    )
    conn.commit()
    return cursor.rowcount
