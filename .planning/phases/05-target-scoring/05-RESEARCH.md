# Phase 5: Target Scoring - Research

**Researched:** 2026-05-12
**Domain:** Pharmaceutical target scoring framework with deterministic multi-dimension computation, decision thresholds, weight customization, and comparative visualization
**Confidence:** MEDIUM-HIGH

## Summary

Phase 5 builds the quantitative scoring engine that converts the raw evidence from Phase 3 (6 evidence sources) and the AI reasoning outputs from Phase 4 (5 reasoning modes) into a deterministic, transparent GO/CONDITIONAL/NO-GO recommendation per target gene. The scoring framework uses 7 dimensions with 24 sub-scores on a 0-100 composite scale, inspired by (but adapted from) the GOT-IT framework published in Nature Reviews Drug Discovery (2021). The LLM explains scores but does not compute them -- all calculations are deterministic Python code using published formulas.

The key architectural insight is that this module is a **pure computation layer** sitting between the evidence/reasoning data and the UI/report layers. It takes structured evidence data as input and produces structured score objects as output. No API calls, no LLM inference, no side effects. This makes it highly testable, fast, and deterministic -- a pharma VP can re-run scoring with different weights and get identical results every time.

**Primary recommendation:** Build the scoring module as a standalone `src/scoring/` package with Pydantic v2 models for all score dataclasses, pure functions for each dimension calculator, a configurable weight system, and Plotly `go.Scatterpolar` for radar chart visualization. Use the existing `AggregatedEvidence` and `ReasoningResult` objects as inputs, never re-fetch data.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | >=2.11.0 | Score data models (DimensionScore, SubScore, CompositeScore, Verdict, ScorecardResult) | Already used in reasoning models; v2 validators enforce score bounds (0-100), weight normalization, and threshold logic at the model level |
| plotly | 5.24.1 | Radar charts (`go.Scatterpolar`) for dimension profile visualization and comparative target overlays | Already used in the project for interactive charts; Streamlit has native `st.plotly_chart` integration |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | 1.26.4 | Weighted average computation, score normalization, array operations for batch scoring | Already installed; use for vectorized multi-target score computation |
| hashlib (stdlib) | 3.x | SHA256 hashing of score inputs for audit trail determinism verification | Already used in compliance module; hash evidence+weights to prove reproducibility |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom weighted sum | scikit-learn scoring | Overkill -- we need simple weighted arithmetic, not ML metrics. Custom is clearer and auditable. |
| Plotly radar | matplotlib polar | matplotlib has no interactivity; Plotly charts are zoomable, hoverable, and exportable from Streamlit |
| Pydantic models | Plain dataclasses | dataclasses lack validators for score bounds, weight normalization, and threshold enforcement |

**Installation:**
No new dependencies needed. All libraries are already in the project.

## Architecture Patterns

### Recommended Project Structure

```
src/scoring/
    __init__.py              # Public API: ScoringFramework, DimensionScore, SubScore,
                             # CompositeScore, Verdict, WeightConfig, ScorecardResult,
                             # ComparativeScorecard
    models.py                # Pydantic v2 models for all score types
    dimensions.py            # 7 dimension calculators (pure functions)
    sub_scores.py            # 24 sub-score extractors (pure functions mapping evidence -> 0-N raw)
    weights.py               # WeightConfig with defaults, normalization, validation
    framework.py             # ScoringFramework orchestrator (wire dimensions + weights + thresholds)
    verdict.py               # GO/CONDITIONAL/NO-GO decision logic with dimension minimums
    comparative.py           # Multi-target comparison, ranking, radar chart data generation
```

### Pattern 1: Pure Function Dimension Calculators

**What:** Each of the 7 dimensions is a pure function that takes evidence data and returns a `DimensionScore` with its sub-scores. No side effects, no I/O, no LLM calls.

**When to use:** For every dimension calculation. The function receives the relevant `EvidenceResult` objects from `AggregatedEvidence` and/or `ReasoningResult` data, and returns a numeric score.

**Example:**

```python
from src.scoring.models import DimensionScore, SubScore

def score_genetic_evidence(
    opentargets_data: dict | None,
    disease_context: str | None = None,
) -> DimensionScore:
    """Score genetic evidence dimension (max 15 points).

    Sub-scores:
    - gwas_associations (0-5): GWAS hits for target-disease pair
    - genetic_association_score (0-4): OpenTargets overall association score
    - causal_evidence (0-3): Mendelian disease links
    - functional_genomics (0-3): Functional genomics evidence
    """
    sub_scores = []

    # Sub-score 1: GWAS associations
    gwas_score = _compute_gwas_subscore(opentargets_data, disease_context)
    sub_scores.append(SubScore(name="gwas_associations", value=gwas_score, max_value=5))

    # Sub-score 2: Overall association score from OpenTargets
    assoc_score = _compute_association_subscore(opentargets_data, disease_context)
    sub_scores.append(SubScore(name="genetic_association_score", value=assoc_score, max_value=4))

    # ... etc for all sub-scores

    total = sum(s.value for s in sub_scores)
    return DimensionScore(
        name="genetic_evidence",
        score=total,
        max_score=15,
        sub_scores=sub_scores,
        data_coverage=_compute_coverage(opentargets_data),
    )
```

