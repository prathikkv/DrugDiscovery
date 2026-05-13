"""Scorecard page -- GO/CONDITIONAL/NO-GO verdict with dimension breakdown and dossier export.

Displays:
- Composite score with verdict badge
- Interactive radar chart via build_single_radar()
- 7-dimension breakdown with expandable sub-scores
- Forced conditional warnings
- HTML and PDF dossier generation and download

Requires an active project with scorecard data (from scoring or showcase).
In compliance mode, upstream reasoning confidence gate must be approved.
"""

import json

import streamlit as st

from src.pages.components.styles import (
    alert_panel,
    metric_card,
    verdict_badge,
    warning_panel,
)


# ── Auth + Project Guard ─────────────────────────────────────────────

if "user" not in st.session_state:
    st.warning("Please log in to access the scorecard.")
    st.stop()

pid = st.session_state.get("active_project_id")
if not pid:
    st.warning("No active project selected. Please select or create a project first.")
    st.stop()

# ── Compliance mode: upstream reasoning confidence gate ──────────────

project_config = st.session_state.get("project_config", {})
mode = project_config.get("mode", "exploration")

if mode == "compliance":
    reasoning_gate_key = f"hitl_{pid}_reasoning_confidence_approved"
    if not st.session_state.get(reasoning_gate_key, False):
        st.warning(
            "Reasoning confidence gate has not been approved. "
            "Please complete the AI Insights review before viewing the scorecard."
        )
        st.stop()


# ── Scorecard Data Loading ───────────────────────────────────────────

scorecard_key = f"project_{pid}_scorecard"
scorecard_data = st.session_state.get(scorecard_key)

if not scorecard_data:
    # Attempt auto-compute from evidence data
    evidence_key = f"project_{pid}_evidence"
    evidence_data = st.session_state.get(evidence_key)
    if evidence_data and isinstance(evidence_data, dict):
        with st.spinner("Computing scorecard from evidence data..."):
            try:
                from src.scoring import ScoringFramework
                from src.evidence.models import AggregatedEvidence, GeneIdentifiers, EvidenceResult

                # Reconstruct AggregatedEvidence from serialized dict
                gene_info = evidence_data.get("gene", {})
                gene = GeneIdentifiers(
                    canonical_symbol=gene_info.get("canonical_symbol", "Unknown"),
                    ensembl_id=gene_info.get("ensembl_id"),
                    uniprot_accession=gene_info.get("uniprot_accession"),
                    query_symbol=gene_info.get("query_symbol", ""),
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
                    disease_context=evidence_data.get("disease_context"),
                    results=results,
                    sources_available=available,
                    sources_failed=failed,
                )

                # Score the target
                framework = ScoringFramework()
                scorecard_result = framework.score_target(evidence_obj)

                # Store in session_state and rerun to display
                st.session_state[scorecard_key] = scorecard_result.model_dump()
                st.rerun()
            except Exception as e:
                st.error(f"Failed to compute scorecard: {e}")
                st.stop()
    else:
        st.info(
            "No evidence data available. Run the evidence pipeline or load a showcase scenario."
        )
        st.stop()


# ── Parse scorecard data ─────────────────────────────────────────────

def _safe_get(data, key, default=None):
    """Get value from dict or Pydantic model safely."""
    if isinstance(data, dict):
        return data.get(key, default)
    return getattr(data, key, default)


# Try to validate as ScorecardResult model, fall back to dict access
try:
    from src.scoring.models import ScorecardResult

    if isinstance(scorecard_data, dict):
        scorecard = ScorecardResult.model_validate(scorecard_data)
    elif isinstance(scorecard_data, ScorecardResult):
        scorecard = scorecard_data
    else:
        scorecard = None
except Exception:
    scorecard = None

# Extract fields -- prefer model access, fall back to dict
if scorecard is not None:
    gene_symbol = scorecard.gene_symbol
    composite_score = scorecard.composite.score
    verdict_level = scorecard.verdict.level.value if hasattr(scorecard.verdict.level, "value") else str(scorecard.verdict.level)
    verdict_obj = scorecard.verdict
    composite_obj = scorecard.composite
    dimension_scores = scorecard.composite.dimension_scores
