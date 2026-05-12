"""Default weight configuration and dimension minimum thresholds.

Provides the default scoring weights (REQ-402) and critical dimension
minimums that can force a CONDITIONAL verdict even when composite score
is above the GO threshold.
"""

from src.scoring.models import WeightConfig

# Default weights from REQ-402: 6 dimensions at 15.0, literature at 10.0
# Total = 100.0. Normalized via WeightConfig.normalized() for computation.
DEFAULT_WEIGHTS = WeightConfig()

# Dimension minimums: only 3 critical dimensions have minimums.
# Values are fractions of max_score. If a dimension's score/max_score
# falls below its minimum, the verdict is forced to CONDITIONAL.
DIMENSION_MINIMUMS: dict[str, float] = {
    "genetic_evidence": 0.20,  # At least 3/15 points
    "safety_selectivity": 0.20,  # At least 3/15 points
    "druggability": 0.13,  # At least 2/15 points (approx)
}
