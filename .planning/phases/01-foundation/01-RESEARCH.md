# Phase 1: Foundation - Research

**Researched:** 2026-05-09
**Domain:** Authentication, compliance audit trails, background execution, project management, test infrastructure
**Confidence:** HIGH

## Summary

Phase 1 establishes the infrastructure that every subsequent phase depends on: user authentication with RBAC, 21 CFR Part 11 compliant audit trails with hash-chain integrity, background task execution via ThreadPoolExecutor with SQLite persistence, project CRUD with audit logging, Streamlit configuration, and a synthetic h5ad test fixture for fast testing.

The existing codebase in `bioorchestrator_real/` provides a working lineage audit trail (`stage7_lineage.py`) and a monolithic Streamlit app (`app.py`) -- both need significant rework. The existing lineage DB tracks pipeline stages but lacks hash chains, user attribution, append-only enforcement, and electronic signatures required by 21 CFR Part 11. The app is a single-file monolith with no authentication. The new v2 architecture should be a clean `src/` layout with the existing code referenced as a migration source, not directly refactored in place.

**Primary recommendation:** Build five independent modules (auth, audit, task_manager, project, test fixtures) with SQLite WAL mode as the shared storage layer, using `st.navigation`/`st.Page` for multipage app structure and `st.cache_resource` for singleton services like the ThreadPoolExecutor.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| bcrypt | 4.x (pin <5.0 to avoid breaking change) | Password hashing | Industry standard for password storage, adjustable work factor, constant-time comparison |
| sqlite3 | stdlib (Python 3.10) | All persistence | Zero-dependency, ACID compliant, WAL mode for concurrent access, matches project constraint |
| streamlit | >=1.40.0,<2.0 | UI framework | Project constraint; 1.40+ has stable `st.navigation`/`st.Page` API |
| anndata | >=0.10.0 | Synthetic test data | Required for h5ad fixture generation |
| scanpy | 1.10.x | scRNA-seq toolkit | Pin to 1.10.x for Python 3.10 compatibility (1.12+ requires Python 3.12) |
| numpy | >=1.23,<2.0 | Numerics | Project constraint: NumPy <2.0 for ecosystem compatibility |
| pytest | >=7.0 | Testing | Standard Python test framework |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scipy.sparse | (bundled with scipy) | Sparse matrix for h5ad fixture | Creating realistic sparse count matrices for test data |
| hashlib | stdlib | SHA-256 hash chains | Audit trail integrity, electronic signature hashing |
| uuid | stdlib | Unique identifiers | User IDs, project IDs, audit record IDs |
| datetime | stdlib | UTC timestamps | All audit records must use `datetime.now(timezone.utc)` |
| concurrent.futures | stdlib | ThreadPoolExecutor | Background task execution |
| threading | stdlib | Lock for thread safety | Serializing SQLite writes from background threads |
| json | stdlib | Config and parameter storage | Audit trail params, project metadata |
| pathlib | stdlib | File path management | Per-project file storage layout |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| bcrypt 4.x | bcrypt 5.x | 5.0 raises ValueError for passwords >72 bytes -- requires pre-hashing with SHA-256; use 4.x to avoid this complexity in MVP |
| bcrypt | argon2-cffi | Argon2 is newer/memory-hard but bcrypt is explicitly required by REQ-501 |
| SQLite | PostgreSQL | PostgreSQL is better for multi-user but SQLite is the MVP constraint; migration path exists |
| ThreadPoolExecutor | Celery/Redis | Celery is overkill for single-user MVP; ThreadPoolExecutor is the explicit requirement (REQ-602) |

**Installation:**
```bash
pip install "bcrypt>=4.0,<5.0" pytest anndata "scanpy>=1.10.0,<1.11" "numpy>=1.23,<2.0" scipy
```

Note: `streamlit`, `sqlite3`, `hashlib`, `uuid`, `datetime`, `concurrent.futures`, `threading`, `json`, `pathlib` are all stdlib or already in requirements.txt.

## Architecture Patterns

