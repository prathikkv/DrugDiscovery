"""Disease-agnostic scRNA-seq analysis pipeline.

Public API:
    run_pipeline() - Execute full pipeline with progress and checkpoint support
    PipelineConfig - Pipeline configuration with tissue-specific defaults
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional

from src.pipeline.config import PipelineConfig, QCConfig, ProcessingConfig, TISSUE_DEFAULTS

logger = logging.getLogger(__name__)


def run_pipeline(
    input_path,
    config: PipelineConfig,
    project_dir,
    task_manager=None,
    task_id: Optional[str] = None,
) -> dict:
    """Execute the full scRNA-seq analysis pipeline.

    Orchestrates all stages in sequence with checkpoint-based resume
    support and progress tracking. Each stage follows the protocol:
    (adata, config, project_dir, progress_tracker) -> (adata, report).

    Stage sequence:
        1. ingest - Load data from h5ad/h5/MTX
        2. ambient_rna - SoupX ambient RNA removal (graceful skip)
        3. qc - Quality control with doublet detection
        4. processing - Normalize, HVG, PCA, Harmony, UMAP, Leiden
        5. annotation - CellTypist cell type annotation
        6. de - Differential expression per cell type
        7. enrichment - Gene set enrichment (ORA) on DE results

    If a checkpoint exists from a previous run, the pipeline resumes
    from the stage after the latest checkpoint, skipping already
    completed stages.

    Args:
        input_path: Path to input data file or directory.
        config: PipelineConfig with tissue-specific defaults.
        project_dir: Root project directory (must contain uploads/,
            checkpoints/, results/, exports/ subdirectories).
        task_manager: Optional TaskManager for progress reporting.
        task_id: Optional task ID for TaskManager integration.

    Returns:
        Dict containing all stage reports, resume info, final paths,
        and pipeline metadata.
    """
    from src.pipeline.ambient_rna import run_ambient_rna_removal
    from src.pipeline.annotation import run_annotation, validate_annotations
    from src.pipeline.checkpointing import (
        get_latest_checkpoint,
        save_checkpoint,
    )
    from src.pipeline.differential_expression import run_differential_expression
    from src.pipeline.enrichment import run_enrichment
    from src.pipeline.ingestion import ingest_data
    from src.pipeline.processing import run_processing
    from src.pipeline.progress import StageProgressTracker
    from src.pipeline.qc import run_qc

    input_path = Path(input_path)
    project_dir = Path(project_dir)

    # Ensure result directories exist
    (project_dir / "results").mkdir(parents=True, exist_ok=True)
    (project_dir / "checkpoints").mkdir(parents=True, exist_ok=True)

    # Create progress tracker
    tracker = StageProgressTracker(task_manager, task_id)

    # Check for resume
    resumed_from = None
    resume_checkpoint = get_latest_checkpoint(project_dir)

    results: dict = {}

    # Stage order for resume logic
    stage_order = [
        "ingest",
        "ambient_rna",
        "qc",
        "processing",
        "annotation",
        "de",
        "enrichment",
    ]

    if resume_checkpoint is not None:
        checkpoint_stage, checkpoint_path = resume_checkpoint
        resumed_from = checkpoint_stage
        logger.info(
            "Resuming pipeline from checkpoint: stage='%s'",
            checkpoint_stage,
        )

        # Load checkpoint data
        import anndata as ad

        adata = ad.read_h5ad(checkpoint_path)

        # Mark all stages up to and including checkpoint as skipped
        checkpoint_idx = stage_order.index(checkpoint_stage)
        for stage_name in stage_order[: checkpoint_idx + 1]:
            results[stage_name] = {
                "status": "skipped",
                "reason": "resumed_from_checkpoint",
            }

        # Determine which stages remain
        remaining_stages = stage_order[checkpoint_idx + 1 :]
    else:
        remaining_stages = stage_order

    # ── Stage execution ──────────────────────────────────────────────

    # Stage a: ingest
    if "ingest" in remaining_stages:
        logger.info("Stage 1/7: Ingesting data from %s", input_path)
        adata = ingest_data(input_path)
        save_checkpoint(adata, project_dir, "ingest")
        tracker.update("ingest")
        results["ingest"] = {
            "stage": "ingest",
            "status": "completed",
            "n_cells": adata.n_obs,
            "n_genes": adata.n_vars,
            "input_path": str(input_path),
        }

    # Stage b: ambient_rna
    if "ambient_rna" in remaining_stages:
        logger.info("Stage 2/7: Ambient RNA removal")
        adata, report = run_ambient_rna_removal(
            adata, config, project_dir, tracker
        )
        results["ambient_rna"] = report

    # Stage c: qc
    if "qc" in remaining_stages:
        logger.info("Stage 3/7: Quality control")
        adata, report = run_qc(adata, config, project_dir, tracker)
        results["qc"] = report

    # Stage d: processing
    if "processing" in remaining_stages:
        logger.info("Stage 4/7: Processing (normalize, HVG, PCA, clustering)")
        adata, report = run_processing(adata, config, project_dir, tracker)
        results["processing"] = report

    # Stage e: annotation
    if "annotation" in remaining_stages:
        logger.info("Stage 5/7: Cell type annotation")
        adata, report = run_annotation(adata, config, project_dir, tracker)
        results["annotation"] = report

        # Validate annotations (REQ-107)
        discrepancies = validate_annotations(adata)
        results["annotation_validation"] = discrepancies

    # Stage f: de
    if "de" in remaining_stages:
        logger.info("Stage 6/7: Differential expression")
        adata, report = run_differential_expression(
            adata, config, project_dir, tracker
        )
        results["de"] = report

    # Stage g: enrichment
    if "enrichment" in remaining_stages:
        logger.info("Stage 7/7: Gene set enrichment")
        adata, report = run_enrichment(adata, config, project_dir, tracker)
        results["enrichment"] = report

    # ── Save final outputs ───────────────────────────────────────────

    # Save final annotated adata
    final_h5ad_path = project_dir / "results" / "final.h5ad"
    adata.write_h5ad(final_h5ad_path)
    logger.info("Saved final h5ad: %s", final_h5ad_path)

    # Build combined pipeline results
    n_cell_types = 0
    if hasattr(adata, "obs") and "cell_type" in adata.obs.columns:
        n_cell_types = int(adata.obs["cell_type"].nunique())

    pipeline_results = {
        **results,
        "resumed_from": resumed_from,
        "final_h5ad_path": str(final_h5ad_path),
        "n_cells_final": adata.n_obs,
        "n_genes_final": adata.n_vars,
        "n_cell_types": n_cell_types,
        "pipeline_config": json.loads(config.to_json()),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # Save combined report
    report_path = project_dir / "results" / "pipeline_report.json"
    with open(report_path, "w") as f:
        json.dump(pipeline_results, f, indent=2, default=str)
    logger.info("Saved pipeline report: %s", report_path)

    # Finalize progress
    tracker.update("finalize")

    return pipeline_results
