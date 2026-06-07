# PRD: BioOrchestrator MVP

**Version**: 1.0
**Status**: Draft
**Last Updated**: 2026-05-02

---

## 1. Summary

BioOrchestrator is an open-source, self-hostable platform that turns raw single-cell RNA-seq data into auditable, AI-interpreted drug target evidence — no coding required. The MVP delivers an end-to-end workflow: upload .h5ad data, run a governed Scanpy pipeline with human approval gates at every step, get AI-generated biological interpretations from free open-source LLMs, score drug targets at cell-type resolution, and export a regulatory-ready audit report. It runs at $0 cost — locally via Docker or publicly via HuggingFace Spaces.

This PRD defines the minimum viable product: what ships in v1.0, what's deferred, and how we measure success.

---

## 2. Contacts

| Role | Name | Responsibility |
|------|------|---------------|
| Product Owner | [Your Name] | Vision, prioritization, stakeholder alignment |
| Lead Developer | [Your Name] | Architecture, implementation, deployment |
| Target Users | Translational Scientists, Comp Bio Directors, Biomarker Teams | Primary users and buyers |
| Advisory | Pharma Comp Bio Professionals (via E2 interviews) | Validation, feedback |

---

## 3. Background

### 3.1 Context

Pharma spends **$2.6B average** per drug. Computational biology is embedded at every stage — target ID, biomarker discovery, patient stratification, regulatory filing. But the tooling is broken:

- **Reproducibility crisis**: Reproducing one analysis for a regulatory filing costs $15K-$50K and takes 2-6 weeks. A failed FDA inspection delays launch 6-18 months ($500M-$2B for a blockbuster).
- **Bioinformatics bottleneck**: Standard scRNA-seq analysis wait time is 2-4 weeks. Custom single-cell: 4-12 weeks. Computational biologists spend only 30-40% of time on actual analysis.
- **GxP compliance gap**: Jupyter notebooks are non-compliant by design. GxP-qualifying a pipeline costs $500K-$2M and takes 6-18 months. Single-cell data becomes "exploratory" evidence to avoid this burden.
- **Translation gap**: A finding like "GIPR enriched in pericytes" doesn't tell you which patients benefit. <5% of scRNA-seq-derived biomarkers survive to clinical validation.

### 3.2 Why Now

Three shifts make this product viable today:

1. **Open-source LLMs reached parity for domain tasks.** Qwen3 and Llama3 can interpret biological data with comparable quality to Claude/GPT-4, at zero cost. This was not true 12 months ago.
2. **Free hosting infrastructure matured.** HuggingFace Spaces offers 16GB RAM, Docker support, and persistent storage — enough to run both an LLM and a Scanpy pipeline in-container.
3. **Pharma's data sovereignty concerns peaked.** After multiple cloud security incidents, pharma IT teams increasingly demand tools that run on their own servers with no external API calls. A self-hosted, open-source tool that needs no cloud LLM calls is perfectly timed.

### 3.3 What We Already Have

The BioOrchestrator prototype is **substantially built**. This is not a greenfield project — it's a polish-and-ship exercise:

| Component | Status | Lines of Code |
|-----------|--------|--------------|
| 7-stage Scanpy pipeline (ingest → export) | Done | ~1,800 |
| Streamlit UI with 7 sections + copilot | Done | ~1,650 |
| AI Copilot with 10 tool functions | Done | ~500 |
| Multi-provider LLM system (Ollama/Groq/Anthropic) | Done | ~350 |
| Pre-computed demo (49,999 cells, 15 .npz files, 8 Q&A) | Done | — |
| SQLite audit trail (21 CFR Part 11 schema) | Done | ~200 |
| GIPR/GLP1R target scoring + spatial validation | Done | ~300 |
| .h5ad upload with auto-subsample | Done | ~50 |
| Dockerfile for HuggingFace Spaces | Done | ~35 |
| Metadata harmonization (fuzzy match + confidence) | Done | ~150 |

**What's missing for MVP**: Human approval gates in the UI, generalized target scoring (beyond GIPR/GLP1R), one-click export, and polish.