### Pattern 2: Deterministic Composite Score with Configurable Weights

**What:** The composite score is a weighted sum of dimension scores, normalized to 0-100. Weights are user-configurable but always normalized to sum to 1.0. The formula is transparent and published.

**When to use:** Always. The composite score formula must be deterministic and reproducible -- given the same evidence and weights, the same score must result every time.

**Example:**

```python
from src.scoring.models import CompositeScore, WeightConfig

def compute_composite(
    dimension_scores: list[DimensionScore],
    weights: WeightConfig,
) -> CompositeScore:
    """Compute weighted composite score (0-100).

    Formula: composite = sum(dim_score_normalized * weight_i) * 100
    where dim_score_normalized = dim_score / dim_max_score
    and weights are normalized to sum to 1.0
    """
    normalized_weights = weights.normalized()  # Always sums to 1.0

    weighted_sum = 0.0
    for dim in dimension_scores:
        dim_normalized = dim.score / dim.max_score if dim.max_score > 0 else 0.0
        weight = normalized_weights[dim.name]
        weighted_sum += dim_normalized * weight

    composite = round(weighted_sum * 100, 1)

    return CompositeScore(
        score=composite,
        dimension_scores=dimension_scores,
        weights=weights,
        formula_version="v1.0",
    )
```

### Pattern 3: Decision Threshold with Dimension Minimums

**What:** The verdict (GO/CONDITIONAL/NO-GO) is determined by the composite score AND dimension minimum checks. Even if composite >= 75, a dimension below its minimum forces CONDITIONAL.

**When to use:** After computing the composite score. The threshold logic is a separate concern from the score computation.

**Example:**

```python
from src.scoring.models import Verdict, VerdictLevel

# Default dimension minimums (as fraction of max)
DIMENSION_MINIMUMS = {
    "genetic_evidence": 0.20,       # At least 3/15 points
    "safety_selectivity": 0.20,     # At least 3/15 points
    "druggability": 0.13,           # At least 2/15 points
}

def determine_verdict(
    composite: CompositeScore,
    minimums: dict[str, float] | None = None,
) -> Verdict:
    """Apply GO/CONDITIONAL/NO-GO thresholds with dimension minimum overrides."""
    mins = minimums or DIMENSION_MINIMUMS

    # Check dimension minimums
    violations = []
    for dim in composite.dimension_scores:
        min_frac = mins.get(dim.name)
        if min_frac is not None:
            actual_frac = dim.score / dim.max_score if dim.max_score > 0 else 0.0
            if actual_frac < min_frac:
                violations.append(dim.name)

    # Apply thresholds
    score = composite.score
    if score >= 75 and not violations:
        level = VerdictLevel.GO
    elif score >= 50 or (score >= 75 and violations):
        level = VerdictLevel.CONDITIONAL
    else:
        level = VerdictLevel.NO_GO

    return Verdict(
        level=level,
        score=score,
        dimension_violations=violations,
        forced_conditional=bool(violations and score >= 75),
    )
```

### Pattern 4: Evidence-to-Score Mapping (Sub-Score Extractors)

**What:** Each sub-score has a dedicated extractor function that maps raw evidence data fields to a numeric score using defined rules. These are the "published formulas" referenced in REQ-401.

**When to use:** Inside each dimension calculator. The extractors are the lowest-level functions and should be individually testable.

**Example mapping for genetic_evidence sub-scores:**

```python
def _compute_gwas_subscore(opentargets_data: dict | None, disease_context: str | None) -> float:
    """GWAS sub-score: 0-5 points.

    Rules:
    - 0 points: No associations or no data
    - 1 point: Any association exists (overall_score > 0)
    - 2 points: Disease-relevant association (context_relevant=True)
    - 3 points: Strong association (overall_score >= 0.5)
    - 4 points: Very strong association (overall_score >= 0.7)
    - 5 points: Top-tier association (overall_score >= 0.9)
    """
    if not opentargets_data:
        return 0.0

    associations = opentargets_data.get("associations", [])
    if not associations:
        return 0.0

    # Find best relevant association
    best_score = 0.0
    has_context_relevant = False
    for assoc in associations:
        score = assoc.get("overall_score", 0.0)
        if disease_context and assoc.get("context_relevant"):
            has_context_relevant = True
            best_score = max(best_score, score)
        else:
            best_score = max(best_score, score)

    if best_score >= 0.9:
        return 5.0
    elif best_score >= 0.7:
        return 4.0
    elif best_score >= 0.5:
        return 3.0
    elif has_context_relevant:
        return 2.0
    elif best_score > 0:
        return 1.0
    return 0.0
```

