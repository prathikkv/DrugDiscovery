"""Evidence Explorer page -- evidence gathering from 6 sources and 3 HITL gates.

Gathers evidence via EvidenceAggregator or loads pre-cached showcase data.
Displays per-source results with confidence metrics and gates progression
through 3 HITL checkpoints: Data Quality, Source Relevance, Evidence Sufficiency.
"""

import streamlit as st

from src.pages.components.hitl_gate import hitl_gate
from src.pages.components.styles import metric_card, alert_panel, insight_panel


def _serialize_evidence(agg_evidence) -> dict:
    """Serialize an AggregatedEvidence object to a session-state-safe dict."""
    gene = agg_evidence.gene
    results_dict = {}
    for source_name, result in agg_evidence.results.items():
        results_dict[source_name] = {
            "confidence": result.confidence,
            "data": result.data,
            "error": result.error,
            "is_fallback": result.is_fallback,
        }

    return {
        "gene": {
            "canonical_symbol": gene.canonical_symbol,
            "ensembl_id": gene.ensembl_id,
            "uniprot_accession": gene.uniprot_accession,
            "query_symbol": gene.query_symbol,
        },
        "disease_context": agg_evidence.disease_context,
        "results": results_dict,
        "sources_available": agg_evidence.sources_available,
        "sources_failed": agg_evidence.sources_failed,
    }


def _display_source_details(source_name: str, source_data: dict):
    """Display details for a single evidence source in an expander."""
    confidence = source_data.get("confidence", 0.0)
    data = source_data.get("data")
    error = source_data.get("error")
    is_fallback = source_data.get("is_fallback", False)

    # Confidence badge color
    if confidence >= 0.8:
        badge_color = "green"
    elif confidence >= 0.5:
        badge_color = "orange"
    else:
        badge_color = "red"

    label = f"{source_name} (confidence: {confidence:.1f})"
    if is_fallback:
        label += " [CACHED]"

    with st.expander(label, expanded=(confidence > 0)):
        if error:
            st.markdown(alert_panel(f"<strong>Error:</strong> {error}"), unsafe_allow_html=True)

        if data is None:
            st.caption("No data available from this source.")
            return

        # Source-specific display
        name_lower = source_name.lower()

        if "opentargets" in name_lower:
            associations = data.get("associations", [])
            st.markdown(f"**Disease associations:** {len(associations)}")
            if associations:
                for assoc in associations[:5]:
                    disease = assoc.get("disease_name", assoc.get("disease_id", "Unknown"))
                    score = assoc.get("score", 0)
                    relevant = assoc.get("is_relevant", False)
                    tag = " **(relevant)**" if relevant else ""
                    st.markdown(f"- {disease}: {score:.3f}{tag}")
                if len(associations) > 5:
                    st.caption(f"... and {len(associations) - 5} more")

        elif "dgidb" in name_lower:
            interactions = data.get("interactions", [])
            count = data.get("interaction_count", len(interactions))
            st.markdown(f"**Drug interactions:** {count}")
            if interactions:
                drug_names = [i.get("drug_name", "Unknown") for i in interactions[:10]]
                st.markdown("**Drugs:** " + ", ".join(drug_names))

        elif "pubmed" in name_lower:
            papers = data.get("papers", [])
            total = data.get("total_count", len(papers))
            st.markdown(f"**Publications:** {total}")
            if papers:
                for paper in papers[:3]:
                    title = paper.get("title", "Untitled")
                    year = paper.get("year", "")
                    st.markdown(f"- {title} ({year})")
                if len(papers) > 3:
                    st.caption(f"... and {len(papers) - 3} more")

        elif "clinicaltrials" in name_lower:
            trials = data.get("trials", [])
            total = data.get("total_count", len(trials))
            st.markdown(f"**Clinical trials:** {total}")
            if trials:
                for trial in trials[:5]:
                    title = trial.get("brief_title", trial.get("title", "Untitled"))
                    phase = trial.get("phase", "N/A")
                    status = trial.get("status", "N/A")
                    st.markdown(f"- {title} (Phase: {phase}, Status: {status})")

        elif "uniprot" in name_lower:
            protein_name = data.get("protein_name", "N/A")
            function_text = data.get("function", data.get("function_summary", ""))
            st.markdown(f"**Protein:** {protein_name}")
            if function_text:
                st.markdown(insight_panel(f"<strong>Function:</strong> {function_text[:500]}"), unsafe_allow_html=True)

        elif "chembl" in name_lower:
            compounds = data.get("compounds", [])
            compound_count = data.get("compound_count", len(compounds))
            target_info = data.get("target_name", data.get("target_pref_name", ""))
            st.markdown(f"**Compounds:** {compound_count}")
            if target_info:
                st.markdown(f"**Target:** {target_info}")
            if compounds:
                for comp in compounds[:5]:
                    name = comp.get("molecule_name", comp.get("pref_name", "Unknown"))
                    st.markdown(f"- {name}")

        else:
            # Generic display
            st.json(data)


