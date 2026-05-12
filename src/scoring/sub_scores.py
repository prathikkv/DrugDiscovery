"""24 sub-score extractor functions mapping evidence data fields to numeric scores.

Each function is a pure computation: takes a dict (or None) from evidence sources,
returns a float within defined bounds. No I/O, no side effects.
All functions handle None input gracefully (return 0.0).
All return values are rounded to 2 decimal places.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Genetic Evidence sub-scores (max 15 total: 5 + 4 + 3 + 3)
# ---------------------------------------------------------------------------


def compute_gwas_subscore(
    opentargets_data: dict | None, disease_context: str | None
) -> float:
    """GWAS sub-score: 0-5 points.

    Rules:
    - 0: No associations or no data
    - 1: Any association exists (overall_score > 0)
    - 2: Disease-relevant association (context_relevant=True)
    - 3: Strong association (overall_score >= 0.5)
    - 4: Very strong association (overall_score >= 0.7)
    - 5: Top-tier association (overall_score >= 0.9)
    """
    if not opentargets_data:
        return 0.0

    associations = opentargets_data.get("associations", [])
    if not associations:
        return 0.0

    best_score = 0.0
    has_context_relevant = False
    for assoc in associations:
        score = assoc.get("overall_score", 0.0)
        best_score = max(best_score, score)
        if disease_context and assoc.get("context_relevant"):
            has_context_relevant = True

    if best_score >= 0.9:
        return round(5.0, 2)
    elif best_score >= 0.7:
        return round(4.0, 2)
    elif best_score >= 0.5:
        return round(3.0, 2)
    elif has_context_relevant:
        return round(2.0, 2)
    elif best_score > 0:
        return round(1.0, 2)
    return 0.0


def compute_genetic_association_subscore(
    opentargets_data: dict | None, disease_context: str | None
) -> float:
    """Genetic association sub-score: 0-4 points.

    Maps OpenTargets overall_score:
    - 0: No data
    - 1: overall_score > 0
    - 2: overall_score >= 0.3
    - 3: overall_score >= 0.6
    - 4: overall_score >= 0.8
    """
    if not opentargets_data:
        return 0.0

    associations = opentargets_data.get("associations", [])
    if not associations:
        return 0.0

    best_score = max(
        (a.get("overall_score", 0.0) for a in associations), default=0.0
    )

    if best_score >= 0.8:
        return round(4.0, 2)
    elif best_score >= 0.6:
        return round(3.0, 2)
    elif best_score >= 0.3:
        return round(2.0, 2)
    elif best_score > 0:
        return round(1.0, 2)
    return 0.0


def compute_causal_evidence_subscore(opentargets_data: dict | None) -> float:
    """Causal evidence sub-score: 0-3 points.

    Checks datatypeScores for genetic_association type.
    - 0: No data
    - 1: Any score
    - 2: score >= 0.3
    - 3: score >= 0.6
    """
    if not opentargets_data:
        return 0.0

    datatype_scores = opentargets_data.get("datatypeScores", [])
    if not datatype_scores:
        return 0.0

    ga_score = 0.0
    for dt in datatype_scores:
        if dt.get("id") == "genetic_association":
            ga_score = max(ga_score, dt.get("score", 0.0))

    if ga_score >= 0.6:
        return round(3.0, 2)
    elif ga_score >= 0.3:
        return round(2.0, 2)
    elif ga_score > 0:
        return round(1.0, 2)
    return 0.0


def compute_functional_genomics_subscore(opentargets_data: dict | None) -> float:
    """Functional genomics sub-score: 0-3 points.

    Checks datatypeScores for affected_pathway type.
    - 0: No data
    - 1: Any score
    - 2: score >= 0.3
    - 3: score >= 0.6
    """
    if not opentargets_data:
        return 0.0

    datatype_scores = opentargets_data.get("datatypeScores", [])
    if not datatype_scores:
        return 0.0

    fg_score = 0.0
    for dt in datatype_scores:
        if dt.get("id") == "affected_pathway":
            fg_score = max(fg_score, dt.get("score", 0.0))

    if fg_score >= 0.6:
        return round(3.0, 2)
    elif fg_score >= 0.3:
        return round(2.0, 2)
    elif fg_score > 0:
        return round(1.0, 2)
    return 0.0


# ---------------------------------------------------------------------------
# Expression Biology sub-scores (max 15 total: 4 + 4 + 4 + 3)
# ---------------------------------------------------------------------------


def compute_tissue_expression_subscore(uniprot_data: dict | None) -> float:
    """Tissue expression sub-score: 0-4 points.

    From UniProt tissue expression data.
    - 0: No data
    - 1: Expressed in at least one tissue
    - 2: Multiple tissues
    - 3: Disease-relevant tissue
    - 4: High expression in relevant tissue
    """
    if not uniprot_data:
        return 0.0

    tissue_expr = uniprot_data.get("tissue_expression", {})
    if not tissue_expr:
        return 0.0

    tissues = tissue_expr.get("tissues", [])
    has_high_relevance = tissue_expr.get("high_relevance", False)
    has_disease_relevant = tissue_expr.get("disease_relevant", False)

    if has_high_relevance:
        return round(4.0, 2)
    elif has_disease_relevant:
        return round(3.0, 2)
    elif len(tissues) > 1:
        return round(2.0, 2)
    elif len(tissues) >= 1 or tissue_expr:
        return round(1.0, 2)
    return 0.0


def compute_cell_type_specificity_subscore(omics_scores: dict | None) -> float:
    """Cell type specificity sub-score: 0-4 points.

    From optional omics tau score (tissue specificity index).
    - 0: No data or broad expression (tau <= 0.3)
    - 1: tau > 0.3
    - 2: tau > 0.5
    - 3: tau > 0.7
    - 4: tau > 0.85
    """
    if not omics_scores:
        return 0.0

    tau = omics_scores.get("tau", 0.0)

    if tau > 0.85:
        return round(4.0, 2)
    elif tau > 0.7:
        return round(3.0, 2)
    elif tau > 0.5:
        return round(2.0, 2)
    elif tau > 0.3:
        return round(1.0, 2)
    return 0.0


def compute_subcellular_location_subscore(uniprot_data: dict | None) -> float:
    """Subcellular location sub-score: 0-4 points.

    UniProt subcellular_location field.
    - 4: Cell surface or secreted (best druggability)
    - 3: Membrane
    - 2: Cytoplasm
    - 1: Nucleus
    - 0: Unknown or no data
    """
    if not uniprot_data:
        return 0.0

    location = uniprot_data.get("subcellular_location", "").lower()
    if not location:
        return 0.0

    if "cell surface" in location or "secreted" in location or "extracellular" in location:
        return round(4.0, 2)
    elif "membrane" in location:
        return round(3.0, 2)
    elif "cytoplasm" in location or "cytosol" in location:
        return round(2.0, 2)
    elif "nucleus" in location or "nuclear" in location:
        return round(1.0, 2)
    return 0.0


def compute_expression_disease_link_subscore(
    opentargets_data: dict | None, uniprot_data: dict | None
) -> float:
    """Expression-disease link sub-score: 0-3 points.

    Differential expression evidence.
    - 0: No evidence
    - 1: Expressed in disease tissue
    - 2: Evidence of dysregulation
    - 3: Strong differential expression evidence
    """
    if not opentargets_data and not uniprot_data:
        return 0.0

    score = 0.0

    # Check OpenTargets for expression evidence
    if opentargets_data:
        datatype_scores = opentargets_data.get("datatypeScores", [])
        for dt in datatype_scores:
            if dt.get("id") in ("rna_expression", "affected_pathway"):
                dt_score = dt.get("score", 0.0)
                if dt_score >= 0.5:
                    score = max(score, 3.0)
                elif dt_score >= 0.3:
                    score = max(score, 2.0)
                elif dt_score > 0:
                    score = max(score, 1.0)

    # Check UniProt for disease-relevant expression
    if uniprot_data and score < 1.0:
        tissue_expr = uniprot_data.get("tissue_expression", {})
        if tissue_expr.get("disease_relevant", False):
            score = max(score, 1.0)

    return round(score, 2)


# ---------------------------------------------------------------------------
# Druggability sub-scores (max 15 total: 4 + 4 + 4 + 3)
# ---------------------------------------------------------------------------


def compute_druggability_class_subscore(dgidb_data: dict | None) -> float:
    """Druggability class sub-score: 0-4 points.

    DGIdb gene categories.
    - 4: Clinically actionable
    - 3: Druggable genome
    - 2: Drug resistant or enzyme
    - 1: Any category
    - 0: No categories
    """
    if not dgidb_data:
        return 0.0

    categories = dgidb_data.get("gene_categories", [])
    if not categories:
        return 0.0

    # Normalize categories for comparison
    upper_categories = [c.upper() for c in categories]

    if "CLINICALLY ACTIONABLE" in upper_categories:
        return round(4.0, 2)
    elif "DRUGGABLE GENOME" in upper_categories:
        return round(3.0, 2)
    elif any(c in upper_categories for c in ["DRUG RESISTANT", "ENZYME"]):
        return round(2.0, 2)
    else:
        return round(1.0, 2)


def compute_existing_compounds_subscore(chembl_data: dict | None) -> float:
    """Existing compounds sub-score: 0-4 points.

    ChEMBL activity count.
    - 0: No activities
    - 1: 1-5 activities
    - 2: 6-20 activities
    - 3: 21-50 activities
    - 4: >50 activities
    """
    if not chembl_data:
        return 0.0

    count = chembl_data.get("activity_count", 0)

    if count > 50:
        return round(4.0, 2)
    elif count >= 21:
        return round(3.0, 2)
    elif count >= 6:
        return round(2.0, 2)
    elif count >= 1:
        return round(1.0, 2)
    return 0.0


def compute_tractability_subscore(opentargets_data: dict | None) -> float:
    """Tractability sub-score: 0-4 points.

    OpenTargets tractability labels.
    Score based on small_molecule, antibody, or other_modalities tractability buckets.
    - 0: No tractability data
    - 1: Low tractability
    - 2: Some tractability evidence
    - 3: Good tractability
    - 4: High tractability (clinical precedence)
    """
    if not opentargets_data:
        return 0.0

    tractability = opentargets_data.get("tractability", {})
    if not tractability:
        return 0.0

    best_bucket = 0
    for modality in ["small_molecule", "antibody", "other_modalities"]:
        buckets = tractability.get(modality, {})
        if isinstance(buckets, dict):
            bucket_val = buckets.get("top_category", 0)
            best_bucket = max(best_bucket, bucket_val)
        elif isinstance(buckets, (int, float)):
            best_bucket = max(best_bucket, int(buckets))

    if best_bucket >= 4:
        return round(4.0, 2)
    elif best_bucket >= 3:
        return round(3.0, 2)
    elif best_bucket >= 2:
        return round(2.0, 2)
    elif best_bucket >= 1:
        return round(1.0, 2)
    return 0.0


def compute_binding_pocket_subscore(chembl_data: dict | None) -> float:
    """Binding pocket sub-score: 0-3 points.

    ChEMBL max_pchembl value.
    - 0: No data
    - 1: Any pchembl value
    - 2: pchembl >= 5.0
    - 3: pchembl >= 7.0
    """
    if not chembl_data:
        return 0.0

    pchembl = chembl_data.get("max_pchembl", 0.0)
    if not pchembl:
        return 0.0

    if pchembl >= 7.0:
        return round(3.0, 2)
    elif pchembl >= 5.0:
        return round(2.0, 2)
    elif pchembl > 0:
        return round(1.0, 2)
    return 0.0


# ---------------------------------------------------------------------------
# Safety/Selectivity sub-scores (max 15 total: 4 + 4 + 4 + 3)
# ---------------------------------------------------------------------------


def compute_expression_breadth_subscore(uniprot_data: dict | None) -> float:
    """Expression breadth sub-score: 0-4 points (INVERTED - broad = lower score).

    Broad expression means lower safety score (more off-target risk).
    - 4: Tissue-restricted (safest)
    - 3: Few tissues
    - 2: Moderate breadth
    - 1: Broad expression
    - 0: Ubiquitous or no data (riskiest)
    """
    if not uniprot_data:
        return 0.0

    tissue_expr = uniprot_data.get("tissue_expression", {})
    if not tissue_expr:
        return 0.0

    if tissue_expr.get("ubiquitous", False):
        return 0.0

    tissue_count = len(tissue_expr.get("tissues", []))
    restricted = tissue_expr.get("restricted", False)

    if restricted or tissue_count <= 2:
        return round(4.0, 2)
    elif tissue_count <= 5:
        return round(3.0, 2)
    elif tissue_count <= 10:
        return round(2.0, 2)
    else:
        return round(1.0, 2)


def compute_known_safety_signals_subscore(chembl_data: dict | None) -> float:
    """Known safety signals sub-score: 0-4 points.

    Known adverse events from ChEMBL mechanisms.
    - 4: No safety signals (clean)
    - 3: Minor signals
    - 2: Moderate signals
    - 1: Significant signals
    - 0: Severe safety flags
    """
    if not chembl_data:
        return 0.0

    safety_signals = chembl_data.get("safety_signals", [])
    adverse_count = chembl_data.get("adverse_event_count", 0)

    if not safety_signals and adverse_count == 0:
        # No data on safety -- assume clean if compounds exist
        if chembl_data.get("activity_count", 0) > 0:
            return round(4.0, 2)
        return 0.0

    severity = chembl_data.get("max_severity", "none")
    if severity == "severe":
        return 0.0
    elif severity == "significant":
        return round(1.0, 2)
    elif severity == "moderate":
        return round(2.0, 2)
    elif severity == "minor":
        return round(3.0, 2)
    else:
        return round(4.0, 2)


def compute_essential_gene_risk_subscore(opentargets_data: dict | None) -> float:
    """Essential gene risk sub-score: 0-4 points.

    Gene essentiality indicator.
    - 4: Not essential
    - 3: Low essentiality
    - 2: Moderate essentiality
    - 1: Context-essential
    - 0: Pan-essential (riskiest)
    """
    if not opentargets_data:
        return 0.0

    essentiality = opentargets_data.get("essentiality", {})
    if not essentiality:
        # No essentiality data -- neutral score
        return round(2.0, 2)

    is_essential = essentiality.get("is_essential", False)
    context_only = essentiality.get("context_dependent", False)

    if is_essential and not context_only:
        return 0.0
    elif context_only:
        return round(1.0, 2)
    elif essentiality.get("low_essentiality", False):
        return round(3.0, 2)
    else:
        return round(4.0, 2)


def compute_selectivity_potential_subscore(uniprot_data: dict | None) -> float:
    """Selectivity potential sub-score: 0-3 points.

    Protein domain uniqueness from UniProt.
    - 0: No data
    - 1: Common domains
    - 2: Some unique features
    - 3: Unique binding site/domain
    """
    if not uniprot_data:
        return 0.0

    domains = uniprot_data.get("domains", [])
    has_unique = uniprot_data.get("unique_binding_site", False)
    has_some_unique = uniprot_data.get("unique_features", False)

    if has_unique:
        return round(3.0, 2)
    elif has_some_unique or len(domains) > 3:
        return round(2.0, 2)
    elif domains:
        return round(1.0, 2)
    return 0.0


# ---------------------------------------------------------------------------
# Competitive Landscape sub-scores (max 15 total: 4 + 4 + 4 + 3)
# ---------------------------------------------------------------------------


def compute_active_trials_subscore(clinicaltrials_data: dict | None) -> float:
    """Active trials sub-score: 0-4 points.

    Active/recruiting clinical trials count.
    - 0: No trials
    - 1: 1-2 trials
    - 2: 3-5 trials
    - 3: 6-10 trials
    - 4: >10 trials
    """
    if not clinicaltrials_data:
        return 0.0

    count = clinicaltrials_data.get("active_count", 0)

    if count > 10:
        return round(4.0, 2)
    elif count >= 6:
        return round(3.0, 2)
    elif count >= 3:
        return round(2.0, 2)
    elif count >= 1:
        return round(1.0, 2)
    return 0.0


def compute_clinical_phase_max_subscore(clinicaltrials_data: dict | None) -> float:
    """Clinical phase max sub-score: 0-4 points.

    Highest clinical trial phase reached.
    - 0: No trials
    - 1: Phase 1
    - 2: Phase 2
    - 3: Phase 3
    - 4: Phase 4/approved
    """
    if not clinicaltrials_data:
        return 0.0

    max_phase = clinicaltrials_data.get("max_phase", 0)

    if max_phase >= 4:
        return round(4.0, 2)
    elif max_phase == 3:
        return round(3.0, 2)
    elif max_phase == 2:
        return round(2.0, 2)
    elif max_phase == 1:
        return round(1.0, 2)
    return 0.0


def compute_competitor_density_subscore(clinicaltrials_data: dict | None) -> float:
    """Competitor density sub-score: 0-4 points.

    Number of unique sponsors in clinical trials.
    - 0: No trials
    - 1: 1 sponsor
    - 2: 2-3 sponsors
    - 3: 4-7 sponsors
    - 4: >7 sponsors
    """
    if not clinicaltrials_data:
        return 0.0

    sponsors = clinicaltrials_data.get("unique_sponsors", 0)

    if sponsors > 7:
        return round(4.0, 2)
    elif sponsors >= 4:
        return round(3.0, 2)
    elif sponsors >= 2:
        return round(2.0, 2)
    elif sponsors >= 1:
        return round(1.0, 2)
    return 0.0


def compute_differentiation_potential_subscore(
    clinicaltrials_data: dict | None,
) -> float:
    """Differentiation potential sub-score: 0-3 points.

    Gap analysis from clinical trials.
    - 3: No competitors (open field)
    - 2: Few competitors
    - 1: Moderate competition
    - 0: Saturated market
    """
    if not clinicaltrials_data:
        return 0.0

    sponsors = clinicaltrials_data.get("unique_sponsors", 0)
    active = clinicaltrials_data.get("active_count", 0)

    if active == 0 and sponsors == 0:
        return round(3.0, 2)
    elif sponsors <= 2:
        return round(2.0, 2)
    elif sponsors <= 5:
        return round(1.0, 2)
    else:
        return 0.0


# ---------------------------------------------------------------------------
# Clinical/Translational sub-scores (max 15 total: 5 + 4 + 3 + 3)
# ---------------------------------------------------------------------------


def compute_clinical_precedent_subscore(opentargets_data: dict | None) -> float:
    """Clinical precedent sub-score: 0-5 points.

    Approved drug for this target.
    - 0: No data
    - 1: Preclinical
    - 2: Phase 1
    - 3: Phase 2
    - 4: Phase 3
    - 5: Approved drug
    """
    if not opentargets_data:
        return 0.0

    if opentargets_data.get("has_approved_drug", False):
        return round(5.0, 2)

    max_phase = opentargets_data.get("max_phase", 0)
    if max_phase >= 4:
        return round(5.0, 2)
    elif max_phase == 3:
        return round(4.0, 2)
    elif max_phase == 2:
        return round(3.0, 2)
    elif max_phase == 1:
        return round(2.0, 2)
    elif max_phase > 0:
        return round(1.0, 2)
    return 0.0


def compute_biomarker_availability_subscore(
    clinicaltrials_data: dict | None,
) -> float:
    """Biomarker availability sub-score: 0-4 points.

    Measurable endpoints from trials.
    - 0: No data
    - 1: Basic endpoints
    - 2: Several endpoints
    - 3: Validated biomarker
    - 4: Companion diagnostic
    """
    if not clinicaltrials_data:
        return 0.0

    biomarker_level = clinicaltrials_data.get("biomarker_level", 0)

    if biomarker_level >= 4:
        return round(4.0, 2)
    elif biomarker_level >= 3:
        return round(3.0, 2)
    elif biomarker_level >= 2:
        return round(2.0, 2)
    elif biomarker_level >= 1:
        return round(1.0, 2)
    return 0.0


def compute_translational_evidence_subscore(
    clinicaltrials_data: dict | None, opentargets_data: dict | None
) -> float:
    """Translational evidence sub-score: 0-3 points.

    Phase transition success evidence.
    - 0: No evidence
    - 1: Some translational evidence
    - 2: Good translational evidence
    - 3: Strong translational evidence
    """
    if not clinicaltrials_data and not opentargets_data:
        return 0.0

    score = 0.0

    # Check for clinical trial phase progression
    if clinicaltrials_data:
        max_phase = clinicaltrials_data.get("max_phase", 0)
        if max_phase >= 3:
            score = max(score, 3.0)
        elif max_phase >= 2:
            score = max(score, 2.0)
        elif max_phase >= 1:
            score = max(score, 1.0)

    # Check for OT known drugs
    if opentargets_data and score < 2.0:
        known_drugs = opentargets_data.get("known_drugs", [])
        if known_drugs:
            score = max(score, 1.0)

    return round(score, 2)


def compute_patient_selection_subscore(clinicaltrials_data: dict | None) -> float:
    """Patient selection sub-score: 0-3 points.

    Trial design specificity.
    - 0: No data
    - 1: Broad enrollment
    - 2: Enriched population
    - 3: Biomarker-selected
    """
    if not clinicaltrials_data:
        return 0.0

    selection_level = clinicaltrials_data.get("patient_selection_level", 0)

    if selection_level >= 3:
        return round(3.0, 2)
    elif selection_level >= 2:
        return round(2.0, 2)
    elif selection_level >= 1:
        return round(1.0, 2)
    return 0.0


# ---------------------------------------------------------------------------
# Literature Consensus sub-scores (max 10 total: 4 + 3 + 3)
# ---------------------------------------------------------------------------


def compute_publication_volume_subscore(pubmed_data: dict | None) -> float:
    """Publication volume sub-score: 0-4 points.

    Paper count.
    - 0: No papers
    - 1: 1-5 papers
    - 2: 6-20 papers
    - 3: 21-100 papers
    - 4: >100 papers
    """
    if not pubmed_data:
        return 0.0

    count = pubmed_data.get("paper_count", 0)

    if count > 100:
        return round(4.0, 2)
    elif count >= 21:
        return round(3.0, 2)
    elif count >= 6:
        return round(2.0, 2)
    elif count >= 1:
        return round(1.0, 2)
    return 0.0


def compute_review_articles_subscore(pubmed_data: dict | None) -> float:
    """Review articles sub-score: 0-3 points.

    Reviews and meta-analyses count.
    - 0: No reviews
    - 1: 1 review
    - 2: 2-5 reviews
    - 3: >5 reviews
    """
    if not pubmed_data:
        return 0.0

    count = pubmed_data.get("review_count", 0)

    if count > 5:
        return round(3.0, 2)
    elif count >= 2:
        return round(2.0, 2)
    elif count >= 1:
        return round(1.0, 2)
    return 0.0


def compute_publication_trend_subscore(pubmed_data: dict | None) -> float:
    """Publication trend sub-score: 0-3 points.

    Year-over-year growth analysis.
    - 0: Declining
    - 1: Stable
    - 2: Growing
    - 3: Rapid growth
    """
    if not pubmed_data:
        return 0.0

    yearly_counts = pubmed_data.get("yearly_counts", [])
    if len(yearly_counts) < 2:
        return round(1.0, 2) if yearly_counts else 0.0

    # Compare recent to older publications
    recent = yearly_counts[-1] if yearly_counts else 0
    earlier = yearly_counts[0] if yearly_counts else 0

    if earlier == 0:
        return round(2.0, 2) if recent > 0 else 0.0

    growth_ratio = recent / earlier

    if growth_ratio >= 2.0:
        return round(3.0, 2)
    elif growth_ratio >= 1.2:
        return round(2.0, 2)
    elif growth_ratio >= 0.8:
        return round(1.0, 2)
    return 0.0
