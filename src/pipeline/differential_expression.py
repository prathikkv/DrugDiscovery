"""Wilcoxon differential expression with adjusted p-values and min-cell filtering (REQ-105).

Produces per-cell-type (or per-Leiden-cluster) DE results using
scanpy's rank_genes_groups with configurable test method and
multiple-testing correction. Groups with fewer than 20 cells are
excluded to ensure statistical reliability.

All parameters come from PipelineConfig -- nothing is hardcoded.
"""

import gc
import logging
import time
import warnings
from pathlib import Path
from typing import Optional

import anndata as ad
import scanpy as sc

from src.pipeline.checkpointing import (
    load_checkpoint,
    save_checkpoint,
    save_stage_report,
)
from src.pipeline.config import PipelineConfig
from src.pipeline.progress import StageProgressTracker

logger = logging.getLogger(__name__)

# Minimum number of cells required in a group for DE analysis
MIN_CELLS_PER_GROUP = 20


def run_differential_expression(
    adata: ad.AnnData,
    config: PipelineConfig,
    project_dir: Path,
    progress_tracker: Optional[StageProgressTracker] = None,
) -> tuple[ad.AnnData, dict]:
    """Run differential expression analysis per cell type or cluster.

    Uses scanpy's rank_genes_groups with the method and correction
    specified in config (default: Wilcoxon + Benjamini-Hochberg).
    Groups with fewer than MIN_CELLS_PER_GROUP cells are excluded.

    Results are stored in adata.uns["de_results"] as a dict mapping
    group names to lists of gene result dicts.

    Args:
        adata: Annotated AnnData object with cell type labels and/or
            Leiden clusters.
        config: PipelineConfig with de_method and de_corr_method.
        project_dir: Project directory for checkpoints and reports.
        progress_tracker: Optional StageProgressTracker for progress
            reporting. None silently skips progress updates.

    Returns:
        Tuple of (adata_with_de_results, de_report_dict).
    """
    # -- Check for existing checkpoint --
    existing = load_checkpoint(project_dir, "de")
    if existing is not None:
        logger.info("DE checkpoint found -- loading cached result")
        from src.pipeline.checkpointing import load_stage_report

        report = load_stage_report(project_dir, "de") or {
            "stage": "de",
            "cached": True,
        }
        if progress_tracker:
            progress_tracker.update("de")
        return existing, report

    t0 = time.time()

    # -- Determine groupby column --
    if "cell_type" in adata.obs.columns:
        groupby = "cell_type"
    else:
        groupby = "leiden"

    if groupby not in adata.obs.columns:
        logger.error("Neither 'cell_type' nor 'leiden' found in adata.obs")
        report = {
            "stage": "de",
            "status": "error",
            "reason": "No groupby column found (need 'cell_type' or 'leiden')",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        save_stage_report(report, project_dir, "de")
        return adata, report

    logger.info("DE analysis: groupby='%s', method='%s'", groupby, config.de_method)

    if progress_tracker:
        progress_tracker.update_substage("de", 0.1)

    # -- Filter groups with too few cells --
    group_counts = adata.obs[groupby].value_counts()
    valid_groups = group_counts[group_counts >= MIN_CELLS_PER_GROUP].index.tolist()
    excluded_groups = [
        {
            "group": str(g),
            "n_cells": int(group_counts[g]),
            "reason": f"fewer than {MIN_CELLS_PER_GROUP} cells",
        }
        for g in group_counts.index
        if g not in valid_groups
    ]

    if excluded_groups:
        logger.info(
            "Excluded %d groups with <%d cells: %s",
            len(excluded_groups),
            MIN_CELLS_PER_GROUP,
            [eg["group"] for eg in excluded_groups],
        )

    if not valid_groups:
        logger.error("No groups with >=%d cells for DE analysis", MIN_CELLS_PER_GROUP)
        report = {
            "stage": "de",
            "status": "error",
            "reason": f"No groups with >={MIN_CELLS_PER_GROUP} cells",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        save_stage_report(report, project_dir, "de")
        return adata, report

    # -- Subset to valid groups --
    mask = adata.obs[groupby].isin(valid_groups)
    adata_sub = adata[mask].copy()
    gc.collect()

    if progress_tracker:
        progress_tracker.update_substage("de", 0.3)

    # -- Determine layer for DE --
    use_layer = "counts" if "counts" in adata_sub.layers else None

    # -- Run rank_genes_groups --
    logger.info(
        "Running rank_genes_groups: %d groups, %d cells",
        len(valid_groups),
        adata_sub.n_obs,
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sc.tl.rank_genes_groups(
            adata_sub,
            groupby=groupby,
            method=config.de_method,
            corr_method=config.de_corr_method,
            n_genes=500,
            use_raw=False,
            pts=True,
            layer=use_layer,
        )

    if progress_tracker:
        progress_tracker.update_substage("de", 0.7)

    # -- Extract results per group --
    de_results: dict[str, list[dict]] = {}
    n_genes_per_group: dict[str, int] = {}

    for group in valid_groups:
        group_str = str(group)
        try:
            df = sc.get.rank_genes_groups_df(adata_sub, group=group_str)
            gene_list = []
            for _, row in df.iterrows():
                gene_dict = {
                    "names": str(row.get("names", "")),
                    "scores": float(row.get("scores", 0.0)),
                    "pvals": float(row.get("pvals", 1.0)),
                    "pvals_adj": float(row.get("pvals_adj", 1.0)),
                    "logfoldchanges": float(row.get("logfoldchanges", 0.0)),
                }
                # pct_nz fields may or may not be present depending on scanpy version
                if "pct_nz_group" in row.index:
                    gene_dict["pct_nz_group"] = float(row["pct_nz_group"])
                if "pct_nz_reference" in row.index:
                    gene_dict["pct_nz_reference"] = float(row["pct_nz_reference"])
                gene_list.append(gene_dict)

            de_results[group_str] = gene_list
            n_genes_per_group[group_str] = len(gene_list)
        except Exception as exc:
            logger.warning("Failed to extract DE results for group '%s': %s", group_str, exc)
            de_results[group_str] = []
            n_genes_per_group[group_str] = 0

    if progress_tracker:
        progress_tracker.update_substage("de", 0.9)

    # -- Store results in adata --
    # Copy rank_genes_groups results from subset back to full adata
    adata.uns["rank_genes_groups"] = adata_sub.uns.get("rank_genes_groups", {})
    adata.uns["de_results"] = de_results

    del adata_sub
    gc.collect()

    elapsed = time.time() - t0
    logger.info(
        "DE complete: %d groups tested in %.1fs",
        len(valid_groups),
        elapsed,
    )

    # -- Build report --
    report = {
        "stage": "de",
        "status": "completed",
        "method": config.de_method,
        "corr_method": config.de_corr_method,
        "groupby": groupby,
        "n_groups_tested": len(valid_groups),
        "groups_excluded": excluded_groups,
        "n_genes_per_group": n_genes_per_group,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": round(elapsed, 1),
    }

    # -- Save checkpoint and report --
    checkpoint_path = save_checkpoint(adata, project_dir, "de")
    save_stage_report(report, project_dir, "de")

    if progress_tracker:
        progress_tracker.update("de", str(checkpoint_path))

    return adata, report
