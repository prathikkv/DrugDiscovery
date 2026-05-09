# Phase 2: Omics Pipeline - Research

**Researched:** 2026-05-10
**Domain:** Disease-agnostic scRNA-seq analysis pipeline (scanpy/anndata ecosystem)
**Confidence:** HIGH

## Summary

Phase 2 transforms the existing hardcoded adipose/MariTide pipeline (in `bioorchestrator_real/`) into a disease-agnostic, tissue-configurable scRNA-seq pipeline integrated with the Phase 1 infrastructure (TaskManager, AuditTrail, ProjectService). The existing code provides a strong reference for the scanpy processing flow (QC -> normalize -> HVG -> PCA -> Harmony -> neighbors -> UMAP -> Leiden -> CellTypist), but every stage contains hardcoded biology that must be parameterized.

The core challenge is threefold: (1) building a multi-format ingestion layer that handles .h5ad, CellRanger .h5, and 10x MTX folders uniformly, (2) making every pipeline parameter configurable per-project with tissue-specific defaults, and (3) integrating ambient RNA removal (SoupX via rpy2) as an optional preprocessing step with a HITL gate. The existing `bioorchestrator_real/` code is a direct blueprint -- the new `src/pipeline/` module will refactor it for configurability, remove all GIPR/GLP1R/adipose/MariTide references, and wire each stage into the TaskManager for progress reporting and checkpoint persistence.

**Primary recommendation:** Structure the pipeline as a series of composable stage functions under `src/pipeline/`, with a `PipelineConfig` dataclass that holds all configurable parameters including tissue-specific QC defaults. Use gseapy (not decoupler) for gene set enrichment because decoupler 2.1.6 requires Python >=3.11 and this project is pinned to Python 3.10. Wire each stage to call `task_manager.update_progress()` at stage boundaries and save checkpoint .h5ad files to the project's `checkpoints/` directory.

## Standard Stack

### Core (already in requirements.txt)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scanpy | >=1.10.0,<1.11 | Full scRNA-seq pipeline (QC metrics, normalize, HVG, PCA, neighbors, UMAP, Leiden, DE) | Industry standard for Python scRNA-seq; already pinned in requirements.txt |
| anndata | >=0.10.0 | Data container (.h5ad read/write, backed mode, layers) | Required by scanpy; the universal scRNA-seq data format |
| h5py | >=3.10.0 | Reading CellRanger HDF5 (.h5) files | Already in requirements.txt; needed for 10x .h5 format |
| scipy | >=1.9.0 | Sparse matrix operations, statistical tests | Already in requirements.txt; required by scanpy |
| numpy | >=1.23,<2.0 | Array operations | Already pinned; numpy 2.0 excluded for compatibility |
| harmonypy | >=0.0.10 | Batch correction | Already in requirements.txt; used in existing stage4 |

### New Dependencies Required
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| celltypist | >=1.7.0 | Automated cell type annotation with pre-trained models | Stage: annotation. Requires log1p-normalized data at 10K counts/cell |
| gseapy | >=1.1.0 | Over-Representation Analysis (ORA) and GSEA for gene set enrichment | Stage: enrichment (REQ-106). Python-native, no R dependency, works on Python 3.10 |
| scrublet | >=0.2.3 | Doublet detection per sample | Stage: QC. Already used in existing code (optional import) |
| rpy2 | >=3.5.0 | Python-to-R bridge for calling SoupX | Stage: ambient RNA removal (REQ-103). Requires R installation with SoupX package |
| leidenalg | >=0.9.0 | Leiden community detection algorithm | Required by celltypist and scanpy's sc.tl.leiden |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| gseapy (ORA) | decoupler | decoupler 2.1.6 requires Python >=3.11; project pinned to 3.10. decoupler 2.1.4 works on 3.10 but is outdated. gseapy has broader method coverage (GSEA, ORA, ssGSEA, enrichr) and no Python version conflict |
| SoupX via rpy2 | CellBender | CellBender is Python-native but requires PyTorch/Pyro (heavy dependencies, GPU preferred). REQ-103 specifies SoupX as primary with CellBender as option. Keep CellBender as optional fallback |
| harmonypy | scvi-tools/scanorama | harmonypy is lightweight, already in requirements.txt, proven in existing pipeline. scvi-tools adds PyTorch dependency |

**Installation (additions to requirements.txt):**
```bash
celltypist>=1.7.0
gseapy>=1.1.0
scrublet>=0.2.3
rpy2>=3.5.0
leidenalg>=0.9.0
```

**R dependency (for SoupX):**
```bash
# R package installation (needed for REQ-103)
R -e "install.packages('SoupX', repos='https://cloud.r-project.org')"
```

## Architecture Patterns

