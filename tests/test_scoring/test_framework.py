"""Tests for scoring framework orchestrator and verdict logic.

Covers composite score computation, verdict determination with threshold
boundaries and forced-CONDITIONAL on dimension minimum violations,
and the ScoringFramework.score_target() orchestrator.
"""

from __future__ import annotations

import hashlib
import json

import pytest

pytestmark = pytest.mark.unit

from src.evidence.models import AggregatedEvidence, EvidenceResult, GeneIdentifiers
from src.reasoning.models import Claim, ReasoningMode, ReasoningResult
from src.scoring.models import (
    CompositeScore,
    DimensionScore,
    ScorecardResult,
    SubScore,
    Verdict,
    VerdictLevel,
    WeightConfig,
)


# ---------------------------------------------------------------------------
# Helpers: build mock data
# ---------------------------------------------------------------------------

def _make_dimension(name: str, score: float, max_score: float, coverage: float = 1.0) -> DimensionScore:
    """Create a DimensionScore with a single sub-score for testing."""
    return DimensionScore(
        name=name,
        score=score,
        max_score=max_score,
        sub_scores=[SubScore(name=f"{name}_sub", value=score, max_value=max_score)],
        data_coverage=coverage,
    )


DIMENSION_NAMES = [
    "genetic_evidence",
    "expression_biology",
    "druggability",
    "safety_selectivity",
    "competitive_landscape",
    "clinical_translational",
    "literature_consensus",
]

MAX_SCORES = {
    "genetic_evidence": 15,
    "expression_biology": 15,
    "druggability": 15,
    "safety_selectivity": 15,
    "competitive_landscape": 15,
    "clinical_translational": 15,
    "literature_consensus": 10,
}


def _make_all_dimensions(fraction: float) -> list[DimensionScore]:
    """Build all 7 dimensions with each scored at `fraction` of max_score."""
    return [
        _make_dimension(name, fraction * MAX_SCORES[name], MAX_SCORES[name])
        for name in DIMENSION_NAMES
    ]


def _make_mock_evidence(
    gene_symbol: str = "EGFR",
    disease_context: str | None = "lung cancer",
) -> AggregatedEvidence:
    """Build a mock AggregatedEvidence with plausible data dicts for all 6 sources.

    Data structures match what each sub-score extractor expects from its
    respective evidence source parser.
    """
    gene = GeneIdentifiers(canonical_symbol=gene_symbol, query_symbol=gene_symbol)

    results = {
        "opentargets": EvidenceResult(
            source_name="opentargets",
            confidence=0.9,
            data={
                "associations": [
                    {
                        "disease_name": "lung carcinoma",
                        "overall_score": 0.85,
                        "datatypeScores": [
                            {"id": "genetic_association", "score": 0.7},
                            {"id": "affected_pathway", "score": 0.5},
                            {"id": "rna_expression", "score": 0.4},
                        ],
                    }
                ],
                "tractability": {
                    "small_molecule": {"top_category": 4},
                    "antibody": {"top_category": 3},
                },
                "known_drugs": [{"drug_name": "Erlotinib", "phase": 4}],
                "has_approved_drug": True,
                "max_phase": 4,
            },
        ),
        "dgidb": EvidenceResult(
            source_name="dgidb",
            confidence=0.8,
            data={
                "gene_categories": ["KINASE", "DRUGGABLE GENOME"],
                "interactions": [
                    {"drug_name": "ERLOTINIB", "interaction_types": ["inhibitor"]},
                    {"drug_name": "GEFITINIB", "interaction_types": ["inhibitor"]},
                ],
            },
        ),
        "pubmed": EvidenceResult(
            source_name="pubmed",
            confidence=0.7,
            data={
                "paper_count": 25,
                "review_count": 3,
                "yearly_counts": [3, 5, 7, 10],
            },
        ),
        "clinicaltrials": EvidenceResult(
            source_name="clinicaltrials",
            confidence=0.8,
            data={
                "active_count": 5,
                "max_phase": 3,
                "unique_sponsors": 3,
                "biomarker_level": 2,
                "patient_selection_level": 1,
            },
        ),
        "uniprot": EvidenceResult(
            source_name="uniprot",
            confidence=0.9,
            data={
                "subcellular_location": "Cell membrane",
                "tissue_expression": {
                    "tissues": ["Lung", "Liver", "Brain"],
                    "disease_relevant": True,
                },
                "domains": ["Protein kinase", "Receptor L domain"],
            },
        ),
        "chembl": EvidenceResult(
            source_name="chembl",
            confidence=0.8,
            data={
                "activity_count": 15,
                "max_pchembl": 8.2,
                "mechanisms": [{"action_type": "INHIBITOR", "target_type": "SINGLE PROTEIN"}],
            },
        ),
    }

    return AggregatedEvidence(
        gene=gene,
        disease_context=disease_context,
        results=results,
        sources_available=6,
        sources_failed=0,
    )


