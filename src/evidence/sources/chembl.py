"""ChEMBL evidence source via Python client.

Fetches bioactivity data (pChEMBL values), compounds, and mechanism of action
using the chembl_webresource_client. CRITICAL: ChEMBL does NOT support gene
symbol lookup directly -- must resolve UniProt accession to ChEMBL target ID
first (research pitfall 3).
"""

from __future__ import annotations

from chembl_webresource_client.new_client import new_client
from tenacity import retry, stop_after_attempt, wait_exponential

from src.evidence.models import EvidenceResult, GeneIdentifiers


class ChEMBLSource:
    """Evidence source querying ChEMBL for chemical tractability data.

    Resolves UniProt accession -> ChEMBL target ID, then fetches top 50
    bioactivities ranked by pChEMBL value and mechanism of action data
    for the target (REQ-206).
    """

    @property
    def source_name(self) -> str:
        """Unique identifier for this evidence source."""
        return "chembl"

    @property
    def source_version(self) -> str:
        """Version string for this source's API/data."""
        return "34"

    def fetch(
        self,
        gene: GeneIdentifiers,
        disease_context: str | None = None,
    ) -> EvidenceResult:
        """Fetch bioactivity and mechanism data from ChEMBL.

        Args:
            gene: Resolved gene identifiers (requires uniprot_accession).
            disease_context: Optional disease context (unused for ChEMBL queries).

        Returns:
            EvidenceResult with activity/mechanism data and confidence score.
        """
        try:
            # ChEMBL requires UniProt accession for target lookup
            if gene.uniprot_accession is None:
                return EvidenceResult(
                    source_name=self.source_name,
                    confidence=0.0,
                    error="No UniProt accession available for ChEMBL target lookup",
                )

            # Resolve UniProt accession to ChEMBL target
            target_info = self._find_target(gene.uniprot_accession)
            if target_info is None:
                return EvidenceResult(
                    source_name=self.source_name,
                    confidence=0.0,
                    error="Target not found in ChEMBL",
                )

            target_chembl_id, target_type = target_info

            # Fetch top 50 bioactivities by pChEMBL value
            activities = self._fetch_activities(target_chembl_id)

            # Fetch mechanism of action data
            mechanisms = self._fetch_mechanisms(target_chembl_id)

            # Compute statistics from activities
            pchembl_values = []
            activity_records = []
            for act in activities:
                record = {
                    "molecule_chembl_id": act.get("molecule_chembl_id", ""),
                    "pchembl_value": act.get("pchembl_value"),
                    "standard_type": act.get("standard_type", ""),
                    "canonical_smiles": act.get("canonical_smiles", ""),
                }
                activity_records.append(record)

                pval = act.get("pchembl_value")
                if pval is not None:
                    try:
                        pchembl_values.append(float(pval))
                    except (ValueError, TypeError):
                        pass

            mean_pchembl = (
                sum(pchembl_values) / len(pchembl_values) if pchembl_values else None
            )
            max_pchembl = max(pchembl_values) if pchembl_values else None

            # Build mechanism records
            mechanism_records = []
            for mech in mechanisms:
                mechanism_records.append({
                    "mechanism_of_action": mech.get("mechanism_of_action", ""),
                    "action_type": mech.get("action_type", ""),
                    "molecule_chembl_id": mech.get("molecule_chembl_id", ""),
                    "max_phase": mech.get("max_phase"),
                })

            # Build data dict
            data = {
                "target_chembl_id": target_chembl_id,
                "target_type": target_type,
                "activities": activity_records,
                "mechanisms": mechanism_records,
                "activity_count": len(activity_records),
                "mean_pchembl": mean_pchembl,
                "max_pchembl": max_pchembl,
            }

            # Set confidence
            confidence = 1.0 if activity_records else 0.5

            return EvidenceResult(
                source_name=self.source_name,
                confidence=confidence,
                data=data,
            )

        except Exception as exc:
            return EvidenceResult(
                source_name=self.source_name,
                confidence=0.0,
                error=str(exc),
                is_fallback=True,
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    def _find_target(self, uniprot_accession: str) -> tuple[str, str] | None:
        """Resolve UniProt accession to ChEMBL target ID.

        Args:
            uniprot_accession: UniProt Swiss-Prot accession (e.g., Q9NZQ7).

        Returns:
            Tuple of (target_chembl_id, target_type) or None if not found.
        """
        results = new_client.target.filter(
            target_components__accession=uniprot_accession
        )
        # QuerySet is lazy -- iterate to trigger fetch
        targets = list(results[:5])
        if targets:
            target = targets[0]
            return (
                target.get("target_chembl_id", ""),
                target.get("target_type", ""),
            )
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    def _fetch_activities(self, target_chembl_id: str) -> list[dict]:
        """Fetch top 50 bioactivities for a ChEMBL target.

        Args:
            target_chembl_id: ChEMBL target identifier (e.g., CHEMBL203).

        Returns:
            List of activity dictionaries with pChEMBL values.
        """
        activities = new_client.activity.filter(
            target_chembl_id=target_chembl_id,
            pchembl_value__isnull=False,
        ).only(
            "molecule_chembl_id",
            "pchembl_value",
            "standard_type",
            "standard_value",
            "standard_units",
            "canonical_smiles",
        )[:50]
        return list(activities)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    def _fetch_mechanisms(self, target_chembl_id: str) -> list[dict]:
        """Fetch mechanism of action data for a ChEMBL target.

        Args:
            target_chembl_id: ChEMBL target identifier (e.g., CHEMBL203).

        Returns:
            List of mechanism dictionaries.
        """
        mechanisms = new_client.mechanism.filter(
            target_chembl_id=target_chembl_id
        )
        return list(mechanisms)

    def is_available(self) -> bool:
        """Check if ChEMBL API is reachable.

        Returns:
            True if a known target (EGFR/CHEMBL203) can be queried.
        """
        try:
            results = new_client.target.filter(target_chembl_id="CHEMBL203")[:1]
            return len(list(results)) > 0
        except Exception:
            return False