### Recommended Project Structure
```
src/
  pipeline/
    __init__.py              # Public API: run_pipeline(), PipelineConfig
    config.py                # PipelineConfig dataclass + tissue defaults registry
    ingestion.py             # Multi-format ingest: .h5ad, .h5, 10x MTX
    ambient_rna.py           # SoupX (rpy2) + CellBender option + skip gate
    qc.py                    # Configurable QC with tissue-specific thresholds
    processing.py            # normalize -> HVG -> PCA -> Harmony -> neighbors -> UMAP -> Leiden
    annotation.py            # CellTypist with tissue-aware model selection + marker validation
    differential_expression.py  # sc.tl.rank_genes_groups wrapper with configurable method/correction
    enrichment.py            # Gene set enrichment via gseapy ORA per cell type
    checkpointing.py         # Save/load intermediate .h5ad at stage boundaries
    progress.py              # TaskManager integration for stage-level progress callbacks
```

### Pattern 1: PipelineConfig Dataclass with Tissue Defaults
**What:** A single `PipelineConfig` dataclass that holds all configurable parameters, with a `TISSUE_DEFAULTS` registry providing tissue-specific presets.
**When to use:** Every pipeline invocation. The config is created at project setup and stored as JSON in the project's `config_json` field.
**Example:**
```python
# Source: Derived from existing bioorchestrator_real/config.py patterns
from dataclasses import dataclass, field, asdict
from typing import Optional
import json

TISSUE_DEFAULTS = {
    "brain": {"max_pct_mt": 5.0, "celltypist_model": "Developing_Human_Brain.pkl"},
    "tumor": {"max_pct_mt": 25.0, "celltypist_model": "Immune_All_Low.pkl"},
    "lung": {"max_pct_mt": 10.0, "celltypist_model": "Human_Lung_Atlas.pkl"},
    "immune": {"max_pct_mt": 10.0, "celltypist_model": "Immune_All_Low.pkl"},
    "heart": {"max_pct_mt": 10.0, "celltypist_model": "Healthy_Adult_Heart.pkl"},
    "adipose": {"max_pct_mt": 20.0, "celltypist_model": "Immune_All_Low.pkl"},
    "kidney": {"max_pct_mt": 10.0, "celltypist_model": "Human_Kidney.pkl"},
    "liver": {"max_pct_mt": 10.0, "celltypist_model": "Human_Liver.pkl"},
    "intestine": {"max_pct_mt": 15.0, "celltypist_model": "Human_Intestine.pkl"},
    "eye": {"max_pct_mt": 10.0, "celltypist_model": "Human_IPF_Lung.pkl"},
    # Fallback for unrecognized tissues
    "default": {"max_pct_mt": 15.0, "celltypist_model": "Immune_All_Low.pkl"},
}

@dataclass
class QCConfig:
    min_genes: int = 200
    max_genes: int = 8000
    max_pct_mt: float = 15.0  # Overridden by tissue default
    doublet_threshold: float = 0.25
    min_cells_per_gene: int = 3
    female_marker: str = "XIST"
    male_markers: list[str] = field(default_factory=lambda: ["RPS4Y1", "DDX3Y", "KDM5D"])
    sex_expr_threshold: float = 0.5

@dataclass
class ProcessingConfig:
    normalize_total_target: float = 1e4
    n_top_hvgs: int = 3000
    batch_key: str = "donor_id"
    n_pcs: int = 50
    n_pcs_neighbors: int = 30
    n_neighbors: int = 15
    leiden_resolution: float = 0.5
    n_jobs: int = 2

@dataclass
class PipelineConfig:
    tissue_type: str = "default"
    qc: QCConfig = field(default_factory=QCConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    celltypist_model: Optional[str] = None  # Auto-selected if None
    de_method: str = "wilcoxon"
    de_corr_method: str = "benjamini-hochberg"
    skip_ambient_rna: bool = False
    ambient_rna_method: str = "soupx"  # "soupx" or "cellbender"
    enrichment_gene_sets: list[str] = field(
        default_factory=lambda: ["GO_Biological_Process_2023", "KEGG_2021_Human"]
    )

    @classmethod
    def for_tissue(cls, tissue: str, **overrides) -> "PipelineConfig":
        """Create a config with tissue-specific defaults."""
        defaults = TISSUE_DEFAULTS.get(tissue, TISSUE_DEFAULTS["default"])
        qc = QCConfig(max_pct_mt=defaults["max_pct_mt"])
        cfg = cls(
            tissue_type=tissue,
            qc=qc,
            celltypist_model=defaults["celltypist_model"],
        )
        # Apply any user overrides
        for key, val in overrides.items():
            if hasattr(cfg, key):
                setattr(cfg, key, val)
        return cfg

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "PipelineConfig":
        data = json.loads(json_str)
        qc = QCConfig(**data.pop("qc", {}))
        proc = ProcessingConfig(**data.pop("processing", {}))
        return cls(qc=qc, processing=proc, **data)
```

