"""PDF dossier renderer: produce professional branded PDF reports via fpdf2.

Renders DossierData into a static PDF with branded headers/footers,
embedded static chart images (PNG via kaleido), professional tables,
and verdict badges. Uses fpdf2 (pure Python, no system dependencies).
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any

from fpdf import FPDF, FontFace
import plotly.graph_objects as go

from src.reporting.models import DossierConfig, DossierData
from src.reporting.visualizations import VisualizationBuilder

logger = logging.getLogger(__name__)


class DossierPDF(FPDF):
    """Branded PDF with headers, footers, and page numbering."""

    def __init__(
        self,
        gene_symbol: str,
        disease_context: str = "",
        brand_color: tuple[int, int, int] = (0, 113, 227),
    ):
        super().__init__()
        self.gene_symbol = gene_symbol
        self.disease_context = disease_context
        self.brand_color = brand_color
        self.set_auto_page_break(auto=True, margin=25)

    def header(self):
        """Render branded header with gene symbol and optional disease context."""
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*self.brand_color)
        self.cell(0, 8, f"Target Assessment Dossier: {self.gene_symbol}", align="L")
        if self.disease_context:
            self.set_font("Helvetica", "", 8)
            self.set_text_color(128, 128, 128)
            self.cell(
                0, 8, f"  |  {self.disease_context}", align="R", new_x="LMARGIN"
            )
        self.ln(4)
        self.set_draw_color(*self.brand_color)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(8)

    def footer(self):
        """Render footer with centered page number."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