---

## 4. Objective

### 4.1 Mission

Make single-cell analysis **auditable, interpretable, and accessible** to every pharma team — without requiring bioinformatics expertise or paid software.

### 4.2 MVP Objective

Ship a product that a pharma comp bio director can:
1. **Try in 30 seconds** — visit a URL, see pre-computed demo results
2. **Upload their own data** — .h5ad file, get QC + UMAP + AI interpretation
3. **Trust the output** — approve/reject every AI decision, full audit trail
4. **Deploy on their servers** — `docker compose up`, no external API calls, no data leaving network

### 4.3 Strategic Alignment

The MVP validates three core hypotheses from the discovery plan:
- **A1**: Pharma wants no-code scRNA-seq (validated if demo gets traction)
- **A18**: Open-source LLMs are good enough (validated by E10 benchmark)
- **A19**: Self-hosted is a selling point (validated by E2 interviews)

### 4.4 Key Results (OKRs)

**Objective: Launch a credible, usable MVP that validates product-market fit**

| Key Result | Target | Measurement |
|-----------|--------|-------------|
| KR1: Live demo accessible at public URL | HF Spaces URL returns 200 | Deploy + uptime check |
| KR2: Demo-to-insight time <60 seconds | Visitor clicks "Start" → sees UMAP + AI interpretation | Stopwatch test |
| KR3: Upload-to-QC time <3 minutes | Upload 50K-cell .h5ad → see QC stats + UMAP | Timed user test (E11) |
| KR4: AI interpretation accuracy ≥80% of Claude | 10-task benchmark scores | Internal benchmark (E10) |
| KR5: >50% of demo visitors rate it "real tool" | Feedback widget on HF Spaces | Feedback distribution (E6) |
| KR6: Self-hosted deployment works in <5 minutes | `docker compose up` → app at localhost:7860 | Cold-start timing |
| KR7: Full audit trail exportable as JSON/PDF | Every step logged with params + timestamps + cell counts | Export button test |
| KR8: >50 GitHub stars in first 2 weeks | Public repo with README + contributing guide | GitHub analytics (E14) |

---

## 5. Market Segment(s)

### 5.1 Primary: Translational Biology Teams at Mid-to-Large Pharma

**Who they are**: 5-20 person teams spanning computational biologists, translational scientists, and biomarker leads. Report to VP of Translational Science or Head of Computational Biology.

**Their job**: Take single-cell data from discovery through to IND-enabling regulatory packages. They need to prove a drug target is real, in the right cell type, in the right tissue, with reproducible evidence.

**Their pain**: They have more data than analysts. The queue is 4-12 weeks. When results finally come back, they can't reproduce them for regulatory. Every analysis is a one-off Jupyter notebook that dies when the analyst leaves.

**Constraints**:
- Data cannot leave the corporate network (HIPAA, internal policy)
- Results must be reproducible for FDA filing
- Biologists outnumber bioinformaticians 5:1
- Budget decisions made by directors, not individual scientists

### 5.2 Secondary: Academic Computational Biologists

**Who they are**: PhD students, postdocs, and PIs running scRNA-seq in academic labs. Comfortable with code but time-constrained.

**Their job**: Analyze single-cell data for papers. Speed matters more than compliance.

**Their pain**: Spend 60-70% of time on data wrangling, not science. Want quick QC + UMAP + DE to decide if a dataset is worth pursuing.

**Why secondary**: They don't buy enterprise software. But they contribute to open-source, write papers referencing tools, and move to pharma.

### 5.3 Tertiary: CROs (Contract Research Organizations)

**Who they are**: Service providers who run scRNA-seq for pharma clients.

**Their job**: Deliver reproducible, auditable analyses to clients. Audit trail is their competitive advantage.

**Why tertiary**: Smaller market, but high compliance requirements align with BioOrchestrator's governance features.

---

## 6. Value Proposition(s)

### 6.1 Customer Jobs We Address

