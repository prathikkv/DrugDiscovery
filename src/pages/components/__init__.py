"""Shared UI components for BioOrchestrator v2 pages.

Provides:
- get_task_manager(): Thread-safe TaskManager singleton via st.cache_resource
- styles: Design system CSS and HTML helpers
- hitl_gate: Reusable HITL gate with dual-mode behavior
- showcase: Pre-cached showcase scenario definitions and loader
"""

import streamlit as st


@st.cache_resource
def get_task_manager():
    """Return a shared TaskManager instance (thread-safe singleton).

    This MUST live here (not in app.py) because app.py is a Streamlit
    script entry point that calls st.set_page_config() and pg.run() at
    module level -- importing it from page files would execute the full
    script and crash.
    """
    from src.execution.task_manager import TaskManager

    return TaskManager(max_workers=2)
