"""Comparative target scoring and visualization.

Multi-target comparison with ranking and Plotly radar chart generation.
Enables side-by-side assessment of 1-20 targets with normalized
dimension scores displayed as polar area charts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import plotly.graph_objects as go

from src.scoring.framework import ScoringFramework
from src.scoring.models import (
    ComparativeScorecard,
    ScorecardResult,
    VerdictLevel,
    WeightConfig,
)

if TYPE_CHECKING:
    from src.evidence.models import AggregatedEvidence
    from src.reasoning.models import ReasoningResult


# Display names for the 7 dimensions on radar charts
DIMENSION_DISPLAY_NAMES = [
    "Genetic Evidence",
    "Expression Biology",
    "Druggability",
    "Safety/Selectivity",
    "Competitive Landscape",
    "Clinical/Translational",
    "Literature Consensus",
]


def score_multiple_targets(
    evidences: list[AggregatedEvidence],
    weights: WeightConfig | None = None,
    minimums: dict[str, float] | None = None,
    reasoning_results_map: dict[str, dict[str, ReasoningResult]] | None = None,
) -> ComparativeScorecard:
    """Score multiple targets and produce a comparative scorecard with ranking.

    Args:
        evidences: List of AggregatedEvidence, one per target gene.
        weights: Optional custom weight configuration.
        minimums: Optional custom dimension minimum thresholds.
        reasoning_results_map: Optional map of gene_symbol -> {mode -> ReasoningResult}.

    Returns:
        ComparativeScorecard with all results and ranking by composite score descending.
    """
    framework = ScoringFramework(weights=weights, minimums=minimums)

    scorecards: list[ScorecardResult] = []
    for evidence in evidences:
        gene_symbol = evidence.gene.canonical_symbol

        # Get reasoning results for this gene if available
        reasoning_results = None
        if reasoning_results_map:
            reasoning_results = reasoning_results_map.get(gene_symbol)

        result = framework.score_target(
            evidence, reasoning_results=reasoning_results
        )
        scorecards.append(result)

    return ComparativeScorecard.from_scorecards(scorecards)


def build_comparative_radar(scorecards: list[ScorecardResult]) -> go.Figure:
    """Build a Plotly radar chart comparing multiple targets.

    Each target gets one Scatterpolar trace with normalized dimension values
    (0-1 range). Polygons are closed by appending the first value at the end.

    Args:
        scorecards: List of ScorecardResult to compare.

    Returns:
        Plotly Figure with one Scatterpolar trace per target.
    """
    fig = go.Figure()

    for scorecard in scorecards:
        # Normalize each dimension to 0-1
        values: list[float] = []
        for dim in scorecard.composite.dimension_scores:
            if dim.max_score > 0:
                values.append(round(dim.score / dim.max_score, 3))
            else:
                values.append(0.0)

        # Close the polygon by appending the first value
        closed_values = values + [values[0]]
        closed_names = list(DIMENSION_DISPLAY_NAMES) + [DIMENSION_DISPLAY_NAMES[0]]

        fig.add_trace(
            go.Scatterpolar(
                r=closed_values,
                theta=closed_names,
                fill="toself",
                name=scorecard.gene_symbol,
                opacity=0.6,
            )
        )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
            ),
        ),
        showlegend=True,
        title="Comparative Target Profile",
    )

    return fig


def build_single_radar(scorecard: ScorecardResult) -> go.Figure:
    """Build a Plotly radar chart for a single target.

    Uses verdict-based coloring:
    - GO: green
    - CONDITIONAL: yellow/orange
    - NO-GO: red

    Args:
        scorecard: Single ScorecardResult to visualize.

    Returns:
        Plotly Figure with one Scatterpolar trace.
    """
    # Select color based on verdict
    color_map = {
        VerdictLevel.GO: "rgba(0, 200, 0, 0.4)",
        VerdictLevel.CONDITIONAL: "rgba(255, 165, 0, 0.4)",
        VerdictLevel.NO_GO: "rgba(255, 0, 0, 0.4)",
    }
    line_color_map = {
        VerdictLevel.GO: "rgba(0, 200, 0, 1.0)",
        VerdictLevel.CONDITIONAL: "rgba(255, 165, 0, 1.0)",
        VerdictLevel.NO_GO: "rgba(255, 0, 0, 1.0)",
    }

    fill_color = color_map.get(scorecard.verdict.level, "rgba(100, 100, 100, 0.4)")
    line_color = line_color_map.get(scorecard.verdict.level, "rgba(100, 100, 100, 1.0)")

    # Normalize dimension values
    values: list[float] = []
    for dim in scorecard.composite.dimension_scores:
        if dim.max_score > 0:
            values.append(round(dim.score / dim.max_score, 3))
        else:
            values.append(0.0)

    # Close polygon
    closed_values = values + [values[0]]
    closed_names = list(DIMENSION_DISPLAY_NAMES) + [DIMENSION_DISPLAY_NAMES[0]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=closed_values,
            theta=closed_names,
            fill="toself",
            fillcolor=fill_color,
            line=dict(color=line_color),
            name=scorecard.gene_symbol,
            opacity=0.8,
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
            ),
        ),
        showlegend=True,
        title=f"Target Profile: {scorecard.gene_symbol} ({scorecard.verdict.level.value})",
    )

    return fig
