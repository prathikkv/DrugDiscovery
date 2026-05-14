"""Tests for reporting data models and data collector.

Covers DossierConfig defaults, SectionContent creation, DossierData
construction with minimal and full data, auto-generated timestamps,
and collect_dossier_data() with and without reasoning results.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.unit

from src.reporting.models import DossierConfig, DossierData, SectionContent
from src.reporting.data_collector import collect_dossier_data
from src.evidence.models import (
    AggregatedEvidence,
    EvidenceResult,
    GeneIdentifiers,
)
from src.scoring.models import (
    CompositeScore,
    DimensionScore,
    ScorecardResult,
    SubScore,
    Verdict,
    VerdictLevel,
    WeightConfig,
)


# -- Fixtures ----------------------------------------------------------------

def _make_scorecard(
    gene: str = "EGFR",
    score: float = 82.5,
    verdict_level: VerdictLevel = VerdictLevel.GO,
) -> ScorecardResult:
    """Build a minimal valid ScorecardResult for testing."""
    return ScorecardResult(
        gene_symbol=gene,
        disease_context="NSCLC",
        composite=CompositeScore(
            score=score,
            dimension_scores=[
                DimensionScore(
                    name="genetic_evidence",
                    score=12.0,
                    max_score=15.0,
                    sub_scores=[
                        SubScore(name="gwas_associations", value=3.0, max_value=5.0),
                    ],
                    data_coverage=0.8,
                ),
                DimensionScore(
                    name="druggability",
                    score=10.0,
                    max_score=15.0,
                    sub_scores=[],
                    data_coverage=0.6,
                ),
            ],
            weights=WeightConfig(),
            formula_version="v1.0",
        ),
        verdict=Verdict(
            level=verdict_level,
            score=score,
            dimension_violations=[],
            forced_conditional=False,
            rationale="Strong evidence supports target advancement.",
        ),
        evidence_hash="abc123def456",
        scored_at="2026-05-12T00:00:00Z",
    )


def _make_evidence(gene: str = "EGFR") -> AggregatedEvidence:
    """Build a minimal valid AggregatedEvidence for testing."""
    return AggregatedEvidence(
        gene=GeneIdentifiers(
            canonical_symbol=gene,
            ensembl_id="ENSG00000146648",
            uniprot_accession="P00533",
            query_symbol=gene,
        ),
        disease_context="NSCLC",
        results={
            "opentargets": EvidenceResult(
                source_name="opentargets",
                confidence=0.9,
                data={"associations": [{"disease": "lung carcinoma", "score": 0.85}]},
            ),
            "dgidb": EvidenceResult(
                source_name="dgidb",
                confidence=0.8,
                data={"interactions": [{"drug": "erlotinib", "interaction_type": "inhibitor"}]},
            ),
        },
        sources_available=2,
        sources_failed=0,
    )


# -- DossierConfig tests ----------------------------------------------------

class TestDossierConfig:
    """Tests for DossierConfig defaults and construction."""

    def test_dossier_config_defaults(self):
        """DossierConfig() has standard brand defaults."""
        config = DossierConfig()
        assert config.brand_color == (0, 113, 227)
        assert config.include_plotlyjs is True
        assert config.chart_scale == 2
        assert config.chart_width == 900
        assert config.chart_height == 550
        assert config.brand_name == "BioOrchestrator"


# -- SectionContent tests ---------------------------------------------------

class TestSectionContent:
    """Tests for SectionContent model."""

    def test_section_content_creation(self):
        """SectionContent can be created with all fields."""
        section = SectionContent(
            title="Executive Summary",
            narrative="Target shows strong evidence.",
            data={"verdict_level": "GO", "score": 85.0},
            charts=["radar_single", "evidence_dimensions_bar"],
        )
        assert section.title == "Executive Summary"
        assert section.narrative == "Target shows strong evidence."
        assert section.data["verdict_level"] == "GO"
        assert len(section.charts) == 2

    def test_section_content_defaults(self):
        """SectionContent uses empty defaults for optional fields."""
        section = SectionContent(title="Test")
        assert section.narrative == ""
        assert section.data == {}
        assert section.charts == []


# -- DossierData tests -------------------------------------------------------

class TestDossierData:
    """Tests for DossierData model."""

    def test_dossier_data_minimal(self):
        """DossierData can be created with just required fields."""
        d = DossierData(
            gene_symbol="EGFR",
            scorecard={},
            evidence={},
        )
        assert d.gene_symbol == "EGFR"
        assert d.scorecard == {}
        assert d.evidence == {}
        assert d.sections == {}
        assert d.disease_context is None
        assert d.comparative is None

    def test_dossier_data_full(self):
        """DossierData can be created with all fields populated."""
        d = DossierData(
            gene_symbol="EGFR",
            disease_context="NSCLC",
            scorecard={"composite": {"score": 82.5}},
            evidence={"results": {"opentargets": {"confidence": 0.9}}},
            reasoning={"synthesis": {"summary": "Strong target."}},
            pipeline_report={"status": "complete"},
            gene_identifiers={"canonical_symbol": "EGFR"},
            sections={
                "executive_summary": SectionContent(
                    title="Executive Summary",
                    narrative="Test narrative.",
                )
            },
            config=DossierConfig(brand_color=(255, 0, 0)),
        )
        assert d.disease_context == "NSCLC"
        assert d.reasoning["synthesis"]["summary"] == "Strong target."
        assert d.pipeline_report["status"] == "complete"
        assert "executive_summary" in d.sections
        assert d.config.brand_color == (255, 0, 0)

    def test_dossier_data_generated_at_auto(self):
        """generated_at is auto-populated with ISO timestamp."""
        d = DossierData(
            gene_symbol="EGFR",
            scorecard={},
            evidence={},
        )
        # Should be a valid ISO 8601 timestamp
        assert d.generated_at is not None
        assert len(d.generated_at) > 10
        # Verify it parses as a timestamp (contains T or date-like pattern)
        assert re.match(r"\d{4}-\d{2}-\d{2}", d.generated_at)


# -- collect_dossier_data tests ----------------------------------------------

class TestCollectDossierData:
    """Tests for collect_dossier_data() function."""

    def test_collect_dossier_data_basic(self):
        """collect_dossier_data() produces DossierData with all 7 sections."""
        scorecard = _make_scorecard()
        evidence = _make_evidence()

        result = collect_dossier_data(
            scorecard_result=scorecard,
            evidence=evidence,
        )

        assert isinstance(result, DossierData)
        assert result.gene_symbol == "EGFR"
        assert result.disease_context == "NSCLC"

        # All 7 sections present
        expected_sections = [
            "executive_summary",
            "target_overview",
            "evidence_dimensions",
            "ai_synthesis",
            "scorecard",
            "recommendations",
            "audit_trail",
        ]
        for section_key in expected_sections:
            assert section_key in result.sections, f"Missing section: {section_key}"
            assert isinstance(result.sections[section_key], SectionContent)

    def test_collect_dossier_data_with_reasoning(self):
        """collect_dossier_data() with reasoning populates ai_synthesis claims."""
        from src.reasoning.models import Claim, ReasoningMode, ReasoningResult

        scorecard = _make_scorecard()
        evidence = _make_evidence()

        reasoning = {
            "synthesis": ReasoningResult(
                mode=ReasoningMode.SYNTHESIS,
                gene_symbol="EGFR",
                summary="EGFR is a validated oncology target with strong evidence.",
                claims=[
                    Claim(
                        text="EGFR mutations drive NSCLC",
                        confidence=0.95,
                        sources=["opentargets"],
                    ),
                ],
            ),
        }

        result = collect_dossier_data(
            scorecard_result=scorecard,
            evidence=evidence,
            reasoning_results=reasoning,
        )

        ai_section = result.sections["ai_synthesis"]
        assert "claims" in ai_section.data
        assert len(ai_section.data["claims"]) == 1
        assert ai_section.data["claims"][0]["text"] == "EGFR mutations drive NSCLC"
        assert "synthesis" in ai_section.data.get("modes_analyzed", [])

    def test_collect_dossier_data_without_reasoning(self):
        """collect_dossier_data() without reasoning degrades gracefully."""
        scorecard = _make_scorecard()
        evidence = _make_evidence()

        result = collect_dossier_data(
            scorecard_result=scorecard,
            evidence=evidence,
            reasoning_results=None,
        )

        ai_section = result.sections["ai_synthesis"]
        # Should have a fallback narrative
        assert ai_section.narrative
        assert "No AI reasoning" in ai_section.narrative or len(ai_section.narrative) > 0
        # Claims should be empty
        assert ai_section.data.get("claims", []) == []
