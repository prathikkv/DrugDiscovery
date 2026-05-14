"""Tests for the evidence cache module.

Validates TTL-based expiration, invalidation strategies, and error result
exclusion from cache.
"""

from __future__ import annotations

import time

import pytest

pytestmark = pytest.mark.integration

from src.evidence.models import EvidenceResult


class TestCachePutAndGet:
    """Tests for basic cache put/get operations."""

    def test_put_and_get(self, tmp_cache, mock_evidence_result):
        """Store result, retrieve it, assert equal."""
        tmp_cache.put("EGFR", "test_source", mock_evidence_result)
        retrieved = tmp_cache.get("EGFR", "test_source")

        assert retrieved is not None
        assert retrieved.source_name == mock_evidence_result.source_name
        assert retrieved.confidence == mock_evidence_result.confidence
        assert retrieved.data == mock_evidence_result.data

    def test_get_returns_none_for_missing(self, tmp_cache):
        """Query nonexistent key returns None."""
        result = tmp_cache.get("NONEXISTENT", "nonexistent_source")
        assert result is None

    def test_error_results_not_cached(self, tmp_cache):
        """Put result with confidence=0.0 should not be stored."""
        error_result = EvidenceResult(
            source_name="test_source",
            confidence=0.0,
            data=None,
            error="Some error",
            fetched_at=time.time(),
        )
        tmp_cache.put("EGFR", "test_source", error_result)
        retrieved = tmp_cache.get("EGFR", "test_source")
        assert retrieved is None


class TestCacheTTL:
    """Tests for TTL-based expiration."""

    def test_ttl_expiration(self, tmp_cache, mock_evidence_result):
        """Store with short TTL, wait past expiry, assert None returned."""
        # tmp_cache has 2-second TTL
        tmp_cache.put("EGFR", "test_source", mock_evidence_result)

        # Immediately should be retrievable
        assert tmp_cache.get("EGFR", "test_source") is not None

        # Wait past TTL
        time.sleep(2.5)

        # Now should be expired
        assert tmp_cache.get("EGFR", "test_source") is None

    def test_cleanup_expired(self, tmp_cache, mock_evidence_result):
        """Store with past expiry, call cleanup_expired, verify removed."""
        tmp_cache.put("EGFR", "test_source", mock_evidence_result)

        # Wait past TTL
        time.sleep(2.5)

        # Verify it's expired (get returns None)
        assert tmp_cache.get("EGFR", "test_source") is None

        # Cleanup should remove it
        removed = tmp_cache.cleanup_expired()
        assert removed >= 1

        # get_stale should also return None now (physically removed)
        assert tmp_cache.get_stale("EGFR", "test_source") is None


class TestCacheInvalidation:
    """Tests for cache invalidation operations."""

    def test_invalidate_by_gene(self, tmp_cache):
        """Store 2 sources for same gene, invalidate by gene, both gone."""
        result_a = EvidenceResult(
            source_name="source_a", confidence=1.0, data={"a": 1}, fetched_at=time.time()
        )
        result_b = EvidenceResult(
            source_name="source_b", confidence=1.0, data={"b": 2}, fetched_at=time.time()
        )
        tmp_cache.put("EGFR", "source_a", result_a)
        tmp_cache.put("EGFR", "source_b", result_b)

        deleted = tmp_cache.invalidate(gene_symbol="EGFR")
        assert deleted == 2
        assert tmp_cache.get("EGFR", "source_a") is None
        assert tmp_cache.get("EGFR", "source_b") is None

    def test_invalidate_by_source(self, tmp_cache):
        """Store same source for 2 genes, invalidate by source, both gone."""
        result_1 = EvidenceResult(
            source_name="opentargets", confidence=1.0, data={"x": 1}, fetched_at=time.time()
        )
        result_2 = EvidenceResult(
            source_name="opentargets", confidence=1.0, data={"x": 2}, fetched_at=time.time()
        )
        tmp_cache.put("EGFR", "opentargets", result_1)
        tmp_cache.put("BRCA1", "opentargets", result_2)

        deleted = tmp_cache.invalidate(source_name="opentargets")
        assert deleted == 2
        assert tmp_cache.get("EGFR", "opentargets") is None
        assert tmp_cache.get("BRCA1", "opentargets") is None

    def test_invalidate_all(self, tmp_cache):
        """Store multiple entries, invalidate with no args, all gone."""
        result_a = EvidenceResult(
            source_name="source_a", confidence=1.0, data={"a": 1}, fetched_at=time.time()
        )
        result_b = EvidenceResult(
            source_name="source_b", confidence=0.8, data={"b": 2}, fetched_at=time.time()
        )
        tmp_cache.put("EGFR", "source_a", result_a)
        tmp_cache.put("BRCA1", "source_b", result_b)

        deleted = tmp_cache.invalidate()
        assert deleted == 2
        assert tmp_cache.get("EGFR", "source_a") is None
        assert tmp_cache.get("BRCA1", "source_b") is None
