"""OpenTargets Platform GraphQL evidence source.

Fetches target information, tractability scores, known drugs, and disease
associations using the OpenTargets Platform API v4 GraphQL endpoint.
"""

from __future__ import annotations

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.evidence.models import EvidenceResult, GeneIdentifiers

BASE_URL = "https://api.platform.opentargets.org/api/v4/graphql"

QUERY_TARGET = """
query TargetInfo($ensemblId: String!) {
  target(ensemblId: $ensemblId) {
    approvedSymbol
    approvedName
    biotype
    tractability {
      label
      modality
      value
    }
    knownDrugs {
      uniqueDrugs
      rows {
        drug {
          name
          mechanismsOfAction {
            rows {
              mechanismOfAction
            }
          }
        }
        disease {
          name
        }
        phase
        status
      }
    }
  }
}
"""

QUERY_ASSOCIATIONS = """
query TargetAssociations($ensemblId: String!, $size: Int!) {
  target(ensemblId: $ensemblId) {
    associatedDiseases(page: {size: $size, index: 0}) {
      rows {
        disease {
          id
          name
        }
        score
        datatypeScores {
          id
          score
        }
      }
    }
  }
}
"""


class OpenTargetsSource:
    """Evidence source querying OpenTargets Platform API v4 GraphQL.

    Fetches target information (gene details, tractability, known drugs)
    and top 25 disease associations by overall score.
    """

    @property
    def source_name(self) -> str:
        """Unique identifier for this evidence source."""
        return "opentargets"

    @property
    def source_version(self) -> str:
        """Version string for this source's API/data."""
        return "v4"

    def fetch(
        self,
        gene: GeneIdentifiers,
        disease_context: str | None = None,
    ) -> EvidenceResult:
        """Fetch evidence for a gene from OpenTargets Platform.

        Args:
            gene: Resolved gene identifiers (requires ensembl_id).
            disease_context: Optional disease name to highlight in associations.

        Returns:
            EvidenceResult with target info, tractability, known drugs, and associations.
        """
        try:
            if gene.ensembl_id is None:
                return EvidenceResult(
                    source_name=self.source_name,
                    confidence=0.0,
                    error="No Ensembl ID available for OpenTargets query",
                )

            # Fetch target info (symbol, name, tractability, known drugs)
            target_response = self._query(
                QUERY_TARGET, {"ensemblId": gene.ensembl_id}
            )
            target_data = target_response.get("data", {}).get("target", {})

            # Fetch top 25 disease associations
            assoc_response = self._query(
                QUERY_ASSOCIATIONS, {"ensemblId": gene.ensembl_id, "size": 25}
            )
            assoc_data = (
                assoc_response.get("data", {})
                .get("target", {})
                .get("associatedDiseases", {})
                .get("rows", [])
            )

            # Extract tractability list
            tractability_list = target_data.get("tractability", []) or []

            # Extract known drugs
            known_drugs_data = target_data.get("knownDrugs", {}) or {}
            drugs_rows = known_drugs_data.get("rows", []) or []
            drugs_list = []
            for row in drugs_rows:
                drug_info = row.get("drug", {}) or {}
                moa_rows = (
                    drug_info.get("mechanismsOfAction", {}) or {}
                ).get("rows", []) or []
                mechanisms = [r.get("mechanismOfAction", "") for r in moa_rows]
                drugs_list.append(
                    {
                        "drug_name": drug_info.get("name", ""),
                        "mechanisms_of_action": mechanisms,
                        "disease": (row.get("disease", {}) or {}).get("name", ""),
                        "phase": row.get("phase"),
                        "status": row.get("status", ""),
                    }
                )

            # Process associations
            associations = []
            for assoc in assoc_data:
                disease_info = assoc.get("disease", {}) or {}
                entry = {
                    "disease_id": disease_info.get("id", ""),
                    "disease_name": disease_info.get("name", ""),
                    "overall_score": assoc.get("score", 0.0),
                    "datatype_scores": assoc.get("datatypeScores", []) or [],
                }
                # Flag disease context relevance if provided
                if disease_context:
                    entry["context_relevant"] = (
                        disease_context.lower() in disease_info.get("name", "").lower()
                    )
                associations.append(entry)

            # Build result data
            data = {
                "target": {
                    "approved_symbol": target_data.get("approvedSymbol", ""),
                    "approved_name": target_data.get("approvedName", ""),
                    "biotype": target_data.get("biotype", ""),
                },
                "associations": associations,
                "tractability": tractability_list,
                "known_drugs": drugs_list,
                "disease_association_count": len(associations),
            }

            return EvidenceResult(
                source_name=self.source_name,
                confidence=1.0,
                data=data,
            )

        except Exception as e:
            return EvidenceResult(
                source_name=self.source_name,
                confidence=0.0,
                error=str(e),
                is_fallback=True,
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
    )
    def _query(self, query: str, variables: dict) -> dict:
        """Execute a GraphQL query against OpenTargets API.

        Args:
            query: GraphQL query string.
            variables: Query variables dict.

        Returns:
            Parsed JSON response dict.

        Raises:
            requests.ConnectionError: On network failure (retried).
            requests.Timeout: On timeout (retried).
            requests.HTTPError: On non-2xx response.
        """
        resp = requests.post(
            BASE_URL,
            json={"query": query, "variables": variables},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def is_available(self) -> bool:
        """Check if OpenTargets API is reachable.

        Returns:
            True if API responds to a simple meta query.
        """
        try:
            resp = requests.post(
                BASE_URL,
                json={"query": "{ meta { apiVersion { x y z } } }", "variables": {}},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False