### Pattern 5: Radar Chart Data Generation for Comparative View

**What:** Generate Plotly-compatible data structures for radar charts comparing multiple targets side-by-side. Each target is a trace on the same polar plot.

**When to use:** When 3-20 targets need comparison (REQ-405).

**Example:**

```python
import plotly.graph_objects as go

def build_comparative_radar(
    scorecards: list[ScorecardResult],
) -> go.Figure:
    """Build overlaid radar chart for multiple targets.

    Each target becomes a Scatterpolar trace with dimension scores
    normalized to 0-1 for comparable visualization.
    """
    dimension_names = [
        "Genetic Evidence", "Expression Biology", "Druggability",
        "Safety/Selectivity", "Competitive Landscape",
        "Clinical/Translational", "Literature Consensus",
    ]

    fig = go.Figure()

    for sc in scorecards:
        # Normalize each dimension to 0-1
        values = [
            dim.score / dim.max_score if dim.max_score > 0 else 0
            for dim in sc.composite.dimension_scores
        ]
        # Close the polygon
        values.append(values[0])
        names = dimension_names + [dimension_names[0]]

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=names,
            fill='toself',
            name=sc.gene_symbol,
            opacity=0.6,
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        title="Comparative Target Profile",
    )
    return fig
```

### Anti-Patterns to Avoid

- **LLM computes scores:** The LLM must NEVER be in the scoring calculation loop. It explains scores (downstream in Phase 6/7) but does not compute them. Scoring must be deterministic -- same inputs, same outputs, always. LLM outputs are inherently non-deterministic.
- **Scores without data coverage indicators:** A score of 0 should be distinguishable from "no data available." Every `DimensionScore` must include a `data_coverage` field (0.0-1.0) indicating what fraction of data sources contributed. A score of 4/15 with full data is meaningful; 4/15 with only 1 of 4 sources responding is not.
- **Hardcoded weights without normalization:** Weights must always be normalized to sum to 1.0. If a user changes one weight, all others must re-normalize. Never assume they sum to 1.0.
- **Monolithic scorer:** Do not put all 24 sub-score calculations in a single function. Each sub-score extractor should be a separate, testable function. Each dimension calculator composes its sub-scores.
- **Floating-point comparison for thresholds:** Use `>=` with well-defined bounds (75.0, 50.0), not approximate comparisons. Round composite scores to 1 decimal place to avoid floating-point edge cases like 74.99999997.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Radar/spider charts | Custom SVG/Canvas rendering | `plotly.graph_objects.Scatterpolar` | Interactive, hoverable, exportable. Plotly handles polygon fill, axis labeling, legend, and responsive sizing. Building this from scratch would take days. |
| Score data models with validation | Plain dicts or unvalidated dataclasses | Pydantic v2 `BaseModel` with `@field_validator` | Score bounds (0-max), weight normalization (sum to 1.0), and threshold enforcement are validation concerns. Pydantic catches invalid scores at construction time, not at query time. |
| Weight normalization | Manual division in every caller | `WeightConfig.normalized()` method | Centralized normalization guarantees weights always sum to 1.0 regardless of how the user configures them. Single source of truth. |
| JSON serialization for audit | Custom `to_dict()` methods | Pydantic `model_dump(mode='json')` | Pydantic v2 handles datetime, enum, and nested model serialization correctly. Deterministic with `sort_keys=True` in `json.dumps`. |

**Key insight:** The scoring framework is essentially a structured data transformation pipeline: raw evidence dicts -> sub-scores -> dimension scores -> composite -> verdict. Every step is a pure function. The only complexity is getting the 24 sub-score extraction rules right -- and that is a domain knowledge problem, not a software engineering problem.

## Common Pitfalls

### Pitfall 1: Arbitrary Weights Without Retrovalidation

**What goes wrong:** Dimension weights are chosen "because they feel right" rather than validated against known outcomes. The framework might rank MELK above EGFR for NSCLC, making the entire scoring system worse than random.
**Why it happens:** No validation dataset exists during initial development. Weight calibration is deferred until "later."
**How to avoid:** Build the retrovalidation harness as part of Phase 5, not Phase 8. Define 3-5 known target-disease pairs with expected outcomes (EGFR/NSCLC=GO, MELK/breast cancer=NO-GO) and run them through the scorer during development. If EGFR does not score >= 75, adjust sub-score extraction rules. This is the pending todo from STATE.md: "Collect 10-20 known target-disease pairs for retrovalidation."
**Warning signs:** All targets score within a narrow band (60-70) regardless of evidence strength. Known good targets score lower than known bad ones.

