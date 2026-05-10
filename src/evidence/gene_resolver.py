"""Gene alias resolver using MyGene.info with local fallback aliases.

Resolves user-provided gene symbols (which may be aliases like PD-L1)
to canonical HGNC symbols with Ensembl IDs and UniProt accessions.
The resolver runs BEFORE evidence sources are called, providing each
source with the identifiers it needs (e.g., Ensembl ID for OpenTargets,
UniProt accession for ChEMBL).
"""

from __future__ import annotations

import logging
from typing import Optional

import mygene

from src.evidence.models import GeneIdentifiers

logger = logging.getLogger(__name__)

# Common gene aliases mapped to canonical HGNC symbols.
# Keys are uppercase-normalized for case-insensitive lookup.
LOCAL_ALIASES: dict[str, str] = {
    "PD-L1": "CD274",
    "PD-1": "PDCD1",
    "HER2": "ERBB2",
    "HER3": "ERBB3",
    "P53": "TP53",
    "VEGF": "VEGFA",
    "TNF-ALPHA": "TNF",
    "IL-6R": "IL6R",
    "CTLA-4": "CTLA4",
    "GIPR": "GIPR",
    "GLP1R": "GLP1R",
}


class GeneResolver:
    """Resolves gene symbols to canonical identifiers via MyGene.info.

    Uses a two-tier strategy:
    1. Local alias table for instant resolution of common aliases
    2. MyGene.info API for canonical symbol, Ensembl ID, and UniProt accession

    Results are cached in-memory to avoid redundant API calls within
    a session. Resolution never raises exceptions -- on failure, returns
    a GeneIdentifiers with the query symbol as canonical and None IDs.
    """

    def __init__(self) -> None:
        self._mg = mygene.MyGeneInfo()
        self._cache: dict[str, GeneIdentifiers] = {}

    def resolve(self, symbol: str) -> GeneIdentifiers:
        """Resolve a gene symbol to canonical identifiers.

        Args:
            symbol: User-provided gene symbol or alias (e.g., 'PD-L1', 'EGFR')

        Returns:
            GeneIdentifiers with canonical_symbol, ensembl_id, uniprot_accession,
            and the original query_symbol preserved.
        """
        original = symbol.strip()
        upper_key = original.upper()

        # Check in-memory cache
        if upper_key in self._cache:
            return self._cache[upper_key]

        # Determine query symbol: resolve local alias if available
        query_symbol = LOCAL_ALIASES.get(upper_key, original)

        # Query MyGene.info
        try:
            result = self._mg.query(
                query_symbol,
                scopes="symbol,alias",
                species="human",
                fields="symbol,ensembl.gene,uniprot.Swiss-Prot",
                size=1,
            )
            gene_ids = self._parse_mygene_response(result, query_symbol, original)
        except Exception as e:
            logger.warning(
                "MyGene.info query failed for '%s': %s. Using fallback.",
                query_symbol,
                e,
            )
            gene_ids = GeneIdentifiers(
                canonical_symbol=query_symbol,
                ensembl_id=None,
                uniprot_accession=None,
                query_symbol=original,
            )

        # Cache and return
        self._cache[upper_key] = gene_ids
        return gene_ids

    def _parse_mygene_response(
        self,
        response: dict,
        query_symbol: str,
        original_symbol: str,
    ) -> GeneIdentifiers:
        """Parse MyGene.info query response into GeneIdentifiers.

        Handles the various response formats:
        - ensembl.gene may be a string or list (take first)
        - uniprot.Swiss-Prot may be a string or list (take first)
        - Response may have no hits
        """
        hits = response.get("hits", [])
        if not hits:
            logger.warning(
                "No MyGene.info hits for '%s'. Using query symbol as canonical.",
                query_symbol,
            )
            return GeneIdentifiers(
                canonical_symbol=query_symbol,
                ensembl_id=None,
                uniprot_accession=None,
                query_symbol=original_symbol,
            )

        hit = hits[0]

        # Extract canonical symbol
        canonical = hit.get("symbol", query_symbol)

        # Extract Ensembl gene ID (may be string or list)
        ensembl_id = self._extract_first(hit.get("ensembl", {}), "gene")

        # Extract UniProt accession (may be string or list)
        uniprot = self._extract_uniprot(hit)

        return GeneIdentifiers(
            canonical_symbol=canonical,
            ensembl_id=ensembl_id,
            uniprot_accession=uniprot,
            query_symbol=original_symbol,
        )

    @staticmethod
    def _extract_first(container: dict | list, key: str) -> Optional[str]:
        """Extract first value from a potentially nested/list field.

        MyGene.info returns ensembl as either:
        - {"gene": "ENSG000..."} (single)
        - [{"gene": "ENSG000..."}, ...] (multiple transcripts)
        """
        if isinstance(container, list):
            # Multiple entries -- take first
            if container and isinstance(container[0], dict):
                value = container[0].get(key)
            else:
                return None
        elif isinstance(container, dict):
            value = container.get(key)
        else:
            return None

        # Value itself might be a list
        if isinstance(value, list):
            return value[0] if value else None
        return value

    @staticmethod
    def _extract_uniprot(hit: dict) -> Optional[str]:
        """Extract UniProt Swiss-Prot accession from a hit.

        uniprot.Swiss-Prot may be a string or list.
        """
        uniprot_data = hit.get("uniprot", {})
        if not isinstance(uniprot_data, dict):
            return None

        swiss_prot = uniprot_data.get("Swiss-Prot")
        if swiss_prot is None:
            return None
        if isinstance(swiss_prot, list):
            return swiss_prot[0] if swiss_prot else None
        return swiss_prot
