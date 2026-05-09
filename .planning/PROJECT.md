# BioOrchestrator v2 — Drug Target Intelligence Platform

## What This Is

An AI-powered Drug Target Intelligence Platform that compresses pharma target assessment from 6 months to 2 weeks. It ingests scRNA-seq data (.h5ad), runs a disease-agnostic QC/analysis pipeline, fetches evidence from 6 external APIs (OpenTargets, DGIdb, PubMed, ClinicalTrials, UniProt, ChEMBL), applies multi-mode AI reasoning, and scores targets on a 7-dimension framework — all with FDA 21 CFR Part 11 compliant audit trails. Built for consulting engagements ($100K-$500K) with mid-size biotech companies.

## Core Value

Scientists can upload omics data and a list of target genes, and receive a structured, evidence-backed GO/CONDITIONAL/NO-GO recommendation with full audit trail — replacing 6 months of manual assessment with 2 weeks of AI-augmented analysis.

## Requirements

### Validated

- ✓ 7-stage Scanpy pipeline (ingest, harmonize, QC, process, annotate, expression, lineage) — existing in bioorchestrator_real/
- ✓ Multi-provider LLM abstraction (Ollama, Groq, Anthropic) — existing in utils/llm_provider.py
- ✓ SQLite lineage audit trail — existing in pipeline/stage7_lineage.py
- ✓ AI copilot with tool calling — existing in utils/ai_copilot.py
- ✓ Interactive Streamlit dashboard — existing in app.py
- ✓ Demo data generation and precomputed visualization data — existing

### Active

- [ ] Disease-agnostic pipeline (remove hardcoded GIPR/GLP1R/adipose references)
- [ ] User authentication system (bcrypt, RBAC, account lockout)
- [ ] 21 CFR Part 11 audit trail with hash chains and e-signatures
- [ ] Multi-format data ingestion (.h5ad, .h5, 10x CellRanger folder)
- [ ] Ambient RNA removal (SoupX/CellBender)
- [ ] Configurable QC thresholds per project
- [ ] Proper DE analysis (Wilcoxon rank-sum with adj p-values)
- [ ] Internal GSEA/ORA on omics data
- [ ] Marker-based validation of CellTypist annotations
- [ ] OpenTargets evidence integration (GraphQL)
- [ ] DGIdb druggability integration (GraphQL)
- [ ] PubMed literature integration (Bio.Entrez)
- [ ] ClinicalTrials.gov integration (REST v2)
- [ ] UniProt protein function integration (REST)
- [ ] ChEMBL bioactivity integration (REST)
- [ ] Evidence caching layer (SQLite with TTL)
- [ ] Gene alias resolution (MyGene.info API)
- [ ] AI reasoning engine with 5 modes (hypothesis, synthesis, contradiction, gap, confidence)
- [ ] ReAct tool-calling loop (max 10 rounds) with provenance tracking
- [ ] 7-dimension target scoring framework (GOT-IT aligned, 100-point scale)
- [ ] 9 HITL gates with Exploration/Compliance mode toggle
- [ ] Background pipeline execution (ThreadPoolExecutor + SQLite persistence)
- [ ] Project resume from last checkpoint
- [ ] Project CRUD with audit logging
- [ ] Multi-page Streamlit app (login, project setup, omics, evidence, AI, scorecard, audit)
- [ ] Target Assessment Dossier report generation (HTML/PDF)
- [ ] Golden test: EGFR #1 in NSCLC retrovalidation

### Out of Scope

- Raw FASTQ processing — we start from .h5ad (post-alignment)
- Spatial transcriptomics — Phase 1.5 (after MVP)
- Multi-omics integration (CITE-seq, Perturb-seq, ATAC-seq) — Phase 2
- Real-time collaboration / multi-user — Phase 3
- Mobile app — web-only
- SaaS self-service — consulting-first GTM
- Market sizing / NPV financial models — outside computational biology scope
- Patent landscape analysis — requires specialized IP databases

## Context

**Existing codebase**: `bioorchestrator_real/` contains a working 7-stage pipeline for adipose tissue snRNA-seq analysis. Key files to refactor:
- `pipeline/stage3_qc.py` → `omics/qc.py` (remove hardcoded donors)
- `pipeline/stage4_process.py` → `omics/process.py` (parameterize all settings)
- `pipeline/stage5_annotate.py` → `omics/annotate.py` (remove GIPR/GLP1R analysis)
- `pipeline/stage7_lineage.py` → `compliance/audit_trail.py` (add hash chains, e-sigs)
- `utils/llm_provider.py` → `llm/provider.py` (clean up, add logging)
- `utils/ai_copilot.py` → `reasoning/` (extract tools, make disease-agnostic)
- `utils/plotting.py` → `ui/components/` (remove hardcoded gene names)
- `config.py` → `config.py` (rewrite as disease-agnostic)

**Regulatory context**: GAMP5 Category 5 custom application. 21 CFR Part 11 aligned for electronic records and signatures. ALCOA+ data integrity principles.

**Expert audit results**: 5-expert panel scored plan 73/100 after blocker resolution. 3 blockers resolved: auth system, scoring framework (GOT-IT aligned), Streamlit execution model (ThreadPoolExecutor).

**Target market**: Mid-size biotech (50-500 employees) with internal scRNA-seq data but no dedicated computational biology team. Consulting GTM at $100K-$500K per engagement.

## Constraints

- **RAM**: 8GB target — pipeline must handle 60K cells in-memory, larger datasets need downsampling
- **LLM**: Primary local (Ollama qwen3:8b), fallback cloud (Groq free tier, Anthropic paid)
- **Timeline**: 12-week build plan for MVP
- **Solo developer**: Claude Code agents as virtual team members for review
- **Python 3.10**: Best compatibility with scientific stack (scanpy, anndata, celltypist)
- **NumPy < 2.0**: Avoid breaking changes with scientific ecosystem
- **SQLite for MVP**: PostgreSQL migration path designed but deferred to Phase 2
- **Streamlit**: Fast to build, great for demo — FastAPI extraction path for Phase 2

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Disease-agnostic from day one | Reusable across indications, not locked to adipose/obesity | — Pending |
| MuData-native internal format | Future multi-omics extensibility even for single-modality MVP | — Pending |
| GOT-IT framework for scoring | Published standard (Nature Reviews Drug Discovery 2021), scientifically credible | — Pending |
| SoupX over CellBender for ambient RNA | Simpler (R via rpy2), no GPU needed, good enough for most datasets | — Pending |
| Wilcoxon rank-sum for DE | Fast, Scanpy default, well-understood. Pseudobulk DESeq2 as optional | — Pending |
| ThreadPoolExecutor for background tasks | Streamlit-compatible, SQLite persistence survives reruns | — Pending |
| Exploration vs Compliance mode | Reduces HITL friction for exploratory use, mandatory gates for regulatory | — Pending |
| 6 evidence sources for MVP | OpenTargets, DGIdb, PubMed, ClinicalTrials, UniProt, ChEMBL. +3 in Phase 1.5 | — Pending |
| Harmony for batch correction | Fast (2 min vs 15 min scVI), linear, good enough for MVP. scVI optional | — Pending |
| bcrypt + RBAC for auth | 21 CFR Part 11 requires unique user ID + password for e-signatures | — Pending |

---
*Last updated: 2026-05-09 after initialization*
