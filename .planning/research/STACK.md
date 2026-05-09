# Technology Stack

**Project:** BioOrchestrator v2 -- Drug Target Intelligence Platform
**Researched:** 2026-05-09
**Confidence:** HIGH (versions verified via live PyPI index)

## Current State Assessment

The existing codebase (`bioorchestrator_real/`) uses Python 3.11, Scanpy 1.10.3, Streamlit >=1.32, and a custom LLM provider abstraction supporting Ollama/Groq/Anthropic with tool-calling. Several packages are 1-2 major versions behind current. The v2 upgrade path is evolutionary, not revolutionary -- upgrade versions, add new capability layers (evidence APIs, scoring framework, compliance), and keep the architecture that already works.

**Critical constraint:** 8GB RAM on the development machine. Every dependency must justify its memory footprint.

## Recommended Stack

### Core Runtime

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| Python | 3.11.x | Runtime | Already in use. 3.12 is fine too, but 3.13 is blocked by cellxgene-census (TileDB-SOMA dependency). Stay on 3.11 for maximum bio-stack compatibility. | HIGH |
| conda (miniforge) | latest | Environment management | Required for numba/llvmlite binary packages. Pip-only installs fail on Apple Silicon for these. Already in use via `environment.yml`. | HIGH |

### scRNA-seq Analysis Core

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| scanpy | **1.12.1** | scRNA-seq analysis pipeline | Industry standard for single-cell analysis. v1.12 adds performance improvements and better AnnData 0.11+ integration. Upgrade from 1.10.3 (2 minor versions behind). | HIGH |
| anndata | **0.11.4** | Single-cell data structures | v0.12.x has breaking API changes still settling (new backed storage system). 0.11.4 is the last stable pre-0.12 release and the safest upgrade target. Upgrade from 0.10.9. | HIGH |
| cellxgene-census | **1.17.0** | CellxGene data access | Keep current. Version is locked to the Census data schema. Don't upgrade unless Census schema version changes. | HIGH |
| celltypist | **1.7.1** | Automated cell type annotation | Upgrade from 1.6.3. v1.7 adds new pre-trained models and improved annotation accuracy. sklearn-based, lightweight. | HIGH |
| harmonypy | **0.0.10** | Batch correction | **Stay on 0.0.10**. v2.0.0 is a complete rewrite with breaking API changes (version jump from 0.0.10 to 2.0.0). The existing integration is validated and working. | MEDIUM |
| scrublet | **0.2.3** | Doublet detection | Keep current. Package is stable but unmaintained. Works correctly for doublet scoring. No viable lightweight replacement. | HIGH |
| leidenalg | **0.10.2** | Leiden clustering | Keep current. v0.11.0 may have API changes with igraph 1.0. Stable at 0.10.2 with current scanpy version. | MEDIUM |
| python-igraph | **0.11.8** | Graph algorithms | Upgrade from 0.11.6 for bug fixes, but **do not jump to 1.0.0** which renames internal imports. leidenalg 0.10.x depends on python-igraph <1.0. | HIGH |
| numpy | **1.26.4** | Numerical computing | **Do NOT upgrade to 2.x**. Multiple bio-stack packages (scrublet, older scanpy internals, cellxgene-census) have numpy 2.x incompatibilities. 1.26.4 is the last 1.x release and the safe choice. | HIGH |
| scipy | **1.13.1** | Scientific computing | Keep current. Compatible with numpy 1.26.x. | HIGH |
| pandas | **2.2.2** | Data manipulation | Keep current. Stable, well-tested with the bio-stack. | HIGH |

