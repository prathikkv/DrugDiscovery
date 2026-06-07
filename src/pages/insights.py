"""AI Insights page -- reasoning across 5 modes with 3 HITL gates.

Triggers reasoning via ReasoningEngine through TaskManager for background
execution. Displays claims with confidence scores and source citations
in a tabbed view (Hypothesis, Synthesis, Contradiction, Gap, Confidence).
Gates progression through 3 HITL checkpoints.
"""

import json
import uuid

import streamlit as st

from src.pages.components.auth_guard import require_auth
from src.pages.components import get_task_manager

require_auth()
from src.pages.components.hitl_gate import hitl_gate
from src.pages.components.styles import metric_card, insight_panel


# ── Reasoning Runner ────────────────────────────────────────────────

def _run_reasoning(gene_symbol, disease_context, evidence_data):
    """Execute reasoning across all 5 modes.

    Args:
        gene_symbol: Target gene to analyze.
        disease_context: Disease/indication context.
        evidence_data: Serialized evidence dict from session state, or None.

    Returns:
        Dict mapping mode_name -> serialized result dict.
    """
    try:
        from src.reasoning.engine import ReasoningEngine
        from src.reasoning.models import ReasoningMode

        engine = ReasoningEngine()

        # Attempt to reconstruct AggregatedEvidence if we have data
        evidence_obj = None
        if evidence_data and isinstance(evidence_data, dict):
            try:
                from src.evidence.models import AggregatedEvidence, GeneIdentifiers, EvidenceResult
                gene_info = evidence_data.get("gene", {})
                gene = GeneIdentifiers(
                    canonical_symbol=gene_info.get("canonical_symbol", gene_symbol),
                    ensembl_id=gene_info.get("ensembl_id"),
                    uniprot_accession=gene_info.get("uniprot_accession"),
                    query_symbol=gene_info.get("query_symbol", gene_symbol),
                )
                results = {}
                for src_name, src_data in evidence_data.get("results", {}).items():
                    results[src_name] = EvidenceResult(
                        source_name=src_name,
                        confidence=src_data.get("confidence", 0.0),
                        data=src_data.get("data"),
                        error=src_data.get("error"),
                        is_fallback=src_data.get("is_fallback", False),
                    )
                available = sum(1 for r in results.values() if r.confidence > 0)
                failed = sum(1 for r in results.values() if r.error)
                evidence_obj = AggregatedEvidence(
                    gene=gene,
                    disease_context=disease_context,
                    results=results,
                    sources_available=available,
                    sources_failed=failed,
                )
            except Exception:
                pass  # Use None for evidence if reconstruction fails

        all_results = engine.reason_all_modes(
            gene_symbol=gene_symbol,
            disease_context=disease_context,
            evidence=evidence_obj,
        )

        # Serialize results for session state (Pydantic models -> dicts)
        serialized = {}
        for mode, result in all_results.items():
            serialized[mode.value] = result.model_dump(mode="json")

        return serialized

    except Exception as e:
        return {"error": str(e)}


