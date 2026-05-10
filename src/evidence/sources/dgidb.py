"""DGIdb GraphQL evidence source.

Fetches drug-gene interactions, druggability categories, and interaction
types from the Drug Gene Interaction Database (DGIdb) v5 GraphQL API.
"""

from __future__ import annotations

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.evidence.models import EvidenceResult, GeneIdentifiers

BASE_URL = "https://dgidb.org/api/graphql"

QUERY_INTERACTIONS = """
query GeneInteractions($geneName: String!) {
  genes(names: [$geneName]) {
    nodes {
      name
      longName
      geneCategories {
        name
      }
      interactions {
        drug {
          name
          conceptId
          approved
        }
        interactionScore
        interactionTypes {
          type
          directionality
        }
        publications {
          pmid
        }
        sources {
          sourceDbName
        }
      }
    }
  }
}
"""


class DGIdbSource:
    """Evidence source querying DGIdb v5 GraphQL API.

    Fetches drug-gene interactions including druggability categories,
    interaction types, scores, and supporting publications.
    """

    @property
    def source_name(self) -> str:
        """Unique identifier for this evidence source."""
        return "dgidb"

    @property
    def source_version(self) -> str:
        """Version string for this source's API/data."""
        return "v5"

    def fetch(
        self,
        gene: GeneIdentifiers,
        disease_context: str | None = None,
    ) -> EvidenceResult:
        """Fetch drug-gene interactions for a gene from DGIdb.

        Args:
            gene: Resolved gene identifiers (uses canonical_symbol).
            disease_context: Optional disease context (not used by DGIdb but accepted for interface).

        Returns:
            EvidenceResult with interactions, druggability categories, and drug counts.
        """
        try:
            response = self._query(
                QUERY_INTERACTIONS, {"geneName": gene.canonical_symbol}
            )

            # Parse response
            genes_data = (
                response.get("data", {}).get("genes", {}).get("nodes", [])
            )

            if not genes_data:
                # Gene not found in DGIdb -- valid result, low confidence
                return EvidenceResult(
                    source_name=self.source_name,
                    confidence=0.5,
                    data={
                        "gene_name": gene.canonical_symbol,
                        "gene_categories": [],
                        "interactions": [],
                        "interaction_count": 0,
                        "approved_drug_count": 0,
                    },
                )

            gene_node = genes_data[0]
            gene_name = gene_node.get("name", gene.canonical_symbol)

            # Extract gene categories (druggability classification)
            categories = [
                cat.get("name", "")
                for cat in (gene_node.get("geneCategories", []) or [])
            ]

            # Extract interactions
            raw_interactions = gene_node.get("interactions", []) or []
            interactions_list = []
            approved_count = 0

            for interaction in raw_interactions:
                drug_info = interaction.get("drug", {}) or {}
                is_approved = drug_info.get("approved", False)
                if is_approved:
                    approved_count += 1

                # Parse interaction types
                interaction_types = []
                for itype in (interaction.get("interactionTypes", []) or []):
                    interaction_types.append(
                        {
                            "type": itype.get("type", ""),
                            "directionality": itype.get("directionality", ""),
                        }
                    )

                # Parse publications
                pmids = [
                    pub.get("pmid", "")
                    for pub in (interaction.get("publications", []) or [])
                    if pub.get("pmid")
                ]

                # Parse sources
                sources = [
                    src.get("sourceDbName", "")
                    for src in (interaction.get("sources", []) or [])
                    if src.get("sourceDbName")
                ]

                interactions_list.append(
                    {
                        "drug_name": drug_info.get("name", ""),
                        "drug_concept_id": drug_info.get("conceptId", ""),
                        "approved": is_approved,
                        "interaction_score": interaction.get("interactionScore"),
                        "interaction_types": interaction_types,
                        "pmids": pmids,
                        "sources": sources,
                    }
                )

            # Build result data
            data = {
                "gene_name": gene_name,
                "gene_categories": categories,
                "interactions": interactions_list,
                "interaction_count": len(interactions_list),
                "approved_drug_count": approved_count,
            }

            # Confidence based on results
            confidence = 1.0 if interactions_list else 0.5

            return EvidenceResult(
                source_name=self.source_name,
                confidence=confidence,
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
        """Execute a GraphQL query against DGIdb API.

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
        """Check if DGIdb API is reachable.

        Returns:
            True if API responds to a simple introspection query.
        """
        try:
            resp = requests.post(
                BASE_URL,
                json={
                    "query": "{ __schema { queryType { name } } }",
                    "variables": {},
                },
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False