### External Evidence API Integration

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| httpx | **0.28.1** | HTTP client (async + sync) | Replace `requests` for new API clients. httpx supports async (for parallel API fetching across 6 evidence sources), connection pooling, HTTP/2, and proper timeout configuration. Keep `requests` for existing code; use httpx for new evidence layer. | HIGH |
| gql | **4.0.0** | GraphQL client | For Open Targets Platform API (GraphQL-based). v4.0 supports async transport via httpx, batched queries, and automatic retry. Much cleaner than raw POST requests to a GraphQL endpoint. Install with `gql[httpx]`. | MEDIUM |
| chembl-webresource-client | **0.10.9** | ChEMBL REST API | Official EBI-maintained Python client. Handles pagination, filtering, and data serialization for compound/target/activity queries. Better than building raw HTTP calls. | MEDIUM |
| biopython | **1.87** | PubMed/NCBI Entrez access | Industry standard for PubMed search via `Bio.Entrez`. Handles API keys, rate limiting (3 req/sec with key, 1/sec without), and XML parsing. Also useful for UniProt sequence data parsing via `Bio.SeqIO`. | HIGH |
| tenacity | **9.1.4** | Retry with backoff | Decorator-based retry with exponential backoff. Essential for external APIs: PubMed has strict rate limits, ClinicalTrials.gov has intermittent timeouts, Open Targets occasionally 503s. Lightweight, no side effects. | HIGH |

### LLM Integration

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| anthropic | **>=0.95.0** | Anthropic Claude API | Official SDK. v0.95+ includes latest tool-calling features, extended thinking support, and batch API. The existing `llm_provider.py` already uses this SDK. Pin floor, not ceiling -- SDK is backward-compatible. | HIGH |
| ollama | **>=0.6.0** | Local LLM inference | Official Python client. v0.6 has significantly improved tool-calling support. Critical for offline/air-gapped pharma environments where data cannot leave the network. | HIGH |
| openai | **>=2.30.0** | OpenAI-compatible API client | Used by Groq SDK under the hood. Also the standard client for any OpenAI-compatible endpoint (vLLM, Together, local deployments). Provides structured output support. | HIGH |
| groq | **>=1.0.0** | Groq cloud inference | Fast inference for iterative development. v1.0+ is a major rewrite built on the openai SDK with better tool-calling support. | MEDIUM |
| pydantic | **>=2.11.0** | Data validation and schemas | Use for: (1) structured LLM output parsing, (2) API response validation, (3) scoring framework data models, (4) audit trail records, (5) configuration management. Pydantic v2 is 5-50x faster than v1 with Rust-based validation core. | HIGH |

### Compliance and Audit

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| SQLite (stdlib) | 3.x | Audit trail database | Already in use for lineage DB. Zero dependencies, ACID-compliant, handles 21 CFR Part 11 immutable audit logging. Enable WAL mode for concurrent reads during Streamlit sessions. No need for PostgreSQL at solo-dev scale. | HIGH |
| structlog | **>=25.0.0** | Structured logging | JSON-structured logs for compliance. Integrates with stdlib logging. Adds automatic context binding (run_id, stage, user_id, timestamp) to every log entry. Critical for GxP audit trails beyond the SQLite lineage DB -- regulators want searchable log files. | MEDIUM |
| hashlib (stdlib) | 3.x | SHA-256 checksums | Already in use for data integrity verification in stage7_lineage.py. No external dependency needed. | HIGH |
| uuid (stdlib) | 3.x | Unique identifiers | Already in use for run_id generation. | HIGH |

### UI and Visualization

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| streamlit | **>=1.44** | Web UI framework | Upgrade floor from 1.32 to 1.44. Key features: `st.fragment` (partial reruns -- essential for long-running scientific workflows), `st.dialog` (modal confirmations for destructive actions), improved caching with `st.cache_data`/`st.cache_resource`. | HIGH |
| plotly | **5.24.1** | Interactive charts | **Stay on 5.x**. Plotly 6.x is a major rewrite (merged plotly.express into main, new rendering engine). Streamlit's `st.plotly_chart` integration is built around Plotly 5.x patterns. Upgrade to 6.x only after explicit Streamlit 6.x support is confirmed. | MEDIUM |
| jinja2 | **>=3.1.6** | Template rendering | For dossier HTML generation (which then converts to PDF). Upgrade from 3.1.4 for security patches. | HIGH |
| fpdf2 | **>=2.8.0** | PDF generation | Lightweight PDF generation for consulting-grade dossiers. No system dependencies (unlike weasyprint which needs Cairo/Pango). Pure Python, embeds images/charts, supports tables and styling. Fits the 8GB RAM constraint. | MEDIUM |

