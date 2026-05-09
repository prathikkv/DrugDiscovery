# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-09)

**Core value:** Scientists upload omics data and target genes, receive a structured GO/CONDITIONAL/NO-GO recommendation with full audit trail -- replacing 6 months of manual assessment with 2 weeks.
**Current focus:** Phase 2: Omics Pipeline

## Current Position

Phase: 2 of 8 (Omics Pipeline)
Plan: 2 of 3 in current phase
Status: Executing
Last activity: 2026-05-10 -- Completed 02-02-PLAN.md (Processing, Annotation, Ambient RNA, DE)

Progress: [██░░░░░░░░] 20%

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: 5min
- Total execution time: 0.41 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 3 | 15min | 5min |
| 02-omics-pipeline | 2 | 10min | 5min |

**Recent Trend:**
- Last 5 plans: 01-01 (3min), 01-02 (6min), 01-03 (6min), 02-01 (5min), 02-02 (5min)
- Trend: Stable ~5min/plan

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: All 8 feature categories in v1 scope (user confirmed)
- [Init]: Comprehensive depth selected (8 phases derived from 59 requirements)
- [Init]: Quality (Opus) model profile for all planning agents
- [Roadmap]: Split Scoring from Deliverables into separate phases (5 and 6)
- [Roadmap]: HITL gates (REQ-505, REQ-506) assigned to Phase 7 (UI) since they need pages to render in
- [Roadmap]: Phases 2+3 marked parallelizable (omics and evidence are independent after foundation)
- [01-01]: Password hash excluded from User dataclass (security boundary)
- [01-01]: Per-operation DB connections to avoid SQLite threading issues
- [01-01]: BEGIN IMMEDIATE for write atomicity under WAL mode
- [01-01]: bcrypt<5.0 and scanpy<1.11 pinned per research pitfall findings
- [01-02]: Submit() uses underscore-prefixed params to avoid kwarg collision when forwarding to fn
- [01-02]: Genesis hash (64 zeros) for first audit record's previous_hash
- [01-02]: Deterministic JSON serialization for reproducible SHA-256 hashes
- [01-02]: E-signature uses bcrypt directly (not AuthService) to avoid circular dependency
- [01-02]: fn_args/fn_kwargs passed as bundles to _wrapped_run to avoid executor-level name collisions
- [01-03]: Soft-delete only -- projects set status='deleted', never physically removed
- [01-03]: Per-project directory structure (uploads/checkpoints/results/exports) at creation
- [01-03]: st.navigation/st.Page routing for explicit page control based on auth state
- [01-03]: Auth guard pattern: session_state check + st.warning + st.stop() on protected pages
- [01-03]: Synthetic h5ad fixture uses scipy.sparse.random with seed 42 for reproducibility
- [02-01]: 12 tissues in TISSUE_DEFAULTS (brain, tumor, lung, immune, heart, adipose, kidney, liver, intestine, eye, pancreas, default)
- [02-01]: Ensembl ID auto-detection in ingestion with swap to gene_symbols column when available
- [02-01]: Flexible donor/sex column detection in QC for cross-dataset compatibility
- [02-01]: sort_keys=True in PipelineConfig.to_json() for deterministic serialization
- [02-02]: TISSUE_MODEL_MAP has 12 entries matching TISSUE_DEFAULTS for consistent coverage
- [02-02]: CellTypist normalization guard: ValueError if adata.X max > 50 (raw vs log1p)
- [02-02]: DE min-cell threshold at 20 cells/group for statistical reliability
- [02-02]: Case-insensitive substring match in validate_annotations for flexible CellTypist label matching

### Pending Todos

- [ ] Verify st.fragment API against current Streamlit docs (Phase 1)
- [ ] Test qwen3:8b tool-calling with scientific queries (Phase 4)
- [ ] Verify GOT-IT framework dimensions against Nature Reviews paper (Phase 5)
- [ ] Collect 10-20 known target-disease pairs for retrovalidation (Phase 8)

### Blockers/Concerns

- R-001: Streamlit reruns kill long operations -- RESOLVED: TaskManager with ThreadPoolExecutor implemented in 01-02
- R-002: SQLite concurrent write deadlock -- RESOLVED: WAL mode + per-operation connections + threading.Lock in 01-01/01-02
- R-005: qwen3:8b tool-calling reliability unknown -- needs testing in Phase 4, fallback chain designed

## Session Continuity

Last session: 2026-05-10
Stopped at: Completed 02-02-PLAN.md (Processing, Annotation, Ambient RNA, DE)
Resume file: None
