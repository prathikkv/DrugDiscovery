"""Tests for reporting renderers, visualization builder, and chart export.

Covers VisualizationBuilder with empty and populated data, chart export
to PNG bytes/file and SVG file, HTMLDossierRenderer output,
PDFDossierRenderer output, and the generate_dossier convenience function.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

import plotly.graph_objects as go

from src.reporting.models import DossierConfig, DossierData, SectionContent
from src.reporting.visualizations import VisualizationBuilder
from src.reporting.chart_export import (
    chart_to_png_bytes,
    export_chart_png,
    export_chart_svg,
)
from src.reporting.html_renderer import HTMLDossierRenderer
from src.reporting.pdf_renderer import PDFDossierRenderer, generate_dossier
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


# -- Shared fixtures ---------------------------------------------------------


@pytest.fixture
def sample_dossier_data() -> DossierData:
    """DossierData with enough scorecard and evidence data to exercise renderers.

    Includes 2 dimension scores with sub-scores, 2 evidence sources,
    basic sections, and gene identifiers. No network or external services needed.
    """
    return DossierData(
        gene_symbol="EGFR",
        disease_context="NSCLC",
        scorecard={
            "gene_symbol": "EGFR",
            "disease_context": "NSCLC",
            "composite": {
                "score": 82.5,
                "dimension_scores": [
                    {
                        "name": "genetic_evidence",
                        "score": 12.0,
                        "max_score": 15.0,
                        "sub_scores": [
                            {
                                "name": "gwas_associations",
                                "value": 3.0,
                                "max_value": 5.0,
                                "description": "GWAS hits",
                                "data_source": "opentargets",
                            },
                            {
                                "name": "somatic_mutations",
                                "value": 4.0,
                                "max_value": 5.0,
                                "description": "Somatic mutation frequency",
                                "data_source": "opentargets",
                            },
                        ],
                        "data_coverage": 0.8,
                    },
                    {
                        "name": "druggability",
                        "score": 10.0,
                        "max_score": 15.0,
                        "sub_scores": [
                            {
                                "name": "known_drugs",
                                "value": 5.0,
                                "max_value": 5.0,
                                "description": "Known drug interactions",
                                "data_source": "dgidb",
                            },
                        ],
                        "data_coverage": 0.6,
                    },
                    {
                        "name": "expression_biology",
                        "score": 11.0,
                        "max_score": 15.0,
                        "sub_scores": [],
                        "data_coverage": 0.7,
                    },
                ],
                "weights": {
                    "genetic_evidence": 15.0,
                    "expression_biology": 15.0,
                    "druggability": 15.0,
                    "safety_selectivity": 15.0,
                    "competitive_landscape": 15.0,
                    "clinical_translational": 15.0,
                    "literature_consensus": 10.0,
                },
                "formula_version": "v1.0",
            },
            "verdict": {
                "level": "GO",
                "score": 82.5,
                "dimension_violations": [],
                "forced_conditional": False,
                "rationale": "Strong evidence supports target advancement.",
            },
            "evidence_hash": "abc123def456",
            "scored_at": "2026-05-12T00:00:00Z",
        },
        evidence={
            "results": {
                "opentargets": {
                    "confidence": 0.9,
                    "data": {"associations": [{"disease": "lung carcinoma", "score": 0.85}]},
                    "error": None,
                    "is_fallback": False,
                },
                "dgidb": {
                    "confidence": 0.8,
                    "data": {"interactions": [{"drug": "erlotinib"}]},
                    "error": None,
                    "is_fallback": False,
                },
            }
        },
        sections={
            "executive_summary": SectionContent(
                title="Executive Summary",
                narrative="EGFR is a validated oncology target with strong genetic evidence.",
                data={
                    "verdict_level": "GO",
                    "composite_score": 82.5,
                    "forced_conditional": False,
                    "dimension_violations": [],
                },
                charts=["radar_single"],
            ),
            "target_overview": SectionContent(
                title="Target Overview",
                narrative="Target gene: EGFR | Ensembl: ENSG00000146648 | UniProt: P00533",
                data={
                    "gene_identifiers": {
                        "canonical_symbol": "EGFR",
                        "ensembl_id": "ENSG00000146648",
                    },
                },
            ),
            "evidence_dimensions": SectionContent(
                title="Evidence Dimensions",
                narrative="Scoring across 3 dimensions.",
                data={"dimension_scores": [], "evidence_sources": ["opentargets", "dgidb"]},
                charts=["evidence_dimensions_bar"],
            ),
            "ai_synthesis": SectionContent(
                title="AI Synthesis & Reasoning",
                narrative="No AI reasoning analysis available.",
                data={"claims": [], "modes_analyzed": []},
            ),
            "scorecard": SectionContent(
                title="Scorecard",
                narrative="Composite score: 82.5/100 (GO)",
                data={"composite": {}, "verdict": {}, "formula_version": "v1.0"},
                charts=["radar_single"],
            ),
            "recommendations": SectionContent(
                title="Recommendations & Next Steps",
                narrative="Proceed to experimental validation and lead optimization.",
                data={"verdict_level": "GO", "dimension_violations": []},
            ),
            "audit_trail": SectionContent(
                title="Audit Trail & Provenance",
                narrative="Full provenance chain for reproducibility.",
                data={
                    "evidence_hash": "abc123def456",
                    "scored_at": "2026-05-12T00:00:00Z",
                    "evidence_sources": {
                        "opentargets": {"confidence": 0.9, "is_fallback": False, "has_error": False},
                        "dgidb": {"confidence": 0.8, "is_fallback": False, "has_error": False},
                    },
                    "reasoning_provenance": {},
                    "pipeline_report_available": False,
                },
            ),
        },
        gene_identifiers={
            "canonical_symbol": "EGFR",
            "ensembl_id": "ENSG00000146648",
            "uniprot_accession": "P00533",
            "query_symbol": "EGFR",
        },
    )


@pytest.fixture
def minimal_dossier_data() -> DossierData:
    """Minimal DossierData with empty scorecard and evidence."""
    return DossierData(
        gene_symbol="BRAF",
        scorecard={},
        evidence={},
        sections={},
    )


def _make_simple_bar_chart() -> go.Figure:
    """Create a simple Plotly bar chart for testing chart export."""
    return go.Figure(
        data=[go.Bar(x=["A", "B", "C"], y=[1, 2, 3])],
        layout=go.Layout(title="Test Chart", width=400, height=300),
    )


# -- VisualizationBuilder tests ----------------------------------------------


class TestVisualizationBuilder:
    """Tests for VisualizationBuilder."""

    def test_visualization_builder_empty_data(self, minimal_dossier_data):
        """VisualizationBuilder with minimal data produces dict (possibly empty)."""
        builder = VisualizationBuilder(minimal_dossier_data)
        figures = builder.build_all()
        assert isinstance(figures, dict)
        # With no dimension scores, most charts should be None/skipped
        # No assertion on exact count -- may produce 0 charts

    def test_visualization_builder_with_dimensions(self, sample_dossier_data):
        """VisualizationBuilder with dimension scores produces expected charts."""
        builder = VisualizationBuilder(sample_dossier_data)
        figures = builder.build_all()
        assert isinstance(figures, dict)
        # Evidence bar chart should be present with dimension scores
        assert "evidence_dimensions_bar" in figures
        assert isinstance(figures["evidence_dimensions_bar"], go.Figure)


# -- Chart export tests -------------------------------------------------------


class TestChartExport:
    """Tests for chart export utilities."""

    def test_chart_to_png_bytes(self):
        """chart_to_png_bytes() returns PNG bytes."""
        fig = _make_simple_bar_chart()
        png_bytes = chart_to_png_bytes(fig, width=400, height=300, scale=1)
        assert isinstance(png_bytes, bytes)
        assert len(png_bytes) > 100
        # PNG magic bytes
        assert png_bytes[:4] == b"\x89PNG"

    def test_export_chart_png(self, tmp_path):
        """export_chart_png() writes PNG file to disk."""
        fig = _make_simple_bar_chart()
        out = export_chart_png(fig, tmp_path / "test.png", width=400, height=300, scale=1)
        assert out.exists()
        assert out.stat().st_size > 100
        content = out.read_bytes()
        assert content[:4] == b"\x89PNG"

    def test_export_chart_svg(self, tmp_path):
        """export_chart_svg() writes SVG file to disk."""
        fig = _make_simple_bar_chart()
        out = export_chart_svg(fig, tmp_path / "test.svg", width=400, height=300)
        assert out.exists()
        assert out.stat().st_size > 100
        content = out.read_text()
        assert "<svg" in content


# -- HTMLDossierRenderer tests -----------------------------------------------


class TestHTMLDossierRenderer:
    """Tests for HTMLDossierRenderer."""

    def test_html_renderer_produces_html(self, sample_dossier_data):
        """HTMLDossierRenderer.render() returns HTML string with key content."""
        renderer = HTMLDossierRenderer()
        html = renderer.render(sample_dossier_data)
        assert isinstance(html, str)
        assert "<html" in html.lower()
        assert "EGFR" in html
        assert "Target Assessment Dossier" in html

    def test_html_renderer_to_file(self, sample_dossier_data, tmp_path):
        """render_to_file() writes HTML to disk."""
        renderer = HTMLDossierRenderer()
        out = renderer.render_to_file(sample_dossier_data, tmp_path / "test.html")
        assert out.exists()
        assert out.stat().st_size > 100
        content = out.read_text()
        assert "<html" in content.lower()

    def test_html_renderer_includes_sections(self, sample_dossier_data):
        """Rendered HTML contains all 7 section headings."""
        renderer = HTMLDossierRenderer()
        html = renderer.render(sample_dossier_data)
        section_headings = [
            "Executive Summary",
            "Target Overview",
            "Evidence Dimensions",
            "AI Synthesis",
            "Scorecard",
            "Recommendations",
            "Audit Trail",
        ]
        for heading in section_headings:
            assert heading in html, f"Missing section heading: {heading}"


# -- PDFDossierRenderer tests ------------------------------------------------


class TestPDFDossierRenderer:
    """Tests for PDFDossierRenderer."""

    def test_pdf_renderer_produces_pdf(self, sample_dossier_data):
        """PDFDossierRenderer.render() returns bytes starting with %PDF-."""
        renderer = PDFDossierRenderer()
        pdf_bytes = renderer.render(sample_dossier_data)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000
        assert pdf_bytes[:5] == b"%PDF-"

    def test_pdf_renderer_to_file(self, sample_dossier_data, tmp_path):
        """render_to_file() writes PDF to disk."""
        renderer = PDFDossierRenderer()
        out = renderer.render_to_file(sample_dossier_data, tmp_path / "test.pdf")
        assert out.exists()
        assert out.stat().st_size > 1000
        content = out.read_bytes()
        assert content[:5] == b"%PDF-"

    def test_pdf_renderer_has_pages(self, sample_dossier_data):
        """PDF has multiple pages for all 7 sections."""
        renderer = PDFDossierRenderer()
        pdf_bytes = renderer.render(sample_dossier_data)
        # Count /Type /Page entries minus /Type /Pages
        text = pdf_bytes.decode("latin-1", errors="ignore")
        page_count = text.count("/Type /Page") - text.count("/Type /Pages")
        # At least 7 pages (one per major section)
        assert page_count >= 7, f"Expected >= 7 pages, got {page_count}"

    def test_pdf_renderer_minimal_data(self, minimal_dossier_data):
        """PDFDossierRenderer handles minimal/empty data without errors."""
        renderer = PDFDossierRenderer()
        pdf_bytes = renderer.render(minimal_dossier_data)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:5] == b"%PDF-"


# -- generate_dossier convenience function tests ----------------------------


class TestGenerateDossier:
    """Tests for the generate_dossier convenience function."""

    def test_generate_dossier_convenience(self, tmp_path):
        """generate_dossier() produces both HTML and PDF files."""
        scorecard = ScorecardResult(
            gene_symbol="EGFR",
            disease_context="NSCLC",
            composite=CompositeScore(
                score=82.5,
                dimension_scores=[
                    DimensionScore(
                        name="genetic_evidence",
                        score=12.0,
                        max_score=15.0,
                        data_coverage=0.8,
                    ),
                ],
                weights=WeightConfig(),
                formula_version="v1.0",
            ),
            verdict=Verdict(
                level=VerdictLevel.GO,
                score=82.5,
                rationale="Strong evidence.",
            ),
            evidence_hash="test123",
            scored_at="2026-05-12T00:00:00Z",
        )
        evidence = AggregatedEvidence(
            gene=GeneIdentifiers(
                canonical_symbol="EGFR",
                ensembl_id="ENSG00000146648",
                uniprot_accession="P00533",
                query_symbol="EGFR",
            ),
            disease_context="NSCLC",
            results={
                "opentargets": EvidenceResult(
                    source_name="opentargets",
                    confidence=0.9,
                    data={"key": "value"},
                ),
            },
            sources_available=1,
            sources_failed=0,
        )

        result = generate_dossier(
            scorecard_result=scorecard,
            evidence=evidence,
            output_dir=tmp_path / "dossiers",
            formats=("html", "pdf"),
        )

        assert "html" in result
        assert "pdf" in result
        assert result["html"].exists()
        assert result["pdf"].exists()
        assert result["html"].suffix == ".html"
        assert result["pdf"].suffix == ".pdf"
        # Verify content
        assert result["html"].stat().st_size > 100
        assert result["pdf"].stat().st_size > 1000
        assert result["pdf"].read_bytes()[:5] == b"%PDF-"