### Pattern 2: Stage Function Protocol
**What:** Each pipeline stage is a standalone function that takes `(adata, config, project_dir, task_manager, task_id)` and returns `(adata, stage_report)`. Stage functions call `task_manager.update_progress()` and save checkpoints.
**When to use:** Every stage implementation.
**Example:**
```python
# Source: Refactored from bioorchestrator_real/pipeline/stage3_qc.py
def run_qc(
    adata: ad.AnnData,
    config: PipelineConfig,
    project_dir: Path,
    task_manager: TaskManager = None,
    task_id: str = None,
) -> tuple[ad.AnnData, dict]:
    """Apply QC filters. Returns (filtered_adata, qc_report)."""
    # Check for checkpoint
    checkpoint_path = project_dir / "checkpoints" / "post_qc.h5ad"
    if checkpoint_path.exists():
        return ad.read_h5ad(checkpoint_path), _load_report(project_dir, "qc")

    # ... QC logic using config.qc.max_pct_mt, etc. ...

    # Progress callback
    if task_manager and task_id:
        task_manager.update_progress(task_id, 0.3, str(checkpoint_path))

    # Save checkpoint
    adata.write_h5ad(checkpoint_path)
    return adata, report
```

### Pattern 3: Multi-Format Ingestion with Format Detection
**What:** A unified `ingest()` function that detects input format and routes to the appropriate scanpy reader.
**When to use:** Data upload entry point (REQ-102).
**Example:**
```python
# Source: scanpy official API (verified)
def ingest(input_path: Path) -> ad.AnnData:
    """Load scRNA-seq data from any supported format."""
    if input_path.suffix == ".h5ad":
        return sc.read_h5ad(str(input_path))
    elif input_path.suffix == ".h5":
        # CellRanger HDF5 format
        return sc.read_10x_h5(str(input_path), gex_only=True)
    elif input_path.is_dir():
        # 10x folder with matrix.mtx.gz + barcodes.tsv.gz + features.tsv.gz
        return sc.read_10x_mtx(str(input_path), var_names="gene_symbols",
                               make_unique=True, gex_only=True)
    else:
        raise ValueError(f"Unsupported format: {input_path.suffix}")
```

### Pattern 4: SoupX via rpy2 with Graceful Fallback
**What:** Call SoupX's R functions through rpy2, with a skip-with-warning HITL gate if R/SoupX is not available.
**When to use:** Ambient RNA removal stage (REQ-103).
**Example:**
```python
# Source: rpy2 bridge pattern for R package calling
def remove_ambient_rna_soupx(
    raw_counts_path: Path,    # Unfiltered (raw) count matrix
    filtered_adata: ad.AnnData,
    clusters: pd.Series,
) -> ad.AnnData:
    """Run SoupX ambient RNA removal via rpy2."""
    try:
        import rpy2.robjects as ro
        from rpy2.robjects import pandas2ri, numpy2ri
        from rpy2.robjects.packages import importr
        pandas2ri.activate()
        numpy2ri.activate()

        soupx = importr("SoupX")

        # SoupX requires: raw (unfiltered) counts, filtered counts, clusters
        # Convert sparse matrices to R-compatible format
        # sc = SoupChannel(tod=filtered_counts, toc=raw_counts)
        # sc = setClusters(sc, clusters)
        # sc = autoEstCont(sc)
        # corrected = adjustCounts(sc)

        # ... rpy2 conversion logic ...
        return corrected_adata

    except (ImportError, Exception) as e:
        # HITL gate: log warning, return original data
        warnings.warn(f"SoupX not available ({e}). Skipping ambient RNA removal.")
        return filtered_adata
```

### Pattern 5: Tissue-Aware CellTypist Model Selection
**What:** Automatically select the best CellTypist model based on tissue type, with fallback chain.
**When to use:** Annotation stage (REQ-110).
**Example:**
```python
# Source: CellTypist API (verified via official tutorial)
import celltypist
from celltypist import models

TISSUE_MODEL_MAP = {
    "lung": "Human_Lung_Atlas.pkl",
    "immune": "Immune_All_Low.pkl",
    "heart": "Healthy_Adult_Heart.pkl",
    "brain": "Developing_Human_Brain.pkl",
    "kidney": "Human_Kidney.pkl",
    "liver": "Human_Liver.pkl",
    "intestine": "Human_Intestine.pkl",
    # ... 10+ tissues per REQ-110
}

def select_celltypist_model(tissue_type: str, custom_model: str = None):
    """Select and load the best CellTypist model for the tissue."""
    if custom_model:
        return celltypist.models.Model.load(model=custom_model)

    # Download all models if not cached
    models.download_models(force_update=False)
    available = models.models_description()
    available_names = list(available["Model"].str.replace(".pkl", "", regex=False))

    # Try tissue-specific model first
    preferred = TISSUE_MODEL_MAP.get(tissue_type)
    if preferred and preferred.replace(".pkl", "") in available_names:
        return celltypist.models.Model.load(model=preferred)

    # Fallback: Immune_All_Low (broadest coverage)
    return celltypist.models.Model.load(model="Immune_All_Low.pkl")
```

