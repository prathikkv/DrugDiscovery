"""BioOrchestrator v2 -- Streamlit multipage application entrypoint.

Run with: streamlit run src/app.py

Uses st.navigation and st.Page for routing (not the pages/ directory
convention). Shows login page for unauthenticated users and 7 pages
organized into Setup/Analysis/Results sections for authenticated users.
Design system CSS is injected globally.
"""

import streamlit as st

from src.pages.components.styles import inject_design_system

st.set_page_config(
    page_title="BioOrchestrator v2",
    page_icon=":material/biotech:",
    layout="wide",
)

# Inject design system CSS globally (once, after set_page_config)
inject_design_system()


def _build_navigation():
    """Build navigation based on authentication state.

    Unauthenticated: login page only.
    Authenticated: 7 pages in 3 sections (Setup, Analysis, Results).
    """
    if "user" not in st.session_state:
        # Unauthenticated: show only login
        pages = [
            st.Page("src/pages/login.py", title="Login", icon=":material/login:"),
        ]
        return st.navigation(pages)

    # Authenticated: 7 pages with section grouping
    pages = {
        "Setup": [
            st.Page(
                "src/pages/projects.py",
                title="Projects",
                icon=":material/folder:",
                default=True,
            ),
        ],
        "Analysis": [
            st.Page(
                "src/pages/omics.py",
                title="Omics Analysis",
                icon=":material/dna:",
            ),
            st.Page(
                "src/pages/evidence.py",
                title="Evidence Explorer",
                icon=":material/search:",
            ),
            st.Page(
                "src/pages/insights.py",
                title="AI Insights",
                icon=":material/psychology:",
            ),
        ],
        "Results": [
            st.Page(
                "src/pages/scorecard.py",
                title="Scorecard",
                icon=":material/assessment:",
            ),
            st.Page(
                "src/pages/audit.py",
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

pg = _build_navigation()
_render_sidebar()
pg.run()
