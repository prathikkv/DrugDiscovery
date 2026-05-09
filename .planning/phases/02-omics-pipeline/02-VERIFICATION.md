---
phase: 02-omics-pipeline
verified: 2026-05-10T00:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 2: Omics Pipeline Verification Report

**Phase Goal:** Scientists can upload any tissue type's scRNA-seq data and run a complete, disease-agnostic analysis pipeline -- from ingestion through QC, processing, annotation, and differential expression -- with no hardcoded biology.
**Verified:** 2026-05-10
**Status:** PASSED
**Re-verification:** No -- initial verification

---

## Goal Achievement

### Observable Truths (Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can upload .h5ad, .h5, or 10x folder with no GIPR/GLP1R/MariTide references in pipeline output | VERIFIED | `ingest_data()` in `src/pipeline/ingestion.py` handles all three formats; grep scan of entire `src/pipeline/` returns CLEAN for GIPR, GLP1R, MariTide, ADIPOQ |
| 2 | Pipeline applies SoupX before annotation with HITL gate allowing skip with recorded warning | VERIFIED | `run_ambient_rna_removal()` in `src/pipeline/ambient_rna.py` checks `config.skip_ambient_rna`; skip stores `reason="user_skip"` and `warning` in the report; orchestrator stores report in `results["ambient_rna"]` |
| 3 | User can set tissue-specific QC thresholds (e.g., max_mito=5% brain, 25% tumor) at project setup | VERIFIED | `PipelineConfig.for_tissue()` in `src/pipeline/config.py` with 12-tissue TISSUE_DEFAULTS; `run_qc()` uses `qc_cfg.max_pct_mt` exclusively -- no hardcoded threshold; test passes with brain (5%) filtering more cells than default (15%) |
| 4 | Pipeline produces DE results with adjusted p-values, gene set enrichment per cell type, and CellTypist annotations validated against canonical markers | VERIFIED | `run_differential_expression()` uses `sc.tl.rank_genes_groups` with `corr_method=config.de_corr_method`; extracts `pvals_adj` per gene; `run_enrichment()` calls `gp.enrich()` per cell type; `validate_annotations()` checks 10 canonical marker sets; `run_annotation()` called by orchestrator followed immediately by `validate_annotations()` |
| 5 | Pipeline stages report progress to TaskManager and save checkpoints so resumed project picks up from last completed stage | VERIFIED | Every stage calls `save_checkpoint()` on completion and `progress_tracker.update()` if tracker provided; `run_pipeline()` calls `get_latest_checkpoint()` at start; checkpoint-based resume tested and passing (`test_checkpoint_resume` passes) |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/pipeline/config.py` | PipelineConfig + TISSUE_DEFAULTS registry | VERIFIED | 12 tissues (brain=5%, tumor=25%, lung=10%, etc.); `for_tissue()`, `to_json()`, `from_json()` all present and tested |
| `src/pipeline/ingestion.py` | Multi-format ingestion with format auto-detection | VERIFIED | Handles .h5ad, .h5, directory; Ensembl ID detection; `raw_counts` layer; 157 lines, substantive |
| `src/pipeline/qc.py` | Configurable QC with doublet detection, sex concordance, mito filtering | VERIFIED | Imports `PipelineConfig`; uses `qc_cfg.*` throughout; scrublet with graceful fallback; sex concordance; 324 lines, substantive |
| `src/pipeline/checkpointing.py` | Save/load checkpoints per stage | VERIFIED | `save_checkpoint`, `load_checkpoint`, `get_latest_checkpoint`, `save_stage_report`, `load_stage_report`; STAGE_ORDER list with 7 stages |
| `src/pipeline/progress.py` | TaskManager integration with stage-weight progress tracking | VERIFIED | `StageProgressTracker` with STAGE_WEIGHTS dict; `update()` and `update_substage()` methods; no-op when task_manager is None |
| `src/pipeline/ambient_rna.py` | SoupX via rpy2 with graceful fallback | VERIFIED | Three fallback paths: user skip, rpy2/SoupX unavailable, no raw counts; all paths produce structured skip reports with `warning` field |
| `src/pipeline/processing.py` | Full scanpy processing: normalize -> HVG -> PCA -> Harmony -> UMAP -> Leiden | VERIFIED | Uses all `config.processing.*` parameters; Harmony batch correction; 228 lines, substantive |
| `src/pipeline/annotation.py` | CellTypist with tissue-aware model selection and marker validation | VERIFIED | `TISSUE_MODEL_MAP` 12 entries; normalization guard; `validate_annotations()` with 10 canonical marker sets (CANONICAL_MARKERS) |
| `src/pipeline/differential_expression.py` | Wilcoxon DE with adjusted p-values, min-cell filtering | VERIFIED | `sc.tl.rank_genes_groups` with `corr_method=config.de_corr_method`; extracts `pvals_adj` per gene dict; MIN_CELLS_PER_GROUP=20 filter |
| `src/pipeline/enrichment.py` | Gene set enrichment via gseapy ORA per cell type | VERIFIED | `gp.enrich()` per cell type; reads `config.enrichment_gene_sets`; per-cell-type error isolation; checkpoint integrated |
| `src/pipeline/__init__.py` | Public API: run_pipeline() orchestrating all 7 stages | VERIFIED | Imports and calls all 7 stage functions in order; checkpoint resume logic; exports PipelineConfig, QCConfig, ProcessingConfig, TISSUE_DEFAULTS |
| `tests/test_pipeline.py` | 12-test suite covering config, ingestion, QC, checkpointing, progress | VERIFIED | 12 tests, all passing: config, serialization, tissue defaults, h5ad ingest, invalid format, QC filtering, QC report, checkpoint save/load, resume, progress no-op, progress with TaskManager, no-hardcoded-biology regression |
| `tests/conftest.py` | Enhanced fixture with pipeline-ready h5ad (includes MT genes) | VERIFIED | `pipeline_h5ad` fixture with 100 cells x 50 genes, 3 MT- genes, high-mito cells; `pipeline_project_dir` fixture |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/pipeline/qc.py` | `src/pipeline/config.py` | QCConfig parameters | WIRED | `qc_cfg = config.qc` then `qc_cfg.max_pct_mt`, `qc_cfg.min_genes`, etc. throughout |
| `src/pipeline/progress.py` | `src/execution/task_manager.py` | `TaskManager.update_progress()` | WIRED | `self._task_manager.update_progress(self._task_id, progress, checkpoint_path)` at line 86; `TaskManager.update_progress` confirmed at line 192 of task_manager.py |
| `src/pipeline/checkpointing.py` | project checkpoints/ directory | Path-based h5ad save/load | WIRED | `checkpoint_dir = project_dir / "checkpoints"` then `adata.write_h5ad(checkpoint_path)` and `ad.read_h5ad(checkpoint_path)` |
| `src/pipeline/processing.py` | `src/pipeline/config.py` | ProcessingConfig parameters | WIRED | `proc = config.processing` then `proc.n_top_hvgs`, `proc.n_pcs`, `proc.leiden_resolution`, etc. |
| `src/pipeline/annotation.py` | celltypist | `celltypist.annotate()` | WIRED | `celltypist.annotate(adata, model=model, majority_voting=True, over_clustering="leiden")` at line 165 |
| `src/pipeline/differential_expression.py` | scanpy | `sc.tl.rank_genes_groups` | WIRED | `sc.tl.rank_genes_groups(adata_sub, groupby=groupby, method=config.de_method, corr_method=config.de_corr_method, ...)` at line 151 |
| `src/pipeline/enrichment.py` | gseapy | `gp.enrich()` for ORA | WIRED | `import gseapy as gp` then `gp.enrich(gene_list=sig_genes, gene_sets=gene_sets, organism="human", ...)` at line 140 |
| `src/pipeline/__init__.py` | all stage modules | Sequential stage function calls | WIRED | All 7 stage functions imported and called in sequence; conditional on `remaining_stages` list membership |
| `src/pipeline/__init__.py` | `src/pipeline/checkpointing.py` | Resume from checkpoint | WIRED | `get_latest_checkpoint(project_dir)` called at line 82; resume logic at lines 97-121 |
| `src/pipeline/__init__.py` | `src/pipeline/progress.py` | StageProgressTracker | WIRED | `StageProgressTracker(task_manager, task_id)` created at line 78; passed to all stage functions |

