"""7 dimension calculator functions composing sub-scores into DimensionScores.

Each dimension calculator is a pure function that takes evidence data dicts
and returns a DimensionScore. No I/O, no side effects. Each calls its
sub-score extractors from sub_scores.py and assembles the result.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.scoring.models import DimensionScore, SubScore
from src.scoring.sub_scores import (
    compute_active_trials_subscore,
    compute_biomarker_availability_subscore,
    compute_binding_pocket_subscore,
    compute_causal_evidence_subscore,
    compute_cell_type_specificity_subscore,
    compute_clinical_phase_max_subscore,
    compute_clinical_precedent_subscore,
    compute_competitor_density_subscore,
    compute_differentiation_potential_subscore,
    compute_druggability_class_subscore,
    compute_essential_gene_risk_subscore,
    compute_existing_compounds_subscore,
    compute_expression_breadth_subscore,
    compute_expression_disease_link_subscore,
    compute_functional_genomics_subscore,
    compute_genetic_association_subscore,
    compute_gwas_subscore,
    compute_known_safety_signals_subscore,
    compute_patient_selection_subscore,
    compute_publication_trend_subscore,
    compute_publication_volume_subscore,
    compute_review_articles_subscore,
    compute_selectivity_potential_subscore,
    compute_subcellular_location_subscore,
    compute_tissue_expression_subscore,
    compute_tractability_subscore,
    compute_translational_evidence_subscore,
)

if TYPE_CHECKING:
    from src.reasoning.models import ReasoningResult


def _compute_coverage(*data_sources: object) -> float:
    """Compute data coverage as fraction of non-None inputs."""
    if not data_sources:
        return 0.0
    present = sum(1 for d in data_sources if d is not None)
    return round(present / len(data_sources), 2)


def score_genetic_evidence(
    opentargets_data: dict | None,
    disease_context: str | None,
) -> DimensionScore:
    """Score genetic evidence dimension (max 15 points).

    Sub-scores:
    - gwas_associations (0-5): GWAS hits for target-disease pair
    - genetic_association_score (0-4): OpenTargets overall association score
    - causal_evidence (0-3): Mendelian disease links
    - functional_genomics (0-3): Functional genomics evidence
    """
    gwas = compute_gwas_subscore(opentargets_data, disease_context)
    assoc = compute_genetic_association_subscore(opentargets_data, disease_context)
    causal = compute_causal_evidence_subscore(opentargets_data)
    func_gen = compute_functional_genomics_subscore(opentargets_data)

    sub_scores = [
        SubScore(
            name="gwas_associations",
            value=gwas,
            max_value=5,
            data_source="opentargets",
        ),
        SubScore(
            name="genetic_association_score",
            value=assoc,
            max_value=4,
            data_source="opentargets",
        ),
        SubScore(
            name="causal_evidence",
            value=causal,
            max_value=3,
            data_source="opentargets",
        ),
        SubScore(
            name="functional_genomics",
            value=func_gen,
            max_value=3,
            data_source="opentargets",
        ),
    ]

    total = round(sum(s.value for s in sub_scores), 2)
    coverage = _compute_coverage(opentargets_data)

    return DimensionScore(
        name="genetic_evidence",
        score=total,
        max_score=15,
        sub_scores=sub_scores,
        data_coverage=coverage,
    )


def score_expression_biology(
    uniprot_data: dict | None,
    opentargets_data: dict | None,
    omics_scores: dict | None = None,
) -> DimensionScore:
    """Score expression biology dimension (max 15 points).

    Sub-scores:
    - tissue_expression (0-4): Expression in disease-relevant tissue
    - cell_type_specificity (0-4): Tissue specificity index (tau)
    - subcellular_location (0-4): Druggability-relevant location
    - expression_disease_link (0-3): Differential expression evidence
    """
    tissue = compute_tissue_expression_subscore(uniprot_data)
    cell_spec = compute_cell_type_specificity_subscore(omics_scores)
    location = compute_subcellular_location_subscore(uniprot_data)
    disease_link = compute_expression_disease_link_subscore(
        opentargets_data, uniprot_data
    )

    sub_scores = [
        SubScore(
            name="tissue_expression",
            value=tissue,
            max_value=4,
            data_source="uniprot",
        ),
        SubScore(
            name="cell_type_specificity",
            value=cell_spec,
            max_value=4,
            data_source="omics",
        ),
        SubScore(
            name="subcellular_location",
            value=location,
            max_value=4,
            data_source="uniprot",
        ),
        SubScore(
            name="expression_disease_link",
            value=disease_link,
            max_value=3,
            data_source="opentargets",
        ),
    ]

    total = round(sum(s.value for s in sub_scores), 2)
    coverage = _compute_coverage(uniprot_data, opentargets_data, omics_scores)

    return DimensionScore(
        name="expression_biology",
        score=total,
        max_score=15,
        sub_scores=sub_scores,
        data_coverage=coverage,
    )


def score_druggability(
    dgidb_data: dict | None,
    chembl_data: dict | None,
    opentargets_data: dict | None,
) -> DimensionScore:
    """Score druggability dimension (max 15 points).

    Sub-scores:
    - druggability_class (0-4): DGIdb gene categories
    - existing_compounds (0-4): ChEMBL activity count
    - tractability_modality (0-4): OT tractability labels
    - binding_pocket (0-3): ChEMBL max_pchembl value
    """
    drug_class = compute_druggability_class_subscore(dgidb_data)
    compounds = compute_existing_compounds_subscore(chembl_data)
    tract = compute_tractability_subscore(opentargets_data)
    pocket = compute_binding_pocket_subscore(chembl_data)

    sub_scores = [
        SubScore(
            name="druggability_class",
            value=drug_class,
            max_value=4,
            data_source="dgidb",
        ),
        SubScore(
            name="existing_compounds",
            value=compounds,
            max_value=4,
            data_source="chembl",
        ),
        SubScore(
            name="tractability_modality",
            value=tract,
            max_value=4,
            data_source="opentargets",
        ),
        SubScore(
            name="binding_pocket",
            value=pocket,
            max_value=3,
            data_source="chembl",
        ),
    ]

    total = round(sum(s.value for s in sub_scores), 2)
    coverage = _compute_coverage(dgidb_data, chembl_data, opentargets_data)

    return DimensionScore(
        name="druggability",
        score=total,
        max_score=15,
        sub_scores=sub_scores,
        data_coverage=coverage,
    )


def score_safety_selectivity(
    uniprot_data: dict | None,
    chembl_data: dict | None,
    opentargets_data: dict | None,
) -> DimensionScore:
    """Score safety/selectivity dimension (max 15 points).

    Sub-scores:
    - expression_breadth (0-4, inverted: broad = lower safety score)
    - known_safety_signals (0-4): ChEMBL adverse event data
    - essential_gene_risk (0-4): Gene essentiality
    - selectivity_potential (0-3): Protein domain uniqueness
    """
    breadth = compute_expression_breadth_subscore(uniprot_data)
    safety = compute_known_safety_signals_subscore(chembl_data)
    essential = compute_essential_gene_risk_subscore(opentargets_data)
    selectivity = compute_selectivity_potential_subscore(uniprot_data)

    sub_scores = [
        SubScore(
            name="expression_breadth",
            value=breadth,
            max_value=4,
            data_source="uniprot",
        ),
        SubScore(
            name="known_safety_signals",
            value=safety,
            max_value=4,
            data_source="chembl",
        ),
        SubScore(
            name="essential_gene_risk",
            value=essential,
            max_value=4,
            data_source="opentargets",
        ),
        SubScore(
            name="selectivity_potential",
            value=selectivity,
            max_value=3,
            data_source="uniprot",
        ),
    ]

    total = round(sum(s.value for s in sub_scores), 2)
    coverage = _compute_coverage(uniprot_data, chembl_data, opentargets_data)

    return DimensionScore(
        name="safety_selectivity",
        score=total,
        max_score=15,
        sub_scores=sub_scores,
        data_coverage=coverage,
    )


def score_competitive_landscape(
    clinicaltrials_data: dict | None,
) -> DimensionScore:
    """Score competitive landscape dimension (max 15 points).

    Sub-scores:
    - active_trials_count (0-4): Active/recruiting trials
    - clinical_phase_max (0-4): Highest phase reached
    - competitor_density (0-4): Unique sponsors
    - differentiation_potential (0-3): Gap analysis
    """
    trials = compute_active_trials_subscore(clinicaltrials_data)
    phase = compute_clinical_phase_max_subscore(clinicaltrials_data)
    density = compute_competitor_density_subscore(clinicaltrials_data)
    diff = compute_differentiation_potential_subscore(clinicaltrials_data)

    sub_scores = [
        SubScore(
            name="active_trials_count",
            value=trials,
            max_value=4,
            data_source="clinicaltrials",
        ),
        SubScore(
            name="clinical_phase_max",
            value=phase,
            max_value=4,
            data_source="clinicaltrials",
        ),
        SubScore(
            name="competitor_density",
            value=density,
            max_value=4,
            data_source="clinicaltrials",
        ),
        SubScore(
            name="differentiation_potential",
            value=diff,
            max_value=3,
            data_source="clinicaltrials",
        ),
    ]

    total = round(sum(s.value for s in sub_scores), 2)
    coverage = _compute_coverage(clinicaltrials_data)

    return DimensionScore(
        name="competitive_landscape",
        score=total,
        max_score=15,
        sub_scores=sub_scores,
        data_coverage=coverage,
    )


def score_clinical_translational(
    clinicaltrials_data: dict | None,
    opentargets_data: dict | None,
) -> DimensionScore:
    """Score clinical/translational dimension (max 15 points).

    Sub-scores:
    - clinical_precedent (0-5): Approved drug for target
    - biomarker_availability (0-4): Measurable endpoints
    - translational_evidence (0-3): Phase transition success
    - patient_selection (0-3): Trial design specificity
    """
    precedent = compute_clinical_precedent_subscore(opentargets_data)
    biomarker = compute_biomarker_availability_subscore(clinicaltrials_data)
    translational = compute_translational_evidence_subscore(
        clinicaltrials_data, opentargets_data
    )
    patient = compute_patient_selection_subscore(clinicaltrials_data)

    sub_scores = [
        SubScore(
            name="clinical_precedent",
            value=precedent,
            max_value=5,
            data_source="opentargets",
        ),
        SubScore(
            name="biomarker_availability",
            value=biomarker,
            max_value=4,
            data_source="clinicaltrials",
        ),
        SubScore(
            name="translational_evidence",
            value=translational,
            max_value=3,
            data_source="clinicaltrials",
        ),
        SubScore(
            name="patient_selection",
            value=patient,
            max_value=3,
            data_source="clinicaltrials",
        ),
    ]

    total = round(sum(s.value for s in sub_scores), 2)
    coverage = _compute_coverage(clinicaltrials_data, opentargets_data)

    return DimensionScore(
        name="clinical_translational",
        score=total,
        max_score=15,
        sub_scores=sub_scores,
        data_coverage=coverage,
    )


def score_literature_consensus(
    pubmed_data: dict | None,
    contradiction_result: ReasoningResult | None = None,
) -> DimensionScore:
    """Score literature consensus dimension (max 10 points, penalty up to -4).

    Base score from publication evidence (0-10), then subtract
    contradictory evidence penalty (0-4) based on the ReasoningEngine's
    CONTRADICTION mode output (REQ-406).

    Sub-scores:
    - publication_volume (0-4): Paper count
    - review_articles (0-3): Reviews/meta-analyses
    - publication_trend (0-3): Year-over-year growth
    - contradictory_evidence (0-4): Penalty for strong contradictions
    """
    pub_volume = compute_publication_volume_subscore(pubmed_data)
    reviews = compute_review_articles_subscore(pubmed_data)
    trend = compute_publication_trend_subscore(pubmed_data)

    base_total = pub_volume + reviews + trend

    # Compute contradiction penalty (REQ-406)
    penalty = 0.0
    num_strong_contradictions = 0
    if contradiction_result and contradiction_result.claims:
        strong_contradictions = [
            c for c in contradiction_result.claims if c.confidence >= 0.7
        ]
        num_strong_contradictions = len(strong_contradictions)
        penalty = min(num_strong_contradictions, 4)

    # Build sub-score list
    sub_scores = [
        SubScore(
            name="publication_volume",
            value=pub_volume,
            max_value=4,
            data_source="pubmed",
        ),
        SubScore(
            name="review_articles",
            value=reviews,
            max_value=3,
            data_source="pubmed",
        ),
        SubScore(
            name="publication_trend",
            value=trend,
            max_value=3,
            data_source="pubmed",
        ),
        SubScore(
            name="contradictory_evidence",
            value=penalty,
            max_value=4,
            description=f"{num_strong_contradictions} high-confidence contradictions found",
            data_source="reasoning",
        ),
    ]

    # Final score: base minus penalty, clamped to 0
    final_score = round(max(0.0, base_total - penalty), 2)

    coverage = _compute_coverage(pubmed_data)

    return DimensionScore(
        name="literature_consensus",
        score=final_score,
        max_score=10,
        sub_scores=sub_scores,
        data_coverage=coverage,
    )
