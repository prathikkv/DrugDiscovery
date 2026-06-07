"""BioOrchestrator v2 -- Streamlit multipage application entrypoint.

Run with: streamlit run src/app.py

Uses st.navigation and st.Page for routing. All pages are accessible
without login. Design system CSS is injected globally.
"""

import streamlit as st

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

# Auto-set a session user so auth guards on individual pages pass.
if "user" not in st.session_state:
    st.session_state["user"] = {
        "user_id": "default",
        "email": "admin@targetsight.ai",
        "role": "admin",
    }


def _build_navigation():
    pages = {
        "": [
            st.Page("pages/home.py", title="Home", icon=":material/home:", default=True),
        ],
        "Setup": [
            st.Page("pages/projects.py", title="Projects", icon=":material/folder:"),
        ],
        "Analysis": [
            st.Page("pages/omics.py", title="Omics Analysis", icon=":material/science:"),
            st.Page("pages/evidence.py", title="Evidence Explorer", icon=":material/search:"),
            st.Page("pages/insights.py", title="AI Insights", icon=":material/psychology:"),
        ],
        "Results": [
            st.Page("pages/scorecard.py", title="Scorecard", icon=":material/assessment:"),
            st.Page("pages/audit.py", title="Audit Trail", icon=":material/history:"),
        ],
    }
    return st.navigation(pages)


def _render_sidebar():
    with st.sidebar:
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


# ── Main ─────────────────────────────────────────────────────────────

pg = _build_navigation()
_render_sidebar()
pg.run()
