"""Audit trail tests -- append, hash chain, tamper detection, e-signatures."""

import pytest

pytestmark = pytest.mark.integration

from src.compliance.audit_trail import AuditTrail
from src.compliance.electronic_signature import ElectronicSignature
from src.auth.service import AuthService
from src.db import get_connection


# ── Basic Operations ─────────────────────────────────────────────────

def test_append_record(audit_trail):
    """Appending a record should return a hash and store all fields."""
    record_hash = audit_trail.append_record(
        user_id="user-001",
        action="CREATE",
        resource_type="project",
        resource_id="proj-001",
        details={"name": "Test Project"},
    )
    assert isinstance(record_hash, str)
    assert len(record_hash) == 64  # SHA-256 hex digest

    records = audit_trail.get_records(resource_id="proj-001")
    assert len(records) == 1
    assert records[0]["user_id"] == "user-001"
    assert records[0]["action"] == "CREATE"
    assert records[0]["resource_type"] == "project"


# ── Hash Chain Integrity ─────────────────────────────────────────────

def test_hash_chain_valid(audit_trail):
    """Appending 5 records should produce a valid hash chain."""
    for i in range(5):
        audit_trail.append_record(
            user_id=f"user-{i}",
            action="CREATE",
            resource_type="project",
            resource_id=f"proj-{i}",
        )

    result = audit_trail.verify_chain()
    assert result["valid"] is True
    assert result["records_checked"] == 5
    assert result["first_broken"] is None


def test_hash_chain_detects_tamper(audit_trail, tmp_audit_db):
    """Tampering with a record should break the hash chain."""
    for i in range(3):
        audit_trail.append_record(
            user_id=f"user-{i}",
            action="CREATE",
            resource_type="project",
            resource_id=f"proj-{i}",
            details={"index": i},
        )

    # Tamper with record 2 directly via raw SQL
    conn = get_connection(tmp_audit_db)
    try:
        conn.execute(
            "UPDATE audit_trail SET details_json = '{\"index\":999}' "
            "WHERE sequence_id = 2"
        )
        conn.commit()
    finally:
        conn.close()

    result = audit_trail.verify_chain()
    assert result["valid"] is False
    assert result["first_broken"] == 2


def test_genesis_hash(audit_trail):
    """First record should have previous_hash of 64 zeros."""
    audit_trail.append_record(
        user_id="user-001",
        action="CREATE",
        resource_type="project",
        resource_id="proj-001",
    )

    records = audit_trail.get_records()
    assert len(records) == 1
    assert records[0]["previous_hash"] == "0" * 64


# ── Append-Only Property ────────────────────────────────────────────

def test_records_are_append_only(audit_trail):
    """AuditTrail should have no update or delete methods."""
    public_methods = [
        m for m in dir(audit_trail) if not m.startswith("_")
    ]
    assert "update" not in public_methods
    assert "delete" not in public_methods
    assert not hasattr(audit_trail, "update")
    assert not hasattr(audit_trail, "delete")


# ── Filtered Queries ────────────────────────────────────────────────

def test_get_records_with_filters(audit_trail):
    """get_records should filter by resource_type correctly."""
    audit_trail.append_record("u1", "CREATE", "project", "p1")
    audit_trail.append_record("u1", "CREATE", "task", "t1")
    audit_trail.append_record("u2", "CREATE", "project", "p2")

    project_records = audit_trail.get_records(resource_type="project")
    assert len(project_records) == 2

    task_records = audit_trail.get_records(resource_type="task")
    assert len(task_records) == 1


# ── Electronic Signatures ───────────────────────────────────────────

def test_electronic_signature_success(tmp_path):
    """E-signature with correct password should succeed."""
    auth_db = tmp_path / "esig_auth.db"
    audit_db = tmp_path / "esig_audit.db"

    auth_svc = AuthService(db_path=auth_db)
    at = AuditTrail(db_path=audit_db)

    # Register a user
    reg = auth_svc.register("signer@example.com", "signpass", "reviewer")
    assert reg["success"]

    esig = ElectronicSignature(audit_trail=at, auth_db_path=auth_db)
    result = esig.sign(
        user_id=reg["user_id"],
        password="signpass",
        resource_type="gate",
        resource_id="gate-001",
        meaning="Approved QC results",
    )

    assert result["success"] is True
    assert "signature_hash" in result
    assert len(result["signature_hash"]) == 64


def test_electronic_signature_bad_password(tmp_path):
    """E-signature with wrong password should fail."""
    auth_db = tmp_path / "esig_auth2.db"
    audit_db = tmp_path / "esig_audit2.db"

    auth_svc = AuthService(db_path=auth_db)
    at = AuditTrail(db_path=audit_db)

    reg = auth_svc.register("signer2@example.com", "correctpass", "reviewer")
    assert reg["success"]

    esig = ElectronicSignature(audit_trail=at, auth_db_path=auth_db)
    result = esig.sign(
        user_id=reg["user_id"],
        password="wrongpass",
        resource_type="gate",
        resource_id="gate-002",
        meaning="Should fail",
    )

    assert result["success"] is False
    assert "failed" in result["error"].lower()
