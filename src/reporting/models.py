"""Dossier data models: DossierData, DossierConfig, and SectionContent.

Pydantic v2 models for structuring all upstream data (scorecard, evidence,
reasoning, pipeline) into a single container consumed by HTML and PDF renderers.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class SectionContent(BaseModel):
    """Content for a single dossier section.

    Attributes:
        title: Section heading text.
        narrative: AI-generated or template narrative text.
        data: Structured data for tables/charts within the section.
        charts: Chart identifiers (keys into VisualizationBuilder output).
    """

    title: str
    narrative: str = ""
    data: dict = Field(default_factory=dict)
    charts: list[str] = Field(default_factory=list)


class DossierConfig(BaseModel):
    """Configuration for dossier rendering.

    Attributes:
        include_plotlyjs: True for self-contained HTML, 'cdn' for smaller files.
            Default True for air-gapped pharma environments.
        chart_width: Chart width in pixels.
        chart_height: Chart height in pixels.
        chart_scale: Scale factor for retina/print quality.
        brand_color: RGB tuple for the design system primary color (#0071e3).
        brand_name: Organization/product name for headers and footers.
    """

    include_plotlyjs: bool | str = True
    chart_width: int = 900
    chart_height: int = 550
    chart_scale: int = 2
    brand_color: tuple[int, int, int] = (0, 113, 227)
    brand_name: str = "BioOrchestrator"


class DossierData(BaseModel):
    """Complete data container for a target assessment dossier.

    Aggregates all upstream outputs (scoring, evidence, reasoning, pipeline)
    into a single serializable model consumed by both HTML and PDF renderers.

    Attributes:
        gene_symbol: Target gene symbol (e.g., "EGFR").
        disease_context: Optional disease/indication context.
        generated_at: ISO 8601 timestamp of dossier generation.
        scorecard: Serialized ScorecardResult (from model_dump()).
        comparative: Serialized ComparativeScorecard (from model_dump()), if multi-target.
        evidence: Serialized AggregatedEvidence (results dict with source_name keys).
        reasoning: Map of mode_name -> ReasoningResult.model_dump().
        pipeline_report: Pipeline report data (from pipeline_report.json), if available.
        gene_identifiers: Gene identifier cross-references (canonical, ensembl, uniprot).
        sections: Named dossier sections built by data_collector.
        config: Rendering configuration.
    """

    gene_symbol: str
    disease_context: str | None = None
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    scorecard: dict
    comparative: dict | None = None
    evidence: dict
    reasoning: dict[str, dict] = Field(default_factory=dict)
    pipeline_report: dict | None = None
    gene_identifiers: dict | None = None
    sections: dict[str, SectionContent] = Field(default_factory=dict)
    config: DossierConfig = Field(default_factory=DossierConfig)
