# Architecture Research

**Domain:** AI-Powered Drug Target Intelligence Platform (Pharma Bioinformatics)
**Researched:** 2026-05-09
**Confidence:** MEDIUM-HIGH

## Standard Architecture

### System Overview

```
+=====================================================================+
|                          PRESENTATION LAYER                          |
|  +-------------+  +-------------+  +-------------+  +-------------+ |
|  |   Login     |  |   Project   |  |   Omics     |  |  Evidence   | |
|  |   Page      |  |   Setup     |  |   Pipeline  |  |  Explorer   | |
|  +-------------+  +-------------+  +-------------+  +-------------+ |
|  +-------------+  +-------------+  +-------------+                   |
|  |   AI        |  |  Scorecard  |  |   Audit     |                   |
|  |  Reasoning  |  |  Dashboard  |  |   Trail     |                   |
|  +-------------+  +-------------+  +-------------+                   |
+====================+================================================+
                     |
+====================v================================================+
|                      ORCHESTRATION LAYER                             |
|  +--------------------+  +--------------------+  +----------------+ |
|  |   Task Manager     |  |   HITL Gate        |  |   Session      | |
|  |   (ThreadPool +    |  |   Controller       |  |   State Mgr    | |
|  |    SQLite state)   |  |   (9 gates)        |  |   (st.session) | |
|  +--------------------+  +--------------------+  +----------------+ |
+====================+================================================+
                     |
+=======+============v==========+=============+===========+===========+
|       |                       |             |           |           |
| +-----v------+  +------------v-+  +--------v---+  +---v-------+   |
| |   OMICS    |  |   EVIDENCE   |  | REASONING  |  | SCORECARD |   |
| |  SERVICES  |  |   SERVICES   |  |  ENGINE    |  | FRAMEWORK |   |
| +------------+  +--------------+  +------------+  +-----------+   |
| | ingest     |  | opentargets  |  | hypothesis |  | 7-dim     |   |
| | harmonize  |  | dgidb        |  | synthesis  |  | scoring   |   |
| | qc         |  | pubmed       |  | contradict |  | weights   |   |
| | process    |  | clintrials   |  | gap_detect |  | composite |   |
| | annotate   |  | uniprot      |  | confidence |  | verdict   |   |
| | expression |  | chembl       |  |            |  |           |   |
| +-----+------+  +------+-------+  +------+-----+  +-----+-----+  |
|       |                |                  |              |          |
+=======+================+==================+=============+===========+
        |                |                  |              |
+=======v================v==================v==============v==========+
|                       CROSS-CUTTING SERVICES                        |
|  +----------------+  +------------------+  +---------------------+  |
|  |  LLM Abstraction|  |  Audit Trail     |  |  Auth + RBAC       |  |
|  |  (llm/)        |  |  (compliance/)   |  |  (core/auth.py)    |  |
|  |  Ollama/Groq/  |  |  Hash chains     |  |  bcrypt + sessions |  |
|  |  Anthropic     |  |  E-signatures    |  |  Account lockout   |  |
|  +----------------+  |  ALCOA+ logging  |  +---------------------+  |
|                       +------------------+                           |
+=========================+============================================+
                          |
+=========================v============================================+
|                       DATA LAYER                                     |
|  +------------------+  +------------------+  +-------------------+   |
|  |  SQLite (MVP)    |  |  File System     |  |  Evidence Cache   |   |
|  |  - projects      |  |  - .h5ad files   |  |  (SQLite + TTL)   |   |
|  |  - audit_trail   |  |  - checkpoints   |  |  - API responses  |   |
|  |  - users         |  |  - plots         |  |  - gene aliases   |   |
|  |  - task_state    |  |  - reports       |  |  - 24h default    |   |
|  +------------------+  +------------------+  +-------------------+   |
+======================================================================+
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **ui/** (Presentation) | 7 Streamlit pages, HITL approval widgets, progress displays, copilot chat | Multi-page Streamlit app via `st.navigation()` or pages/ directory |
| **core/task_manager.py** (Orchestration) | Submit background tasks, poll status, manage ThreadPoolExecutor lifecycle | ThreadPoolExecutor(max_workers=2) + SQLite task_state table |
| **core/hitl.py** (Orchestration) | Define 9 gate schemas, track approval state, enforce Compliance vs Exploration mode | Pydantic models for gate state, SQLite persistence |
| **omics/** (Domain Service) | 7-stage Scanpy pipeline: ingest, harmonize, QC, process, annotate, expression, export | Refactored from existing pipeline/ stages, disease-agnostic |
| **evidence/** (Domain Service) | 6 external API integrations, parallel fetch, result normalization, caching | aiohttp or concurrent.futures for parallel fetch, SQLite cache |
| **reasoning/** (Domain Service) | 5-mode AI engine (hypothesis, synthesis, contradiction, gap, confidence), ReAct loop | LLM tool-calling with up to 10 rounds, provenance tracking |
| **scorecard/** (Domain Service) | 7-dimension GOT-IT scoring, weight configuration, composite score, GO/CONDITIONAL/NO-GO | Pydantic models, weighted sum, configurable per-project |
| **llm/** (Cross-cutting) | Provider abstraction, model selection, token tracking, fallback chain | Existing llm_provider.py, cleaned up with logging |
| **compliance/** (Cross-cutting) | 21 CFR Part 11 audit trail, hash chains, e-signatures, ALCOA+ | Append-only SQLite with SHA-256 hash chains |
| **core/auth.py** (Cross-cutting) | User authentication, RBAC (admin/scientist/reviewer), session management | bcrypt password hashing, SQLite users table |
| **core/models.py** (Cross-cutting) | Shared data models: Project, Target, EvidenceRecord, AuditEntry, Score | Pydantic BaseModel or dataclasses |

## Recommended Project Structure

```
bioorchestrator/
+-- config.py                    # Disease-agnostic configuration
+-- main.py                      # Entry point (streamlit run main.py)
+-- core/
|   +-- __init__.py
|   +-- models.py                # Shared Pydantic models (Project, Target, Score, etc.)
|   +-- auth.py                  # User auth, RBAC, sessions
|   +-- task_manager.py          # Background task execution + polling
|   +-- hitl.py                  # HITL gate definitions and state management
|   +-- audit.py                 # Low-level audit logging (used by compliance/)
+-- omics/
|   +-- __init__.py
|   +-- pipeline.py              # Pipeline orchestrator (runs stages in sequence)
|   +-- ingest.py                # Stage 1: Data ingestion (.h5ad, .h5, 10x)
|   +-- harmonize.py             # Stage 2: Metadata harmonization (CDISC)
|   +-- qc.py                    # Stage 3: QC gates (5-layer)
|   +-- process.py               # Stage 4: Scanpy processing
|   +-- annotate.py              # Stage 5: Cell type annotation (CellTypist)
|   +-- expression.py            # Stage 6: DE analysis, expression profiling
|   +-- export.py                # Stage 7: Results export
+-- evidence/
|   +-- __init__.py
|   +-- aggregator.py            # Parallel fetch orchestrator
|   +-- cache.py                 # SQLite evidence cache with TTL
|   +-- gene_resolver.py         # Gene alias resolution (MyGene.info)
|   +-- sources/
|       +-- opentargets.py       # OpenTargets GraphQL
|       +-- dgidb.py             # DGIdb GraphQL
|       +-- pubmed.py            # PubMed via Bio.Entrez
|       +-- clinicaltrials.py    # ClinicalTrials.gov REST v2
|       +-- uniprot.py           # UniProt REST
|       +-- chembl.py            # ChEMBL REST
+-- reasoning/
|   +-- __init__.py
|   +-- engine.py                # 5-mode reasoning orchestrator
|   +-- react_loop.py            # ReAct tool-calling loop (max 10 rounds)
|   +-- tools.py                 # Tool definitions for LLM (data queries)
|   +-- prompts.py               # System prompts per reasoning mode
|   +-- provenance.py            # Track reasoning chain for audit
+-- scorecard/
|   +-- __init__.py
|   +-- framework.py             # 7-dimension GOT-IT scoring
|   +-- dimensions.py            # Individual dimension calculators
|   +-- weights.py               # Weight configuration and defaults
|   +-- verdict.py               # GO / CONDITIONAL / NO-GO logic
+-- llm/
|   +-- __init__.py
|   +-- provider.py              # Multi-provider abstraction (existing)
|   +-- fallback.py              # Fallback chain logic
|   +-- token_tracker.py         # Token usage logging
+-- compliance/
|   +-- __init__.py
|   +-- audit_trail.py           # Hash-chained audit trail (21 CFR Part 11)
|   +-- e_signature.py           # Electronic signature capture
|   +-- report_generator.py      # Target Assessment Dossier (HTML/PDF)
|   +-- alcoa.py                 # ALCOA+ data integrity checks
+-- ui/
|   +-- __init__.py
|   +-- app.py                   # Main Streamlit entry + navigation
|   +-- pages/
|   |   +-- 1_login.py
|   |   +-- 2_project_setup.py
|   |   +-- 3_omics_pipeline.py
|   |   +-- 4_evidence.py
|   |   +-- 5_ai_reasoning.py
|   |   +-- 6_scorecard.py
|   |   +-- 7_audit_trail.py
|   +-- components/
|       +-- hitl_widgets.py      # Approve/reject/comment widgets
|       +-- progress.py          # Pipeline progress display
|       +-- charts.py            # Plotly chart components
|       +-- copilot.py           # Chat interface
+-- data/                        # Runtime data (gitignored)
|   +-- projects/                # Per-project h5ad, checkpoints
|   +-- cache/                   # Evidence cache DB
|   +-- db/                      # Main SQLite database
+-- tests/
    +-- test_omics/
    +-- test_evidence/
    +-- test_reasoning/
    +-- test_scorecard/
    +-- test_compliance/
    +-- golden/                  # Golden test: EGFR in NSCLC
