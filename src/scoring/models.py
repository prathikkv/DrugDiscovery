"""Scoring data models: sub-scores, dimensions, weights, composites, verdicts, and scorecards.

Pydantic v2 models enforce score bounds, weight normalization, and threshold logic
at the model level. All scoring types are defined here for the entire scoring framework.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class VerdictLevel(str, Enum):
    """GO/CONDITIONAL/NO-GO recommendation levels."""

    GO = "GO"
    CONDITIONAL = "CONDITIONAL"
    NO_GO = "NO-GO"


class SubScore(BaseModel):
    """Individual sub-score within a scoring dimension.

    Attributes:
        name: Sub-score identifier (e.g., "gwas_associations")
        value: Actual score (>= 0)
        max_value: Maximum possible score (> 0)
        description: Human-readable explanation of the score
        data_source: Which evidence source contributed this score
    """

    name: str
    value: float = Field(ge=0)
    max_value: float = Field(gt=0)
    description: str = ""
    data_source: str = ""

    @property
    def normalized(self) -> float:
        """Return value normalized to 0-1 range, rounded to 3 decimals."""
        if self.max_value == 0:
            return 0.0
        return round(self.value / self.max_value, 3)


class DimensionScore(BaseModel):
    """Score for one of the 7 scoring dimensions.

    Attributes:
        name: Dimension identifier (e.g., "genetic_evidence")
        score: Total dimension score (>= 0, <= max_score)
        max_score: Maximum possible score (e.g., 15 or 10)
        sub_scores: Component sub-scores that make up this dimension
        data_coverage: Fraction of expected data present (0.0-1.0)
    """

    name: str
    score: float = Field(ge=0)
    max_score: float = Field(gt=0)
    sub_scores: list[SubScore] = Field(default_factory=list)
    data_coverage: float = Field(ge=0.0, le=1.0, default=0.0)

    @model_validator(mode="after")
    def score_within_max(self) -> DimensionScore:
        """Validate score does not exceed max_score. Round to 2 decimals."""
        if self.score > self.max_score:
            raise ValueError(
                f"score {self.score} exceeds max_score {self.max_score}"
            )
        self.score = round(self.score, 2)
        return self


class WeightConfig(BaseModel):
    """User-configurable dimension weights.

    Default weights from REQ-402: 6 dimensions at 15.0 each, literature at 10.0.
    Total defaults to 100.0. Weights are always normalized via normalized() method.
    """

    genetic_evidence: float = 15.0
    expression_biology: float = 15.0
    druggability: float = 15.0
    safety_selectivity: float = 15.0
    competitive_landscape: float = 15.0
    clinical_translational: float = 15.0
    literature_consensus: float = 10.0

    def normalized(self) -> dict[str, float]:
        """Return weights normalized to sum to 1.0.

        If total sum is 0, returns equal weights (1/7 each).
        """
        raw = self.as_dict()
        total = sum(raw.values())
        if total == 0:
            return {k: 1.0 / len(raw) for k in raw}
        return {k: v / total for k, v in raw.items()}

    def as_dict(self) -> dict[str, float]:
        """Return raw weights as a dictionary."""
        return {
            "genetic_evidence": self.genetic_evidence,
            "expression_biology": self.expression_biology,
            "druggability": self.druggability,
            "safety_selectivity": self.safety_selectivity,
            "competitive_landscape": self.competitive_landscape,
            "clinical_translational": self.clinical_translational,
            "literature_consensus": self.literature_consensus,
        }


class CompositeScore(BaseModel):
    """Weighted composite score across all dimensions (0-100).

    Attributes:
        score: Weighted composite score (0-100)
        dimension_scores: Individual dimension scores
        weights: Weight configuration used for computation
        formula_version: Version of the scoring formula
    """

    score: float = Field(ge=0, le=100)
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    weights: WeightConfig = Field(default_factory=WeightConfig)
    formula_version: str = "v1.0"


class Verdict(BaseModel):
    """GO/CONDITIONAL/NO-GO decision with rationale.

    Attributes:
        level: The recommendation level
        score: The composite score that led to this verdict
        dimension_violations: Dimensions below their minimum threshold
        forced_conditional: True when composite >= 75 but violations exist
        rationale: Human-readable explanation
    """

    level: VerdictLevel
    score: float
    dimension_violations: list[str] = Field(default_factory=list)
    forced_conditional: bool = False
    rationale: str = ""


class ScorecardResult(BaseModel):
    """Complete scorecard for a single target gene.

    Attributes:
        gene_symbol: The target gene symbol (e.g., "EGFR")
        disease_context: Optional disease/indication context
        composite: The weighted composite score with dimensions
        verdict: The GO/CONDITIONAL/NO-GO decision
        evidence_hash: SHA256 of input evidence for reproducibility
        scored_at: ISO 8601 timestamp of when scoring was performed
    """

    gene_symbol: str
    disease_context: str | None = None
    composite: CompositeScore
    verdict: Verdict
    evidence_hash: str = ""
    scored_at: str = ""


class ComparativeScorecard(BaseModel):
    """Side-by-side comparison of 1-20 scored targets.

    Attributes:
        scorecards: List of individual scorecard results (1-20)
        ranking: Gene symbols sorted by composite score descending
    """

    scorecards: list[ScorecardResult]
    ranking: list[str] = Field(default_factory=list)

    @field_validator("scorecards")
    @classmethod
    def validate_count(cls, v: list[ScorecardResult]) -> list[ScorecardResult]:
        """Validate scorecard count is between 1 and 20."""
        if len(v) < 1:
            raise ValueError("Need at least 1 scorecard")
        if len(v) > 20:
            raise ValueError("Maximum 20 targets for comparison")
        return v

    @classmethod
    def from_scorecards(
        cls, scorecards: list[ScorecardResult]
    ) -> ComparativeScorecard:
        """Create a ComparativeScorecard with ranking sorted by composite desc."""
        ranked = sorted(scorecards, key=lambda s: s.composite.score, reverse=True)
        return cls(
            scorecards=scorecards,
            ranking=[s.gene_symbol for s in ranked],
        )
