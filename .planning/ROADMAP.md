# Roadmap: BioOrchestrator v2 — Drug Target Intelligence Platform

## Overview

This roadmap transforms the existing BioOrchestrator scRNA-seq pipeline into a consulting-ready Drug Target Intelligence Platform. The journey starts with infrastructure (auth, compliance, execution model), then builds the three analytical pillars in dependency order (omics, evidence, AI reasoning), layers scoring and reporting on top, integrates everything into a polished UI, and closes with validation against known targets. The critical path is Foundation then Omics+Evidence (parallelizable) then AI Reasoning then Scoring then Deliverables then UI then Validation. Eight phases cover all 58 requirements at comprehensive depth.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Auth, compliance infrastructure, execution model, config system, and test scaffolding
- [x] **Phase 2: Omics Pipeline** - Disease-agnostic scRNA-seq pipeline with ambient RNA removal, configurable QC, DE, and annotation
- [x] **Phase 3: Evidence Integration** - Six external API integrations with caching, gene resolution, and parallel fetching
- [ ] **Phase 4: AI Reasoning Engine** - Multi-mode reasoning orchestrator with tool-calling, provenance, and hallucination safeguards
- [ ] **Phase 5: Target Scoring** - Seven-dimension scoring framework with decision thresholds and comparative assessment
- [ ] **Phase 6: Deliverables** - Target Assessment Dossier generation with interactive visualizations and chart export
- [ ] **Phase 7: UI Integration** - Seven-page Streamlit app with HITL gates, design system, and demo project
- [ ] **Phase 8: Validation + Launch** - Golden test retrovalidation, three-tier testing, GxP documentation, and deployment

## Phase Details

### Phase 1: Foundation
**Goal**: The platform has a secure, compliant, and observable infrastructure that all subsequent phases build upon -- users can authenticate, actions are audited, and long-running work executes safely in the background.
**Depends on**: Nothing (first phase)
**Requirements**: REQ-501, REQ-502, REQ-503, REQ-504, REQ-505, REQ-506, REQ-507, REQ-508, REQ-602, REQ-603, REQ-604, REQ-605, REQ-805
**Success Criteria** (what must be TRUE):
  1. A user can create an account, log in with email/password, and be assigned a role (admin, analyst, or reviewer) -- account locks after 5 failed attempts
  2. Every state-changing action (create project, approve gate, modify config) produces an append-only audit record with hash-chain integrity that detects tampering if a record is modified directly in SQLite
  3. A long-running task (simulated 30-second job) completes successfully in the background while the user navigates other Streamlit pages, and task state survives a browser refresh
  4. A project can be created, listed, opened, and deleted, with each operation logged in the audit trail
  5. Running `pytest` executes at least one test using a synthetic h5ad fixture (50 cells, 10 genes) in under 10 seconds
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Foundation infrastructure (config, DB utilities, Streamlit config) and authentication module (bcrypt, RBAC, lockout)
- [x] 01-02-PLAN.md — 21 CFR Part 11 audit trail with hash chains, electronic signatures, and background task execution engine
- [x] 01-03-PLAN.md — Project CRUD with audit integration, Streamlit app shell, and test suite with synthetic h5ad fixture

### Phase 2: Omics Pipeline
**Goal**: Scientists can upload any tissue type's scRNA-seq data and run a complete, disease-agnostic analysis pipeline -- from ingestion through QC, processing, annotation, and differential expression -- with no hardcoded biology.
**Depends on**: Phase 1
**Requirements**: REQ-101, REQ-102, REQ-103, REQ-104, REQ-105, REQ-106, REQ-107, REQ-108, REQ-109, REQ-110
**Success Criteria** (what must be TRUE):
  1. A user can upload .h5ad, .h5 (CellRanger HDF5), or a 10x folder and the system ingests it into the pipeline without errors -- no references to GIPR, GLP1R, adipose, or MariTide appear anywhere in pipeline output
  2. The pipeline applies ambient RNA correction (SoupX) before cell type annotation, with a HITL gate allowing the user to skip with a recorded warning
  3. A user can set tissue-specific QC thresholds (e.g., max_mito=5% for brain, 25% for tumor) at project setup, and the pipeline applies those thresholds instead of defaults
  4. The pipeline produces differential expression results with adjusted p-values, gene set enrichment per cell type, and CellTypist annotations validated against canonical markers -- all viewable as structured output
  5. Pipeline stages report progress to the TaskManager and save checkpoints, so a resumed project picks up from the last completed stage rather than restarting
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md — Pipeline config with tissue defaults, multi-format ingestion, configurable QC, checkpointing, and progress tracking
- [x] 02-02-PLAN.md — Processing pipeline (normalize through Leiden), CellTypist annotation with tissue-aware models, ambient RNA removal, and differential expression
- [x] 02-03-PLAN.md — Gene set enrichment via gseapy, pipeline orchestrator with checkpoint resume, and test suite