```

### Structure Rationale

- **core/:** Shared infrastructure that all domain services depend on. Auth, models, task management, and HITL gates are foundational -- everything else uses them. Build this first.
- **omics/:** Direct refactor of existing pipeline/ code. Each stage becomes a standalone module with configurable parameters (no hardcoded genes). The pipeline.py orchestrator replaces run_pipeline.py.
- **evidence/:** Each API source is an independent module behind a common interface (EvidenceSource protocol). The aggregator runs them in parallel. The cache prevents redundant API calls across reasoning rounds.
- **reasoning/:** Extends the existing ai_copilot.py into a structured engine. Five reasoning modes share the same ReAct loop but use different system prompts and tool subsets. Provenance tracking logs every LLM call and tool use for audit.
- **scorecard/:** Pure computation -- takes evidence records and produces scores. No side effects. Each dimension is a function: (target, evidence) -> score. The verdict function applies thresholds. Easily testable.
- **llm/:** Already well-structured. Minimal changes: add token tracking and formalize the fallback chain.
- **compliance/:** Upgraded from the existing stage7_lineage.py. Adds hash chains (each audit entry includes SHA-256 of the previous entry) and e-signature capture for HITL approvals.
- **ui/:** Multi-page Streamlit replaces the monolithic app.py. Each page imports from domain services but never from other pages. Components/ holds reusable widgets.

## Architectural Patterns

### Pattern 1: Pipeline-with-Checkpoints

**What:** Each omics pipeline stage reads an AnnData object, transforms it, writes a checkpoint (.h5ad), and returns metadata. The pipeline orchestrator runs stages sequentially, skipping any stage with an existing checkpoint when resuming.

**When to use:** Long-running sequential data processing where intermediate results are valuable and reruns are common.

**Trade-offs:** Checkpoints consume disk (100-500MB per checkpoint for 60K cells). Worth it because pipeline runs take 15-30 minutes, and a crash at stage 5 without checkpoints wastes all progress.

**Example:**
```python
# omics/pipeline.py
class OmicsPipeline:
    def __init__(self, project_id: str, config: PipelineConfig):
        self.project_id = project_id
        self.config = config
        self.checkpoint_dir = Path(f"data/projects/{project_id}/checkpoints")

    def run(self, resume: bool = True) -> PipelineResult:
        """Run all stages, skipping completed ones if resume=True."""
        stages = [
            ("ingest", ingest.run),
            ("harmonize", harmonize.run),
            ("qc", qc.run),
            ("process", process.run),
            ("annotate", annotate.run),
            ("expression", expression.run),
            ("export", export.run),
        ]

        adata = None
        for stage_name, stage_fn in stages:
            checkpoint = self.checkpoint_dir / f"{stage_name}.h5ad"

            if resume and checkpoint.exists():
                adata = ad.read_h5ad(checkpoint)
                continue

            # Record stage start in audit trail
            audit.record_stage_start(self.project_id, stage_name)

            adata, metadata = stage_fn(adata, self.config)
            adata.write_h5ad(checkpoint)

            # Record stage completion
            audit.record_stage_complete(
                self.project_id, stage_name, metadata
            )

            # Check for HITL gate
            gate = hitl.get_gate(stage_name)
            if gate and gate.requires_approval(self.config.mode):
                yield HITLRequest(stage_name, adata, metadata)
                # Pipeline pauses here until UI approves