else:
    # Pure dict access
    gene_symbol = _safe_get(scorecard_data, "gene_symbol", "Unknown")
    composite_dict = _safe_get(scorecard_data, "composite", {})
    verdict_dict = _safe_get(scorecard_data, "verdict", {})
    composite_score = _safe_get(composite_dict, "score", 0)
    verdict_level = _safe_get(verdict_dict, "level", "UNKNOWN")
    verdict_obj = verdict_dict
    composite_obj = composite_dict
    dimension_scores = _safe_get(composite_dict, "dimension_scores", [])


# ── Page Layout ──────────────────────────────────────────────────────

st.title("Target Scorecard")

# Verdict header
st.markdown(
    f"## {gene_symbol} {verdict_badge(verdict_level)}",
    unsafe_allow_html=True,
)

# ── Composite Score Metrics Row ──────────────────────────────────────

# Compute average data coverage
if scorecard is not None:
    coverages = [dim.data_coverage for dim in dimension_scores]
else:
    coverages = [_safe_get(d, "data_coverage", 0) for d in dimension_scores]

avg_coverage = sum(coverages) / len(coverages) if coverages else 0

metrics_html = '<div class="metrics-row">'
metrics_html += metric_card("Composite Score", f"{composite_score:.1f}/100")
metrics_html += metric_card("Verdict", str(verdict_level))
metrics_html += metric_card("Data Coverage", f"{avg_coverage:.0%}")
metrics_html += "</div>"
st.markdown(metrics_html, unsafe_allow_html=True)


# ── Radar Chart ──────────────────────────────────────────────────────

try:
    from src.scoring import build_single_radar, ScorecardResult as _SR

    if scorecard is not None:
        radar_fig = build_single_radar(scorecard)
    else:
        # Attempt to reconstruct from dict
        _scorecard_for_radar = _SR.model_validate(scorecard_data)
        radar_fig = build_single_radar(_scorecard_for_radar)

    st.plotly_chart(radar_fig, use_container_width=True, key="scorecard_radar")
except Exception as e:
    st.warning(f"Could not render radar chart: {e}")


# ── Dimension Breakdown ──────────────────────────────────────────────

st.subheader("Dimension Breakdown")

# Check for forced conditional violations
forced_conditional = False
dim_violations = []
if scorecard is not None:
    forced_conditional = scorecard.verdict.forced_conditional
    dim_violations = scorecard.verdict.dimension_violations
else:
    forced_conditional = _safe_get(verdict_obj, "forced_conditional", False)
    dim_violations = _safe_get(verdict_obj, "dimension_violations", [])

for dim in dimension_scores:
    if scorecard is not None:
        dim_name = dim.name
        dim_score = dim.score
        dim_max = dim.max_score
        dim_coverage = dim.data_coverage
        sub_scores = dim.sub_scores
    else:
        dim_name = _safe_get(dim, "name", "unknown")
        dim_score = _safe_get(dim, "score", 0)
        dim_max = _safe_get(dim, "max_score", 1)
        dim_coverage = _safe_get(dim, "data_coverage", 0)
        sub_scores = _safe_get(dim, "sub_scores", [])

    display_name = dim_name.replace("_", " ").title()
    pct = dim_score / dim_max if dim_max > 0 else 0

    with st.expander(f"{display_name} -- {dim_score:.1f}/{dim_max:.0f}"):
        st.progress(min(pct, 1.0), text=f"{pct:.0%}")
        st.caption(f"Data coverage: {dim_coverage:.0%}")

        # Sub-scores
        if sub_scores:
            st.markdown("**Sub-scores:**")
            for sub in sub_scores:
                if scorecard is not None:
                    sub_name = sub.name
                    sub_value = sub.value
                    sub_max = sub.max_value
                    sub_desc = sub.description
                else:
                    sub_name = _safe_get(sub, "name", "")
                    sub_value = _safe_get(sub, "value", 0)
                    sub_max = _safe_get(sub, "max_value", 1)
                    sub_desc = _safe_get(sub, "description", "")

                sub_display = sub_name.replace("_", " ").title()
                desc_text = f" -- {sub_desc}" if sub_desc else ""
                st.markdown(f"- **{sub_display}**: {sub_value:.2f}/{sub_max:.0f}{desc_text}")

        # Violation warning for this dimension
        if dim_name in dim_violations:
            st.markdown(
                warning_panel(
                    f"<strong>Dimension violation:</strong> {display_name} is below the minimum threshold, "
                    "contributing to a forced CONDITIONAL downgrade."
                ),
                unsafe_allow_html=True,
            )