### Phase 3: Evidence Integration
**Goal**: The platform can fetch, cache, and aggregate structured evidence from six external sources for any gene target, presenting a unified evidence profile that feeds downstream AI reasoning and scoring.
**Depends on**: Phase 1 (can run in parallel with Phase 2)
**Requirements**: REQ-201, REQ-202, REQ-203, REQ-204, REQ-205, REQ-206, REQ-207, REQ-208, REQ-209, REQ-210, REQ-211
**Success Criteria** (what must be TRUE):
  1. Given a gene symbol (e.g., EGFR) and disease context (e.g., NSCLC), the platform fetches evidence from all six sources (OpenTargets, DGIdb, PubMed, ClinicalTrials.gov, UniProt, ChEMBL) and returns structured results within 60 seconds
  2. A second query for the same gene within 24 hours returns cached results instantly (under 2 seconds) without hitting external APIs, and the cache can be manually invalidated
  3. Ambiguous gene names (e.g., PD-L1, HER2) resolve to canonical identifiers (CD274, ERBB2) via MyGene.info with local alias fallback, before any API queries are dispatched
  4. When an external API is unavailable, the system retries 3 times with exponential backoff, falls back to cached data if available, and returns evidence with confidence=0.0 and a visible flag rather than failing the entire query
  5. Each evidence source implements a common interface (source_name, source_version, fetch, is_available) making it straightforward to add a seventh source without modifying the aggregator
**Plans**: 4 plans

Plans:
- [x] 03-01-PLAN.md — Evidence models, Protocol interface, SQLite cache with TTL, and gene alias resolver
- [x] 03-02-PLAN.md — OpenTargets GraphQL, DGIdb GraphQL, and PubMed/Entrez evidence sources
- [x] 03-03-PLAN.md — ClinicalTrials.gov v2 REST, UniProt REST, and ChEMBL evidence sources
- [x] 03-04-PLAN.md — Evidence aggregator (parallel fetch orchestrator) and test suite

### Phase 4: AI Reasoning Engine
**Goal**: The platform can apply structured AI reasoning across omics and evidence data -- generating hypotheses, synthesizing findings, identifying contradictions, flagging gaps, and assessing confidence -- with every claim traceable to its source data.
**Depends on**: Phase 2, Phase 3
**Requirements**: REQ-301, REQ-302, REQ-303, REQ-304, REQ-305, REQ-306, REQ-307, REQ-308
**Success Criteria** (what must be TRUE):
  1. A user can trigger each of the five reasoning modes (hypothesis, synthesis, contradiction, gap, confidence) for a target gene, and each mode produces a distinct, structured output that addresses its specific analytical purpose
  2. The reasoning engine uses Ollama native tool-calling to query omics data and evidence APIs (14+ tool definitions), completing within 10 tool rounds, with each tool call and its result visible in a reasoning trace
  3. Every AI-generated claim includes a citation to a specific tool call result (e.g., "[Source: OpenTargets]"), and claims with confidence above 0.8 are backed by 3 or more independent sources
  4. AI output records include full provenance: model name, prompt version (SHA256), input evidence hashes, tools used, and the complete reasoning chain -- all stored in the audit trail
  5. If the primary LLM (Ollama qwen3:8b) fails, the system falls back to Groq then Anthropic, logging each fallback event, and evidence exceeding 8K tokens is automatically summarized to fit context windows
