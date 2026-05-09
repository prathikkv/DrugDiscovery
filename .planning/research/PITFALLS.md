# Pitfalls Research

**Domain:** AI-powered pharma bioinformatics platform (scRNA-seq + evidence APIs + LLM reasoning + GxP compliance)
**Project:** BioOrchestrator v2 — Drug Target Intelligence Platform
**Researched:** 2026-05-09
**Confidence:** MEDIUM (codebase analysis = HIGH, domain patterns = MEDIUM, regulatory specifics = LOW-MEDIUM without official verification)

---

## Critical Pitfalls

Mistakes that cause rewrites, lost months, or product failure.

---

### Pitfall 1: Streamlit Script Rerun Model Kills Long-Running Pipelines

**What goes wrong:**
Streamlit re-executes the entire Python script from top to bottom on every user interaction (button click, slider change, text input). A Scanpy pipeline processing 60K cells takes 15-45 minutes. If a user clicks anything while the pipeline runs -- or even switches browser tabs and returns -- the pipeline restarts from scratch.

**How to avoid:**
- Never run compute-heavy work in the Streamlit process. Use `ThreadPoolExecutor` or `subprocess` to spawn pipeline execution in a separate process.
- Persist pipeline state to SQLite (not `st.session_state`). On each rerun, poll the database for status.
- Use the pattern: submit job -> write job ID to DB -> poll DB on rerun -> display results when complete.
- Consider `st.fragment` (Streamlit 1.33+) for partial reruns of specific UI sections.

**Warning signs:**
- Pipeline appears to "hang" in the UI but CPU shows no activity (it restarted)
- Users report losing progress when interacting with sidebar controls
- Duplicate checkpoint files or partial results in the output directory

**Phase to address:** Phase 1 (Foundation)

**Confidence:** MEDIUM

---

### Pitfall 2: SQLite Concurrent Write Deadlocks Under Streamlit Threading

**What goes wrong:**
SQLite allows only one writer at a time. When a background `ThreadPoolExecutor` thread writes pipeline stage results while the Streamlit UI thread reads from the same DB, you get `sqlite3.OperationalError: database is locked`. The existing `LineageDB.__init__` in `stage7_lineage.py` calls `sqlite3.connect()` without configuring WAL mode, timeout, or check_same_thread.

**How to avoid:**
- Enable WAL mode: `conn.execute("PRAGMA journal_mode=WAL")`.
- Set busy timeout: `conn.execute("PRAGMA busy_timeout=5000")`.
- Use `check_same_thread=False` when passing connections across threads.
- Create separate connection objects per thread.
- For the evidence cache, consider a separate SQLite file from the lineage DB.

**Phase to address:** Phase 1 (Foundation)

**Confidence:** HIGH

---

### Pitfall 3: Hardcoded Biology Prevents Disease-Agnostic Reuse

**What goes wrong:**
GIPR, GLP1R, MariTide, adipose tissue, and obesity-specific logic in 8+ files: `config.py` (MARITIDE_GENES), `stage5_annotate.py` (GIPR enrichment), `ai_copilot.py` (MariTide system prompt), `data_queries.py`, and plotting utilities.

**How to avoid:**
- Refactor in one focused sprint. Create a `project_config` dataclass with target genes, tissue type, disease context, reference markers.
- Keep the existing MariTide config as a "preset" JSON file.
- AI copilot system prompt must be template-based with `{target_genes}`, `{disease_context}`, `{tissue_type}` placeholders.
- Write a "golden test" for the adipose demo before AND after refactoring.

**Phase to address:** Phase 1 (Foundation)

**Confidence:** HIGH

---

### Pitfall 4: "21 CFR Part 11 Compliant" Without Actually Being Compliant

**What goes wrong:**
Current lineage DB lacks: hash-chain integrity, electronic signatures with meaning, access controls, audit trail immutability, system validation documentation. Claiming compliance without these creates legal liability.

**How to avoid:**
- Hash chain: Each audit record includes `sha256(previous_record_hash + current_record_data)`.
- E-signatures: Require re-authentication at HITL gates with meaning ("I have reviewed and approve").
- Immutability: INSERT-only tables. Never UPDATE/DELETE audit records.
- RBAC: Scientist (run analysis), Reviewer (approve results), Administrator (manage users).
- Say "21 CFR Part 11 aligned" not "compliant" until organizational procedures exist.

**Phase to address:** Phase 2 (Compliance Infrastructure)

**Confidence:** MEDIUM

---

### Pitfall 5: LLM Hallucination in Scientific Reasoning Destroys Trust

**What goes wrong:**
AI generates plausible-sounding biological claims that are factually wrong. In target assessment, a hallucinated claim could lead to incorrect GO/NO-GO decisions.

