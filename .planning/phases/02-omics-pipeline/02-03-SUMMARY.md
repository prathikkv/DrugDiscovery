---
phase: 02-omics-pipeline
plan: 03
subsystem: pipeline
tags: [gseapy, enrichment, orchestrator, scanpy, anndata, pytest, checkpointing]

# Dependency graph
requires:
  - phase: 02-omics-pipeline
    plan: 01
    provides: "PipelineConfig, ingestion, QC, checkpointing, progress tracking"
  - phase: 02-omics-pipeline
    plan: 02
    provides: "Processing, annotation, ambient RNA removal, differential expression"
provides:
  - "run_enrichment(): ORA via gseapy on DE results per cell type"
  - "run_pipeline(): 7-stage orchestrator with checkpoint resume and progress tracking"
  - "Public API: run_pipeline, PipelineConfig, QCConfig, ProcessingConfig, TISSUE_DEFAULTS"
  - "12-test suite covering config, ingestion, QC, checkpointing, progress, and biology regression"
  - "pipeline_h5ad fixture with MT genes for QC testing"
affects: [03-evidence-pipeline, 05-scoring, 07-ui, 08-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [orchestrator-with-resume, stage-skip-on-checkpoint, fixture-with-mt-genes]

key-files:
  created:
    - src/pipeline/enrichment.py
    - tests/test_pipeline.py
  modified:
    - src/pipeline/__init__.py
    - tests/conftest.py

key-decisions:
  - "Enrichment thresholds: pvals_adj < 0.05 and logfoldchanges > 0.5 for significant upregulated genes"
  - "Minimum 5 significant genes required per cell type for ORA (too_few_genes skip otherwise)"
  - "ConnectionError handled gracefully in enrichment -- network failures logged per cell type, not fatal"
  - "Resume logic: stages before checkpoint stored as skipped with reason=resumed_from_checkpoint"
  - "Installed scanpy via conda to enable actual test execution (previous plans verified via AST only)"

patterns-established:
  - "Orchestrator pattern: sequential stage execution with in-list membership check for resume"
  - "Enrichment error isolation: per-cell-type try/except prevents one failure from blocking others"
  - "Pipeline-ready test fixture with MT genes and high-mito cells for realistic QC testing"
  - "Test-only verification of no-hardcoded-biology via file scanning (REQ-101 regression guard)"

# Metrics
duration: 13min
completed: 2026-05-10
---

# Phase 2 Plan 3: Enrichment, Orchestrator, and Test Suite Summary

**Gene set enrichment via gseapy ORA, run_pipeline() orchestrator wiring 7 stages with checkpoint resume, and 12-test suite covering config through biology-free regression**

## Performance

- **Duration:** 13 min
- **Started:** 2026-05-09T19:51:42Z
- **Completed:** 2026-05-09T20:05:27Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Gene set enrichment module (run_enrichment) performing ORA via gseapy on significant DE genes per cell type, with configurable gene sets from PipelineConfig and graceful error handling per cell type
- run_pipeline() orchestrator wiring all 7 stages (ingest -> ambient_rna -> qc -> processing -> annotation -> de -> enrichment) with checkpoint-based resume, progress tracking, and comprehensive result reporting
- Public API exporting run_pipeline, PipelineConfig, QCConfig, ProcessingConfig, and TISSUE_DEFAULTS from src.pipeline
- 12-test pipeline test suite covering config validation, ingestion, QC filtering, checkpointing, progress tracking, and no-hardcoded-biology regression -- all passing alongside 29 Phase 1 tests (41 total, zero regressions)
- Pipeline-ready test fixture (pipeline_h5ad) with 100 cells, 50 genes including MT genes and high-mito cells for realistic QC testing

## Task Commits

Each task was committed atomically:

1. **Task 1: Enrichment module and pipeline orchestrator** - `853a8c5` (feat)
2. **Task 2: Pipeline test suite and enhanced fixtures** - `d975260` (test)

## Files Created/Modified
- `src/pipeline/enrichment.py` - Gene set enrichment via gseapy ORA per cell type with checkpoint/progress integration
- `src/pipeline/__init__.py` - Public API with run_pipeline() orchestrator wiring all 7 stages with resume support
- `tests/test_pipeline.py` - 12-test suite covering config, ingestion, QC, checkpointing, progress, biology regression
- `tests/conftest.py` - Added pipeline_h5ad (100x50 with MT genes) and pipeline_project_dir fixtures

## Decisions Made
- **Enrichment gene thresholds**: pvals_adj < 0.05 and logfoldchanges > 0.5 for extracting significant upregulated genes, minimum 5 genes required for ORA analysis
- **Network error isolation**: ConnectionError during gseapy enrichment logged per cell type with error dict, not propagated as pipeline failure
- **Resume via stage list membership**: Used `if stage_name in remaining_stages` pattern rather than index-based loop for clarity and robustness
- **Installed scanpy**: conda install resolved scipy/sklearn/numba dependency chain that pip could not build; enabled actual test execution vs previous AST-only verification

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed scanpy and fixed numpy/scipy compatibility**
- **Found during:** Task 2 (test execution)
- **Issue:** scanpy not installed; conda install introduced scipy/numpy version conflicts
- **Fix:** conda install scanpy, then pip install numpy<2.2 and scipy reinstall to resolve numba/numpy incompatibility
- **Files modified:** None (environment only)
- **Verification:** All 41 tests pass, scanpy imports correctly
- **Committed in:** N/A (environment change, no code files affected)

---

**Total deviations:** 1 auto-fixed (1 blocking dependency)
**Impact on plan:** Environment fix only, no code scope change. Actually improved confidence vs prior plans that could only verify via AST.

## Issues Encountered
- scipy/sklearn/numba version conflicts after conda install of scanpy -- resolved by downgrading numpy to <2.2 for numba compatibility. Future deployments should use conda-forge channel for consistent package resolution.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 2 (Omics Pipeline) is now complete: all 7 pipeline stages implemented and wired together
- run_pipeline() provides a single-call API for the entire scRNA-seq analysis workflow
- Pipeline supports: multi-format ingestion, ambient RNA removal (SoupX), configurable QC, full scanpy processing, CellTypist annotation with 12-tissue model selection, Wilcoxon DE, and gene set enrichment
- Checkpoint-based resume enables long pipelines to survive interruptions
- All 41 tests pass (12 pipeline + 29 foundation)
- Phase 3 (Evidence Pipeline) can proceed independently
- Phase 5 (Scoring) will consume pipeline outputs (DE results, enrichment, cell type annotations)
- Phase 7 (UI) will integrate run_pipeline() via TaskManager for background execution

## Self-Check: PASSED