**Plans**: 3 plans

Plans:
- [ ] 04-01-PLAN.md — Reasoning data models (6 Pydantic models), 14 LLM tool definitions, versioned prompt registry, and token manager
- [ ] 04-02-PLAN.md — Fallback chain (Ollama/Groq/Anthropic), tool executor (14 dispatchers), agentic tool-calling loop (10-round), and provenance tracker
- [ ] 04-03-PLAN.md — Multi-mode reasoning engine orchestrator, hallucination checker, and comprehensive test suite (26+ tests)

### Phase 5: Target Scoring
**Goal**: The platform produces a quantitative, defensible GO/CONDITIONAL/NO-GO recommendation for each target gene based on a published scoring framework, with transparent dimension-level scores that a pharma VP can interrogate.
**Depends on**: Phase 3, Phase 4
**Requirements**: REQ-401, REQ-402, REQ-403, REQ-404, REQ-405, REQ-406
**Success Criteria** (what must be TRUE):
  1. Each target gene receives a composite score (0-100) computed deterministically from 7 dimensions (genetic evidence, expression biology, druggability, safety/selectivity, competitive landscape, clinical/translational, literature consensus) with 24 sub-scores -- the LLM explains but does not calculate
  2. Decision thresholds are applied automatically: GO for scores 75 or above, CONDITIONAL for 50-74, NO-GO below 50 -- and dimension minimums can force a CONDITIONAL even when the composite exceeds 75
  3. A user can adjust dimension weights at the HITL-009 gate and immediately see how the composite score and recommendation change
  4. For a project with 3-20 target genes, the user can view a side-by-side comparative scorecard with radar charts showing each target's dimension profile
  5. Contradictory evidence in the literature dimension applies a penalty (up to -4 points), visible in the score breakdown
**Plans**: 2 plans

Plans:
- [ ] 05-01-PLAN.md — Scoring models, weight configuration, 24 sub-score extractors, and 7 dimension calculators (TDD)
- [ ] 05-02-PLAN.md — Framework orchestrator, verdict logic, comparative scorecard, and radar chart visualization (TDD)

### Phase 6: Deliverables
**Goal**: The platform generates professional, consulting-grade Target Assessment Dossiers that a scientist can hand directly to a pharma VP -- with structured sections, embedded visualizations, and exportable charts.
**Depends on**: Phase 5
**Requirements**: REQ-701, REQ-702, REQ-703, REQ-704
**Success Criteria** (what must be TRUE):
  1. A user can generate a complete Target Assessment Dossier in both HTML and PDF (via fpdf2) containing all required sections: Executive Summary, Target Overview, 7 Evidence Dimensions, AI Synthesis, Scorecard, Recommendations, and Audit Trail
  2. The dossier includes embedded interactive visualizations (UMAP plots, expression heatmaps, volcano plots, evidence charts) in HTML, and static renders in PDF
  3. Individual charts can be exported as PNG or SVG from any visualization in the platform
**Plans**: 3 plans

Plans:
- [ ] 06-01-PLAN.md — Dossier data models, data collector, visualization builder, and chart export utilities
- [ ] 06-02-PLAN.md — HTML dossier renderer with Jinja2 templates and interactive Plotly charts
- [ ] 06-03-PLAN.md — PDF dossier renderer with fpdf2 and comprehensive reporting test suite