---

### Requirements Coverage

| Requirement | Status | Notes |
|-------------|--------|-------|
| REQ-101 (No hardcoded biology) | SATISFIED | grep scan CLEAN; regression test `test_no_hardcoded_biology` passes |
| REQ-102 (Multi-format ingestion) | SATISFIED | `ingest_data()` handles .h5ad, .h5, 10x MTX directory |
| REQ-103 (Ambient RNA correction) | SATISFIED | `run_ambient_rna_removal()` with SoupX + graceful fallback |
| REQ-104 (Tissue-specific QC thresholds) | SATISFIED | `PipelineConfig.for_tissue()` + 12-tissue TISSUE_DEFAULTS; thresholds flow through to `run_qc()` |
| REQ-105 (DE with adjusted p-values) | SATISFIED | Wilcoxon + BH correction via `rank_genes_groups`; `pvals_adj` in results |
| REQ-106 (Gene set enrichment) | SATISFIED | `run_enrichment()` via gseapy ORA on significant DE genes per cell type |
| REQ-107 (CellTypist annotations validated) | SATISFIED | `validate_annotations()` with CANONICAL_MARKERS; called in orchestrator after annotation |
| REQ-108 (Progress reporting to TaskManager) | SATISFIED | `StageProgressTracker` wired to TaskManager; STAGE_WEIGHTS map; test passes |
| REQ-109 (Checkpoint/resume) | SATISFIED | Every stage saves checkpoint; orchestrator detects and resumes from latest; test passes |
| REQ-110 (CellTypist annotation) | SATISFIED | `run_annotation()` with tissue-aware model selection from TISSUE_MODEL_MAP |

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `src/pipeline/qc.py` lines 111, 231, 252 | `groupby()` without `observed=` parameter (FutureWarning from pandas) | Info | Will become error in future pandas; does not affect current behavior or test results |

