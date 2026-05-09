"""Stage checkpoint and report persistence (REQ-109).

Saves and loads intermediate .h5ad files at stage boundaries so the
pipeline can resume from the last completed stage. Also manages
per-stage JSON reports in the project results directory.
"""

import json
import logging
from pathlib import Path
from typing import Optional

import anndata as ad

logger = logging.getLogger(__name__)

# Canonical stage execution order -- used by get_latest_checkpoint()
# to determine which checkpoint represents the furthest progress.
STAGE_ORDER: list[str] = [
    "ingest",
    "ambient_rna",
    "qc",
    "processing",
    "annotation",
    "de",
    "enrichment",
]


def save_checkpoint(
    adata: ad.AnnData,
    project_dir: Path,
    stage_name: str,
) -> Path:
    """Save an AnnData checkpoint for the given stage.

    Writes adata to ``{project_dir}/checkpoints/{stage_name}.h5ad``.
    Creates the checkpoints directory if it does not exist.

    Args:
        adata: The AnnData object to persist.
        project_dir: Root directory of the project.
        stage_name: Pipeline stage identifier (e.g., "qc", "processing").

    Returns:
        Path to the saved checkpoint file.
    """
    checkpoint_dir = project_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_path = checkpoint_dir / f"{stage_name}.h5ad"
    adata.write_h5ad(checkpoint_path)
    logger.info("Saved checkpoint: %s", checkpoint_path)

    return checkpoint_path


def load_checkpoint(
    project_dir: Path,
    stage_name: str,
) -> Optional[ad.AnnData]:
    """Load a checkpoint for the given stage, if it exists.

    Args:
        project_dir: Root directory of the project.
        stage_name: Pipeline stage identifier.

    Returns:
        AnnData object if checkpoint exists, None otherwise.
    """
    checkpoint_path = project_dir / "checkpoints" / f"{stage_name}.h5ad"

    if not checkpoint_path.exists():
        logger.debug("No checkpoint found for stage '%s'", stage_name)
        return None

    logger.info("Loading checkpoint: %s", checkpoint_path)
    return ad.read_h5ad(checkpoint_path)


def get_latest_checkpoint(
    project_dir: Path,
) -> Optional[tuple[str, Path]]:
    """Find the latest checkpoint by stage order.

    Checks for checkpoint files in reverse stage order and returns
    the (stage_name, path) of the furthest completed stage.

    Args:
        project_dir: Root directory of the project.

    Returns:
        Tuple of (stage_name, checkpoint_path) for the latest
        checkpoint, or None if no checkpoints exist.
    """
    checkpoint_dir = project_dir / "checkpoints"

    if not checkpoint_dir.exists():
        return None

    # Walk stages in reverse order to find the latest
    for stage_name in reversed(STAGE_ORDER):
        checkpoint_path = checkpoint_dir / f"{stage_name}.h5ad"
        if checkpoint_path.exists():
            logger.info(
                "Latest checkpoint: stage '%s' at %s",
                stage_name,
                checkpoint_path,
            )
            return (stage_name, checkpoint_path)

    return None


def save_stage_report(
    report: dict,
    project_dir: Path,
    stage_name: str,
) -> Path:
    """Save a stage report as JSON.

    Writes to ``{project_dir}/results/{stage_name}_report.json``.
    Creates the results directory if needed.

    Args:
        report: Dictionary containing stage results and metrics.
        project_dir: Root directory of the project.
        stage_name: Pipeline stage identifier.

    Returns:
        Path to the saved report file.
    """
    results_dir = project_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    report_path = results_dir / f"{stage_name}_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    logger.info("Saved report: %s", report_path)
    return report_path


def load_stage_report(
    project_dir: Path,
    stage_name: str,
) -> Optional[dict]:
    """Load a stage report if it exists.

    Args:
        project_dir: Root directory of the project.
        stage_name: Pipeline stage identifier.

    Returns:
        Report dictionary if found, None otherwise.
    """
    report_path = project_dir / "results" / f"{stage_name}_report.json"

    if not report_path.exists():
        logger.debug("No report found for stage '%s'", stage_name)
        return None

    with open(report_path) as f:
        return json.load(f)