### Anti-Patterns to Avoid
- **Hardcoded gene lists:** Never reference specific genes (GIPR, GLP1R, ADIPOQ, etc.) in pipeline code. All gene-specific analysis belongs in downstream phases (scoring/reporting), not the pipeline.
- **Hardcoded tissue references:** Never reference "adipose", "MariTide", or any specific tissue/drug in the pipeline module. The tissue type comes from PipelineConfig.
- **Global mutable state:** Don't use `sc.settings.figdir` as global state across stages. Each stage should set its own output directory explicitly.
- **Loading entire h5ad into memory when backed mode available:** For very large datasets, use `sc.read_h5ad(path, backed='r')` to avoid OOM. However, many scanpy operations require in-memory data, so backed mode is primarily useful for initial inspection.
- **Skipping `.copy()` after subsetting:** After boolean indexing `adata[mask]`, always call `.copy()` to avoid dangling references to the original array. The existing QC code does this correctly.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Doublet detection | Custom expression-based heuristic | scrublet (Scrublet class) | Scrublet uses simulated doublet approach with validated thresholds; hand-rolling misses heterotypic doublets |
| Cell type annotation | Marker gene if/else trees | celltypist with pre-trained models | 50+ pre-trained models covering most human tissues; manual marker trees are fragile and tissue-specific |
| Batch correction | Custom linear regression | harmonypy.run_harmony() | Harmony is mathematically principled (iterative soft clustering); custom approaches under-correct or over-correct |
| Gene set enrichment | Custom hypergeometric test | gseapy.enrich() for ORA | gseapy handles background gene lists, multiple testing correction, and gene set databases correctly |
| Ambient RNA estimation | Heuristic count subtraction | SoupX (via rpy2) or CellBender | Ambient RNA profiles are sample-specific; SoupX estimates contamination fraction from empty droplets |
| Differential expression | Custom t-test loop | sc.tl.rank_genes_groups() | Scanpy handles sparse matrices, multiple testing, and multiple methods (wilcoxon, t-test, logreg) |
| HVG selection | Variance-based manual filter | sc.pp.highly_variable_genes() | Scanpy implements Seurat v3 method with batch-aware selection; manual approaches miss low-abundance HVGs |
| QC metric calculation | Manual gene counting | sc.pp.calculate_qc_metrics() | Handles sparse matrices, mitochondrial/ribosomal gene detection, percent_top calculations |

**Key insight:** The scRNA-seq ecosystem has mature, validated implementations for every standard analysis step. The value-add is in parameterization, orchestration, and integration -- not reimplementing algorithms.

## Common Pitfalls

### Pitfall 1: SoupX Requires Raw (Unfiltered) Counts
**What goes wrong:** SoupX needs BOTH the filtered cell matrix AND the raw (all droplets including empty) matrix to estimate ambient RNA. Users who upload only filtered .h5ad files cannot run SoupX.
**Why it happens:** Most public datasets and many lab outputs provide only filtered counts. The raw droplet matrix is a separate CellRanger output.
**How to avoid:** Make ambient RNA removal optional (REQ-103 already specifies a skip-with-warning HITL gate). When the user uploads only filtered data, auto-detect the absence of raw counts and present the skip option with a clear warning. Log the decision in audit trail.
**Warning signs:** File format is .h5ad (typically filtered only) rather than 10x folder (which may contain both raw and filtered).

### Pitfall 2: CellTypist Expects Specific Normalization
**What goes wrong:** CellTypist models are trained on log1p-normalized data at 10,000 counts per cell. If data is not normalized this way, annotations are unreliable.
**Why it happens:** The pipeline might run CellTypist before normalization, or use a different target_sum.
**How to avoid:** Always normalize with `target_sum=1e4` followed by `log1p` before CellTypist. Store raw counts in `adata.layers["counts"]` before normalizing (the existing stage4 does this correctly). CellTypist can also use `.raw.X` if it contains the right normalization.
**Warning signs:** CellTypist returning very few cell types or all cells as the same type.