### Data and Utility Libraries

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| rapidfuzz | **>=3.14.0** | Fuzzy string matching | Already in use for metadata harmonization. Upgrade from 3.9.7 for performance improvements. C++ backend is fast. | HIGH |
| rich | **>=13.7.0** | CLI output formatting | Keep current. Used for pipeline console output with panels, tables, and progress bars. | HIGH |
| tqdm | **>=4.66.0** | Progress bars | Keep current. Used for pipeline stage progress. | HIGH |
| seaborn | **0.13.2** | Statistical plots | Keep current. Used for static plot generation in the pipeline. | HIGH |
| matplotlib | **>=3.9.0** | Base plotting | Keep current. Required by scanpy for backend plotting and figure generation. | HIGH |

### Development and Testing

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| pytest | **>=8.3.0** | Test framework | Use 8.x (stable, well-supported). 9.x is very new (May 2026) -- let it stabilize. |
| pytest-asyncio | latest | Async test support | For testing async API clients (httpx, gql async transport). |
| ruff | latest | Linting + formatting | Replaces flake8 + black + isort with a single Rust-based tool. 10-100x faster. |
| mypy | latest | Type checking | Critical for Pydantic models and pipeline data flow type safety. |
| pre-commit | latest | Git hooks | Run ruff + mypy checks before commit for consistent code quality. |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| LLM Framework | Custom provider abstraction | **LangChain** | Adds ~200MB of transitive dependencies, abstracts away the tool-calling control needed for multi-step scientific reasoning, and has frequent breaking changes (monthly major releases). The existing `llm_provider.py` is 300 lines, does exactly what's needed, and has zero extra dependencies. On 8GB RAM, every MB counts. |
| LLM Framework | Custom provider abstraction | **LlamaIndex** | Designed for RAG/retrieval pipelines, not tool-calling scientific reasoning. Would force the architecture into a retrieval paradigm that doesn't match the evidence integration + reasoning pattern. |
| HTTP Client | httpx | **aiohttp** | aiohttp is async-only (no sync mode), has a more complex API with explicit session management, and is harder to debug. httpx supports both sync and async with the same interface -- better fit for a codebase that mixes sync (Streamlit callbacks) and async (parallel API calls). |
| GraphQL Client | gql | **sgqlc** | sgqlc generates typed Python classes from GraphQL schema (code generation step). Overkill for querying one API (Open Targets). gql is simpler, has the best async support, and most active maintenance. |
| PDF Generation | fpdf2 | **weasyprint** | weasyprint requires system-level Cairo and Pango C libraries, which are painful to install on macOS and problematic in containerized deployments. fpdf2 is pure Python, handles professional tables and embedded images, and produces clean PDFs. |
| PDF Generation | fpdf2 | **reportlab** | reportlab's open-source version has limited features (no proper table styling). The commercial version is expensive. fpdf2 is fully open-source with a simpler API. |
| Database | SQLite | **PostgreSQL** | Solo developer, single-machine deployment. PostgreSQL adds operational complexity (installation, configuration, backup management) with zero benefit at this scale. SQLite with WAL mode handles concurrent reads during Streamlit sessions. |
| Cell Annotation | celltypist | **scANVI (scvi-tools)** | scvi-tools requires PyTorch (~2GB disk, ~1-2GB RAM at runtime), which would consume 25-50% of available RAM before any data is loaded. CellTypist is sklearn-based, lightweight (<50MB), and has good pre-trained models for human tissues. |
| Batch Correction | harmonypy | **scanorama** | Scanorama uses a mutual nearest neighbors approach that requires more RAM for large datasets. Harmony is faster, validated for atlas-scale data, and already integrated. |
| Data Validation | pydantic | **dataclasses + marshmallow** | Pydantic v2 is faster than marshmallow, has built-in JSON serialization, integrates naturally with LLM SDK output parsing, and provides better error messages. Raw dataclasses lack validation entirely. |
| Structured Logging | structlog | **loguru** | loguru produces prettier console output but less structured machine-parseable logs. For 21 CFR Part 11 compliance, you need JSON-structured logs that can be ingested by audit tools. structlog produces proper JSON by default. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **LangChain** | Massive dependency tree, constant breaking changes, abstracts away tool-calling control needed for scientific reasoning chains. Overkill for this use case. | Direct SDK calls (anthropic, openai, ollama) via existing provider abstraction |
| **numpy 2.x** | Breaks scrublet (uses deprecated numpy.float), has compatibility issues with cellxgene-census and older scanpy C extensions. The bio-stack is still catching up to numpy 2. | numpy 1.26.4 |
| **python-igraph 1.0.0** | Package renamed from `igraph` to `python-igraph`, breaks leidenalg 0.10.x imports that expect the old module structure. | python-igraph 0.11.8 |
| **harmonypy 2.0.0** | Version jump from 0.0.10 to 2.0.0 signals a complete rewrite. Risk of regression in batch correction results that are already validated against known biology. | harmonypy 0.0.10 |
| **Plotly 6.x** | Major rewrite with merged plotly.express. Streamlit `st.plotly_chart` integration status with 6.x is unconfirmed. | Plotly 5.24.1 |
| **weasyprint** | Requires system Cairo/Pango C libraries. Installation hell on macOS, problematic in Docker containers. | fpdf2 (pure Python) |
| **FastAPI** | Not needed for a Streamlit-based application. Adding a REST API layer increases complexity without clear value for a solo-developer internal tool. If API exposure is needed later, Streamlit components can handle it. | Streamlit only |
| **Docker (initially)** | Premature complexity for a solo developer iterating fast. conda environment is sufficient for development. Containerize after the platform architecture stabilizes. | conda environment |
| **scvi-tools / PyTorch** | PyTorch alone is ~2GB on disk, ~1-2GB RAM at runtime. On 8GB total RAM with AnnData objects holding 60K cells, this leaves no headroom for the actual analysis. | CellTypist (sklearn-based, <50MB) |
| **requests (for new code)** | No async support, no HTTP/2, no built-in connection pooling. Fine for existing code, but new evidence API clients should use httpx for parallel fetching. | httpx (for new code) |

