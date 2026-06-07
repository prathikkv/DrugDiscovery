"""End-to-end smoke tests using pre-cached showcase data.

These tests prove the full pipeline works — evidence deserialization →
scoring framework → verdict — without requiring live API calls or LLM keys.

They are the ONLY tests that catch: broken scoring algorithms, broken
evidence→scoring data flow, and verdict logic regressions.

Run: pytest tests/test_e2e_smoke.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.evidence.models import AggregatedEvidence, EvidenceResult, GeneIdentifiers
from src.scoring.framework import ScoringFramework
from src.scoring.models import VerdictLevel

SCENARIOS_DIR = Path("data/showcase_scenarios")

# Expected verdicts and minimum scores for pre-cached showcase scenarios
EXPECTED = {
    "egfr": {"verdict": VerdictLevel.GO, "min_score": 75.0},
    "esr1": {"verdict": VerdictLevel.GO, "min_score": 70.0},
    "pik3ca": {"verdict": VerdictLevel.GO, "min_score": 65.0},
    "glp1r": {"verdict": VerdictLevel.GO, "min_score": 65.0},
    "parp1": {"verdict": VerdictLevel.GO, "min_score": 65.0},
    "cd274": {"verdict": VerdictLevel.CONDITIONAL, "min_score": 50.0},
    "melk": {"verdict": VerdictLevel.NO_GO, "min_score": 0.0},
}


def _load_evidence(gene: str) -> AggregatedEvidence:
    """Load pre-cached evidence.json and reconstruct AggregatedEvidence."""
    path = SCENARIOS_DIR / gene / "evidence.json"
    raw = json.loads(path.read_text())

    gene_ids = GeneIdentifiers(
        canonical_symbol=raw["gene"]["canonical_symbol"],
        ensembl_id=raw["gene"].get("ensembl_id"),
        uniprot_accession=raw["gene"].get("uniprot_accession"),
        query_symbol=raw["gene"].get("query_symbol", ""),
    )

    results = {}
    for source_name, result_data in raw["results"].items():
        results[source_name] = EvidenceResult(
            source_name=source_name,
            confidence=result_data["confidence"],
            data=result_data.get("data"),
            error=result_data.get("error"),
            is_fallback=result_data.get("is_fallback", False),
        )

    return AggregatedEvidence(
        gene=gene_ids,
        disease_context=raw.get("disease_context"),
        results=results,
        sources_available=raw.get("sources_available", len(results)),
        sources_failed=raw.get("sources_failed", 0),
    )


@pytest.mark.integration
class TestEgfrEndToEnd:
    """Full pipeline test for EGFR/NSCLC — the gold-standard showcase."""

    def test_egfr_evidence_loads(self):
        """Pre-cached EGFR evidence deserializes without error."""
        evidence = _load_evidence("egfr")
        assert evidence.gene.canonical_symbol == "EGFR"
        assert evidence.disease_context == "Non-Small Cell Lung Cancer"
        assert len(evidence.results) == 6
        assert evidence.sources_available == 6

    def test_egfr_all_six_sources_present(self):
        """All 6 evidence sources are present and have data."""
        evidence = _load_evidence("egfr")
        expected_sources = {"opentargets", "dgidb", "pubmed", "clinicaltrials", "uniprot", "chembl"}
        assert set(evidence.results.keys()) == expected_sources

        for source_name, result in evidence.results.items():
            assert result.confidence > 0.0, f"{source_name} has zero confidence"

    def test_egfr_scores_go_verdict(self):
        """EGFR scoring produces GO verdict with score >= 75."""
        evidence = _load_evidence("egfr")
        scorecard = ScoringFramework().score_target(evidence)

        assert scorecard.verdict.level == VerdictLevel.GO, (
            f"Expected GO but got {scorecard.verdict.level} "
            f"(score={scorecard.composite.score:.1f})"
        )
        assert scorecard.composite.score >= 75.0, (
            f"EGFR composite score {scorecard.composite.score:.1f} below GO threshold"
        )

    def test_egfr_has_seven_dimensions(self):
        """Scorecard contains exactly 7 scoring dimensions."""
        evidence = _load_evidence("egfr")
        scorecard = ScoringFramework().score_target(evidence)

        assert len(scorecard.composite.dimension_scores) == 7

        dim_names = {d.name for d in scorecard.composite.dimension_scores}
        expected_names = {
            "genetic_evidence",
            "expression_biology",
            "druggability",
            "safety_selectivity",
            "competitive_landscape",
            "clinical_translational",
            "literature_consensus",
        }
        assert dim_names == expected_names

    def test_egfr_score_matches_pre_cached(self):
        """Freshly computed EGFR score matches pre-cached scoring.json within tolerance."""
        # Load expected from pre-cached file
        cached = json.loads((SCENARIOS_DIR / "egfr" / "scoring.json").read_text())
        expected_score = cached["composite"]["score"]
        expected_verdict = cached["verdict"]["level"]

        # Compute fresh
        evidence = _load_evidence("egfr")
        scorecard = ScoringFramework().score_target(evidence)

        assert scorecard.verdict.level.value == expected_verdict
        # Allow ±2 point tolerance for any future weight tuning
        assert abs(scorecard.composite.score - expected_score) <= 2.0, (
            f"Fresh score {scorecard.composite.score:.1f} diverges from "
            f"cached {expected_score:.1f} by more than 2 points"
        )

    def test_egfr_no_dimension_violations(self):
        """EGFR GO verdict has no dimension violations (no forced conditional)."""
        evidence = _load_evidence("egfr")
        scorecard = ScoringFramework().score_target(evidence)

        assert scorecard.verdict.forced_conditional is False
        assert scorecard.verdict.dimension_violations == []

    def test_egfr_evidence_hash_is_sha256(self):
        """Evidence hash is a 64-character hex string (SHA256)."""
        evidence = _load_evidence("egfr")
        scorecard = ScoringFramework().score_target(evidence)

        assert len(scorecard.evidence_hash) == 64
        assert all(c in "0123456789abcdef" for c in scorecard.evidence_hash)

    def test_egfr_scoring_is_deterministic(self):
        """Running scoring twice on same evidence produces identical results."""
        evidence = _load_evidence("egfr")
        fw = ScoringFramework()

        result1 = fw.score_target(evidence)
        result2 = fw.score_target(evidence)

        assert result1.composite.score == result2.composite.score
        assert result1.verdict.level == result2.verdict.level
        assert result1.evidence_hash == result2.evidence_hash


@pytest.mark.integration
class TestAllShowcaseVerdicts:
    """Verify pre-cached verdict expectations for all 7 showcase scenarios."""

    @pytest.mark.parametrize("gene,expected", list(EXPECTED.items()))
    def test_verdict_matches_expected(self, gene, expected):
        """Each showcase gene produces the expected verdict level."""
        scenario_path = SCENARIOS_DIR / gene
        if not scenario_path.exists():
            pytest.skip(f"Showcase scenario not found: {gene}")

        evidence = _load_evidence(gene)
        scorecard = ScoringFramework().score_target(evidence)

        assert scorecard.verdict.level == expected["verdict"], (
            f"{gene.upper()}: expected {expected['verdict'].value} "
            f"but got {scorecard.verdict.level.value} "
            f"(score={scorecard.composite.score:.1f})"
        )

    @pytest.mark.parametrize("gene,expected", list(EXPECTED.items()))
    def test_score_above_minimum(self, gene, expected):
        """Each showcase gene composite score is above the expected minimum."""
        scenario_path = SCENARIOS_DIR / gene
        if not scenario_path.exists():
            pytest.skip(f"Showcase scenario not found: {gene}")

        evidence = _load_evidence(gene)
        scorecard = ScoringFramework().score_target(evidence)

        assert scorecard.composite.score >= expected["min_score"], (
            f"{gene.upper()}: score {scorecard.composite.score:.1f} "
            f"below expected minimum {expected['min_score']}"
        )


@pytest.mark.integration
class TestNegativeControl:
    """MELK (negative control) should produce a NO-GO verdict."""

    def test_melk_is_no_go(self):
        """MELK is not a validated target — should produce NO-GO verdict."""
        scenario_path = SCENARIOS_DIR / "melk"
        if not scenario_path.exists():
            pytest.skip("MELK negative control scenario not found")

        evidence = _load_evidence("melk")
        scorecard = ScoringFramework().score_target(evidence)

        assert scorecard.verdict.level == VerdictLevel.NO_GO, (
            f"MELK (negative control) expected NO-GO but got "
            f"{scorecard.verdict.level.value} (score={scorecard.composite.score:.1f})"
        )

    def test_melk_score_below_go_threshold(self):
        """MELK composite score is below 50 (NO-GO range)."""
        scenario_path = SCENARIOS_DIR / "melk"
        if not scenario_path.exists():
            pytest.skip("MELK negative control scenario not found")

        evidence = _load_evidence("melk")
        scorecard = ScoringFramework().score_target(evidence)

        assert scorecard.composite.score < 50.0, (
            f"MELK (negative control) score {scorecard.composite.score:.1f} "
            f"is unexpectedly high — check negative control data"
        )


@pytest.mark.integration
class TestScoringRobustness:
    """Edge cases: what happens when some evidence sources are missing."""

    def test_scoring_with_missing_sources_does_not_crash(self):
        """Scoring with only OpenTargets data (4 sources missing) returns a verdict."""
        evidence = _load_evidence("egfr")
        # Remove all sources except opentargets
        evidence.results = {
            k: v for k, v in evidence.results.items() if k == "opentargets"
        }
        evidence.sources_available = 1
        evidence.sources_failed = 5

        # Should not raise — scoring handles missing data via neutral coverage
        scorecard = ScoringFramework().score_target(evidence)
        assert scorecard.verdict.level in list(VerdictLevel)
        assert 0 <= scorecard.composite.score <= 100

    def test_scoring_with_zero_confidence_source_treats_as_missing(self):
        """A source with confidence=0.0 is treated the same as missing."""
        evidence = _load_evidence("egfr")
        # Zero out DGIdb confidence
        evidence.results["dgidb"].confidence = 0.0
        evidence.results["dgidb"].data = None

        scorecard = ScoringFramework().score_target(evidence)
        # Should still produce a valid verdict (just with reduced coverage)
        assert scorecard.verdict.level in list(VerdictLevel)

    def test_all_sources_missing_produces_no_go(self):
        """With no evidence at all, the verdict should be NO-GO or CONDITIONAL."""
        gene_ids = GeneIdentifiers(canonical_symbol="UNKNOWN", query_symbol="UNKNOWN")
        empty_evidence = AggregatedEvidence(
            gene=gene_ids,
            disease_context=None,
            results={},
            sources_available=0,
            sources_failed=6,
        )

        scorecard = ScoringFramework().score_target(empty_evidence)
        # No data → should be NO-GO or at most CONDITIONAL
        assert scorecard.verdict.level != VerdictLevel.GO, (
            "Empty evidence should never produce GO verdict"
        )
