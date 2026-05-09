# BioOrchestrator v2 — Requirements

## Milestone 1: Consulting-Ready MVP

### Category 1: Omics Pipeline

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| REQ-101 | Disease-agnostic scRNA-seq pipeline — remove all hardcoded GIPR/GLP1R/adipose references | P0 | FEATURES.md, PROJECT.md |
| REQ-102 | Multi-format data ingestion: .h5ad, .h5 (CellRanger HDF5), 10x folder (matrix.mtx.gz + barcodes + features) | P0 | Expert audit U3 |
| REQ-103 | Ambient RNA removal via SoupX (rpy2) with CellBender option and skip-with-warning HITL gate | P0 | Expert audit C1 |
| REQ-104 | Configurable QC thresholds per project with tissue-specific defaults (brain max_mito=5%, tumor max_mito=25%) | P0 | PITFALLS.md |
| REQ-105 | Differential expression using sc.tl.rank_genes_groups (Wilcoxon default) with adj p-values and multiple testing correction | P0 | Expert audit C3 |
| REQ-106 | Internal gene set enrichment (ORA via decoupler or gseapy) on omics data per cell type | P1 | Expert audit C4 |
| REQ-107 | Marker-based validation of CellTypist annotations — flag discrepancies between classifier and canonical markers | P1 | Expert audit H2 |
| REQ-108 | Pipeline progress callbacks to TaskManager for background execution with stage-level progress reporting | P0 | Expert audit E2 |
| REQ-109 | Pipeline checkpointing — save intermediate .h5ad after QC, normalization, PCA, clustering, annotation for resume | P1 | Expert audit E7 |
| REQ-110 | Tissue-aware CellTypist model selection: lung->Human_Lung_Atlas, immune->Immune_All_Low, etc. for 10+ tissues | P1 | Expert audit M3 |

### Category 2: Evidence Integration

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| REQ-201 | OpenTargets GraphQL integration — genetic associations, disease links, tractability scores, known drugs | P0 | FEATURES.md |
| REQ-202 | DGIdb GraphQL integration — druggability classification, drug-gene interactions | P0 | FEATURES.md |
| REQ-203 | PubMed/Bio.Entrez integration — recent papers (5yr), abstracts, AI summary of top 10 | P0 | FEATURES.md |
| REQ-204 | ClinicalTrials.gov REST v2 — active trials, phases, sponsors. Query by indication + filter by drug names from DGIdb | P0 | FEATURES.md, Fix 1 |
| REQ-205 | UniProt REST — protein function, subcellular location, domains, AlphaFold structure availability | P0 | FEATURES.md |
| REQ-206 | ChEMBL REST — bioactivity data (pChEMBL values), existing compounds, mechanism of action | P0 | FEATURES.md |
| REQ-207 | Evidence caching layer (SQLite with 24h TTL, configurable, manual invalidation) | P0 | ARCHITECTURE.md |
| REQ-208 | Parallel evidence fetching using ThreadPoolExecutor (not async) with per-source rate limiting | P0 | Expert audit E5 |
| REQ-209 | Gene alias resolution via MyGene.info API + local common aliases (PD-L1->CD274, HER2->ERBB2) | P1 | Expert audit U4 |
| REQ-210 | API failure fallback: retry 3x exponential backoff -> cache -> Evidence with confidence=0.0 + flag | P0 | PITFALLS.md |
| REQ-211 | Abstract EvidenceSource interface with source_name, source_version, fetch(), is_available() | P0 | ARCHITECTURE.md |

### Category 3: AI Reasoning Engine

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| REQ-301 | Multi-mode reasoning orchestrator supporting 5 modes: hypothesis, synthesis, contradiction, gap, confidence | P0 | FEATURES.md |
| REQ-302 | Ollama native tool-calling API (not custom ReAct parser) with max 10 tool rounds | P0 | Fix 2 |
| REQ-303 | 14+ LLM tool definitions for all evidence queries (omics expression, enrichment, DE, 6 APIs, cell composition, QC) | P0 | Master plan Part 2 |
| REQ-304 | Versioned system prompts with SHA256 hash tracking in audit trail | P0 | Master plan Part 2 |
| REQ-305 | AI output provenance tagging: model, prompt_version, input_evidence_hashes, tools_used, reasoning_chain | P0 | Master plan Part 2 |
| REQ-306 | LLM fallback chain: Ollama qwen3:8b -> Groq llama-3.3-70b -> Anthropic Claude. Each fallback logged | P1 | STACK.md |
| REQ-307 | Hallucination checks: every claim must cite tool call result, confidence >0.8 requires 3+ sources | P1 | Expert audit |
| REQ-308 | Token/context management: summarize evidence >8K tokens, reserve 2K for output | P1 | Master plan |

