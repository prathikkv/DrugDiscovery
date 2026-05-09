"""BioOrchestrator v2 -- Streamlit multipage application entrypoint.

Run with: streamlit run src/app.py

Uses st.navigation and st.Page for routing (not the pages/ directory
convention). Shows login page for unauthenticated users and projects
page for authenticated users.
"""

import streamlit as st

st.set_page_config(
    page_title="BioOrchestrator v2",
    page_icon=":material/biotech:",
    layout="wide",
)


def _build_navigation():
    """Build navigation based on authentication state."""
    if "user" not in st.session_state:
        # Unauthenticated: show only login
        pages = [
            st.Page("src/pages/login.py", title="Login", icon=":material/login:"),
        ]
    else:
        # Authenticated: show projects (hide login)
        pages = [
            st.Page("src/pages/projects.py", title="Projects", icon=":material/folder:"),
        ]
    return st.navigation(pages)


def _render_sidebar():
    """Render sidebar with user info and logout button."""
    if "user" in st.session_state:
        user = st.session_state["user"]
        with st.sidebar:
            st.markdown(f"**User:** {user['email']}")
            st.markdown(f"**Role:** {user['role']}")
            st.divider()
            if st.button("Logout", type="secondary", use_container_width=True):
                del st.session_state["user"]
                st.rerun()


# ── Main ─────────────────────────────────────────────────────────────

pg = _build_navigation()
_render_sidebar()
pg.run()
