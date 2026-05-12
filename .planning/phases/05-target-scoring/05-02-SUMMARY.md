---
phase: 05-target-scoring
plan: 02
subsystem: scoring
tags: [scoring-framework, verdict, composite, radar-chart, plotly, comparative, sha256]

# Dependency graph
requires:
  - phase: 05-target-scoring
    plan: 01
    provides: "DimensionScore, WeightConfig, CompositeScore models; 7 dimension calculators; DEFAULT_WEIGHTS; DIMENSION_MINIMUMS"
  - phase: 03-evidence-integration
    provides: "AggregatedEvidence with source-specific data dicts"
  - phase: 04-ai-reasoning-engine
    provides: "ReasoningResult with Claim objects for contradiction penalty"
provides:
  - "ScoringFramework.score_target() orchestrator: AggregatedEvidence -> ScorecardResult pipeline"
  - "compute_composite() weighted sum with low-coverage neutral substitution"
  - "determine_verdict() with GO/CONDITIONAL/NO-GO thresholds and forced-CONDITIONAL on dimension minimum violations"
  - "score_multiple_targets() comparative assessment for 1-20 targets with ranking"
  - "build_comparative_radar() Plotly Scatterpolar radar chart with normalized dimensions"
  - "build_single_radar() single-target radar with verdict-based coloring"
  - "SHA256 evidence hash for reproducibility verification"
  - "Complete public API with 22 exports from src/scoring/__init__.py"
affects: [06-deliverables, 07-ui, 08-validation]

# Tech tracking
tech-stack:
  added: [plotly]
  patterns:
    - "Orchestrator pattern: ScoringFramework wires dimension calculators -> composite -> verdict -> ScorecardResult"
    - "Evidence hash: SHA256 of JSON-serialized evidence data (sort_keys=True) for deterministic reproducibility"
    - "Low-coverage neutral substitution: dimensions with data_coverage < 0.3 get neutral score (0.5) to prevent missing data conflation"
    - "Forced CONDITIONAL: composite >= 75 but dimension minimum violation overrides GO verdict"

key-files:
  created:
    - src/scoring/verdict.py
    - src/scoring/framework.py
    - src/scoring/comparative.py
    - tests/test_scoring/test_framework.py
    - tests/test_scoring/test_comparative.py
  modified:
    - src/scoring/__init__.py

key-decisions:
  - "Low data coverage threshold at 0.3: dimensions below this get neutral 0.5 score to prevent conflating missing data with negative evidence"
  - "Evidence hash computed over confidence + data (not full EvidenceResult) for deterministic fingerprinting"
  - "Plotly Scatterpolar with polygon closure (n+1 points) for radar chart visualization"
  - "Verdict-based coloring in single radar: green (GO), orange (CONDITIONAL), red (NO-GO)"

patterns-established:
  - "Framework orchestrator: ScoringFramework is the single entry point for evidence-to-verdict pipeline"
  - "Convenience wrappers: module-level score_target() delegates to ScoringFramework for simple usage"
  - "ComparativeScorecard.from_scorecards() factory handles ranking with sorted-by-composite-desc"

# Metrics
duration: 9min
completed: 2026-05-12
---

# Phase 5 Plan 2: Scoring Framework & Comparative Summary

**Scoring framework orchestrator with GO/CONDITIONAL/NO-GO verdict logic, forced-CONDITIONAL on dimension minimums, multi-target comparison with Plotly radar charts, and SHA256 evidence hashing -- all 60 scoring tests passing**

## Performance

