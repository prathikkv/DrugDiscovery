"""Project CRUD tests -- create, list, get, delete, audit, h5ad fixture."""

import pytest

from src import config
from src.project.service import ProjectService


# ── Basic CRUD ───────────────────────────────────────────────────────

def test_create_project(project_service):
    """Creating a project should return a Project with correct fields."""
    project = project_service.create("Alpha Study", "Phase I trial", "user-001")

    assert project.name == "Alpha Study"
    assert project.description == "Phase I trial"
    assert project.created_by == "user-001"
    assert project.status == "active"
    assert len(project.project_id) > 0
    assert project.config_json == "{}"


def test_list_projects(project_service):
    """Listing projects should return all active projects."""
    project_service.create("Project A", None, "user-001")
    project_service.create("Project B", None, "user-001")
    project_service.create("Project C", None, "user-002")

    projects = project_service.list()
    assert len(projects) == 3


def test_get_project(project_service):
    """Getting a project by ID should return the correct project."""
    created = project_service.create("Lookup Test", "desc", "user-001")
    fetched = project_service.get(created.project_id)

    assert fetched is not None
    assert fetched.project_id == created.project_id
    assert fetched.name == "Lookup Test"


def test_delete_project(project_service):
    """Deleting a project should soft-delete it (not in active list)."""
    created = project_service.create("To Delete", None, "user-001")
    result = project_service.delete(created.project_id, "user-001")

    assert result is True
    active = project_service.list()
    assert len(active) == 0

    # Project still exists with status 'deleted'
    deleted = project_service.get(created.project_id)
    assert deleted is not None
    assert deleted.status == "deleted"


def test_delete_nonexistent(project_service):
    """Deleting a non-existent project should return False."""
    result = project_service.delete("fake-id-999", "user-001")
    assert result is False


# ── Audit Integration ───────────────────────────────────────────────

def test_crud_produces_audit_records(project_service, audit_trail):
    """Create and delete should both produce audit trail records."""
    project = project_service.create("Audited Project", None, "user-001")
    project_service.delete(project.project_id, "user-001")

    records = audit_trail.get_records(resource_type="project")
    assert len(records) >= 2  # CREATE + DELETE

    actions = [r["action"] for r in records]
    assert "CREATE" in actions
    assert "DELETE" in actions


# ── Directory Structure ──────────────────────────────────────────────

def test_project_directory_created(project_service):
    """Creating a project should create per-project directories."""
    project = project_service.create("Dir Test", None, "user-001")

    project_dir = config.PROJECTS_DIR / project.project_id
    assert (project_dir / "uploads").exists()
    assert (project_dir / "checkpoints").exists()
    assert (project_dir / "results").exists()
    assert (project_dir / "exports").exists()


# ── Synthetic h5ad Fixture ───────────────────────────────────────────

def test_synthetic_h5ad_fixture(synthetic_h5ad):
    """Synthetic h5ad fixture should produce a valid 50x10 sparse dataset."""
    import anndata
    import scipy.sparse as sp

    adata = anndata.read_h5ad(synthetic_h5ad)

    # Shape
    assert adata.shape == (50, 10)

    # Obs columns
    assert "cell_type" in adata.obs.columns
    assert "donor_id" in adata.obs.columns
    assert "n_genes_by_counts" in adata.obs.columns
    assert "pct_counts_mt" in adata.obs.columns

    # Var columns
    assert "gene_name" in adata.var.columns
    assert "feature_biotype" in adata.var.columns

    # X is sparse
    assert sp.issparse(adata.X)
