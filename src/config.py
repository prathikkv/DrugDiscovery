"""Central configuration constants for BioOrchestrator v2."""

from pathlib import Path

# ── Directory structure ──────────────────────────────────────────────
DATA_DIR = Path("data")
PROJECTS_DIR = DATA_DIR / "projects"
DB_DIR = DATA_DIR / "db"

# ── Database paths ───────────────────────────────────────────────────
AUTH_DB = DB_DIR / "auth.db"
AUDIT_DB = DB_DIR / "audit.db"
TASKS_DB = DB_DIR / "tasks.db"
PROJECTS_DB = DB_DIR / "projects.db"

# ── Auth settings ────────────────────────────────────────────────────
LOCKOUT_THRESHOLD = 5          # failed attempts before lockout
LOCKOUT_DURATION_MINUTES = 15  # lockout cooldown in minutes
BCRYPT_ROUNDS = 12             # work factor for password hashing

# ── Evidence integration ─────────────────────────────────────────────
EVIDENCE_CACHE_DB = DB_DIR / "evidence_cache.db"

# ── Database settings ────────────────────────────────────────────────
DB_TIMEOUT = 30.0              # SQLite busy_timeout in seconds

# ── Session settings ─────────────────────────────────────────────────
import os as _os
SESSION_TIMEOUT_MINUTES = int(_os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
