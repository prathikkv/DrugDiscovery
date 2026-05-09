"""SoupX ambient RNA removal via rpy2 with graceful fallback (REQ-103).

Attempts ambient RNA contamination removal using SoupX through rpy2.
Falls back gracefully with clear skip reporting when SoupX or R
dependencies are unavailable, or when raw (unfiltered) counts are
not provided.

The HITL gate for SoupX skip is a UI concern (Phase 7). At the
pipeline level, the skip decision is encoded in config.skip_ambient_rna
or detected automatically (no raw counts, no R/SoupX). The audit
trail logging of the skip happens in the orchestrator (Plan 03).
"""

import logging
import time
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


def run_ambient_rna_removal(
    adata: ad.AnnData,
    config: PipelineConfig,
    project_dir: Path,
    progress_tracker: Optional[StageProgressTracker] = None,
    raw_counts_path: Optional[Path] = None,
) -> tuple[ad.AnnData, dict]:
    """Attempt ambient RNA removal using SoupX with graceful fallback.

    SoupX requires:
      1. rpy2 and R with SoupX installed
      2. Unfiltered (raw) count matrix from CellRanger

    If any dependency is missing or SoupX fails, the function returns
    the original adata unchanged with a skip report documenting why
    removal was not performed.

    Args:
        adata: Input AnnData object (post-QC or post-ingestion).
        config: PipelineConfig with skip_ambient_rna flag.
        project_dir: Project directory for checkpoints and reports.
        progress_tracker: Optional StageProgressTracker for progress
            reporting. None silently skips progress updates.
        raw_counts_path: Path to unfiltered (raw) count matrix from
            CellRanger. Required for SoupX. If None, SoupX is skipped.

    Returns:
        Tuple of (adata, ambient_rna_report_dict).
    """
    # -- User explicitly requested skip --
    if config.skip_ambient_rna:
        report = _skip_report(
            reason="user_skip",
            warning="Ambient RNA removal was skipped by user configuration",
        )
        _save_and_report(report, project_dir, progress_tracker)
        return adata, report

    # -- Check for existing checkpoint --
    existing = load_checkpoint(project_dir, "ambient_rna")
    if existing is not None:
        logger.info("Ambient RNA checkpoint found -- loading cached result")
        from src.pipeline.checkpointing import load_stage_report

        report = load_stage_report(project_dir, "ambient_rna") or {
            "stage": "ambient_rna",
            "cached": True,
        }
        if progress_tracker:
            progress_tracker.update("ambient_rna")
        return existing, report

    # -- Try importing rpy2 and SoupX --
    try:
        import rpy2.robjects as ro  # noqa: PLC0415, F401
        from rpy2.robjects.packages import importr  # noqa: PLC0415

        soupx = importr("SoupX")
    except Exception as exc:
        logger.warning("SoupX/rpy2 not available: %s", exc)
        report = _skip_report(
            reason="soupx_unavailable",
            warning=(
                f"SoupX or rpy2 not available ({exc}). "
                "Install R, rpy2, and the SoupX R package to enable "
                "ambient RNA removal."
            ),
        )
        _save_and_report(report, project_dir, progress_tracker)
        return adata, report

    # -- Check for raw (unfiltered) counts --
    if raw_counts_path is None or not Path(raw_counts_path).exists():
        logger.warning(
            "No raw counts path provided or path does not exist: %s",
            raw_counts_path,
        )
        report = _skip_report(
            reason="no_raw_counts",
            warning=(
                "SoupX requires unfiltered (raw) count matrix. "
                "Only filtered data provided."
            ),
        )
        _save_and_report(report, project_dir, progress_tracker)
        return adata, report

    # -- Run SoupX --
    try:
        adata, contamination_fraction = _run_soupx(
            adata, raw_counts_path, soupx, ro, progress_tracker
        )
    except Exception as exc:
        logger.error("SoupX execution failed: %s", exc)
        report = _skip_report(
            reason="soupx_error",
            warning=f"SoupX failed during execution: {exc}",
        )
        _save_and_report(report, project_dir, progress_tracker)
        return adata, report

    # -- Success --
    report = {
        "stage": "ambient_rna",
        "status": "completed",
        "method": "soupx",
        "contamination_fraction": round(contamination_fraction, 4),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    checkpoint_path = save_checkpoint(adata, project_dir, "ambient_rna")
    save_stage_report(report, project_dir, "ambient_rna")

    if progress_tracker:
        progress_tracker.update("ambient_rna", str(checkpoint_path))

    return adata, report


def _run_soupx(
    adata: ad.AnnData,
    raw_counts_path: Path,
    soupx,
    ro,
    progress_tracker: Optional[StageProgressTracker] = None,
) -> tuple[ad.AnnData, float]:
    """Execute SoupX ambient RNA removal.

    Converts Python data to R format, runs SoupX pipeline
    (SoupChannel -> setClusters -> autoEstCont -> adjustCounts),
    and converts results back.

    Args:
        adata: Filtered AnnData object.
        raw_counts_path: Path to raw (unfiltered) counts.
        soupx: Imported SoupX R package.
        ro: rpy2.robjects module.
        progress_tracker: Optional progress tracker.

    Returns:
        Tuple of (corrected_adata, contamination_fraction).
    """
    import numpy as np  # noqa: PLC0415
    import scipy.sparse as sp  # noqa: PLC0415
    from rpy2.robjects import numpy2ri, pandas2ri  # noqa: PLC0415
    from rpy2.robjects.packages import importr  # noqa: PLC0415

    numpy2ri.activate()
    pandas2ri.activate()

    try:
        base = importr("base")
        matrix_pkg = importr("Matrix")

        # Load raw counts
        import scanpy as sc  # noqa: PLC0415

        raw_path = Path(raw_counts_path)
        if raw_path.suffix == ".h5ad":
            raw_adata = sc.read_h5ad(str(raw_path))
        elif raw_path.suffix == ".h5":
            raw_adata = sc.read_10x_h5(str(raw_path), gex_only=True)
        elif raw_path.is_dir():
            raw_adata = sc.read_10x_mtx(str(raw_path), var_names="gene_symbols")
        else:
            raise ValueError(f"Unsupported raw counts format: {raw_path.suffix}")

        if progress_tracker:
            progress_tracker.update_substage("ambient_rna", 0.3)

        # Convert to dense arrays for R
        X_filtered = (
            adata.X.toarray() if sp.issparse(adata.X) else np.array(adata.X)
        )
        X_raw = (
            raw_adata.X.toarray()
            if sp.issparse(raw_adata.X)
            else np.array(raw_adata.X)
        )

        # Transpose: R expects genes x cells
        r_filtered = ro.r["matrix"](
            ro.FloatVector(X_filtered.T.flatten()),
            nrow=X_filtered.shape[1],
            ncol=X_filtered.shape[0],
        )
        r_raw = ro.r["matrix"](
            ro.FloatVector(X_raw.T.flatten()),
            nrow=X_raw.shape[1],
            ncol=X_raw.shape[0],
        )

        if progress_tracker:
            progress_tracker.update_substage("ambient_rna", 0.5)

        # Create SoupChannel
        sc_obj = soupx.SoupChannel(r_raw, r_filtered)

        # Set clusters (use leiden if available)
        if "leiden" in adata.obs.columns:
            clusters = ro.StrVector(adata.obs["leiden"].astype(str).values)
        else:
            # Single cluster fallback
            clusters = ro.StrVector(["0"] * adata.n_obs)

        sc_obj = soupx.setClusters(sc_obj, clusters)

        if progress_tracker:
            progress_tracker.update_substage("ambient_rna", 0.7)

        # Estimate contamination and adjust
        sc_obj = soupx.autoEstCont(sc_obj, verbose=False)
        corrected = soupx.adjustCounts(sc_obj)

        # Extract contamination fraction
        contamination_fraction = float(
            ro.r["slot"](sc_obj, "fit")[ro.r["which"](
                ro.r["names"](ro.r["slot"](sc_obj, "fit")) == "rhoEst"
            )[0] - 1]
        )

        if progress_tracker:
            progress_tracker.update_substage("ambient_rna", 0.9)

        # Convert back to numpy (genes x cells -> cells x genes)
        corrected_matrix = np.array(base.as_matrix(corrected)).T

        # Update adata with corrected counts
        if sp.issparse(adata.X):
            adata.X = sp.csr_matrix(corrected_matrix)
        else:
            adata.X = corrected_matrix

        logger.info(
            "SoupX ambient RNA removal complete. "
            "Contamination fraction: %.4f",
            contamination_fraction,
        )

        return adata, contamination_fraction

    finally:
        numpy2ri.deactivate()
        pandas2ri.deactivate()


def _skip_report(reason: str, warning: str) -> dict:
    """Build a standardized skip report."""
    return {
        "stage": "ambient_rna",
        "status": "skipped",
        "method": "skipped",
        "reason": reason,
        "warning": warning,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def _save_and_report(
    report: dict,
    project_dir: Path,
    progress_tracker: Optional[StageProgressTracker] = None,
) -> None:
    """Save report and update progress for skip cases."""
    save_stage_report(report, project_dir, "ambient_rna")
    if progress_tracker:
        progress_tracker.update("ambient_rna")
