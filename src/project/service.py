"""Project CRUD service with audit trail integration (REQ-605).

Every state-changing operation (create, delete) logs to the audit trail
for 21 CFR Part 11 compliance. Per-project directory structures are
created at project creation time.

Each method creates its own database connection for thread safety
(per-operation connection pattern from Plan 01).
"""

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src import config
from src.compliance.audit_trail import AuditTrail
from src.db import get_connection
from src.project.db import (
    get_project,
    init_project_db,
    insert_project,
    list_projects,
    update_project_status,
)
from src.project.models import Project


class ProjectService:
    """Manages project lifecycle with audit logging.

    Every CRUD operation is recorded in the audit trail.
    Soft-delete only -- projects are never physically removed.
    """

    def __init__(
        self,
        db_path: Path = None,
        audit_trail: AuditTrail = None,
    ) -> None:
        self.db_path = db_path or config.PROJECTS_DB
        self.audit_trail = audit_trail or AuditTrail()
        self._write_lock = threading.Lock()

        # Ensure schema exists
        conn = get_connection(self.db_path)
        try:
            init_project_db(conn)
        finally:
            conn.close()

    def create(
        self,
        name: str,
        description: Optional[str],
        created_by: str,
        project_config: Optional[dict] = None,
    ) -> Project:
        """Create a new project with directory structure and audit record.

        Args:
            name: Project display name.
            description: Optional project description.
            created_by: user_id of the creator.
            project_config: Optional config dict (stored as JSON).

        Returns:
            The created Project dataclass.
        """
        project_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        config_json = json.dumps(
            project_config or {},
            sort_keys=True,
            separators=(",", ":"),
        )

        # Insert into database
        conn = get_connection(self.db_path)
        try:
            with self._write_lock:
                insert_project(
                    conn,
                    project_id=project_id,
                    name=name,
                    description=description,
                    created_by=created_by,
                    created_at=now,
                    updated_at=now,
                    status="active",
                    config_json=config_json,
                )
        finally:
            conn.close()

        # Create per-project directory structure
        project_dir = config.PROJECTS_DIR / project_id
        for subdir in ("uploads", "checkpoints", "results", "exports"):
            (project_dir / subdir).mkdir(parents=True, exist_ok=True)

        # Audit trail
        self.audit_trail.append_record(
            user_id=created_by,
            action="CREATE",
            resource_type="project",
            resource_id=project_id,
            details={"name": name},
        )

        return Project(
            project_id=project_id,
            name=name,
            description=description,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            status="active",
            config_json=config_json,
        )

    def list(self, status: str = "active") -> list[Project]:
        """List projects filtered by status.

        Args:
            status: Filter by status (default: 'active').

        Returns:
            List of Project dataclasses.
        """
        conn = get_connection(self.db_path)
        try:
            rows = list_projects(conn, status=status)
            return [Project.from_row(row) for row in rows]
        finally:
            conn.close()

    def get(self, project_id: str) -> Optional[Project]:
        """Get a single project by ID.

        Returns:
            Project dataclass or None if not found.
        """
        conn = get_connection(self.db_path)
        try:
            row = get_project(conn, project_id)
            if row is None:
                return None
            return Project.from_row(row)
        finally:
            conn.close()

    def delete(self, project_id: str, deleted_by: str) -> bool:
        """Soft-delete a project (set status to 'deleted').

        Does NOT remove the database row or the project directory.
        Logs the deletion to the audit trail.

        Args:
            project_id: ID of the project to delete.
            deleted_by: user_id performing the deletion.

        Returns:
            True if project was found and deleted, False otherwise.
        """
        now = datetime.now(timezone.utc).isoformat()

        conn = get_connection(self.db_path)
        try:
            with self._write_lock:
                rows_affected = update_project_status(
                    conn, project_id, "deleted", now
                )
        finally:
            conn.close()

        if rows_affected == 0:
            return False

        # Audit trail
        self.audit_trail.append_record(
            user_id=deleted_by,
            action="DELETE",
            resource_type="project",
            resource_id=project_id,
        )

        return True