### Pitfall 2: Missing Data Treated as Zero Score

**What goes wrong:** When an evidence source returns no data (API failure, gene not found), the dimension score defaults to 0, dragging down the composite. A target with 4 excellent dimensions and 3 missing dimensions scores lower than a mediocre target with all 7 dimensions present.
**Why it happens:** The natural default for "no data" is zero. But zero means "evidence says this is bad," not "we don't know."
**How to avoid:** Track `data_coverage` per dimension (0.0-1.0). When coverage is below a threshold (e.g., < 0.3), either (a) exclude the dimension from the weighted sum and re-normalize remaining weights, or (b) assign a neutral score (e.g., 50% of max) with a visible "insufficient data" flag. The composite score should clearly indicate how many dimensions had adequate data.
**Warning signs:** Targets with fewer evidence sources consistently score lower than targets with more sources, regardless of evidence quality.

### Pitfall 3: Weight Adjustment Without Re-Normalization

**What goes wrong:** User changes "genetic_evidence" weight from 15 to 25 via HITL-009 slider. Other weights remain unchanged. Total weight is now 110, not 100. Composite score exceeds 100 or behaves unpredictably.
**Why it happens:** UI sliders set absolute values. Developer forgets to normalize.
**How to avoid:** All weight operations go through `WeightConfig.normalized()` which always returns weights summing to 1.0. The raw user-facing values (e.g., 15, 15, 15, 15, 15, 15, 10) are divided by their sum to get proportional weights. Display both raw weights and effective percentages in the UI.
**Warning signs:** Composite scores change when weights are modified but don't match the expected direction/magnitude.

### Pitfall 4: Contradictory Evidence Penalty Applied Incorrectly

**What goes wrong:** The -4 point penalty for contradictory evidence (REQ-406) is applied to the composite score instead of the literature_consensus dimension score, allowing it to push the composite below zero or cause inconsistencies when weights are re-adjusted.
**Why it happens:** The penalty is conceptually "punitive" so it feels like a global modifier. But it belongs to a specific dimension.
**How to avoid:** Apply the penalty within the `literature_consensus` dimension calculator. The `score_literature_consensus()` function computes a base score (0-10), then subtracts the contradiction penalty (0-4), clamped to a minimum of 0. The penalty and its magnitude are visible in the sub-score breakdown. The contradiction detection itself comes from the ReasoningEngine's CONTRADICTION mode output.
**Warning signs:** Literature dimension scores go negative. Penalty magnitude seems arbitrary.

### Pitfall 5: Verdict Logic Does Not Account for Dimension Minimums Correctly

**What goes wrong:** A target scores 78/100 overall (GO) but has 0/15 in safety_selectivity because no safety data was available. The target gets a GO recommendation despite having zero safety assessment. A pharma VP would reject this immediately.
**Why it happens:** The composite score masks individual dimension weaknesses. Weighted average hides outliers.
**How to avoid:** Define explicit dimension minimums (as fraction of max score). If any critical dimension falls below its minimum, the verdict is forced to CONDITIONAL regardless of composite score. The forced CONDITIONAL must be visually distinct: "GO by score, CONDITIONAL due to insufficient safety data" with a clear call-to-action.
**Warning signs:** Targets with missing safety or genetic data receive GO recommendations.

### Pitfall 6: Non-Deterministic Scoring from Floating Point Accumulation

**What goes wrong:** Scoring the same target twice produces slightly different results (74.9999 vs 75.0001), causing the verdict to flip between CONDITIONAL and GO depending on execution order.
**Why it happens:** Floating-point arithmetic accumulation errors across 24 sub-scores.
**How to avoid:** Round each sub-score to 2 decimal places at computation time. Round the composite to 1 decimal place. Use `round()` consistently, not `math.floor` or truncation. Define threshold comparisons with explicit rounding: `round(composite, 1) >= 75.0`.
**Warning signs:** Identical inputs produce different verdicts in rare cases.

## Code Examples

### Complete Pydantic Models for Scoring

