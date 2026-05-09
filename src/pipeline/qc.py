"""Configurable QC with doublet detection and sex concordance (REQ-104).

Refactored from bioorchestrator_real/pipeline/stage3_qc.py to:
  - Accept PipelineConfig (not raw dict) for all thresholds
  - Remove all rich console output (this is a library, not CLI)
  - Remove plot generation (plots belong in the UI phase)
  - Integrate with checkpointing and progress tracking
  - Return structured (adata, report) tuple

All QC thresholds come from PipelineConfig.qc -- nothing is hardcoded.
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

# Human mitochondrial gene prefix
MT_PREFIX = "MT-"


def _detect_doublets(
    adata_sub: ad.AnnData,
    threshold: float,
) -> np.ndarray:
    """Run scrublet on a single-donor slice.

    Returns a boolean mask where True indicates a predicted doublet.
    Gracefully falls back to all-False if scrublet is not installed
    or fails for any reason.
    """
    try:
        import scrublet as scr  # noqa: PLC0415
    except ImportError:
        logger.warning("scrublet not installed -- skipping doublet detection")
        return np.zeros(adata_sub.n_obs, dtype=bool)

    import scipy.sparse as sp

    X = adata_sub.X
    if sp.issparse(X):
        X = X.toarray()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            scrub = scr.Scrublet(X)
            scores, _ = scrub.scrub_doublets(verbose=False)
            return scores > threshold
        except Exception as exc:
            logger.warning("Scrublet failed: %s -- skipping", exc)
            return np.zeros(adata_sub.n_obs, dtype=bool)


def _check_sex_concordance(
    adata: ad.AnnData,
    female_marker: str,
    male_markers: list[str],
    expr_threshold: float,
) -> dict[str, str]:
    """Check sex concordance between expression markers and metadata.

    Infers sex from XIST (female) and Y-chromosome genes (male)
    expression, then compares to reported sex in obs metadata.

    Returns a dict: donor_id -> "concordant" | "MISMATCH ..." | "unknown".
    """
    import scipy.sparse as sp

    # Find the sex metadata column
    sex_col = None
    for candidate in ("sex", "SEXCD", "Sex", "gender"):
        if candidate in adata.obs.columns:
            sex_col = candidate
            break

    # Find the donor grouping column
    donor_col = None
    for candidate in ("donor_id", "SUBJID", "sample_id", "donor"):
        if candidate in adata.obs.columns:
            donor_col = candidate
            break

    if donor_col is None:
        return {}

    result = {}
    var_names = list(adata.var_names)

    female_gene_idx = (
        var_names.index(female_marker) if female_marker in var_names else None
    )
    male_gene_idxs = [var_names.index(g) for g in male_markers if g in var_names]

    for donor, group in adata.obs.groupby(donor_col):
        cell_mask = adata.obs.index.isin(group.index)
        X_donor = adata.X[cell_mask]
        if sp.issparse(X_donor):
            X_donor = X_donor.toarray()

        xist_mean = (
            float(X_donor[:, female_gene_idx].mean())
            if female_gene_idx is not None
            else 0.0
        )
        male_mean = (
            float(X_donor[:, male_gene_idxs].mean()) if male_gene_idxs else 0.0
        )

        if xist_mean > expr_threshold and male_mean <= expr_threshold:
            predicted = "female"
        elif male_mean > expr_threshold and xist_mean <= expr_threshold:
            predicted = "male"
        else:
            predicted = "unknown"

        if sex_col is None:
            result[str(donor)] = "unknown"
            continue

        reported_raw = group[sex_col].iloc[0]
        reported_sex = (
            str(reported_raw).lower() if reported_raw is not None else "unknown"
        )

        if predicted == "unknown" or reported_sex == "unknown":
            result[str(donor)] = "unknown"
        elif predicted == reported_sex:
            result[str(donor)] = "concordant"
        else:
            result[str(donor)] = (
                f"MISMATCH (reported={reported_sex}, predicted={predicted})"
            )

    return result


def run_qc(
    adata: ad.AnnData,
    config: PipelineConfig,
    project_dir: Path,
    progress_tracker: Optional[StageProgressTracker] = None,
) -> tuple[ad.AnnData, dict]:
    """Apply configurable QC filters to the AnnData object.

    Performs the following QC steps using thresholds from config.qc:
      1. Mark mitochondrial genes and compute QC metrics
      2. Sex concordance check (only if donor_id and sex columns exist)
      3. Per-donor doublet detection via scrublet
      4. Apply cell filters: min_genes, max_genes, max_pct_mt, doublets
      5. Remove quarantined donors (sex mismatch)
      6. Filter genes by min_cells_per_gene

    Integrates with checkpointing (loads existing, saves on completion)
    and progress tracking (reports stage completion).

    Args:
        adata: Input AnnData object.
        config: PipelineConfig with QC thresholds in config.qc.
        project_dir: Project directory for checkpoints and reports.
        progress_tracker: Optional StageProgressTracker for progress
            reporting. None silently skips progress updates.

    Returns:
        Tuple of (filtered_adata, qc_report_dict).
    """
    # ── Check for existing checkpoint ──────────────────────────────
    existing = load_checkpoint(project_dir, "qc")
    if existing is not None:
        logger.info("QC checkpoint found -- loading cached result")
        from src.pipeline.checkpointing import load_stage_report

        report = load_stage_report(project_dir, "qc") or {"stage": "qc", "cached": True}
        if progress_tracker:
            progress_tracker.update("qc")
        return existing, report

    t0 = time.time()
    qc_cfg = config.qc
    n_cells_start = adata.n_obs
    logger.info("Starting QC: %d cells, tissue=%s", n_cells_start, config.tissue_type)

    # ── Mark mitochondrial genes ───────────────────────────────────
    adata.var["mt"] = adata.var_names.str.startswith(MT_PREFIX)
    sc.pp.calculate_qc_metrics(
        adata, qc_vars=["mt"], percent_top=None, log1p=False, inplace=True
    )

    # ── Sex concordance ────────────────────────────────────────────
    sex_concordance = _check_sex_concordance(
        adata,
        female_marker=qc_cfg.female_marker,
        male_markers=qc_cfg.male_markers,
        expr_threshold=qc_cfg.sex_expr_threshold,
    )
    quarantined_donors = [
        d for d, v in sex_concordance.items() if "MISMATCH" in v
    ]
    if quarantined_donors:
        logger.warning("Quarantined donors (sex mismatch): %s", quarantined_donors)

    # ── Doublet detection (per donor, memory-efficient) ────────────
    # Find donor column
    donor_col = None
    for candidate in ("donor_id", "SUBJID", "sample_id", "donor"):
        if candidate in adata.obs.columns:
            donor_col = candidate
            break

    doublet_mask = np.zeros(adata.n_obs, dtype=bool)
    if donor_col is not None:
        if progress_tracker:
            progress_tracker.update_substage("qc", 0.3)

        for donor, group in adata.obs.groupby(donor_col):
            if str(donor) in quarantined_donors:
                continue
            cell_idxs = np.where(adata.obs.index.isin(group.index))[0]
            sub = adata[cell_idxs]
            is_doublet = _detect_doublets(sub, qc_cfg.doublet_threshold)
            doublet_mask[cell_idxs] = is_doublet
            del sub
            gc.collect()
    else:
        # No donor column -- run scrublet on entire dataset
        doublet_mask = _detect_doublets(adata, qc_cfg.doublet_threshold)

    adata.obs["predicted_doublet"] = doublet_mask

    if progress_tracker:
        progress_tracker.update_substage("qc", 0.6)

    # ── Build per-donor QC summary ─────────────────────────────────
    donor_qc: dict = {}
    if donor_col is not None:
        for donor, group in adata.obs.groupby(donor_col):
            donor_qc[str(donor)] = {
                "n_cells": int(len(group)),
                "mean_genes": round(float(group["n_genes_by_counts"].mean()), 1),
                "mean_mt_pct": round(float(group["pct_counts_mt"].mean()), 2),
                "n_doublets": int(group["predicted_doublet"].sum()),
                "sex_concordance": sex_concordance.get(str(donor), "unknown"),
            }

    # ── Apply filters ──────────────────────────────────────────────
    keep = (
        (adata.obs["n_genes_by_counts"] >= qc_cfg.min_genes)
        & (adata.obs["n_genes_by_counts"] <= qc_cfg.max_genes)
        & (adata.obs["pct_counts_mt"] <= qc_cfg.max_pct_mt)
        & (~adata.obs["predicted_doublet"])
    )

    # Remove quarantined donors
    if quarantined_donors and donor_col is not None:
        keep &= ~adata.obs[donor_col].isin(quarantined_donors)

    n_removed = int((~keep).sum())
    adata = adata[keep].copy()
    gc.collect()

    # ── Minimum cells per gene ─────────────────────────────────────
    sc.pp.filter_genes(adata, min_cells=qc_cfg.min_cells_per_gene)

    n_cells_end = adata.n_obs
    elapsed = time.time() - t0

    logger.info(
        "QC complete: %d -> %d cells (%.1f%% retained) in %.1fs",
        n_cells_start,
        n_cells_end,
        100.0 * n_cells_end / n_cells_start if n_cells_start > 0 else 0.0,
        elapsed,
    )

    # ── Build report ───────────────────────────────────────────────
    report = {
        "stage": "qc",
        "n_cells_in": n_cells_start,
        "n_cells_out": n_cells_end,
        "n_cells_removed": n_removed,
        "pct_cells_retained": (
            round(100.0 * n_cells_end / n_cells_start, 1)
            if n_cells_start > 0
            else 0.0
        ),
        "thresholds_applied": {
            "min_genes": qc_cfg.min_genes,
            "max_genes": qc_cfg.max_genes,
            "max_pct_mt": qc_cfg.max_pct_mt,
            "doublet_threshold": qc_cfg.doublet_threshold,
            "min_cells_per_gene": qc_cfg.min_cells_per_gene,
        },
        "donor_qc": donor_qc,
        "quarantined_donors": quarantined_donors,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": round(elapsed, 1),
    }

    # ── Save checkpoint and report ─────────────────────────────────
    checkpoint_path = save_checkpoint(adata, project_dir, "qc")
    save_stage_report(report, project_dir, "qc")

    # ── Report progress ────────────────────────────────────────────
    if progress_tracker:
        progress_tracker.update("qc", str(checkpoint_path))

    return adata, report
