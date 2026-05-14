"""Tests for scoring Pydantic models and weight configuration.

TDD RED tests: written before implementation. All should fail initially.
"""

import pytest

pytestmark = pytest.mark.unit

import pytest
from pydantic import ValidationError


class TestSubScore:
    """SubScore model validation tests."""

    def test_subscore_bounds_zero_valid(self):
        """value=0 is valid."""
        from src.scoring.models import SubScore

        ss = SubScore(name="test", value=0, max_value=5)
        assert ss.value == 0

    def test_subscore_bounds_negative_rejected(self):
        """value=-1 raises ValidationError."""
        from src.scoring.models import SubScore

        with pytest.raises(ValidationError):
            SubScore(name="test", value=-1, max_value=5)

    def test_subscore_normalized(self):
        """SubScore(value=3, max_value=5).normalized == 0.6."""
        from src.scoring.models import SubScore

        ss = SubScore(name="test", value=3, max_value=5)
        assert ss.normalized == 0.6


class TestDimensionScore:
    """DimensionScore model validation tests."""

    def test_dimension_score_exceeds_max(self):
        """score=16 with max_score=15 raises ValidationError."""
        from src.scoring.models import DimensionScore

        with pytest.raises(ValidationError):
            DimensionScore(name="test", score=16, max_score=15)

    def test_dimension_score_rounds(self):
        """score=3.456 rounds to 3.46."""
        from src.scoring.models import DimensionScore

        ds = DimensionScore(name="test", score=3.456, max_score=15)
        assert ds.score == 3.46


class TestWeightConfig:
    """WeightConfig model validation tests."""

    def test_weight_config_defaults(self):
        """Default weight sum is 100.0."""
        from src.scoring.models import WeightConfig

        wc = WeightConfig()
        total = (
            wc.genetic_evidence
            + wc.expression_biology
            + wc.druggability
            + wc.safety_selectivity
            + wc.competitive_landscape
            + wc.clinical_translational
            + wc.literature_consensus
        )
        assert total == 100.0

    def test_weight_normalized_sums_to_one(self):
        """Custom weights (25, 10, 10, 10, 10, 10, 5) normalized sums to 1.0."""
        from src.scoring.models import WeightConfig

        wc = WeightConfig(
            genetic_evidence=25,
            expression_biology=10,
            druggability=10,
            safety_selectivity=10,
            competitive_landscape=10,
            clinical_translational=10,
            literature_consensus=5,
        )
        normalized = wc.normalized()
        assert abs(sum(normalized.values()) - 1.0) < 1e-9

    def test_weight_normalized_zero_total(self):
        """All weights 0 -> equal distribution (1/7 each)."""
        from src.scoring.models import WeightConfig

        wc = WeightConfig(
            genetic_evidence=0,
            expression_biology=0,
            druggability=0,
            safety_selectivity=0,
            competitive_landscape=0,
            clinical_translational=0,
            literature_consensus=0,
        )
        normalized = wc.normalized()
        for v in normalized.values():
            assert abs(v - 1.0 / 7) < 1e-9


class TestCompositeScore:
    """CompositeScore model validation tests."""

    def test_composite_score_bounds(self):
        """score=101 raises ValidationError."""
        from src.scoring.models import CompositeScore, DimensionScore, WeightConfig

        with pytest.raises(ValidationError):
            CompositeScore(
                score=101,
                dimension_scores=[],
                weights=WeightConfig(),
            )


class TestVerdictLevel:
    """VerdictLevel enum tests."""

    def test_verdict_levels(self):
        """VerdictLevel.GO == 'GO', NO_GO == 'NO-GO'."""
        from src.scoring.models import VerdictLevel

        assert VerdictLevel.GO == "GO"
        assert VerdictLevel.NO_GO == "NO-GO"
        assert VerdictLevel.CONDITIONAL == "CONDITIONAL"


class TestScorecardResult:
    """ScorecardResult serialization tests."""

    def test_scorecard_result_serialization(self):
        """model_dump(mode='json') produces valid JSON."""
        import json

        from src.scoring.models import (
            CompositeScore,
            DimensionScore,
            ScorecardResult,
            SubScore,
            Verdict,
            VerdictLevel,
            WeightConfig,
        )

        dim = DimensionScore(
            name="genetic_evidence",
            score=10.0,
            max_score=15,
            sub_scores=[SubScore(name="gwas", value=5, max_value=5)],
            data_coverage=1.0,
        )
        composite = CompositeScore(
            score=66.7,
            dimension_scores=[dim],
            weights=WeightConfig(),
        )
        verdict = Verdict(
            level=VerdictLevel.CONDITIONAL,
            score=66.7,
        )
        result = ScorecardResult(
            gene_symbol="EGFR",
            disease_context="NSCLC",
            composite=composite,
            verdict=verdict,
            evidence_hash="abc123",
            scored_at="2026-05-12T00:00:00Z",
        )

        dumped = result.model_dump(mode="json")
        json_str = json.dumps(dumped)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["gene_symbol"] == "EGFR"
        assert parsed["verdict"]["level"] == "CONDITIONAL"


class TestComparativeScorecard:
    """ComparativeScorecard validation tests."""

    def _make_scorecard(self, gene: str, score: float):
        """Helper to create a minimal ScorecardResult."""
        from src.scoring.models import (
            CompositeScore,
            ScorecardResult,
            Verdict,
            VerdictLevel,
            WeightConfig,
        )

        return ScorecardResult(
            gene_symbol=gene,
            composite=CompositeScore(
                score=score,
                dimension_scores=[],
                weights=WeightConfig(),
            ),
            verdict=Verdict(level=VerdictLevel.CONDITIONAL, score=score),
        )

    def test_comparative_scorecard_max_count(self):
        """21 scorecards raises ValidationError."""
        from src.scoring.models import ComparativeScorecard

        cards = [self._make_scorecard(f"GENE{i}", 50.0) for i in range(21)]
        with pytest.raises(ValidationError):
            ComparativeScorecard(scorecards=cards, ranking=[])

    def test_comparative_scorecard_ranking(self):
        """from_scorecards() ranks by composite desc."""
        from src.scoring.models import ComparativeScorecard

        cards = [
            self._make_scorecard("LOW", 30.0),
            self._make_scorecard("HIGH", 90.0),
            self._make_scorecard("MID", 60.0),
        ]
        comp = ComparativeScorecard.from_scorecards(cards)
        assert comp.ranking == ["HIGH", "MID", "LOW"]