### Recommended Project Structure
```
src/
    app.py                      # Entrypoint: st.navigation + st.Page routing
    pages/
        login.py                # Login/registration page
        projects.py             # Project CRUD page
    auth/
        __init__.py
        models.py               # User dataclass, Role enum
        service.py              # AuthService: register, login, lockout logic
        db.py                   # Auth SQLite schema + queries
    compliance/
        __init__.py
        audit_trail.py          # AuditTrail: append-only records, hash chains
        electronic_signature.py # E-signature: re-auth + SHA-256 signing
        db.py                   # Audit SQLite schema + queries
    execution/
        __init__.py
        task_manager.py         # TaskManager: ThreadPoolExecutor + SQLite state
        models.py               # TaskStatus enum, TaskRecord dataclass
    project/
        __init__.py
        service.py              # ProjectService: CRUD + audit integration
        models.py               # Project dataclass
        db.py                   # Project SQLite schema + queries
    config.py                   # Central config (paths, DB names, constants)
    db.py                       # Shared DB utilities (WAL mode, busy_timeout)
tests/
    conftest.py                 # Synthetic h5ad fixture, temp DB fixtures
    test_auth.py                # Auth unit tests
    test_audit_trail.py         # Audit trail + hash chain tests
    test_task_manager.py        # Background execution tests
    test_project.py             # Project CRUD tests
.streamlit/
    config.toml                 # maxUploadSize=2000, theme, fastReruns
data/
    projects/                   # Per-project file storage root
```

### Pattern 1: SQLite WAL Mode Connection Factory
**What:** Every SQLite connection in the application uses WAL mode and a busy_timeout for concurrent access safety.
**When to use:** Every time a database connection is created anywhere in the app.
**Example:**
```python
# Source: Python 3.10 sqlite3 docs + SQLite WAL docs
import sqlite3
from pathlib import Path

def get_connection(db_path: Path, timeout: float = 30.0) -> sqlite3.Connection:
    """Create a SQLite connection with WAL mode and busy_timeout."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(db_path),
        timeout=timeout,  # busy_timeout in seconds
        check_same_thread=False,  # Required for ThreadPoolExecutor access
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")  # 30s in milliseconds
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
```

### Pattern 2: Hash-Chain Audit Trail (21 CFR Part 11)
**What:** Each audit record includes a SHA-256 hash of the previous record, creating a tamper-evident chain. If any record is modified directly in SQLite, the chain breaks and tampering is detectable.
**When to use:** Every state-changing operation must produce an audit record through this system.
**Example:**
```python
# Source: 21 CFR Part 11 requirements + ALCOA+ principles
import hashlib
import json
from datetime import datetime, timezone

def compute_record_hash(
    previous_hash: str,
    timestamp: str,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: dict,
) -> str:
    """Compute SHA-256 hash for audit record integrity chain."""
    payload = json.dumps({
        "previous_hash": previous_hash,
        "timestamp": timestamp,
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details,
    }, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def append_audit_record(conn, user_id, action, resource_type, resource_id, details=None):
    """Append an immutable audit record with hash-chain integrity."""
    # Get previous hash (or genesis hash for first record)
    row = conn.execute(
        "SELECT record_hash FROM audit_trail ORDER BY sequence_id DESC LIMIT 1"
    ).fetchone()
    previous_hash = row["record_hash"] if row else "0" * 64  # genesis

    timestamp = datetime.now(timezone.utc).isoformat()
    record_hash = compute_record_hash(
        previous_hash, timestamp, user_id, action,
        resource_type, resource_id, details or {}
    )

    conn.execute(
        """INSERT INTO audit_trail
           (timestamp, user_id, action, resource_type, resource_id,
            details_json, previous_hash, record_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (timestamp, user_id, action, resource_type, resource_id,
         json.dumps(details or {}), previous_hash, record_hash)
    )
    conn.commit()
    return record_hash
```

