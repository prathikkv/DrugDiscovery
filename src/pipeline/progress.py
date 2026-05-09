"""TaskManager integration for pipeline stage progress (REQ-108).

Provides StageProgressTracker that maps pipeline stage completions
to fractional progress values and reports them to the TaskManager.
Operates silently when no TaskManager is available, allowing the
pipeline to run standalone for testing.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Cumulative progress weights per stage.
# Each value represents the fraction of total pipeline work completed
# when that stage finishes.
STAGE_WEIGHTS: dict[str, float] = {
    "ingest": 0.10,
    "ambient_rna": 0.15,
    "qc": 0.25,
    "processing": 0.50,
    "annotation": 0.65,
    "de": 0.80,
    "enrichment": 0.90,
    "finalize": 1.00,
}

# Ordered list for interpolation lookups
_STAGE_ORDER = list(STAGE_WEIGHTS.keys())


class StageProgressTracker:
    """Maps pipeline stage completions to TaskManager progress updates.

    If task_manager or task_id is None, all update calls become
    silent no-ops. This allows running the pipeline without a
    TaskManager (e.g., in tests or standalone scripts).

    Usage::

        tracker = StageProgressTracker(task_manager, task_id)
        # ... run QC stage ...
        tracker.update("qc")  # reports 25% progress
        # ... during processing, report sub-stage progress ...
        tracker.update_substage("processing", 0.5)  # reports 37.5%
    """

    def __init__(
        self,
        task_manager=None,
        task_id: Optional[str] = None,
    ) -> None:
        """Initialize the progress tracker.

        Args:
            task_manager: TaskManager instance (or None for no-op mode).
            task_id: Task ID to update progress for (or None for no-op).
        """
        self._task_manager = task_manager
        self._task_id = task_id

    def update(
        self,
        stage_name: str,
        checkpoint_path: Optional[str] = None,
    ) -> None:
        """Report that a pipeline stage has completed.

        Looks up the cumulative weight for the stage and calls
        task_manager.update_progress().

        Args:
            stage_name: Name of the completed stage (must be in STAGE_WEIGHTS).
            checkpoint_path: Optional path to the stage checkpoint file.
        """
        if self._task_manager is None or self._task_id is None:
            return

        progress = STAGE_WEIGHTS.get(stage_name)
        if progress is None:
            logger.warning(
                "Unknown stage '%s' -- skipping progress update", stage_name
            )
            return

        self._task_manager.update_progress(
            self._task_id, progress, checkpoint_path
        )
        logger.debug(
            "Progress update: stage=%s, progress=%.2f", stage_name, progress
        )

    def update_substage(
        self,
        stage_name: str,
        fraction: float,
    ) -> None:
        """Report intra-stage progress.

        Interpolates between the previous stage's weight and the
        current stage's weight to compute a fractional progress value.

        For example, ``update_substage("qc", 0.5)`` reports progress
        halfway between the ambient_rna weight (0.15) and the qc
        weight (0.25), which is 0.20.

        Args:
            stage_name: Name of the current stage.
            fraction: Completion fraction within the stage (0.0 to 1.0).
        """
        if self._task_manager is None or self._task_id is None:
            return

        current_weight = STAGE_WEIGHTS.get(stage_name)
        if current_weight is None:
            logger.warning(
                "Unknown stage '%s' -- skipping substage update", stage_name
            )
            return

        # Find the previous stage's weight
        stage_idx = _STAGE_ORDER.index(stage_name)
        if stage_idx == 0:
            prev_weight = 0.0
        else:
            prev_weight = STAGE_WEIGHTS[_STAGE_ORDER[stage_idx - 1]]

        # Clamp fraction
        fraction = max(0.0, min(1.0, fraction))

        progress = prev_weight + fraction * (current_weight - prev_weight)
        self._task_manager.update_progress(self._task_id, progress)
        logger.debug(
            "Substage update: stage=%s, fraction=%.2f, progress=%.3f",
            stage_name,
            fraction,
            progress,
        )
