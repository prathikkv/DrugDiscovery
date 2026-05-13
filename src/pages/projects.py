"""Enhanced Project page with mode toggle and showcase scenario selector.

Requires authentication -- redirects to login if not authenticated.
Provides:
- Create project form with exploration/compliance mode toggle
- Showcase scenario selector with 6 pharma scenarios (card grid)
- Project list with Open/Delete actions and active project indicator
"""

import json

import streamlit as st

from src.pages.components.showcase import SHOWCASE_SCENARIOS, load_scenario
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
    proj_name = st.text_input("Project Name", key="projects_name")
    proj_desc = st.text_area("Description (optional)", key="projects_desc")
    proj_mode = st.radio(
        "Analysis Mode",
        options=["exploration", "compliance"],
        format_func=lambda m: {
            "exploration": "Exploration -- HITL gates auto-approve for rapid iteration",
            "compliance": "Compliance -- HITL gates require electronic signature (21 CFR Part 11)",
        }[m],
        key="projects_mode",
    )
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
            project_config={"mode": proj_mode},
        )
        st.session_state["active_project_id"] = project.project_id
        st.session_state["active_project_name"] = project.name
        st.session_state["project_config"] = {"mode": proj_mode}
        st.success(f"Project '{project.name}' created successfully.")
        st.rerun()


# ── Showcase Scenarios ───────────────────────────────────────────────

st.divider()
st.subheader("Showcase Scenarios")
st.caption("Pre-loaded pharma scenarios with cached evidence. No live API calls required.")

scenario_names = list(SHOWCASE_SCENARIOS.keys())

# Display in 3-column grid (2 rows of 3)
for row_start in range(0, len(scenario_names), 3):
    row_scenarios = scenario_names[row_start : row_start + 3]
    cols = st.columns(3)
    for col_idx, name in enumerate(row_scenarios):
        scenario = SHOWCASE_SCENARIOS[name]
        with cols[col_idx]:
            with st.container(border=True):
                st.markdown(f"**{name}**")
                st.caption(scenario["description"])
                st.caption(f"Company: {scenario.get('company', 'N/A')}")
                if st.button(
                    "Load Scenario",
                    key=f"projects_load_{name}",
                    use_container_width=True,
                ):
                    try:
                        data = load_scenario(name)
                        # Create project for showcase
                        project = ps.create(
                            name=f"Showcase: {name}",
                            description=scenario["description"],
                            created_by=user["user_id"],
                            project_config={
                                "mode": "exploration",
                                "showcase": name,
                            },
                        )
                        pid = project.project_id

                        # Pre-populate ALL workflow data in session_state
                        if data.get("evidence"):
                            st.session_state[f"project_{pid}_evidence"] = data["evidence"]
                        if data.get("reasoning"):
                            st.session_state[f"project_{pid}_reasoning"] = data["reasoning"]
                        if data.get("scoring"):
                            st.session_state[f"project_{pid}_scorecard"] = data["scoring"]
                        if data.get("pipeline_report"):
                            st.session_state[f"project_{pid}_pipeline_result"] = data["pipeline_report"]

                        # Set as active project
                        st.session_state["active_project_id"] = pid
                        st.session_state["active_project_name"] = project.name
                        st.session_state["project_config"] = {
                            "mode": "exploration",
                            "showcase": name,
                        }
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to load scenario: {e}")


# ── Project List ─────────────────────────────────────────────────────

st.divider()
st.subheader("Active Projects")

projects = ps.list()
active_project_id = st.session_state.get("active_project_id")

if not projects:
    st.info("No active projects. Create one above or load a showcase scenario.")
else:
    for project in projects:
        is_active = project.project_id == active_project_id
        with st.container(border=True):
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                # Active indicator
                prefix = ":material/check_circle: " if is_active else ""
                st.markdown(f"**{prefix}{project.name}**")
                if project.description:
                    st.caption(project.description)
                st.caption(f"Created: {project.created_at[:19]} UTC")

                # Show project config if available
                try:
                    config_data = json.loads(project.config_json) if project.config_json else {}
                    if config_data.get("mode"):
                        st.caption(f"Mode: {config_data['mode']}")
                    if config_data.get("showcase"):
                        st.caption(f"Showcase: {config_data['showcase']}")
                except (json.JSONDecodeError, TypeError):
                    pass

            with col2:
                if st.button(
                    "Open",
                    key=f"projects_open_{project.project_id}",
                    type="primary" if not is_active else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["active_project_id"] = project.project_id
                    st.session_state["active_project_name"] = project.name
                    # Load project config
                    try:
                        config_data = json.loads(project.config_json) if project.config_json else {}
                        st.session_state["project_config"] = config_data
                    except (json.JSONDecodeError, TypeError):
                        st.session_state["project_config"] = {}
                    st.rerun()

            with col3:
                if st.button(
                    "Delete",
                    key=f"projects_delete_{project.project_id}",
                    type="secondary",
                    use_container_width=True,
                ):
                    ps.delete(project.project_id, user["user_id"])
                    # Clear active project if deleting active
                    if project.project_id == active_project_id:
                        if "active_project_id" in st.session_state:
                            del st.session_state["active_project_id"]
                        if "active_project_name" in st.session_state:
                            del st.session_state["active_project_name"]
                        if "project_config" in st.session_state:
                            del st.session_state["project_config"]
                    st.rerun()
