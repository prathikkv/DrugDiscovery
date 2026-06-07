"""UniProt REST API evidence source.

Fetches protein function, subcellular location, domains, and structure
availability using the new REST API at rest.uniprot.org (NOT the deprecated
www.uniprot.org/uniprot endpoint).
"""

from __future__ import annotations

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.evidence.models import EvidenceResult, GeneIdentifiers


class UniProtSource:
    """Evidence source querying UniProt new REST API.

    Fetches protein biology data including function annotations,
    subcellular location, domain architecture, and structure availability
    for the target gene's protein product (REQ-205).
    """

    BASE_URL = "https://rest.uniprot.org/uniprotkb/search"

    @property
    def source_name(self) -> str:
        """Unique identifier for this evidence source."""
        return "uniprot"

    @property
    def source_version(self) -> str:
        """Version string for this source's API/data."""
        return "2024"

    def fetch(
        self,
        gene: GeneIdentifiers,
        disease_context: str | None = None,
    ) -> EvidenceResult:
        """Fetch protein biology data from UniProt.

        Args:
            gene: Resolved gene identifiers with canonical symbol and optional accession.
            disease_context: Optional disease context (unused for UniProt queries).

        Returns:
            EvidenceResult with protein data and confidence score.
        """
        try:
            # Build query
            if gene.uniprot_accession:
                query = f"accession:{gene.uniprot_accession}"
            else:
                query = (
                    f"(gene_exact:{gene.canonical_symbol}) "
                    f"AND (organism_id:9606) AND (reviewed:true)"
                )

            # Fields to retrieve
            fields = (
                "accession,gene_names,protein_name,cc_function,"
                "cc_subcellular_location,ft_domain,ft_binding,structure_3d,length"
            )

            # Fetch data
            response = self._search(query, fields)

            # Parse response
            results = response.get("results", [])
            if not results:
                return EvidenceResult(
                    source_name=self.source_name,
                    confidence=0.0,
                    error=f"No UniProt entry found for {gene.canonical_symbol}",
                )

            entry = results[0]

            # Extract accession
            accession = entry.get("primaryAccession", "")

            # Extract protein name
            protein_name = ""
            protein_desc = entry.get("proteinDescription", {})
            rec_name = protein_desc.get("recommendedName", {})
            if rec_name:
                full_name = rec_name.get("fullName", {})
                protein_name = full_name.get("value", "")

            # Extract function comments
            functions = []
            comments = entry.get("comments", [])
            for comment in comments:
                if comment.get("commentType") == "FUNCTION":
                    texts = comment.get("texts", [])
                    for text in texts:
                        val = text.get("value", "")
                        if val:
                            functions.append(val)

            # Extract subcellular locations
            subcellular_locations = []
            for comment in comments:
                if comment.get("commentType") == "SUBCELLULAR LOCATION":
                    sub_locs = comment.get("subcellularLocations", [])
                    for sub_loc in sub_locs:
                        location = sub_loc.get("location", {})
                        loc_value = location.get("value", "")
                        if loc_value:
                            subcellular_locations.append(loc_value)

            # Extract domains (features where type == "Domain")
            domains = []
            features = entry.get("features", [])
            for feature in features:
                if feature.get("type") == "Domain":
                    desc = feature.get("description", "")
                    if desc:
                        domains.append(desc)

            # Check for 3D structure
            has_structure = bool(entry.get("structure3D"))

            # Sequence length
            sequence = entry.get("sequence", {})
            seq_length = sequence.get("length", 0)

            # Gene names
            gene_names = []
            genes_data = entry.get("genes", [])
            for g in genes_data:
                name = g.get("geneName", {}).get("value", "")
                if name:
                    gene_names.append(name)
                synonyms = g.get("synonyms", [])
                for syn in synonyms:
                    syn_val = syn.get("value", "")
                    if syn_val:
                        gene_names.append(syn_val)

            # Build data dict
            data = {
                "accession": accession,
                "protein_name": protein_name,
                "function": functions,
                "subcellular_location": subcellular_locations,
                "domains": domains,
                "has_alphafold_structure": has_structure,
                "sequence_length": seq_length,
                "gene_names": gene_names,
            }

            return EvidenceResult(
                source_name=self.source_name,
                confidence=1.0,
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
    def _search(self, query: str, fields: str) -> dict:
        """Execute a search query against UniProt REST API.

        Args:
            query: UniProt query string (e.g., "gene_exact:BRCA1").
            fields: Comma-separated field names to retrieve.

        Returns:
            Parsed JSON response dictionary.
        """
        resp = requests.get(
            self.BASE_URL,
            params={
                "query": query,
                "fields": fields,
                "format": "json",
                "size": 1,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def is_available(self) -> bool:
        """Check if UniProt REST API is reachable.

        Returns:
            True if the API responds with HTTP 200.
        """
        try:
            resp = requests.get(
                self.BASE_URL,
                params={"query": "accession:P00533", "size": 1, "format": "json"},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False