### Pitfall 3: Leiden Resolution Varies Drastically by Dataset Size
**What goes wrong:** A resolution of 0.5 might produce 10 clusters on 10K cells but 50 clusters on 100K cells, leading to over-fragmented annotations.
**Why it happens:** Leiden resolution is not scale-invariant; larger graphs produce more communities at the same resolution.
**How to avoid:** Make leiden_resolution configurable per project (already in ProcessingConfig). Document that typical ranges are 0.1-0.5 for <50K cells, 0.3-1.0 for >50K cells. Consider providing an "auto" option that adjusts based on cell count.
**Warning signs:** >50 Leiden clusters, or CellTypist majority_voting collapsing many clusters into the same cell type.

### Pitfall 4: Memory Exhaustion on Large Datasets
**What goes wrong:** Loading a 500K-cell h5ad into memory, then creating copies during normalization/scaling, causes OOM on 8GB machines.
**Why it happens:** scanpy operations create intermediate copies. The existing code is designed for 60K cells (DEFAULT_N_CELLS = 60_000).
**How to avoid:** (1) Store raw counts in a layer instead of copying the full matrix. (2) Subset to HVGs before scaling and PCA (existing stage4 does this). (3) Use `gc.collect()` after deleting intermediate objects (existing code does this). (4) Document recommended RAM requirements in pipeline config.
**Warning signs:** Pipeline crashes during PCA or scaling steps; Python process exceeding 8GB RSS.

### Pitfall 5: Differential Expression with Too Few Cells per Group
**What goes wrong:** `sc.tl.rank_genes_groups()` with Wilcoxon test produces unreliable results when a cell type has <20 cells.
**Why it happens:** Rare cell types may have very few representatives.
**How to avoid:** Filter out groups with fewer than a minimum number of cells (e.g., 20) before running DE. Log which groups were excluded.
**Warning signs:** Very high or very low p-values for all genes in a group; NaN values in results.

### Pitfall 6: rpy2 Import Fails Silently or Crashes
**What goes wrong:** rpy2 requires a working R installation with SoupX. If R is not installed or SoupX is not installed in R, import fails.
**Why it happens:** R is not a Python dependency and cannot be installed via pip. Many environments (Docker, CI) don't have R pre-installed.
**How to avoid:** Wrap all rpy2 imports in try/except. Make SoupX a "best-effort" feature with graceful degradation. The HITL gate (REQ-103) handles this by allowing skip-with-warning.
**Warning signs:** `ImportError: rpy2` or `RRuntimeError: there is no package called 'SoupX'`.

### Pitfall 7: Gene Name Format Mismatches
**What goes wrong:** Some datasets use Ensembl IDs (ENSG00000...) while CellTypist and marker validation expect gene symbols (BRCA1, TP53).
**Why it happens:** CellRanger outputs can use either format depending on the reference genome used.
**How to avoid:** During ingestion, detect if var_names are Ensembl IDs and provide a conversion option. Check for `gene_symbols` column in var if var_names are IDs.
**Warning signs:** All CellTypist annotations are "Unknown" or very low confidence; marker genes not found in var_names.

## Code Examples

Verified patterns from official sources:

### Multi-Format Data Ingestion (REQ-102)
```python
# Source: scanpy official API (verified)
import scanpy as sc
import anndata as ad
from pathlib import Path

def ingest_data(input_path: Path) -> ad.AnnData:
    """Load scRNA-seq data from .h5ad, .h5, or 10x MTX folder."""
    input_path = Path(input_path)

    if input_path.suffix == ".h5ad":
        adata = sc.read_h5ad(str(input_path))
    elif input_path.suffix == ".h5":
        adata = sc.read_10x_h5(str(input_path), gex_only=True)
    elif input_path.is_dir():
        # Expect: matrix.mtx.gz, barcodes.tsv.gz, features.tsv.gz
        adata = sc.read_10x_mtx(
            str(input_path),
            var_names="gene_symbols",
            make_unique=True,
            gex_only=True,
        )
    else:
        raise ValueError(
            f"Unsupported format: {input_path}. "
            "Expected .h5ad, .h5, or directory with 10x files."
        )

    # Ensure var_names are unique
    adata.var_names_make_unique()
    # Store original counts as layer for later use
    adata.layers["raw_counts"] = adata.X.copy()
    return adata
```