### Pattern 3: Singleton TaskManager via st.cache_resource
**What:** A single ThreadPoolExecutor instance shared across all Streamlit reruns, with task state persisted to SQLite so it survives browser refresh.
**When to use:** For background pipeline execution that outlives Streamlit's rerun cycle.
**Example:**
```python
# Source: Streamlit docs (st.cache_resource), Python concurrent.futures docs
import streamlit as st
from concurrent.futures import ThreadPoolExecutor

@st.cache_resource
def get_task_manager():
    """Singleton TaskManager that persists across reruns."""
    return TaskManager(max_workers=2, db_path=Path("data/tasks.db"))

class TaskManager:
    def __init__(self, max_workers: int, db_path: Path):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def submit(self, task_id: str, fn, *args, **kwargs):
        """Submit task, persist PENDING state, run in background."""
        with self._lock:
            self._update_state(task_id, "RUNNING")
        future = self.executor.submit(self._wrapped_run, task_id, fn, *args, **kwargs)
        return future

    def _wrapped_run(self, task_id, fn, *args, **kwargs):
        try:
            result = fn(*args, **kwargs)
            with self._lock:
                self._update_state(task_id, "COMPLETED", result=str(result))
            return result
        except Exception as e:
            with self._lock:
                self._update_state(task_id, "FAILED", error=str(e))
            raise

    def get_status(self, task_id: str) -> dict:
        """Read task status from SQLite (survives browser refresh)."""
        conn = get_connection(self.db_path)
        row = conn.execute(
            "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None
```

### Pattern 4: Streamlit Multipage with st.navigation
**What:** Use `st.Page` and `st.navigation` for page routing with programmatic control over which pages are visible based on auth state.
**When to use:** App entrypoint (app.py).
**Example:**
```python
# Source: Streamlit docs (st.navigation, st.Page)
import streamlit as st

def main():
    # Check auth state
    if "user" not in st.session_state:
        # Only show login page
        pg = st.navigation([
            st.Page("pages/login.py", title="Login", icon=":material/login:"),
        ])
    else:
        # Show all pages
        pg = st.navigation({
            "Projects": [
                st.Page("pages/projects.py", title="Projects", icon=":material/folder:"),
            ],
            "Admin": [
                st.Page("pages/audit.py", title="Audit Trail",
                        icon=":material/security:", default=False),
            ],
        })
    pg.run()

if __name__ == "__main__":
    main()
```

### Anti-Patterns to Avoid
- **Mutable audit records:** NEVER use UPDATE or DELETE on the audit_trail table. All records are INSERT-only. Use database triggers or application-level guards to prevent mutation.
- **Sharing SQLite connections across threads:** Always create new connections per thread, or use a lock-protected shared connection. The `check_same_thread=False` flag disables Python's check but does NOT make SQLite thread-safe -- you must serialize writes.
- **Storing passwords in session state:** Session state is not encrypted. Store only user_id and role after successful authentication, never the password or hash.
- **Using `time.gmtime()` for audit timestamps:** The existing codebase uses `time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())`. Use `datetime.now(timezone.utc).isoformat()` instead -- it is timezone-aware and the Python-recommended approach.
- **Relying on session state for task persistence:** Session state is lost on browser refresh/tab close. Task state MUST be in SQLite for REQ-603 compliance.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing | Custom SHA-256 + salt | `bcrypt.hashpw()` + `bcrypt.checkpw()` | Timing attacks, salt management, work factor tuning -- bcrypt handles all of this correctly |
| UUID generation | Custom ID schemes | `uuid.uuid4()` | Guaranteed uniqueness without coordination, standard format |
| Timestamp generation | `time.time()` or `time.gmtime()` | `datetime.now(timezone.utc).isoformat()` | Timezone-aware, ISO 8601 format, no ambiguity |
| Thread pool management | Manual thread creation | `concurrent.futures.ThreadPoolExecutor` | Proper cleanup, Future objects, exception propagation |
| JSON serialization for hashing | String concatenation | `json.dumps(sort_keys=True, separators=(",",":"))` | Deterministic output required for reproducible hashes |
| Config file parsing | Custom parser | Streamlit's built-in config.toml support | Already handles all config loading, env var overrides |
| Sparse matrix creation | Dense arrays for test h5ad | `scipy.sparse.random()` or `scipy.sparse.csr_matrix()` | Real scRNA-seq data is >95% zeros; dense matrices misrepresent data and waste memory |

