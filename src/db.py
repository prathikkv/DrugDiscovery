"""Shared SQLite connection factory with WAL mode and safety pragmas."""

import sqlite3
from pathlib import Path

from src import config


def get_connection(
    db_path: Path,
    timeout: float = None,
) -> sqlite3.Connection:
    """Create a configured SQLite connection.

    - WAL journal mode for concurrent reads
    - busy_timeout for write contention
    - Foreign keys enforced
    - Row factory for dict-like access
    - check_same_thread=False for ThreadPoolExecutor compatibility
    """
    if timeout is None:
        timeout = config.DB_TIMEOUT

    # Ensure parent directories exist
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(db_path),
        timeout=timeout,
        check_same_thread=False,
    )

    # Set pragmas
    mode = conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
    assert mode == "wal", f"Expected WAL mode, got {mode}"

    busy_timeout_ms = int(timeout * 1000)
    conn.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
    conn.execute("PRAGMA foreign_keys=ON")

    conn.row_factory = sqlite3.Row

    return conn
