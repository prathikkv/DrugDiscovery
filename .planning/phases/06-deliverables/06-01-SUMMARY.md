---
phase: 06-deliverables
plan: 01
subsystem: reporting
tags: [pydantic, plotly, kaleido, data-models, visualization, chart-export]

# Dependency graph
requires:
  - phase: 05-target-scoring
    provides: ScorecardResult, CompositeScore, Verdict, build_single_radar, build_comparative_radar
  - phase: 03-evidence-integration
    provides: AggregatedEvidence, GeneIdentifiers, EvidenceResult
  - phase: 04-ai-reasoning-engine
    provides: ReasoningResult, ReasoningMode, Claim
provides:
  - DossierData Pydantic model aggregating all upstream outputs
  - DossierConfig for rendering configuration (chart sizes, brand, plotlyjs)
  - SectionContent model for 7 standard dossier sections
  - collect_dossier_data() serializer from upstream types to DossierData
  - VisualizationBuilder producing Plotly figures from DossierData
  - chart export utilities (PNG, SVG, in-memory bytes)
affects: [06-02, 06-03, 07-ui]

# Tech tracking
tech-stack:
  added: [kaleido==0.2.1]
  patterns: [lazy-import for upstream types, graceful-degradation for missing chart data]

key-files:
  created:
    - src/reporting/__init__.py
    - src/reporting/models.py
    - src/reporting/data_collector.py
    - src/reporting/visualizations.py
    - src/reporting/chart_export.py
  modified: []

key-decisions:
  - "Lazy imports for all upstream types (ScorecardResult, AggregatedEvidence, ReasoningResult) to avoid circular dependencies"
  - "VisualizationBuilder returns None for charts with missing data -- graceful degradation over error"
  - "Radar charts delegate to existing build_single_radar/build_comparative_radar for consistent styling"
  - "kaleido 0.2.1 installed per plan despite deprecation warning with Plotly 6.x (functionally works)"
  - "7 pre-built sections in collect_dossier_data: executive_summary, target_overview, evidence_dimensions, ai_synthesis, scorecard, recommendations, audit_trail"

patterns-established:
  - "DossierData as single serializable container for all upstream outputs"
  - "SectionContent with title/narrative/data/charts structure for renderer consumption"
  - "VisualizationBuilder pattern: build_all() collects individual builder results, skipping None"
  - "chart_to_png_bytes() for in-memory PDF embedding without temp files"

# Metrics
duration: 8min
completed: 2026-05-12
---

# Phase 6 Plan 1: Reporting Foundation Summary

**Pydantic DossierData model with 7-section data collector, VisualizationBuilder producing radar/bar/breakdown Plotly figures, and PNG/SVG chart export via kaleido**

## Performance

- **Duration:** 8 min
- **Started:** 2026-05-12T09:45:59Z
- **Completed:** 2026-05-12T09:54:07Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- DossierData, DossierConfig, SectionContent Pydantic v2 models providing unified data layer for HTML/PDF renderers
- collect_dossier_data() serializes ScorecardResult, AggregatedEvidence, and ReasoningResult into 7 pre-built dossier sections
- VisualizationBuilder creates radar_single, radar_comparative, evidence_dimensions_bar, score_breakdown, umap, heatmap, and volcano charts
- Chart export utilities: file-based PNG/SVG export and in-memory PNG bytes for PDF embedding

## Task Commits

Each task was committed atomically:

1. **Task 1: Dossier data models and data collector** - `161fe73` (feat)
2. **Task 2: Visualization builder and chart export utilities** - `135c3b4` (feat)

## Files Created/Modified
- `src/reporting/__init__.py` - Package public API with all 8 exports
- `src/reporting/models.py` - DossierData, DossierConfig, SectionContent Pydantic models
- `src/reporting/data_collector.py` - collect_dossier_data() serializer with 7-section builder
- `src/reporting/visualizations.py` - VisualizationBuilder with 7 chart builder methods
- `src/reporting/chart_export.py` - export_chart_png, export_chart_svg, chart_to_png_bytes

## Decisions Made
- Lazy imports for upstream types to prevent circular dependency chains between reporting, scoring, evidence, and reasoning modules
- VisualizationBuilder returns None (not raises) when chart data is missing, allowing dossiers to render with partial data
- Radar charts reuse existing build_single_radar/build_comparative_radar from scoring module for consistency
- kaleido 0.2.1 installed per plan specification; works with Plotly 6.7.0 despite deprecation warning
- 7 standard sections pre-built in data collector with structured data and chart identifiers ready for renderer templates

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- src/reporting/ package complete with data layer and visualization layer
- Plans 02 (HTML renderer) and 03 (PDF renderer) can now consume DossierData and VisualizationBuilder
- Both renderers share the same data models and chart builder, enabling parallel implementation
- All 149 existing tests pass with no regressions

## Self-Check: PASSED

All 5 created files verified on disk. Both task commits (161fe73, 135c3b4) verified in git log.

---
*Phase: 06-deliverables*
*Completed: 2026-05-12*