## Stack Patterns by Variant

**If deploying to pharma IT (air-gapped network):**
- Use Ollama exclusively for LLM inference (no cloud API calls)
- Bundle all pip packages in a wheelhouse directory (`pip download -d ./wheelhouse -r requirements.txt`)
- Use `pip install --no-index --find-links=./wheelhouse -r requirements.txt` for offline installation
- Pre-download CellTypist models to `~/.celltypist/data/models/`
- Pre-cache CellxGene Census data as local .h5ad files

**If running on a machine with 16GB+ RAM:**
- Consider anndata 0.12.x (backed by more efficient on-disk formats via TileDB)
- Could add scvi-tools for advanced batch integration (scANVI) and latent representations
- Increase `DEFAULT_N_CELLS` in config.py to 100K+ for full atlas analysis
- Consider numpy 2.x if all bio-stack dependencies have been updated

**If adding multi-user support later:**
- Replace SQLite with PostgreSQL for concurrent writes
- Add streamlit-authenticator for user login
- Add session-scoped state management via `st.session_state` namespacing
- Consider Redis for caching shared computation results

## Version Compatibility Matrix

| Package A | Compatible With | Incompatible With | Notes |
|-----------|-----------------|-------------------|-------|
| scanpy 1.12.1 | anndata >=0.10, <=0.11.x; numpy 1.26.x | numpy 2.x (some internal C extensions) | Test thoroughly if upgrading anndata |
| cellxgene-census 1.17.0 | Python 3.10-3.12 | Python 3.13+ | Hard requirement from TileDB-SOMA backend |
| leidenalg 0.10.2 | python-igraph >=0.10, <1.0 | python-igraph 1.0.0 | Import name change in igraph 1.0 breaks leidenalg |
| scrublet 0.2.3 | numpy <2.0 | numpy 2.x | Uses deprecated `numpy.float` type alias |
| anthropic >=0.95 | pydantic >=2.0 | pydantic 1.x | SDK uses pydantic v2 models internally |
| streamlit >=1.44 | plotly 5.x | plotly 6.x (unconfirmed) | `st.plotly_chart` rendering assumptions |
| gql 4.0.0 | httpx 0.28.x (via `gql[httpx]`) | requests transport (deprecated in gql 4) | Use httpx transport for async support |