**How to avoid:**
- Every LLM claim must be grounded to a specific evidence source with `[Source: OpenTargets]` citations.
- Store raw API response JSON alongside LLM's interpretation for side-by-side comparison.
- Scoring must be deterministic (weighted formula on evidence data). LLM explains; it does not calculate.
- Rate-limit ReAct loop to 5 rounds for local models.
- Add "Reasoning Trace" view showing each step.

**Phase to address:** Phase 4 (AI Reasoning)

**Confidence:** MEDIUM

---

### Pitfall 6: Ambient RNA Contamination Invalidating Cell Type Annotations

**What goes wrong:**
In snRNA-seq, ambient mRNA contaminates all droplets. Without correction, CellTypist may misannotate cells. The GIPR enrichment in pericytes could be an artifact.

**How to avoid:**
- Add SoupX as mandatory QC stage between ingest and standard QC.
- For CellxGene Census data, implement contamination estimate using marker gene leakage.
- Make ambient RNA removal configurable but default ON.
- Record contamination fraction in audit trail.

**Phase to address:** Phase 1 (Omics Pipeline)

**Confidence:** HIGH

---

### Pitfall 7: Scoring Framework Without Validation Produces Meaningless Numbers

**What goes wrong:**
Without validation against known outcomes, scoring weights are arbitrary. If EGFR scores lower than a random gene, the framework is worse than useless.

**How to avoid:**
- Build retrovalidation suite FIRST with 10-20 known target-disease pairs.
- Adjust weights until approved targets consistently score higher than failed targets.
- Make weights configurable per therapeutic area.
- Display individual dimension scores alongside composite.
- Include data coverage indicators.

**Phase to address:** Phase 5 (Scoring)

**Confidence:** LOW (needs GOT-IT paper verification)

---

### Pitfall 8: Solo Developer Without Test Infrastructure

**What goes wrong:**
Zero tests in current codebase. In 12-week timeline with massive refactoring, silent regressions are guaranteed.

**How to avoid:**
- "Test the contract" philosophy: 2-3 tests per pipeline stage on tiny synthetic dataset (5 cells, 10 genes).
- Create 50-cell synthetic h5ad fixture that runs full pipeline in <10 seconds.
- Use `pytest` with `conftest.py` fixtures. Add `mypy --strict` for new code.
- Record API responses as JSON fixtures for evidence testing.
- Set up GitHub Actions: `pytest + mypy`.

**Phase to address:** Phase 1 (Foundation, Week 1)

**Confidence:** HIGH

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **OpenTargets GraphQL** | Fetching all associations (50K+ rows) | Use pagination, filter by `score > 0.1`, cache aggressively |
| **PubMed (Bio.Entrez)** | Not setting email/api_key, IP-banned | Set `Entrez.email` + API key. Batch fetch abstracts |
| **ClinicalTrials.gov v2** | Using deprecated v1 API | Use `/v2/studies`, `pageSize=100`, follow `nextPageToken` |
| **DGIdb GraphQL** | Treating all interactions equally | Filter `interactionScore > 0.5`, require 2+ publications |
| **UniProt REST** | Fetching full entries | Use `fields` parameter, reduce response by 90% |
| **ChEMBL REST** | Querying by gene name | Resolve gene -> UniProt ID -> ChEMBL target ID first |

---

## Performance Traps

| Trap | Prevention | When It Breaks |
|------|------------|----------------|
| Loading full h5ad on every Streamlit rerun | Use `@st.cache_resource`, extract summaries to SQLite | 30K cells on 8GB RAM |
| Synchronous API calls to 6 sources | Use `ThreadPoolExecutor` for parallel fetch + cache | First real user interaction |
| Base64 plots in JSON | Store as files, serve via `st.image(path)` | 10+ pipeline runs |
| CellxGene Census re-download | Cache by filter hash | Second project, same tissue |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Streamlit rerun model | Phase 1: Foundation | Pipeline completes while user interacts; browser refresh shows correct status |
| SQLite concurrency | Phase 1: Foundation | Concurrent read+write without "database is locked" across 10 runs |
| Hardcoded biology | Phase 1: Foundation | Run pipeline with lung config, no GIPR/MariTide in output |
| 21 CFR Part 11 | Phase 2: Compliance | Modify record in SQLite, hash chain detects tampering |
| LLM hallucination | Phase 4: AI Reasoning | 10-question adversarial test, all responses cite sources |
| Ambient RNA | Phase 1: Omics Pipeline | SoupX on test data, compare annotations pre/post correction |
| Scoring validation | Phase 5: Scoring | EGFR in top 3 for NSCLC, failed targets score below approved |
| No tests | Phase 1: Foundation | pytest in CI, synthetic h5ad runs pipeline in <10s |

---
*Pitfalls research for: BioOrchestrator v2*
*Researched: 2026-05-09*
