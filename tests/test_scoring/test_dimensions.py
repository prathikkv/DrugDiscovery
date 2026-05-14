"""Tests for sub-score extractors and dimension calculators.

TDD RED tests: written before implementation. All should fail initially.
Covers 10 sub-score boundary tests + 8 dimension calculator tests = 18 total.
"""

import pytest

pytestmark = pytest.mark.unit

import pytest


# ---------------------------------------------------------------------------
# Sub-score extractor tests (boundary cases)
# ---------------------------------------------------------------------------


class TestSubScoreExtractors:
    """Individual sub-score extractor boundary tests."""

    def test_gwas_no_data(self):
        """None input -> 0.0."""
        from src.scoring.sub_scores import compute_gwas_subscore

        assert compute_gwas_subscore(None, None) == 0.0

    def test_gwas_strong_association(self):
        """overall_score=0.9 -> 5.0."""
        from src.scoring.sub_scores import compute_gwas_subscore

        data = {"associations": [{"overall_score": 0.9}]}
        assert compute_gwas_subscore(data, None) == 5.0

    def test_gwas_disease_relevant(self):
        """Context-relevant association with moderate score -> 2.0."""
        from src.scoring.sub_scores import compute_gwas_subscore

        data = {
            "associations": [
                {"overall_score": 0.3, "context_relevant": True},
            ]
        }
        assert compute_gwas_subscore(data, "NSCLC") == 2.0

    def test_druggability_class_clinically_actionable(self):
        """Category list includes 'CLINICALLY ACTIONABLE' -> 4.0."""
        from src.scoring.sub_scores import compute_druggability_class_subscore

        data = {"gene_categories": ["CLINICALLY ACTIONABLE", "KINASE"]}
        assert compute_druggability_class_subscore(data) == 4.0

    def test_existing_compounds_many(self):
        """55 activities -> 4.0."""
        from src.scoring.sub_scores import compute_existing_compounds_subscore

        data = {"activity_count": 55}
        assert compute_existing_compounds_subscore(data) == 4.0

    def test_expression_breadth_inverted(self):
        """Ubiquitous expression -> 0 (safety risk)."""
        from src.scoring.sub_scores import compute_expression_breadth_subscore

        data = {"tissue_expression": {"ubiquitous": True}}
        assert compute_expression_breadth_subscore(data) == 0.0

    def test_publication_volume_high(self):
        """150 papers -> 4.0."""
        from src.scoring.sub_scores import compute_publication_volume_subscore

        data = {"paper_count": 150}
        assert compute_publication_volume_subscore(data) == 4.0

    def test_active_trials_moderate(self):
        """4 trials -> 2.0."""
        from src.scoring.sub_scores import compute_active_trials_subscore

        data = {"active_count": 4}
        assert compute_active_trials_subscore(data) == 2.0

    def test_clinical_precedent_approved(self):
        """Approved drug -> 5.0."""
        from src.scoring.sub_scores import compute_clinical_precedent_subscore

        data = {"max_phase": 4, "has_approved_drug": True}
        assert compute_clinical_precedent_subscore(data) == 5.0

    def test_all_subscores_handle_none(self):
        """Every sub-score function returns 0.0 or valid float when passed None."""
        from src.scoring.sub_scores import (
            compute_active_trials_subscore,
            compute_biomarker_availability_subscore,
            compute_binding_pocket_subscore,
            compute_causal_evidence_subscore,
            compute_cell_type_specificity_subscore,
            compute_clinical_phase_max_subscore,
            compute_clinical_precedent_subscore,
            compute_competitor_density_subscore,
            compute_differentiation_potential_subscore,
            compute_druggability_class_subscore,
            compute_essential_gene_risk_subscore,
            compute_existing_compounds_subscore,
            compute_expression_breadth_subscore,
            compute_expression_disease_link_subscore,
            compute_functional_genomics_subscore,
            compute_genetic_association_subscore,
            compute_gwas_subscore,
            compute_known_safety_signals_subscore,
            compute_patient_selection_subscore,
            compute_publication_trend_subscore,
            compute_publication_volume_subscore,
            compute_review_articles_subscore,
            compute_selectivity_potential_subscore,
            compute_subcellular_location_subscore,
            compute_tissue_expression_subscore,
            compute_tractability_subscore,
            compute_translational_evidence_subscore,
        )

        # All single-data-source functions
        single_arg_funcs = [
            compute_causal_evidence_subscore,
            compute_functional_genomics_subscore,
            compute_druggability_class_subscore,
            compute_existing_compounds_subscore,
            compute_binding_pocket_subscore,
            compute_expression_breadth_subscore,
            compute_known_safety_signals_subscore,
            compute_essential_gene_risk_subscore,
            compute_selectivity_potential_subscore,
            compute_active_trials_subscore,
            compute_clinical_phase_max_subscore,
            compute_competitor_density_subscore,
            compute_differentiation_potential_subscore,
            compute_biomarker_availability_subscore,
            compute_patient_selection_subscore,
            compute_publication_volume_subscore,
            compute_review_articles_subscore,
            compute_publication_trend_subscore,
            compute_tissue_expression_subscore,
            compute_subcellular_location_subscore,
            compute_cell_type_specificity_subscore,
        ]

        for fn in single_arg_funcs:
            result = fn(None)
            assert isinstance(result, float), f"{fn.__name__} did not return float"
            assert result >= 0.0, f"{fn.__name__} returned negative value"

        # Two-arg functions
        assert compute_gwas_subscore(None, None) == 0.0
        assert compute_genetic_association_subscore(None, None) == 0.0
        assert compute_expression_disease_link_subscore(None, None) == 0.0
        assert compute_clinical_precedent_subscore(None) == 0.0
        assert compute_translational_evidence_subscore(None, None) == 0.0
        assert compute_tractability_subscore(None) == 0.0


