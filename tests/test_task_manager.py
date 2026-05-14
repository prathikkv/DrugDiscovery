"""TaskManager tests -- submit, status, failure, progress, persistence."""

import time

import pytest

pytestmark = pytest.mark.integration

from src.execution.models import TaskStatus
from src.execution.task_manager import TaskManager


# ── Submit and Complete ──────────────────────────────────────────────

def test_submit_and_complete(task_manager):
    """Submitted task should complete and show COMPLETED status."""

    def fast_task():
        time.sleep(0.1)
        return {"result": "done"}

    task_id = task_manager.submit("task-ok-1", "test", fast_task)
    assert task_id == "task-ok-1"

    # Wait for completion
    time.sleep(1.0)

    record = task_manager.get_status(task_id)
    assert record is not None
    assert record.status == TaskStatus.COMPLETED
    assert record.progress == 1.0


# ── Submit and Fail ──────────────────────────────────────────────────

def test_submit_and_fail(task_manager):
    """Task that raises should show FAILED status with error message."""

    def failing_task():
        raise ValueError("Something went wrong")

    task_id = task_manager.submit("task-fail-1", "test", failing_task)

    # Wait for failure
    time.sleep(1.0)

    record = task_manager.get_status(task_id)
    assert record is not None
    assert record.status == TaskStatus.FAILED
    assert "Something went wrong" in record.error_message


# ── Progress Update ──────────────────────────────────────────────────

def test_progress_update(task_manager):
    """Task that calls update_progress should have progress > 0."""

    def progress_task():
        task_manager.update_progress("task-prog-1", 0.5)
        time.sleep(0.1)
        return "done"

    task_manager.submit("task-prog-1", "test", progress_task)

    # Wait for completion
    time.sleep(1.0)

    record = task_manager.get_status("task-prog-1")
    assert record is not None
    # Progress should be 1.0 at completion (auto-set by _wrapped_run)
    assert record.progress == 1.0


# ── State Persistence ────────────────────────────────────────────────

def test_status_survives_reconnect(task_manager, tmp_tasks_db):
    """Task status should persist across TaskManager instances."""

    def simple_task():
        return "persisted"

    task_manager.submit("task-persist-1", "test", simple_task)

    # Wait for completion
    time.sleep(1.0)

    # Shut down the original manager
    task_manager.shutdown()

    # Create a NEW TaskManager with the SAME db_path
    tm2 = TaskManager(db_path=tmp_tasks_db, max_workers=1)
    try:
        record = tm2.get_status("task-persist-1")
        assert record is not None
        assert record.status == TaskStatus.COMPLETED
        assert record.task_type == "test"
    finally:
        tm2.shutdown()


# ── Task Filtering ───────────────────────────────────────────────────

def test_get_tasks_filter(task_manager):
    """get_tasks should filter by project_id correctly."""

    def noop():
        return None

    task_manager.submit("t1", "test", noop, project_id="proj-A")
    task_manager.submit("t2", "test", noop, project_id="proj-A")
    task_manager.submit("t3", "test", noop, project_id="proj-B")

    # Wait for completion
    time.sleep(1.0)

    proj_a_tasks = task_manager.get_tasks(project_id="proj-A")
    assert len(proj_a_tasks) == 2

    proj_b_tasks = task_manager.get_tasks(project_id="proj-B")
    assert len(proj_b_tasks) == 1
