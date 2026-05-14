"""Tests for the gene resolver module.

Validates local alias resolution, MyGene.info integration, failure handling,
and in-memory caching. All tests use mocks -- no real network calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.integration

from src.evidence.gene_resolver import GeneResolver, LOCAL_ALIASES
from src.evidence.models import GeneIdentifiers


class TestLocalAliases:
    """Tests for local alias resolution."""

    def test_local_alias_pd_l1(self):
        """PD-L1 resolves to canonical_symbol=CD274."""
        with patch("mygene.MyGeneInfo") as mock_mg_cls:
            mock_mg = MagicMock()
            mock_mg_cls.return_value = mock_mg
            mock_mg.query.return_value = {
                "hits": [
                    {
                        "symbol": "CD274",
                        "ensembl": {"gene": "ENSG00000120217"},
                        "uniprot": {"Swiss-Prot": "Q9NZQ7"},
                    }
                ]
            }

            resolver = GeneResolver()
            result = resolver.resolve("PD-L1")

            assert result.canonical_symbol == "CD274"
            assert result.query_symbol == "PD-L1"
            assert result.ensembl_id == "ENSG00000120217"
            assert result.uniprot_accession == "Q9NZQ7"

    def test_local_alias_her2(self):
        """HER2 resolves to canonical_symbol=ERBB2."""
        with patch("mygene.MyGeneInfo") as mock_mg_cls:
            mock_mg = MagicMock()
            mock_mg_cls.return_value = mock_mg
            mock_mg.query.return_value = {
                "hits": [
                    {
                        "symbol": "ERBB2",
                        "ensembl": {"gene": "ENSG00000141736"},
                        "uniprot": {"Swiss-Prot": "P04626"},
                    }
                ]
            }

            resolver = GeneResolver()
            result = resolver.resolve("HER2")

            assert result.canonical_symbol == "ERBB2"
            assert result.query_symbol == "HER2"


class TestMyGeneIntegration:
    """Tests for MyGene.info API integration."""

    def test_already_canonical(self):
        """EGFR is already canonical; mock mygene returns it with Ensembl ID."""
        with patch("mygene.MyGeneInfo") as mock_mg_cls:
            mock_mg = MagicMock()
            mock_mg_cls.return_value = mock_mg
            mock_mg.query.return_value = {
                "hits": [
                    {
                        "symbol": "EGFR",
                        "ensembl": {"gene": "ENSG00000146648"},
                        "uniprot": {"Swiss-Prot": "P00533"},
                    }
                ]
            }

            resolver = GeneResolver()
            result = resolver.resolve("EGFR")

            assert result.canonical_symbol == "EGFR"
            assert result.ensembl_id == "ENSG00000146648"
            assert result.uniprot_accession == "P00533"
            assert result.query_symbol == "EGFR"

    def test_mygene_failure_returns_input(self):
        """Mock mygene to raise exception; resolver returns input symbol as canonical."""
        with patch("mygene.MyGeneInfo") as mock_mg_cls:
            mock_mg = MagicMock()
            mock_mg_cls.return_value = mock_mg
            mock_mg.query.side_effect = ConnectionError("Network error")

            resolver = GeneResolver()
            result = resolver.resolve("EGFR")

            assert result.canonical_symbol == "EGFR"
            assert result.ensembl_id is None
            assert result.uniprot_accession is None
            assert result.query_symbol == "EGFR"


class TestResolverCaching:
    """Tests for in-memory caching."""

    def test_caching(self):
        """Resolve same symbol twice; mock mygene called only once."""
        with patch("mygene.MyGeneInfo") as mock_mg_cls:
            mock_mg = MagicMock()
            mock_mg_cls.return_value = mock_mg
            mock_mg.query.return_value = {
                "hits": [
                    {
                        "symbol": "EGFR",
                        "ensembl": {"gene": "ENSG00000146648"},
                        "uniprot": {"Swiss-Prot": "P00533"},
                    }
                ]
            }

            resolver = GeneResolver()
            result1 = resolver.resolve("EGFR")
            result2 = resolver.resolve("EGFR")

            assert result1.canonical_symbol == result2.canonical_symbol
            # MyGene should have been called only once
            assert mock_mg.query.call_count == 1
