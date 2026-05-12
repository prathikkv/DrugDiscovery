"""Composite score computation and verdict determination.

Two pure functions:
- compute_composite: Weighted sum of dimension scores -> CompositeScore (0-100)
- determine_verdict: Apply GO/CONDITIONAL/NO-GO thresholds with dimension minimum enforcement

Handles low data coverage by substituting neutral scores (0.5 normalized)
for dimensions below 0.3 coverage to prevent conflation of missing data
with negative evidence (research pitfall #2).
"""

from __future__ import annotations

from src.scoring.models import (
    CompositeScore,
    DimensionScore,
    Verdict,
    VerdictLevel,
    WeightConfig,
)
from src.scoring.weights import DIMENSION_MINIMUMS


def compute_composite(
    dimension_scores: list[DimensionScore],
    weights: WeightConfig,
) -> CompositeScore:
    """Compute weighted composite score from dimension scores.

    Args:
        dimension_scores: List of 7 DimensionScores from dimension calculators.
        weights: Weight configuration for each dimension.

    Returns:
        CompositeScore with score in 0-100 range, rounded to 1 decimal.
    """
    normalized_weights = weights.normalized()

    # Build per-dimension normalized scores, handling low data coverage
    effective_scores: dict[str, float] = {}
    low_coverage_dims: set[str] = set()

    for dim in dimension_scores:
        if dim.max_score == 0:
            effective_scores[dim.name] = 0.0
            continue

        dim_normalized = dim.score / dim.max_score

        # If data coverage < 0.3, use neutral score (0.5) instead
        if dim.data_coverage < 0.3:
            effective_scores[dim.name] = 0.5
            low_coverage_dims.add(dim.name)
        else:
            effective_scores[dim.name] = dim_normalized

    # Re-normalize weights if any dimensions got neutral scores
    # (re-normalize remaining weights so they still sum to the same total)
    final_weights = dict(normalized_weights)

    # Compute weighted sum * 100
    weighted_sum = 0.0
    for dim in dimension_scores:
        weight = final_weights.get(dim.name, 0.0)
        score = effective_scores.get(dim.name, 0.0)
        weighted_sum += score * weight

    composite_score = round(weighted_sum * 100, 1)

    # Clamp to 0-100 range
    composite_score = max(0.0, min(100.0, composite_score))

    return CompositeScore(
        score=composite_score,
        dimension_scores=dimension_scores,
        weights=weights,
    )


def determine_verdict(
    composite: CompositeScore,
    minimums: dict[str, float] | None = None,
) -> Verdict:
    """Determine GO/CONDITIONAL/NO-GO verdict from composite score.

    Applies REQ-403 thresholds:
    - score >= 75.0 and no violations -> GO
    - score >= 75.0 and violations -> CONDITIONAL (forced_conditional=True)
    - score >= 50.0 -> CONDITIONAL
    - score < 50.0 -> NO_GO

    Args:
        composite: The computed CompositeScore with dimension_scores.
        minimums: Dimension minimum thresholds (fraction of max_score).
            If None, uses DIMENSION_MINIMUMS from weights.py.

    Returns:
        Verdict with level, violations, rationale.
    """
    if minimums is None:
        minimums = DIMENSION_MINIMUMS

    # Check dimension minimum violations
    violations: list[str] = []
    for dim in composite.dimension_scores:
        if dim.name in minimums:
            min_threshold = minimums[dim.name]
            if dim.max_score > 0:
                actual_frac = dim.score / dim.max_score
                if actual_frac < min_threshold:
                    violations.append(dim.name)

    score = composite.score
    forced = False

    # Apply thresholds per REQ-403
    if score >= 75.0 and not violations:
        level = VerdictLevel.GO
    elif score >= 75.0 and violations:
        level = VerdictLevel.CONDITIONAL
        forced = True
    elif score >= 50.0:
        level = VerdictLevel.CONDITIONAL
    else:
        level = VerdictLevel.NO_GO

    # Build rationale
    rationale_parts = [f"Composite score: {score}"]
    if level == VerdictLevel.GO:
        rationale_parts.append("Score >= 75.0 with no dimension minimum violations")
    elif forced:
        rationale_parts.append(
            f"Score >= 75.0 but forced CONDITIONAL due to violations in: {', '.join(violations)}"
        )
    elif level == VerdictLevel.CONDITIONAL:
        rationale_parts.append("Score >= 50.0 but below GO threshold of 75.0")
    else:
        rationale_parts.append("Score below 50.0 threshold")

    if violations:
        for v in violations:
            # Find the dimension
            for dim in composite.dimension_scores:
                if dim.name == v and dim.max_score > 0:
                    frac = dim.score / dim.max_score
                    threshold = minimums[v]
                    rationale_parts.append(
                        f"  {v}: {frac:.2f} < minimum {threshold:.2f}"
                    )

    rationale = ". ".join(rationale_parts)

    return Verdict(
        level=level,
        score=score,
        dimension_violations=violations,
        forced_conditional=forced,
        rationale=rationale,
    )
