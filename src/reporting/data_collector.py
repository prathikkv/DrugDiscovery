"""Data collector: serialize upstream outputs into a unified DossierData container.

Aggregates ScorecardResult, AggregatedEvidence, ReasoningResult, and pipeline
report data into the DossierData model with pre-built section structure for
renderers to consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.reporting.models import DossierConfig, DossierData, SectionContent

if TYPE_CHECKING:
    from src.evidence.models import AggregatedEvidence
    from src.scoring.models import ComparativeScorecard, ScorecardResult
    from src.reasoning.models import ReasoningResult


def collect_dossier_data(
    scorecard_result: "ScorecardResult",
    evidence: "AggregatedEvidence",
    reasoning_results: dict[str, "ReasoningResult"] | None = None,
    pipeline_report: dict | None = None,
    comparative: "ComparativeScorecard | None" = None,
    config: DossierConfig | None = None,
) -> DossierData:
    """Collect all upstream data into a single DossierData container.

    Serializes upstream Pydantic/dataclass models into plain dicts suitable
    for JSON serialization and template rendering.

    Args:
        scorecard_result: Scored target result with composite and verdict.
        evidence: Aggregated evidence from all sources.
        reasoning_results: Optional map of mode_name -> ReasoningResult.
        pipeline_report: Optional pipeline report dict (from pipeline_report.json).
        comparative: Optional ComparativeScorecard for multi-target comparison.
        config: Optional rendering configuration (uses defaults if not provided).

    Returns:
        Populated DossierData with serialized data and 7 pre-built sections.
    """
    effective_config = config or DossierConfig()

    # Serialize scorecard
    scorecard_dict = scorecard_result.model_dump()

    # Serialize comparative if present
    comparative_dict = comparative.model_dump() if comparative else None

    # Serialize evidence: build dict with gene, disease_context, and results
    evidence_dict = _serialize_evidence(evidence)

    # Extract gene identifiers
    gene_identifiers = _extract_gene_identifiers(evidence)

    # Serialize reasoning results
    reasoning_dict: dict[str, dict] = {}
    if reasoning_results:
        for mode_name, result in reasoning_results.items():
            reasoning_dict[mode_name] = result.model_dump()

    # Build sections
    sections = _build_sections(
        scorecard_dict=scorecard_dict,
        evidence_dict=evidence_dict,
        reasoning_dict=reasoning_dict,
        gene_identifiers=gene_identifiers,
        pipeline_report=pipeline_report,
    )

    return DossierData(
        gene_symbol=scorecard_result.gene_symbol,
        disease_context=getattr(evidence, "disease_context", None),
        scorecard=scorecard_dict,
        comparative=comparative_dict,
        evidence=evidence_dict,
        reasoning=reasoning_dict,
        pipeline_report=pipeline_report,
        gene_identifiers=gene_identifiers,
        sections=sections,
        config=effective_config,
    )


def _serialize_evidence(evidence: "AggregatedEvidence") -> dict:
    """Serialize AggregatedEvidence into a plain dict.

    Builds a dict with gene identifiers, disease_context, and results
    mapped by source_name with confidence, data, error, and is_fallback fields.
    """
    results_dict: dict[str, dict] = {}
    for source_name, result in evidence.results.items():
        results_dict[source_name] = {
            "confidence": result.confidence,
            "data": result.data,
            "error": result.error,
            "is_fallback": result.is_fallback,
        }

    gene = evidence.gene
    return {
        "gene": {
            "canonical_symbol": gene.canonical_symbol,
            "ensembl_id": gene.ensembl_id,
            "uniprot_accession": gene.uniprot_accession,
            "query_symbol": gene.query_symbol,
        },
        "disease_context": evidence.disease_context,
        "results": results_dict,
    }


def _extract_gene_identifiers(evidence: "AggregatedEvidence") -> dict:
    """Extract gene identifiers from evidence into a plain dict."""
    gene = evidence.gene
    return {
        "canonical_symbol": gene.canonical_symbol,
        "ensembl_id": gene.ensembl_id,
        "uniprot_accession": gene.uniprot_accession,
        "query_symbol": gene.query_symbol,
    }


def _build_sections(
    scorecard_dict: dict,
    evidence_dict: dict,
    reasoning_dict: dict[str, dict],
    gene_identifiers: dict,
    pipeline_report: dict | None,
) -> dict[str, SectionContent]:
    """Build the 7 standard dossier sections from serialized data.

    Sections: executive_summary, target_overview, evidence_dimensions,
    ai_synthesis, scorecard, recommendations, audit_trail.
    """
    sections: dict[str, SectionContent] = {}

    # 1. Executive Summary
    verdict = scorecard_dict.get("verdict", {})
    composite = scorecard_dict.get("composite", {})
    synthesis_summary = ""
    if "synthesis" in reasoning_dict:
        synthesis_summary = reasoning_dict["synthesis"].get("summary", "")

    sections["executive_summary"] = SectionContent(
        title="Executive Summary",
        narrative=_build_executive_narrative(verdict, composite, synthesis_summary),
        data={
            "verdict_level": verdict.get("level", ""),
            "composite_score": composite.get("score", 0),
            "forced_conditional": verdict.get("forced_conditional", False),
            "dimension_violations": verdict.get("dimension_violations", []),
        },
        charts=["radar_single"],
    )

    # 2. Target Overview
    uniprot_data = _extract_uniprot_data(evidence_dict)
    sections["target_overview"] = SectionContent(
        title="Target Overview",
        narrative=_build_target_overview_narrative(gene_identifiers, uniprot_data),
        data={
            "gene_identifiers": gene_identifiers,
            "uniprot_data": uniprot_data,
        },
        charts=[],
    )

    # 3. Evidence Dimensions
    dimension_scores = composite.get("dimension_scores", [])
    sections["evidence_dimensions"] = SectionContent(
        title="Evidence Dimensions",
        narrative=_build_evidence_dimensions_narrative(dimension_scores),
        data={
            "dimension_scores": dimension_scores,
            "evidence_sources": list(evidence_dict.get("results", {}).keys()),
        },
        charts=["evidence_dimensions_bar", "score_breakdown"],
    )

    # 4. AI Synthesis
    claims = []
    for mode_name, mode_data in reasoning_dict.items():
        mode_claims = mode_data.get("claims", [])
        for claim in mode_claims:
            claims.append({"mode": mode_name, **claim})

    sections["ai_synthesis"] = SectionContent(
        title="AI Synthesis & Reasoning",
        narrative=synthesis_summary or "No AI reasoning analysis available.",
        data={
            "claims": claims,
            "modes_analyzed": list(reasoning_dict.keys()),
        },
        charts=[],
    )

    # 5. Scorecard
    sections["scorecard"] = SectionContent(
        title="Scorecard",
        narrative=_build_scorecard_narrative(composite, verdict),
        data={
            "composite": composite,
            "verdict": verdict,
            "formula_version": composite.get("formula_version", "v1.0"),
        },
        charts=["radar_single"],
    )

    # 6. Recommendations
    sections["recommendations"] = SectionContent(
        title="Recommendations & Next Steps",
        narrative=_build_recommendations_narrative(verdict, composite),
        data={
            "verdict_level": verdict.get("level", ""),
            "dimension_violations": verdict.get("dimension_violations", []),
        },
        charts=[],
    )

    # 7. Audit Trail
    evidence_sources_info: dict[str, dict] = {}
    for source_name, source_data in evidence_dict.get("results", {}).items():
        evidence_sources_info[source_name] = {
            "confidence": source_data.get("confidence", 0),
            "is_fallback": source_data.get("is_fallback", False),
            "has_error": source_data.get("error") is not None,
        }

    reasoning_provenance: dict[str, dict] = {}
    for mode_name, mode_data in reasoning_dict.items():
        reasoning_provenance[mode_name] = {
            "created_at": mode_data.get("created_at", ""),
            "has_tool_trace": mode_data.get("tool_trace") is not None,
            "hallucination_issues": len(mode_data.get("hallucination_issues", [])),
        }

    sections["audit_trail"] = SectionContent(
        title="Audit Trail & Provenance",
        narrative="Full provenance chain for reproducibility and regulatory compliance.",
        data={
            "evidence_hash": scorecard_dict.get("evidence_hash", ""),
            "scored_at": scorecard_dict.get("scored_at", ""),
            "evidence_sources": evidence_sources_info,
            "reasoning_provenance": reasoning_provenance,
            "pipeline_report_available": pipeline_report is not None,
        },
        charts=[],
    )

    return sections


def _build_executive_narrative(
    verdict: dict, composite: dict, synthesis_summary: str
) -> str:
    """Build executive summary narrative from verdict and synthesis."""
    level = verdict.get("level", "UNKNOWN")
    score = composite.get("score", 0)
    rationale = verdict.get("rationale", "")

    parts = [f"Assessment result: {level} (composite score: {score:.1f}/100)."]

    if rationale:
        parts.append(rationale)

    violations = verdict.get("dimension_violations", [])
    if violations:
        parts.append(
            f"Dimension violations detected: {', '.join(violations)}."
        )

    if verdict.get("forced_conditional"):
        parts.append(
            "Note: Score exceeds GO threshold but was downgraded to CONDITIONAL "
            "due to dimension violations."
        )

    if synthesis_summary:
        parts.append(f"\nAI Synthesis: {synthesis_summary}")

    return "\n\n".join(parts)


def _build_target_overview_narrative(
    gene_identifiers: dict, uniprot_data: dict | None
) -> str:
    """Build target overview narrative from gene identifiers and UniProt data."""
    symbol = gene_identifiers.get("canonical_symbol", "Unknown")
    parts = [f"Target gene: {symbol}"]

    ensembl = gene_identifiers.get("ensembl_id")
    if ensembl:
        parts.append(f"Ensembl: {ensembl}")

    uniprot = gene_identifiers.get("uniprot_accession")
    if uniprot:
        parts.append(f"UniProt: {uniprot}")

    query = gene_identifiers.get("query_symbol")
    if query and query != symbol:
        parts.append(f"Query alias: {query}")

    narrative = " | ".join(parts)

    if uniprot_data:
        protein_name = uniprot_data.get("protein_name", "")
        function_text = uniprot_data.get("function", "")
        if protein_name:
            narrative += f"\n\nProtein: {protein_name}"
        if function_text:
            narrative += f"\n\nFunction: {function_text}"

    return narrative


def _extract_uniprot_data(evidence_dict: dict) -> dict | None:
    """Extract UniProt protein data from evidence results if available."""
    results = evidence_dict.get("results", {})
    uniprot_result = results.get("uniprot", {})
    data = uniprot_result.get("data")
    if not data:
        return None

    return {
        "protein_name": data.get("protein_name", ""),
        "function": data.get("function", ""),
        "subcellular_location": data.get("subcellular_location", ""),
        "gene_names": data.get("gene_names", []),
    }


def _build_evidence_dimensions_narrative(dimension_scores: list[dict]) -> str:
    """Build evidence dimensions narrative from dimension score list."""
    if not dimension_scores:
        return "No dimension scores available."

    parts = [f"Scoring across {len(dimension_scores)} dimensions:"]
    for dim in dimension_scores:
        name = dim.get("name", "unknown")
        score = dim.get("score", 0)
        max_score = dim.get("max_score", 1)
        coverage = dim.get("data_coverage", 0)
        pct = (score / max_score * 100) if max_score > 0 else 0
        parts.append(
            f"  - {name}: {score:.1f}/{max_score:.0f} "
            f"({pct:.0f}%, data coverage: {coverage:.0%})"
        )

    return "\n".join(parts)


def _build_scorecard_narrative(composite: dict, verdict: dict) -> str:
    """Build scorecard section narrative with composite breakdown."""
    score = composite.get("score", 0)
    level = verdict.get("level", "UNKNOWN")
    version = composite.get("formula_version", "v1.0")

    return (
        f"Composite score: {score:.1f}/100 ({level})\n"
        f"Formula version: {version}\n"
        f"Score breakdown by weighted dimensions available in data."
    )


def _build_recommendations_narrative(verdict: dict, composite: dict) -> str:
    """Build recommendations based on verdict level and violations."""
    level = verdict.get("level", "UNKNOWN")
    violations = verdict.get("dimension_violations", [])
    score = composite.get("score", 0)

    if level == "GO":
        narrative = (
            f"Target scores {score:.1f}/100 with no critical dimension violations. "
            "Proceed to experimental validation and lead optimization. "
            "Recommended next steps:\n"
            "  1. Design validation experiments for top-scoring dimensions\n"
            "  2. Commission additional assays for lower-scoring areas\n"
            "  3. Begin competitive landscape deep-dive"
        )
    elif level == "CONDITIONAL":
        violation_text = ", ".join(violations) if violations else "none specified"
        narrative = (
            f"Target scores {score:.1f}/100 but requires additional evidence or "
            f"resolution of concerns in: {violation_text}.\n"
            "Recommended next steps:\n"
            "  1. Address dimension violations with targeted experiments\n"
            "  2. Gather additional evidence for low-coverage areas\n"
            "  3. Re-assess after new data is available"
        )
    elif level == "NO-GO":
        narrative = (
            f"Target scores {score:.1f}/100, below the threshold for advancement. "
            "Significant concerns identified.\n"
            "Recommended next steps:\n"
            "  1. Review dimension scores for salvageable aspects\n"
            "  2. Consider alternative targets in the same pathway\n"
            "  3. Archive assessment for future reference"
        )
    else:
        narrative = "Assessment status unknown. Review scorecard data manually."

    return narrative
