"""Audit trail database schema and initialization (REQ-503, REQ-507)."""

import sqlite3


# ── Schema ───────────────────────────────────────────────────────────

AUDIT_SCHEMA = """\
CREATE TABLE IF NOT EXISTS audit_trail (
    sequence_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    action          TEXT NOT NULL CHECK(action IN (
                        'CREATE', 'UPDATE', 'DELETE',
                        'APPROVE', 'SIGN', 'LOGIN', 'LOGOUT'
                    )),
    resource_type   TEXT NOT NULL CHECK(resource_type IN (
                        'project', 'gate', 'config', 'user', 'task'
                    )),
    resource_id     TEXT NOT NULL,
    details_json    TEXT NOT NULL DEFAULT '{}',
    previous_hash   TEXT NOT NULL,
    record_hash     TEXT NOT NULL
);

-- REQ-507: Indices for audit trail queries
CREATE INDEX IF NOT EXISTS idx_audit_user_id
    ON audit_trail(user_id);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp
    ON audit_trail(timestamp);

CREATE INDEX IF NOT EXISTS idx_audit_resource_type
    ON audit_trail(resource_type);

CREATE INDEX IF NOT EXISTS idx_audit_resource_id
    ON audit_trail(resource_id);
"""


def init_audit_db(conn: sqlite3.Connection) -> None:
    """Create the audit_trail table and indices if they do not exist."""
    conn.executescript(AUDIT_SCHEMA)
