"""Evidence data models: results, gene identifiers, and aggregation containers."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GeneIdentifiers:
    """Resolved gene identity with canonical symbol and cross-references.

    Attributes:
        canonical_symbol: Official HGNC gene symbol (e.g., CD274)
        ensembl_id: Ensembl gene ID (e.g., ENSG00000120217) or None
        uniprot_accession: UniProt Swiss-Prot accession (e.g., Q9NZQ7) or None
        query_symbol: The original user-provided input symbol (e.g., PD-L1)
    """

    canonical_symbol: str
    ensembl_id: Optional[str] = None
    uniprot_accession: Optional[str] = None
    query_symbol: str = ""


@dataclass
class EvidenceResult:
    """Single evidence source result with confidence scoring.

    Attributes:
        source_name: Identifier of the evidence source (e.g., 'opentargets')
        confidence: Confidence score from 0.0 (no data/error) to 1.0 (strong)
        data: Parsed evidence data payload, or None on error
        error: Error description if fetch failed, or None on success
        is_fallback: True if this result came from stale cache (expired TTL)
        fetched_at: Unix timestamp when data was fetched
    """

    source_name: str
    confidence: float
    data: Optional[dict] = None
    error: Optional[str] = None
    is_fallback: bool = False
    fetched_at: float = field(default_factory=time.time)

    def to_json(self) -> str:
        """Serialize to deterministic JSON string."""
        return json.dumps(
            {
                "source_name": self.source_name,
                "confidence": self.confidence,
                "data": self.data,
                "error": self.error,
                "is_fallback": self.is_fallback,
                "fetched_at": self.fetched_at,
            },
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "EvidenceResult":
        """Deserialize from JSON string."""
        obj = json.loads(json_str)
        return cls(
            source_name=obj["source_name"],
            confidence=obj["confidence"],
            data=obj.get("data"),
            error=obj.get("error"),
            is_fallback=obj.get("is_fallback", False),
            fetched_at=obj["fetched_at"],
        )


@dataclass
class SourceStatus:
    """Health status of an evidence source.

    Attributes:
        source_name: Identifier of the evidence source
        available: Whether the source responded successfully
        last_checked: Unix timestamp of last availability check
    """

    source_name: str
    available: bool
    last_checked: float = field(default_factory=time.time)


@dataclass
class AggregatedEvidence:
    """Combined evidence from multiple sources for a single gene.

    Attributes:
        gene: Resolved gene identifiers
        disease_context: Optional disease/indication context for the query
        results: Map of source_name -> EvidenceResult
        fetched_at: Unix timestamp when aggregation completed
        sources_available: Count of sources that responded successfully
        sources_failed: Count of sources that failed or returned errors
    """

    gene: GeneIdentifiers
    disease_context: Optional[str] = None
    results: dict = field(default_factory=dict)
    fetched_at: float = field(default_factory=time.time)
    sources_available: int = 0
    sources_failed: int = 0

    @property
    def all_successful(self) -> bool:
        """True if no sources failed during aggregation."""
        return self.sources_failed == 0