### Configurable QC with Tissue Defaults (REQ-104)
```python
# Source: Refactored from bioorchestrator_real/pipeline/stage3_qc.py
import scanpy as sc
import numpy as np

MT_PREFIX = "MT-"  # Human mitochondrial gene prefix

def run_qc(adata: ad.AnnData, config: QCConfig) -> tuple[ad.AnnData, dict]:
    """Apply configurable QC filters. No hardcoded biology."""
    n_start = adata.n_obs

    # Mark mitochondrial genes
    adata.var["mt"] = adata.var_names.str.startswith(MT_PREFIX)
    sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], percent_top=None,
                               log1p=False, inplace=True)

    # Apply configurable thresholds
    keep = (
        (adata.obs["n_genes_by_counts"] >= config.min_genes)
        & (adata.obs["n_genes_by_counts"] <= config.max_genes)
        & (adata.obs["pct_counts_mt"] <= config.max_pct_mt)
    )
    adata = adata[keep].copy()
    sc.pp.filter_genes(adata, min_cells=config.min_cells_per_gene)

    report = {
        "stage": "qc",
        "n_cells_in": n_start,
        "n_cells_out": adata.n_obs,
        "thresholds_applied": {
            "max_pct_mt": config.max_pct_mt,
            "min_genes": config.min_genes,
            "max_genes": config.max_genes,
        },
    }
    return adata, report
```

### Differential Expression with Adjusted P-values (REQ-105)
```python
# Source: scanpy.tl.rank_genes_groups official API (verified)
def run_differential_expression(
    adata: ad.AnnData,
    groupby: str = "cell_type",
    method: str = "wilcoxon",
    corr_method: str = "benjamini-hochberg",
    n_genes: int = 500,
) -> dict:
    """Run DE analysis per cell type. Returns structured results."""
    # Filter groups with too few cells
    min_cells = 20
    group_counts = adata.obs[groupby].value_counts()
    valid_groups = group_counts[group_counts >= min_cells].index.tolist()

    if not valid_groups:
        return {"error": "No groups with sufficient cells for DE"}

    adata_sub = adata[adata.obs[groupby].isin(valid_groups)].copy()

    sc.tl.rank_genes_groups(
        adata_sub,
        groupby=groupby,
        method=method,
        corr_method=corr_method,
        n_genes=n_genes,
        use_raw=False,
        layer="counts" if "counts" in adata_sub.layers else None,
        pts=True,  # Include fraction of cells expressing
    )

    # Extract results as DataFrame per group
    results = {}
    for group in valid_groups:
        df = sc.get.rank_genes_groups_df(adata_sub, group=group)
        results[group] = df.to_dict(orient="records")

    return results
```

### Gene Set Enrichment via gseapy ORA (REQ-106)
```python
# Source: gseapy official API
import gseapy as gp

def run_enrichment_per_celltype(
    de_results: dict,
    gene_sets: list[str],
    organism: str = "human",
    pval_cutoff: float = 0.05,
) -> dict:
    """Run ORA on DE genes per cell type."""
    enrichment_results = {}

    for cell_type, de_genes_list in de_results.items():
        # Get significant upregulated genes
        sig_genes = [
            g["names"] for g in de_genes_list
            if g.get("pvals_adj", 1.0) < pval_cutoff and g.get("logfoldchanges", 0) > 0.5
        ]

        if len(sig_genes) < 5:
            enrichment_results[cell_type] = {"status": "too_few_genes"}
            continue

        try:
            enr = gp.enrich(
                gene_list=sig_genes,
                gene_sets=gene_sets,  # e.g., ["GO_Biological_Process_2023"]
                organism=organism,
                outdir=None,  # Don't write files
                cutoff=pval_cutoff,
            )
            enrichment_results[cell_type] = enr.results.to_dict(orient="records")
        except Exception as e:
            enrichment_results[cell_type] = {"error": str(e)}

    return enrichment_results
```

### CellTypist Annotation with Majority Voting (REQ-110)
```python
# Source: CellTypist official API (verified via tutorial)
import celltypist
from celltypist import models

def annotate_cells(
    adata: ad.AnnData,
    model_name: str,
    over_clustering_key: str = "leiden",
) -> tuple[ad.AnnData, dict]:
    """Annotate cells using CellTypist with majority voting."""
    # Download models if needed
    models.download_models(force_update=False)

    # Load model
    model = celltypist.models.Model.load(model=model_name)

    # Run annotation with majority voting
    predictions = celltypist.annotate(
        adata,
        model=model,
        majority_voting=True,
        over_clustering=over_clustering_key,
    )

    adata = predictions.to_adata()

    # Standardize column name
    if "majority_voting" in adata.obs.columns:
        adata.obs["cell_type"] = adata.obs["majority_voting"]
    elif "predicted_labels" in adata.obs.columns:
        adata.obs["cell_type"] = adata.obs["predicted_labels"]

    summary = {
        "model_used": model_name,
        "n_cell_types": int(adata.obs["cell_type"].nunique()),
        "cell_type_counts": adata.obs["cell_type"].value_counts().to_dict(),
    }
    return adata, summary
```

