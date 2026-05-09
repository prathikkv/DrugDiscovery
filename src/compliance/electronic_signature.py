"""Electronic signature with re-authentication (REQ-504).

21 CFR Part 11 requires electronic signatures to include:
- Re-authentication (password verification) before signing
- SHA-256 hash of the signature payload
- Recording in the audit trail

Re-authentication uses bcrypt directly (not AuthService) to avoid
circular dependency -- only the password check is needed.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import bcrypt

from src import config
from src.compliance.audit_trail import AuditTrail
from src.db import get_connection


class ElectronicSignature:
    """21 CFR Part 11 compliant electronic signatures.

    Requires re-authentication before every signing operation.
    Each signature produces a SHA-256 hash and is recorded in the
    audit trail.
    """

    def __init__(
        self,
        audit_trail: AuditTrail,
        auth_db_path: Path = None,
    ) -> None:
        self.audit_trail = audit_trail
        self.auth_db_path = auth_db_path or config.AUTH_DB

    def sign(
        self,
        user_id: str,
        password: str,
        resource_type: str,
        resource_id: str,
        meaning: str,
    ) -> dict:
        """Sign a resource after re-authentication.

        Args:
            user_id: ID of the signing user.
            password: Plaintext password for re-authentication.
            resource_type: Type of resource being signed.
            resource_id: ID of the resource being signed.
            meaning: Textual meaning of the signature (e.g. "Approved QC results").

        Returns:
            {"success": True, "signature_hash": ..., "timestamp": ...} on success,
            {"success": False, "error": ...} on failure.
        """
        # Re-authenticate: look up user and verify password
        conn = get_connection(self.auth_db_path)
        try:
            row = conn.execute(
                "SELECT password_hash FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            return {"success": False, "error": "Re-authentication failed"}

        if not bcrypt.checkpw(
            password.encode("utf-8"),
            row["password_hash"].encode("utf-8"),
        ):
            return {"success": False, "error": "Re-authentication failed"}

        # Build signature payload
        timestamp = datetime.now(timezone.utc).isoformat()
        payload = {
            "user_id": user_id,
            "timestamp": timestamp,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "meaning": meaning,
        }
        signature_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        # Record in audit trail
        self.audit_trail.append_record(
            user_id=user_id,
            action="SIGN",
            resource_type=resource_type,
            resource_id=resource_id,
            details={"meaning": meaning, "signature_hash": signature_hash},
        )

        return {
            "success": True,
            "signature_hash": signature_hash,
            "timestamp": timestamp,
        }
