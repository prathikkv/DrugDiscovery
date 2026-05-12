---
phase: 06-deliverables
plan: 02
subsystem: reporting
tags: [jinja2, html, plotly, templates, dossier, interactive-charts]

# Dependency graph
requires:
  - phase: 06-deliverables
    plan: 01
    provides: DossierData, DossierConfig, SectionContent, VisualizationBuilder, collect_dossier_data
  - phase: 05-target-scoring
    provides: ScorecardResult, CompositeScore, Verdict, build_single_radar
provides:
  - HTMLDossierRenderer class producing self-contained interactive HTML dossiers
  - 9 Jinja2 templates (base + dossier + 7 section templates) with consulting-grade CSS
  - Custom Jinja2 filters (format_score, format_pct, verdict_color)
  - render() returning HTML string and render_to_file() writing to disk
affects: [06-03, 07-ui]

# Tech tracking
tech-stack:
  added: [jinja2>=3.1.6]
  patterns: [jinja2-template-inheritance, custom-filter-registration, autoescape-with-safe-plotly-divs]

key-files:
  created:
    - src/reporting/html_renderer.py
    - src/reporting/templates/base.html
    - src/reporting/templates/dossier.html
    - src/reporting/templates/sections/executive_summary.html
    - src/reporting/templates/sections/target_overview.html
    - src/reporting/templates/sections/evidence_dimensions.html
    - src/reporting/templates/sections/ai_synthesis.html
    - src/reporting/templates/sections/scorecard.html
    - src/reporting/templates/sections/recommendations.html
    - src/reporting/templates/sections/audit_trail.html
  modified:
    - src/reporting/__init__.py

key-decisions:
  - "Jinja2 autoescape enabled for HTML safety; Plotly chart divs passed through | safe filter (trusted pre-rendered content)"
  - "First chart div includes plotly.js (per config); subsequent divs set include_plotlyjs=False to avoid loading multiple times"
  - "Chart download buttons enabled via Plotly config (PNG format, 900x600, 2x scale)"
  - "Graceful degradation: templates use {% if %} guards so sections show 'not available' fallback when data is missing"

patterns-established:
  - "Jinja2 template inheritance: base.html -> dossier.html -> section includes"
  - "Custom filter registration at renderer init (format_score, format_pct, verdict_color)"
  - "Chart div conversion: figures_to_divs() with first-chart plotly.js inclusion pattern"

# Metrics
duration: 6min
completed: 2026-05-12
---

# Phase 6 Plan 2: HTML Dossier Renderer Summary

**Jinja2-based HTMLDossierRenderer producing self-contained interactive HTML dossiers with 7 section templates, embedded Plotly charts, and consulting-grade CSS styling (#0071e3 brand)**

## Performance

- **Duration:** 6 min
- **Started:** 2026-05-12T09:57:35Z
- **Completed:** 2026-05-12T10:03:56Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- 9 Jinja2 templates with consulting-grade CSS: base template with brand color system (#0071e3), print media query, score bars, verdict badges, data tables
- HTMLDossierRenderer class producing self-contained HTML with embedded interactive Plotly charts and download buttons
- All 7 dossier sections render with proper data: executive_summary, target_overview, evidence_dimensions, ai_synthesis, scorecard, recommendations, audit_trail
- Graceful degradation: empty/missing data shows fallback messages without errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Jinja2 templates for dossier sections** - `11e653b` (feat)
2. **Task 2: HTML dossier renderer** - `9022189` (feat)

## Files Created/Modified
- `src/reporting/html_renderer.py` - HTMLDossierRenderer class with render/render_to_file, custom filters, Plotly div conversion
- `src/reporting/templates/base.html` - Base template with CSS variables, data-table, score-bar, verdict-badge, print styling
- `src/reporting/templates/dossier.html` - Main dossier template extending base with all 7 section includes
- `src/reporting/templates/sections/executive_summary.html` - Verdict badge, composite score, narrative, radar chart
- `src/reporting/templates/sections/target_overview.html` - Gene identifiers table, UniProt data, disease context
- `src/reporting/templates/sections/evidence_dimensions.html` - Dimension score bars, sub-score tables, bar chart
- `src/reporting/templates/sections/ai_synthesis.html` - Claims table, contradiction/gap/hypothesis sections
- `src/reporting/templates/sections/scorecard.html` - Full scoring table, weights, verdict rationale, charts
- `src/reporting/templates/sections/recommendations.html` - Verdict badge, narrative, key risks
- `src/reporting/templates/sections/audit_trail.html` - Evidence sources table, reproducibility hash, provenance
- `src/reporting/__init__.py` - Added HTMLDossierRenderer to public API and __all__

## Decisions Made
- Jinja2 autoescape enabled for HTML safety; Plotly chart divs passed through `| safe` filter since they are trusted pre-rendered content
- First chart div includes plotly.js (True or 'cdn' per config); subsequent divs set `include_plotlyjs=False` to avoid loading plotly.js multiple times
- Chart download buttons enabled via Plotly config object with PNG format at 900x600 and 2x scale
- Graceful degradation via `{% if %}` guards in all templates -- missing data shows "not available" fallback messages

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed jinja2 dependency**
- **Found during:** Task 1 (template creation)
- **Issue:** jinja2 not installed in environment despite being listed in plan
- **Fix:** Ran `pip install "jinja2>=3.1.6"` to install dependency
- **Files modified:** None (pip package)
- **Verification:** `import jinja2` succeeds, templates parse correctly
- **Committed in:** N/A (environment-level change)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Trivial dependency installation. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- HTMLDossierRenderer is fully operational and exported from src.reporting
- Plan 03 (PDF renderer) can reuse the same DossierData, VisualizationBuilder, and template structure
- All 149 existing tests pass with no regressions
- Self-contained HTML files work offline in any browser

## Self-Check: PASSED