def _make_failed_evidence(gene_symbol: str = "UNKNOWN_GENE") -> AggregatedEvidence:
    """Build mock evidence where all sources failed (confidence=0.0)."""
    gene = GeneIdentifiers(canonical_symbol=gene_symbol, query_symbol=gene_symbol)
    results = {
        name: EvidenceResult(
            source_name=name,
            confidence=0.0,
            data=None,
            error="Source unavailable",
        )
        for name in ["opentargets", "dgidb", "pubmed", "clinicaltrials", "uniprot", "chembl"]
    }
    return AggregatedEvidence(
        gene=gene,
        disease_context=None,
        results=results,
        sources_available=0,
        sources_failed=6,
    )


# ---------------------------------------------------------------------------
# Composite score tests
# ---------------------------------------------------------------------------


class TestComputeComposite:
    """Tests for compute_composite function."""

    def test_composite_all_perfect(self):
        """All dimensions at max -> composite near 100."""
        from src.scoring.verdict import compute_composite

        dims = _make_all_dimensions(1.0)
        weights = WeightConfig()
        result = compute_composite(dims, weights)
        assert result.score == 100.0

    def test_composite_all_zero(self):
        """All dimensions at 0 -> composite 0.0."""
        from src.scoring.verdict import compute_composite

        dims = _make_all_dimensions(0.0)
        weights = WeightConfig()
        result = compute_composite(dims, weights)
        assert result.score == 0.0

    def test_composite_weighted(self):
        """Unequal weights change score proportionally."""
        from src.scoring.verdict import compute_composite

        # Set genetic_evidence to max, everything else to zero
        dims = []
        for name in DIMENSION_NAMES:
            if name == "genetic_evidence":
                dims.append(_make_dimension(name, MAX_SCORES[name], MAX_SCORES[name]))
            else:
                dims.append(_make_dimension(name, 0, MAX_SCORES[name]))

        # Default weights: genetic = 15/100 = 0.15
        default_result = compute_composite(dims, WeightConfig())
        assert abs(default_result.score - 15.0) < 0.2

        # Heavy weights on genetic: 90/100 = 0.9
        heavy = WeightConfig(
            genetic_evidence=90,
            expression_biology=1,
            druggability=1,
            safety_selectivity=1,
            competitive_landscape=1,
            clinical_translational=1,
            literature_consensus=5,
        )
        heavy_result = compute_composite(dims, heavy)
        assert heavy_result.score > default_result.score

    def test_composite_deterministic(self):
        """Same inputs produce identical score twice."""
        from src.scoring.verdict import compute_composite

        dims = _make_all_dimensions(0.6)
        weights = WeightConfig()
        r1 = compute_composite(dims, weights)
        r2 = compute_composite(dims, weights)
        assert r1.score == r2.score

    def test_composite_rounds_to_one_decimal(self):
        """Score is rounded to 1 decimal place."""
        from src.scoring.verdict import compute_composite

        # Use a fraction that causes an ugly float
        dims = _make_all_dimensions(1.0 / 3.0)
        weights = WeightConfig()
        result = compute_composite(dims, weights)
        # Check it has at most 1 decimal place
        assert result.score == round(result.score, 1)


# ---------------------------------------------------------------------------
# Verdict tests
# ---------------------------------------------------------------------------


class TestDetermineVerdict:
    """Tests for determine_verdict function."""

    def _make_composite(self, score: float, dim_fraction: float = 0.8) -> CompositeScore:
        """Helper to build a CompositeScore with the given score value."""
        dims = _make_all_dimensions(dim_fraction)
        return CompositeScore(
            score=score,
            dimension_scores=dims,
            weights=WeightConfig(),
        )

    def test_verdict_go(self):
        """Composite 80.0, no violations -> GO."""
        from src.scoring.verdict import determine_verdict

        composite = self._make_composite(80.0)
        verdict = determine_verdict(composite)
        assert verdict.level == VerdictLevel.GO

    def test_verdict_conditional(self):
        """Composite 65.0 -> CONDITIONAL."""
        from src.scoring.verdict import determine_verdict

        composite = self._make_composite(65.0, dim_fraction=0.65)
        verdict = determine_verdict(composite)
        assert verdict.level == VerdictLevel.CONDITIONAL

    def test_verdict_no_go(self):
        """Composite 40.0 -> NO_GO."""
        from src.scoring.verdict import determine_verdict

        composite = self._make_composite(40.0, dim_fraction=0.4)
        verdict = determine_verdict(composite)
        assert verdict.level == VerdictLevel.NO_GO

    def test_verdict_forced_conditional(self):
        """Composite 80.0 but genetic_evidence at 1/15 (below 0.20 minimum) -> CONDITIONAL with forced_conditional."""
        from src.scoring.verdict import determine_verdict

        # Build dimensions where genetic_evidence is very low
        dims = []
        for name in DIMENSION_NAMES:
            if name == "genetic_evidence":
                dims.append(_make_dimension(name, 1.0, 15))  # 1/15 = 0.067 < 0.20
            else:
                dims.append(_make_dimension(name, MAX_SCORES[name], MAX_SCORES[name]))

        composite = CompositeScore(
            score=80.0,
            dimension_scores=dims,
            weights=WeightConfig(),
        )
        verdict = determine_verdict(composite)
        assert verdict.level == VerdictLevel.CONDITIONAL
        assert verdict.forced_conditional is True
        assert "genetic_evidence" in verdict.dimension_violations

    def test_verdict_threshold_boundary_75(self):
        """Composite exactly 75.0, no violations -> GO."""
        from src.scoring.verdict import determine_verdict

        composite = self._make_composite(75.0, dim_fraction=0.75)
        verdict = determine_verdict(composite)
        assert verdict.level == VerdictLevel.GO

    def test_verdict_threshold_boundary_50(self):
        """Composite exactly 50.0 -> CONDITIONAL."""
        from src.scoring.verdict import determine_verdict

        composite = self._make_composite(50.0, dim_fraction=0.5)
        verdict = determine_verdict(composite)
        assert verdict.level == VerdictLevel.CONDITIONAL

    def test_verdict_threshold_boundary_49_9(self):
        """Composite 49.9 -> NO_GO."""
        from src.scoring.verdict import determine_verdict

        composite = self._make_composite(49.9, dim_fraction=0.49)
        verdict = determine_verdict(composite)
        assert verdict.level == VerdictLevel.NO_GO