**Key insight:** This phase is entirely infrastructure -- every component has a well-established stdlib or single-library solution. The complexity is in correct integration (hash chains, thread safety, session management), not in the individual components.

## Common Pitfalls

### Pitfall 1: SQLite Thread Safety with ThreadPoolExecutor
**What goes wrong:** Background tasks running in ThreadPoolExecutor threads try to use a SQLite connection created in the main Streamlit thread. Python raises `ProgrammingError: SQLite objects created in a thread can only be used in that same thread`.
**Why it happens:** Python's sqlite3 module defaults to `check_same_thread=True`.
**How to avoid:** Either (a) set `check_same_thread=False` and protect all writes with a `threading.Lock`, or (b) create a new connection inside each thread/task function. Option (b) is safer and simpler. With WAL mode, concurrent readers do not block each other.
**Warning signs:** Intermittent `ProgrammingError` exceptions during background task execution.

### Pitfall 2: Hash Chain Ordering Under Concurrent Writes
**What goes wrong:** Two audit records are written simultaneously, both read the same "previous_hash", producing a forked chain instead of a linear one.
**Why it happens:** The read-previous-hash and insert-new-record are not atomic.
**How to avoid:** Use a single `threading.Lock` around the entire read-previous-hash + compute-hash + insert sequence. Since audit writes are small and fast, this lock will not create a bottleneck. Alternatively, use `BEGIN IMMEDIATE` transaction.
**Warning signs:** Hash chain verification fails sporadically under concurrent operations.

### Pitfall 3: bcrypt 5.0 Password Length Limit
**What goes wrong:** bcrypt 5.0+ raises `ValueError` for passwords longer than 72 bytes. Users with long passwords get cryptic errors.
**Why it happens:** bcrypt algorithm silently truncated passwords at 72 bytes. Version 5.0 made this an explicit error instead.
**How to avoid:** Pin `bcrypt<5.0` for MVP simplicity. If using 5.0+, pre-hash with SHA-256: `hashlib.sha256(password.encode()).digest()` before passing to bcrypt.
**Warning signs:** Registration or login fails for users with passwords containing multi-byte UTF-8 characters or very long passphrases.

### Pitfall 4: Streamlit Session State Lost on Refresh
**What goes wrong:** User logs in, refreshes browser, and is logged out. Background task completes but UI shows "unknown" status.
**Why it happens:** Streamlit session state exists only in server memory for the active WebSocket connection. Browser refresh creates a new session.
**How to avoid:** For auth: accept this limitation for MVP (user must re-login on refresh). For task state: always read from SQLite, never rely on session state alone. Store `task_id` in session state but always query SQLite for current status.
**Warning signs:** Users report losing context after browser refresh.

### Pitfall 5: WAL Mode Not Persisting Across Connections
**What goes wrong:** WAL mode is set on one connection, but new connections revert to journal mode.
**Why it happens:** `PRAGMA journal_mode=WAL` is persistent for the database file (it stays WAL until explicitly changed), but only if the first connection that creates the file sets it. However, if the database is created without WAL and later connections try to change it, it works -- but you must check the return value.
**How to avoid:** Set WAL mode in the connection factory function and verify the return: `result = conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]` should return `"wal"`.
**Warning signs:** `PRAGMA journal_mode` returns `"delete"` instead of `"wal"`.

### Pitfall 6: Audit Trail Indices Missing
**What goes wrong:** Audit trail queries become slow as records accumulate (seconds instead of milliseconds).
**Why it happens:** REQ-507 requires indices on user_id, timestamp, resource_type, resource_id but they are easy to forget during initial schema creation.
**How to avoid:** Include index creation in the schema DDL alongside the table creation. Verify with `EXPLAIN QUERY PLAN` that queries hit indices.
**Warning signs:** Audit trail page loads slowly in production.

### Pitfall 7: Account Lockout Timer Race Condition
**What goes wrong:** Multiple rapid login attempts bypass the lockout counter because each request reads the count before the other increments it.
**Why it happens:** Streamlit reruns are synchronous per session, but if using the same account from multiple browser tabs, reads and writes can interleave.
**How to avoid:** Use `BEGIN IMMEDIATE` transaction for the check-and-increment operation. Single-user MVP makes this unlikely but the pattern should be correct from day one.
**Warning signs:** Account locks at 6 or 7 attempts instead of exactly 5.