### Phase 7: UI Integration
**Goal**: All platform capabilities are accessible through a polished, multi-page Streamlit application with human-in-the-loop gates, mode controls, and a professional design system -- a scientist can run a complete target assessment end-to-end through the UI.
**Depends on**: Phase 6
**Requirements**: REQ-601, REQ-505, REQ-506, REQ-606
**Success Criteria** (what must be TRUE):
  1. A user can navigate through all seven pages (login, project setup, omics analysis, evidence explorer, AI insights, scorecard, audit trail) in a logical workflow, with each page rendering without errors
  2. All nine HITL gates across three modules (Omics: 3, Evidence: 3, Reasoning: 3) present approval/rejection UI with decision logging -- in Exploration mode, gates auto-approve with a recorded override; in Compliance mode, gates block until explicitly approved with e-signature
  3. The application uses a consistent design system (primary #0071e3, sans-serif font) with consulting-grade aesthetics suitable for a $100K-$500K engagement demo
  4. Six pre-built pharma showcase scenarios (EGFR/NSCLC, ESR1/ER+Breast, PIK3CA/HR+Breast, GLP1R/Obesity, PARP1/BRCA+Breast, CD274/Pan-cancer) can each be loaded and run through the full workflow in under 5 minutes with pre-cached evidence -- no live API calls required. Each scenario is drawn from a real top-10 pharma pipeline (AstraZeneca, Roche, Eli Lilly, Merck) and tells a distinct story suitable for a pharma VP demo
**Plans**: 4 plans

Plans:
- [ ] 07-01-PLAN.md — Shared components (design system CSS, HITL gate component, showcase loader) and app shell with 7-page navigation
- [ ] 07-02-PLAN.md — Analysis pages (omics pipeline, evidence explorer, AI insights) with 9 HITL gates and TaskManager polling
- [ ] 07-03-PLAN.md — Results pages (scorecard with radar chart and dossier export, audit trail viewer) and enhanced projects page with showcase scenarios
- [ ] 07-04-PLAN.md — Pre-cached showcase scenario data for 6 pharma targets and UI integration test suite

### Phase 8: Validation + Launch
**Goal**: The platform is validated against known drug targets, fully tested at three tiers, documented to GxP standards, and packaged for deployment -- ready for the first consulting engagement.
**Depends on**: Phase 7
**Requirements**: REQ-801, REQ-802, REQ-803, REQ-804, REQ-806
**Success Criteria** (what must be TRUE):
  1. The pharma showcase validation suite passes: all 6 real-world targets score within expected ranges -- EGFR (NSCLC, GO ≥75), ESR1 (ER+Breast, GO ≥70), PIK3CA (HR+Breast, GO ≥68), GLP1R (Obesity, GO ≥72), PARP1 (BRCA+Breast, GO ≥70), CD274 (Pan-cancer, CONDITIONAL 55-70) -- demonstrating the platform correctly distinguishes validated drug targets and complex/competitive ones
  2. Three-tier testing is operational: unit tests run in under 30 seconds, integration tests in under 5 minutes, and a GxP validation suite covers all critical path requirements
  3. GxP documentation is complete: Validation Master Plan, User Requirements Specification, Functional Requirements Specification, FMEA, traceability matrix (requirements to tests), and 5 or more priority SOPs
  4. Pre-commit hooks enforce compliance: audit trail integrity check, no hardcoded parameters check, and config change flagging are active on every commit
  5. The application runs in Docker with a single `docker compose up` command and all tests pass in the containerized environment
**Plans**: 3 plans

Plans:
- [ ] 08-01-PLAN.md — pytest marker registration (unit/integration/validation), tier classification of existing tests, GxP validation suite (6 showcase targets + MELK negative control), MELK fixture data, pre-commit structural tests
  - Wave 1 (autonomous)
  - Files: pyproject.toml, tests/conftest.py, 13 existing test files (markers), tests/test_validation/ (3 new files), data/showcase_scenarios/melk/ (2 JSON files)
- [ ] 08-02-PLAN.md — GxP documentation suite: VMP, URS, FRS, FMEA, traceability.yaml with real test function names, and 5 SOPs (system operation, data backup, change control, incident response, user management)
  - Wave 1 (autonomous, parallel with 08-01)
  - Files: docs/gxp/ (10 files: 5 docs + 5 SOPs + traceability.yaml)
- [ ] 08-03-PLAN.md — Updated Dockerfile (v2 src/ layout, port 8501, HEALTHCHECK), docker-compose.yml (app + test services), and three pre-commit compliance hooks
  - Wave 2 (after 08-01 + 08-02, has human checkpoint)
  - Files: Dockerfile, docker-compose.yml, .pre-commit-config.yaml, scripts/hooks/ (3 hook scripts), requirements.txt

## Progress

**Execution Order:**
Phases execute in numeric order: 1 then 2+3 (parallelizable) then 4 then 5 then 6 then 7 then 8.

**Critical Path:**
Phase 1 (Foundation) --> Phase 2+3 (Omics + Evidence, parallel) --> Phase 4 (AI Reasoning) --> Phase 5 (Scoring) --> Phase 6 (Deliverables) --> Phase 7 (UI) --> Phase 8 (Validation)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 3/3 | Complete | 2026-05-10 |
| 2. Omics Pipeline | 3/3 | Complete | 2026-05-10 |
| 3. Evidence Integration | 4/4 | Complete | 2026-05-11 |
| 4. AI Reasoning Engine | 3/3 | Complete | 2026-05-11 |
| 5. Target Scoring | 2/2 | Complete | 2026-05-12 |
| 6. Deliverables | 3/3 | Complete | 2026-05-12 |
| 7. UI Integration | 5/5 | Complete | 2026-05-13 |
| 8. Validation + Launch | 0/3 | Planned | - |

## Coverage

All 58 requirements mapped. No orphans. No duplicates.

| Requirement | Phase | Status |
|-------------|-------|--------|
| REQ-101 | Phase 2 | Done |
| REQ-102 | Phase 2 | Done |
| REQ-103 | Phase 2 | Done |
| REQ-104 | Phase 2 | Done |
| REQ-105 | Phase 2 | Done |
| REQ-106 | Phase 2 | Done |
| REQ-107 | Phase 2 | Done |
| REQ-108 | Phase 2 | Done |
| REQ-109 | Phase 2 | Done |
| REQ-110 | Phase 2 | Done |
| REQ-201 | Phase 3 | Done |
| REQ-202 | Phase 3 | Done |
| REQ-203 | Phase 3 | Done |
| REQ-204 | Phase 3 | Done |
| REQ-205 | Phase 3 | Done |
| REQ-206 | Phase 3 | Done |
| REQ-207 | Phase 3 | Done |
| REQ-208 | Phase 3 | Done |
| REQ-209 | Phase 3 | Done |
| REQ-210 | Phase 3 | Done |
| REQ-211 | Phase 3 | Done |
| REQ-301 | Phase 4 | Pending |
| REQ-302 | Phase 4 | Pending |
| REQ-303 | Phase 4 | Pending |
| REQ-304 | Phase 4 | Pending |
| REQ-305 | Phase 4 | Pending |
| REQ-306 | Phase 4 | Pending |
| REQ-307 | Phase 4 | Pending |
| REQ-308 | Phase 4 | Pending |
| REQ-401 | Phase 5 | Pending |
| REQ-402 | Phase 5 | Pending |
| REQ-403 | Phase 5 | Pending |
| REQ-404 | Phase 5 | Pending |
| REQ-405 | Phase 5 | Pending |
| REQ-406 | Phase 5 | Pending |
| REQ-501 | Phase 1 | Done |
| REQ-502 | Phase 1 | Done |
| REQ-503 | Phase 1 | Done |
| REQ-504 | Phase 1 | Done |
| REQ-505 | Phase 7 | Pending |
| REQ-506 | Phase 7 | Pending |
| REQ-507 | Phase 1 | Done |
| REQ-508 | Phase 1 | Done |
| REQ-601 | Phase 7 | Pending |
| REQ-602 | Phase 1 | Done |
| REQ-603 | Phase 1 | Done |
| REQ-604 | Phase 1 | Done |
| REQ-605 | Phase 1 | Done |
| REQ-606 | Phase 7 | Pending |
| REQ-701 | Phase 6 | Pending |
| REQ-702 | Phase 6 | Pending |
| REQ-703 | Phase 6 | Pending |
| REQ-704 | Phase 6 | Pending |
| REQ-801 | Phase 8 | Pending |
| REQ-802 | Phase 8 | Pending |
| REQ-803 | Phase 8 | Pending |
| REQ-804 | Phase 8 | Pending |
| REQ-805 | Phase 1 | Done |
| REQ-806 | Phase 8 | Pending |