```

### Pattern 2: Background Task Execution in Streamlit

**What:** Streamlit reruns the entire script on every interaction. Long-running tasks (15-30 min pipelines) must run in a separate thread, with the UI polling for status. Use ThreadPoolExecutor to submit tasks, SQLite to persist state (survives Streamlit reruns), and st.session_state for in-memory caching.

**When to use:** Any operation taking more than 2-3 seconds in a Streamlit app.

**Trade-offs:** Adds complexity (task state machine, polling). But without it, the UI freezes or tasks are lost on rerun. SQLite persistence is critical -- if a user navigates away and returns, the task state must survive.

**Example:**
```python
# core/task_manager.py
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"

# Module-level executor (persists across Streamlit reruns within the same process)
_executor = ThreadPoolExecutor(max_workers=2)

class TaskManager:
    def __init__(self, db_path: str = "data/db/tasks.db"):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def submit(self, task_id: str, fn, *args, **kwargs):
        """Submit a task for background execution."""
        self.db.execute(
            "INSERT OR REPLACE INTO tasks (task_id, status, submitted_at) "
            "VALUES (?, 'pending', datetime('now'))",
            (task_id,)
        )
        self.db.commit()

        def _wrapped():
            try:
                self._update_status(task_id, TaskStatus.RUNNING)
                result = fn(*args, **kwargs)
                self._update_status(task_id, TaskStatus.COMPLETED, result=result)
            except Exception as e:
                self._update_status(task_id, TaskStatus.FAILED, error=str(e))

        _executor.submit(_wrapped)

    def get_status(self, task_id: str) -> dict:
        """Poll task status (called from Streamlit UI on each rerun)."""
        row = self.db.execute(
            "SELECT status, progress_pct, current_stage, error FROM tasks WHERE task_id=?",
            (task_id,)
        ).fetchone()
        if not row:
            return {"status": "not_found"}
        return {
            "status": row[0],
            "progress_pct": row[1],
            "current_stage": row[2],
            "error": row[3],
        }
```

```python
# ui/pages/3_omics_pipeline.py (Streamlit page)
import streamlit as st
from core.task_manager import TaskManager

tm = TaskManager()

# Check if a pipeline is already running
task_id = f"pipeline_{st.session_state.project_id}"
status = tm.get_status(task_id)

if status["status"] == "running":
    st.progress(status["progress_pct"] / 100)
    st.info(f"Running: {status['current_stage']}")
    # Auto-refresh every 3 seconds
    st.rerun()  # Streamlit >= 1.27

elif status["status"] == "awaiting_approval":
    # Show HITL gate
    render_hitl_gate(status["current_stage"])

elif status["status"] == "completed":
    st.success("Pipeline complete!")
    render_results()

elif st.button("Run Pipeline"):
    tm.submit(task_id, pipeline.run, project_id=st.session_state.project_id)
    st.rerun()
```

**Critical detail:** The `st.rerun()` call for polling should use `time.sleep(3)` before `st.rerun()` to avoid hammering the server. Alternatively, use Streamlit's `st.fragment` (introduced in Streamlit 1.33) to create an auto-refreshing fragment that does not rerun the entire page:

```python
@st.fragment(run_every=3)
def pipeline_status():
    status = tm.get_status(task_id)
    if status["status"] == "running":
        st.progress(status["progress_pct"] / 100)
        st.caption(f"Stage: {status['current_stage']}")
