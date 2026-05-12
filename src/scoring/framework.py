"""Scoring framework orchestrator.

ScoringFramework wires together the 7 dimension calculators, composite
scoring, and verdict logic into a single score_target() call that
takes AggregatedEvidence and returns a ScorecardResult.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.scoring.dimensions import (
    score_clinical_translational,
    score_competitive_landscape,
    score_druggability,
    score_expression_biology,
    score_genetic_evidence,
    score_literature_consensus,
    score_safety_selectivity,
)
from src.scoring.models import ScorecardResult, WeightConfig
from src.scoring.verdict import compute_composite, determine_verdict
from src.scoring.weights import DEFAULT_WEIGHTS

if TYPE_CHECKING:
    from src.evidence.models import AggregatedEvidence
    from src.reasoning.models import ReasoningResult


class ScoringFramework:
    """Orchestrates the full scoring pipeline from evidence to verdict.

    Args:
        weights: Custom weight configuration, or None for DEFAULT_WEIGHTS.
        minimums: Custom dimension minimums, or None for DIMENSION_MINIMUMS default.
    """

    def __init__(
        self,
        weights: WeightConfig | None = None,
        minimums: dict[str, float] | None = None,
    ):
        self.weights = weights or DEFAULT_WEIGHTS
        self.minimums = minimums  # None uses DIMENSION_MINIMUMS default in verdict

    def score_target(
        self,
        evidence: AggregatedEvidence,
        reasoning_results: dict[str, ReasoningResult] | None = None,
        omics_scores: dict | None = None,
    ) -> ScorecardResult:
        """Score a single target gene from evidence and reasoning data.

        Args:
            evidence: Aggregated evidence from all sources for a single gene.
            reasoning_results: Optional dict of reasoning mode -> ReasoningResult.
                Keys can be mode names like "contradiction" or ReasoningMode enum values.
            omics_scores: Optional dict with omics-derived scores (e.g., cell type specificity).

        Returns:
            Complete ScorecardResult with 7 dimensions, composite score, and verdict.
        """
        # Extract evidence data dicts from evidence.results
        # Use None for sources with confidence=0.0 or missing
        def _get_data(source_name: str) -> dict | None:
            result = evidence.results.get(source_name)
            if result is None or result.confidence == 0.0:
                return None
            return result.data

        opentargets_data = _get_data("opentargets")
        dgidb_data = _get_data("dgidb")
        pubmed_data = _get_data("pubmed")
        clinicaltrials_data = _get_data("clinicaltrials")
        uniprot_data = _get_data("uniprot")
        chembl_data = _get_data("chembl")

        # Get contradiction result from reasoning_results if available
        contradiction_result = None
        if reasoning_results:
            contradiction_result = reasoning_results.get("contradiction")
            if contradiction_result is None:
                # Try enum value key
                try:
                    from src.reasoning.models import ReasoningMode
                    contradiction_result = reasoning_results.get(
                        ReasoningMode.CONTRADICTION.value
                    )
                except ImportError:
                    pass

        # Call all 7 dimension calculators
        dim_genetic = score_genetic_evidence(opentargets_data, evidence.disease_context)
        dim_expression = score_expression_biology(
            uniprot_data, opentargets_data, omics_scores
        )
        dim_druggability = score_druggability(dgidb_data, chembl_data, opentargets_data)
        dim_safety = score_safety_selectivity(uniprot_data, chembl_data, opentargets_data)
        dim_competitive = score_competitive_landscape(clinicaltrials_data)
        dim_clinical = score_clinical_translational(clinicaltrials_data, opentargets_data)
        dim_literature = score_literature_consensus(pubmed_data, contradiction_result)

        dimension_scores = [
            dim_genetic,
            dim_expression,
            dim_druggability,
            dim_safety,
            dim_competitive,
            dim_clinical,
            dim_literature,
        ]

        # Compute composite score
        composite = compute_composite(dimension_scores, self.weights)

        # Determine verdict
        verdict = determine_verdict(composite, self.minimums)

        # Compute evidence hash for reproducibility
        evidence_hash = _compute_evidence_hash(evidence)

        # Build result
        return ScorecardResult(
            gene_symbol=evidence.gene.canonical_symbol,
            disease_context=evidence.disease_context,
            composite=composite,
            verdict=verdict,
            evidence_hash=evidence_hash,
            scored_at=datetime.now(timezone.utc).isoformat(),
        )


def _compute_evidence_hash(evidence: AggregatedEvidence) -> str:
    """Compute SHA256 hash of evidence data for reproducibility verification.

    Serializes all evidence result data dicts to deterministic JSON
    (sort_keys=True) and hashes the combined payload.
    """
    data_payload = {}
    for source_name, result in sorted(evidence.results.items()):
        data_payload[source_name] = {
            "confidence": result.confidence,
            "data": result.data,
        }

    serialized = json.dumps(data_payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def score_target(evidence: AggregatedEvidence, **kwargs) -> ScorecardResult:
    """Convenience: create ScoringFramework and score a target.

    Args:
        evidence: Aggregated evidence for a single gene.
        **kwargs: Passed to ScoringFramework constructor (weights, minimums).

    Returns:
        Complete ScorecardResult.
    """
    # Separate framework kwargs from score_target kwargs
    framework_kwargs = {}
    score_kwargs = {}
    framework_params = {"weights", "minimums"}
    for k, v in kwargs.items():
        if k in framework_params:
            framework_kwargs[k] = v
        else:
            score_kwargs[k] = v

    return ScoringFramework(**framework_kwargs).score_target(evidence, **score_kwargs)
