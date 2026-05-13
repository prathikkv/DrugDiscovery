---
phase: 07-ui-integration
plan: 04
subsystem: ui
tags: [showcase-data, pharma-scenarios, json, integration-tests, pytest]

# Dependency graph
requires:
  - phase: 07-ui-integration
    provides: "SHOWCASE_SCENARIOS dict, load_scenario() loader, styles module, hitl_gate"
  - phase: 05-target-scoring
    provides: "ScorecardResult model schema for scoring.json format"
  - phase: 03-evidence-integration
    provides: "AggregatedEvidence model schema for evidence.json format"
  - phase: 04-ai-reasoning-engine
    provides: "ReasoningResult model schema for reasoning.json format"
provides:
  - "24 pre-cached JSON files (4 per scenario x 6 pharma targets) for VP demo"
  - "EGFR/NSCLC GO verdict (82.5 composite), CD274/Pan-cancer CONDITIONAL (62.4)"
  - "Scientifically plausible evidence, reasoning, scoring, and pipeline data"
  - "23-test UI integration suite covering pages, components, scenarios, and data models"
  - "scripts/generate_showcase_data.py for reproducible data generation"
affects: [08-validation]

# Tech tracking
tech-stack:
  added: []
  patterns: [pre-cached-json-scenarios, session-state-mock-for-testing, bare-mode-import-testing]

key-files:
  created:
    - scripts/generate_showcase_data.py
    - tests/test_ui_integration.py
    - data/showcase_scenarios/egfr/evidence.json
    - data/showcase_scenarios/egfr/scoring.json
    - data/showcase_scenarios/egfr/reasoning.json
    - data/showcase_scenarios/egfr/pipeline_report.json
    - data/showcase_scenarios/esr1/evidence.json
    - data/showcase_scenarios/esr1/scoring.json
    - data/showcase_scenarios/esr1/reasoning.json
    - data/showcase_scenarios/esr1/pipeline_report.json
    - data/showcase_scenarios/pik3ca/evidence.json
    - data/showcase_scenarios/pik3ca/scoring.json
    - data/showcase_scenarios/pik3ca/reasoning.json
    - data/showcase_scenarios/pik3ca/pipeline_report.json
    - data/showcase_scenarios/glp1r/evidence.json
    - data/showcase_scenarios/glp1r/scoring.json
    - data/showcase_scenarios/glp1r/reasoning.json
    - data/showcase_scenarios/glp1r/pipeline_report.json
    - data/showcase_scenarios/parp1/evidence.json
    - data/showcase_scenarios/parp1/scoring.json
    - data/showcase_scenarios/parp1/reasoning.json
    - data/showcase_scenarios/parp1/pipeline_report.json
    - data/showcase_scenarios/cd274/evidence.json
    - data/showcase_scenarios/cd274/scoring.json
    - data/showcase_scenarios/cd274/reasoning.json
    - data/showcase_scenarios/cd274/pipeline_report.json
  modified: []

key-decisions:
  - "Pre-populated st.session_state['user'] in test to handle projects.py module-level auth guard in bare mode"
  - "Generation script produces all 24 files deterministically with fixed timestamps for reproducibility"
  - "CD274 competitive_landscape dimension set to 5.5/15.0 to drive CONDITIONAL verdict via dimension violation"

patterns-established:
  - "Bare-mode Streamlit import testing: pre-populate session_state for pages with module-level auth guards"
  - "Scenario data generation via standalone script (scripts/generate_showcase_data.py) for auditability"

# Metrics
duration: 21min
completed: 2026-05-13
---

# Phase 7 Plan 04: Showcase Scenario Data and Integration Tests Summary

**24 pre-cached JSON files across 6 pharma targets (EGFR GO at 82.5, CD274 CONDITIONAL at 62.4) with 23-test integration suite verifying all pages, components, and data models**

## Performance