```python
# Source: Project architecture (ARCHITECTURE.md scorecard section)
from enum import Enum
from pydantic import BaseModel, Field, field_validator

class VerdictLevel(str, Enum):
    GO = "GO"
    CONDITIONAL = "CONDITIONAL"
    NO_GO = "NO-GO"

class SubScore(BaseModel):
    """Individual sub-score within a dimension."""
    name: str
    value: float = Field(ge=0)
    max_value: float = Field(gt=0)
    description: str = ""
    data_source: str = ""  # Which evidence source contributed

    @property
    def normalized(self) -> float:
        return round(self.value / self.max_value, 3) if self.max_value > 0 else 0.0

class DimensionScore(BaseModel):
    """Score for one of the 7 scoring dimensions."""
    name: str
    score: float = Field(ge=0)
    max_score: float = Field(gt=0)
    sub_scores: list[SubScore] = Field(default_factory=list)
    data_coverage: float = Field(ge=0.0, le=1.0, default=0.0)

    @field_validator('score')
    @classmethod
    def score_within_max(cls, v, info):
        max_s = info.data.get('max_score')
        if max_s is not None and v > max_s:
            raise ValueError(f'score {v} exceeds max_score {max_s}')
        return round(v, 2)

class WeightConfig(BaseModel):
    """User-configurable dimension weights."""
    genetic_evidence: float = 15.0
    expression_biology: float = 15.0
    druggability: float = 15.0
    safety_selectivity: float = 15.0
    competitive_landscape: float = 15.0
    clinical_translational: float = 15.0
    literature_consensus: float = 10.0

    def normalized(self) -> dict[str, float]:
        """Return weights normalized to sum to 1.0."""
        raw = {
            "genetic_evidence": self.genetic_evidence,
            "expression_biology": self.expression_biology,
            "druggability": self.druggability,
            "safety_selectivity": self.safety_selectivity,
            "competitive_landscape": self.competitive_landscape,
            "clinical_translational": self.clinical_translational,
            "literature_consensus": self.literature_consensus,
        }
        total = sum(raw.values())
        if total == 0:
            return {k: 1.0 / len(raw) for k in raw}
        return {k: v / total for k, v in raw.items()}

class CompositeScore(BaseModel):
    """Weighted composite score across all dimensions."""
    score: float = Field(ge=0, le=100)
    dimension_scores: list[DimensionScore]
    weights: WeightConfig
    formula_version: str = "v1.0"

class Verdict(BaseModel):
    """GO/CONDITIONAL/NO-GO decision with rationale."""
    level: VerdictLevel
    score: float
    dimension_violations: list[str] = Field(default_factory=list)
    forced_conditional: bool = False
    rationale: str = ""

class ScorecardResult(BaseModel):
    """Complete scorecard for a single target gene."""
    gene_symbol: str
    disease_context: str | None = None
    composite: CompositeScore
    verdict: Verdict
    evidence_hash: str = ""  # SHA256 of input evidence for reproducibility
    scored_at: str = ""  # ISO 8601 timestamp
```

### Dimension-to-Evidence Source Mapping

```python
# Source: Project evidence sources (Phase 3) and requirements (REQ-402)

# Each dimension maps to specific evidence sources from AggregatedEvidence
DIMENSION_EVIDENCE_MAP = {
    "genetic_evidence": {
        "primary": "opentargets",  # associations, datatypeScores
        "sub_scores": [
            "gwas_associations",        # OT associations with disease context (0-5)
            "genetic_association_score", # OT overall_score for relevant disease (0-4)
            "causal_evidence",          # Mendelian/functional genomics datatypes (0-3)
            "functional_genomics",      # OT functional genomics datatype score (0-3)
        ],
    },
    "expression_biology": {
        "primary": "uniprot",     # subcellular_location, tissue expression
        "secondary": "opentargets",  # expression data if available
        "sub_scores": [
            "tissue_expression",        # Expression in disease-relevant tissue (0-4)
            "cell_type_specificity",    # From omics pipeline tau score (0-4)
            "subcellular_location",     # UniProt location (surface=high, nuclear=lower) (0-4)
            "expression_disease_link",  # Differential expression in disease (0-3)
        ],
    },
    "druggability": {
        "primary": "dgidb",       # gene_categories, interactions
        "secondary": "chembl",    # activities, mechanisms, pchembl values
        "tertiary": "opentargets",  # tractability data
        "sub_scores": [
            "druggability_class",       # DGIdb gene categories (0-4)
            "existing_compounds",       # ChEMBL activity count + quality (0-4)
            "tractability_modality",    # OT tractability labels (0-4)
            "binding_pocket",           # ChEMBL max_pchembl, mechanism data (0-3)
        ],
    },
    "safety_selectivity": {
        "primary": "uniprot",     # expression breadth, domains
        "secondary": "chembl",    # known adverse events
        "sub_scores": [
            "expression_breadth",       # UniProt: broad expression = risk (0-4, inverted)
            "known_safety_signals",     # ChEMBL mechanisms, known AEs (0-4)
            "essential_gene_risk",      # Essentiality indicators (0-4)
            "selectivity_potential",    # UniProt domains, paralogs (0-3)
        ],
    },
    "competitive_landscape": {
        "primary": "clinicaltrials",  # active trials, phases
        "secondary": "opentargets",   # known drugs
        "sub_scores": [
            "active_trials_count",      # ClinicalTrials active/recruiting (0-4)
            "clinical_phase_max",       # Highest phase reached (0-4)
            "competitor_density",       # Number of unique sponsors (0-4)
            "differentiation_potential",# Gap analysis from trials (0-3)
        ],
    },
    "clinical_translational": {
        "primary": "clinicaltrials",  # trial outcomes
        "secondary": "opentargets",   # known drugs with phases
        "sub_scores": [
            "clinical_precedent",       # Any approved drug for target (0-5)
            "biomarker_availability",   # Measurable endpoints from trials (0-4)
            "translational_evidence",   # Phase transitions success (0-3)
            "patient_selection",        # Trial design specificity (0-3)
        ],
    },
    "literature_consensus": {
        "primary": "pubmed",      # papers, publication count, AI summary
        "reasoning": "contradiction",  # ReasoningMode.CONTRADICTION output
        "sub_scores": [
            "publication_volume",       # Number of recent papers (0-4)
            "review_articles",          # Review/meta-analysis presence (0-3)
            "publication_trend",        # Year-over-year growth (0-3)
        ],
        "penalty": "contradictory_evidence",  # Up to -4 points (REQ-406)
    },
}
```