def _display_reasoning_results(pid, reasoning_data):
    """Display reasoning results in tabbed view with HITL gates."""
    # Mode display names
    mode_names = {
        "hypothesis": "Hypothesis",
        "synthesis": "Synthesis",
        "contradiction": "Contradiction",
        "gap": "Gap Analysis",
        "confidence": "Confidence",
    }

    # Collect stats for gates
    all_claims = []
    all_sources = set()
    modes_completed = 0
    total_hallucination_issues = 0
    confidence_values = []

    for mode_key, mode_label in mode_names.items():
        result = reasoning_data.get(mode_key, {})
        if result and not result.get("error"):
            modes_completed += 1
            claims = result.get("claims", [])
            all_claims.extend(claims)
            for claim in claims:
                all_sources.update(claim.get("sources", []))
                if claim.get("confidence") is not None:
                    confidence_values.append(claim["confidence"])
            total_hallucination_issues += len(result.get("hallucination_issues", []))

    avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0

    # Summary metrics
    cols = st.columns(4)
    with cols[0]:
        st.markdown(
            metric_card("Modes Analyzed", f"{modes_completed}/5"),
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            metric_card("Total Claims", str(len(all_claims))),
            unsafe_allow_html=True,
        )
    with cols[2]:
        st.markdown(
            metric_card("Avg Confidence", f"{avg_confidence:.0%}"),
            unsafe_allow_html=True,
        )
    with cols[3]:
        st.markdown(
            metric_card("Sources Used", str(len(all_sources))),
            unsafe_allow_html=True,
        )

    if total_hallucination_issues > 0:
        st.warning(f"Hallucination checker found {total_hallucination_issues} issue(s) across all modes.")

    # Tabbed view per reasoning mode
    st.markdown("---")
    tabs = st.tabs([mode_names.get(k, k) for k in mode_names.keys()])

    for tab, (mode_key, mode_label) in zip(tabs, mode_names.items()):
        with tab:
            result = reasoning_data.get(mode_key, {})

            if not result:
                st.info(f"No results for {mode_label} mode.")
                continue

            if result.get("error"):
                st.error(f"Mode failed: {result['error']}")
                continue

            # Summary text
            summary = result.get("summary", "")
            if summary:
                st.markdown(insight_panel(f"<strong>Summary:</strong> {summary[:800]}"), unsafe_allow_html=True)

            # Claims list
            claims = result.get("claims", [])
            if claims:
                st.subheader(f"Claims ({len(claims)})")
                for i, claim in enumerate(claims, 1):
                    text = claim.get("text", "")
                    conf = claim.get("confidence", 0.5)
                    sources = claim.get("sources", [])

                    with st.container(border=True):
                        st.markdown(f"**{i}.** {text}")
                        col_conf, col_sources = st.columns([1, 2])
                        with col_conf:
                            st.progress(conf, text=f"Confidence: {conf:.0%}")
                        with col_sources:
                            if sources:
                                source_tags = " ".join(
                                    f"`{s}`" for s in sources
                                )
                                st.markdown(f"Sources: {source_tags}")
            else:
                st.caption("No structured claims parsed for this mode.")

            # Hallucination issues
            hall_issues = result.get("hallucination_issues", [])
            if hall_issues:
                with st.expander(f"Hallucination Issues ({len(hall_issues)})", expanded=False):
                    for issue in hall_issues:
                        issue_type = issue.get("type", "unknown")
                        description = issue.get("description", str(issue))
                        st.markdown(f"- **{issue_type}**: {description}")

    # ── HITL Gates ──────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Quality Gates")

    # Count hypothesis claims specifically
    hyp_result = reasoning_data.get("hypothesis", {})
    hyp_claims = hyp_result.get("claims", []) if hyp_result else []
    hyp_confidences = [c.get("confidence", 0.5) for c in hyp_claims]
    hyp_avg = sum(hyp_confidences) / len(hyp_confidences) if hyp_confidences else 0.0

    # Gate 1: Hypothesis Review
    hitl_gate(
        gate_id=f"{pid}_reasoning_hypothesis",
        gate_title="Hypothesis Review",
        module="reasoning",
        description="Review AI-generated hypotheses for scientific validity.",
        data_summary={
            "Hypotheses": str(len(hyp_claims)),
            "Avg Confidence": f"{hyp_avg:.0%}",
        },
    )

    # Gate 2: Synthesis Review
    syn_result = reasoning_data.get("synthesis", {})
    syn_claims = syn_result.get("claims", []) if syn_result else []
    hitl_gate(
        gate_id=f"{pid}_reasoning_synthesis",
        gate_title="Synthesis Review",
        module="reasoning",
        description="Review cross-source synthesis for accuracy.",
        data_summary={
            "Claims": str(len(syn_claims)),
            "Sources Used": str(len(all_sources)),
        },
    )

    # Gate 3: Confidence Assessment Review
    conf_result = reasoning_data.get("confidence", {})
    conf_claims = conf_result.get("claims", []) if conf_result else []
    conf_confidences = [c.get("confidence", 0.5) for c in conf_claims]
    overall_conf = sum(conf_confidences) / len(conf_confidences) if conf_confidences else 0.0

    hitl_gate(
        gate_id=f"{pid}_reasoning_confidence",
        gate_title="Confidence Assessment Review",
        module="reasoning",
        description="Review confidence assessment before scoring.",
        data_summary={
            "Overall Confidence": f"{overall_conf:.0%}",
            "Modes Analyzed": str(modes_completed),
        },
    )

    # ── Navigation ──────────────────────────────────────────────────
    st.markdown("---")
    st.page_link(
        "src/pages/scorecard.py",
        label="Continue to Scorecard",
        icon=":material/arrow_forward:",
    )


