"""Pipeline module test suite covering config, ingestion, QC, checkpointing,
progress tracking, and no-hardcoded-biology regression.

Tests only modules that run offline (no CellTypist model downloads, no
network access). Annotation and enrichment are integration-test candidates
for Phase 8.
"""

import time
from pathlib import Path

import anndata as ad
import numpy as np
import pytest

pytestmark = pytest.mark.integration

from src.pipeline.config import PipelineConfig, TISSUE_DEFAULTS
from src.pipeline.ingestion import ingest_data
from src.pipeline.qc import run_qc
from src.pipeline.checkpointing import (
    save_checkpoint,
    load_checkpoint,
    get_latest_checkpoint,
)
from src.pipeline.progress import StageProgressTracker


# ── Config Tests ────────────────────────────────────────────────────


class TestPipelineConfig:
    """Tests for PipelineConfig, QCConfig, and TISSUE_DEFAULTS."""

    def test_pipeline_config_for_tissue(self):
        """Verify tissue-specific config defaults."""
        brain = PipelineConfig.for_tissue("brain")
        assert brain.qc.max_pct_mt == 5.0
        assert brain.tissue_type == "brain"

        tumor = PipelineConfig.for_tissue("tumor")
        assert tumor.qc.max_pct_mt == 25.0

        unknown = PipelineConfig.for_tissue("unknown")
        assert unknown.qc.max_pct_mt == 15.0  # default fallback

    def test_pipeline_config_serialization(self):
        """Verify JSON roundtrip preserves all fields."""
        original = PipelineConfig.for_tissue("lung")
        json_str = original.to_json()
        restored = PipelineConfig.from_json(json_str)

        assert restored.tissue_type == original.tissue_type
        assert restored.qc.max_pct_mt == original.qc.max_pct_mt
        assert restored.qc.min_genes == original.qc.min_genes
        assert restored.processing.n_pcs == original.processing.n_pcs
        assert restored.celltypist_model == original.celltypist_model
        assert restored.de_method == original.de_method
        assert restored.enrichment_gene_sets == original.enrichment_gene_sets

    def test_tissue_defaults_coverage(self):
        """TISSUE_DEFAULTS should have at least 11 entries (10 tissues + default)."""
        assert len(TISSUE_DEFAULTS) >= 11
        assert "default" in TISSUE_DEFAULTS
        assert "brain" in TISSUE_DEFAULTS
        assert "tumor" in TISSUE_DEFAULTS
        assert "lung" in TISSUE_DEFAULTS


# ── Ingestion Tests ─────────────────────────────────────────────────


class TestIngestion:
    """Tests for ingest_data() multi-format loader."""

    def test_ingest_h5ad(self, pipeline_h5ad):
        """Ingest h5ad file and verify shape and raw_counts layer."""
        adata = ingest_data(pipeline_h5ad)

        assert isinstance(adata, ad.AnnData)
        assert adata.n_obs == 100
        assert adata.n_vars == 50
        assert "raw_counts" in adata.layers

    def test_ingest_invalid_format(self, tmp_path):
        """Unsupported file format should raise ValueError."""
        txt_file = tmp_path / "bad_data.txt"
        txt_file.write_text("not a real data file")

        with pytest.raises(ValueError, match="Unsupported format"):
            ingest_data(txt_file)


# ── QC Tests ────────────────────────────────────────────────────────


class TestQC:
    """Tests for run_qc() configurable quality control."""

    def test_qc_applies_config_thresholds(self, pipeline_h5ad, pipeline_project_dir):
        """Strict mito threshold should filter out cells with high MT expression."""
        adata = ingest_data(pipeline_h5ad)
        n_cells_before = adata.n_obs

        # Strict mito threshold of 5% to ensure some cells are filtered
        config = PipelineConfig.for_tissue("brain")  # max_pct_mt=5.0

        adata_qc, report = run_qc(adata, config, pipeline_project_dir)

        assert adata_qc.n_obs < n_cells_before
        assert report["n_cells_in"] > report["n_cells_out"]

    def test_qc_report_structure(self, pipeline_h5ad, pipeline_project_dir):
        """QC report should contain all expected keys."""
        adata = ingest_data(pipeline_h5ad)
        config = PipelineConfig.for_tissue("default")

        _, report = run_qc(adata, config, pipeline_project_dir)

        assert report["stage"] == "qc"
        assert "n_cells_in" in report
        assert "n_cells_out" in report
        assert "thresholds_applied" in report
        assert "max_pct_mt" in report["thresholds_applied"]


# ── Checkpointing Tests ────────────────────────────────────────────


class TestCheckpointing:
    """Tests for save_checkpoint, load_checkpoint, get_latest_checkpoint."""

    def test_checkpointing_save_load(self, pipeline_h5ad, pipeline_project_dir):
        """Save a checkpoint and load it back, verifying shape is preserved."""
        adata = ingest_data(pipeline_h5ad)
        original_shape = (adata.n_obs, adata.n_vars)

        save_checkpoint(adata, pipeline_project_dir, "qc")

        loaded = load_checkpoint(pipeline_project_dir, "qc")
        assert loaded is not None
        assert (loaded.n_obs, loaded.n_vars) == original_shape

    def test_checkpoint_resume(self, pipeline_h5ad, pipeline_project_dir):
        """get_latest_checkpoint should return the furthest completed stage."""
        adata = ingest_data(pipeline_h5ad)

        # Save two checkpoints
        save_checkpoint(adata, pipeline_project_dir, "qc")
        save_checkpoint(adata, pipeline_project_dir, "processing")

        latest = get_latest_checkpoint(pipeline_project_dir)
        assert latest is not None
        stage_name, path = latest
        assert stage_name == "processing"


# ── Progress Tracker Tests ──────────────────────────────────────────


class TestProgressTracker:
    """Tests for StageProgressTracker."""

    def test_progress_tracker_no_taskmanager(self):
        """Tracker with no TaskManager should not raise on update."""
        tracker = StageProgressTracker(None, None)
        # Should be a silent no-op
        tracker.update("qc")
        tracker.update_substage("qc", 0.5)

    def test_progress_tracker_with_taskmanager(self, task_manager, pipeline_project_dir):
        """Tracker with real TaskManager should update task progress."""
        # Submit a dummy long-running task
        task_id = task_manager.submit(
            "test-progress-task",
            "pipeline",
            lambda: time.sleep(5),
        )

        # Give the task a moment to start running
        time.sleep(0.2)

        # Create tracker and update progress
        tracker = StageProgressTracker(task_manager, task_id)
        tracker.update("qc")  # Should set progress to 0.25

        status = task_manager.get_status(task_id)
        assert status is not None
        assert status.progress >= 0.25


# ── Regression Test ─────────────────────────────────────────────────


class TestNoBiology:
    """Regression test ensuring no hardcoded biology in pipeline module."""

    def test_no_hardcoded_biology(self):
        """No pipeline .py file should contain drug/target references (REQ-101)."""
        pipeline_dir = Path("src/pipeline")
        forbidden = ["GIPR", "GLP1R", "MariTide", "ADIPOQ"]

        violations = []
        for py_file in pipeline_dir.glob("*.py"):
            content = py_file.read_text()
            content_upper = content.upper()
            for term in forbidden:
                if term.upper() in content_upper:
                    violations.append(
                        f"{py_file.name} contains '{term}'"
                    )

        assert violations == [], (
            f"Hardcoded biology found in pipeline: {violations}"
        )