| Job | Who | Current Solution | BioOrchestrator |
|-----|-----|-----------------|-----------------|
| "Analyze my scRNA-seq data without waiting 4 weeks for a bioinformatician" | Translational scientist | Wait in queue, or learn Python | Upload .h5ad → results in minutes, no code |
| "Make my single-cell analysis reproducible for regulatory" | Comp bio director | Manual SOPs + Jupyter + prayer | Automated audit trail with every parameter logged |
| "Understand what my scRNA-seq results mean for drug targets" | Biomarker scientist | Read papers, ask colleagues | AI copilot interprets results in biological context |
| "Score drug targets at cell-type resolution, not just gene level" | Target assessment team | PandaOmics (bulk only) or manual | Cell-type-level composite scoring with evidence breakdown |
| "Run AI analysis without sending patient data to the cloud" | Pharma IT / compliance | Reject cloud AI tools | Self-hosted, Ollama runs locally, zero external API calls |

### 6.2 Gains

- **10x faster**: Upload → target evidence in minutes, not weeks
- **100% auditable**: Every step logged with parameters, timestamps, cell counts, package versions
- **$0 cost**: Open-source LLMs, free hosting, no API keys needed
- **Self-hosted**: Data never leaves your network. Docker Compose up, done.
- **Cell-type resolution**: Not "GIPR is associated with obesity" but "GIPR is 5.1x enriched in pericytes with druggability 0.82"

### 6.3 Pains Avoided

- No more Jupyter notebooks with hidden state
- No more 4-12 week bioinformatics queue
- No more "which version of scanpy did we use?" conversations before FDA inspection
- No more manual QC threshold decisions without documentation
- No more paying $20K+/year for cloud AI tools that can't handle patient data

### 6.4 Competitive Differentiation

**No single competitor offers all 4:**

| Capability | Cellenics | PandaOmics | CELLxGENE | Benchling | **BioOrchestrator** |
|-----------|-----------|------------|-----------|-----------|-------------------|
| scRNA-seq pipeline | Basic | No | View only | No | **Full (7-stage)** |
| AI interpretation | No | Yes (bulk) | No | No | **Yes (cell-type)** |
| Cell-type target scoring | No | No | No | No | **Yes** |
| GxP audit trail | No | No | No | Yes | **Yes** |
| Self-hostable | No | No | Partial | No | **Yes** |
| Open-source / free | Yes | No | Yes | No | **Yes** |
| Human-in-the-Loop | No | No | No | Partial | **Yes (every step)** |

---

## 7. Solution

