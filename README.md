# BioOrchestrator v2

**AI-powered drug target intelligence platform for pharmaceutical R&D**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![21 CFR Part 11](https://img.shields.io/badge/compliance-21%20CFR%20Part%2011-green.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## The Problem

Drug target identification is the highest-stakes, most manual step in pharmaceutical R&D. A team of 3–5 computational biologists spends **2–4 weeks** manually triaging a single target across disconnected databases — OpenTargets, PubMed, ChEMBL, ClinicalTrials.gov, DGIdb, UniProt — before producing a GO/NO-GO recommendation.

Wrong decisions here cost $100M–$2.6B and years of failed development.

## The Solution

BioOrchestrator replaces that manual process with a single, auditable AI workflow:

```
Gene Symbol → Evidence Aggregation → AI Reasoning → 7-Dimension Scorecard → GO / NO-GO
```

**In 15 minutes. With a 21 CFR Part 11 compliant audit trail.**

---

## Platform Overview

```
┌─────────────────────────────────────────────────────────┐
│                   BioOrchestrator v2                    │
├──────────────┬──────────────┬───────────────────────────┤
│  Omics       │  Evidence    │  AI Reasoning             │
│  Pipeline    │  Explorer    │  Engine                   │
│              │              │                           │
│  scRNA-seq   │  6 live DBs  │  5 parallel LLM modes     │
│  QC → DE →   │  OpenTargets │  Hypothesis               │
│  Enrichment  │  PubMed      │  Synthesis                │
│              │  ChEMBL      │  Contradiction             │
│  HITL gates  │  DGIdb       │  Gap Analysis             │
│  at each     │  UniProt     │  Confidence               │
│  stage       │  ClinTrials  │                           │
├──────────────┴──────────────┴───────────────────────────┤
│               Scoring Framework                         │
│  Genetic Evidence · Druggability · Safety · Expression  │
│  Competitive Landscape · Clinical · Literature          │
│              GO / CONDITIONAL / NO-GO                   │
├─────────────────────────────────────────────────────────┤
│    21 CFR Part 11 Audit Trail · E-Signatures · GxP      │
└─────────────────────────────────────────────────────────┘
```

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Omics Pipeline** | scRNA-seq QC → normalization → clustering → DE → pathway enrichment |
| **Evidence Aggregation** | 6 databases queried in parallel with graceful degradation |
| **AI Reasoning** | 5 LLM modes with agentic tool-calling loop (up to 10 rounds) |
| **7-Dimension Scoring** | Genetic, druggability, safety, expression, competitive, clinical, literature |
| **HITL Gates** | Human-in-the-loop approval at every critical decision point |
| **GxP Compliance** | 21 CFR Part 11 hash-chain audit trail with electronic signatures |
| **Showcase Scenarios** | 6 pre-loaded pharma targets: EGFR, ESR1, PIK3CA, GLP1R, PARP1, CD274 |
| **Dual Mode** | Exploration (auto-approve) or Compliance (e-signature required) |

---

## Quick Start

### Option 1 — macOS One-Click App

```bash
# Run once to create BioOrchestrator v2.app on your Desktop
bash bioorchestrator_real/create_app.sh

# Then double-click the app icon
```

### Option 2 — Local (Streamlit)

```bash
# Install dependencies
pip install -r requirements.txt

# Add your API key
cp .env.example .env
# Edit .env: ANTHROPIC_API_KEY=sk-ant-...

# Generate showcase data (one-time)
python scripts/generate_showcase_data.py

# Launch
streamlit run src/app.py
```

### Option 3 — Docker

```bash
docker compose up
# Open http://localhost:8501
```

---

## Deploy to Streamlit Community Cloud (Free)

1. Fork this repo to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app
3. Select your fork → Branch: `main` → Main file: `src/app.py`
4. Under **Advanced settings** → change requirements file to `requirements-cloud.txt`
5. Under **Secrets**, add:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-your-key-here"
   ```
6. Click **Deploy**

> The 6 pharma showcase scenarios run without any API key. The AI Insights page requires `ANTHROPIC_API_KEY`.

---

## Architecture

```
src/
├── app.py                    # Streamlit entry point + navigation
├── auth/                     # Login, registration, session management
├── pages/
│   ├── home.py               # Landing page with platform overview
│   ├── projects.py           # Project lifecycle + showcase loader
│   ├── omics.py              # scRNA-seq pipeline + 3 HITL gates
│   ├── evidence.py           # 6-source evidence aggregation
│   ├── insights.py           # AI reasoning (5 modes)
│   ├── scorecard.py          # GO/NO-GO verdict + dossier export
│   └── audit.py              # Compliance audit trail
├── reasoning/
│   ├── engine.py             # ReasoningEngine orchestrator
│   ├── tool_loop.py          # Agentic tool-calling loop (10 rounds)
│   ├── fallback.py           # Multi-provider LLM fallback chain
│   └── prompts.py            # Versioned prompt registry
├── evidence/
│   ├── aggregator.py         # 2-phase parallel fetch
│   └── sources/              # OpenTargets, DGIdb, PubMed, UniProt, ChEMBL, ClinicalTrials
├── scoring/
│   ├── framework.py          # ScoringFramework orchestrator
│   └── dimensions.py         # 7 dimension scorers
├── pipeline/                 # scRNA-seq pipeline stages
└── compliance/
    ├── audit_trail.py        # SHA-256 hash-chain records
    └── electronic_signature.py
```

---

## Pharma Showcase Scenarios

| Target | Indication | Reference |
|--------|------------|-----------|
| **EGFR** | Non-Small Cell Lung Cancer | AstraZeneca Tagrisso |
| **ESR1** | ER+ Breast Cancer | AstraZeneca Faslodex |
| **PIK3CA** | HR+ Breast Cancer | Roche Piqray |
| **GLP1R** | Obesity / T2D | Eli Lilly Mounjaro |
| **PARP1** | BRCA+ Breast Cancer | Merck Lynparza |
| **CD274** | Pan-cancer Immunotherapy | Merck Keytruda |

---

## For Biotech Teams

Looking to accelerate your target identification process? I offer:

- **Paid POC** ($15K–$25K): Run BioOrchestrator on your top 3 targets in 2 weeks
- **SaaS License** ($2,500–$8,000/month): Full platform for your computational biology team
- **Consulting** ($150–$250/hr): Custom AI pipeline development for drug discovery workflows

**Contact:** [LinkedIn](https://linkedin.com) | [Email](mailto:your@email.com)

---

## Tech Stack

Python 3.11 · Streamlit 1.56 · Anthropic Claude · Scanpy · Anndata · SQLite · Docker

---

## License

MIT — see [LICENSE](LICENSE)
