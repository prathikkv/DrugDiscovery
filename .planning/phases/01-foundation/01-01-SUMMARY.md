---
phase: 01-foundation
plan: 01
subsystem: auth, infra
tags: [sqlite, wal-mode, bcrypt, rbac, streamlit, pathlib]

# Dependency graph
requires: []
provides:
  - "SQLite connection factory with WAL mode (src/db.py)"
  - "Central config constants -- DB paths, lockout settings (src/config.py)"
  - "AuthService with register/login/lockout (src/auth/service.py)"
  - "Role enum (admin/analyst/reviewer) and User dataclass (src/auth/models.py)"
  - "Streamlit config with maxUploadSize=2000 (.streamlit/config.toml)"
  - "Pinned Phase 1 dependencies (requirements.txt)"
affects: [compliance, execution, project, audit, ui]

# Tech tracking
tech-stack:
  added: [sqlite3, bcrypt, pathlib, streamlit]
  patterns: [WAL-mode-connections, per-operation-connections, thread-lock-writes, bcrypt-hashing]

key-files:
  created:
    - src/__init__.py
    - src/config.py
    - src/db.py
    - src/auth/__init__.py
    - src/auth/models.py
    - src/auth/db.py
    - src/auth/service.py
    - .streamlit/config.toml
  modified:
    - requirements.txt

key-decisions:
  - "Password hash excluded from User dataclass to prevent leaking outside auth module"
  - "Per-operation connections (not shared) to avoid SQLite threading issues"
  - "BEGIN IMMEDIATE for write atomicity under WAL mode"
  - "bcrypt<5.0 pinned to avoid 72-byte ValueError"
  - "scanpy<1.11 pinned for Python 3.10 compatibility"

patterns-established:
  - "Connection factory pattern: always use get_connection(db_path) from src.db"
  - "Config-as-module: import constants from src.config, never hardcode paths"
  - "Auth result dict pattern: {success: bool, error?: str, user_id?: str, role?: str}"
  - "Thread-safe writes: acquire threading.Lock before DB mutations"
  - "ISO 8601 UTC timestamps via datetime.now(timezone.utc).isoformat()"

# Metrics
duration: 3min
completed: 2026-05-09
---

# Phase 1 Plan 1: Foundation Infrastructure and Auth Summary

**SQLite connection factory with WAL mode, bcrypt auth service with RBAC and account lockout, Streamlit config for 2GB uploads**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-09T18:35:42Z
- **Completed:** 2026-05-09T18:38:34Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Central config module with all DB paths, auth settings, and directory structure using pathlib
- SQLite connection factory enforcing WAL mode, busy_timeout=30s, foreign_keys, and Row factory
- AuthService supporting register (bcrypt hash), login (constant-time comparison), and account lockout (5 attempts / 15 min)
- Role-based access control with admin/analyst/reviewer enum
- Streamlit configured for 2GB uploads, headless mode, and Amgen-style theme
- All Phase 1 dependencies pinned with upper bounds for reproducibility

## Task Commits

Each task was committed atomically:

1. **Task 1: Create foundation infrastructure** - `7304607` (feat)
2. **Task 2: Implement authentication module** - `ce8a221` (feat)

## Files Created/Modified
- `src/__init__.py` - Package marker for src
- `src/config.py` - Central path constants and settings (DATA_DIR, AUTH_DB, LOCKOUT_THRESHOLD, etc.)
- `src/db.py` - SQLite connection factory with WAL mode, busy_timeout, foreign_keys
- `src/auth/__init__.py` - Auth module exports (AuthService, User, Role)
- `src/auth/models.py` - Role enum and User dataclass (password hash intentionally excluded)
- `src/auth/db.py` - Users table schema (DDL), parameterized CRUD queries
- `src/auth/service.py` - AuthService class with register, login, lockout, get_user
- `.streamlit/config.toml` - Server limits, theme, runner settings
- `requirements.txt` - Pinned Phase 1 dependencies (bcrypt, scanpy, numpy, pytest, etc.)

## Decisions Made
- Password hash excluded from User dataclass to prevent leaking outside auth module boundary
- Per-operation database connections (not shared) to avoid SQLite threading issues per RESEARCH.md Pitfall 1
- BEGIN IMMEDIATE transaction for update_failed_attempts to ensure write atomicity under WAL
- bcrypt pinned to <5.0 to avoid 72-byte ValueError (RESEARCH.md Pitfall 3)
- scanpy pinned to <1.11 for Python 3.10 compatibility (RESEARCH.md Pitfall 8)
- numpy pinned to <2.0 for scipy/scanpy compatibility

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Foundation layer (config + db) ready for all subsequent modules to import
- Auth service ready for session management integration (Plan 01-03)
- WAL mode and connection patterns established for compliance, audit, execution modules

---
*Phase: 01-foundation*
*Completed: 2026-05-09*

## Self-Check: PASSED

All 9 files verified present on disk. Both task commits (7304607, ce8a221) verified in git log.