def _page():
    """Evidence Explorer page entry point."""
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
    if mode == "compliance" and not st.session_state.get(f"hitl_{pid}_omics_de_approved"):
        st.warning("Complete omics review first.")
        st.stop()
        return

    # Session state key
    evidence_key = f"project_{pid}_evidence"

    # Page header
    st.title("Evidence Explorer")
    st.caption(
        "Gather and review evidence from 6 sources: OpenTargets, DGIdb, "
        "PubMed, ClinicalTrials, UniProt, and ChEMBL."
    )

    # Check for existing evidence data (from showcase or prior run)
    evidence_data = st.session_state.get(evidence_key)

    # ── Evidence Gathering Form (only if no data) ───────────────────
    if evidence_data is None:
        with st.form("evidence_gather_form"):
            st.subheader("Evidence Query")

            # Default gene from project config
            default_gene = st.session_state.get("project_config", {}).get("gene_symbol", "")

            gene_symbol = st.text_input(
                "Gene Symbol",
                value=default_gene,
                placeholder="EGFR",
                key="evidence_gene_symbol",
            )
            disease_context = st.text_input(
                "Disease Context (optional)",
                placeholder="Non-Small Cell Lung Cancer",
                key="evidence_disease_context",
            )

            submitted = st.form_submit_button("Gather Evidence", type="primary")

        if submitted and gene_symbol:
            with st.spinner("Fetching evidence from 6 sources..."):
                try:
                    from src.evidence import gather_evidence
                    agg_evidence = gather_evidence(gene_symbol, disease_context or None)
                    st.session_state[evidence_key] = _serialize_evidence(agg_evidence)
                    st.rerun()
                except Exception as e:
                    st.error(f"Evidence gathering failed: {e}")
        elif submitted:
            st.warning("Please enter a gene symbol.")

        return

    # ── Evidence Results Display ────────────────────────────────────
    gene_info = evidence_data.get("gene", {})
    gene_symbol = gene_info.get("canonical_symbol", gene_info.get("query_symbol", "N/A"))
    disease_ctx = evidence_data.get("disease_context", "N/A")
    results = evidence_data.get("results", {})

    # Count available sources
    available = sum(1 for r in results.values() if r.get("confidence", 0) > 0)
    total_sources = len(results) or 6
    errors = sum(1 for r in results.values() if r.get("error"))
    total_confidence = sum(r.get("confidence", 0) for r in results.values())

    # Summary metrics
    cols = st.columns(4)
    with cols[0]:
        st.markdown(
            metric_card("Sources Available", f"{available}/{total_sources}"),
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            metric_card("Total Confidence", f"{total_confidence:.1f}"),
            unsafe_allow_html=True,
        )
    with cols[2]:
        st.markdown(
            metric_card("Gene Symbol", gene_symbol),
            unsafe_allow_html=True,
        )
    with cols[3]:
        st.markdown(
            metric_card("Disease Context", str(disease_ctx) if disease_ctx else "General"),
            unsafe_allow_html=True,
        )

    # Per-source details
    st.markdown("---")
    st.subheader("Evidence by Source")

    for source_name, source_data in results.items():
        _display_source_details(source_name, source_data)

    # ── HITL Gates ──────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Quality Gates")

    # Gate 1: Data Quality
    hitl_gate(
        gate_id=f"{pid}_evidence_quality",
        gate_title="Evidence Data Quality Review",
        module="evidence",
        description="Review source availability and data completeness.",
        data_summary={
            "Sources Available": f"{available}/{total_sources}",
            "Sources with Errors": str(errors),
        },
    )

    # Gate 2: Relevance Assessment
    hitl_gate(
        gate_id=f"{pid}_evidence_relevance",
        gate_title="Evidence Relevance Assessment",
        module="evidence",
        description="Confirm retrieved evidence is relevant to target assessment.",
        data_summary={
            "Gene": gene_symbol,
            "Disease": str(disease_ctx) if disease_ctx else "General",
        },
    )

    # Gate 3: Evidence Sufficiency
    hitl_gate(
        gate_id=f"{pid}_evidence_sufficiency",
        gate_title="Evidence Sufficiency for Scoring",
        module="evidence",
        description="Confirm sufficient evidence to proceed to AI analysis.",
        data_summary={
            "Recommendation": "Proceed to AI Insights",
        },
    )

    # ── Navigation ──────────────────────────────────────────────────
    st.markdown("---")
    st.page_link(
        "src/pages/insights.py",
        label="Continue to AI Insights",
        icon=":material/arrow_forward:",
    )


_page()
