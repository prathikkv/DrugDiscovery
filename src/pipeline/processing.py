"""Full scanpy processing: normalize -> HVG -> scale -> PCA -> Harmony -> neighbors -> UMAP -> Leiden (REQ-101).

Refactored from bioorchestrator_real/pipeline/stage4_process.py to:
  - Accept PipelineConfig (not raw dict) for all parameters
  - Remove all rich console output (this is a library, not CLI)
  - Remove sc.settings.figdir manipulation
  - Integrate with checkpointing and progress tracking
  - Return structured (adata, report) tuple
"""

import gc
import logging
import time
import warnings
from pathlib import Path
from typing import Optional

import anndata as ad
import numpy as np
import scanpy as sc

from src.pipeline.checkpointing import (
    load_checkpoint,
    save_checkpoint,
    save_stage_report,
)
from src.pipeline.config import PipelineConfig
from src.pipeline.progress import StageProgressTracker

logger = logging.getLogger(__name__)


def run_processing(
    adata: ad.AnnData,
    config: PipelineConfig,
    project_dir: Path,
    progress_tracker: Optional[StageProgressTracker] = None,
) -> tuple[ad.AnnData, dict]:
    """Run the full scanpy processing pipeline on QC-filtered data.

    Performs normalization, HVG selection, scaling, PCA, optional
    Harmony batch correction, neighbor graph construction, UMAP
    embedding, and Leiden clustering. All parameters come from
    config.processing.

    Integrates with checkpointing (loads existing, saves on completion)
    and progress tracking (reports stage completion and substage updates).

    Args:
        adata: Input AnnData object (post-QC).
        config: PipelineConfig with processing parameters.
        project_dir: Project directory for checkpoints and reports.
        progress_tracker: Optional StageProgressTracker for progress
            reporting. None silently skips progress updates.

    Returns:
        Tuple of (processed_adata, processing_report_dict).
    """
    # -- Check for existing checkpoint --
    existing = load_checkpoint(project_dir, "processing")
    if existing is not None:
        logger.info("Processing checkpoint found -- loading cached result")
        from src.pipeline.checkpointing import load_stage_report

        report = load_stage_report(project_dir, "processing") or {
            "stage": "processing",
            "cached": True,
        }
        if progress_tracker:
            progress_tracker.update("processing")
        return existing, report

    sc.settings.verbosity = 0
    t0 = time.time()
    proc = config.processing

    logger.info(
        "Starting processing: %d cells, %d genes",
        adata.n_obs,
        adata.n_vars,
    )

    # -- Store raw counts (needed for CellTypist and DE later) --
    adata.layers["counts"] = adata.X.copy()

    if progress_tracker:
        progress_tracker.update_substage("processing", 0.05)

    # -- Normalize --
    sc.pp.normalize_total(adata, target_sum=proc.normalize_total_target)
    sc.pp.log1p(adata)

    if progress_tracker:
        progress_tracker.update_substage("processing", 0.15)

    # -- Highly variable genes --
    batch_key = (
        proc.batch_key if proc.batch_key in adata.obs.columns else None
    )
    sc.pp.highly_variable_genes(
        adata,
        n_top_genes=proc.n_top_hvgs,
        batch_key=batch_key,
        flavor="seurat_v3" if batch_key else "seurat",
        layer="counts" if batch_key else None,
    )
    n_hvgs = int(adata.var["highly_variable"].sum())
    logger.info("Selected %d highly variable genes", n_hvgs)

    if progress_tracker:
        progress_tracker.update_substage("processing", 0.25)

    # -- Subset to HVGs for PCA (memory-efficient) --
    adata_hvg = adata[:, adata.var["highly_variable"]].copy()

    # -- Scale --
    sc.pp.scale(adata_hvg, max_value=10)

    # -- PCA --
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sc.tl.pca(
            adata_hvg,
            n_comps=proc.n_pcs,
            svd_solver="arpack",
            random_state=42,
        )

    # Transfer PCA embedding back to full adata
    adata.obsm["X_pca"] = adata_hvg.obsm["X_pca"]
    del adata_hvg
    gc.collect()

    if progress_tracker:
        progress_tracker.update_substage("processing", 0.45)

    # -- Harmony batch correction --
    batch_col = (
        proc.batch_key if proc.batch_key in adata.obs.columns else None
    )
    batch_corrected = False
    use_rep = "X_pca"

    if batch_col and adata.obs[batch_col].nunique() > 1:
        try:
            import harmonypy  # noqa: PLC0415

            ho = harmonypy.run_harmony(
                adata.obsm["X_pca"],
                adata.obs,
                batch_col,
                random_state=42,
                verbose=False,
            )
            adata.obsm["X_pca_harmony"] = ho.Z_corr.T
            use_rep = "X_pca_harmony"
            batch_corrected = True
            logger.info(
                "Harmony batch correction applied (key='%s')", batch_col
            )
        except Exception as exc:
            logger.warning(
                "Harmony failed (%s); falling back to PCA", exc
            )
            use_rep = "X_pca"
    else:
        logger.info("Single batch or no batch column -- skipping Harmony")

    if progress_tracker:
        progress_tracker.update_substage("processing", 0.60)

    # -- Neighbors --
    n_pcs = min(proc.n_pcs_neighbors, adata.obsm[use_rep].shape[1])
    sc.pp.neighbors(
        adata,
        use_rep=use_rep,
        n_neighbors=proc.n_neighbors,
        n_pcs=n_pcs,
        random_state=42,
    )

    if progress_tracker:
        progress_tracker.update_substage("processing", 0.75)

    # -- UMAP --
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sc.tl.umap(adata, random_state=42)

    if progress_tracker:
        progress_tracker.update_substage("processing", 0.85)

    # -- Leiden clustering --
    sc.tl.leiden(
        adata,
        resolution=proc.leiden_resolution,
        random_state=42,
    )
    n_clusters = int(adata.obs["leiden"].nunique())
    logger.info("Leiden clustering: %d clusters identified", n_clusters)

    elapsed = time.time() - t0
    logger.info("Processing complete in %.1fs", elapsed)

    # -- Build report --
    report = {
        "stage": "processing",
        "n_hvgs": n_hvgs,
        "n_pcs": proc.n_pcs,
        "batch_corrected": batch_corrected,
        "use_rep": use_rep,
        "n_clusters": n_clusters,
        "n_cells": adata.n_obs,
        "n_genes": adata.n_vars,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": round(elapsed, 1),
    }

    # -- Save checkpoint and report --
    checkpoint_path = save_checkpoint(adata, project_dir, "processing")
    save_stage_report(report, project_dir, "processing")

    # -- Report progress --
    if progress_tracker:
        progress_tracker.update("processing", str(checkpoint_path))

    return adata, report
