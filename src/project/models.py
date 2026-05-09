"""Project data models -- Project dataclass."""

import sqlite3
from dataclasses import dataclass
from typing import Optional


@dataclass
class Project:
    """Represents a research project in BioOrchestrator.

    Maps 1:1 with the projects table schema. Soft-deletable via
    status field (never physically removed).
    """

    project_id: str
    name: str
    description: Optional[str]
    created_by: str
    created_at: str
    updated_at: str
    status: str  # "active", "archived", "deleted"
    config_json: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Project":
        """Create a Project from a sqlite3.Row."""
        return cls(
            project_id=row["project_id"],
            name=row["name"],
            description=row["description"],
            created_by=row["created_by"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            status=row["status"],
            config_json=row["config_json"],
        )