No blockers. No stubs. No placeholder implementations. No hardcoded biology.

---

### Human Verification Required

#### 1. SoupX End-to-End Execution

**Test:** Upload a CellRanger output folder that includes both filtered and raw barcode matrices, set `skip_ambient_rna=False`, and run the full pipeline.
**Expected:** SoupX executes successfully; report shows `status=completed` and a numeric `contamination_fraction`; annotated data reflects corrected counts.
**Why human:** rpy2 and R with SoupX are not installed in the dev environment. The SoupX code path is correct by inspection and follows the plan exactly, but actual R execution cannot be verified programmatically.

#### 2. CellTypist Annotation Output

**Test:** Run `run_annotation()` on a real scRNA-seq h5ad with normalized data; check that `adata.obs["cell_type"]` is populated with recognizable cell type names.
**Expected:** `cell_type` column populated; `n_cell_types` > 1 in annotation report; `validate_annotations()` returns discrepancy list.
**Why human:** CellTypist requires model download (network access) and non-trivial data. The logic is correct by inspection but actual CellTypist output cannot be verified without the model files.

#### 3. Pipeline Resume After Interruption

**Test:** Start a pipeline on real data, kill it after the QC checkpoint is written, then restart with the same project directory.
**Expected:** Pipeline logs "Resuming pipeline from checkpoint: stage='qc'"; ingest and ambient_rna appear as `skipped/resumed_from_checkpoint` in the report; processing begins from the QC checkpoint.
**Why human:** The resume logic is verified by unit tests with synthetic data, but real-world checkpoint file integrity across restarts benefits from human confirmation.

---

### Gaps Summary

None. All 5 observable truths verified, all 13 artifacts exist and are substantive, all 10 key links are wired. 41/41 tests passing including 12 new pipeline tests. No hardcoded biology in any pipeline file.

The single FutureWarning from pandas groupby is a deprecation notice, not a failure. It does not affect correctness.

---

_Verified: 2026-05-10_
_Verifier: Claude (gsd-verifier)_
