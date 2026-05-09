"""Shared test fixtures for BioOrchestrator v2.

Provides:
- synthetic_h5ad: 50x10 sparse h5ad fixture (REQ-805)
- Temp database path fixtures for each module
- Pre-configured service fixtures with teardown
"""

import sys
from pathlib import Path

# Ensure src imports work from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import pytest
import scipy.sparse as sp

import anndata as ad

from src.auth.service import AuthService
from src.compliance.audit_trail import AuditTrail
from src.execution.task_manager import TaskManager
from src.project.service import ProjectService


# ── Synthetic h5ad Fixture (REQ-805) ─────────────────────────────────

@pytest.fixture
def synthetic_h5ad(tmp_path):
    """Create a synthetic h5ad file with 50 cells and 10 genes.

    Returns the path to the written file. Uses fixed random seed
    for reproducibility.
    """
    rng = np.random.default_rng(42)

    # Sparse count matrix: 50 cells x 10 genes
    X = sp.random(50, 10, density=0.1, format="csr", random_state=42,
                  dtype=np.float32)
    # Scale to integer-ish counts
    X.data = np.round(X.data * 10).astype(np.float32)

    # Cell metadata
    cell_types = rng.choice(
        ["T_cell", "B_cell", "Macrophage", "Epithelial"], size=50
    )
    donor_ids = rng.choice(["D1", "D2", "D3"], size=50)
    n_genes = rng.integers(200, 5000, size=50)
    pct_mt = rng.uniform(0, 15, size=50)

    obs = pd.DataFrame(
        {
            "cell_type": cell_types,
            "donor_id": donor_ids,
            "n_genes_by_counts": n_genes,
            "pct_counts_mt": pct_mt,
        },
        index=[f"cell_{i}" for i in range(50)],
    )

    # Gene metadata
    var = pd.DataFrame(
        {
            "gene_name": [f"GENE{i}" for i in range(10)],
            "feature_biotype": ["protein_coding"] * 10,
        },
        index=[f"GENE{i}" for i in range(10)],
    )

    adata = ad.AnnData(X=X, obs=obs, var=var)

    path = tmp_path / "synthetic_50x10.h5ad"
    adata.write_h5ad(path)

    return path


# ── Temp Database Fixtures ───────────────────────────────────────────

@pytest.fixture
def tmp_auth_db(tmp_path):
    """Temporary auth database path."""
    return tmp_path / "test_auth.db"


@pytest.fixture
def tmp_audit_db(tmp_path):
    """Temporary audit database path."""
    return tmp_path / "test_audit.db"


@pytest.fixture
def tmp_tasks_db(tmp_path):
    """Temporary tasks database path."""
    return tmp_path / "test_tasks.db"


@pytest.fixture
def tmp_projects_db(tmp_path):
    """Temporary projects database path."""
    return tmp_path / "test_projects.db"


# ── Service Fixtures ─────────────────────────────────────────────────

@pytest.fixture
def auth_service(tmp_auth_db):
    """Pre-configured AuthService with temp database."""
    return AuthService(db_path=tmp_auth_db)


@pytest.fixture
def audit_trail(tmp_audit_db):
    """Pre-configured AuditTrail with temp database."""
    return AuditTrail(db_path=tmp_audit_db)


@pytest.fixture
def task_manager(tmp_tasks_db):
    """Pre-configured TaskManager with temp database and teardown."""
    tm = TaskManager(db_path=tmp_tasks_db, max_workers=2)
    yield tm
    tm.shutdown()


@pytest.fixture
def project_service(tmp_projects_db, audit_trail):
    """Pre-configured ProjectService with temp database and audit trail."""
    return ProjectService(db_path=tmp_projects_db, audit_trail=audit_trail)


# ── Pipeline Fixtures ───────────────────────────────────────────────

@pytest.fixture
def pipeline_h5ad(tmp_path):
    """Create a pipeline-ready synthetic h5ad with MT genes and realistic structure.

    100 cells x 50 genes including 3 MT- genes for QC testing.
    Includes donor_id and leiden columns for processing compatibility.
    """
    rng = np.random.default_rng(42)

    n_cells = 100
    n_genes = 50

    # Gene names: 3 MT genes + 47 regular genes
    mt_genes = ["MT-CO1", "MT-CO2", "MT-ND1"]
    regular_genes = [f"GENE{i}" for i in range(47)]
    gene_names = mt_genes + regular_genes

    # Sparse count matrix with density=0.3
    X = sp.random(
        n_cells, n_genes, density=0.3, format="csr",
        random_state=42, dtype=np.float32,
    )
    # Scale to integer counts (0-100 range)
    X.data = np.round(X.data * 100).astype(np.float32)

    # Make some cells have high MT expression (>20% of total counts)
    # by boosting MT gene columns for first 15 cells
    X_dense = X.toarray()
    for cell_idx in range(15):
        for mt_idx in range(3):
            X_dense[cell_idx, mt_idx] = rng.integers(50, 200)
    X = sp.csr_matrix(X_dense)

    # Cell metadata
    donor_ids = rng.choice(["D1", "D2", "D3"], size=n_cells)
    n_genes_counts = rng.integers(200, 5000, size=n_cells)

    obs = pd.DataFrame(
        {
            "donor_id": donor_ids,
            "n_genes_by_counts": n_genes_counts,
        },
        index=[f"cell_{i}" for i in range(n_cells)],
    )

    # Gene metadata
    var = pd.DataFrame(
        {
            "gene_name": gene_names,
            "feature_biotype": ["protein_coding"] * n_genes,
        },
        index=gene_names,
    )

    adata = ad.AnnData(X=X, obs=obs, var=var)

    path = tmp_path / "pipeline_test.h5ad"
    adata.write_h5ad(path)

    return path


@pytest.fixture
def pipeline_project_dir(tmp_path):
    """Create a project directory structure matching Phase 1 conventions."""
    project_dir = tmp_path / "test_project"
    for subdir in ("uploads", "checkpoints", "results", "exports"):
        (project_dir / subdir).mkdir(parents=True, exist_ok=True)
    return project_dir
