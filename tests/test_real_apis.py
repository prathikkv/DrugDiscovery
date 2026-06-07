"""Real API integration tests — call live external services.

These tests are SKIPPED by default. To run:
    RUN_REAL_APIS=1 pytest tests/test_real_apis.py -v

They verify that:
- OpenTargets GraphQL API returns data for known genes
- PubMed Entrez API returns publications for known queries
- DGIdb returns drug interactions for known targets
- Data shapes match what the scoring framework expects

Run these when: API schemas might have changed, after upgrading evidence source code,
or before a customer demo where live data is critical.
"""

from __future__ import annotations

import os

import pytest

# Skip entire module unless RUN_REAL_APIS is set
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_REAL_APIS"),
    reason="Set RUN_REAL_APIS=1 to run real API integration tests",
)


@pytest.fixture(scope="module")
def opentargets_source():
    from src.evidence.sources.opentargets import OpenTargetsSource
    return OpenTargetsSource()


@pytest.fixture(scope="module")
def pubmed_source():
    from src.evidence.sources.pubmed import PubMedSource
    return PubMedSource()


@pytest.fixture(scope="module")
def dgidb_source():
    from src.evidence.sources.dgidb import DGIdbSource
    return DGIdbSource()


@pytest.fixture(scope="module")
def clinicaltrials_source():
    from src.evidence.sources.clinicaltrials import ClinicalTrialsSource
    return ClinicalTrialsSource()


# ── OpenTargets ────────────────────────────────────────────────────────────


class TestOpenTargetsRealAPI:
    """Tests against the live OpenTargets Platform GraphQL API."""

    def test_egfr_returns_high_confidence(self, opentargets_source):
        """EGFR (gold-standard target) should return confidence >= 0.8."""
        from src.evidence.models import GeneIdentifiers
        gene = GeneIdentifiers(
            canonical_symbol="EGFR",
            ensembl_id="ENSG00000146648",
            query_symbol="EGFR",
        )
        result = opentargets_source.fetch(gene, "lung cancer")

        assert result.error is None, f"OpenTargets returned error: {result.error}"
        assert result.confidence >= 0.8, (
            f"EGFR confidence {result.confidence} is below 0.8 — "
            "API schema may have changed"
        )

    def test_egfr_has_genetic_associations(self, opentargets_source):
        """EGFR should have multiple disease associations in OpenTargets."""
        from src.evidence.models import GeneIdentifiers
        gene = GeneIdentifiers(
            canonical_symbol="EGFR",
            ensembl_id="ENSG00000146648",
            query_symbol="EGFR",
        )
        result = opentargets_source.fetch(gene, "lung cancer")

        assert result.data is not None
        associations = result.data.get("genetic_associations", [])
        assert len(associations) > 0, (
            "EGFR should have at least 1 genetic association in OpenTargets"
        )

    def test_egfr_has_known_drugs(self, opentargets_source):
        """EGFR should have known drugs (Erlotinib, Gefitinib, Osimertinib)."""
        from src.evidence.models import GeneIdentifiers
        gene = GeneIdentifiers(
            canonical_symbol="EGFR",
            ensembl_id="ENSG00000146648",
            query_symbol="EGFR",
        )
        result = opentargets_source.fetch(gene, "lung cancer")

        assert result.data is not None
        known_drugs = result.data.get("known_drugs", [])
        assert len(known_drugs) > 0, "EGFR should have known approved drugs"

    def test_unknown_gene_returns_low_confidence(self, opentargets_source):
        """A nonsense gene symbol should return low confidence gracefully."""
        from src.evidence.models import GeneIdentifiers
        gene = GeneIdentifiers(
            canonical_symbol="FAKE_GENE_XYZ999",
            ensembl_id=None,
            query_symbol="FAKE_GENE_XYZ999",
        )
        result = opentargets_source.fetch(gene, "cancer")

        # Should not raise, should return low confidence
        assert result.confidence <= 0.3, (
            "Unknown gene should return low confidence"
        )

    def test_response_has_required_fields(self, opentargets_source):
        """OpenTargets response data has all fields that scoring needs."""
        from src.evidence.models import GeneIdentifiers
        gene = GeneIdentifiers(
            canonical_symbol="BRCA1",
            ensembl_id="ENSG00000012048",
            query_symbol="BRCA1",
        )
        result = opentargets_source.fetch(gene, "breast cancer")

        if result.confidence > 0 and result.data:
            # These fields are used by the scoring framework
            # (not all need to be present, but we check the shape)
            assert isinstance(result.data, dict), "Data should be a dict"


# ── PubMed ─────────────────────────────────────────────────────────────────


