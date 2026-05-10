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
from src.evidence.cache import EvidenceCache
from src.evidence.gene_resolver import GeneResolver

__all__ = [
    "AggregatedEvidence",
    "EvidenceCache",
    "EvidenceResult",
    "EvidenceSource",
    "GeneIdentifiers",
    "GeneResolver",
    "SourceStatus",
]
