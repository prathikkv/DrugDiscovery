"""Target scoring framework for BioOrchestrator v2.

Provides deterministic, transparent GO/CONDITIONAL/NO-GO recommendations
with 7-dimension scoring, configurable weights, and comparative assessment.
"""

from src.scoring.models import (
    SubScore,
    DimensionScore,
    WeightConfig,
    CompositeScore,
    VerdictLevel,
    Verdict,
    ScorecardResult,
    ComparativeScorecard,
)
from src.scoring.weights import DEFAULT_WEIGHTS, DIMENSION_MINIMUMS
from src.scoring.dimensions import (
    score_genetic_evidence,
    score_expression_biology,
    score_druggability,
    score_safety_selectivity,
    score_competitive_landscape,
    score_clinical_translational,
    score_literature_consensus,
)
from src.scoring.verdict import compute_composite, determine_verdict
from src.scoring.framework import ScoringFramework, score_target
from src.scoring.comparative import (
    score_multiple_targets,
    build_comparative_radar,
    build_single_radar,
)

__all__ = [
    # Models
    "SubScore",
    "DimensionScore",
    "WeightConfig",
    "CompositeScore",
    "VerdictLevel",
    "Verdict",
    "ScorecardResult",
    "ComparativeScorecard",
    # Constants
    "DEFAULT_WEIGHTS",
    "DIMENSION_MINIMUMS",
    # Dimension calculators
    "score_genetic_evidence",
    "score_expression_biology",
    "score_druggability",
    "score_safety_selectivity",
    "score_competitive_landscape",
    "score_clinical_translational",
    "score_literature_consensus",
    # Scoring pipeline
    "compute_composite",
    "determine_verdict",
    "ScoringFramework",
    "score_target",
    # Comparative
    "score_multiple_targets",
    "build_comparative_radar",
    "build_single_radar",
]
