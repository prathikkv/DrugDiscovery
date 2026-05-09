"""CellTypist annotation with tissue-aware model selection and marker validation (REQ-110, REQ-107).

Provides run_annotation() for automated cell type annotation using
CellTypist with tissue-appropriate model selection, and
validate_annotations() for cross-checking CellTypist labels against
canonical marker gene expression.

No hardcoded biology -- all tissue-model mappings and canonical markers
are generic cell type references applicable to any study context.
"""

import logging
import time
import warnings
from pathlib import Path
from typing import Optional

import anndata as ad

from src.pipeline.checkpointing import (
    load_checkpoint,
    save_checkpoint,
    save_stage_report,
)
from src.pipeline.config import PipelineConfig
from src.pipeline.progress import StageProgressTracker

logger = logging.getLogger(__name__)

# ── Tissue-to-CellTypist model mapping ────────────────────────────────
# Maps tissue type to the best-matching CellTypist pre-trained model.
# These are generic biological categories -- no drug, target, or
# disease-specific references belong here.

TISSUE_MODEL_MAP: dict[str, str] = {
    "lung": "Human_Lung_Atlas.pkl",
    "immune": "Immune_All_Low.pkl",
    "heart": "Healthy_Adult_Heart.pkl",
    "brain": "Developing_Human_Brain.pkl",
    "kidney": "Human_Kidney.pkl",
    "liver": "Human_Liver.pkl",
    "intestine": "Human_Intestine.pkl",
    "adipose": "Immune_All_Low.pkl",
    "eye": "Immune_All_Low.pkl",
    "pancreas": "Immune_All_Low.pkl",
    "tumor": "Immune_All_Low.pkl",
    "default": "Immune_All_Low.pkl",
}

# ── Canonical marker genes for cell type validation (REQ-107) ─────────
# Used by validate_annotations() to cross-check CellTypist labels
# against expected marker expression. These are well-established
# pan-tissue markers, not study-specific.

CANONICAL_MARKERS: dict[str, list[str]] = {
    "T cells": ["CD3D", "CD3E", "CD3G"],
    "B cells": ["CD19", "MS4A1", "CD79A"],
    "Macrophages": ["CD68", "CD163", "MRC1"],
    "Endothelial": ["PECAM1", "VWF", "CDH5"],
    "Fibroblasts": ["COL1A1", "COL3A1", "DCN"],
    "Epithelial": ["EPCAM", "KRT8", "KRT18"],
    "NK cells": ["NKG7", "GNLY", "KLRD1"],
    "Monocytes": ["CD14", "FCGR3A", "S100A8"],
    "Dendritic": ["FCER1A", "CD1C", "CLEC10A"],
    "Plasma cells": ["JCHAIN", "MZB1", "SDC1"],
}


def run_annotation(
    adata: ad.AnnData,
    config: PipelineConfig,
    project_dir: Path,
    progress_tracker: Optional[StageProgressTracker] = None,
) -> tuple[ad.AnnData, dict]:
    """Annotate cell types using CellTypist with tissue-aware model selection.

    Selects the CellTypist model based on config.celltypist_model (if
    set) or tissue_type lookup in TISSUE_MODEL_MAP. Runs CellTypist
    with majority voting over Leiden clusters.

    CellTypist requires log1p-normalized data at 10K counts/cell.
    Raises ValueError if the data appears unnormalized.

    Args:
        adata: Input AnnData object (post-processing, with leiden clusters).
        config: PipelineConfig with celltypist_model and tissue_type.
        project_dir: Project directory for checkpoints and reports.
        progress_tracker: Optional StageProgressTracker for progress
            reporting. None silently skips progress updates.

    Returns:
        Tuple of (annotated_adata, annotation_report_dict).

    Raises:
        ValueError: If adata.X appears to contain raw (unnormalized) counts.
    """
    # -- Check for existing checkpoint --
    existing = load_checkpoint(project_dir, "annotation")
    if existing is not None:
        logger.info("Annotation checkpoint found -- loading cached result")
        from src.pipeline.checkpointing import load_stage_report

        report = load_stage_report(project_dir, "annotation") or {
            "stage": "annotation",
            "cached": True,
        }
        if progress_tracker:
            progress_tracker.update("annotation")
        return existing, report

    t0 = time.time()

    # -- Determine CellTypist model --
    if config.celltypist_model:
        model_name = config.celltypist_model
    else:
        model_name = TISSUE_MODEL_MAP.get(
            config.tissue_type, TISSUE_MODEL_MAP["default"]
        )

    logger.info(
        "Annotation: using CellTypist model '%s' (tissue=%s)",
        model_name,
        config.tissue_type,
    )

    if progress_tracker:
        progress_tracker.update_substage("annotation", 0.1)

    # -- Import and load CellTypist --
    import celltypist  # noqa: PLC0415
    from celltypist import models as ct_models  # noqa: PLC0415

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ct_models.download_models(force_update=False)

    model = ct_models.Model.load(model=model_name)

    if progress_tracker:
        progress_tracker.update_substage("annotation", 0.3)

    # -- Verify normalization --
    # CellTypist expects log1p-normalized data (10K counts/cell).
    # Raw counts would have max values in the hundreds/thousands;
    # log1p-normalized data should have max < ~15-20.
    import numpy as np  # noqa: PLC0415
    import scipy.sparse as sp  # noqa: PLC0415

    x_max = float(
        adata.X.max() if not sp.issparse(adata.X) else adata.X.toarray().max()
    )
    if x_max > 50:
        raise ValueError(
            f"adata.X appears to contain raw counts (max={x_max:.1f}). "
            "CellTypist requires log1p-normalized data at 10K counts/cell. "
            "Run sc.pp.normalize_total(adata, target_sum=1e4) then "
            "sc.pp.log1p(adata) before annotation."
        )

    # -- Run CellTypist --
    logger.info("Running CellTypist annotation (majority voting)...")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        predictions = celltypist.annotate(
            adata,
            model=model,
            majority_voting=True,
            over_clustering="leiden",
        )

    if progress_tracker:
        progress_tracker.update_substage("annotation", 0.7)

    # -- Convert predictions to AnnData --
    adata = predictions.to_adata()

    # Standardize cell type column name
    if "majority_voting" in adata.obs.columns:
        adata.obs["cell_type"] = adata.obs["majority_voting"]
    elif "predicted_labels" in adata.obs.columns:
        adata.obs["cell_type"] = adata.obs["predicted_labels"]

    n_cell_types = (
        int(adata.obs["cell_type"].nunique())
        if "cell_type" in adata.obs.columns
        else 0
    )

    cell_type_counts = {}
    if "cell_type" in adata.obs.columns:
        cell_type_counts = {
            str(k): int(v)
            for k, v in adata.obs["cell_type"].value_counts().items()
        }

    logger.info("CellTypist identified %d cell types", n_cell_types)

    if progress_tracker:
        progress_tracker.update_substage("annotation", 0.9)

    elapsed = time.time() - t0

    # -- Build report --
    report = {
        "stage": "annotation",
        "model_used": model_name,
        "n_cell_types": n_cell_types,
        "cell_type_counts": cell_type_counts,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": round(elapsed, 1),
    }

    # -- Save checkpoint and report --
    checkpoint_path = save_checkpoint(adata, project_dir, "annotation")
    save_stage_report(report, project_dir, "annotation")

    if progress_tracker:
        progress_tracker.update("annotation", str(checkpoint_path))

    return adata, report


