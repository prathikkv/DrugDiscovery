"""Shared fixtures for evidence integration tests."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.evidence.cache import EvidenceCache
from src.evidence.models import EvidenceResult, GeneIdentifiers


@pytest.fixture
def tmp_cache(tmp_path: Path) -> EvidenceCache:
    """EvidenceCache with a temporary database and short TTL (2 seconds) for expiration tests."""
    db_path = tmp_path / "test_cache.db"
    return EvidenceCache(db_path=db_path, ttl_seconds=2)


@pytest.fixture
def mock_gene_identifiers() -> GeneIdentifiers:
    """Standard mock gene identifiers for EGFR."""
    return GeneIdentifiers(
        canonical_symbol="EGFR",
        ensembl_id="ENSG00000146648",
        uniprot_accession="P00533",
        query_symbol="EGFR",
    )


@pytest.fixture
def mock_evidence_result() -> EvidenceResult:
    """Standard mock evidence result with full confidence and sample data."""
    return EvidenceResult(
        source_name="test_source",
        confidence=1.0,
        data={"key": "value", "interactions": [{"drug_name": "Erlotinib"}]},
        error=None,
        is_fallback=False,
        fetched_at=time.time(),
    )


@pytest.fixture
def mock_source():
    """Factory for creating mock evidence sources.

    Returns a factory function that creates a mock source with configurable:
    - source_name: str (default "test_source")
    - return_value: EvidenceResult to return from fetch()
    - should_raise: Exception to raise from fetch() (overrides return_value)
    """

    def _factory(
        source_name: str = "test_source",
        return_value: EvidenceResult | None = None,
        should_raise: Exception | None = None,
    ):
        source = MagicMock()
        source.source_name = source_name
        source.source_version = "test"

        if should_raise is not None:
            source.fetch.side_effect = should_raise
        elif return_value is not None:
            source.fetch.return_value = return_value
        else:
            source.fetch.return_value = EvidenceResult(
                source_name=source_name,
                confidence=1.0,
                data={"test": True},
                fetched_at=time.time(),
            )

        return source

    return _factory
