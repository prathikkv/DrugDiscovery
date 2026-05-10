"""Evidence integration subsystem for BioOrchestrator v2.

Public API exports for evidence sources, models, cache, and gene resolution.
"""

from src.evidence.models import (
    AggregatedEvidence,
    EvidenceResult,
    GeneIdentifiers,
    SourceStatus,
)
from src.evidence.interface import EvidenceSource

__all__ = [
    "AggregatedEvidence",
    "EvidenceCache",
    "EvidenceResult",
    "EvidenceSource",
    "GeneIdentifiers",
    "GeneResolver",
    "SourceStatus",
]


def __getattr__(name: str):
    """Lazy imports for modules created in later tasks."""
    if name == "EvidenceCache":
        from src.evidence.cache import EvidenceCache
        return EvidenceCache
    if name == "GeneResolver":
        from src.evidence.gene_resolver import GeneResolver
        return GeneResolver
    raise AttributeError(f"module 'src.evidence' has no attribute {name!r}")