### Contradictory Evidence Penalty (REQ-406)

```python
# Source: Requirements REQ-406 and reasoning/models.py CONTRADICTION mode

def score_literature_consensus(
    pubmed_data: dict | None,
    contradiction_result: "ReasoningResult | None" = None,
) -> DimensionScore:
    """Score literature consensus dimension (max 10 points, penalty up to -4).

    Base score from publication evidence (0-10), then subtract
    contradictory evidence penalty (0-4) based on the ReasoningEngine's
    CONTRADICTION mode output.
    """
    # Compute base sub-scores (0-10 total)
    pub_volume = _score_publication_volume(pubmed_data)    # 0-4
    reviews = _score_review_articles(pubmed_data)          # 0-3
    trend = _score_publication_trend(pubmed_data)           # 0-3
    base_total = pub_volume.value + reviews.value + trend.value

    # Compute contradiction penalty (REQ-406)
    penalty = 0.0
    if contradiction_result and contradiction_result.claims:
        # Count high-confidence contradiction claims
        strong_contradictions = [
            c for c in contradiction_result.claims
            if c.confidence >= 0.7
        ]
        # Scale: 1 contradiction = -1pt, 2 = -2pt, 3 = -3pt, 4+ = -4pt
        penalty = min(len(strong_contradictions), 4)

    contradiction_subscore = SubScore(
        name="contradictory_evidence",
        value=penalty,
        max_value=4,
        description=f"{len(strong_contradictions) if contradiction_result else 0} contradictions found",
    )

    # Final score: base minus penalty, clamped to 0
    final_score = max(0.0, base_total - penalty)

    return DimensionScore(
        name="literature_consensus",
        score=round(final_score, 2),
        max_score=10,
        sub_scores=[pub_volume, reviews, trend, contradiction_subscore],
        data_coverage=_pubmed_coverage(pubmed_data),
    )
```

### Comparative Scorecard for Multiple Targets (REQ-405)

```python
# Source: Requirements REQ-405, plotly.com/python/radar-chart/

class ComparativeScorecard(BaseModel):
    """Side-by-side comparison of 3-20 scored targets."""
    scorecards: list[ScorecardResult]
    ranking: list[str]  # Gene symbols sorted by composite score descending

    @field_validator('scorecards')
    @classmethod
    def validate_count(cls, v):
        if len(v) < 1:
            raise ValueError('Need at least 1 scorecard')
        if len(v) > 20:
            raise ValueError('Maximum 20 targets for comparison')
        return v

    @classmethod
    def from_scorecards(cls, scorecards: list[ScorecardResult]) -> "ComparativeScorecard":
        ranking = sorted(scorecards, key=lambda s: s.composite.score, reverse=True)
        return cls(
            scorecards=scorecards,
            ranking=[s.gene_symbol for s in ranking],
        )
```

## GOT-IT Framework Alignment

### What GOT-IT Actually Is

The GOT-IT framework ("Guidelines On Target Assessment for Innovative Therapeutics") was published in Nature Reviews Drug Discovery (2021, volume 20, pages 64-81) by Emmerich et al. It defines **5 assessment blocks** with **40 Critical Path Questions** and a **go/no-go decision process** -- but notably it does NOT define a numerical scoring system. GOT-IT provides qualitative assessment guidelines, not quantitative scores.

