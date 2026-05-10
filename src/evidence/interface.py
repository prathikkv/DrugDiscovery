"""Evidence source protocol defining the contract for all evidence integrations."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.evidence.models import EvidenceResult, GeneIdentifiers


@runtime_checkable
class EvidenceSource(Protocol):
    """Protocol for evidence source implementations.

    All evidence sources must implement this interface to be registered
    with the aggregator. The Protocol is runtime-checkable, allowing
    isinstance() verification at registration time.

    The fetch() method receives GeneIdentifiers (not raw symbol) because
    the GeneResolver runs first, providing Ensembl IDs and UniProt
    accessions needed by sources like OpenTargets and ChEMBL.
    """

    @property
    def source_name(self) -> str:
        """Unique identifier for this evidence source."""
        ...

    @property
    def source_version(self) -> str:
        """Version string for this source's API/data."""
        ...

    def fetch(
        self,
        gene: GeneIdentifiers,
        disease_context: str | None = None,
    ) -> EvidenceResult:
        """Fetch evidence for a gene, optionally in a disease context.

        Args:
            gene: Resolved gene identifiers with canonical symbol and IDs.
            disease_context: Optional disease/indication string for context.

        Returns:
            EvidenceResult with confidence score and data payload.
        """
        ...

    def is_available(self) -> bool:
        """Check if this source is reachable and responding.

        Returns:
            True if the source can be queried successfully.
        """
        ...