## Installation

```bash
# Create environment (using conda for binary packages)
conda create -n bioorchestrator python=3.11 -y
conda activate bioorchestrator

# Binary packages that need conda (avoid LLVM/cmake source builds)
conda install -c conda-forge numba llvmlite hdf5 -y

# Core bioinformatics
pip install \
    scanpy==1.12.1 \
    anndata==0.11.4 \
    cellxgene-census==1.17.0 \
    celltypist==1.7.1 \
    harmonypy==0.0.10 \
    scrublet==0.2.3 \
    leidenalg==0.10.2 \
    python-igraph==0.11.8

# Numerical / data (pin numpy to 1.x!)
pip install \
    "numpy==1.26.4" \
    scipy==1.13.1 \
    pandas==2.2.2

# LLM integration
pip install \
    "anthropic>=0.95.0" \
    "ollama>=0.6.0" \
    "openai>=2.30.0" \
    "groq>=1.0.0" \
    "pydantic>=2.11.0"

# Evidence API clients
pip install \
    "httpx>=0.28.0" \
    "gql[httpx]>=4.0.0" \
    "chembl-webresource-client>=0.10.9" \
    "biopython>=1.87" \
    "tenacity>=9.0.0"

# UI and visualization
pip install \
    "streamlit>=1.44" \
    plotly==5.24.1 \
    matplotlib==3.9.2 \
    seaborn==0.13.2

# Reporting and compliance
pip install \
    "fpdf2>=2.8.0" \
    "jinja2>=3.1.6" \
    "structlog>=25.0.0" \
    "rapidfuzz>=3.14.0" \
    "rich>=13.7.0" \
    "tqdm>=4.66.0"

# Dev dependencies
pip install \
    "pytest>=8.3.0" \
    pytest-asyncio \
    ruff \
    mypy \
    pre-commit
```

## Sources

- **PyPI package index** (`pip index versions`) -- verified 2026-05-09 -- HIGH confidence for all version numbers
- **Existing codebase** (`bioorchestrator_real/environment.yml`, `config.py`, `llm_provider.py`, `ai_copilot.py`, `stage7_lineage.py`) -- HIGH confidence for current state assessment
- **Training data** for ecosystem patterns (LangChain vs direct SDK tradeoffs, bio-stack compatibility, Plotly 5 vs 6 differences) -- MEDIUM confidence, based on well-established community patterns but not web-verified today
- **numpy 2.x bio-stack incompatibility** -- MEDIUM confidence (well-documented in scanpy/anndata issue trackers per training data, consistent with scrublet's use of deprecated numpy.float)
- **Plotly 6.x / Streamlit compatibility** -- LOW confidence (unable to verify via web search; recommendation to stay on 5.x is the conservative safe path)
- **harmonypy 2.0.0 breaking changes** -- LOW confidence (inferred from major version jump 0.0.10 -> 2.0.0, not verified with changelog; conservative recommendation to stay on 0.0.10)

---
*Stack research for: pharma drug target intelligence platform*
*Researched: 2026-05-09*