**Assessment Blocks:**
1. AB1: Target-Disease Linkage (causal relationships, not just associations)
2. AB2: Safety Aspects (on-target and off-target toxicity)
3. AB3: Microbial Targets (not relevant for human targets)
4. AB4: Strategic Issues (IP, unmet need, competitive landscape, commercial viability)
5. AB5: Technical Feasibility (druggability, assayability, tool compounds, biomarkers)

### How Our Framework Adapts GOT-IT

Our 7-dimension framework is **inspired by** GOT-IT but adapted with quantitative scoring. The mapping:

| GOT-IT Block | Our Dimension(s) | Adaptation |
|--------------|-------------------|------------|
| AB1: Target-Disease Linkage | genetic_evidence, expression_biology | Split into genetic (GWAS, Mendelian) and expression (tissue/cell specificity) |
| AB2: Safety | safety_selectivity | Quantified using expression breadth, essential gene status, known AEs |
| AB3: Microbial | N/A | Not applicable for human therapeutic targets |
| AB4: Strategic | competitive_landscape, clinical_translational | Split into competitive (market) and clinical (precedent) dimensions |
| AB5: Feasibility | druggability | Quantified using DGIdb categories, ChEMBL bioactivity, OT tractability |
| (Extended) | literature_consensus | Added as evidence quality meta-dimension with contradiction penalty |

This is an honest adaptation, not a 1:1 implementation. GOT-IT is qualitative and question-based; our framework adds quantitative scoring on top of the same assessment philosophy.

### Open Targets Comparison

Open Targets Platform uses a 4-section target prioritization view: **Precedence, Tractability, Doability, Safety**. Their association scoring uses a **harmonic sum** methodology (not weighted average) where evidence pieces are sorted by score and divided by position-squared, then normalized.

Our framework differs deliberately:
- **Weighted average** (not harmonic sum) for transparency -- pharma VPs understand "genetic evidence counts for 15%"
- **7 dimensions** (not 4 sections) for finer-grained assessment
- **24 sub-scores** for drill-down transparency -- every number traceable to a specific evidence data point
- **Configurable weights** per therapeutic area and user preference
- **Decision thresholds** with dimension minimums -- Open Targets does not make GO/NO-GO recommendations

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual scoring by analysts | Quantitative frameworks (OT, GOT-IT) | 2020-2021 | Reproducible, transparent assessments |
| Single overall score | Multi-dimension with sub-scores | 2020+ | Identifies specific weaknesses, not just overall ranking |
| Black-box AI scoring (PandaOmics) | Transparent dimension-level scoring | 2023+ | Pharma VPs demand explainability |
| Fixed weights for all diseases | Therapeutic area-specific weight presets | 2024+ | Oncology weights genetics higher, rare disease weights Mendelian |
| Score only | Score + narrative per dimension | 2024+ | Context for non-expert decision-makers |

**Deprecated/outdated:**
- Simple additive scoring without normalization: replaced by weighted average with normalized dimensions
- Single threshold (GO/NO-GO binary): replaced by three-tier system with CONDITIONAL band
- Score without provenance: replaced by evidence-hashed, auditable scoring with formula versioning

## Open Questions

1. **GOT-IT Dimension Weights Calibration**
   - What we know: Default weights are 15/15/15/15/15/15/10 (from REQ-402). This gives equal weight to 6 dimensions and slightly less to literature_consensus.
   - What's unclear: Whether these defaults produce reasonable rankings for known targets (EGFR, MELK). The pending todo says "Verify GOT-IT framework dimensions against Nature Reviews paper" but GOT-IT does not specify numeric weights -- it is qualitative.
   - Recommendation: Accept the REQ-402 defaults as the starting configuration. Build retrovalidation test cases (EGFR/NSCLC=GO, MELK/BC=NO-GO) in the test suite and adjust sub-score extraction rules if results are unreasonable. Weight calibration is a Phase 8 validation concern, not a Phase 5 blocking issue.

2. **Dimension Minimum Thresholds**
   - What we know: REQ-403 says "dimension minimums can force a CONDITIONAL" but does not specify which dimensions have minimums or what the minimum values are.
   - What's unclear: Should all 7 dimensions have minimums, or only critical ones (safety, genetic)? What fraction of max_score triggers the minimum?
   - Recommendation: Default minimums for 3 critical dimensions only: genetic_evidence (20% = 3/15), safety_selectivity (20% = 3/15), druggability (13% = 2/15). Other dimensions do not have minimums. Make minimums configurable per project. This avoids false CONDITIONAL verdicts from less critical dimensions while catching truly dangerous gaps.

