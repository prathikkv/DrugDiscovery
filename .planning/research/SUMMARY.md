# Research Summary

**Project:** BioOrchestrator v2 — Drug Target Intelligence Platform
**Synthesized:** 2026-05-09
**Sources:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md

---

## Executive Summary

BioOrchestrator v2 is a brownfield project extending an existing Scanpy scRNA-seq pipeline into an enterprise drug target intelligence platform. Research across 4 dimensions (stack, features, architecture, pitfalls) reveals a clear path: the core bio-stack is solid and needs version upgrades (not rewrites), the competitive white space is real (nobody combines proprietary omics + public evidence + AI reasoning + consulting dossiers), and the architectural patterns for long-running Streamlit workflows are well-understood. The biggest risks are not technical but operational: solo developer without tests, compliance claims without authentication, and a scoring framework without validation data.

---

## Key Findings

### Stack
- **Python 3.11, numpy 1.26.4 (NOT 2.x)** — critical version pins for bio-stack compatibility
- **Scanpy 1.12.1, anndata 0.11.4, celltypist 1.7.1** — safe upgrades from current versions
- **harmonypy 0.0.10** — stay put, v2.0.0 is a breaking rewrite
- **httpx + gql** — new additions for parallel evidence API calls (OpenTargets GraphQL, 6 REST sources)
- **Keep custom LLM provider** — LangChain/LlamaIndex add 200MB+ bloat with no benefit on 8GB RAM
- **fpdf2 for PDF dossiers** — pure Python, no system dependencies (unlike weasyprint)
- **structlog for GxP logging** — JSON-structured logs complement SQLite audit trail
- **tenacity for API retry** — exponential backoff essential for 6 external APIs

### Features
- **16 table stakes features** across evidence integration, data quality, deliverables, and analytics
- **13 differentiators** — top 3: AI reasoning with transparent chains, proprietary scRNA-seq integration, automated consulting dossiers
- **8 anti-features** scoped out: no LIMS, no real-time collab, no chemistry, no patent automation
- **White space confirmed**: No platform combines client proprietary omics + public evidence + AI reasoning + consulting deliverables
- **Pharma VP decision hierarchy**: genetic evidence first, then expression, druggability, safety, competitive landscape, clinical precedent — maps to our 7-dimension framework

### Architecture
- **6-layer architecture**: Presentation (Streamlit) → Orchestration (TaskManager, HITL) → Domain Services (omics, evidence, reasoning, scorecard) → Cross-cutting (LLM, compliance, auth) → Data (SQLite, file store)
- **Background execution pattern**: ThreadPoolExecutor + SQLite task state + `st.fragment` polling — proven pattern for Streamlit long-running workflows
- **Build order is dependency-driven**: Foundation → Orchestration → Domain services (omics & evidence parallelizable) → Intelligence (reasoning, scorecard) → UI pages
- **Migration path clear**: 12 existing files map cleanly to new module structure

### Pitfalls (Top 8)
1. **Streamlit reruns kill pipelines** — must use background threads from day one
2. **SQLite deadlocks** — WAL mode + busy_timeout required before any concurrent access
3. **Hardcoded biology in 8+ files** — refactor in one focused sprint, not incrementally
4. **False compliance claims** — say "aligned" not "compliant" until auth + hash chains exist
5. **LLM hallucination** — scoring must be deterministic formula, not LLM-computed
6. **Ambient RNA contamination** — SoupX before CellTypist, or annotations are unreliable
7. **Unvalidated scoring** — build retrovalidation suite before finalizing weights
8. **Zero tests** — pytest + synthetic h5ad fixture in Week 1

---

## Roadmap Implications

### Recommended Phase Structure (6 phases)

| Phase | Focus | Dependencies | Research Flags |
|-------|-------|-------------|---------------|
| **1. Foundation** | Models, auth, audit trail, task manager, config, test infra | None | Streamlit threading pattern needs validation |
| **2. Omics Pipeline** | Disease-agnostic refactor, ambient RNA, QC, pipeline with progress callbacks | Phase 1 | SoupX via rpy2 may need R installation |
| **3. Evidence Integration** | 6 external APIs, caching, gene resolver, aggregator | Phase 1 | API rate limits need live testing |
| **4. AI Reasoning** | 5 modes, ReAct loop, tool definitions, provenance | Phases 2 + 3 | qwen3:8b tool-calling reliability unknown |
| **5. Scoring + Dossier** | 7-dimension framework, retrovalidation, PDF/HTML reports | Phases 3 + 4 | GOT-IT dimension weights need calibration |
| **6. UI + Polish** | 7 Streamlit pages, HITL gates, demo project, E2E testing | All phases | Demo must be 30 min max |

### Critical Path
Phase 1 (Foundation) → Phase 2+3 (parallel: Omics + Evidence) → Phase 4 (AI Reasoning) → Phase 5 (Scoring) → Phase 6 (UI)

### Research Flags for Phase Planning
- **Phase 1**: Verify `st.fragment(run_every=N)` API against current Streamlit docs
- **Phase 3**: Test actual API rate limits for all 6 evidence sources before committing to architecture
- **Phase 4**: Empirically test qwen3:8b tool-calling with scientific queries before relying on it
- **Phase 5**: Verify GOT-IT framework dimensions against the actual Nature Reviews Drug Discovery paper
- **Phase 5**: Collect 10-20 known target-disease pairs for retrovalidation before finalizing scoring weights

---

## Confidence Assessment

| Dimension | Confidence | Key Uncertainty |
|-----------|-----------|-----------------|
| Stack | HIGH | harmonypy 2.0 changelog, Plotly 6/Streamlit compat |
| Features | MEDIUM | PandaOmics 2026 features unknown, buyer validation needed |
| Architecture | MEDIUM-HIGH | st.fragment API needs verification, SQLite WAL scale limits |
| Pitfalls | MEDIUM | FDA 21 CFR Part 11 current guidance, GOT-IT weight calibration |

**Overall: MEDIUM-HIGH** — stack and architecture are well-understood; feature prioritization and scoring validation carry the most uncertainty.

---

## Gaps Requiring Resolution

1. **Retrovalidation dataset**: Need 10-20 known target-disease pairs before Phase 5 scoring
2. **First customer identification**: Business validation parallel to technical build
3. **FDA guidance verification**: Current 21 CFR Part 11 interpretation for AI/ML tools
4. **CellTypist model mapping**: Tissue-to-model mapping for 10+ tissue types
5. **Demo runtime budget**: Pre-compute most results for 30-min demo constraint

---
*Research synthesized: 2026-05-09*
*Sources: 4 parallel researcher agents (Opus model)*
