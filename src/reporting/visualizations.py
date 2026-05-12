"""Visualization builder: create all Plotly figures for a dossier.

VisualizationBuilder takes a DossierData instance and produces a dict of
chart_id -> Plotly Figure for all available chart types. Individual builder
methods return None when required data is missing, ensuring the dossier
renders gracefully with partial data.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import plotly.graph_objects as go

from src.reporting.models import DossierData

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Styling constants matching project design system
PLOTLY_TEMPLATE = "plotly_white"
BRAND_COLOR_HEX = "#0071e3"
BRAND_COLOR_RGB = "rgb(0, 113, 227)"
BRAND_COLOR_RGBA = "rgba(0, 113, 227, 0.7)"
LIGHT_GRAY = "rgba(220, 220, 220, 0.5)"


class VisualizationBuilder:
    """Creates all Plotly figures for a dossier from DossierData.

    Each build method returns a Figure or None (if required data is absent).
    build_all() collects all non-None figures into a dict keyed by chart_id.
    """

    def __init__(self, dossier_data: DossierData) -> None:
        self.data = dossier_data

    def build_all(self) -> dict[str, go.Figure]:
        """Build all available figures. Returns dict of chart_id -> Figure.

        Skips charts whose data is missing. Never raises -- logs warnings instead.
        """
        builders = {
            "radar_single": self.build_radar_single,
            "radar_comparative": self.build_radar_comparative,
            "evidence_dimensions_bar": self.build_evidence_bar,
            "score_breakdown": self.build_score_breakdown,
            "umap_celltype": self.build_umap,
            "expression_heatmap": self.build_heatmap,
            "volcano": self.build_volcano,
        }

        figures: dict[str, go.Figure] = {}
        for chart_id, builder in builders.items():
            try:
                fig = builder()
                if fig is not None:
                    figures[chart_id] = fig
            except Exception:
                logger.warning("Failed to build chart '%s'", chart_id, exc_info=True)

        return figures

    def build_radar_single(self) -> go.Figure | None:
        """Build single-target radar chart using upstream build_single_radar.

        Reconstructs a ScorecardResult from the serialized dict and delegates
        to src.scoring.comparative.build_single_radar for consistent styling.
        """
        try:
            from src.scoring.models import ScorecardResult
            from src.scoring.comparative import build_single_radar

            scorecard_obj = ScorecardResult(**self.data.scorecard)
            if not scorecard_obj.composite.dimension_scores:
                return None
            return build_single_radar(scorecard_obj)
        except (ImportError, KeyError, TypeError, Exception) as exc:
            logger.warning("Cannot build radar_single: %s", exc)
            return None

    def build_radar_comparative(self) -> go.Figure | None:
        """Build comparative radar chart for multiple targets.

        Only available when comparative data is present in the dossier.
        """
        if self.data.comparative is None:
            return None

        try:
            from src.scoring.models import ScorecardResult
            from src.scoring.comparative import build_comparative_radar

            comp_data = self.data.comparative
            scorecards_data = comp_data.get("scorecards", [])
            if not scorecards_data:
                return None

            scorecard_objs = [ScorecardResult(**sc) for sc in scorecards_data]
            return build_comparative_radar(scorecard_objs)
        except (ImportError, KeyError, TypeError, Exception) as exc:
            logger.warning("Cannot build radar_comparative: %s", exc)
            return None

    def build_evidence_bar(self) -> go.Figure | None:
        """Build horizontal bar chart showing dimension scores vs max.

        Shows each of the 7 dimensions with filled (actual) and unfilled (remaining)
        portions, plus data_coverage annotation.
        """
        composite = self.data.scorecard.get("composite", {})
        dimension_scores = composite.get("dimension_scores", [])
        if not dimension_scores:
            return None

        names = []
        scores = []
        max_scores = []
        coverages = []

        for dim in dimension_scores:
            names.append(dim.get("name", "unknown").replace("_", " ").title())
            scores.append(dim.get("score", 0))
            max_scores.append(dim.get("max_score", 1))
            coverages.append(dim.get("data_coverage", 0))

        # Remaining (unfilled) portion
        remaining = [m - s for s, m in zip(scores, max_scores)]

        fig = go.Figure()

        # Actual score bars
        fig.add_trace(
            go.Bar(
                y=names,
                x=scores,
                orientation="h",
                name="Score",
                marker_color=BRAND_COLOR_RGB,
                text=[f"{s:.1f}" for s in scores],
                textposition="inside",
                insidetextanchor="end",
            )
        )

        # Remaining bars (gray)
        fig.add_trace(
            go.Bar(
                y=names,
                x=remaining,
                orientation="h",
                name="Remaining",
                marker_color=LIGHT_GRAY,
                text=[f"/{m:.0f}" for m in max_scores],
                textposition="inside",
                insidetextanchor="start",
            )
        )

        # Add data coverage annotations on the right
        for i, coverage in enumerate(coverages):
            fig.add_annotation(
                x=max_scores[i] + 0.5,
                y=i,
                text=f"{coverage:.0%} data",
                showarrow=False,
                font=dict(size=9, color="#6e6e73"),
                xanchor="left",
            )

        fig.update_layout(
            barmode="stack",
            title="Evidence Dimension Scores",
            xaxis_title="Score",
            yaxis=dict(autorange="reversed"),
            template=PLOTLY_TEMPLATE,
            height=max(400, len(names) * 55),
            showlegend=False,
            margin=dict(l=160, r=80, t=50, b=40),
        )

        return fig

    def build_score_breakdown(self) -> go.Figure | None:
        """Build grouped bar chart showing sub-scores within each dimension.

        Each dimension's sub-scores are shown as grouped bars with their
        normalized values (0-1).
        """
        composite = self.data.scorecard.get("composite", {})
        dimension_scores = composite.get("dimension_scores", [])
        if not dimension_scores:
            return None

        # Collect all unique sub-score names across dimensions
        all_sub_names: list[str] = []
        for dim in dimension_scores:
            for sub in dim.get("sub_scores", []):
                name = sub.get("name", "")
                if name and name not in all_sub_names:
                    all_sub_names.append(name)

        if not all_sub_names:
            return None

        dim_names = [
            dim.get("name", "unknown").replace("_", " ").title()
            for dim in dimension_scores
        ]

        fig = go.Figure()

        for sub_name in all_sub_names:
            values = []
            for dim in dimension_scores:
                sub_scores = dim.get("sub_scores", [])
                found = False
                for sub in sub_scores:
                    if sub.get("name") == sub_name:
                        max_val = sub.get("max_value", 1)
                        val = sub.get("value", 0)
                        normalized = val / max_val if max_val > 0 else 0
                        values.append(round(normalized, 3))
                        found = True
                        break
                if not found:
                    values.append(0)

            display_name = sub_name.replace("_", " ").title()
            fig.add_trace(
                go.Bar(
                    x=dim_names,
                    y=values,
                    name=display_name,
                )
            )

        fig.update_layout(
            barmode="group",
            title="Sub-Score Breakdown by Dimension",
            yaxis_title="Normalized Score (0-1)",
            template=PLOTLY_TEMPLATE,
            height=500,
            margin=dict(l=60, r=20, t=50, b=100),
            xaxis_tickangle=-45,
        )

        return fig

    def build_umap(self) -> go.Figure | None:
        """Build UMAP cell-type plot from pipeline report data.

        Delegates to bioorchestrator_real.utils.plotting.plot_umap() if
        pipeline data includes UMAP coordinates.
        """
        if not self.data.pipeline_report:
            return None

        umap_data = self.data.pipeline_report.get("umap_data")
        if not umap_data:
            return None

        try:
            from bioorchestrator_real.utils.plotting import plot_umap

            coords = umap_data.get("coords", {})
            cell_types = umap_data.get("cell_types", [])
            title = umap_data.get("title", "UMAP -- Cell Types")

            if not coords or not cell_types:
                return None

            return plot_umap(coords, cell_types, title)
        except (ImportError, KeyError, TypeError, Exception) as exc:
            logger.warning("Cannot build umap_celltype: %s", exc)
            return None

    def build_heatmap(self) -> go.Figure | None:
        """Build expression heatmap from pipeline report data.

        Delegates to bioorchestrator_real.utils.plotting.plot_expression_heatmap()
        if pipeline data includes expression matrix.
        """
        if not self.data.pipeline_report:
            return None

        expr_data = self.data.pipeline_report.get("expression_data")
        if not expr_data:
            return None

        try:
            from bioorchestrator_real.utils.plotting import plot_expression_heatmap

            return plot_expression_heatmap(expr_data)
        except (ImportError, KeyError, TypeError, Exception) as exc:
            logger.warning("Cannot build expression_heatmap: %s", exc)
            return None

    def build_volcano(self) -> go.Figure | None:
        """Build volcano plot from pipeline report DE data.

        Delegates to bioorchestrator_real.utils.plotting.plot_volcano()
        if pipeline data includes differential expression results.
        """
        if not self.data.pipeline_report:
            return None

        de_data = self.data.pipeline_report.get("de_data")
        if not de_data:
            return None

        try:
            from bioorchestrator_real.utils.plotting import plot_volcano

            return plot_volcano(de_data)
        except (ImportError, KeyError, TypeError, Exception) as exc:
            logger.warning("Cannot build volcano: %s", exc)
            return None