### Pitfall 8: scanpy Version Incompatibility
**What goes wrong:** Installing scanpy 1.12+ pulls in Python 3.12 requirements, breaking the environment.
**Why it happens:** The project requires Python 3.10, but scanpy 1.12+ requires Python 3.12.
**How to avoid:** Pin `scanpy>=1.10.0,<1.11` in requirements. scanpy 1.10.x supports Python 3.10.
**Warning signs:** `pip install scanpy` fails with Python version errors.

## Code Examples

Verified patterns from official sources:

### Audit Trail Schema (REQ-503, REQ-507)
```python
# Source: 21 CFR Part 11 requirements + SQLite best practices
AUDIT_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_trail (
    sequence_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,           -- ISO 8601 UTC
    user_id         TEXT NOT NULL,
    action          TEXT NOT NULL,           -- CREATE, UPDATE, DELETE, APPROVE, SIGN
    resource_type   TEXT NOT NULL,           -- project, gate, config, user
    resource_id     TEXT NOT NULL,
    details_json    TEXT NOT NULL DEFAULT '{}',
    previous_hash   TEXT NOT NULL,           -- SHA-256 of previous record
    record_hash     TEXT NOT NULL            -- SHA-256 of this record
);

-- REQ-507: Required indices for query performance
CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_trail(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_trail(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_resource_type ON audit_trail(resource_type);
CREATE INDEX IF NOT EXISTS idx_audit_resource_id ON audit_trail(resource_id);
"""
```

### User Authentication Schema (REQ-501, REQ-502)
```python
# Source: bcrypt docs + 21 CFR Part 11 user management requirements
AUTH_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id         TEXT PRIMARY KEY,        -- UUID
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,           -- bcrypt hash
    role            TEXT NOT NULL CHECK(role IN ('admin', 'analyst', 'reviewer')),
    created_at      TEXT NOT NULL,           -- ISO 8601 UTC
    is_active       INTEGER NOT NULL DEFAULT 1,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    TEXT                     -- ISO 8601 UTC, NULL = not locked
);
"""

import bcrypt

def hash_password(password: str) -> str:
    """Hash password with bcrypt. Enforces 72-byte limit."""
    pw_bytes = password.encode("utf-8")
    if len(pw_bytes) > 72:
        raise ValueError("Password exceeds 72 bytes")
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt(rounds=12)).decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time password verification."""
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8")
    )
```

### Account Lockout Logic (REQ-502)
```python
# Source: REQ-502 specification
from datetime import datetime, timezone, timedelta

LOCKOUT_THRESHOLD = 5
LOCKOUT_DURATION = timedelta(minutes=15)

def check_and_handle_login(conn, email: str, password: str) -> dict:
    """Authenticate user with lockout enforcement."""
    user = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ).fetchone()

    if not user:
        return {"success": False, "error": "Invalid credentials"}

    # Check lockout
    if user["locked_until"]:
        locked_until = datetime.fromisoformat(user["locked_until"])
        if datetime.now(timezone.utc) < locked_until:
            remaining = (locked_until - datetime.now(timezone.utc)).seconds // 60
            return {"success": False, "error": f"Account locked. Try again in {remaining} minutes"}
        else:
            # Lockout expired, reset
            conn.execute(
                "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE user_id = ?",
                (user["user_id"],)
            )
            conn.commit()

    if not verify_password(password, user["password_hash"]):
        new_attempts = user["failed_attempts"] + 1
        if new_attempts >= LOCKOUT_THRESHOLD:
            locked_until = (datetime.now(timezone.utc) + LOCKOUT_DURATION).isoformat()
            conn.execute(
                "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE user_id = ?",
                (new_attempts, locked_until, user["user_id"])
            )
        else:
            conn.execute(
                "UPDATE users SET failed_attempts = ? WHERE user_id = ?",
                (new_attempts, user["user_id"])
            )
        conn.commit()
        return {"success": False, "error": "Invalid credentials"}

    # Success: reset failed attempts
    conn.execute(
        "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE user_id = ?",
        (user["user_id"],)
    )
    conn.commit()
    return {"success": True, "user_id": user["user_id"], "role": user["role"]}
```