### Category 4: Scoring & Decision Framework

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| REQ-401 | 7-dimension scoring framework (100-point scale) with 24 sub-scores and published formulas | P0 | Master plan Part 19.2 |
| REQ-402 | Dimensions: genetic_evidence(15), expression_biology(15), druggability(15), safety_selectivity(15), competitive_landscape(15), clinical_translational(15), literature_consensus(10) | P0 | Master plan Part 19.2 |
| REQ-403 | Decision thresholds: GO >=75, CONDITIONAL 50-74, NO-GO <50. Dimension minimums force CONDITIONAL | P0 | Master plan Part 19.2 |
| REQ-404 | User-adjustable dimension weights at HITL-009 gate | P1 | FEATURES.md |
| REQ-405 | Comparative target assessment — side-by-side scoring for 3-20 targets with radar charts | P1 | FEATURES.md |
| REQ-406 | Contradictory evidence penalty in literature_consensus dimension (up to -4 points) | P0 | Master plan Part 19.2 |

### Category 5: Auth + Compliance

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| REQ-501 | User authentication with bcrypt password hashing, unique user_id, RBAC (admin/analyst/reviewer) | P0 | Expert audit E3/R1 |
| REQ-502 | Account lockout after 5 failed attempts (15 min cooldown) | P0 | Master plan Part 19.1 |
| REQ-503 | 21 CFR Part 11 audit trail: append-only SQLite, hash chains, NTP timestamps, ALCOA+ compliance | P0 | Master plan Part 1.4 |
| REQ-504 | Electronic signatures: re-authentication at signing, SHA256 signature hash, meaning field | P0 | Master plan Part 19.1 |
| REQ-505 | 9 HITL gates across 3 modules (Omics: 3, Evidence: 3, Reasoning: 3) with decision logging | P0 | Master plan Part 6 |
| REQ-506 | Exploration vs Compliance mode toggle at project creation | P0 | Expert audit U1 |
| REQ-507 | Audit trail indices on: user_id, timestamp, resource_type, resource_id | P1 | Gap fix |
| REQ-508 | WAL mode for all SQLite databases + busy_timeout for concurrent access | P0 | PITFALLS.md |

### Category 6: UI + Execution

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| REQ-601 | Multi-page Streamlit app: login, project setup, omics analysis, evidence explorer, AI insights, scorecard, audit trail | P0 | Master plan Part 1.2 |
| REQ-602 | Background pipeline execution via ThreadPoolExecutor with SQLite task state persistence | P0 | Master plan Part 19.3 |
| REQ-603 | Project resume from last checkpoint across browser sessions | P0 | Expert audit U2 |
| REQ-604 | .streamlit/config.toml: maxUploadSize=2000, theme, fastReruns=true | P0 | Expert audit E10 |
| REQ-605 | Project CRUD with audit logging and per-project file storage layout | P0 | Master plan |
| REQ-606 | Professional design system: primary #0071e3, sans-serif font, consulting-grade aesthetics | P1 | Master plan |

### Category 7: Deliverables

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| REQ-701 | Target Assessment Dossier in HTML and PDF (fpdf2, no system deps) | P0 | FEATURES.md, STACK.md |
| REQ-702 | Report sections: Executive Summary, Target Overview, 7 Evidence Dimensions, AI Synthesis, Scorecard, Recommendations, Audit Trail | P0 | Expert audit |
| REQ-703 | Interactive visualizations: UMAP plots, expression heatmaps, volcano plots, evidence charts | P0 | FEATURES.md |
| REQ-704 | Individual chart export as PNG/SVG | P1 | Expert audit U7 |