```

**Confidence:** MEDIUM -- `st.fragment(run_every=...)` is from Streamlit 1.33+. Verify the exact API before implementation. The ThreadPoolExecutor + SQLite pattern is well-established.

### Pattern 3: Hash-Chained Audit Trail (21 CFR Part 11)

**What:** Every audit entry includes the SHA-256 hash of the previous entry, creating a tamper-evident chain. If any historical entry is modified, the chain breaks and downstream hashes no longer validate. Combined with electronic signatures (user ID + password re-entry + timestamp) at HITL gates.

**When to use:** Regulated environments requiring data integrity proof. 21 CFR Part 11 mandates that electronic records be trustworthy, reliable, and equivalent to paper records.

**Trade-offs:** Adds ~10ms per audit write (SHA-256 computation). Requires user re-authentication at signature points (friction). But this is non-negotiable for FDA-facing use cases.

**Example:**
```python
# compliance/audit_trail.py
import hashlib
import json
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_chain (
    seq_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    event_type  TEXT NOT NULL,       -- 'stage_start', 'stage_complete', 'hitl_approve', etc.
    actor_id    TEXT NOT NULL,       -- user ID or 'system'
    payload     TEXT NOT NULL,       -- JSON: parameters, decisions, metadata
    prev_hash   TEXT NOT NULL,       -- SHA-256 of previous entry (or '0' * 64 for first)
    entry_hash  TEXT NOT NULL        -- SHA-256 of this entry
);