3. **How to Handle Missing Evidence Sources in Scoring**
   - What we know: `EvidenceResult.confidence == 0.0` means the source failed or returned no data. `is_fallback=True` means stale cache was used.
   - What's unclear: Should a missing source score as 0, be excluded from the weighted average, or score as a neutral midpoint?
   - Recommendation: Track `data_coverage` per dimension. If a dimension has `data_coverage < 0.3` (less than 30% of expected data sources contributed), flag it as "insufficient data" and assign a neutral score (50% of max). Display this prominently in the scorecard. This prevents missing data from being conflated with negative evidence.

4. **24 Sub-Score Definitions**
   - What we know: REQ-401 specifies 24 sub-scores but does not enumerate them. The dimension-to-evidence mapping above proposes 24 sub-scores (4 per dimension for 6 dimensions, 3 + penalty for literature).
   - What's unclear: Whether these specific 24 sub-scores are the right ones, or if the mapping should be different.
   - Recommendation: Use the 24 sub-scores defined in the dimension-evidence mapping above. Each is traceable to a specific evidence field from Phase 3 sources. Validate during retrovalidation (Phase 8) and adjust as needed.

5. **Expression Biology from Omics Data**
   - What we know: The omics pipeline (Phase 2) produces cell-type annotations, differential expression, and expression profiles. The evidence aggregator (Phase 3) does not include omics data -- it fetches external evidence only.
   - What's unclear: How omics pipeline results feed into the expression_biology dimension. Does the scoring framework need to read AnnData files or the pipeline's output?
   - Recommendation: The `expression_biology` dimension should accept an optional `omics_scores` parameter with pre-computed values (tau score, fold change, DE p-values) extracted from the pipeline results. If omics data is unavailable (no upload), fall back to UniProt expression annotations. This keeps the scoring module decoupled from scanpy/AnnData.

## Sources

### Primary (HIGH confidence)
- Open Targets Platform documentation: [Target Prioritisation](https://platform-docs.opentargets.org/web-interface/target-prioritisation) - Four-section framework (Precedence, Tractability, Doability, Safety), property-level scoring
- Open Targets Platform documentation: [Association Scoring](https://platform-docs.opentargets.org/associations) - Harmonic sum methodology, data source weights, normalization
- Plotly documentation: [Radar Charts](https://plotly.com/python/radar-chart/) - `go.Scatterpolar` with `fill='toself'` for multi-trace overlays
- Existing codebase: `src/evidence/models.py` (AggregatedEvidence, EvidenceResult), `src/reasoning/models.py` (ReasoningResult, Claim) - Input data structures
- Project requirements: `.planning/REQUIREMENTS.md` REQ-401 through REQ-406 - Scoring framework specifications
- Project architecture: `.planning/research/ARCHITECTURE.md` scorecard section - Module structure guidance

### Secondary (MEDIUM confidence)
- GOT-IT paper: [Nature Reviews Drug Discovery (2021)](https://www.nature.com/articles/s41573-020-0087-3) - 5 assessment blocks (AB1-AB5), 40 CPQs, qualitative decision framework. Confirmed via PMC article that GOT-IT is question-based, not score-based.
- [GOT-IT PMC Article](https://pmc.ncbi.nlm.nih.gov/articles/PMC7667479/) - Full text confirming assessment blocks and methodology
- [Plotly vs Matplotlib Radar Charts](https://www.statology.org/how-to-create-radar-charts-in-python-plotly-vs-matplotlib-comparison/) - Comparison confirming Plotly is superior for interactive multi-trace polar charts

### Tertiary (LOW confidence)
- [DrugnomeAI](https://www.nature.com/articles/s42003-022-04245-4) - Machine learning druggability prediction. Interesting approach but too complex for our deterministic framework. Could be future enhancement.
- [Genetic Priority Score](https://www.nature.com/articles/s41467-025-63762-y) - Genetic evidence integration for side effect prediction. Confirms multi-line genetic evidence integration approach.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in project, well-documented APIs, verified with official docs
- Architecture: HIGH - Pure computation pattern is well-understood; Pydantic v2 models are battle-tested in Phase 4
- Scoring methodology: MEDIUM - Sub-score extraction rules are domain-specific and need retrovalidation; GOT-IT alignment is an adaptation, not a direct implementation
- Pitfalls: HIGH - Weight calibration, missing data handling, and floating-point issues are well-known scoring system problems with documented solutions
- Visualization: HIGH - Plotly Scatterpolar is mature, well-documented, and already used in the project

**Research date:** 2026-05-12
**Valid until:** 2026-06-12 (stable domain -- scoring frameworks don't change rapidly)