def validate_annotations(
    adata: ad.AnnData,
    marker_dict: Optional[dict[str, list[str]]] = None,
    label_col: str = "cell_type",
) -> list[dict]:
    """Validate CellTypist annotations against canonical marker expression.

    For each cell type in marker_dict, finds cells with matching
    annotations (case-insensitive substring match) and checks what
    percentage of those cells express each canonical marker gene.
    Flags discrepancies where <10% of cells express a canonical marker.

    Args:
        adata: Annotated AnnData object with cell type labels.
        marker_dict: Dict mapping cell type names to lists of marker
            genes. Defaults to CANONICAL_MARKERS if None.
        label_col: Column in adata.obs containing cell type labels.
            Defaults to "cell_type".

    Returns:
        List of discrepancy dicts, each with keys:
          - cell_type: str
          - marker: str
          - pct_expressing: float
          - flag: "LOW_MARKER_EXPRESSION"
          - message: str
    """
    import numpy as np  # noqa: PLC0415
    import scipy.sparse as sp  # noqa: PLC0415

    if marker_dict is None:
        marker_dict = CANONICAL_MARKERS

    if label_col not in adata.obs.columns:
        logger.warning(
            "Label column '%s' not found in adata.obs -- "
            "skipping annotation validation",
            label_col,
        )
        return []

    discrepancies: list[dict] = []
    var_names_list = list(adata.var_names)

    for cell_type_name, markers in marker_dict.items():
        # Find cells annotated with a label containing this cell type name
        pattern = cell_type_name.lower()
        mask = adata.obs[label_col].str.lower().str.contains(
            pattern, na=False
        )
        n_matching_cells = int(mask.sum())

        if n_matching_cells == 0:
            continue

        # Get expression matrix for matching cells
        X_sub = adata[mask].X

        for marker in markers:
            if marker not in var_names_list:
                continue

            gene_idx = var_names_list.index(marker)

            # Extract expression for this gene
            if sp.issparse(X_sub):
                gene_expr = np.asarray(X_sub[:, gene_idx].todense()).flatten()
            else:
                gene_expr = X_sub[:, gene_idx]

            # Calculate percentage of cells expressing this marker (>0)
            pct_expressing = float((gene_expr > 0).mean() * 100)

            if pct_expressing < 10.0:
                discrepancies.append(
                    {
                        "cell_type": cell_type_name,
                        "marker": marker,
                        "pct_expressing": round(pct_expressing, 2),
                        "flag": "LOW_MARKER_EXPRESSION",
                        "message": (
                            f"Only {pct_expressing:.1f}% of cells labeled as "
                            f"'{cell_type_name}' (n={n_matching_cells}) express "
                            f"canonical marker {marker}"
                        ),
                    }
                )
                logger.warning(
                    "Annotation discrepancy: %s marker %s expressed in "
                    "only %.1f%% of %d matching cells",
                    cell_type_name,
                    marker,
                    pct_expressing,
                    n_matching_cells,
                )

    if discrepancies:
        logger.info(
            "Annotation validation: %d discrepancies found",
            len(discrepancies),
        )
    else:
        logger.info("Annotation validation: no discrepancies found")

    return discrepancies