- **Duration:** 21 min
- **Started:** 2026-05-13T11:49:12Z
- **Completed:** 2026-05-13T12:10:56Z
- **Tasks:** 2
- **Files modified:** 26

## Accomplishments
- Generated scientifically plausible pre-cached data for 6 pharma showcase scenarios (EGFR, ESR1, PIK3CA, GLP1R, PARP1, CD274) with evidence from 6 sources, 5 reasoning modes, 7-dimension scoring, and pipeline QC metrics
- EGFR/NSCLC scores GO (82.5 composite) and CD274/Pan-cancer scores CONDITIONAL (62.4 composite with competitive_landscape dimension violation) -- matching ROADMAP validation criteria
- 23 integration tests covering 7 page imports, 3 component exports, 8 showcase scenarios, 3 style helpers, and 2 data model compatibility checks
- Full test suite: 194 tests pass (171 existing + 23 new, zero regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1: Generate pre-cached showcase scenario data for 6 pharma targets** - `9ee3f4b` (feat)
2. **Task 2: UI integration test suite** - `8fa6292` (test)

## Files Created/Modified
- `scripts/generate_showcase_data.py` - Standalone script generating all 24 JSON files with scenario-specific data
- `tests/test_ui_integration.py` - 23-test integration suite for pages, components, scenarios, and data models
- `data/showcase_scenarios/egfr/*.json` - EGFR/NSCLC evidence, reasoning, scoring, pipeline_report (GO, 82.5)
- `data/showcase_scenarios/esr1/*.json` - ESR1/ER+Breast evidence, reasoning, scoring, pipeline_report (GO, 74.3)
- `data/showcase_scenarios/pik3ca/*.json` - PIK3CA/HR+Breast evidence, reasoning, scoring, pipeline_report (GO, 71.0)
- `data/showcase_scenarios/glp1r/*.json` - GLP1R/Obesity evidence, reasoning, scoring, pipeline_report (GO, 78.8)
- `data/showcase_scenarios/parp1/*.json` - PARP1/BRCA+Breast evidence, reasoning, scoring, pipeline_report (GO, 73.5)
- `data/showcase_scenarios/cd274/*.json` - CD274/Pan-cancer evidence, reasoning, scoring, pipeline_report (CONDITIONAL, 62.4)

## Decisions Made
- Pre-populated `st.session_state["user"]` in test_projects_page_imports to handle the module-level auth guard pattern (`st.session_state["user"]` access at import time in bare mode)
- CD274 competitive_landscape score set to 5.5/15.0 (lowest among all dimensions) to naturally drive the CONDITIONAL verdict with a dimension violation, matching realistic PD-L1 market dynamics
- Generation script uses fixed timestamps for deterministic output, enabling reproducible data regeneration

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed projects.py import test for module-level session state access**
- **Found during:** Task 2 (UI integration test suite)
- **Issue:** `src/pages/projects.py` accesses `st.session_state["user"]` at module level (line 24), causing KeyError during bare-mode import in pytest
- **Fix:** Pre-populated `st.session_state["user"]` with mock user dict before import in the test
- **Files modified:** tests/test_ui_integration.py
- **Verification:** test_projects_page_imports passes
- **Committed in:** 8fa6292 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor test adaptation for Streamlit bare-mode compatibility. No scope creep.

## Issues Encountered
None -- plan executed smoothly.

## User Setup Required
None -- no external service configuration required.

## Next Phase Readiness
- All 7 pages import cleanly and are ready for end-to-end demo
- 24 pre-cached JSON files enable "under 5 minutes" showcase demo with no external API calls
- All 6 scenarios loadable via `load_scenario()` with complete evidence, reasoning, scoring, and pipeline data
- Full test suite at 194 tests provides regression safety net for Phase 8 (validation)

## Self-Check: PASSED

All 26 created files verified on disk. Both task commits (9ee3f4b, 8fa6292) verified in git log.

---
*Phase: 07-ui-integration*
*Completed: 2026-05-13*