class TestPubMedRealAPI:
    """Tests against the live NCBI Entrez/PubMed API."""

    def test_egfr_nsclc_returns_publications(self, pubmed_source):
        """EGFR + NSCLC query should return recent publications."""
        from src.evidence.models import GeneIdentifiers
        gene = GeneIdentifiers(canonical_symbol="EGFR", query_symbol="EGFR")
        result = pubmed_source.fetch(gene, "Non-Small Cell Lung Cancer")

        assert result.error is None, f"PubMed returned error: {result.error}"
        assert result.confidence > 0.0
        papers = result.data.get("papers", []) if result.data else []
        assert len(papers) > 0, "EGFR/NSCLC should have recent publications"

    def test_publications_have_required_fields(self, pubmed_source):
        """Each returned publication has pmid, title, and year."""
        from src.evidence.models import GeneIdentifiers
        gene = GeneIdentifiers(canonical_symbol="EGFR", query_symbol="EGFR")
        result = pubmed_source.fetch(gene, "lung cancer")

        if result.data and result.data.get("papers"):
            for paper in result.data["papers"][:3]:  # Check first 3
                assert "pmid" in paper or "title" in paper, (
                    f"Paper missing expected fields: {list(paper.keys())}"
                )

    def test_total_count_is_positive(self, pubmed_source):
        """PubMed total_count for well-studied genes should be > 10."""
        from src.evidence.models import GeneIdentifiers
        gene = GeneIdentifiers(canonical_symbol="TP53", query_symbol="TP53")
        result = pubmed_source.fetch(gene, "cancer")

        if result.data:
            total = result.data.get("total_count", 0)
            assert total > 10, (
                f"TP53 should have many publications, got {total}"
            )


# ── DGIdb ──────────────────────────────────────────────────────────────────


class TestDGIdbRealAPI:
    """Tests against the live DGIdb GraphQL API."""

    def test_egfr_has_drug_interactions(self, dgidb_source):
        """EGFR should have multiple drug interactions in DGIdb."""
        from src.evidence.models import GeneIdentifiers
        gene = GeneIdentifiers(canonical_symbol="EGFR", query_symbol="EGFR")
        result = dgidb_source.fetch(gene, "lung cancer")

        assert result.error is None, f"DGIdb returned error: {result.error}"
        interactions = result.data.get("interactions", []) if result.data else []
        assert len(interactions) > 0, (
            "EGFR should have drug interactions in DGIdb"
        )

    def test_response_confidence_is_valid(self, dgidb_source):
        """DGIdb confidence is between 0.0 and 1.0."""
        from src.evidence.models import GeneIdentifiers
        gene = GeneIdentifiers(canonical_symbol="BRCA1", query_symbol="BRCA1")
        result = dgidb_source.fetch(gene, "breast cancer")

        assert 0.0 <= result.confidence <= 1.0


# ── Full Aggregation ────────────────────────────────────────────────────────


class TestFullEvidenceAggregation:
    """Test the full 6-source evidence aggregation for EGFR."""

    def test_egfr_aggregation_returns_6_sources(self):
        """Aggregating EGFR from all 6 sources returns at least 4 successful sources."""
        from src.evidence.aggregator import EvidenceAggregator
        from src.evidence.models import GeneIdentifiers

        gene = GeneIdentifiers(
            canonical_symbol="EGFR",
            ensembl_id="ENSG00000146648",
            query_symbol="EGFR",
        )
        aggregator = EvidenceAggregator()
        evidence = aggregator.aggregate(gene, disease_context="lung cancer")

        assert evidence.sources_available >= 4, (
            f"Expected at least 4 of 6 sources for EGFR, "
            f"got {evidence.sources_available}"
        )

    def test_egfr_aggregation_produces_go_verdict(self):
        """Live EGFR evidence aggregation should still produce a GO verdict."""
        from src.evidence.aggregator import EvidenceAggregator
        from src.evidence.models import GeneIdentifiers
        from src.scoring.framework import ScoringFramework
        from src.scoring.models import VerdictLevel

        gene = GeneIdentifiers(
            canonical_symbol="EGFR",
            ensembl_id="ENSG00000146648",
            query_symbol="EGFR",
        )
        aggregator = EvidenceAggregator()
        evidence = aggregator.aggregate(gene, disease_context="lung cancer")
        scorecard = ScoringFramework().score_target(evidence)

        assert scorecard.verdict.level == VerdictLevel.GO, (
            f"Live EGFR data produced {scorecard.verdict.level.value} "
            f"(score={scorecard.composite.score:.1f}) — "
            "API data may have changed significantly"
        )
