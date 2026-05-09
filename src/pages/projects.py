"""Project CRUD page using ProjectService.

Requires authentication -- redirects to login if not authenticated.
Provides:
- Create project form (name + description)
- List of active projects with delete buttons
"""

import streamlit as st

from src.project.service import ProjectService


# ── Auth Guard ───────────────────────────────────────────────────────

if "user" not in st.session_state:
    st.warning("Please log in to access projects.")
    st.stop()

user = st.session_state["user"]
ps = ProjectService()

st.title("Projects")

# ── Create Project ───────────────────────────────────────────────────

st.subheader("Create New Project")

with st.form("create_project_form"):
    proj_name = st.text_input("Project Name")
    proj_desc = st.text_area("Description (optional)")
    create_submitted = st.form_submit_button(
        "Create Project", use_container_width=True
    )

if create_submitted:
    if not proj_name:
        st.error("Project name is required.")
    else:
        project = ps.create(
            name=proj_name,
            description=proj_desc or None,
            created_by=user["user_id"],
        )
        st.success(f"Project '{project.name}' created successfully.")
        st.rerun()

# ── Project List ─────────────────────────────────────────────────────

st.subheader("Active Projects")

projects = ps.list()

if not projects:
    st.info("No active projects. Create one above.")
else:
    for project in projects:
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{project.name}**")
                if project.description:
                    st.caption(project.description)
                st.caption(f"Created: {project.created_at[:19]} UTC")
            with col2:
                if st.button(
                    "Delete",
                    key=f"delete_{project.project_id}",
                    type="secondary",
                ):
                    ps.delete(project.project_id, user["user_id"])
                    st.rerun()
