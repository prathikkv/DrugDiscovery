"""Tests for comparative scorecard, radar charts, and multi-target scoring.

Covers score_multiple_targets(), build_comparative_radar(),
build_single_radar(), and ranking logic.
"""

from __future__ import annotations

import pytest

from src.evidence.models import AggregatedEvidence, EvidenceResult, GeneIdentifiers
from src.scoring.models import (
    ComparativeScorecard,
    CompositeScore,
    DimensionScore,
    ScorecardResult,
    SubScore,
    Verdict,
    VerdictLevel,
    WeightConfig,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _make_scorecard(
    gene_symbol: str,
    composite_score: float,
    dim_fraction: float = 0.5,
    verdict_level: VerdictLevel = VerdictLevel.CONDITIONAL,
) -> ScorecardResult:
    """Build a mock ScorecardResult with controllable scores."""
    dims = []
    for name in DIMENSION_NAMES:
        ms = MAX_SCORES[name]
        dims.append(
            DimensionScore(
                name=name,
                score=round(dim_fraction * ms, 2),
                max_score=ms,
                sub_scores=[
                    SubScore(name=f"{name}_sub", value=round(dim_fraction * ms, 2), max_value=ms)
                ],
                data_coverage=1.0,
            )
        )

    composite = CompositeScore(
        score=composite_score,
        dimension_scores=dims,
        weights=WeightConfig(),
    )

    verdict = Verdict(
        level=verdict_level,
        score=composite_score,
        rationale=f"Mock verdict for {gene_symbol}",
    )

    return ScorecardResult(
        gene_symbol=gene_symbol,
        disease_context="test disease",
        composite=composite,
        verdict=verdict,
        evidence_hash="a" * 64,
        scored_at="2026-05-12T00:00:00Z",
    )


def _make_mock_evidence(
    gene_symbol: str,
    overall_score: float = 0.5,
) -> AggregatedEvidence:
    """Build mock AggregatedEvidence for multi-target scoring tests."""
    gene = GeneIdentifiers(canonical_symbol=gene_symbol, query_symbol=gene_symbol)

    results = {
        "opentargets": EvidenceResult(
            source_name="opentargets",
            confidence=0.9,
            data={
                "associations": [
                    {
                        "disease_name": "test disease",
                        "overall_score": overall_score,
                        "datatypeScores": [
                            {"id": "genetic_association", "score": overall_score},
                        ],
                    }
                ],
                "tractability": {
                    "small_molecule": {"top_category": 3},
                },
                "known_drugs": [{"drug_name": "TestDrug", "phase": 2}],
                "max_phase": 2,
            },
        ),
        "dgidb": EvidenceResult(
            source_name="dgidb",
            confidence=0.7,
            data={
                "gene_categories": ["DRUGGABLE GENOME"],
                "interactions": [{"drug_name": "X", "interaction_types": ["inhibitor"]}],
            },
        ),
        "pubmed": EvidenceResult(
            source_name="pubmed",
            confidence=0.6,
            data={
                "paper_count": 10,
                "review_count": 2,
                "yearly_counts": [2, 4],
            },
        ),
        "clinicaltrials": EvidenceResult(
            source_name="clinicaltrials",
            confidence=0.5,
            data={
                "active_count": 2,
                "max_phase": 2,
                "unique_sponsors": 2,
                "biomarker_level": 1,
                "patient_selection_level": 1,
            },
        ),
        "uniprot": EvidenceResult(
            source_name="uniprot",
            confidence=0.8,
            data={
                "subcellular_location": "Cell membrane",
                "tissue_expression": {
                    "tissues": ["Lung"],
                    "disease_relevant": True,
                },
                "domains": ["Kinase"],
            },
        ),
        "chembl": EvidenceResult(
            source_name="chembl",
            confidence=0.7,
            data={
                "activity_count": 5,
                "max_pchembl": 6.0,
            },
        ),
    }

    return AggregatedEvidence(
        gene=gene,
        disease_context="test disease",
        results=results,
        sources_available=6,
        sources_failed=0,
    )


# ---------------------------------------------------------------------------
# score_multiple_targets tests
# ---------------------------------------------------------------------------


class TestScoreMultipleTargets:
    """Tests for score_multiple_targets function."""

    def test_score_multiple_targets_returns_comparative(self):
        """3 mock evidences -> ComparativeScorecard with 3 scorecards and ranking of length 3."""
        from src.scoring.comparative import score_multiple_targets

        evidences = [
            _make_mock_evidence("EGFR", 0.9),
            _make_mock_evidence("TP53", 0.5),
            _make_mock_evidence("BRCA1", 0.7),
        ]
        result = score_multiple_targets(evidences)
        assert isinstance(result, ComparativeScorecard)
        assert len(result.scorecards) == 3
        assert len(result.ranking) == 3

    def test_score_multiple_targets_ranking_order(self):
        """Target with highest composite first in ranking."""
        from src.scoring.comparative import score_multiple_targets

        # EGFR gets highest overall_score, should rank first
        evidences = [
            _make_mock_evidence("LOW_GENE", 0.1),
            _make_mock_evidence("HIGH_GENE", 0.95),
            _make_mock_evidence("MID_GENE", 0.5),
        ]
        result = score_multiple_targets(evidences)
        # First in ranking should have the highest score
        assert result.ranking[0] == "HIGH_GENE"
        assert result.ranking[-1] == "LOW_GENE"

    def test_score_multiple_targets_custom_weights(self):
        """Passing WeightConfig changes scores for all targets."""
        from src.scoring.comparative import score_multiple_targets

        evidences = [
            _make_mock_evidence("EGFR", 0.8),
            _make_mock_evidence("TP53", 0.6),
        ]

        default_result = score_multiple_targets(evidences)

        custom_weights = WeightConfig(
            genetic_evidence=50,
            expression_biology=5,
            druggability=5,
            safety_selectivity=5,
            competitive_landscape=5,
            clinical_translational=5,
            literature_consensus=25,
        )
        custom_result = score_multiple_targets(evidences, weights=custom_weights)

        # At least one target should have a different score
        default_scores = {s.gene_symbol: s.composite.score for s in default_result.scorecards}
        custom_scores = {s.gene_symbol: s.composite.score for s in custom_result.scorecards}
        assert default_scores != custom_scores

    def test_score_multiple_targets_empty_reasoning(self):
        """reasoning_results_map=None -> still works, no crash."""
        from src.scoring.comparative import score_multiple_targets

        evidences = [
            _make_mock_evidence("EGFR"),
            _make_mock_evidence("TP53"),
        ]
        result = score_multiple_targets(evidences, reasoning_results_map=None)
        assert isinstance(result, ComparativeScorecard)
        assert len(result.scorecards) == 2


# ---------------------------------------------------------------------------
# Radar chart tests
# ---------------------------------------------------------------------------


class TestBuildComparativeRadar:
    """Tests for build_comparative_radar function."""

    def test_comparative_radar_returns_figure(self):
        """build_comparative_radar(3 scorecards) returns go.Figure."""
        import plotly.graph_objects as go

        from src.scoring.comparative import build_comparative_radar

        scorecards = [
            _make_scorecard("EGFR", 80.0, 0.8, VerdictLevel.GO),
            _make_scorecard("TP53", 65.0, 0.65),
            _make_scorecard("BRCA1", 45.0, 0.45, VerdictLevel.NO_GO),
        ]
        fig = build_comparative_radar(scorecards)
        assert isinstance(fig, go.Figure)

    def test_comparative_radar_trace_count(self):
        """Figure has exactly N traces for N scorecards."""
        from src.scoring.comparative import build_comparative_radar

        scorecards = [
            _make_scorecard("EGFR", 80.0, 0.8, VerdictLevel.GO),
            _make_scorecard("TP53", 65.0, 0.65),
        ]
        fig = build_comparative_radar(scorecards)
        assert len(fig.data) == 2

    def test_comparative_radar_trace_type(self):
        """Each trace is Scatterpolar."""
        import plotly.graph_objects as go

        from src.scoring.comparative import build_comparative_radar

        scorecards = [
            _make_scorecard("EGFR", 80.0, 0.8, VerdictLevel.GO),
            _make_scorecard("TP53", 65.0, 0.65),
        ]
        fig = build_comparative_radar(scorecards)
        for trace in fig.data:
            assert isinstance(trace, go.Scatterpolar)

    def test_comparative_radar_polygon_closed(self):
        """r values list has len(dimensions)+1 (last = first for polygon closure)."""
        from src.scoring.comparative import build_comparative_radar

        scorecards = [_make_scorecard("EGFR", 80.0, 0.8, VerdictLevel.GO)]
        fig = build_comparative_radar(scorecards)
        trace = fig.data[0]
        r_values = list(trace.r)
        # 7 dimensions + 1 for closure = 8
        assert len(r_values) == 8
        assert r_values[0] == r_values[-1]

    def test_comparative_radar_normalized_values(self):
        """All r values between 0.0 and 1.0."""
        from src.scoring.comparative import build_comparative_radar

        scorecards = [
            _make_scorecard("EGFR", 80.0, 0.8, VerdictLevel.GO),
            _make_scorecard("TP53", 40.0, 0.4, VerdictLevel.NO_GO),
        ]
        fig = build_comparative_radar(scorecards)
        for trace in fig.data:
            for val in trace.r:
                assert 0.0 <= val <= 1.0, f"r value {val} out of [0,1] range"


class TestBuildSingleRadar:
    """Tests for build_single_radar function."""

    def test_single_radar_returns_figure(self):
        """build_single_radar(scorecard) returns go.Figure with 1 trace."""
        import plotly.graph_objects as go

        from src.scoring.comparative import build_single_radar

        scorecard = _make_scorecard("EGFR", 80.0, 0.8, VerdictLevel.GO)
        fig = build_single_radar(scorecard)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