### Category 8: Validation

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| REQ-801 | Golden test: EGFR scores #1 among 8 candidates in NSCLC retrovalidation (score >=75/100 = GO) | P0 | Master plan Part 13 |
| REQ-802 | Negative control: MELK scores <50/100 (NO-GO) in breast cancer with specific red flags | P1 | Master plan Part 13 |
| REQ-803 | Three-tier testing: unit (<30s), integration (<5min), validation (GxP qualification) | P0 | Master plan Part 1.2 |
| REQ-804 | GxP documentation: VMP, URS, FRS, FMEA, traceability.yaml, 5+ priority SOPs | P0 | Master plan Part 3 |
| REQ-805 | Synthetic h5ad test fixture in Week 1 — small dataset for fast pipeline testing | P0 | PITFALLS.md |
| REQ-806 | Pre-commit compliance hooks: audit trail check, no hardcoded params, config change flag | P1 | Master plan Part 3.5 |

---

### Priority Summary
- **P0**: 42 requirements (must have for v1 launch)
- **P1**: 17 requirements (high value, deferrable if schedule pressure)
- **Total**: 59 requirements

### Requirement-to-Phase Mapping

| Phase | Requirements | Count |
|-------|-------------|-------|
| 1. Foundation | REQ-501, REQ-502, REQ-503, REQ-504, REQ-507, REQ-508, REQ-602, REQ-603, REQ-604, REQ-605, REQ-805 | 11 |
| 2. Omics Pipeline | REQ-101, REQ-102, REQ-103, REQ-104, REQ-105, REQ-106, REQ-107, REQ-108, REQ-109, REQ-110 | 10 |
| 3. Evidence Integration | REQ-201, REQ-202, REQ-203, REQ-204, REQ-205, REQ-206, REQ-207, REQ-208, REQ-209, REQ-210, REQ-211 | 11 |
| 4. AI Reasoning Engine | REQ-301, REQ-302, REQ-303, REQ-304, REQ-305, REQ-306, REQ-307, REQ-308 | 8 |
| 5. Target Scoring | REQ-401, REQ-402, REQ-403, REQ-404, REQ-405, REQ-406 | 6 |
| 6. Deliverables | REQ-701, REQ-702, REQ-703, REQ-704 | 4 |
| 7. UI Integration | REQ-505, REQ-506, REQ-601, REQ-606 | 4 |
| 8. Validation + Launch | REQ-801, REQ-802, REQ-803, REQ-804, REQ-806 | 5 |
| **Total** | | **59** |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| REQ-101 | Phase 2 | Pending |
| REQ-102 | Phase 2 | Pending |
| REQ-103 | Phase 2 | Pending |
| REQ-104 | Phase 2 | Pending |
| REQ-105 | Phase 2 | Pending |
| REQ-106 | Phase 2 | Pending |
| REQ-107 | Phase 2 | Pending |
| REQ-108 | Phase 2 | Pending |
| REQ-109 | Phase 2 | Pending |
| REQ-110 | Phase 2 | Pending |
| REQ-201 | Phase 3 | Pending |
| REQ-202 | Phase 3 | Pending |
| REQ-203 | Phase 3 | Pending |
| REQ-204 | Phase 3 | Pending |
| REQ-205 | Phase 3 | Pending |
| REQ-206 | Phase 3 | Pending |
| REQ-207 | Phase 3 | Pending |
| REQ-208 | Phase 3 | Pending |
| REQ-209 | Phase 3 | Pending |
| REQ-210 | Phase 3 | Pending |
| REQ-211 | Phase 3 | Pending |
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
| REQ-501 | Phase 1 | Pending |
| REQ-502 | Phase 1 | Pending |
| REQ-503 | Phase 1 | Pending |
| REQ-504 | Phase 1 | Pending |
| REQ-505 | Phase 7 | Pending |
| REQ-506 | Phase 7 | Pending |
| REQ-507 | Phase 1 | Pending |
| REQ-508 | Phase 1 | Pending |
| REQ-601 | Phase 7 | Pending |
| REQ-602 | Phase 1 | Pending |
| REQ-603 | Phase 1 | Pending |
| REQ-604 | Phase 1 | Pending |
| REQ-605 | Phase 1 | Pending |
| REQ-606 | Phase 7 | Pending |
| REQ-701 | Phase 6 | Pending |
| REQ-702 | Phase 6 | Pending |
| REQ-703 | Phase 6 | Pending |
| REQ-704 | Phase 6 | Pending |
| REQ-801 | Phase 8 | Pending |
| REQ-802 | Phase 8 | Pending |
| REQ-803 | Phase 8 | Pending |
| REQ-804 | Phase 8 | Pending |
| REQ-805 | Phase 1 | Pending |
| REQ-806 | Phase 8 | Pending |
