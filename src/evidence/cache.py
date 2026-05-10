"""SQLite-backed evidence cache with TTL expiration and manual invalidation.

Follows project patterns:
- Per-operation connections (fresh connection, try/finally close)
- BEGIN IMMEDIATE for write atomicity under WAL mode
- get_connection() from src.db for consistent pragmas
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from src import config
from src.db import get_connection
from src.evidence.models import EvidenceResult


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS evidence_cache (
    gene_symbol TEXT NOT NULL,
    source_name TEXT NOT NULL,
    fetched_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    data_json TEXT NOT NULL,
    PRIMARY KEY (gene_symbol, source_name)
);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON evidence_cache(expires_at);
"""


class EvidenceCache:
    """SQLite evidence cache with configurable TTL and invalidation.

    Stores EvidenceResult objects keyed by (gene_symbol, source_name) with
    automatic TTL-based expiration. Supports stale reads for fallback when
    live fetches fail (REQ-210 step 2).

    Args:
        db_path: Path to SQLite database file. Defaults to config.EVIDENCE_CACHE_DB.
        ttl_seconds: Time-to-live for cached entries in seconds. Default 24 hours.
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        ttl_seconds: int = 86400,
    ) -> None:
        self._db_path = db_path or config.EVIDENCE_CACHE_DB
        self._ttl_seconds = ttl_seconds
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create cache table and indexes if they don't exist."""
        conn = get_connection(self._db_path)
        try:
            conn.executescript(_SCHEMA_SQL)
        finally:
            conn.close()

    def get(self, gene_symbol: str, source_name: str) -> Optional[EvidenceResult]:
        """Retrieve a cached result if it exists and has not expired.

        Args:
            gene_symbol: Gene symbol key (e.g., 'EGFR')
            source_name: Evidence source identifier (e.g., 'opentargets')

        Returns:
            EvidenceResult if found and not expired, None otherwise.
        """
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT data_json, expires_at FROM evidence_cache "
                "WHERE gene_symbol = ? AND source_name = ?",
                (gene_symbol, source_name),
            ).fetchone()

            if row is None:
                return None

            # Check TTL expiration
            if time.time() > row["expires_at"]:
                return None

            return EvidenceResult.from_json(row["data_json"])
        finally:
            conn.close()

    def get_stale(self, gene_symbol: str, source_name: str) -> Optional[EvidenceResult]:
        """Retrieve a cached result ignoring TTL expiration.

        Used as fallback when live fetch fails after retry exhaustion (REQ-210
        step 2). Returns the cached entry even if expired (stale).

        Args:
            gene_symbol: Gene symbol key
            source_name: Evidence source identifier

        Returns:
            EvidenceResult with is_fallback=True if found, None if no entry exists.
        """
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT data_json FROM evidence_cache "
                "WHERE gene_symbol = ? AND source_name = ?",
                (gene_symbol, source_name),
            ).fetchone()

            if row is None:
                return None

            result = EvidenceResult.from_json(row["data_json"])
            result.is_fallback = True
            return result
        finally:
            conn.close()

    def put(
        self,
        gene_symbol: str,
        source_name: str,
        result: EvidenceResult,
    ) -> None:
        """Store an evidence result in the cache.

        Only caches results with confidence > 0.0 (error results with zero
        confidence are never cached, per research anti-pattern guidance).

        Args:
            gene_symbol: Gene symbol key
            source_name: Evidence source identifier
            result: EvidenceResult to cache
        """
        # Do NOT cache error results (confidence == 0.0)
        if result.confidence <= 0.0:
            return

        now = time.time()
        expires_at = now + self._ttl_seconds
        data_json = result.to_json()

        conn = get_connection(self._db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT OR REPLACE INTO evidence_cache "
                "(gene_symbol, source_name, fetched_at, expires_at, data_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (gene_symbol, source_name, now, expires_at, data_json),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def invalidate(
        self,
        gene_symbol: Optional[str] = None,
        source_name: Optional[str] = None,
    ) -> int:
        """Delete cached entries matching the given filters.

        Args:
            gene_symbol: If provided, delete only entries for this gene.
            source_name: If provided, delete only entries from this source.
            If both None, deletes ALL entries.

        Returns:
            Number of rows deleted.
        """
        conn = get_connection(self._db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")

            conditions = []
            params: list = []

            if gene_symbol is not None:
                conditions.append("gene_symbol = ?")
                params.append(gene_symbol)
            if source_name is not None:
                conditions.append("source_name = ?")
                params.append(source_name)

            where_clause = ""
            if conditions:
                where_clause = " WHERE " + " AND ".join(conditions)

            cursor = conn.execute(
                f"DELETE FROM evidence_cache{where_clause}",
                params,
            )
            conn.commit()
            return cursor.rowcount
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def cleanup_expired(self) -> int:
        """Delete all expired entries from the cache.

        Returns:
            Number of rows deleted.
        """
        conn = get_connection(self._db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                "DELETE FROM evidence_cache WHERE expires_at < ?",
                (time.time(),),
            )
            conn.commit()
            return cursor.rowcount
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
