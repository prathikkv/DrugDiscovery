"""Append-only audit trail with SHA-256 hash chain integrity (REQ-503).

Every state-changing action produces an immutable audit record.
Records are chained via SHA-256 hashes -- tampering with any record
breaks the chain and is detectable via verify_chain().

CRITICAL: This module intentionally provides NO update or delete
operations. The audit trail is append-only by regulatory design.
"""

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src import config
from src.compliance.db import init_audit_db
from src.db import get_connection


# Genesis hash -- used as previous_hash for the very first record
_GENESIS_HASH = "0" * 64


class AuditTrail:
    """21 CFR Part 11 compliant audit trail with hash chain integrity.

    Thread-safe: uses a lock to serialize the read-previous-hash,
    compute-hash, insert sequence (RESEARCH.md Pitfall 2).
    """

    def __init__(self, db_path: Path = None) -> None:
        self.db_path = db_path or config.AUDIT_DB
        self._write_lock = threading.Lock()

        # Ensure schema exists
        conn = get_connection(self.db_path)
        try:
            init_audit_db(conn)
        finally:
            conn.close()

    @staticmethod
    def _compute_record_hash(
        previous_hash: str,
        timestamp: str,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: str,
    ) -> str:
        """Compute SHA-256 hash of an audit record.

        Uses deterministic JSON serialization (sorted keys, compact
        separators) to ensure reproducible hashes.
        """
        payload = json.dumps(
            {
                "previous_hash": previous_hash,
                "timestamp": timestamp,
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def append_record(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict = None,
    ) -> str:
        """Append a new audit record and return its hash.

        The entire read-compute-insert sequence is serialized via a
        threading lock to guarantee hash chain ordering.
        """
        details_json = json.dumps(
            details or {},
            sort_keys=True,
            separators=(",", ":"),
        )
        timestamp = datetime.now(timezone.utc).isoformat()

        with self._write_lock:
            conn = get_connection(self.db_path)
            try:
                # Read previous hash
                row = conn.execute(
                    "SELECT record_hash FROM audit_trail "
                    "ORDER BY sequence_id DESC LIMIT 1"
                ).fetchone()
                previous_hash = row["record_hash"] if row else _GENESIS_HASH

                # Compute this record's hash
                record_hash = self._compute_record_hash(
                    previous_hash,
                    timestamp,
                    user_id,
                    action,
                    resource_type,
                    resource_id,
                    details_json,
                )

                # Insert
                conn.execute(
                    "INSERT INTO audit_trail "
                    "(timestamp, user_id, action, resource_type, resource_id, "
                    "details_json, previous_hash, record_hash) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        timestamp,
                        user_id,
                        action,
                        resource_type,
                        resource_id,
                        details_json,
                        previous_hash,
                        record_hash,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        return record_hash

    def verify_chain(self) -> dict:
        """Verify the integrity of the entire audit trail hash chain.

        Returns:
            {
                "valid": bool,
                "records_checked": int,
                "first_broken": Optional[int],  # sequence_id of first broken record
                "error": Optional[str],
            }
        """
        conn = get_connection(self.db_path)
        try:
            rows = conn.execute(
                "SELECT sequence_id, timestamp, user_id, action, "
                "resource_type, resource_id, details_json, "
                "previous_hash, record_hash "
                "FROM audit_trail ORDER BY sequence_id ASC"
            ).fetchall()
        finally:
            conn.close()

        if not rows:
            return {
                "valid": True,
                "records_checked": 0,
                "first_broken": None,
                "error": None,
            }

        expected_previous = _GENESIS_HASH

        for row in rows:
            # Check previous_hash linkage
            if row["previous_hash"] != expected_previous:
                return {
                    "valid": False,
                    "records_checked": row["sequence_id"],
                    "first_broken": row["sequence_id"],
                    "error": (
                        f"Record {row['sequence_id']}: previous_hash mismatch. "
                        f"Expected {expected_previous}, "
                        f"got {row['previous_hash']}"
                    ),
                }

            # Recompute and verify record_hash
            computed = self._compute_record_hash(
                row["previous_hash"],
                row["timestamp"],
                row["user_id"],
                row["action"],
                row["resource_type"],
                row["resource_id"],
                row["details_json"],
            )
            if computed != row["record_hash"]:
                return {
                    "valid": False,
                    "records_checked": row["sequence_id"],
                    "first_broken": row["sequence_id"],
                    "error": (
                        f"Record {row['sequence_id']}: record_hash mismatch. "
                        f"Expected {computed}, got {row['record_hash']}"
                    ),
                }

            expected_previous = row["record_hash"]

        return {
            "valid": True,
            "records_checked": len(rows),
            "first_broken": None,
            "error": None,
        }

    def get_records(
        self,
        user_id: str = None,
        resource_type: str = None,
        resource_id: str = None,
        limit: int = 100,
    ) -> list[dict]:
        """Query audit records with optional filters.

        Returns list of dicts ordered by sequence_id DESC (newest first).
        """
        conditions = []
        params: list = []

        if user_id is not None:
            conditions.append("user_id = ?")
            params.append(user_id)
        if resource_type is not None:
            conditions.append("resource_type = ?")
            params.append(resource_type)
        if resource_id is not None:
            conditions.append("resource_id = ?")
            params.append(resource_id)

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        query = (
            f"SELECT * FROM audit_trail {where} "
            f"ORDER BY sequence_id DESC LIMIT ?"
        )
        params.append(limit)

        conn = get_connection(self.db_path)
        try:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