# ---------------------------------------------------------------------------
# Dimension calculator tests
# ---------------------------------------------------------------------------


class TestDimensionCalculators:
    """Dimension calculator integration tests."""

    def test_genetic_evidence_full_data(self):
        """All OT fields present -> DimensionScore with 4 sub-scores, score <= 15."""
        from src.scoring.dimensions import score_genetic_evidence

        ot_data = {
            "associations": [{"overall_score": 0.85, "context_relevant": True}],
            "datatypeScores": [
                {"id": "genetic_association", "score": 0.7},
                {"id": "affected_pathway", "score": 0.5},
            ],
        }

        result = score_genetic_evidence(ot_data, "NSCLC")
        assert result.name == "genetic_evidence"
        assert len(result.sub_scores) == 4
        assert 0 <= result.score <= 15
        assert result.max_score == 15
        assert result.data_coverage > 0.0

    def test_genetic_evidence_no_data(self):
        """None -> DimensionScore with score near 0 and data_coverage=0.0."""
        from src.scoring.dimensions import score_genetic_evidence

        result = score_genetic_evidence(None, None)
        assert result.score == 0.0
        assert result.data_coverage == 0.0
        assert result.max_score == 15

    def test_literature_consensus_no_contradiction(self):
        """pubmed data, no contradiction -> score based on pubs only."""
        from src.scoring.dimensions import score_literature_consensus

        pubmed = {"paper_count": 50, "review_count": 3, "yearly_counts": [10, 12, 15]}
        result = score_literature_consensus(pubmed, None)
        assert result.name == "literature_consensus"
        assert result.max_score == 10
        assert result.score > 0

    def test_literature_consensus_with_penalty(self):
        """3 strong contradiction claims -> penalty of 3, visible in sub_scores."""
        from src.scoring.dimensions import score_literature_consensus
        from src.reasoning.models import Claim, ReasoningMode, ReasoningResult

        pubmed = {"paper_count": 50, "review_count": 3, "yearly_counts": [10, 12, 15]}
        contradiction = ReasoningResult(
            mode=ReasoningMode.CONTRADICTION,
            gene_symbol="EGFR",
            claims=[
                Claim(text=f"Contradiction {i}", confidence=0.8, sources=["PubMed"])
                for i in range(3)
            ],
        )

        result_no_penalty = score_literature_consensus(pubmed, None)
        result_with_penalty = score_literature_consensus(pubmed, contradiction)

        # The penalty should reduce the score
        assert result_with_penalty.score < result_no_penalty.score

        # Find the contradiction sub-score
        contradiction_ss = [
            s for s in result_with_penalty.sub_scores if s.name == "contradictory_evidence"
        ]
        assert len(contradiction_ss) == 1
        assert contradiction_ss[0].value == 3.0

    def test_literature_consensus_penalty_capped_at_4(self):
        """10 strong contradictions -> penalty still 4 (not 10)."""
        from src.scoring.dimensions import score_literature_consensus
        from src.reasoning.models import Claim, ReasoningMode, ReasoningResult

        pubmed = {"paper_count": 150, "review_count": 10, "yearly_counts": [20, 30, 40]}
        contradiction = ReasoningResult(
            mode=ReasoningMode.CONTRADICTION,
            gene_symbol="EGFR",
            claims=[
                Claim(text=f"Contradiction {i}", confidence=0.9, sources=["PubMed"])
                for i in range(10)
            ],
        )

        result = score_literature_consensus(pubmed, contradiction)
        contradiction_ss = [
            s for s in result.sub_scores if s.name == "contradictory_evidence"
        ]
        assert len(contradiction_ss) == 1
        assert contradiction_ss[0].value == 4.0  # capped

    def test_literature_consensus_penalty_floors_at_zero(self):
        """base score 2 with penalty 4 -> final score 0 (not -2)."""
        from src.scoring.dimensions import score_literature_consensus
        from src.reasoning.models import Claim, ReasoningMode, ReasoningResult

        # Minimal pubmed data -> low base score
        pubmed = {"paper_count": 3, "review_count": 0, "yearly_counts": [1, 1, 1]}
        contradiction = ReasoningResult(
            mode=ReasoningMode.CONTRADICTION,
            gene_symbol="TEST",
            claims=[
                Claim(text=f"Strong contradiction {i}", confidence=0.95, sources=["PubMed"])
                for i in range(5)
            ],
        )

        result = score_literature_consensus(pubmed, contradiction)
        assert result.score >= 0.0  # Never negative

    def test_dimension_data_coverage(self):
        """Partial data -> coverage between 0 and 1."""
        from src.scoring.dimensions import score_druggability

        # Only dgidb data, no chembl or opentargets
        dgidb = {"gene_categories": ["KINASE"], "interactions": []}
        result = score_druggability(dgidb, None, None)
        assert 0.0 < result.data_coverage < 1.0

    def test_all_dimensions_return_correct_max_score(self):
        """Each of 7 dimension calculators returns its documented max_score (15 or 10)."""
        from src.scoring.dimensions import (
            score_clinical_translational,
            score_competitive_landscape,
            score_druggability,
            score_expression_biology,
            score_genetic_evidence,
            score_literature_consensus,
            score_safety_selectivity,
        )

        # All with None data
        assert score_genetic_evidence(None, None).max_score == 15
        assert score_expression_biology(None, None).max_score == 15
        assert score_druggability(None, None, None).max_score == 15
        assert score_safety_selectivity(None, None, None).max_score == 15
        assert score_competitive_landscape(None).max_score == 15
        assert score_clinical_translational(None, None).max_score == 15
        assert score_literature_consensus(None, None).max_score == 10
