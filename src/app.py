"""BioOrchestrator v2 -- Streamlit multipage application entrypoint.

Run with: streamlit run src/app.py

Uses st.navigation and st.Page for routing (not the pages/ directory
convention). Shows login page for unauthenticated users and 7 pages
organized into Setup/Analysis/Results sections for authenticated users.
Design system CSS is injected globally.
"""

from datetime import datetime, timezone

import streamlit as st

from src.config import SESSION_TIMEOUT_MINUTES
from src.logging_config import setup_logging
from src.pages.components.styles import inject_design_system

setup_logging()

st.set_page_config(
    page_title="TargetSight",
    page_icon=":material/biotech:",
    layout="wide",
)

# Inject design system CSS globally (once, after set_page_config)
inject_design_system()


def _check_session_timeout() -> None:
    """Expire idle sessions after SESSION_TIMEOUT_MINUTES of inactivity."""
    if "user" not in st.session_state:
        return
    now = datetime.now(timezone.utc)
    last_active = st.session_state.get("last_active_at")
    if last_active is not None:
        elapsed = (now - last_active).total_seconds()
        if elapsed > SESSION_TIMEOUT_MINUTES * 60:
            st.session_state.clear()
            st.session_state["session_expired"] = True
            st.rerun()
    st.session_state["last_active_at"] = now


def _build_navigation():
    """Build navigation based on authentication state.

    Unauthenticated: login page only.
    Authenticated: 7 pages in 3 sections (Setup, Analysis, Results).
    """
    if "user" not in st.session_state:
        # Unauthenticated: show only login
        pages = [
            st.Page("pages/login.py", title="Login", icon=":material/login:"),
        ]
        return st.navigation(pages)

    # Authenticated: 8 pages in 4 sections (Home + Setup + Analysis + Results)
    pages = {
        "": [
            st.Page(
                "pages/home.py",
                title="Home",
                icon=":material/home:",
                default=True,
            ),
        ],
        "Setup": [
            st.Page(
                "pages/projects.py",
                title="Projects",
                icon=":material/folder:",
            ),
        ],
        "Analysis": [
            st.Page(
                "pages/omics.py",
                title="Omics Analysis",
                icon=":material/science:",
            ),
            st.Page(
                "pages/evidence.py",
                title="Evidence Explorer",
                icon=":material/search:",
            ),
            st.Page(
                "pages/insights.py",
                title="AI Insights",
                icon=":material/psychology:",
            ),
        ],
        "Results": [
            st.Page(
                "pages/scorecard.py",
                title="Scorecard",
                icon=":material/assessment:",
            ),
            st.Page(
                "pages/audit.py",
                title="Audit Trail",
                icon=":material/history:",
            ),
        ],
    }
    return st.navigation(pages)


def _render_sidebar():
    """Render sidebar with user info, mode display, and logout button."""
    if "user" in st.session_state:
        user = st.session_state["user"]
        with st.sidebar:
            st.markdown(f"**User:** {user['email']}")
            st.markdown(f"**Role:** {user['role']}")

            # Show active project if set
            active_project_id = st.session_state.get("active_project_id")
            if active_project_id:
                project_name = st.session_state.get(
                    "active_project_name", active_project_id
                )
                st.markdown(f"**Project:** {project_name}")

            # Show current mode
            project_config = st.session_state.get("project_config", {})
            mode = project_config.get("mode", "exploration")
            mode_icon = ":material/explore:" if mode == "exploration" else ":material/verified_user:"
            st.markdown(f"**Mode:** {mode_icon} {mode.title()}")

            st.divider()
            if st.button("Logout", type="secondary", use_container_width=True):
                del st.session_state["user"]
                st.rerun()


# ── Main ─────────────────────────────────────────────────────────────

_check_session_timeout()
pg = _build_navigation()
_render_sidebar()
pg.run()