### 7.1 User Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BioOrchestrator MVP                          │
│                                                                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐        │
│  │  Upload   │──▶│    QC    │──▶│ Process  │──▶│ Annotate │        │
│  │  .h5ad    │   │  Gates   │   │ Scanpy   │   │ Cell Type│        │
│  │          │   │          │   │          │   │          │        │
│  │ [HItL:   │   │ [HItL:   │   │ [HItL:   │   │ [HItL:   │        │
│  │ confirm  │   │ approve  │   │ review   │   │ confirm  │        │
│  │ metadata]│   │ thresholds│   │ params]  │   │ labels]  │        │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘        │
│       │                                              │              │
│       │         ┌──────────────────────────┐         │              │
│       └────────▶│      AI Copilot          │◀────────┘              │
│                 │  "Ask anything about     │                        │
│                 │   your data"             │                        │
│                 │  [Ollama / Groq / Claude] │                        │
│                 └──────────────────────────┘                        │
│                              │                                      │
│                 ┌────────────┴────────────┐                         │
│                 │                         │                         │
│           ┌──────────┐           ┌──────────┐                      │
│           │  Target   │           │  Export   │                      │
│           │  Scoring  │           │  Audit    │                      │
│           │          │           │  Report   │                      │
│           │ [HItL:   │           │          │                      │
│           │ review   │           │ [HItL:   │                      │
│           │ weights] │           │ approve  │                      │
│           └──────────┘           │ export]  │                      │
│                                  └──────────┘                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Two modes, one interface:**
- **Demo mode** (default): Pre-computed adipose tissue dataset. Instant. No upload needed. Visitor sees real results immediately.
- **Upload mode**: User uploads .h5ad → runs live Scanpy pipeline → sees their own data through every step.

### 7.2 Key Features

#### F1: Data Ingestion + Upload

**What it does**: Accept .h5ad files (AnnData format) up to 200MB. Auto-subsample at 100K cells. Show metadata summary (n_cells, n_genes, obs columns, tissue type if annotated).

**HItL gate**: User confirms dataset metadata (species, tissue, expected cell count) before proceeding. If metadata looks wrong, user can correct before pipeline runs.

**Already built**: Basic upload widget with auto-subsample. Needs: metadata confirmation dialog, data validation checks (are obs/var present? is expression matrix non-empty?).

| Sub-feature | Status | Effort |
|-------------|--------|--------|
| .h5ad file uploader with size limit | Done | — |
| Auto-subsample at 100K cells | Done | — |
| Metadata summary display | Done | — |
| Metadata confirmation dialog (HItL) | **To build** | S |
| Data validation checks | **To build** | S |
| Demo dataset auto-load | Done | — |

#### F2: Metadata Harmonization

**What it does**: Map dataset column names to CDISC standard terminology using fuzzy matching + optional LLM enhancement. Display confidence scores per mapping. Flag low-confidence mappings for human review.

**HItL gate**: Mandatory approval. Every mapping shown with confidence badge:
- Green (≥95%): Auto-suggested, one-click approve
- Yellow (85-94%): Recommended, review encouraged
- Orange (70-84%): Flagged, review required
- Red (<70%): Blocked, human must decide

User can accept, modify, or reject each mapping. All decisions logged to audit trail.

**Already built**: Fuzzy matching with confidence scores, animated LLM mapping display. Needs: interactive approve/reject UI per mapping, human override logging.

| Sub-feature | Status | Effort |
|-------------|--------|--------|
| Fuzzy match with rapidfuzz | Done | — |
| Confidence score calculation | Done | — |
| Animated mapping display | Done | — |
| Approve/reject buttons per mapping (HItL) | **To build** | M |
| Human override logging to audit trail | **To build** | S |
| LLM-enhanced mapping (optional) | **To build** | M |

#### F3: Quality Control Gates

**What it does**: 5-layer QC filtering: gene count, mitochondrial %, doublet detection, sex concordance, cell count threshold. Show funnel chart (cells at each stage), per-donor verdict table, and QC scatter plots.

**HItL gate**: Mandatory approval. After QC runs, user sees:
- Suggested thresholds with statistical justification
- Per-donor PASS/QUARANTINE verdicts with reasoning
- Interactive sliders to adjust thresholds
- "Approve QC" or "Adjust and Re-run" buttons

Every threshold change logged with reason-for-change.

**Already built**: Full 5-gate QC pipeline, funnel chart, donor verdict table, scatter plots. Needs: interactive threshold sliders, approve/re-run buttons, reason-for-change input.

| Sub-feature | Status | Effort |
|-------------|--------|--------|
| 5-gate QC pipeline | Done | — |
| Funnel chart visualization | Done | — |
| Per-donor verdict table | Done | — |
| QC scatter/violin plots | Done | — |
| Interactive threshold sliders (HItL) | **To build** | M |
| Approve/re-run workflow (HItL) | **To build** | M |
| Reason-for-change input | **To build** | S |

#### F4: Scanpy Processing Pipeline

**What it does**: Normalize → log-transform → HVG selection → scale → PCA → Harmony batch correction → UMAP → Leiden clustering. Display: PCA scree plot, before/after Harmony UMAP, HVG volcano.

**HItL gate**: User reviews processing parameters before execution:
- Number of PCs (default: 50)
- Leiden resolution (default: 0.5)
- Batch key for Harmony (auto-detected from metadata)
- HVG selection method

After processing, user approves UMAP + clustering quality or adjusts parameters.

**Already built**: Full processing pipeline, all visualizations. Needs: parameter review dialog before run, post-run approval.

| Sub-feature | Status | Effort |
|-------------|--------|--------|
| Full Scanpy pipeline (normalize → UMAP) | Done | — |
| Harmony batch correction | Done | — |
| Before/after UMAP display | Done | — |
| PCA scree plot | Done | — |
| Parameter review dialog (HItL) | **To build** | S |
| Post-processing approval (HItL) | **To build** | S |

#### F5: Cell Type Annotation

**What it does**: Automated cell type annotation using marker gene expression patterns. Display UMAP colored by cell type, composition bar chart, marker gene dot plot.

**HItL gate**: User reviews cell type labels:
- Each cluster shown with suggested label + supporting markers + confidence
- User can accept, rename, merge clusters, or flag for review
- AI biological narrator generates plain-English interpretation of each cell type's significance

**Already built**: CellTypist annotation, UMAP display, composition chart, dot plot. Needs: interactive label editing, merge/rename UI, AI narrative per cell type.

| Sub-feature | Status | Effort |
|-------------|--------|--------|
| Automated cell type labeling | Done | — |
| UMAP colored by cell type | Done | — |
| Composition bar chart | Done | — |
| Marker gene dot plot | Done | — |
| Interactive label editing (HItL) | **To build** | M |
| AI narrative per cell type | **To build** | M |

#### F6: Drug Target Scoring

**What it does**: Score drug targets at cell-type resolution using composite evidence:

| Evidence Dimension | Data Source | Score Range |
|-------------------|-------------|-------------|
| Expression specificity (tau) | Uploaded/demo scRNA-seq data | 0-1 |
| Fold enrichment | Per cell type vs cohort mean | 0-10x+ |
| Druggability | DGIdb API (free) | 0-1 |
| Genetic evidence | OpenTargets API (free) | 0-1 |
| Literature support | PubMed E-utilities API (free) | 0-1 |

**Composite score**: Weighted sum with explainable per-factor breakdown. Default weights: expression 0.3, enrichment 0.2, druggability 0.2, genetics 0.2, literature 0.1.

**HItL gate**: User reviews target scorecard:
- Sortable table of all scored targets
- Click to expand per-factor breakdown
- Adjust weights with sliders
- Accept/reject targets from the shortlist
- Document rationale for each decision

**Already built**: GIPR/GLP1R enrichment analysis with fold-change per cell type. Needs: generalized scoring for any gene, external API integration, composite scoring, interactive weight adjustment.

| Sub-feature | Status | Effort |
|-------------|--------|--------|
| Expression enrichment (fold-change per cell type) | Done (GIPR/GLP1R) | — |
| Generalize to any user-defined gene set | **To build** | L |
| Druggability score (DGIdb API) | **To build** | M |
| Genetic evidence (OpenTargets API) | **To build** | M |
| Literature score (PubMed API) | **To build** | M |
| Composite scoring with weights | **To build** | M |
| Interactive scorecard UI (HItL) | **To build** | L |
| Weight adjustment sliders | **To build** | S |

#### F7: AI Copilot

**What it does**: Natural language interface to query analysis data. Powered by open-source LLMs (Ollama local or Groq cloud) with fallback to Anthropic. 10 tool functions give the LLM access to expression data, enrichment scores, QC metrics, DE results, spatial data, and pipeline summary.

**HItL gate**: Per-query evaluation. User sees AI response + tools used + confidence indicator. Can flag inaccurate responses, which are logged to audit trail.

**Already built**: Full copilot with 10 tools, demo mode (8 pre-computed Q&A), live mode with multi-provider support. Needs: response feedback buttons (accurate/inaccurate), flagging mechanism.

| Sub-feature | Status | Effort |
|-------------|--------|--------|
| 10 query functions (expression, enrichment, QC, etc.) | Done | — |
| Tool-calling loop (max 3 rounds) | Done | — |
| Demo mode (8 pre-computed Q&A) | Done | — |
| Multi-provider LLM (Ollama/Groq/Anthropic) | Done | — |
| Auto-detect provider | Done | — |
| Chart suggestions based on query | Done | — |
| Response feedback buttons (HItL) | **To build** | S |
| Inaccuracy flagging + audit log | **To build** | S |

#### F8: Audit Trail + Export

**What it does**: Complete provenance tracking for every pipeline run. SQLite database with 3 tables (runs, stages, packages). Every parameter, timestamp, cell count, and package version recorded.

**Export formats**:
- JSON (machine-readable, for downstream tools)
- PDF/HTML (human-readable, for regulatory submissions)
- CDISC/SDTM mapping (structured data for FDA filings)

**HItL gate**: User reviews audit report before export. Can add narrative commentary. Must approve before download.

**Already built**: SQLite audit trail with SHA256 checksums, package version tracking, query API. Needs: export to PDF/HTML, CDISC mapping, export approval UI, narrative commentary.

| Sub-feature | Status | Effort |
|-------------|--------|--------|
| SQLite audit trail (append-only) | Done | — |
| SHA256 checksums | Done | — |
| Package version tracking | Done | — |
| Parameter logging (JSON) | Done | — |
| Stage timing + cell counts | Done | — |
| Export to JSON | Done | — |
| Export to PDF/HTML | **To build** | M |
| CDISC/SDTM mapping | **To build** | L |
| Export approval UI (HItL) | **To build** | S |
| Narrative commentary input | **To build** | S |
| User identity logging | **To build** | S |

#### F9: Deployment

**What it does**: Two deployment options:

1. **HuggingFace Spaces** (public demo): Docker container with Ollama + qwen3:4b + Streamlit. Port 7860. Live URL anyone can access.
2. **Docker Compose** (self-hosted): Same container, runs on pharma's own servers. No external API calls. Data never leaves the network.

**Already built**: Dockerfile, requirements.txt, Streamlit config for port 7860. Needs: docker-compose.yml for self-hosted, health check endpoint, environment detection.

| Sub-feature | Status | Effort |
|-------------|--------|--------|
| Dockerfile (Python 3.11 + Ollama + qwen3:4b) | Done | — |
| requirements.txt | Done | — |
| HF Spaces port config (7860) | Done | — |
| docker-compose.yml for self-hosted | **To build** | S |
| Health check endpoint | **To build** | S |
| Environment detection (HF vs local) | Partial | S |
| README with quickstart | **To build** | S |

### 7.3 Technology

| Layer | Technology | Why |
|-------|-----------|-----|
| UI | Streamlit | Rapid prototyping, Python-native, built-in widgets |
| Pipeline | Scanpy + AnnData | Industry standard for scRNA-seq |
| Batch correction | Harmony (harmonypy) | Best-in-class for multi-donor integration |
| Cell typing | CellTypist | Pre-trained models, high accuracy |
| AI (local) | Ollama + Qwen3:4b/8b | Free, runs locally, tool-calling support |
| AI (cloud) | Groq (Llama 3.3 70B) | Free tier (30 req/min), OpenAI-compatible |
| AI (paid) | Anthropic Claude | Backward compatible for users with keys |
| Audit trail | SQLite | Zero config, embeddable, append-only |
| Deployment | Docker + HuggingFace Spaces | Free hosting, 16GB RAM, persistent storage |
| Fuzzy matching | rapidfuzz | Fast Levenshtein distance for harmonization |
| Visualization | Plotly | Interactive, publication-quality charts |

### 7.4 Assumptions

**Product assumptions** (to be validated by discovery experiments):

| # | Assumption | Risk if Wrong | Validation |
|---|-----------|--------------|------------|
| A1 | Pharma wants no-code scRNA-seq | Product has no market | E1 survey |
| A18 | Open-source LLMs match Claude quality | AI features lose credibility | E10 benchmark |
| A19 | Self-hosted is a selling point | Docker distribution is wasted | E2 interviews |
| A3 | Scientists trust AI from open-source LLMs | AI copilot unused | E3 landing page |
| A22 | "Free" doesn't signal "low quality" | Pharma won't adopt | E2/E13 pricing |

**Technical assumptions**:

| Assumption | Risk if Wrong | Mitigation |
|-----------|--------------|-----------|
| Ollama runs within 16GB HF Spaces RAM | OOM crashes, slow responses | Use smaller model (qwen3:4b), fall back to Groq |
| .h5ad files under 200MB cover most use cases | Users can't upload their data | Add support for larger files in v2 (chunked upload) |
| Scanpy pipeline runs in Streamlit's single-thread model | UI freezes during processing | Use st.spinner + background processing for long steps |
| SQLite is sufficient for audit trail | Performance issues at scale | Migrate to PostgreSQL in enterprise version |
| 100K cell subsample captures biological signal | Subsampling loses rare cell types | Warn user, offer full-data mode in v2 |

---

## 8. Release

### 8.1 MVP Scope (v1.0)

**Must have** (ship or don't ship):
- [ ] Demo mode works out of the box (pre-computed data, no setup)
- [ ] .h5ad upload → QC stats + UMAP + cell type annotation
- [ ] AI copilot responds to questions (Ollama or Groq, no paid key needed)
- [ ] Harmonization with approve/reject per mapping (HItL)
- [ ] QC gates with approve/adjust thresholds (HItL)
- [ ] Full audit trail (SQLite with every parameter logged)
- [ ] Docker deployment (self-hosted, `docker compose up`)
- [ ] HuggingFace Spaces deployment (public URL)
- [ ] GitHub repo with README + MIT license

**Should have** (ship if time allows):
- [ ] Generalized target scoring for any gene (not just GIPR/GLP1R)
- [ ] Cell type label editing (rename, merge clusters)
- [ ] AI biological narrator per pipeline step
- [ ] Export audit report as PDF/HTML
- [ ] Response feedback buttons on AI copilot
- [ ] Contributing guide + 5 "good first issue" items

**Won't have** (explicitly deferred to v2+):
- [ ] Real spatial transcriptomics (Visium/CosMx/MERFISH)
- [ ] Multi-dataset management (compare two analyses)
- [ ] User authentication + role-based access
- [ ] Digital signatures (21 CFR Part 11.100)
- [ ] CDISC/SDTM export
- [ ] FastAPI backend (REST API)
- [ ] Enterprise support package (SSO, SLA)
- [ ] Plugin architecture for community extensions
- [ ] Multi-omics integration (proteomics, CITE-seq)

### 8.2 Effort Estimates

| Category | Items | Effort |
|----------|-------|--------|
| HItL approval gates (F2, F3, F4, F5) | Approve/reject UI, threshold sliders, reason-for-change, label editing | **~3-4 weeks** |
| Target scoring generalization (F6) | Any-gene scoring, external APIs, composite, scorecard UI | **~2-3 weeks** |
| AI enhancements (F5, F7) | Cell type narrator, response feedback, flagging | **~1-2 weeks** |
| Export + audit (F8) | PDF/HTML export, user identity, export approval | **~1-2 weeks** |
| Deployment + docs (F9) | docker-compose.yml, README, contributing guide, health check | **~1 week** |
| Testing + polish | E2E testing, error handling, mobile-responsive, performance | **~1-2 weeks** |
| **Total** | | **~9-14 weeks** |

### 8.3 Release Phases

**Phase 1: Core HItL + Polish (Weeks 1-4)**
- Add approval gates to harmonization, QC, processing, annotation
- Reason-for-change logging
- Interactive threshold sliders
- Polish upload flow (validation, error handling)
- Deploy to HF Spaces + publish GitHub repo

**Phase 2: Target Scoring + AI (Weeks 5-8)**
- Generalize target scoring beyond GIPR/GLP1R
- Integrate DGIdb, OpenTargets, PubMed APIs
- Composite scoring with weight adjustment UI
- AI biological narrator per step
- Copilot response feedback

**Phase 3: Export + Enterprise (Weeks 9-12)**
- PDF/HTML audit report export
- User identity logging
- docker-compose.yml with production config
- README with architecture diagram + quickstart
- Contributing guide + issue templates

### 8.4 Success Criteria for Launch

| Criteria | Threshold | How to Measure |
|----------|-----------|---------------|
| Demo loads without errors | 100% | Automated health check |
| Upload .h5ad produces results | 95% success rate for valid files | Test with 5 public datasets |
| AI copilot responds in <30s | 90th percentile | Performance monitoring |
| All HItL gates functional | 100% of approval flows work | Manual test checklist |
| Audit trail captures all events | Every parameter, decision, timestamp logged | Audit trail review |
| Docker self-hosted works | `docker compose up` → app accessible in <5 min | Cold-start test |
| GitHub repo passes quality bar | README, license, contributing, 5 issues | Checklist |

### 8.5 Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Open-source LLM quality insufficient for biology | Medium | High | E10 benchmark before launch; fall back to Groq (Llama 70B) |
| HF Spaces OOM with Ollama + Scanpy | Medium | High | Use qwen3:4b (smaller), monitor memory, Groq fallback |
| No market demand for no-code scRNA-seq | Medium | Critical | E1 survey before heavy build investment |
| "Free" perception blocks pharma adoption | Low | High | Open-core model: free community + paid enterprise support |
| Competitor ships similar features | Low | Medium | Speed advantage: we have 80% built. Ship fast. |
| Single developer = bus factor of 1 | High | High | Open-source community, comprehensive docs, clean architecture |

---

## Appendix A: Competitive Landscape

| Platform | scRNA-seq | AI | Target Scoring | Audit Trail | Self-Hosted | Free | HItL |
|----------|-----------|-----|---------------|-------------|-------------|------|------|
| Cellenics | Basic | No | No | No | No | Yes | No |
| PandaOmics | No | Yes (bulk) | Yes (gene-level) | No | No | No | No |
| CELLxGENE | View only | No | No | No | Partial | Yes | No |
| Loupe (10x) | View only | No | No | No | No | No | No |
| Benchling | No | No | No | Yes | No | No | Partial |
| Scanpy/Seurat | Deep (code) | No | No | No | Yes | Yes | No |
| **BioOrchestrator** | **Full** | **Yes** | **Yes (cell-type)** | **Yes** | **Yes** | **Yes** | **Yes** |

## Appendix B: One-Line Pitches

- **To a VP of Translational Science**: "Go from raw single-cell data to regulatory-ready target evidence in hours, not months — self-hosted, no API keys, full audit trail."
- **To a Comp Bio Director**: "Give your biologists self-service scRNA-seq analysis with governance that passes FDA inspection — runs entirely on your servers."
- **To a Biomarker Scientist**: "AI-powered target scoring at cell-type resolution — not just what gene, but what cell type, where in tissue, with what evidence."
- **To Pharma IT**: "Open-source, self-hosted, no external API calls, no data leaving your network. Docker Compose up, done."
- **To a GitHub visitor**: "Upload scRNA-seq data → get auditable, AI-interpreted analysis with drug target prioritization. No coding. No API keys. No cost."

## Appendix C: Glossary

| Term | Definition |
|------|-----------|
| scRNA-seq | Single-cell RNA sequencing — measures gene expression in individual cells |
| .h5ad | HDF5-based file format for annotated data matrices (AnnData) |
| UMAP | Uniform Manifold Approximation and Projection — dimensionality reduction for visualization |
| Leiden clustering | Community detection algorithm for identifying cell types |
| Harmony | Batch correction algorithm that integrates data from different donors/experiments |
| GIPR | Gastric Inhibitory Polypeptide Receptor — drug target in MariTide (Amgen's obesity drug) |
| GLP1R | Glucagon-Like Peptide 1 Receptor — drug target in GLP-1 agonists (e.g., Ozempic) |
| CDISC/SDTM | Clinical Data Interchange Standards for regulatory submissions |
| 21 CFR Part 11 | FDA regulation for electronic records and signatures |
| HItL | Human-in-the-Loop — AI proposes, human approves |
| GxP | Good Practice regulations (GLP, GCP, GMP) |
| CRO | Contract Research Organization — service provider for pharma |
| Ollama | Open-source tool for running LLMs locally |
| Groq | Cloud inference provider with free tier for open-source LLMs |
