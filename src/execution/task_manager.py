"""Background task execution engine with SQLite state persistence (REQ-602, REQ-603).

Solves Streamlit's fundamental limitation: reruns kill long-running
operations. By submitting work to a ThreadPoolExecutor and persisting
state to SQLite, task progress survives page refreshes.

IMPORTANT: Each database operation creates its own connection via
get_connection(). Connections are NOT stored as instance variables
because threads require separate connections.
"""

import json
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src import config
from src.db import get_connection
from src.execution.models import TaskRecord, TaskStatus


# ── Schema ───────────────────────────────────────────────────────────

TASK_SCHEMA = """\
CREATE TABLE IF NOT EXISTS tasks (
    task_id         TEXT PRIMARY KEY,
    project_id      TEXT,
    task_type       TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'PENDING'
                    CHECK(status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')),
    progress        REAL NOT NULL DEFAULT 0.0,
    created_at      TEXT NOT NULL,
    started_at      TEXT,
    completed_at    TEXT,
    result_json     TEXT,
    error_message   TEXT,
    checkpoint_path TEXT
);
"""


def init_tasks_db(conn) -> None:
    """Create the tasks table if it does not exist."""
    conn.executescript(TASK_SCHEMA)


class TaskManager:
    """Manages background task execution with SQLite state persistence.

    Tasks are submitted to a ThreadPoolExecutor and their state
    transitions (PENDING -> RUNNING -> COMPLETED/FAILED) are
    persisted to SQLite so they survive Streamlit reruns.
    """

    def __init__(
        self,
        db_path: Path = None,
        max_workers: int = 2,
    ) -> None:
        self.db_path = db_path or config.TASKS_DB
        self._write_lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # Ensure schema exists
        conn = get_connection(self.db_path)
        try:
            init_tasks_db(conn)
        finally:
            conn.close()

    def submit(
        self,
        _task_id: str,
        _task_type: str,
        _fn,
        *args,
        project_id: str = None,
        **kwargs,
    ) -> str:
        """Submit a function for background execution.

        Args:
            _task_id: Unique task identifier (or None for auto-generated).
                Prefixed with underscore to avoid collision with kwargs
                forwarded to fn (e.g. task_id passed to the callable).
            _task_type: Category of task (pipeline, export, analysis).
            _fn: Callable to execute in background thread.
            *args: Positional arguments passed to fn.
            project_id: Optional project association.
            **kwargs: Keyword arguments passed to fn.

        Returns:
            The task_id.
        """
        task_id = _task_id
        if not task_id:
            task_id = str(uuid.uuid4())

        created_at = datetime.now(timezone.utc).isoformat()

        # Persist PENDING state
        conn = get_connection(self.db_path)
        try:
            with self._write_lock:
                conn.execute(
                    "INSERT INTO tasks "
                    "(task_id, project_id, task_type, status, progress, created_at) "
                    "VALUES (?, ?, ?, 'PENDING', 0.0, ?)",
                    (task_id, project_id, _task_type, created_at),
                )
                conn.commit()
        finally:
            conn.close()

        # Submit to thread pool -- pass fn_args and fn_kwargs as bundles
        # to avoid parameter name collisions at the executor level
        self.executor.submit(self._wrapped_run, task_id, _fn, args, kwargs)

        return task_id

    def _wrapped_run(
        self,
        task_id: str,
        fn,
        fn_args: tuple,
        fn_kwargs: dict,
    ) -> None:
        """Execute fn in a background thread with state tracking.

        Updates status to RUNNING, executes fn, then updates to
        COMPLETED or FAILED based on outcome.

        fn_args and fn_kwargs are passed as bundles (not *args/**kwargs)
        to avoid parameter name collisions at the submit() call site.
        """
        # Mark as RUNNING
        started_at = datetime.now(timezone.utc).isoformat()
        conn = get_connection(self.db_path)
        try:
            with self._write_lock:
                conn.execute(
                    "UPDATE tasks SET status = 'RUNNING', started_at = ? "
                    "WHERE task_id = ?",
                    (started_at, task_id),
                )
                conn.commit()
        finally:
            conn.close()

        try:
            result = fn(*fn_args, **fn_kwargs)

            # Mark as COMPLETED
            completed_at = datetime.now(timezone.utc).isoformat()
            result_json = json.dumps(result) if result is not None else None

            conn = get_connection(self.db_path)
            try:
                with self._write_lock:
                    conn.execute(
                        "UPDATE tasks SET status = 'COMPLETED', "
                        "completed_at = ?, result_json = ?, progress = 1.0 "
                        "WHERE task_id = ?",
                        (completed_at, result_json, task_id),
                    )
                    conn.commit()
            finally:
                conn.close()

        except Exception as exc:
            # Mark as FAILED
            completed_at = datetime.now(timezone.utc).isoformat()
            error_message = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"

            conn = get_connection(self.db_path)
            try:
                with self._write_lock:
                    conn.execute(
                        "UPDATE tasks SET status = 'FAILED', "
                        "completed_at = ?, error_message = ? "
                        "WHERE task_id = ?",
                        (completed_at, error_message, task_id),
                    )
                    conn.commit()
            finally:
                conn.close()

    def update_progress(
        self,
        task_id: str,
        progress: float,
        checkpoint_path: str = None,
    ) -> None:
        """Update task progress (callable from within a running task).

        Args:
            task_id: ID of the task to update.
            progress: Progress value between 0.0 and 1.0.
            checkpoint_path: Optional path to a checkpoint file for resume.
        """
        progress = max(0.0, min(1.0, progress))

        conn = get_connection(self.db_path)
        try:
            with self._write_lock:
                if checkpoint_path is not None:
                    conn.execute(
                        "UPDATE tasks SET progress = ?, checkpoint_path = ? "
                        "WHERE task_id = ?",
                        (progress, checkpoint_path, task_id),
                    )
                else:
                    conn.execute(
                        "UPDATE tasks SET progress = ? WHERE task_id = ?",
                        (progress, task_id),
                    )
                conn.commit()
        finally:
            conn.close()

    def get_status(self, task_id: str) -> Optional[TaskRecord]:
        """Get the current state of a task.

        Creates its own connection -- safe to call from any thread.
        Returns TaskRecord or None if task not found.
        """
        conn = get_connection(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                return None
            return TaskRecord.from_row(row)
        finally:
            conn.close()

    def get_tasks(
        self,
        project_id: str = None,
        status: TaskStatus = None,
    ) -> list[TaskRecord]:
        """Query tasks with optional filters.

        Returns list of TaskRecord ordered by created_at DESC.
        """
        conditions = []
        params: list = []

        if project_id is not None:
            conditions.append("project_id = ?")
            params.append(project_id)
        if status is not None:
            conditions.append("status = ?")
            params.append(status.value)

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        conn = get_connection(self.db_path)
        try:
            rows = conn.execute(
                f"SELECT * FROM tasks {where} ORDER BY created_at DESC",
                params,
            ).fetchall()
            return [TaskRecord.from_row(row) for row in rows]
        finally:
            conn.close()

    def cancel(self, task_id: str) -> bool:
        """Cancel a PENDING task.

        Cannot cancel RUNNING tasks in ThreadPoolExecutor without
        cooperative cancellation. Returns True if cancelled, False otherwise.
        """
        conn = get_connection(self.db_path)
        try:
            with self._write_lock:
                cursor = conn.execute(
                    "UPDATE tasks SET status = 'CANCELLED' "
                    "WHERE task_id = ? AND status = 'PENDING'",
                    (task_id,),
                )
                conn.commit()
                return cursor.rowcount > 0
        finally:
            conn.close()

    def shutdown(self, wait: bool = True) -> None:
        """Shut down the thread pool executor.

        Args:
            wait: If True, wait for all submitted tasks to complete.
        """
        self.executor.shutdown(wait=wait)