### Marker-Based Validation of Annotations (REQ-107)
```python
# Source: Pattern from scanpy + domain knowledge
CANONICAL_MARKERS = {
    "T cells": ["CD3D", "CD3E", "CD3G"],
    "B cells": ["CD19", "MS4A1", "CD79A"],
    "Macrophages": ["CD68", "CD163", "MRC1"],
    "Endothelial": ["PECAM1", "VWF", "CDH5"],
    "Fibroblasts": ["COL1A1", "COL3A1", "DCN"],
    "Epithelial": ["EPCAM", "KRT8", "KRT18"],
    "NK cells": ["NKG7", "GNLY", "KLRD1"],
    # Extend as needed -- this is configurable, not hardcoded biology
}

def validate_annotations(
    adata: ad.AnnData,
    marker_dict: dict[str, list[str]],
    label_col: str = "cell_type",
) -> list[dict]:
    """Flag discrepancies between CellTypist annotations and canonical markers."""
    import scipy.sparse as sp

    discrepancies = []
    for cell_type, markers in marker_dict.items():
        present_markers = [m for m in markers if m in adata.var_names]
        if not present_markers:
            continue

        # Find clusters annotated as this cell type
        mask = adata.obs[label_col].str.contains(cell_type, case=False, na=False)
        if mask.sum() == 0:
            continue

        # Check if canonical markers are expressed
        X_sub = adata[mask, present_markers].X
        if sp.issparse(X_sub):
            X_sub = X_sub.toarray()
        pct_expressing = (X_sub > 0).mean(axis=0)

        for marker, pct in zip(present_markers, pct_expressing):
            if pct < 0.1:  # Less than 10% of cells express this marker
                discrepancies.append({
                    "cell_type": cell_type,
                    "marker": marker,
                    "pct_expressing": round(float(pct) * 100, 1),
                    "flag": "LOW_MARKER_EXPRESSION",
                    "message": f"{cell_type} cells show only {pct*100:.1f}% "
                              f"expression of canonical marker {marker}",
                })

    return discrepancies
```