# ---------------------------------------------------------------------------
# Framework orchestrator tests
# ---------------------------------------------------------------------------


class TestScoringFramework:
    """Tests for ScoringFramework.score_target() orchestrator."""

    def test_score_target_returns_scorecard_result(self):
        """ScoringFramework().score_target(mock_evidence) returns ScorecardResult."""
        from src.scoring.framework import ScoringFramework

        evidence = _make_mock_evidence()
        framework = ScoringFramework()
        result = framework.score_target(evidence)
        assert isinstance(result, ScorecardResult)

    def test_score_target_has_evidence_hash(self):
        """result.evidence_hash is non-empty SHA256 hex string (64 chars)."""
        from src.scoring.framework import ScoringFramework

        evidence = _make_mock_evidence()
        result = ScoringFramework().score_target(evidence)
        assert len(result.evidence_hash) == 64
        # Validate it's a valid hex string
        int(result.evidence_hash, 16)

    def test_score_target_gene_symbol(self):
        """result.gene_symbol matches evidence.gene.canonical_symbol."""
        from src.scoring.framework import ScoringFramework

        evidence = _make_mock_evidence(gene_symbol="TP53")
        result = ScoringFramework().score_target(evidence)
        assert result.gene_symbol == "TP53"

    def test_score_target_has_7_dimensions(self):
        """result.composite.dimension_scores has length 7."""
        from src.scoring.framework import ScoringFramework

        evidence = _make_mock_evidence()
        result = ScoringFramework().score_target(evidence)
        assert len(result.composite.dimension_scores) == 7

    def test_score_target_custom_weights(self):
        """Different WeightConfig produces different composite score."""
        from src.scoring.framework import ScoringFramework

        evidence = _make_mock_evidence()
        default_result = ScoringFramework().score_target(evidence)

        custom_weights = WeightConfig(
            genetic_evidence=50,
            expression_biology=5,
            druggability=5,
            safety_selectivity=5,
            competitive_landscape=5,
            clinical_translational=5,
            literature_consensus=25,
        )
        custom_result = ScoringFramework(weights=custom_weights).score_target(evidence)
        assert default_result.composite.score != custom_result.composite.score

    def test_score_target_with_reasoning(self):
        """Passing contradiction ReasoningResult affects literature_consensus score."""
        from src.scoring.framework import ScoringFramework

        evidence = _make_mock_evidence()

        # Without contradiction
        result_no_contradiction = ScoringFramework().score_target(evidence)

        # With high-confidence contradictions
        contradiction = ReasoningResult(
            mode=ReasoningMode.CONTRADICTION,
            gene_symbol="EGFR",
            claims=[
                Claim(text="Contradicting evidence 1", confidence=0.9, sources=["PubMed"]),
                Claim(text="Contradicting evidence 2", confidence=0.8, sources=["PubMed"]),
                Claim(text="Contradicting evidence 3", confidence=0.75, sources=["PubMed"]),
            ],
        )
        reasoning_results = {"contradiction": contradiction}
        result_with_contradiction = ScoringFramework().score_target(
            evidence, reasoning_results=reasoning_results
        )

        # Literature consensus should be lower with contradictions
        lit_no = None
        lit_with = None
        for dim in result_no_contradiction.composite.dimension_scores:
            if dim.name == "literature_consensus":
                lit_no = dim.score
        for dim in result_with_contradiction.composite.dimension_scores:
            if dim.name == "literature_consensus":
                lit_with = dim.score

        assert lit_no is not None
        assert lit_with is not None
        assert lit_with < lit_no

    def test_score_target_missing_evidence(self):
        """Evidence with all sources failed (confidence=0.0) -> still produces valid ScorecardResult."""
        from src.scoring.framework import ScoringFramework

        evidence = _make_failed_evidence()
        result = ScoringFramework().score_target(evidence)
        assert isinstance(result, ScorecardResult)
        assert result.composite.score >= 0
        assert result.verdict.level in [VerdictLevel.GO, VerdictLevel.CONDITIONAL, VerdictLevel.NO_GO]
