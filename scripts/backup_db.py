"""Backup all SQLite databases to a timestamped tar.gz archive.

Keeps the 7 most recent backups and deletes older ones automatically.

Usage:
    python scripts/backup_db.py

Add to cron for daily backups:
    0 2 * * * cd /app && python scripts/backup_db.py >> /var/log/backup.log 2>&1
"""

from __future__ import annotations

import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

DB_DIR = Path("data/db")
BACKUP_DIR = Path("data/backups")
KEEP_LAST_N = 7


def backup() -> None:
    if not DB_DIR.exists():
        print(f"ERROR: DB directory not found: {DB_DIR}", file=sys.stderr)
        sys.exit(1)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_path = BACKUP_DIR / f"db_backup_{timestamp}.tar.gz"

    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(DB_DIR, arcname="db")

    size_kb = archive_path.stat().st_size / 1024
    print(f"Backup created: {archive_path}  ({size_kb:.1f} KB)")

    # Prune old backups — keep only the most recent KEEP_LAST_N
    existing = sorted(BACKUP_DIR.glob("db_backup_*.tar.gz"))
    for old in existing[:-KEEP_LAST_N]:
        old.unlink()
        print(f"Removed old backup: {old.name}")


if __name__ == "__main__":
    backup()