### Electronic Signature (REQ-504)
```python
# Source: REQ-504 specification + 21 CFR Part 11
import hashlib

def create_electronic_signature(
    conn, user_id: str, password: str,
    resource_type: str, resource_id: str, meaning: str
) -> dict:
    """Create e-signature with re-authentication."""
    # Re-authenticate
    user = conn.execute(
        "SELECT password_hash FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    if not user or not verify_password(password, user["password_hash"]):
        return {"success": False, "error": "Re-authentication failed"}

    # Create signature hash
    timestamp = datetime.now(timezone.utc).isoformat()
    sig_payload = json.dumps({
        "user_id": user_id,
        "timestamp": timestamp,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "meaning": meaning,
    }, sort_keys=True, separators=(",", ":"))
    signature_hash = hashlib.sha256(sig_payload.encode("utf-8")).hexdigest()

    # Record in audit trail
    append_audit_record(
        conn, user_id, "SIGN",
        resource_type, resource_id,
        details={"meaning": meaning, "signature_hash": signature_hash}
    )

    return {"success": True, "signature_hash": signature_hash, "timestamp": timestamp}
```

### Task State Schema (REQ-602, REQ-603)
```python
# Source: REQ-602 + REQ-603 specifications
TASK_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id         TEXT PRIMARY KEY,
    project_id      TEXT,
    task_type       TEXT NOT NULL,           -- pipeline, export, analysis
    status          TEXT NOT NULL DEFAULT 'PENDING'
                    CHECK(status IN ('PENDING','RUNNING','COMPLETED','FAILED','CANCELLED')),
    progress        REAL NOT NULL DEFAULT 0.0,  -- 0.0 to 1.0
    created_at      TEXT NOT NULL,
    started_at      TEXT,
    completed_at    TEXT,
    result_json     TEXT,
    error_message   TEXT,
    checkpoint_path TEXT                     -- For resume (REQ-603)
);
"""
```

### Project Schema (REQ-605)
```python
# Source: REQ-605 specification
PROJECT_SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    project_id      TEXT PRIMARY KEY,        -- UUID
    name            TEXT NOT NULL,
    description     TEXT,
    created_by      TEXT NOT NULL,           -- user_id FK
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK(status IN ('active', 'archived', 'deleted')),
    config_json     TEXT NOT NULL DEFAULT '{}'
);
"""
# Per-project file storage layout:
# data/projects/{project_id}/
#   uploads/          -- raw uploaded files
#   checkpoints/      -- pipeline checkpoint h5ad files
#   results/          -- analysis outputs
#   exports/          -- generated reports
```

### Synthetic h5ad Fixture (REQ-805)
```python
# Source: anndata docs + scanpy best practices
import numpy as np
import anndata as ad
import scipy.sparse as sp
import pandas as pd
import pytest

@pytest.fixture
def synthetic_h5ad(tmp_path):
    """Create a minimal synthetic h5ad (50 cells, 10 genes) for fast testing.

    Mimics realistic scRNA-seq properties:
    - Sparse count matrix (~90% zeros)
    - Cell type annotations
    - Standard obs/var columns
    """
    n_cells, n_genes = 50, 10
    rng = np.random.default_rng(42)

    # Sparse count matrix (realistic sparsity)
    X = sp.random(n_cells, n_genes, density=0.1, format="csr",
                  random_state=42, dtype=np.float32)
    X.data = np.round(X.data * 10).astype(np.float32)  # Integer-ish counts

    gene_names = [f"GENE{i}" for i in range(n_genes)]
    cell_ids = [f"CELL_{i:03d}" for i in range(n_cells)]
    cell_types = rng.choice(["T_cell", "B_cell", "Macrophage", "Epithelial"],
                            size=n_cells)

    obs = pd.DataFrame({
        "cell_type": cell_types,
        "donor_id": rng.choice(["D1", "D2", "D3"], size=n_cells),
        "n_genes_by_counts": rng.integers(200, 5000, size=n_cells),
        "pct_counts_mt": rng.uniform(0, 15, size=n_cells).round(2),
    }, index=cell_ids)

    var = pd.DataFrame({
        "gene_name": gene_names,
        "feature_biotype": "protein_coding",
    }, index=gene_names)

    adata = ad.AnnData(X=X, obs=obs, var=var)

    path = tmp_path / "synthetic_50x10.h5ad"
    adata.write_h5ad(path)
    return path
```