def _page():
    """AI Insights page entry point."""
    # Auth guard
    if "user" not in st.session_state:
        st.warning("Please log in to access this page.")
        st.stop()
        return

    if not st.session_state.get("active_project_id"):
        st.warning("Please select a project first.")
        st.stop()
        return

    pid = st.session_state["active_project_id"]

    # Upstream gate guard (compliance mode)
    project_config = st.session_state.get("project_config", {})
    mode = project_config.get("mode", "exploration")
    if mode == "compliance" and not st.session_state.get(f"hitl_{pid}_evidence_sufficiency_approved"):
        st.warning("Complete evidence review first.")
        st.stop()
        return

    # Session state keys
    reasoning_key = f"project_{pid}_reasoning"
    task_id_key = f"project_{pid}_reasoning_task_id"
    evidence_key = f"project_{pid}_evidence"

    # Page header
    st.title("AI Insights")
    st.caption(
        "Run AI reasoning across 5 analysis modes: Hypothesis, Synthesis, "
        "Contradiction, Gap Analysis, and Confidence Assessment."
    )

    # Check for existing reasoning data (from showcase or prior run)
    reasoning_data = st.session_state.get(reasoning_key)

    # ── Reasoning Trigger (only if no data and no active task) ──────
    if reasoning_data is None and not st.session_state.get(task_id_key):
        # Show current evidence summary
        evidence_data = st.session_state.get(evidence_key)
        if evidence_data:
            gene_info = evidence_data.get("gene", {})
            gene_symbol = gene_info.get("canonical_symbol", "Unknown")
            disease_ctx = evidence_data.get("disease_context", "General")
            st.info(f"Evidence loaded for **{gene_symbol}** ({disease_ctx}). Ready for AI analysis.")
        else:
            st.info("No evidence data loaded. AI analysis will proceed with tool-calling only.")
            gene_symbol = st.session_state.get("project_config", {}).get("gene_symbol", "")
            disease_ctx = ""

        col_btn, _ = st.columns([1, 3])
        with col_btn:
            if st.button("Run AI Analysis", type="primary", key="insights_run_btn"):
                # Determine gene and disease from evidence or project config
                if evidence_data:
                    gene_info = evidence_data.get("gene", {})
                    gene_sym = gene_info.get("canonical_symbol", gene_info.get("query_symbol", "EGFR"))
                    dis_ctx = evidence_data.get("disease_context", "")
                else:
                    gene_sym = st.session_state.get("project_config", {}).get("gene_symbol", "EGFR")
                    dis_ctx = st.session_state.get("project_config", {}).get("disease_context", "")

                # Submit reasoning as background task
                tm = get_task_manager()
                task_id = f"reasoning_{pid}_{uuid.uuid4().hex[:8]}"
                tm.submit(
                    task_id,
                    "reasoning",
                    _run_reasoning,
                    gene_sym,
                    dis_ctx,
                    evidence_data,
                    project_id=pid,
                )
                st.session_state[task_id_key] = task_id
                st.rerun()

    # ── Progress Polling ────────────────────────────────────────────
    if st.session_state.get(task_id_key) and not st.session_state.get(reasoning_key):
        active_task_id = st.session_state[task_id_key]

        @st.fragment(run_every=2)
        def _poll_reasoning_progress():
            tm = get_task_manager()
            status = tm.get_status(active_task_id)

            if status is None:
                st.info("Initializing AI analysis...")
                return

            status_val = status.status.value

            if status_val == "PENDING":
                st.info("AI analysis queued...")

            elif status_val == "RUNNING":
                progress_val = status.progress or 0.0
                st.progress(progress_val, text=f"Analyzing... {progress_val:.0%}")

            elif status_val == "COMPLETED":
                st.success("AI analysis complete!")
                if status.result_json:
                    result = json.loads(status.result_json)
                else:
                    result = {"error": "No result data returned"}
                st.session_state[reasoning_key] = result
                if task_id_key in st.session_state:
                    del st.session_state[task_id_key]
                st.rerun()

            elif status_val == "FAILED":
                st.error(f"AI analysis failed: {status.error_message}")

        _poll_reasoning_progress()

    # ── Results Display ─────────────────────────────────────────────
    reasoning_data = st.session_state.get(reasoning_key)
    if reasoning_data is not None:
        if "error" in reasoning_data and len(reasoning_data) == 1:
            st.error(f"Reasoning failed: {reasoning_data['error']}")
        else:
            _display_reasoning_results(pid, reasoning_data)


_page()