### Pipeline Orchestrator with Progress Callbacks (REQ-108)
```python
# Source: Integration pattern with Phase 1 TaskManager
from src.execution.task_manager import TaskManager

STAGE_WEIGHTS = {
    "ingest": 0.10,
    "ambient_rna": 0.15,
    "qc": 0.25,
    "process": 0.50,
    "annotate": 0.65,
    "de": 0.80,
    "enrichment": 0.90,
    "finalize": 1.00,
}

def run_pipeline(
    input_path: Path,
    config: PipelineConfig,
    project_dir: Path,
    task_manager: TaskManager,
    task_id: str,
) -> dict:
    """Run the full pipeline with progress reporting."""
    results = {}

    # Stage 1: Ingest
    adata = ingest_data(input_path)
    task_manager.update_progress(task_id, STAGE_WEIGHTS["ingest"])
    results["ingest"] = {"n_cells": adata.n_obs, "n_genes": adata.n_vars}

    # Stage 2: Ambient RNA (optional)
    if not config.skip_ambient_rna:
        adata = remove_ambient_rna(adata, config)
    task_manager.update_progress(task_id, STAGE_WEIGHTS["ambient_rna"])

    # Stage 3: QC
    adata, qc_report = run_qc(adata, config.qc)
    checkpoint_path = project_dir / "checkpoints" / "post_qc.h5ad"
    adata.write_h5ad(checkpoint_path)
    task_manager.update_progress(
        task_id, STAGE_WEIGHTS["qc"], str(checkpoint_path)
    )
    results["qc"] = qc_report

    # ... remaining stages follow same pattern ...

    return results
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual marker-based annotation | CellTypist pre-trained models with majority voting | 2022-2023 | Automated, reproducible annotation across tissues |
| Seurat (R only) pipelines | scanpy Python-native pipeline | 2018-present | Python ecosystem enables integration with ML/web frameworks |
| Simple variance-based HVG | Seurat v3 method (in scanpy, batch-aware) | scanpy 1.8+ | Better HVG selection for multi-batch experiments |
| PCA + manual batch correction | Harmony automated batch integration | harmonypy 0.0.5+ | Scalable, fast, no parameter tuning required |
| Manual hypergeometric test | gseapy/decoupler ORA frameworks | 2023-2024 | Correct multiple testing, built-in gene set databases |
| CellRanger-only input | Multi-format ingestion (h5ad, h5, MTX) | scanpy 1.4+ | Flexibility for different lab/public data sources |

**Deprecated/outdated:**
- `sc.tl.louvain()`: Replaced by `sc.tl.leiden()` which produces better community detection. The existing codebase correctly uses Leiden.
- `flavor="seurat"` for HVG without batch: Still works but `flavor="seurat_v3"` with `layer="counts"` is preferred for batch-aware selection (existing code already handles this).
- numpy 2.0: Excluded in requirements.txt (`<2.0`) because scanpy 1.10.x has compatibility issues with numpy 2.0.

## Open Questions

1. **CellTypist Model Availability for All 10+ Tissues**
   - What we know: CellTypist has models for lung, immune, heart, brain, kidney, liver, intestine. The exact model names need runtime verification via `models.models_description()`.
   - What's unclear: Whether models exist for all tissues REQ-110 intends to support (the requirement says "10+ tissues"). Some tissues may lack dedicated models.
   - Recommendation: Build the tissue-model map with known models, fall back to `Immune_All_Low.pkl` for unmapped tissues, and log a warning. The map should be a configuration dict, not hardcoded.

2. **SoupX Raw Count Matrix Availability**
   - What we know: SoupX requires both raw (all droplets) and filtered count matrices. Most uploaded .h5ad files contain only filtered data.
   - What's unclear: How often users will have raw count data available. The HITL gate handles the skip case, but the UX for uploading two separate files needs design.
   - Recommendation: For .h5ad uploads, default to skip-with-warning. For 10x folders, check for both `raw_feature_bc_matrix/` and `filtered_feature_bc_matrix/`. For CellRanger .h5, check for `raw_feature_bc_matrix` group in the HDF5 file.

3. **decoupler vs gseapy for Python 3.10**
   - What we know: decoupler 2.1.6 requires Python >=3.11. decoupler 2.1.4 works on Python 3.10. gseapy 1.2.1 works on Python >=3.8.
   - What's unclear: Whether the project will upgrade to Python 3.11+ in the future.
   - Recommendation: Use gseapy for now. It provides ORA via `gp.enrich()` plus additional methods (GSEA, ssGSEA, enrichr API). Pin `gseapy>=1.1.0`. If the project upgrades to Python 3.11+, decoupler can be swapped in as it offers tighter scanpy/AnnData integration.

4. **Checkpoint File Size Management**
   - What we know: Each checkpoint saves a full .h5ad. With 5 checkpoints and a 100K cell dataset, this could be 2-5GB total per project.
   - What's unclear: Disk budget per project. Whether to compress checkpoints or use backed mode.
   - Recommendation: Save checkpoints with default compression (gzip in h5ad). Consider adding a config option to skip intermediate checkpoints and only keep the latest.

## Sources

### Primary (HIGH confidence)
- scanpy official API: `read_10x_h5()`, `read_10x_mtx()`, `read_h5ad()`, `tl.rank_genes_groups()` -- verified via scanpy.readthedocs.io
- CellTypist API: `models.download_models()`, `models.Model.load()`, `celltypist.annotate()` with `majority_voting=True` -- verified via official tutorial notebook
- Existing codebase: `bioorchestrator_real/pipeline/stage3_qc.py`, `stage4_process.py`, `stage5_annotate.py` -- read directly
- Phase 1 infrastructure: `src/execution/task_manager.py` (TaskManager.update_progress, submit, get_status), `src/project/service.py` (ProjectService, per-project directories) -- read directly

### Secondary (MEDIUM confidence)
- CellTypist model list: Known models include Human_Lung_Atlas, Immune_All_Low, Immune_All_High, Healthy_Adult_Heart, Developing_Human_Brain, Human_Kidney, Human_Liver -- from celltypist.org (dynamic loading prevented full verification)
- gseapy 1.2.1 API: ORA via `gp.enrich()`, GSEA via `gp.prerank()` -- from PyPI package description
- decoupler Python 3.11 requirement: Verified via PyPI JSON API (decoupler 2.1.6 requires_python >=3.11, 2.1.4 requires >=3.10)
- rpy2 3.6.7: Supports Python 3.9-3.13 -- verified via PyPI JSON API

### Tertiary (LOW confidence)
- CellBender 0.3.2: Requires PyTorch/Pyro, GPU recommended -- from PyPI JSON API, not hands-on verified
- Full CellTypist model list for all 10+ tissues: The exact model names beyond the core set need runtime verification via `models.models_description()`
- SoupX rpy2 integration pattern: Based on known rpy2 patterns and SoupX R documentation; specific conversion code needs testing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - scanpy/anndata/harmonypy are verified in existing codebase; celltypist/gseapy verified via PyPI/docs
- Architecture: HIGH - Architecture derives directly from refactoring existing working pipeline code with well-understood Phase 1 infrastructure
- Pitfalls: HIGH - Most pitfalls identified from existing code patterns and known scRNA-seq domain issues
- CellTypist model coverage: MEDIUM - Core models verified but full 10+ tissue list needs runtime confirmation
- SoupX/rpy2 integration: MEDIUM - Pattern is standard but R dependency management adds deployment complexity
- gseapy ORA API: MEDIUM - API structure verified but specific function signatures based on package description + training data

**Research date:** 2026-05-10
**Valid until:** 2026-06-10 (30 days -- ecosystem is stable; scanpy 1.10.x is mature)
