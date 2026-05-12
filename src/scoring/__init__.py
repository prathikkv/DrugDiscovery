"""Scoring framework: models, weights, sub-scores, and dimension calculators.

Public API for the target scoring module. All scoring types and functions
are exported from this package for convenient access.
"""

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
from src.scoring.weights import DEFAULT_WEIGHTS, DIMENSION_MINIMUMS

__all__ = [
    "SubScore",
    "DimensionScore",
    "WeightConfig",
    "CompositeScore",
    "VerdictLevel",
    "Verdict",
    "ScorecardResult",
    "ComparativeScorecard",
    "DEFAULT_WEIGHTS",
    "DIMENSION_MINIMUMS",
]