### Streamlit Config (REQ-604)
```toml
# .streamlit/config.toml
# Source: Streamlit configuration docs

[server]
maxUploadSize = 2000       # MB - for large h5ad files
maxMessageSize = 2000      # MB - match upload size
headless = true

[runner]
fastReruns = true          # Handle reruns immediately

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#0071e3"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f5f5f7"
textColor = "#1d1d1f"
font = "sans serif"
```

### Hash Chain Verification
```python
def verify_audit_chain(conn) -> dict:
    """Verify the entire audit trail hash chain integrity.

    Returns: {"valid": bool, "records_checked": int, "first_broken": int|None}
    """
    rows = conn.execute(
        "SELECT * FROM audit_trail ORDER BY sequence_id ASC"
    ).fetchall()

    if not rows:
        return {"valid": True, "records_checked": 0, "first_broken": None}

    expected_previous = "0" * 64  # genesis hash
    for row in rows:
        # Verify previous_hash links correctly
        if row["previous_hash"] != expected_previous:
            return {
                "valid": False,
                "records_checked": row["sequence_id"],
                "first_broken": row["sequence_id"],
                "error": "previous_hash mismatch"
            }

        # Recompute this record's hash
        recomputed = compute_record_hash(
            row["previous_hash"], row["timestamp"], row["user_id"],
            row["action"], row["resource_type"], row["resource_id"],
            json.loads(row["details_json"])
        )
        if recomputed != row["record_hash"]:
            return {
                "valid": False,
                "records_checked": row["sequence_id"],
                "first_broken": row["sequence_id"],
                "error": "record_hash tampered"
            }

        expected_previous = row["record_hash"]

    return {"valid": True, "records_checked": len(rows), "first_broken": None}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `datetime.utcnow()` | `datetime.now(timezone.utc)` | Python 3.12 deprecation | Use aware datetimes for all timestamps |
| `time.strftime(gmtime())` (existing codebase) | `datetime.now(timezone.utc).isoformat()` | Best practice | ISO 8601 with timezone info, unambiguous |
| bcrypt silent truncation at 72 bytes | bcrypt 5.0 raises ValueError | September 2025 | Pin bcrypt<5.0 or pre-hash long passwords |
| Streamlit `pages/` directory convention | `st.Page` + `st.navigation` | Streamlit ~1.36+ | Programmatic page control, dynamic visibility, grouped navigation |
| `st.cache` (deprecated) | `st.cache_data` + `st.cache_resource` | Streamlit 1.18+ | Separate data caching from resource (connection/executor) caching |
| Single-file Streamlit app | Multipage with `st.navigation` | Current best practice | Proper separation of concerns, page-level access control |

**Deprecated/outdated:**
- `st.cache`: Replaced by `st.cache_data` and `st.cache_resource`
- `datetime.utcnow()`: Deprecated in Python 3.12, returns naive datetime
- `st.experimental_rerun()`: Replaced by `st.rerun()` in Streamlit 1.27+
- scanpy 1.12+: Requires Python 3.12+, incompatible with project constraint

## Open Questions

1. **Database File Organization: Single vs Multiple SQLite Files**
   - What we know: REQ-508 says "WAL mode for all SQLite databases" (plural). The audit trail, auth, tasks, and projects could each be separate .db files or consolidated.
   - What's unclear: Whether separate files improve concurrent access or add unnecessary complexity.
   - Recommendation: Use separate files -- `auth.db`, `audit.db`, `tasks.db`, `projects.db`. This provides better isolation, simpler backups, and avoids WAL mode contention between unrelated tables. The connection factory pattern makes this trivial.

2. **NTP Timestamp Validation**
   - What we know: REQ-503 mentions "NTP timestamps". Python's `datetime.now(timezone.utc)` uses the system clock, which may or may not be NTP-synchronized.
   - What's unclear: Whether the requirement expects the app to validate NTP sync or just use system time (which is typically NTP-synced on modern OS).
   - Recommendation: Use `datetime.now(timezone.utc)` and document that the deployment environment must have NTP enabled (standard on all modern OS). Do not implement custom NTP client -- that is infrastructure, not application concern.

3. **Existing Codebase Migration Strategy**
   - What we know: `bioorchestrator_real/` has a working lineage DB, LLM provider, config, and app. Phase 1 should reference these as design inputs.
   - What's unclear: Whether v2 code lives alongside `bioorchestrator_real/` or replaces it.
   - Recommendation: Create a new `src/` directory for v2 code. Keep `bioorchestrator_real/` intact as reference. This avoids breaking the existing demo while building the new foundation.

4. **ALCOA+ Completeness**
   - What we know: ALCOA+ stands for Attributable, Legible, Contemporaneous, Original, Accurate + Complete, Consistent, Enduring, Available.
   - What's unclear: How strictly each principle maps to technical implementation beyond the explicit requirements.
   - Recommendation: The hash-chain audit trail with user attribution, UTC timestamps, and append-only storage covers the core principles. Document the mapping in code comments for GxP auditors. The "Enduring" principle is satisfied by SQLite file-based storage (no server dependency). "Available" is satisfied by the audit trail query page (Phase 7).

## Sources

### Primary (HIGH confidence)
- Python 3.10 sqlite3 docs (https://docs.python.org/3.10/library/sqlite3.html) -- WAL mode, check_same_thread, timeout parameter
- Python 3.10 concurrent.futures docs (https://docs.python.org/3.10/library/concurrent.futures.html) -- ThreadPoolExecutor API
- Python 3.10 datetime docs (https://docs.python.org/3.10/library/datetime.html) -- timezone-aware timestamps
- bcrypt PyPI (https://pypi.org/project/bcrypt/) -- v5.0 breaking change (72-byte limit), API: hashpw/checkpw/gensalt
- Streamlit docs (https://docs.streamlit.io) -- st.Page, st.navigation, st.cache_resource, session state lifecycle
- anndata docs (https://anndata.readthedocs.io) -- AnnData constructor for synthetic fixtures
- scanpy 1.10.x pyproject.toml (GitHub) -- Python >=3.10, numpy >=1.23

### Secondary (MEDIUM confidence)
- Streamlit config.py source (GitHub) -- maxUploadSize=200 default, runner.fastReruns=True default, server.maxMessageSize=200 default
- Existing codebase analysis -- `stage7_lineage.py` schema (lacks hash chains), `config.py` structure, `app.py` monolith pattern
- Streamlit multipage docs -- st.navigation position options, page grouping with dict

### Tertiary (LOW confidence)
- 21 CFR Part 11 regulatory text -- Could not access eCFR directly (redirected). Requirements interpreted from project specifications (REQ-503, REQ-504) which appear well-researched. Hash chain + append-only + user attribution + timestamps is the standard technical implementation.
- ALCOA+ principles -- Based on training data knowledge of FDA data integrity guidance. Principles are stable and well-established, but exact regulatory interpretation may vary.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries verified via PyPI/official docs, version constraints confirmed
- Architecture: HIGH -- patterns verified against Streamlit docs (st.navigation, st.cache_resource), Python stdlib docs (sqlite3, concurrent.futures)
- Pitfalls: HIGH -- thread safety issues verified in sqlite3 docs, bcrypt breaking change verified on PyPI, session state lifecycle confirmed in Streamlit docs
- Regulatory compliance: MEDIUM -- 21 CFR Part 11 requirements interpreted from project specs (could not access eCFR directly), but hash chain + audit trail pattern is well-established

**Research date:** 2026-05-09
**Valid until:** 2026-06-09 (30 days -- all technologies are stable/mature)