- **Duration:** 9 min
- **Started:** 2026-05-12T05:00:49Z
- **Completed:** 2026-05-12T05:10:28Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- ScoringFramework.score_target() pipeline: AggregatedEvidence -> 7 dimensions -> weighted composite -> GO/CONDITIONAL/NO-GO verdict with evidence hash
- Verdict logic with threshold boundaries (75/50) and forced-CONDITIONAL when dimension minimums are violated even with composite >= 75
- Low data coverage guard: dimensions with coverage < 0.3 receive neutral 0.5 score to prevent missing data from falsely tanking the composite
- Multi-target comparison with ranking and Plotly Scatterpolar radar charts with normalized values and closed polygons

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: Scoring framework orchestrator and verdict logic**
   - `2d33913` (test) - RED: 19 failing tests for composite, verdict, and framework
   - `947b726` (feat) - GREEN: verdict.py + framework.py pass all 19 tests
2. **Task 2: Comparative scorecard, radar charts, and public API**
   - `6d9683c` (test) - RED: 10 failing tests for comparative and radar
   - `098d171` (feat) - GREEN: comparative.py + __init__.py pass all 10 tests

## Files Created/Modified
- `src/scoring/verdict.py` - compute_composite() and determine_verdict() pure functions
- `src/scoring/framework.py` - ScoringFramework class orchestrating 7 dimensions + composite + verdict
- `src/scoring/comparative.py` - score_multiple_targets(), build_comparative_radar(), build_single_radar()
- `src/scoring/__init__.py` - Complete public API with 22 exports (models, constants, calculators, pipeline, comparative)
- `tests/test_scoring/test_framework.py` - 19 tests: 5 composite, 7 verdict, 7 framework orchestrator
- `tests/test_scoring/test_comparative.py` - 10 tests: 4 multi-target scoring, 5 radar chart, 1 single radar

## Decisions Made
- Low data coverage threshold set at 0.3 (30%) -- dimensions below this receive neutral 0.5 normalized score instead of their computed value, preventing missing data from being conflated with negative evidence (addresses research pitfall #2)
- Evidence hash includes confidence and data per source but not metadata like fetched_at, ensuring deterministic hashing regardless of timing
- Plotly Scatterpolar traces close the polygon by appending the first dimension value, producing visually correct radar shapes
- Single radar uses verdict-based fill colors (green GO, orange CONDITIONAL, red NO-GO) for instant visual assessment

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Mock evidence data structure mismatch in test fixtures**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Test mock `_make_mock_evidence()` used data structures that didn't match sub-score extractor expectations (e.g., `tissue_expression` as list instead of dict with `tissues` key, `subcellular_location` as list instead of string, PubMed using `total_count` instead of `paper_count`)
- **Fix:** Rebuilt all 6 mock evidence data dicts to match the actual sub-score extractor API from `sub_scores.py`
- **Files modified:** tests/test_scoring/test_framework.py
- **Verification:** All 19 tests pass with corrected mock data
- **Committed in:** 947b726 (Task 1 GREEN commit)

**2. [Rule 3 - Blocking] Installed missing plotly dependency**
- **Found during:** Task 2 (RED phase)
- **Issue:** `plotly` not installed, causing `ModuleNotFoundError` in tests
- **Fix:** `pip install plotly` (plotly 6.7.0 installed)
- **Files modified:** None (runtime dependency only)
- **Verification:** `import plotly.graph_objects as go` succeeds
- **Committed in:** N/A (not a code change)

---

**Total deviations:** 2 auto-fixed (1 bug fix, 1 blocking dependency)
**Impact on plan:** Minor fixes for test data accuracy and missing dependency. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Complete scoring pipeline ready: evidence in -> ScorecardResult out with transparent 7-dimension assessment
- All scoring models, calculators, framework, and comparative modules are fully tested (60 tests)
- Public API exports 22 symbols covering models, constants, calculators, pipeline, and visualization
- Ready for Phase 6 (Deliverables) to generate reports from ScorecardResult
- Ready for Phase 7 (UI) to display radar charts and weight sliders using ScoringFramework

## Self-Check: PASSED

- All 6 created/modified files verified on disk
- All 4 task commits (2d33913, 947b726, 6d9683c, 098d171) verified in git log
- 60 scoring tests passing, 149 total tests with no regressions

---
*Phase: 05-target-scoring*
*Completed: 2026-05-12*
