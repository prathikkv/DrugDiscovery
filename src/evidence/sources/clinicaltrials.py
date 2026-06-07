"""ClinicalTrials.gov v2 REST API evidence source.

Fetches active and recruiting clinical trials filtered by disease condition
and drug intervention names (from DGIdb via aggregator two-phase fetch, REQ-204).
Uses the v2 API exclusively -- v1 was retired June 2024.
"""

from __future__ import annotations

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.evidence.models import EvidenceResult, GeneIdentifiers


class ClinicalTrialsSource:
    """Evidence source querying ClinicalTrials.gov v2 REST API.

    Fetches active/recruiting trials filtered by condition and drug names.
    The drug_names kwarg is populated by the aggregator's two-phase fetch
    after DGIdb returns known drug interactions for the gene (REQ-204).
    """

    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

    def __init__(self, max_results: int = 50) -> None:
        self._max_results = max_results

    @property
    def source_name(self) -> str:
        """Unique identifier for this evidence source."""
        return "clinicaltrials"

    @property
    def source_version(self) -> str:
        """Version string for this source's API/data."""
        return "v2"

    def fetch(
        self,
        gene: GeneIdentifiers,
        disease_context: str | None = None,
        drug_names: list[str] | None = None,
    ) -> EvidenceResult:
        """Fetch active clinical trials for a gene/disease/drug combination.

        Args:
            gene: Resolved gene identifiers.
            disease_context: Disease or condition string for filtering.
            drug_names: Drug names from DGIdb (passed by aggregator two-phase fetch).

        Returns:
            EvidenceResult with trial data and confidence score.
        """
        try:
            # Build condition query
            condition_query = disease_context if disease_context else f"{gene.canonical_symbol} target"

            # Build params
            params: dict = {
                "query.cond": condition_query,
                "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING,NOT_YET_RECRUITING",
                "pageSize": min(self._max_results, 100),
                "format": "json",
            }

            # Build intervention filter (REQ-204: filter by drug names from DGIdb)
            intervention_used = None
            if drug_names:
                intervention_used = " OR ".join(drug_names[:5])
                params["query.intr"] = intervention_used
            elif disease_context and gene.canonical_symbol:
                intervention_used = gene.canonical_symbol
                params["query.intr"] = intervention_used

            # Fetch studies with pagination
            studies = self._fetch_studies(params)

            # Parse each study
            trials = []
            for study in studies:
                protocol = study.get("protocolSection", {})
                id_module = protocol.get("identificationModule", {})
                status_module = protocol.get("statusModule", {})
                design_module = protocol.get("designModule", {})
                sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
                conditions_module = protocol.get("conditionsModule", {})
                arms_module = protocol.get("armsInterventionsModule", {})

                trial = {
                    "nctId": id_module.get("nctId", ""),
                    "briefTitle": id_module.get("briefTitle", ""),
                    "overallStatus": status_module.get("overallStatus", ""),
                    "phases": design_module.get("phases", []),
                    "leadSponsor": sponsor_module.get("leadSponsor", {}).get("name", ""),
                    "conditions": conditions_module.get("conditions", []),
                    "interventions": [
                        i.get("name", "")
                        for i in arms_module.get("interventions", [])
                    ],
                }
                trials.append(trial)

            # Build result data
            data = {
                "trials": trials,
                "total_count": len(trials),
                "query_condition": condition_query,
                "query_intervention": intervention_used,
                "drug_names_used": drug_names[:5] if drug_names else None,
            }

            # Set confidence
            confidence = 1.0 if trials else 0.5

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
        retry=retry_if_exception_type((ConnectionError, requests.exceptions.Timeout, requests.exceptions.HTTPError)),
    )
    def _fetch_studies(self, params: dict) -> list[dict]:
        """Fetch studies from ClinicalTrials.gov v2 API with pagination.

        Args:
            params: Query parameters for the API request.

        Returns:
            List of raw study dictionaries.
        """
        studies: list[dict] = []
        current_params = dict(params)

        while len(studies) < self._max_results:
            resp = requests.get(self.BASE_URL, params=current_params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            batch = data.get("studies", [])
            studies.extend(batch)

            # Check for next page
            next_token = data.get("nextPageToken")
            if not next_token or not batch:
                break

            current_params["pageToken"] = next_token

        return studies[: self._max_results]

    def is_available(self) -> bool:
        """Check if ClinicalTrials.gov v2 API is reachable.

        Returns:
            True if the API responds with HTTP 200.
        """
        try:
            resp = requests.get(
                self.BASE_URL,
                params={"pageSize": 1, "format": "json"},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False
