# Phase 7: UI Integration - Research

**Researched:** 2026-05-12
**Domain:** Multi-page Streamlit application with HITL gates, design system, and pre-cached showcase scenarios
**Confidence:** HIGH

## Summary

Phase 7 integrates all six prior phases (Foundation, Omics, Evidence, Reasoning, Scoring, Reporting) into a 7-page Streamlit application that lets a scientist run a complete target assessment end-to-end through the UI. The existing codebase provides a solid shell: `src/app.py` already implements `st.navigation`/`st.Page` routing with auth-based dynamic page selection, `src/pages/login.py` provides login/registration, and `src/pages/projects.py` handles project CRUD. The existing `bioorchestrator_real/app.py` provides a complete reference implementation with a professional CSS design system (primary #0071e3, dark sidebar, metric cards, panel components, IBM Plex Mono for data) that must be adapted for the v2 app.

The primary technical challenges are: (1) wiring 7 pages through a coherent workflow where each page consumes the output of the previous step via `st.session_state`, (2) implementing 9 HITL gates across 3 modules with dual-mode behavior (Exploration auto-approves, Compliance blocks with e-signature), (3) building 6 pre-cached showcase scenarios that can run the full workflow in under 5 minutes with no live API calls, and (4) polling `TaskManager` for background task progress without triggering full-page reruns (solved with `st.fragment` and `run_every`).

All backend services already exist with clean public APIs. The UI pages are thin integration layers: they instantiate services (`EvidenceAggregator`, `ReasoningEngine`, `ScoringFramework`, `DossierGenerator`), submit long-running work through `TaskManager`, display results with Plotly charts via `st.plotly_chart`, and gate progression through HITL checkpoints stored in `st.session_state`. The `st.dialog` decorator (with `dismissible=False` for compliance mode) is the right tool for e-signature re-authentication modals.

**Primary recommendation:** Build 5 new page files (`src/pages/omics.py`, `src/pages/evidence.py`, `src/pages/insights.py`, `src/pages/scorecard.py`, `src/pages/audit.py`), a shared HITL gate component (`src/pages/components/hitl_gate.py`), a design system CSS module (`src/pages/components/styles.py`), a showcase scenario loader (`src/pages/components/showcase.py`), and update `src/app.py` to route all 7 pages with section grouping. Use `st.fragment(run_every="2s")` for background task polling. Store all inter-page state in `st.session_state` under namespaced keys.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| streamlit | >=1.45 | Multi-page app framework with st.navigation, st.Page, st.dialog, st.fragment | Already in project. st.navigation provides section-grouped pages, st.dialog provides modal overlays for HITL gates, st.fragment enables partial reruns for progress polling |
| plotly | 5.24.1 | All interactive visualizations (radar, bar, UMAP, volcano, heatmap) | Already used in scoring module (build_single_radar, build_comparative_radar) and reporting module (VisualizationBuilder). Streamlit renders via st.plotly_chart |
| pydantic | >=2.11.0 | All data models (ScorecardResult, DossierData, etc.) | Already used throughout project for scoring, reporting, and reasoning models |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| bcrypt | (existing) | Password re-authentication in e-signature dialogs | Used by ElectronicSignature.sign() for compliance-mode HITL gates |
| sqlite3 (stdlib) | 3.x | All persistence (auth, projects, tasks, audit, evidence cache) | Already used via per-operation connection pattern from Phase 1 |
| json (stdlib) | 3.x | Showcase scenario data loading from pre-cached JSON files | Loading pre-built evidence, scoring, and reasoning results |
| pathlib (stdlib) | 3.x | File path management for data, exports, scenarios | Already used throughout project |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| st.dialog for HITL gates | st.form in main page | st.dialog provides modal overlay that blocks interaction, which is correct for compliance-mode gates. Forms don't block the rest of the page. |
| st.fragment for polling | st.rerun with time.sleep | st.fragment only reruns the polling section, not the entire page. Full rerun flickers and loses scroll position. |
| Session state for inter-page data | Database persistence | Session state is simpler and faster for workflow data within a session. Database is already used for durable data (tasks, audit). Combine both: session state for active workflow, database for persistence. |
| Custom CSS via st.markdown | streamlit-extras or st-styled | No extra dependency. The existing bioorchestrator_real/app.py already demonstrates the exact pattern with st.markdown and unsafe_allow_html=True. Proven to work. |

**Installation:**
```bash
# No new dependencies required. All libraries already installed.
```

## Architecture Patterns

### Recommended Project Structure

```
src/
  app.py                              # Entrypoint: st.navigation with 7 pages, sidebar, CSS injection
  pages/
    __init__.py
    login.py                           # Existing: login/register (Phase 1)
    projects.py                        # Enhanced: add mode toggle, scenario selector
    omics.py                           # NEW: omics pipeline execution + 3 HITL gates
    evidence.py                        # NEW: evidence gathering + 3 HITL gates
    insights.py                        # NEW: AI reasoning display + 3 HITL gates
    scorecard.py                       # NEW: scoring + radar chart + verdict
    audit.py                           # NEW: audit trail viewer + hash chain verify
    components/
      __init__.py
      styles.py                        # Design system CSS (inject via st.markdown)
      hitl_gate.py                     # Reusable HITL gate component
      showcase.py                      # Pre-cached scenario loader
      metrics.py                       # Metric card HTML helpers
```

### Pattern 1: Auth-Gated Dynamic Navigation with Section Groups

**What:** Use st.navigation with dict-based section grouping, dynamically selecting pages based on auth state and project context.
**When to use:** Always -- this is the app shell.

```python
# src/app.py
import streamlit as st
from src.pages.components.styles import inject_design_system

st.set_page_config(
    page_title="BioOrchestrator v2",
    page_icon=":material/biotech:",
    layout="wide",
)

inject_design_system()

def _build_navigation():
    if "user" not in st.session_state:
        pages = [st.Page("src/pages/login.py", title="Login", icon=":material/login:")]
    else:
        pages = {
            "Setup": [
                st.Page("src/pages/projects.py", title="Projects", icon=":material/folder:", default=True),
            ],
            "Analysis": [
                st.Page("src/pages/omics.py", title="Omics Analysis", icon=":material/dna:"),
                st.Page("src/pages/evidence.py", title="Evidence Explorer", icon=":material/search:"),
                st.Page("src/pages/insights.py", title="AI Insights", icon=":material/psychology:"),
            ],
            "Results": [
                st.Page("src/pages/scorecard.py", title="Scorecard", icon=":material/assessment:"),
                st.Page("src/pages/audit.py", title="Audit Trail", icon=":material/history:"),
            ],
        }
    return st.navigation(pages)

pg = _build_navigation()
_render_sidebar()  # User info + logout
pg.run()
```

### Pattern 2: HITL Gate Component with Dual-Mode Behavior

**What:** A reusable component that renders an approval/rejection UI. In Exploration mode, it auto-approves with a logged override. In Compliance mode, it blocks with an e-signature dialog.
**When to use:** At every HITL checkpoint (9 total across 3 modules).

```python
# src/pages/components/hitl_gate.py
import streamlit as st
from src.compliance.audit_trail import AuditTrail
from src.compliance.electronic_signature import ElectronicSignature

def hitl_gate(
    gate_id: str,
    gate_title: str,
    module: str,          # "omics", "evidence", "reasoning"
    description: str,
    data_summary: dict,   # Key metrics to display for review
) -> bool:
    """Render a HITL gate. Returns True if approved, False if rejected.

    In Exploration mode: auto-approves, logs override, returns True immediately.
    In Compliance mode: shows blocking dialog requiring e-signature.
    """
    project_config = st.session_state.get("project_config", {})
    mode = project_config.get("mode", "exploration")
    gate_key = f"hitl_{gate_id}_approved"

    # Already approved in this session
    if st.session_state.get(gate_key):
        return True

    if mode == "exploration":
        # Auto-approve with logged override
        audit = AuditTrail()
        audit.append_record(
            user_id=st.session_state["user"]["user_id"],
            action="AUTO_APPROVE",
            resource_type="hitl_gate",
            resource_id=gate_id,
            details={"module": module, "mode": "exploration", "gate_title": gate_title},
        )
        st.session_state[gate_key] = True
        return True

    # Compliance mode: render blocking gate
    st.divider()
    with st.container(border=True):
        st.subheader(f"Approval Required: {gate_title}")
        st.caption(description)
        # Display data summary for review
        for key, value in data_summary.items():
            st.metric(key, value)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Approve", key=f"approve_{gate_id}", type="primary"):
                _show_esign_dialog(gate_id, gate_title, module, approved=True)
        with col2:
            if st.button("Reject", key=f"reject_{gate_id}", type="secondary"):
                _show_esign_dialog(gate_id, gate_title, module, approved=False)

    st.stop()  # Block page progression until gate is resolved
    return False


@st.dialog("Electronic Signature Required", width="medium", dismissible=False)
def _show_esign_dialog(gate_id: str, gate_title: str, module: str, approved: bool):
    """Non-dismissible e-signature dialog for compliance mode."""
    st.write("Re-authenticate to sign this decision.")
    password = st.text_input("Password", type="password", key=f"esign_pw_{gate_id}")
    meaning = "Approved" if approved else "Rejected"
    st.write(f"**Action:** {meaning} -- {gate_title}")

    if st.button("Sign", key=f"sign_{gate_id}", type="primary"):
        audit = AuditTrail()
        esig = ElectronicSignature(audit)
        result = esig.sign(
            user_id=st.session_state["user"]["user_id"],
            password=password,
            resource_type="hitl_gate",
            resource_id=gate_id,
            meaning=f"{meaning}: {gate_title} ({module})",
        )
        if result["success"]:
            st.session_state[f"hitl_{gate_id}_approved"] = approved
            st.rerun()  # Closes dialog and resumes page
        else:
            st.error(result["error"])
```

### Pattern 3: Background Task Polling with st.fragment

**What:** Use `st.fragment(run_every="2s")` to poll `TaskManager.get_status()` without triggering a full-page rerun. The fragment shows a progress bar and status text that auto-updates.
**When to use:** Any page that submits work to TaskManager (omics pipeline, evidence gathering, reasoning).

```python
@st.fragment(run_every="2s")
def task_progress_monitor(task_id: str, task_manager):
    """Auto-refreshing task progress display."""
    status = task_manager.get_status(task_id)
    if status is None:
        st.warning("Task not found.")
        return

    if status.status == TaskStatus.RUNNING:
        st.progress(status.progress, text=f"Running... {status.progress:.0%}")
    elif status.status == TaskStatus.COMPLETED:
        st.success("Task completed!")
        # Store result in session state for page consumption
        st.session_state[f"task_result_{task_id}"] = status.result_json
    elif status.status == TaskStatus.FAILED:
        st.error(f"Task failed: {status.error_message}")
    elif status.status == TaskStatus.PENDING:
        st.info("Task queued...")
```

### Pattern 4: Pre-cached Showcase Scenario Loader

**What:** Load pre-built JSON files containing evidence, scoring, and reasoning results for 6 pharma scenarios. Bypass all live API calls and long computations.
**When to use:** On the projects page, when user selects "Load Showcase Scenario."

```python
# src/pages/components/showcase.py
import json
from pathlib import Path

SCENARIOS_DIR = Path("data/showcase_scenarios")

SHOWCASE_SCENARIOS = {
    "EGFR/NSCLC": {
        "gene_symbol": "EGFR",
        "disease_context": "Non-Small Cell Lung Cancer",
        "tissue_type": "lung",
        "description": "EGFR-targeted therapy in NSCLC -- gold standard target with extensive clinical validation",
    },
    "ESR1/ER+Breast": {
        "gene_symbol": "ESR1",
        "disease_context": "ER-positive Breast Cancer",
        "tissue_type": "tumor",
        "description": "Estrogen receptor in hormone-positive breast cancer",
    },
    "PIK3CA/HR+Breast": {
        "gene_symbol": "PIK3CA",
        "disease_context": "HR-positive Breast Cancer",
        "tissue_type": "tumor",
        "description": "PI3K catalytic subunit alpha -- alpelisib target",
    },
    "GLP1R/Obesity": {
        "gene_symbol": "GLP1R",
        "disease_context": "Obesity",
        "tissue_type": "adipose",
        "description": "GLP-1 receptor -- semaglutide/tirzepatide target",
    },
    "PARP1/BRCA+Breast": {
        "gene_symbol": "PARP1",
        "disease_context": "BRCA-mutant Breast Cancer",
        "tissue_type": "tumor",
        "description": "Poly(ADP-ribose) polymerase -- olaparib target",
    },
    "CD274/Pan-cancer": {
        "gene_symbol": "CD274",
        "disease_context": "Pan-cancer",
        "tissue_type": "tumor",
        "description": "PD-L1 -- checkpoint immunotherapy target",
    },
}

def load_scenario(scenario_name: str) -> dict:
    """Load all pre-cached data for a showcase scenario.

    Returns dict with keys: evidence, reasoning, scoring, pipeline_report
    Each is a serialized dict ready for deserialization by the respective module.
    """
    scenario = SHOWCASE_SCENARIOS[scenario_name]
    gene = scenario["gene_symbol"]
    scenario_dir = SCENARIOS_DIR / gene.lower()

    data = {"scenario": scenario}
    for key in ("evidence", "reasoning", "scoring", "pipeline_report"):
        file_path = scenario_dir / f"{key}.json"
        if file_path.exists():
            with open(file_path) as f:
                data[key] = json.load(f)

    return data
```

### Pattern 5: Session State Namespacing for Workflow Data

**What:** Use structured keys in `st.session_state` to pass data between pages. Namespace by project to support project switching.
**When to use:** Every page that produces or consumes workflow data.

```python
# Key naming convention:
# st.session_state["project_{project_id}_pipeline_result"]   -- omics output
# st.session_state["project_{project_id}_evidence"]          -- evidence output
# st.session_state["project_{project_id}_reasoning"]         -- reasoning output
# st.session_state["project_{project_id}_scorecard"]         -- scoring output
# st.session_state["project_{project_id}_mode"]              -- exploration/compliance
# st.session_state["hitl_{gate_id}_approved"]                -- gate decisions

def get_project_key(key: str) -> str:
    """Build a project-scoped session state key."""
    project_id = st.session_state.get("active_project_id", "none")
    return f"project_{project_id}_{key}"
```

### Anti-Patterns to Avoid

- **Storing service instances in session_state:** Service objects (AuthService, ProjectService, etc.) use threading locks and DB connections. Create fresh instances per page execution. Never pickle/cache them.
- **Using st.rerun() for progress polling:** Causes full-page rerender, loses scroll position, flickers. Use `st.fragment(run_every=...)` instead.
- **Sharing SQLite connections across threads:** Already solved in codebase with per-operation connections, but UI code must continue this pattern.
- **Putting widgets inside st.fragment that affect outer state:** Fragment reruns only execute the fragment function. Widgets that need to trigger full-page reruns must be outside fragments, or use `st.rerun()` (without scope="fragment") explicitly.
- **Using st.cache_data for user-specific data:** `st.cache_data` is global across all sessions. User-specific workflow data belongs in `st.session_state`.
- **Blocking the main thread with long computations:** All pipeline, evidence gathering, and reasoning calls must go through `TaskManager.submit()` to run in background threads.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Modal overlays for HITL approval | Custom HTML modal with JavaScript | `@st.dialog(dismissible=False)` | Built-in Streamlit dialog handles z-index, focus trap, accessibility. Non-dismissible mode ensures compliance gates cannot be bypassed. |
| Progress polling for background tasks | setTimeout/setInterval JavaScript injection | `@st.fragment(run_every="2s")` | Fragment-based polling is native, handles rerun scoping, and avoids WebSocket complexity. |
| Radar chart visualization | Custom D3 or SVG chart | `build_single_radar()` / `build_comparative_radar()` from `src.scoring.comparative` | Already implemented with verdict-based coloring, polygon closure, and normalized dimensions. |
| Evidence dimension bar chart | Custom HTML table | `VisualizationBuilder.build_evidence_bar()` from `src.reporting.visualizations` | Already implemented with stacked bars, data coverage annotations, and brand colors. |
| Password re-authentication | Custom hash verification | `ElectronicSignature.sign()` from `src.compliance.electronic_signature` | Already implements bcrypt verification, SHA-256 payload hashing, and audit trail recording. |
| Audit trail display with hash verification | Custom query builder | `AuditTrail.get_records()` + `AuditTrail.verify_chain()` | Already implements filtered queries and full chain verification with tamper detection. |
| UMAP/volcano/heatmap plots | Matplotlib recreations | `bioorchestrator_real/utils/plotting.py` functions | Production-quality Plotly figures already exist. Just pass data and render with `st.plotly_chart`. |
| Scenario data generation | Manual JSON editing | Script that calls existing services and serializes results | Use `EvidenceAggregator.gather()`, `ScoringFramework.score_target()`, etc. with real API data, then cache the JSON output. |

**Key insight:** Phase 7 is an integration phase, not a feature-building phase. Every piece of functionality the UI displays already exists as a Python API. The job is to wire backend service calls to Streamlit widgets and manage the workflow state machine across pages.

## Common Pitfalls

### Pitfall 1: Session State Lost on Navigation
**What goes wrong:** User navigates to a different page using markdown links or browser URL bar, which creates a new session and clears all session state.
**Why it happens:** Streamlit only preserves session state when navigation happens through `st.navigation`, `st.switch_page`, or `st.page_link`. Direct URL navigation resets the session.
**How to avoid:** Never use `st.markdown("[Go to page](url)")` for navigation. Use `st.page_link("src/pages/evidence.py", label="Continue to Evidence")` for in-app navigation. Store critical workflow data in both session state (for speed) and SQLite (for durability) so it can be recovered.
**Warning signs:** Users report losing their analysis when clicking browser back button.

### Pitfall 2: Full-Page Rerun During Background Task Polling
**What goes wrong:** Using `st.rerun()` or `time.sleep()` loops to poll task status causes the entire page to re-execute, leading to flickering, scroll position loss, and re-instantiation of all widgets.
**Why it happens:** Streamlit's execution model reruns the entire script on every interaction or rerun call.
**How to avoid:** Use `@st.fragment(run_every="2s")` to isolate the polling section. Only the fragment function re-executes, leaving the rest of the page stable.
**Warning signs:** Page flickers every 2 seconds, scroll jumps to top, widget state resets.

### Pitfall 3: Widget Key Collisions Across Pages
**What goes wrong:** Two different pages use the same widget key (e.g., `key="submit_button"`), causing `DuplicateWidgetID` errors when Streamlit's widget registry encounters them.
**Why it happens:** All pages share the same session state namespace. Widget keys must be globally unique across all pages.
**How to avoid:** Prefix all widget keys with the page name: `key="omics_submit_button"`, `key="evidence_approve_gate"`. For dynamic widgets in loops, include the iteration variable: `key=f"evidence_source_{source_name}"`.
**Warning signs:** `DuplicateWidgetID` error in Streamlit console.

### Pitfall 4: st.dialog Decorated Functions Cannot Be Called Conditionally
**What goes wrong:** Trying to call `@st.dialog` function inside an `if st.button()` block works but the dialog disappears on rerun because the button state resets.
**Why it happens:** When the dialog calls `st.rerun()`, the outer button is no longer pressed, so the condition is False and the dialog function is not called.
**How to avoid:** Use session state to track whether the dialog should be open: set a flag in session state when the button is clicked, call the dialog function based on the flag (not the button), and clear the flag inside the dialog after `st.rerun()`.
**Warning signs:** Dialog opens briefly then immediately disappears.

### Pitfall 5: Plotly Chart Width Deprecation
**What goes wrong:** Using `use_container_width=True` in `st.plotly_chart()` triggers deprecation warnings.
**Why it happens:** As of late 2025, `use_container_width` is deprecated in favor of `width='stretch'`.
**How to avoid:** Use `st.plotly_chart(fig, width='stretch')` instead. If targeting older Streamlit versions, check with `hasattr(st, 'version')` and fall back.
**Warning signs:** Yellow deprecation warning in the app.

### Pitfall 6: Showcase Scenario Data Staleness
**What goes wrong:** Pre-cached scenario JSON files contain evidence/scoring data that doesn't match the current codebase's model schemas (e.g., new fields added, renamed fields).
**Why it happens:** Backend models evolve across phases but cached JSON files are not regenerated.
**How to avoid:** Build a `generate_showcase_data.py` script that programmatically creates all 6 scenarios using the actual service APIs. Run it as a build step whenever models change. Include a schema version in the cached JSON.
**Warning signs:** Pydantic validation errors when deserializing cached scenario data.

### Pitfall 7: Compliance Mode E-Signature Blocking Does Not Truly Block
**What goes wrong:** In compliance mode, the HITL gate calls `st.stop()` to block page progression, but the user can still navigate to downstream pages via the sidebar navigation menu.
**Why it happens:** `st.stop()` only stops rendering the current page. The navigation menu is rendered by `st.navigation` in app.py, not by the page.
**How to avoid:** Check gate approval status at the TOP of each downstream page. If upstream gates for the project are not approved, display a warning and call `st.stop()`. The gate approval check should verify the session state flags set by the HITL gate component.
**Warning signs:** User skips evidence review gate by clicking "Scorecard" in sidebar.

### Pitfall 8: TaskManager Thread Safety in Streamlit
**What goes wrong:** Multiple Streamlit sessions submit tasks to the same `TaskManager` singleton, causing thread pool exhaustion or DB write conflicts.
**Why it happens:** Streamlit reruns create new TaskManager instances per session, each with its own ThreadPoolExecutor, but they all write to the same SQLite DB.
**How to avoid:** Use `@st.cache_resource` to share a single TaskManager instance across all sessions. Its `_write_lock` and per-operation connections already handle thread safety. Set `max_workers=2` (already the default) to limit concurrent background tasks.
**Warning signs:** "database is locked" errors under concurrent use.

## Code Examples

### Example 1: Enhanced Projects Page with Mode Toggle and Scenario Selector

```python
# src/pages/projects.py (enhanced)

import streamlit as st
from src.project.service import ProjectService
from src.pages.components.showcase import SHOWCASE_SCENARIOS, load_scenario

if "user" not in st.session_state:
    st.warning("Please log in to access projects.")
    st.stop()

user = st.session_state["user"]
ps = ProjectService()

st.title("Projects")

# ── Create Project ──────────────────────────────────────────
with st.expander("Create New Project", expanded=True):
    with st.form("create_project_form"):
        proj_name = st.text_input("Project Name")
        proj_desc = st.text_area("Description (optional)")
        mode = st.radio(
            "Analysis Mode",
            options=["exploration", "compliance"],
            format_func=lambda x: {
                "exploration": "Exploration -- HITL gates auto-approve",
                "compliance": "Compliance -- HITL gates require e-signature",
            }[x],
            help="Exploration mode auto-approves HITL gates for rapid iteration. "
                 "Compliance mode requires electronic signatures at every gate.",
        )
        create_submitted = st.form_submit_button("Create Project", use_container_width=True)

    if create_submitted and proj_name:
        project = ps.create(
            name=proj_name,
            description=proj_desc or None,
            created_by=user["user_id"],
            project_config={"mode": mode},
        )
        st.session_state["active_project_id"] = project.project_id
        st.session_state["project_config"] = {"mode": mode}
        st.success(f"Project '{project.name}' created.")
        st.rerun()

# ── Showcase Scenarios ──────────────────────────────────────
st.divider()
st.subheader("Showcase Scenarios")
st.caption("Pre-loaded pharma scenarios with cached evidence. No live API calls required.")

cols = st.columns(3)
for i, (name, scenario) in enumerate(SHOWCASE_SCENARIOS.items()):
    with cols[i % 3]:
        with st.container(border=True):
            st.markdown(f"**{name}**")
            st.caption(scenario["description"])
            if st.button("Load", key=f"load_scenario_{name}", use_container_width=True):
                data = load_scenario(name)
                # Create project with pre-loaded data
                project = ps.create(
                    name=f"Showcase: {name}",
                    description=scenario["description"],
                    created_by=user["user_id"],
                    project_config={"mode": "exploration", "showcase": name},
                )
                pid = project.project_id
                st.session_state["active_project_id"] = pid
                st.session_state["project_config"] = {"mode": "exploration", "showcase": name}
                # Pre-populate all workflow data
                st.session_state[f"project_{pid}_evidence"] = data.get("evidence")
                st.session_state[f"project_{pid}_reasoning"] = data.get("reasoning")
                st.session_state[f"project_{pid}_scorecard"] = data.get("scoring")
                st.session_state[f"project_{pid}_pipeline_result"] = data.get("pipeline_report")
                st.rerun()
```

### Example 2: Evidence Explorer Page with HITL Gates

```python
# src/pages/evidence.py (structure)

import streamlit as st
from src.evidence import EvidenceAggregator, gather_evidence
from src.pages.components.hitl_gate import hitl_gate
from src.pages.components.styles import metric_card

if "user" not in st.session_state:
    st.warning("Please log in.")
    st.stop()

pid = st.session_state.get("active_project_id")
if not pid:
    st.warning("Please select a project first.")
    st.stop()

st.title("Evidence Explorer")

# Check if evidence already loaded (from showcase or prior run)
evidence_key = f"project_{pid}_evidence"
evidence_data = st.session_state.get(evidence_key)

if evidence_data is None:
    # Show evidence gathering form
    gene_symbol = st.text_input("Gene Symbol", value="EGFR")
    disease = st.text_input("Disease Context (optional)")

    if st.button("Gather Evidence", type="primary"):
        with st.spinner("Fetching evidence from 6 sources..."):
            evidence = gather_evidence(gene_symbol, disease or None)
            st.session_state[evidence_key] = _serialize_evidence(evidence)
            st.rerun()
else:
    # Display evidence results
    _display_evidence_results(evidence_data)

    # HITL Gate 1: Data Quality Review
    hitl_gate(
        gate_id=f"{pid}_evidence_quality",
        gate_title="Evidence Data Quality Review",
        module="evidence",
        description="Review source availability and data completeness before proceeding.",
        data_summary={
            "Sources Available": f"{evidence_data.get('sources_available', 0)}/6",
            "Sources Failed": str(evidence_data.get('sources_failed', 0)),
        },
    )

    # HITL Gate 2: Source Relevance
    hitl_gate(
        gate_id=f"{pid}_evidence_relevance",
        gate_title="Evidence Relevance Assessment",
        module="evidence",
        description="Confirm that retrieved evidence is relevant to the target assessment.",
        data_summary={
            "Gene": evidence_data.get("gene", {}).get("canonical_symbol", "Unknown"),
            "Disease Context": evidence_data.get("disease_context", "N/A"),
        },
    )

    # HITL Gate 3: Evidence Sufficiency
    hitl_gate(
        gate_id=f"{pid}_evidence_sufficiency",
        gate_title="Evidence Sufficiency for Scoring",
        module="evidence",
        description="Confirm sufficient evidence quality to proceed to AI analysis.",
        data_summary={"Recommendation": "Proceed to AI Insights"},
    )

    st.page_link("src/pages/insights.py", label="Continue to AI Insights", icon=":material/arrow_forward:")
```

### Example 3: Design System CSS Module

```python
# src/pages/components/styles.py

import streamlit as st

DESIGN_SYSTEM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --blue: #0071e3;
    --dark: #1d1d1f;
    --text2: #6e6e73;
    --bg: #ffffff;
    --bg2: #f5f5f7;
    --bg3: #e8e8ed;
    --green: #1a7a35;
    --orange: #c96800;
    --red: #c0392b;
    --purple: #7a28c6;
    --space-xs: 4px;
    --space-sm: 8px;
    --space-md: 16px;
    --space-lg: 24px;
    --space-xl: 32px;
}

.block-container { max-width: 1100px; padding-top: 1rem; }

html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Inter', system-ui, sans-serif;
    color: var(--dark);
    line-height: 1.7;
}

/* Dark sidebar */
section[data-testid="stSidebar"] { background: var(--dark) !important; }
section[data-testid="stSidebar"] * { color: rgba(255,255,255,0.7) !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: white !important; }

/* Metric cards */
.metric-card {
    background: var(--bg);
    border: 1px solid var(--bg3);
    border-radius: 12px;
    padding: 20px var(--space-md);
    text-align: center;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}
.metric-val {
    font-family: 'IBM Plex Mono', 'SF Mono', monospace;
    font-size: 1.75rem;
    font-weight: 600;
    color: var(--blue);
}
.metric-label {
    font-size: 0.72rem;
    color: var(--text2);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 6px;
}

/* Insight/alert/warning panels */
.insight-panel {
    background: rgba(0,113,227,0.04);
    border-left: 4px solid var(--blue);
    border-radius: 0 12px 12px 0;
    padding: var(--space-md) 20px;
    margin: var(--space-md) 0;
}
.alert-panel {
    background: rgba(192,57,43,0.04);
    border-left: 4px solid var(--red);
    border-radius: 0 12px 12px 0;
    padding: var(--space-md) 20px;
    margin: var(--space-md) 0;
}
.warning-panel {
    background: rgba(201,104,0,0.04);
    border-left: 4px solid var(--orange);
    border-radius: 0 12px 12px 0;
    padding: var(--space-md) 20px;
    margin: var(--space-md) 0;
}

/* Verdict badges */
.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; }
.badge-go { background: var(--green); color: white; }
.badge-conditional { background: var(--orange); color: white; }
.badge-nogo { background: var(--red); color: white; }

/* Button enhancements */
.stMainBlockContainer button[kind="primary"] {
    border-radius: 8px !important;
    font-weight: 600 !important;
}
.stMainBlockContainer button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(0,113,227,0.25) !important;
}

/* Expander styling */
details[data-testid="stExpander"] {
    border: 1px solid var(--bg3) !important;
    border-radius: 12px !important;
}

/* Print styles */
@media print {
    section[data-testid="stSidebar"] { display: none !important; }
    .block-container { max-width: 100% !important; }
    button { display: none !important; }
}
</style>
"""

def inject_design_system():
    """Inject the design system CSS. Call once in app.py."""
    st.markdown(DESIGN_SYSTEM_CSS, unsafe_allow_html=True)


def metric_card(label: str, value: str) -> str:
    """Return HTML for a styled metric card."""
    return f"""
    <div class="metric-card">
        <div class="metric-val">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """


def verdict_badge(level: str) -> str:
    """Return HTML for a verdict badge."""
    css_class = {
        "GO": "badge-go",
        "CONDITIONAL": "badge-conditional",
        "NO-GO": "badge-nogo",
    }.get(level, "badge-conditional")
    return f'<span class="badge {css_class}">{level}</span>'
```

### Example 4: Scorecard Page with Radar Chart

```python
# src/pages/scorecard.py (structure)

import streamlit as st
from src.scoring import ScoringFramework, build_single_radar, build_comparative_radar
from src.reporting.visualizations import VisualizationBuilder

if "user" not in st.session_state:
    st.warning("Please log in.")
    st.stop()

pid = st.session_state.get("active_project_id")
scorecard_data = st.session_state.get(f"project_{pid}_scorecard")

if scorecard_data is None:
    st.warning("Complete evidence gathering and AI analysis first.")
    st.stop()

st.title("Target Scorecard")

# Reconstruct ScorecardResult from serialized dict
from src.scoring.models import ScorecardResult
scorecard = ScorecardResult(**scorecard_data)

# Verdict display
from src.pages.components.styles import verdict_badge
st.markdown(
    f"## {scorecard.gene_symbol} -- {verdict_badge(scorecard.verdict.level.value)}",
    unsafe_allow_html=True,
)

# Composite score
st.metric("Composite Score", f"{scorecard.composite.score:.1f}/100")

# Radar chart
col1, col2 = st.columns(2)
with col1:
    fig = build_single_radar(scorecard)
    st.plotly_chart(fig, width="stretch")
with col2:
    # Evidence dimensions bar chart
    from src.reporting.models import DossierData, DossierConfig
    dossier_data = DossierData(
        gene_symbol=scorecard.gene_symbol,
        scorecard=scorecard.model_dump(),
        evidence=st.session_state.get(f"project_{pid}_evidence", {}),
    )
    viz = VisualizationBuilder(dossier_data)
    bar_fig = viz.build_evidence_bar()
    if bar_fig:
        st.plotly_chart(bar_fig, width="stretch")

# Dimension breakdown
st.subheader("Dimension Scores")
for dim in scorecard.composite.dimension_scores:
    with st.expander(f"{dim.name.replace('_', ' ').title()} -- {dim.score:.1f}/{dim.max_score:.0f}"):
        st.progress(dim.score / dim.max_score if dim.max_score > 0 else 0)
        st.caption(f"Data coverage: {dim.data_coverage:.0%}")
        if dim.sub_scores:
            for sub in dim.sub_scores:
                st.write(f"- **{sub.name}**: {sub.value:.1f}/{sub.max_value:.0f} -- {sub.description}")

# Export options
st.divider()
st.subheader("Export")
col1, col2 = st.columns(2)
with col1:
    if st.button("Generate HTML Dossier", type="primary"):
        # Use HTMLDossierRenderer
        pass
with col2:
    if st.button("Generate PDF Dossier"):
        # Use PDFDossierRenderer
        pass
```

### Example 5: TaskManager as Cached Resource

```python
# Singleton TaskManager shared across all Streamlit sessions
@st.cache_resource
def get_task_manager():
    """Return a shared TaskManager instance (thread-safe singleton)."""
    from src.execution.task_manager import TaskManager
    return TaskManager(max_workers=2)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `use_container_width=True` in st.plotly_chart | `width='stretch'` parameter | Late 2025 | Former is deprecated, may show warnings |
| `st.experimental_dialog` | `@st.dialog()` | Streamlit 1.37 (mid-2024) | Stable API, supports dismissible parameter |
| `st.experimental_fragment` | `@st.fragment()` | Streamlit 1.37 (mid-2024) | Stable API with run_every parameter |
| Pages directory convention | `st.navigation` / `st.Page` | Streamlit 1.36 (2024) | Explicit page control, section grouping, position parameter |
| Global `st.cache` | `st.cache_data` + `st.cache_resource` | Streamlit 1.18 (2023) | cache_data for serializable data, cache_resource for connections/singletons |

**Deprecated/outdated:**
- `st.experimental_dialog`: Use `@st.dialog()` instead
- `st.experimental_fragment`: Use `@st.fragment()` instead
- `use_container_width` in chart functions: Use `width='stretch'` instead
- Pages directory convention: Use `st.navigation`/`st.Page` for explicit control (already adopted in Phase 1)

## Open Questions

1. **Showcase Scenario Data Generation**
   - What we know: The 6 scenarios are defined (EGFR/NSCLC, ESR1/ER+Breast, PIK3CA/HR+Breast, GLP1R/Obesity, PARP1/BRCA+Breast, CD274/Pan-cancer). The backend APIs exist to gather evidence and score targets.
   - What's unclear: Whether to generate scenario data with real API calls (requires network, may hit rate limits) or to hand-craft realistic synthetic JSON (more work but deterministic). Also unclear if the "under 5 minutes" requirement includes the initial data loading or only the UI walkthrough.
   - Recommendation: Generate with real APIs once, cache to JSON, commit the JSON files. Build a `scripts/generate_showcase_data.py` that can be re-run when models change. The 5-minute requirement should cover the full UI walkthrough from scenario load to scorecard view, which is trivially achievable with pre-cached data.

2. **Omics Pipeline Page -- Real vs Mock Data**
   - What we know: The omics pipeline (`src/pipeline/run_pipeline`) requires actual h5ad input files and takes minutes to run.
   - What's unclear: Whether showcase scenarios should include real pipeline output data or skip the omics page entirely.
   - Recommendation: For showcase scenarios, pre-cache a minimal pipeline_report.json with UMAP coordinates, DE results, and QC metrics. The omics page should detect showcase mode and display cached results instead of running the pipeline.

3. **HITL Gate Numbering Across Modules**
   - What we know: 9 gates total -- 3 per module (Omics, Evidence, Reasoning). The gate IDs need to be unique and ordered.
   - What's unclear: Exact placement of each gate within each module.
   - Recommendation: Define gates as: Omics (QC Review, Annotation Review, DE Review), Evidence (Data Quality, Source Relevance, Evidence Sufficiency), Reasoning (Hypothesis Review, Synthesis Review, Confidence Review). Each gate checks the output of the preceding analysis step.

## Sources

### Primary (HIGH confidence)
- `src/app.py` -- Existing st.navigation/st.Page routing pattern (Phase 1 implementation)
- `src/pages/login.py` -- Existing auth pattern with session_state
- `src/pages/projects.py` -- Existing project CRUD with auth guard pattern
- `src/compliance/audit_trail.py` -- Hash-chain audit trail API
- `src/compliance/electronic_signature.py` -- E-signature with re-authentication
- `src/execution/task_manager.py` -- Background task execution with SQLite persistence
- `src/evidence/__init__.py` -- `gather_evidence()` public API
- `src/reasoning/engine.py` -- `ReasoningEngine.reason()` / `reason_all_modes()` API
- `src/scoring/framework.py` -- `ScoringFramework.score_target()` API
- `src/scoring/comparative.py` -- `build_single_radar()` / `build_comparative_radar()` API
- `src/reporting/visualizations.py` -- `VisualizationBuilder.build_all()` API
- `src/reporting/data_collector.py` -- `collect_dossier_data()` API
- `src/reporting/html_renderer.py` -- `HTMLDossierRenderer.render()` API
- `bioorchestrator_real/app.py` -- Reference CSS design system, complete with metric cards, panels, badges, sidebar styling

### Secondary (MEDIUM confidence)
- [Streamlit st.navigation docs](https://docs.streamlit.io/develop/api-reference/navigation/st.navigation) -- API parameters, section grouping, position parameter
- [Streamlit st.dialog docs](https://docs.streamlit.io/develop/api-reference/execution-flow/st.dialog) -- dismissible parameter, form-in-dialog pattern
- [Streamlit st.fragment docs](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment) -- run_every parameter, scope parameter for st.rerun
- [Streamlit 2026 release notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026) -- st.dialog icon parameter, width='stretch' deprecation of use_container_width
- [Streamlit multipage concepts](https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation) -- Dynamic navigation, session state preservation across pages

### Tertiary (LOW confidence)
- None -- all critical claims verified with primary or secondary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in project, APIs verified by reading source code
- Architecture: HIGH -- patterns derived from existing codebase (app.py, login.py, projects.py) and official Streamlit documentation
- Pitfalls: HIGH -- derived from Streamlit's documented behavior and known session state mechanics
- HITL gate design: MEDIUM -- pattern is well-structured but specific gate placements within each module may need adjustment during implementation
- Showcase scenarios: MEDIUM -- the scenario list is defined in requirements but the data generation approach needs validation

**Research date:** 2026-05-12
**Valid until:** 2026-06-12 (Streamlit releases monthly; design system is stable)