class PDFDossierRenderer:
    """Renders DossierData as a professional PDF with static chart images.

    Uses fpdf2 for PDF generation with branded headers/footers,
    professional table styling, verdict badges, and embedded PNG charts.

    Attributes:
        config: Rendering configuration controlling brand color and chart sizes.
    """

    def __init__(self, config: DossierConfig | None = None) -> None:
        self.config = config or DossierConfig()

    def render(self, dossier_data: DossierData) -> bytes:
        """Render complete PDF as bytes.

        1. Creates DossierPDF with branded headers/footers.
        2. Builds all Plotly figures via VisualizationBuilder.
        3. Renders each of the 7 dossier sections.
        4. Returns PDF as bytes.

        Args:
            dossier_data: Complete dossier data container.

        Returns:
            PDF file content as bytes.
        """
        brand = dossier_data.config.brand_color or self.config.brand_color

        pdf = DossierPDF(
            gene_symbol=dossier_data.gene_symbol,
            disease_context=dossier_data.disease_context or "",
            brand_color=brand,
        )
        pdf.alias_nb_pages()

        # Build visualization figures
        viz_builder = VisualizationBuilder(dossier_data)
        figures = viz_builder.build_all()

        # Render all 7 sections
        self._render_executive_summary(pdf, dossier_data, figures)
        self._render_target_overview(pdf, dossier_data)
        self._render_evidence_dimensions(pdf, dossier_data, figures)
        self._render_ai_synthesis(pdf, dossier_data)
        self._render_scorecard(pdf, dossier_data, figures)
        self._render_recommendations(pdf, dossier_data)
        self._render_audit_trail(pdf, dossier_data)

        logger.info(
            "Rendered PDF dossier for %s (%d pages)",
            dossier_data.gene_symbol,
            pdf.page,
        )
        return bytes(pdf.output())

    def render_to_file(self, dossier_data: DossierData, output_path: Path) -> Path:
        """Render and write PDF to file. Returns output_path.

        Creates parent directories if they do not exist.

        Args:
            dossier_data: Complete dossier data container.
            output_path: Destination file path.

        Returns:
            The output_path after successful write.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        pdf_bytes = self.render(dossier_data)
        output_path.write_bytes(pdf_bytes)

        logger.info("Wrote PDF dossier: %s (%d bytes)", output_path, len(pdf_bytes))
        return output_path

    # ----------------------------------------------------------------
    # Section rendering methods
    # ----------------------------------------------------------------

    def _render_executive_summary(
        self,
        pdf: DossierPDF,
        dossier_data: DossierData,
        figures: dict[str, go.Figure],
    ) -> None:
        """Render Executive Summary section."""
        pdf.add_page()
        self._section_title(pdf, "Executive Summary")

        section = dossier_data.sections.get("executive_summary")
        scorecard = dossier_data.scorecard
        verdict = scorecard.get("verdict", {})
        composite = scorecard.get("composite", {})

        # Verdict badge
        verdict_level = verdict.get("level", "")
        if verdict_level:
            self._draw_verdict_badge(pdf, verdict_level)
            pdf.ln(6)

        # Composite score
        score = composite.get("score", 0)
        self._subsection_title(pdf, f"Composite Score: {score:.1f}/100")
        pdf.ln(2)

        # Narrative
        if section and section.narrative:
            self._body_text(pdf, section.narrative)
            pdf.ln(4)

        # Strengths and risks from section data
        if section and section.data:
            violations = section.data.get("dimension_violations", [])
            if violations:
                self._subsection_title(pdf, "Key Risks")
                for v in violations:
                    self._body_text(pdf, f"  - Dimension violation: {v}")
                pdf.ln(4)

            if section.data.get("forced_conditional"):
                self._body_text(
                    pdf,
                    "Note: Score exceeds GO threshold but was downgraded to "
                    "CONDITIONAL due to dimension violations.",
                )
                pdf.ln(4)

        # Radar chart
        radar_fig = figures.get("radar_single")
        if radar_fig:
            self._embed_chart(pdf, radar_fig)
            pdf.ln(4)

    def _render_target_overview(
        self, pdf: DossierPDF, dossier_data: DossierData
    ) -> None:
        """Render Target Overview section with gene identifiers and protein data."""
        pdf.add_page()
        self._section_title(pdf, "Target Overview")

        section = dossier_data.sections.get("target_overview")
        identifiers = dossier_data.gene_identifiers or {}

        # Gene identifiers table
        if identifiers:
            table_data = [["Field", "Value"]]
            id_fields = [
                ("Gene Symbol", identifiers.get("canonical_symbol", "")),
                ("Ensembl ID", identifiers.get("ensembl_id", "")),
                ("UniProt Accession", identifiers.get("uniprot_accession", "")),
                ("Query Symbol", identifiers.get("query_symbol", "")),
            ]
            for field_name, value in id_fields:
                if value:
                    table_data.append([field_name, str(value)])

            if len(table_data) > 1:
                self._render_table(pdf, table_data)
                pdf.ln(6)

        # Narrative (protein function, disease context)
        if section and section.narrative:
            self._body_text(pdf, section.narrative)
            pdf.ln(4)

        # Disease context
        if dossier_data.disease_context:
            self._subsection_title(pdf, "Disease Context")
            self._body_text(pdf, dossier_data.disease_context)
            pdf.ln(4)

    def _render_evidence_dimensions(
        self,
        pdf: DossierPDF,
        dossier_data: DossierData,
        figures: dict[str, go.Figure],
    ) -> None:
        """Render Evidence Dimensions section with per-dimension score bars and tables."""
        pdf.add_page()
        self._section_title(pdf, "Evidence Dimensions")

        section = dossier_data.sections.get("evidence_dimensions")
        composite = dossier_data.scorecard.get("composite", {})
        dimension_scores = composite.get("dimension_scores", [])

        if not dimension_scores:
            self._body_text(pdf, "No dimension scores available.")
            return

        # Narrative overview
        if section and section.narrative:
            self._body_text(pdf, section.narrative)
            pdf.ln(6)

        # Per-dimension details
        for dim in dimension_scores:
            name = dim.get("name", "unknown").replace("_", " ").title()
            score = dim.get("score", 0)
            max_score = dim.get("max_score", 1)
            coverage = dim.get("data_coverage", 0)

            self._subsection_title(pdf, name)

            # Score bar
            self._draw_score_bar(pdf, score, max_score)
            pdf.ln(2)
            self._body_text(pdf, f"Data coverage: {coverage:.0%}")
            pdf.ln(4)

            # Sub-scores table
            sub_scores = dim.get("sub_scores", [])
            if sub_scores:
                sub_table = [["Sub-Score", "Value", "Max", "Normalized"]]
                for sub in sub_scores:
                    sub_name = sub.get("name", "")
                    sub_val = sub.get("value", 0)
                    sub_max = sub.get("max_value", 1)
                    norm = sub_val / sub_max if sub_max > 0 else 0
                    sub_table.append([
                        sub_name.replace("_", " ").title(),
                        f"{sub_val:.2f}",
                        f"{sub_max:.0f}",
                        f"{norm:.3f}",
                    ])
                self._render_table(pdf, sub_table)
                pdf.ln(6)

        # Evidence bar chart
        bar_fig = figures.get("evidence_dimensions_bar")
        if bar_fig:
            pdf.add_page()
            self._subsection_title(pdf, "Dimension Scores Chart")
            self._embed_chart(pdf, bar_fig)
            pdf.ln(4)

    def _render_ai_synthesis(
        self, pdf: DossierPDF, dossier_data: DossierData
    ) -> None:
        """Render AI Synthesis section with claims table and analysis."""
        pdf.add_page()
        self._section_title(pdf, "AI Synthesis & Reasoning")

        section = dossier_data.sections.get("ai_synthesis")

        # Full synthesis narrative
        if section and section.narrative:
            self._body_text(pdf, section.narrative)
            pdf.ln(6)

        # Claims table
        if section and section.data:
            claims = section.data.get("claims", [])
            if claims:
                self._subsection_title(pdf, "Key Claims")
                claims_table = [["Claim", "Confidence", "Mode"]]
                for claim in claims:
                    text = claim.get("text", str(claim))
                    confidence = claim.get("confidence", "")
                    mode = claim.get("mode", "")
                    # Truncate long claim text for PDF table
                    if len(text) > 100:
                        text = text[:97] + "..."
                    claims_table.append([
                        text,
                        f"{confidence}" if confidence else "N/A",
                        mode,
                    ])
                self._render_table(pdf, claims_table, repeat_headings=True)
                pdf.ln(6)

            # Modes analyzed
            modes = section.data.get("modes_analyzed", [])
            if modes:
                self._body_text(
                    pdf, f"Reasoning modes analyzed: {', '.join(modes)}"
                )
                pdf.ln(4)

    def _render_scorecard(
        self,
        pdf: DossierPDF,
        dossier_data: DossierData,
        figures: dict[str, go.Figure],
    ) -> None:
        """Render Scorecard section with full scoring table and composite breakdown."""
        pdf.add_page()
        self._section_title(pdf, "Scorecard")

        section = dossier_data.sections.get("scorecard")
        composite = dossier_data.scorecard.get("composite", {})
        verdict = dossier_data.scorecard.get("verdict", {})
        dimension_scores = composite.get("dimension_scores", [])

        # Narrative
        if section and section.narrative:
            self._body_text(pdf, section.narrative)
            pdf.ln(6)

        # Full scoring table
        if dimension_scores:
            score_table = [["Dimension", "Score", "Max", "Pct", "Coverage"]]
            for dim in dimension_scores:
                name = dim.get("name", "unknown").replace("_", " ").title()
                score = dim.get("score", 0)
                max_score = dim.get("max_score", 1)
                pct = score / max_score * 100 if max_score > 0 else 0
                coverage = dim.get("data_coverage", 0)
                score_table.append([
                    name,
                    f"{score:.1f}",
                    f"{max_score:.0f}",
                    f"{pct:.0f}%",
                    f"{coverage:.0%}",
                ])
            self._render_table(pdf, score_table)
            pdf.ln(6)

        # Composite breakdown with weights
        weights = composite.get("weights", {})
        if dimension_scores and weights:
            self._subsection_title(pdf, "Composite Breakdown")
            breakdown_table = [["Dimension", "Raw", "Max", "Weight", "Weighted"]]
            # Get normalized weights
            norm_weights = weights
            if hasattr(weights, "normalized"):
                norm_weights = weights.normalized()
            elif isinstance(weights, dict):
                total = sum(weights.values()) if weights else 1
                if total > 0:
                    norm_weights = {k: v / total for k, v in weights.items()}

            for dim in dimension_scores:
                name = dim.get("name", "unknown")
                display_name = name.replace("_", " ").title()
                score = dim.get("score", 0)
                max_score = dim.get("max_score", 1)
                norm = score / max_score if max_score > 0 else 0
                weight = norm_weights.get(name, 0) if isinstance(norm_weights, dict) else 0
                weighted = norm * weight * 100
                breakdown_table.append([
                    display_name,
                    f"{score:.1f}",
                    f"{max_score:.0f}",
                    f"{weight:.3f}",
                    f"{weighted:.1f}",
                ])
            self._render_table(pdf, breakdown_table)
            pdf.ln(6)

        # Verdict rationale
        rationale = verdict.get("rationale", "")
        if rationale:
            self._subsection_title(pdf, "Verdict Rationale")
            self._body_text(pdf, rationale)
            pdf.ln(4)

        # Score breakdown chart
        score_fig = figures.get("score_breakdown")
        if score_fig:
            self._embed_chart(pdf, score_fig)
            pdf.ln(4)

        # Comparative radar if available
        comp_fig = figures.get("radar_comparative")
        if comp_fig:
            self._subsection_title(pdf, "Comparative Radar")
            self._embed_chart(pdf, comp_fig)
            pdf.ln(4)

    def _render_recommendations(
        self, pdf: DossierPDF, dossier_data: DossierData
    ) -> None:
        """Render Recommendations section with verdict, risks, and next steps."""
        pdf.add_page()
        self._section_title(pdf, "Recommendations & Next Steps")

        section = dossier_data.sections.get("recommendations")
        verdict = dossier_data.scorecard.get("verdict", {})

        # Verdict badge
        verdict_level = verdict.get("level", "")
        if verdict_level:
            self._draw_verdict_badge(pdf, verdict_level)
            pdf.ln(6)

        # Narrative (includes numbered next steps)
        if section and section.narrative:
            self._body_text(pdf, section.narrative)
            pdf.ln(6)

        # Dimension violations as risks
        if section and section.data:
            violations = section.data.get("dimension_violations", [])
            if violations:
                self._subsection_title(pdf, "Key Risks")
                for i, v in enumerate(violations, 1):
                    self._body_text(pdf, f"  {i}. Dimension violation: {v}")
                pdf.ln(4)

    def _render_audit_trail(
        self, pdf: DossierPDF, dossier_data: DossierData
    ) -> None:
        """Render Audit Trail section with evidence sources and provenance."""
        pdf.add_page()
        self._section_title(pdf, "Audit Trail & Provenance")

        section = dossier_data.sections.get("audit_trail")

        if section and section.narrative:
            self._body_text(pdf, section.narrative)
            pdf.ln(6)

        if section and section.data:
            # Evidence source table
            evidence_sources = section.data.get("evidence_sources", {})
            if evidence_sources:
                self._subsection_title(pdf, "Evidence Sources")
                source_table = [["Source", "Confidence", "Is Fallback", "Has Error"]]
                for source_name, info in evidence_sources.items():
                    conf = info.get("confidence", 0)
                    fallback = "Yes" if info.get("is_fallback") else "No"
                    error = "Yes" if info.get("has_error") else "No"
                    source_table.append([
                        source_name,
                        f"{conf:.2f}",
                        fallback,
                        error,
                    ])
                self._render_table(pdf, source_table)
                pdf.ln(6)

            # Evidence hash
            ev_hash = section.data.get("evidence_hash", "")
            if ev_hash:
                self._body_text(pdf, f"Evidence Hash: {ev_hash}")
                pdf.ln(2)

            # Scored at
            scored_at = section.data.get("scored_at", "")
            if scored_at:
                self._body_text(pdf, f"Scored At: {scored_at}")
                pdf.ln(2)

            # Reasoning provenance
            reasoning_prov = section.data.get("reasoning_provenance", {})
            if reasoning_prov:
                self._subsection_title(pdf, "AI Reasoning Provenance")
                prov_table = [["Mode", "Created At", "Tool Trace", "Hallucination Issues"]]
                for mode_name, prov_info in reasoning_prov.items():
                    created = prov_info.get("created_at", "N/A")
                    tool_trace = "Yes" if prov_info.get("has_tool_trace") else "No"
                    hall = str(prov_info.get("hallucination_issues", 0))
                    prov_table.append([mode_name, str(created), tool_trace, hall])
                self._render_table(pdf, prov_table)
                pdf.ln(6)

        # Generation timestamp
        self._body_text(pdf, f"Dossier Generated: {dossier_data.generated_at}")
        pdf.ln(2)

    # ----------------------------------------------------------------
    # Helper methods
    # ----------------------------------------------------------------

    def _embed_chart(
        self,
        pdf: DossierPDF,
        fig: go.Figure,
        width: float | None = None,
    ) -> None:
        """Embed a Plotly figure as a PNG image in the PDF.

        Uses chart_to_png_bytes from chart_export module. Creates a
        fresh BytesIO per call (pitfall #3: fpdf2 may close the stream).

        Args:
            pdf: The DossierPDF instance.
            fig: Plotly Figure to embed.
            width: Image width in mm. Defaults to page effective width.
        """
        try:
            from src.reporting.chart_export import chart_to_png_bytes

            png_bytes = chart_to_png_bytes(
                fig,
                width=self.config.chart_width,
                height=self.config.chart_height,
                scale=self.config.chart_scale,
            )
            # Fresh BytesIO per call (pitfall #3)
            img_buffer = io.BytesIO(png_bytes)
            pdf.image(img_buffer, w=width or pdf.epw)
        except Exception:
            logger.warning("Failed to embed chart in PDF", exc_info=True)
            self._body_text(pdf, "[Chart could not be rendered]")

    def _section_title(self, pdf: DossierPDF, title: str) -> None:
        """Render a section title in 16pt bold brand color."""
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(*pdf.brand_color)
        pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)

    def _subsection_title(self, pdf: DossierPDF, title: str) -> None:
        """Render a subsection title in 12pt bold dark color."""
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(29, 29, 31)
        pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    def _body_text(self, pdf: DossierPDF, text: str) -> None:
        """Render body text in 10pt Helvetica dark gray."""
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(29, 29, 31)
        pdf.multi_cell(0, 5, text)

    def _draw_verdict_badge(self, pdf: DossierPDF, verdict_level: str) -> None:
        """Draw a colored rounded rectangle verdict badge.

        Green for GO, orange for CONDITIONAL, red for NO-GO.
        """
        color_map = {
            "GO": (0, 180, 0),
            "CONDITIONAL": (255, 165, 0),
            "NO-GO": (220, 0, 0),
        }
        r, g, b = color_map.get(str(verdict_level).upper(), (128, 128, 128))

        x = pdf.get_x()
        y = pdf.get_y()

        pdf.set_fill_color(r, g, b)
        pdf.rect(x, y, 45, 12, round_corners=True, style="F")

        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(x, y + 1)
        pdf.cell(45, 10, str(verdict_level), align="C")

        # Reset position below badge
        pdf.set_xy(x, y + 14)

    def _draw_score_bar(
        self,
        pdf: DossierPDF,
        score: float,
        max_score: float,
        width: float = 100,
    ) -> None:
        """Draw a horizontal score bar with brand color fill.

        Gray background bar with colored fill proportional to score/max_score.
        Score text overlaid on the bar.
        """
        x = pdf.get_x()
        y = pdf.get_y()
        bar_height = 8

        # Gray background
        pdf.set_fill_color(230, 230, 230)
        pdf.rect(x, y, width, bar_height, style="F")

        # Brand color fill
        fill_width = (score / max_score * width) if max_score > 0 else 0
        if fill_width > 0:
            pdf.set_fill_color(*pdf.brand_color)
            pdf.rect(x, y, fill_width, bar_height, style="F")

        # Score text overlay
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(x, y)
        pdf.cell(width, bar_height, f"{score:.1f}/{max_score:.0f}", align="C")

        # Reset position below bar
        pdf.set_xy(x, y + bar_height + 2)

    def _render_table(
        self,
        pdf: DossierPDF,
        data: list[list[str]],
        repeat_headings: bool = False,
    ) -> None:
        """Render a styled table with branded header row.

        Args:
            pdf: The DossierPDF instance.
            data: List of rows; first row is the header.
            repeat_headings: If True, repeat headers on each page.
        """
        if not data:
            return

        headings_style = FontFace(
            emphasis="BOLD",
            color=(255, 255, 255),
            fill_color=pdf.brand_color,
        )

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(29, 29, 31)

        num_cols = len(data[0]) if data else 0
        col_width = pdf.epw / num_cols if num_cols > 0 else pdf.epw

        with pdf.table(
            headings_style=headings_style,
            cell_fill_color=245,
            cell_fill_mode="ROWS",
            line_height=6,
            first_row_as_headings=True,
            repeat_headings=1 if repeat_headings else 0,
        ) as table:
            for row_data in data:
                row = table.row()
                for cell_data in row_data:
                    row.cell(str(cell_data))


def generate_dossier(
    scorecard_result: Any,
    evidence: Any,
    output_dir: Path,
    reasoning_results: Any | None = None,
    pipeline_report: dict | None = None,
    comparative: Any | None = None,
    config: DossierConfig | None = None,
    formats: tuple[str, ...] = ("html", "pdf"),
) -> dict[str, Path]:
    """Generate dossier in requested formats. Returns dict of format -> path.

    Convenience function wiring together data collection, visualization,
    and dual rendering.

    Args:
        scorecard_result: ScorecardResult from scoring module.
        evidence: AggregatedEvidence from evidence module.
        output_dir: Directory to write output files.
        reasoning_results: Optional dict of mode_name -> ReasoningResult.
        pipeline_report: Optional pipeline report dict.
        comparative: Optional ComparativeScorecard.
        config: Optional rendering configuration.
        formats: Tuple of formats to generate ("html", "pdf").

    Returns:
        Dict mapping format name to output file Path.
    """
    from src.reporting.data_collector import collect_dossier_data
    from src.reporting.html_renderer import HTMLDossierRenderer

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect data
    dossier_data = collect_dossier_data(
        scorecard_result=scorecard_result,
        evidence=evidence,
        reasoning_results=reasoning_results,
        pipeline_report=pipeline_report,
        comparative=comparative,
        config=config,
    )

    gene = dossier_data.gene_symbol.lower()
    results: dict[str, Path] = {}

    if "html" in formats:
        html_renderer = HTMLDossierRenderer(config=config)
        html_path = output_dir / f"{gene}_dossier.html"
        html_renderer.render_to_file(dossier_data, html_path)
        results["html"] = html_path
        logger.info("Generated HTML dossier: %s", html_path)

    if "pdf" in formats:
        pdf_renderer = PDFDossierRenderer(config=config)
        pdf_path = output_dir / f"{gene}_dossier.pdf"
        pdf_renderer.render_to_file(dossier_data, pdf_path)
        results["pdf"] = pdf_path
        logger.info("Generated PDF dossier: %s", pdf_path)

    return results