CREATE TABLE IF NOT EXISTS e_signatures (
    sig_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_seq   INTEGER NOT NULL,    -- FK to audit_chain.seq_id
    user_id     TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    meaning     TEXT NOT NULL,       -- 'APPROVED', 'REJECTED', 'REVIEWED'
    reason      TEXT,                -- Free-text justification
    password_hash TEXT NOT NULL,     -- Re-authenticated password hash
    FOREIGN KEY (audit_seq) REFERENCES audit_chain(seq_id)
);
"""

class AuditTrail:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.executescript(SCHEMA)

    def append(self, project_id: str, event_type: str,
               actor_id: str, payload: dict) -> int:
        """Append an entry to the hash chain. Returns seq_id."""
        # Get previous hash
        row = self.conn.execute(
            "SELECT entry_hash FROM audit_chain "
            "WHERE project_id=? ORDER BY seq_id DESC LIMIT 1",
            (project_id,)
        ).fetchone()
        prev_hash = row[0] if row else "0" * 64

        timestamp = datetime.now(timezone.utc).isoformat()

        # Compute entry hash
        content = json.dumps({
            "project_id": project_id,
            "timestamp": timestamp,
            "event_type": event_type,
            "actor_id": actor_id,
            "payload": payload,
            "prev_hash": prev_hash,
        }, sort_keys=True)
        entry_hash = hashlib.sha256(content.encode()).hexdigest()

        cur = self.conn.execute(
            "INSERT INTO audit_chain "
            "(project_id, timestamp, event_type, actor_id, payload, prev_hash, entry_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, timestamp, event_type, actor_id,
             json.dumps(payload), prev_hash, entry_hash)
        )
        self.conn.commit()
        return cur.lastrowid

    def verify_chain(self, project_id: str) -> bool:
        """Verify the entire hash chain for a project. Returns True if intact."""
        rows = self.conn.execute(
            "SELECT * FROM audit_chain WHERE project_id=? ORDER BY seq_id",
            (project_id,)
        ).fetchall()

        prev_hash = "0" * 64
        for row in rows:
            content = json.dumps({
                "project_id": row[1],
                "timestamp": row[2],
                "event_type": row[3],
                "actor_id": row[4],
                "payload": json.loads(row[5]),
                "prev_hash": prev_hash,
            }, sort_keys=True)
            expected = hashlib.sha256(content.encode()).hexdigest()

            if expected != row[7]:  # entry_hash column
                return False
            prev_hash = row[7]

        return True
```

### Pattern 4: Evidence Aggregation (Parallel Fetch + Normalize)

**What:** For each target gene, fetch evidence from 6 external APIs in parallel. Each source returns a normalized EvidenceRecord. Cache responses in SQLite with a configurable TTL (default: 24 hours). Gene alias resolution happens first (e.g., "p53" -> "TP53") so all sources query the canonical symbol.

**When to use:** Whenever you need to gather information from multiple independent external services.

**Trade-offs:** Parallel fetch is faster (6 serial API calls of 2-5s each = 12-30s serial vs 5s parallel) but requires careful error handling -- one source failing must not block others.

**Example:**
```python
# evidence/aggregator.py
from concurrent.futures import ThreadPoolExecutor, as_completed
from evidence.cache import EvidenceCache
from evidence.gene_resolver import resolve_gene

class EvidenceAggregator:
    def __init__(self, sources: list, cache: EvidenceCache):
        self.sources = sources  # List of EvidenceSource instances
        self.cache = cache

    def gather(self, gene_symbol: str, disease_context: str = None) -> dict:
        """Fetch evidence from all sources in parallel."""
        # Step 1: Resolve gene alias to canonical symbol
        canonical = resolve_gene(gene_symbol)

        # Step 2: Check cache
        cached = self.cache.get_all(canonical)
        sources_to_fetch = [
            s for s in self.sources
            if s.name not in cached or cached[s.name].is_expired()
        ]

        # Step 3: Parallel fetch for uncached sources
        results = dict(cached)  # Start with cached
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {
                pool.submit(s.fetch, canonical, disease_context): s
                for s in sources_to_fetch
            }
            for future in as_completed(futures, timeout=30):
                source = futures[future]
                try:
                    evidence = future.result()
                    results[source.name] = evidence
                    self.cache.put(canonical, source.name, evidence)
                except Exception as e:
                    results[source.name] = EvidenceRecord(
                        source=source.name,
                        status="error",
                        error=str(e),
                    )

        return results
```

### Pattern 5: HITL Gate (Propose-Review-Approve)

**What:** At each HITL gate, the system proposes a decision (e.g., "QC thresholds: min_genes=200, max_mt=20%"), presents it to the user with supporting evidence, and waits for approval. The gate has two modes: Exploration (auto-approve, log only) and Compliance (mandatory human approval with e-signature).

**When to use:** Every pipeline decision point that affects scientific or regulatory outcomes.

**Trade-offs:** Compliance mode adds friction (user must review and sign each gate). Exploration mode is faster but produces weaker audit trails. The mode toggle is per-project, set at project creation.

**Example:**
```python
# core/hitl.py
from enum import Enum
from pydantic import BaseModel

class GateMode(Enum):
    EXPLORATION = "exploration"  # Auto-approve, log decision
    COMPLIANCE = "compliance"    # Mandatory human approval + e-signature

class GateStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"        # User changed proposed values

class HITLGate(BaseModel):
    gate_id: str                 # e.g., "qc_thresholds"
    stage: str                   # e.g., "qc"
    title: str
    proposed_values: dict        # What the system suggests
    evidence: dict               # Why (statistical justification)
    status: GateStatus = GateStatus.PENDING
    actual_values: dict = None   # What the user approved (may differ)
    reviewer_id: str = None
    review_comment: str = None
    reviewed_at: str = None

# Nine gates defined for the platform:
GATE_DEFINITIONS = {
    "data_confirmation":    {"stage": "ingest",     "title": "Confirm Dataset Metadata"},
    "harmonization_review": {"stage": "harmonize",  "title": "Review Field Mappings"},
    "qc_thresholds":        {"stage": "qc",         "title": "Approve QC Thresholds"},
    "qc_donor_verdicts":    {"stage": "qc",         "title": "Approve Donor Verdicts"},
    "processing_params":    {"stage": "process",    "title": "Review Processing Parameters"},
    "annotation_review":    {"stage": "annotate",   "title": "Confirm Cell Type Labels"},
    "evidence_review":      {"stage": "evidence",   "title": "Review External Evidence"},
    "scoring_weights":      {"stage": "scorecard",  "title": "Approve Scoring Weights"},
    "final_report":         {"stage": "export",     "title": "Approve Final Report"},
}
```

## Data Flow

### Primary Data Flow: Upload to Report

```
[User uploads .h5ad]
    |
    v
[INGEST] -- validate format, subsample if >100K cells, compute SHA-256
    |
    v
[HARMONIZE] -- map metadata to CDISC schema (fuzzy match + LLM)
    |         -- HITL GATE: review mappings
    v
[QC] -- 5-layer filtering (gene count, mito %, doublet, sex, cell count)
    |   -- HITL GATE: approve thresholds + donor verdicts
    v
[PROCESS] -- normalize -> log1p -> HVG -> PCA -> Harmony -> UMAP -> Leiden
    |       -- HITL GATE: review params, approve UMAP quality
    v
[ANNOTATE] -- CellTypist + marker validation, DE analysis
    |        -- HITL GATE: confirm cell type labels
    v
[EXPRESSION] -- per-gene, per-cell-type expression profiling
    |          -- target gene enrichment analysis
    v
    +----------------------+
    |                      |
    v                      v
[EVIDENCE FETCH]     [INTERNAL EVIDENCE]
  6 APIs in parallel    Expression specificity (tau)
  OpenTargets            Fold enrichment
  DGIdb                  DE significance
  PubMed                 Cell type composition
  ClinicalTrials
  UniProt
  ChEMBL
    |                      |
    +----------+-----------+
               |
               v
[AI REASONING ENGINE] -- 5 modes applied to aggregated evidence
    |   hypothesis: "What biological mechanism explains this pattern?"
    |   synthesis:  "Summarize all evidence for/against this target"
    |   contradict: "What evidence contradicts the hypothesis?"
    |   gap:        "What evidence is missing?"
    |   confidence: "How confident should we be? (1-10)"
    |   -- HITL GATE: review AI reasoning chains
    v
[SCORECARD] -- 7-dimension GOT-IT scoring
    |   1. Genetic association (OpenTargets)
    |   2. Expression specificity (omics tau)
    |   3. Druggability (DGIdb)
    |   4. Literature support (PubMed)
    |   5. Clinical feasibility (ClinicalTrials)
    |   6. Safety signals (ChEMBL)
    |   7. Biological plausibility (AI reasoning)
    |   -- HITL GATE: approve weights, review scores
    v
[VERDICT] -- GO / CONDITIONAL / NO-GO per target
    |
    v
[REPORT GENERATION] -- Target Assessment Dossier (HTML/PDF)
    |                 -- Full audit trail with hash chain verification
    |                 -- HITL GATE: approve for export
    v
[EXPORT] -- Signed dossier with e-signature
```

### State Management Pattern

Streamlit's execution model (full script rerun on interaction) requires careful state management:

```
+----------------------------+     +----------------------------+
|    st.session_state        |     |    SQLite (persistent)     |
|    (in-memory, per-tab)    |     |    (survives reruns)       |
+----------------------------+     +----------------------------+
| - current_page             |     | - project records          |
| - current_project_id       |     | - task status/progress     |
| - llm_provider instance    |     | - HITL gate states         |
| - conversation_history     |     | - audit trail (hash chain) |
| - ui_form_state            |     | - evidence cache           |
| - cached AnnData (small)   |     | - user sessions            |
+----------------------------+     +----------------------------+
         |                                    |
         |  UI reads from session_state       |  Background tasks write to SQLite
         |  for instant rendering             |  UI polls SQLite on each rerun
         +------------------------------------+
```

**Rule:** Anything that must survive a page navigation or browser refresh goes in SQLite. Anything that is ephemeral (form state, cached objects) goes in st.session_state. The task manager bridges both: it writes to SQLite from the background thread, and the UI reads SQLite on each rerun.

### Background Pipeline Flow (detail)

```
User clicks "Run Pipeline"
    |
    v
[UI thread] --> TaskManager.submit(task_id, pipeline.run, ...)
    |                |
    |                v
    |           [ThreadPool worker thread]
    |                |
    |                +-- Updates SQLite: status=running, stage=ingest
    |                +-- Runs ingest stage
    |                +-- Updates SQLite: stage=harmonize
    |                +-- ...
    |                +-- Hits HITL gate: Updates SQLite: status=awaiting_approval
    |                +-- Worker thread BLOCKS on gate.wait_for_approval()
    |
    v
[UI thread] --> polls TaskManager.get_status(task_id) every 3s
    |
    +-- status=running: show progress bar
    +-- status=awaiting_approval: render HITL gate widget
    +-- User clicks "Approve": write approval to SQLite
    |       --> gate.wait_for_approval() unblocks (via SQLite polling or Event)
    +-- status=completed: show results
    +-- status=failed: show error + retry button
```

**Threading safety:** SQLite supports concurrent reads + single writer. The worker thread writes status updates; the UI thread reads them. Use `check_same_thread=False` on the connection. For the HITL gate blocking mechanism, use `threading.Event` with a timeout loop that polls the SQLite approval state.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-5 users (MVP, 8GB RAM) | Single Streamlit process, ThreadPoolExecutor(2), SQLite, local file storage. Current architecture handles this well. Run one pipeline at a time per user. |
| 5-20 users (Small team) | Add Streamlit session isolation (each user gets independent session state). Consider PostgreSQL for audit trail (concurrent writes). Separate evidence cache DB from main DB. May need 16-32GB RAM if multiple pipelines run concurrently. |
| 20+ users (Enterprise) | Extract domain services behind FastAPI. Streamlit becomes thin UI client. PostgreSQL required. Celery or Dramatiq for task queue (replaces ThreadPoolExecutor). Redis for session state. S3/MinIO for h5ad storage. This is a substantial rewrite -- plan for it but do not build it in MVP. |

### Scaling Priorities

1. **First bottleneck: Memory.** A single 60K-cell AnnData object consumes 2-4GB RAM. Two concurrent pipeline runs on 8GB RAM will OOM. Mitigation: enforce single-pipeline-at-a-time via TaskManager, queue additional requests.

2. **Second bottleneck: SQLite write contention.** With multiple concurrent users writing audit entries and task status updates, SQLite's single-writer lock becomes a bottleneck. Mitigation: use WAL mode (`PRAGMA journal_mode=WAL`) for MVP. Migrate to PostgreSQL when concurrent write throughput matters.

3. **Third bottleneck: LLM throughput.** Local Ollama handles one request at a time. Multiple users hitting the AI reasoning engine will queue. Mitigation: Groq/Anthropic cloud fallback for concurrent users. In enterprise, run Ollama with multiple model instances or use vLLM.

## Anti-Patterns

### Anti-Pattern 1: Monolithic Streamlit App

**What people do:** Put all UI logic, business logic, and data access in a single `app.py` file (as in the current bioorchestrator_real/app.py at 1000+ lines).

**Why it is wrong:** Impossible to test business logic without running Streamlit. Changes to one page risk breaking others. CSS, data loading, and domain logic are entangled. Cannot reuse domain logic from CLI or API.

**Do this instead:** Multi-page Streamlit with pages/ directory. Domain logic lives in omics/, evidence/, reasoning/, scorecard/ modules with zero Streamlit imports. UI pages are thin wrappers that call domain functions and display results.

### Anti-Pattern 2: Synchronous Pipeline in Streamlit Main Thread

**What people do:** Run the 15-30 minute omics pipeline directly in the Streamlit script execution. Use `st.spinner()` and hope the browser tab stays open.

**Why it is wrong:** Streamlit has a script execution timeout. Browser tabs disconnect on sleep/lock. Any UI interaction during the run cancels and restarts the script. State is lost.

**Do this instead:** Submit pipeline to ThreadPoolExecutor. Persist state in SQLite. Poll from UI with `st.fragment(run_every=3)`. Pipeline survives page navigation, browser closure, and Streamlit reruns.

### Anti-Pattern 3: Evidence Fetching Without Cache or Timeout

**What people do:** Call external APIs (OpenTargets, PubMed, etc.) directly from the reasoning engine on every LLM tool call. No caching, no timeout, no retry.

**Why it is wrong:** The AI reasoning engine may call the same evidence source 3-5 times in a single reasoning session (across 10 ReAct rounds). Rate limits hit quickly. A slow API blocks the entire reasoning chain. API downtime breaks the pipeline.

**Do this instead:** Evidence cache (SQLite, 24h TTL) sits between the reasoning engine and external APIs. First check cache, then fetch. Timeout at 10s per API. Return partial results with error flags rather than failing entirely.

### Anti-Pattern 4: Hardcoded Domain Knowledge

**What people do:** Embed specific genes (GIPR, GLP1R), tissues (adipose), and diseases (obesity) directly in pipeline code, scoring logic, and UI labels. (Current codebase does this extensively.)

**Why it is wrong:** Every new engagement requires forking or heavily modifying the code. Disease-specific assumptions leak into QC thresholds, annotation models, and scoring weights. Makes the platform useless for any disease other than the one it was built for.

**Do this instead:** All disease/tissue/gene specificity lives in project configuration (config.py or per-project JSON). Pipeline stages, scoring dimensions, and UI components are parameterized. The only place disease-specific knowledge belongs is in the AI system prompts (reasoning/prompts.py) and those are configurable per project.

### Anti-Pattern 5: Mutable Audit Records

**What people do:** Use UPDATE statements on audit trail records. Allow deletion of log entries. Store audit data in the same database as operational data.

**Why it is wrong:** 21 CFR Part 11 requires that electronic records cannot be modified after creation. Auditors look for tamper evidence. If audit records can be UPDATEd, the entire trail is suspect.

**Do this instead:** Append-only audit trail with hash chains. No UPDATE or DELETE on audit tables. Separate audit database file from operational database. Chain verification function to detect tampering. The operational database (projects, task state, cache) can be mutable; the audit trail cannot.

## Integration Points

### External Services

| Service | Integration Pattern | Rate Limits | Notes |
|---------|---------------------|-------------|-------|
| OpenTargets | GraphQL (genetics.opentargets.org) | None published, be respectful | Best source for genetic association scores. Query by Ensembl gene ID. |
| DGIdb | GraphQL (dgidb.org/api/graphql) | None published | Druggability scores, drug-gene interactions. Query by gene symbol. |
| PubMed | REST via Bio.Entrez (eutils.ncbi.nlm.nih.gov) | 3 req/s without API key, 10 req/s with | Literature evidence. Always set Entrez.email. Use API key for production. |
| ClinicalTrials.gov | REST v2 (clinicaltrials.gov/api/v2) | 200 requests/min per IP | Clinical pipeline status for targets. Filter by gene symbol + condition. |
| UniProt | REST (rest.uniprot.org) | None published | Protein function, subcellular location, tissue expression. Query by gene symbol. |
| ChEMBL | REST (www.ebi.ac.uk/chembl/api/data) | None published | Bioactivity data, known compounds against target. Query by target ID. |
| MyGene.info | REST (mygene.info/v3) | 1000 req/15min | Gene alias resolution. Call first before querying other sources. |
| Ollama | Local HTTP (localhost:11434) | Limited by GPU/CPU | Local LLM inference. One request at a time per model. |
| Groq | REST (api.groq.com) | 30 req/min free tier | Cloud LLM fallback. Fast inference (Llama 3.3 70B). |
| Anthropic | REST (api.anthropic.com) | Pay-per-token | Premium LLM option. Best reasoning quality. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| UI <-> Domain Services | Direct Python imports | UI pages import from omics/, evidence/, etc. No REST API for MVP. FastAPI extraction path for v2. |
| Domain Services <-> Data Layer | SQLite via shared connection | Use connection pooling pattern. WAL mode for concurrent reads. |
| Task Manager <-> Pipeline | ThreadPoolExecutor submit/result | Worker thread runs pipeline. UI thread polls SQLite for status. |
| HITL Gates <-> UI | SQLite state + threading.Event | Gate writes "awaiting_approval" to SQLite. UI renders widget. User approval writes to SQLite + signals Event. |
| Reasoning Engine <-> Evidence | Evidence Aggregator API | Reasoning tools call aggregator.gather(gene). Aggregator handles caching, parallel fetch, error recovery. |
| Reasoning Engine <-> LLM | LLM Provider abstraction | Reasoning engine calls provider.chat_with_tools(). Provider handles Ollama/Groq/Anthropic differences. |
| Scorecard <-> Evidence + Omics | Pure function calls | Scorecard.score(target, evidence_records, omics_results) -> Score. No side effects. Fully testable. |
| Compliance <-> Everything | Audit trail append calls | Every component calls audit.append() at decision points. Compliance module is write-only from their perspective. |

## Build Order and Dependencies

The following dependency graph determines build order. Items higher in the list must be built before items that depend on them.

```
Phase 1: Foundation (no dependencies)
  core/models.py          -- Shared data models (everything depends on these)
  core/auth.py            -- User authentication (compliance depends on this)
  compliance/audit_trail.py -- Hash-chained audit trail (everything logs here)
  config.py               -- Disease-agnostic configuration schema

Phase 2: Orchestration (depends on Phase 1)
  core/task_manager.py    -- Background task execution
  core/hitl.py            -- HITL gate framework
  llm/provider.py         -- LLM abstraction (clean up existing)

Phase 3: Omics Pipeline (depends on Phases 1-2)
  omics/ingest.py         -- Refactor from stage1_ingest.py
  omics/harmonize.py      -- Refactor from stage2_harmonize.py
  omics/qc.py             -- Refactor from stage3_qc.py
  omics/process.py        -- Refactor from stage4_process.py
  omics/annotate.py       -- Refactor from stage5_annotate.py
  omics/expression.py     -- New: general expression profiling
  omics/pipeline.py       -- Pipeline orchestrator (replaces run_pipeline.py)

Phase 4: Evidence Integration (depends on Phase 1, parallel with Phase 3)
  evidence/cache.py       -- SQLite caching layer
  evidence/gene_resolver.py -- Gene alias resolution
  evidence/sources/*.py   -- 6 API source modules
  evidence/aggregator.py  -- Parallel fetch orchestrator

Phase 5: Intelligence (depends on Phases 3-4)
  reasoning/tools.py      -- Tool definitions (queries omics + evidence)
  reasoning/prompts.py    -- System prompts per reasoning mode
  reasoning/react_loop.py -- ReAct tool-calling loop
  reasoning/engine.py     -- 5-mode reasoning orchestrator
  scorecard/dimensions.py -- Individual dimension calculators
  scorecard/framework.py  -- 7-dimension GOT-IT scoring
  scorecard/verdict.py    -- GO / CONDITIONAL / NO-GO

Phase 6: Presentation (depends on Phases 1-5)
  ui/components/*.py      -- Reusable widgets (HITL, progress, charts)
  ui/pages/1_login.py     -- Login page
  ui/pages/2_project_setup.py
  ui/pages/3_omics_pipeline.py
  ui/pages/4_evidence.py
  ui/pages/5_ai_reasoning.py
  ui/pages/6_scorecard.py
  ui/pages/7_audit_trail.py
  compliance/report_generator.py -- Dossier generation (needs all data)
```

**Build order rationale:**
- **Phase 1 first** because every other module imports core models, writes audit entries, and reads config. Without these, nothing can be built properly.
- **Phase 2 before 3** because the omics pipeline needs task_manager for background execution and hitl.py for gate definitions. Without orchestration, the pipeline would be synchronous-only.
- **Phase 3 and 4 in parallel** because omics processing and evidence fetching are independent. A developer working on evidence APIs does not need the omics pipeline, and vice versa. They only converge in Phase 5 (reasoning/scorecard).
- **Phase 5 after 3 and 4** because the reasoning engine queries both omics results and external evidence. The scorecard requires evidence records from all sources. These cannot be built until their data sources exist.
- **Phase 6 last** because UI pages are thin wrappers around domain services. Building UI before the services exist leads to mock-heavy code that must be rewritten. Exception: build a minimal "skeleton" UI in Phase 2 to test task_manager and HITL gates.

## Migration Path from Existing Codebase

| Existing File | Target Module | Key Changes |
|---------------|---------------|-------------|
| `pipeline/stage1_ingest.py` | `omics/ingest.py` | Support multiple formats (.h5ad, .h5, 10x), remove CellxGene-specific code |
| `pipeline/stage2_harmonize.py` | `omics/harmonize.py` | Already well-structured, minimal changes |
| `pipeline/stage3_qc.py` | `omics/qc.py` | Remove hardcoded donor references, make thresholds fully configurable |
| `pipeline/stage4_process.py` | `omics/process.py` | Already parameterized, add SoupX ambient RNA step |
| `pipeline/stage5_annotate.py` | `omics/annotate.py` | Remove _gipr_glp1r_analysis, replace with generic target expression profiling |
| `pipeline/stage6_export.py` | `omics/export.py` | Decouple from specific plot filenames |
| `pipeline/stage7_lineage.py` | `compliance/audit_trail.py` | Add hash chains, e-signatures, separate from operational DB |
| `utils/llm_provider.py` | `llm/provider.py` | Already clean, add token tracking + logging |
| `utils/ai_copilot.py` | `reasoning/engine.py` + `reasoning/tools.py` | Split tools from engine, make disease-agnostic, increase to 10 rounds |
| `utils/data_queries.py` | `reasoning/tools.py` | Make queries parameterized (not hardcoded genes) |
| `utils/plotting.py` | `ui/components/charts.py` | Remove hardcoded gene/tissue references |
| `config.py` | `config.py` | Rewrite as disease-agnostic with per-project overrides |
| `app.py` | `ui/pages/*.py` + `ui/components/*.py` | Split 1000+ line monolith into 7 pages + reusable components |

## Sources

- **Existing codebase analysis**: All architecture patterns derived from reading bioorchestrator_real/ source code (HIGH confidence)
- **Streamlit execution model**: Based on training data knowledge of Streamlit's rerun model, ThreadPoolExecutor pattern, and st.fragment API. `st.fragment(run_every=...)` introduced in Streamlit 1.33 (MEDIUM confidence -- verify exact API)
- **21 CFR Part 11 compliance**: Based on training data knowledge of FDA electronic records regulation. Hash chain pattern is well-established in audit trail design. E-signature requirements (unique user ID + password + meaning) from 21 CFR 11.50 and 11.100 (MEDIUM confidence -- verify against current FDA guidance document)
- **GOT-IT framework**: Referenced in PROJECT.md as published in Nature Reviews Drug Discovery 2021. Scoring dimensions based on the framework (MEDIUM confidence -- verify publication for exact dimension definitions)
- **OpenTargets, DGIdb, PubMed, ClinicalTrials.gov, UniProt, ChEMBL APIs**: Based on training data knowledge of public bioinformatics APIs. Rate limits and endpoints should be verified against current documentation before implementation (MEDIUM confidence)

---
*Architecture research for: AI-Powered Drug Target Intelligence Platform*
*Researched: 2026-05-09*
