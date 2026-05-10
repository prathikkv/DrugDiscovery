"""Evidence integration subsystem for BioOrchestrator v2.

Public API exports for evidence sources, models, cache, gene resolution,
and the aggregator orchestrator.
"""

from src.evidence.aggregator import EvidenceAggregator
from src.evidence.models import (
    AggregatedEvidence,
    EvidenceResult,
    GeneIdentifiers,
    SourceStatus,
)
from src.evidence.interface import EvidenceSource
from src.evidence.cache import EvidenceCache
from src.evidence.gene_resolver import GeneResolver


def gather_evidence(gene_symbol: str, disease_context: str | None = None) -> AggregatedEvidence:
    """Convenience function: resolve gene, fetch all sources, return aggregated evidence.

    This is the primary public API for Phase 3. Creates a default EvidenceAggregator
    and calls gather() with the given parameters.

    Args:
        gene_symbol: Gene symbol or alias (e.g., 'EGFR', 'PD-L1').
        disease_context: Optional disease/indication string for context.

    Returns:
        AggregatedEvidence with results from all 6 sources.
    """
    aggregator = EvidenceAggregator()
    return aggregator.gather(gene_symbol, disease_context)


__all__ = [
    "AggregatedEvidence",
    "EvidenceAggregator",
    "EvidenceCache",
    "EvidenceResult",
    "EvidenceSource",
    "GeneIdentifiers",
    "GeneResolver",
    "SourceStatus",
    "gather_evidence",
]