# ── Forced Conditional Warning ───────────────────────────────────────

if forced_conditional:
    violation_names = [v.replace("_", " ").title() for v in dim_violations]
    st.markdown(
        alert_panel(
            f"<strong>Forced CONDITIONAL:</strong> The composite score exceeds the GO threshold, "
            f"but the following dimensions triggered a downgrade: "
            f"<strong>{', '.join(violation_names)}</strong>."
        ),
        unsafe_allow_html=True,
    )


# ── Export Section ───────────────────────────────────────────────────

st.divider()
st.subheader("Export Assessment Dossier")

col_html, col_pdf = st.columns(2)

with col_html:
    if st.button("Generate HTML Dossier", type="primary", key="scorecard_gen_html",
                 use_container_width=True):
        try:
            from src.reporting import HTMLDossierRenderer
            from src.reporting.models import DossierData, DossierConfig

            # Build DossierData from session_state data
            evidence_data = st.session_state.get(f"project_{pid}_evidence", {})
            reasoning_data = st.session_state.get(f"project_{pid}_reasoning", {})

            dossier_data = DossierData(
                gene_symbol=gene_symbol,
                disease_context=_safe_get(scorecard_data, "disease_context"),
                scorecard=scorecard_data if isinstance(scorecard_data, dict) else scorecard.model_dump(),
                evidence=evidence_data if isinstance(evidence_data, dict) else {},
                reasoning=reasoning_data if isinstance(reasoning_data, dict) else {},
            )

            renderer = HTMLDossierRenderer()
            html_str = renderer.render(dossier_data)

            st.download_button(
                "Download HTML",
                data=html_str,
                file_name=f"{gene_symbol}_dossier.html",
                mime="text/html",
                key="scorecard_download_html",
            )
        except Exception as e:
            st.error(f"HTML dossier generation failed: {e}")

with col_pdf:
    if st.button("Generate PDF Dossier", type="secondary", key="scorecard_gen_pdf",
                 use_container_width=True):
        try:
            from src.reporting import PDFDossierRenderer
            from src.reporting.models import DossierData, DossierConfig

            evidence_data = st.session_state.get(f"project_{pid}_evidence", {})
            reasoning_data = st.session_state.get(f"project_{pid}_reasoning", {})

            dossier_data = DossierData(
                gene_symbol=gene_symbol,
                disease_context=_safe_get(scorecard_data, "disease_context"),
                scorecard=scorecard_data if isinstance(scorecard_data, dict) else scorecard.model_dump(),
                evidence=evidence_data if isinstance(evidence_data, dict) else {},
                reasoning=reasoning_data if isinstance(reasoning_data, dict) else {},
            )

            renderer = PDFDossierRenderer()
            pdf_bytes = renderer.render(dossier_data)

            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name=f"{gene_symbol}_dossier.pdf",
                mime="application/pdf",
                key="scorecard_download_pdf",
            )
        except Exception as e:
            st.error(f"PDF dossier generation failed: {e}")


# ── Navigation ───────────────────────────────────────────────────────

st.page_link(
    "src/pages/audit.py",
    label="View Audit Trail",
    icon=":material/arrow_forward:",
)
