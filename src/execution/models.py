"""Task execution data models -- TaskStatus enum and TaskRecord dataclass."""

import sqlite3
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TaskStatus(Enum):
    """Lifecycle states for background tasks."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class TaskRecord:
    """Represents a persisted task state.

    Mirrors the tasks table schema for easy round-tripping
    between SQLite rows and Python objects.
    """

    task_id: str
    project_id: Optional[str]
    task_type: str
    status: TaskStatus
    progress: float
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    result_json: Optional[str]
    error_message: Optional[str]
    checkpoint_path: Optional[str]

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "TaskRecord":
        """Create a TaskRecord from a sqlite3.Row."""
        return cls(
            task_id=row["task_id"],
            project_id=row["project_id"],
            task_type=row["task_type"],
            status=TaskStatus(row["status"]),
            progress=row["progress"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            result_json=row["result_json"],
            error_message=row["error_message"],
            checkpoint_path=row["checkpoint_path"],
        )
