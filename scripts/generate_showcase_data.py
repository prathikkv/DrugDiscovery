#!/usr/bin/env python3
"""Generate pre-cached JSON data for all 6 pharma showcase scenarios.

Creates 24 JSON files (4 per scenario x 6 scenarios) in data/showcase_scenarios/.
Each file matches the project's data model schemas and contains scientifically
plausible synthetic data suitable for a VP demo.

Usage:
    python scripts/generate_showcase_data.py
"""

import json
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Output directory ─────────────────────────────────────────────────
SCENARIOS_DIR = Path("data/showcase_scenarios")

# ── Timestamps ───────────────────────────────────────────────────────
NOW_ISO = datetime.now(timezone.utc).isoformat()
NOW_EPOCH = time.time()


def sha256_hash(data: str) -> str:
    """Compute SHA256 hex digest of a string."""
    return hashlib.sha256(data.encode()).hexdigest()


# ═════════════════════════════════════════════════════════════════════
# SCENARIO DEFINITIONS
# ═════════════════════════════════════════════════════════════════════

SCENARIOS = {
    "egfr": {
        "gene_symbol": "EGFR",
        "canonical_symbol": "EGFR",
        "ensembl_id": "ENSG00000146648",
        "uniprot_accession": "P00533",
        "disease_context": "Non-Small Cell Lung Cancer",
        "tissue_type": "lung",
        "composite_score": 82.5,
        "verdict_level": "GO",
        "verdict_rationale": "EGFR is a gold-standard oncology target with extensive clinical validation across multiple NSCLC subtypes. Strong genetic evidence from activating mutations (L858R, exon 19 deletions), four FDA-approved TKIs, and robust clinical trial data support a GO recommendation.",
        "forced_conditional": False,
        "dimension_violations": [],
        "drugs": ["erlotinib", "gefitinib", "osimertinib", "afatinib"],
        "mutations": ["L858R", "T790M", "C797S", "exon 19 deletion", "exon 20 insertion"],
    },
    "esr1": {
        "gene_symbol": "ESR1",
        "canonical_symbol": "ESR1",
        "ensembl_id": "ENSG00000091831",
        "uniprot_accession": "P03372",
        "disease_context": "ER-positive Breast Cancer",
        "tissue_type": "tumor",
        "composite_score": 74.3,
        "verdict_level": "GO",
        "verdict_rationale": "ESR1 is a well-validated therapeutic target in ER-positive breast cancer with multiple approved endocrine therapies. ESR1 mutations (Y537S, D538G) drive endocrine resistance, creating opportunities for next-generation SERDs like elacestrant.",
        "forced_conditional": False,
        "dimension_violations": [],
        "drugs": ["tamoxifen", "fulvestrant", "elacestrant", "anastrozole"],
        "mutations": ["Y537S", "D538G", "E380Q", "L536R"],
    },
    "pik3ca": {
        "gene_symbol": "PIK3CA",
        "canonical_symbol": "PIK3CA",
        "ensembl_id": "ENSG00000121879",
        "uniprot_accession": "P42336",
        "disease_context": "HR-positive Breast Cancer",
        "tissue_type": "tumor",
        "composite_score": 71.0,
        "verdict_level": "GO",
        "verdict_rationale": "PIK3CA mutations occur in approximately 40% of HR+/HER2- breast cancers. Alpelisib (Piqray) received FDA approval based on SOLAR-1 trial results. Toxicity management (hyperglycemia) remains a clinical consideration but does not preclude GO recommendation.",
        "forced_conditional": False,
        "dimension_violations": [],
        "drugs": ["alpelisib", "inavolisib", "taselisib", "copanlisib"],
        "mutations": ["H1047R", "E545K", "E542K", "C420R"],
    },
    "glp1r": {
        "gene_symbol": "GLP1R",
        "canonical_symbol": "GLP1R",
        "ensembl_id": "ENSG00000112164",
        "uniprot_accession": "P43220",
        "disease_context": "Obesity",
        "tissue_type": "adipose",
        "composite_score": 78.8,
        "verdict_level": "GO",
        "verdict_rationale": "GLP-1 receptor agonists represent a breakthrough class in metabolic disease. Semaglutide and tirzepatide have demonstrated sustained weight loss of 15-22% in Phase 3 trials. Strong safety profile and massive market opportunity support GO despite competitive landscape intensity.",
        "forced_conditional": False,
        "dimension_violations": [],
        "drugs": ["semaglutide", "tirzepatide", "liraglutide", "exenatide"],
        "mutations": [],
    },
    "parp1": {
        "gene_symbol": "PARP1",
        "canonical_symbol": "PARP1",
        "ensembl_id": "ENSG00000143799",
        "uniprot_accession": "P09874",
        "disease_context": "BRCA-mutant Breast Cancer",
        "tissue_type": "tumor",
        "composite_score": 73.5,
        "verdict_level": "GO",
        "verdict_rationale": "PARP inhibition exploits synthetic lethality in BRCA1/2-mutant cancers. Olaparib (Lynparza) and three additional PARPi have FDA approval. Resistance mechanisms (53BP1 loss, BRCA reversion mutations) present challenges but biomarker-selected populations show durable responses.",
        "forced_conditional": False,
        "dimension_violations": [],
        "drugs": ["olaparib", "niraparib", "rucaparib", "talazoparib"],
        "mutations": [],
    },
    "cd274": {
        "gene_symbol": "CD274",
        "canonical_symbol": "CD274",
        "ensembl_id": "ENSG00000120217",
        "uniprot_accession": "Q9NZQ7",
        "disease_context": "Pan-cancer",
        "tissue_type": "tumor",
        "composite_score": 62.4,
        "verdict_level": "CONDITIONAL",
        "verdict_rationale": "PD-L1/CD274 is a validated immuno-oncology target but faces extreme competitive pressure with 5+ approved agents. Biomarker complexity (TPS vs CPS vs IC scoring), variable response rates across tumor types, and the crowded checkpoint inhibitor landscape drive a CONDITIONAL recommendation. Differentiation strategy required.",
        "forced_conditional": False,
        "dimension_violations": ["competitive_landscape"],
        "drugs": ["pembrolizumab", "atezolizumab", "durvalumab", "avelumab", "nivolumab"],
        "mutations": [],
    },
}


# ═════════════════════════════════════════════════════════════════════
# EVIDENCE GENERATION
# ═════════════════════════════════════════════════════════════════════

def _make_opentargets(scenario: dict) -> dict:
    """Generate OpenTargets evidence source data."""
    gene = scenario["gene_symbol"]
    disease = scenario["disease_context"]

    base_associations = [
        {"disease_name": disease, "score": 0.92, "data_types": ["genetic_association", "known_drug", "literature"]},
        {"disease_name": f"{disease} (subtype)", "score": 0.78, "data_types": ["genetic_association", "somatic_mutation"]},
        {"disease_name": "Cancer (general)", "score": 0.65, "data_types": ["literature", "rna_expression"]},
        {"disease_name": "Neoplasm", "score": 0.55, "data_types": ["genetic_association"]},
    ]

    if gene == "EGFR":
        base_associations.extend([
            {"disease_name": "Glioblastoma multiforme", "score": 0.85, "data_types": ["genetic_association", "known_drug"]},
            {"disease_name": "Colorectal carcinoma", "score": 0.72, "data_types": ["known_drug", "literature"]},
            {"disease_name": "Head and neck squamous cell carcinoma", "score": 0.68, "data_types": ["known_drug"]},
            {"disease_name": "Pancreatic carcinoma", "score": 0.45, "data_types": ["literature"]},
        ])
    elif gene == "GLP1R":
        base_associations = [
            {"disease_name": "Obesity", "score": 0.95, "data_types": ["genetic_association", "known_drug", "literature"]},
            {"disease_name": "Type 2 Diabetes Mellitus", "score": 0.92, "data_types": ["genetic_association", "known_drug"]},
            {"disease_name": "Non-alcoholic fatty liver disease", "score": 0.58, "data_types": ["literature"]},
            {"disease_name": "Cardiovascular disease", "score": 0.52, "data_types": ["literature", "known_drug"]},
        ]

    overall_score = max(a["score"] for a in base_associations)

    return {
        "confidence": 1.0 if gene in ("EGFR", "GLP1R") else 0.95,
        "data": {
            "associations": base_associations,
            "overall_score": round(overall_score, 2),
            "target_id": f"ENSG{'0' * (15 - len(scenario['ensembl_id'].replace('ENSG', '')))}{scenario['ensembl_id'].replace('ENSG', '')}",
            "approved_symbol": gene,
        },
        "error": None,
        "is_fallback": False,
    }


def _make_dgidb(scenario: dict) -> dict:
    """Generate DGIdb drug-gene interaction data."""
    drugs = scenario["drugs"]
    interactions = []
    for i, drug in enumerate(drugs):
        interactions.append({
            "drug_name": drug.capitalize(),
            "interaction_types": ["inhibitor"] if i % 2 == 0 else ["antagonist"],
            "score": round(0.95 - i * 0.08, 2),
            "pmids": [str(30000000 + i * 1000 + j) for j in range(3)],
        })

    return {
        "confidence": 1.0,
        "data": {
            "gene_name": scenario["gene_symbol"],
            "interactions": interactions,
            "interaction_count": len(interactions),
            "categories": ["DRUGGABLE GENOME", "CLINICALLY ACTIONABLE"],
        },
        "error": None,
        "is_fallback": False,
    }


def _make_pubmed(scenario: dict) -> dict:
    """Generate PubMed literature evidence."""
    gene = scenario["gene_symbol"]
    disease = scenario["disease_context"]

    paper_templates = [
        {
            "pmid": "35000001",
            "title": f"Molecular mechanisms of {gene} in {disease}: a comprehensive review",
            "journal": "Nature Reviews Cancer",
            "year": 2024,
            "citations": 156,
        },
        {
            "pmid": "35000002",
            "title": f"Clinical outcomes of {gene}-targeted therapy in advanced {disease}",
            "journal": "Journal of Clinical Oncology",
            "year": 2023,
            "citations": 89,
        },
        {
            "pmid": "35000003",
            "title": f"Biomarker-driven patient selection for {gene} inhibitors",
            "journal": "The Lancet Oncology",
            "year": 2024,
            "citations": 72,
        },
        {
            "pmid": "35000004",
            "title": f"Resistance mechanisms to {gene}-directed therapies: current understanding and future directions",
            "journal": "Cancer Discovery",
            "year": 2023,
            "citations": 145,
        },
        {
            "pmid": "35000005",
            "title": f"Next-generation {gene} modulators: structure-activity relationships and selectivity profiles",
            "journal": "Journal of Medicinal Chemistry",
            "year": 2024,
            "citations": 48,
        },
        {
            "pmid": "35000006",
            "title": f"Real-world evidence for {gene} inhibitor efficacy in {disease}",
            "journal": "Annals of Oncology",
            "year": 2023,
            "citations": 67,
        },
        {
            "pmid": "35000007",
            "title": f"Combination strategies targeting {gene} and immune checkpoint pathways",
            "journal": "Nature Medicine",
            "year": 2024,
            "citations": 112,
        },
    ]

    # EGFR gets more papers
    if gene == "EGFR":
        paper_templates.extend([
            {
                "pmid": "35000008",
                "title": "Osimertinib in T790M-positive NSCLC: 5-year follow-up of AURA3",
                "journal": "New England Journal of Medicine",
                "year": 2024,
                "citations": 234,
            },
            {
                "pmid": "35000009",
                "title": "EGFR exon 20 insertion mutations: emerging therapeutic landscape",
                "journal": "Clinical Cancer Research",
                "year": 2023,
                "citations": 98,
            },
            {
                "pmid": "35000010",
                "title": "Liquid biopsy for EGFR mutation detection in NSCLC: systematic review",
                "journal": "JAMA Oncology",
                "year": 2024,
                "citations": 187,
            },
        ])

    total_count = 250 if gene == "EGFR" else 120 if gene in ("ESR1", "PARP1") else 85

    return {
        "confidence": 0.95 if gene == "EGFR" else 0.85,
        "data": {
            "papers": paper_templates,
            "total_count": total_count,
            "query": f"{gene} AND {disease}",
            "ai_summary": (
                f"{gene} is extensively studied in the context of {disease}. "
                f"The literature supports strong target validation with {total_count}+ publications "
                f"spanning mechanistic studies, clinical trials, and resistance biology."
            ),
        },
        "error": None,
        "is_fallback": False,
    }


def _make_clinicaltrials(scenario: dict) -> dict:
    """Generate ClinicalTrials.gov evidence."""
    gene = scenario["gene_symbol"]
    disease = scenario["disease_context"]
    drugs = scenario["drugs"]

    phases = ["Phase 1", "Phase 1/Phase 2", "Phase 2", "Phase 3", "Phase 4"]
    statuses = ["RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING"]

    trials = []
    for i, drug in enumerate(drugs):
        for j, phase in enumerate(phases[:3 + (i == 0)]):
            trial = {
                "nct_id": f"NCT0{5000000 + i * 100 + j}",
                "title": f"A {phase} Study of {drug.capitalize()} in Patients with {disease}",
                "phase": phase,
                "status": statuses[j % len(statuses)],
                "enrollment": 150 + i * 80 + j * 50,
                "start_date": f"202{2 + j}-{(i + j) % 12 + 1:02d}-01",
                "sponsor": "AstraZeneca" if gene in ("EGFR", "ESR1") else "Roche" if gene == "PIK3CA" else "Eli Lilly" if gene == "GLP1R" else "Merck",
            }
            trials.append(trial)

    # EGFR gets many more trials
    if gene == "EGFR":
        for k in range(8):
            trials.append({
                "nct_id": f"NCT0{6000000 + k}",
                "title": f"Combination {drugs[0].capitalize()} with immunotherapy in EGFR-mutant NSCLC (Study {k+1})",
                "phase": phases[k % 4],
                "status": statuses[k % 3],
                "enrollment": 200 + k * 60,
                "start_date": f"2024-{k % 12 + 1:02d}-15",
                "sponsor": "AstraZeneca",
            })

    total_count = 55 if gene == "EGFR" else 35 if gene in ("ESR1", "PARP1", "GLP1R") else 20

    return {
        "confidence": 0.9,
        "data": {
            "trials": trials,
            "total_count": total_count,
            "query_terms": [gene] + drugs[:2],
        },
        "error": None,
        "is_fallback": False,
    }


def _make_uniprot(scenario: dict) -> dict:
    """Generate UniProt protein data."""
    gene = scenario["gene_symbol"]

    protein_names = {
        "EGFR": "Epidermal growth factor receptor",
        "ESR1": "Estrogen receptor",
        "PIK3CA": "Phosphatidylinositol 4,5-bisphosphate 3-kinase catalytic subunit alpha isoform",
        "GLP1R": "Glucagon-like peptide 1 receptor",
        "PARP1": "Poly [ADP-ribose] polymerase 1",
        "CD274": "Programmed cell death 1 ligand 1",
    }

    protein_lengths = {
        "EGFR": 1210, "ESR1": 595, "PIK3CA": 1068,
        "GLP1R": 463, "PARP1": 1014, "CD274": 290,
    }

    protein_functions = {
        "EGFR": "Receptor tyrosine kinase that activates downstream RAS-MAPK and PI3K-AKT signaling. Essential for cell proliferation, differentiation, and survival. Activating mutations drive oncogenesis in NSCLC.",
        "ESR1": "Nuclear hormone receptor that mediates estrogen signaling. Acts as transcription factor regulating genes involved in cell proliferation. Mutations in ligand-binding domain confer endocrine resistance.",
        "PIK3CA": "Catalytic subunit of PI3K that phosphorylates PtdIns(4,5)P2 to generate PtdIns(3,4,5)P3. Hotspot mutations (H1047R, E545K) constitutively activate AKT-mTOR signaling.",
        "GLP1R": "G protein-coupled receptor for glucagon-like peptide-1. Stimulates insulin secretion, inhibits glucagon release, slows gastric emptying, and promotes satiety.",
        "PARP1": "Nuclear enzyme catalyzing poly(ADP-ribosyl)ation of target proteins. Essential for DNA single-strand break repair via base excision repair pathway. Inhibition is synthetically lethal with BRCA1/2 deficiency.",
        "CD274": "Type I transmembrane protein that binds PD-1 receptor on T cells. Engagement delivers inhibitory signal suppressing T cell activation. Tumor expression enables immune evasion.",
    }

    subcellular = {
        "EGFR": ["Cell membrane", "Cytoplasm", "Nucleus"],
        "ESR1": ["Nucleus", "Cytoplasm"],
        "PIK3CA": ["Cytoplasm", "Cell membrane"],
        "GLP1R": ["Cell membrane"],
        "PARP1": ["Nucleus"],
        "CD274": ["Cell membrane"],
    }

    return {
        "confidence": 0.95,
        "data": {
            "accession": scenario["uniprot_accession"],
            "protein_name": protein_names.get(gene, gene),
            "gene_name": gene,
            "organism": "Homo sapiens (Human)",
            "length": protein_lengths.get(gene, 500),
            "function": protein_functions.get(gene, ""),
            "subcellular_location": subcellular.get(gene, ["Unknown"]),
            "pdb_structures": ["6JXT", "5UG9"] if gene == "EGFR" else ["1ERE"] if gene == "ESR1" else [],
            "sequence_status": "Complete",
        },
        "error": None,
        "is_fallback": False,
    }


def _make_chembl(scenario: dict) -> dict:
    """Generate ChEMBL compound data."""
    drugs = scenario["drugs"]
    gene = scenario["gene_symbol"]

    compounds = []
    for i, drug in enumerate(drugs):
        compounds.append({
            "molecule_chembl_id": f"CHEMBL{100000 + i * 1000}",
            "pref_name": drug.upper(),
            "max_phase": 4 if i < 2 else 3,
            "molecule_type": "Small molecule" if gene != "GLP1R" else "Peptide",
            "first_approval": 2003 + i * 4 if i < 2 else None,
            "oral_bioavailability": True if gene != "GLP1R" else False,
            "target_type": "SINGLE PROTEIN",
            "activity_type": "IC50" if gene != "GLP1R" else "EC50",
            "activity_value_nm": round(0.5 + i * 2.3, 1),
        })

    return {
        "confidence": 0.9,
        "data": {
            "target_chembl_id": f"CHEMBL{200 + hash(gene) % 1000}",
            "target_name": gene,
            "compounds": compounds,
            "compound_count": len(compounds),
            "max_phase_reached": 4,
        },
        "error": None,
        "is_fallback": False,
    }


def generate_evidence(scenario_key: str, scenario: dict) -> dict:
    """Generate complete evidence.json for a scenario."""
    return {
        "gene": {
            "canonical_symbol": scenario["canonical_symbol"],
            "ensembl_id": scenario["ensembl_id"],
            "uniprot_accession": scenario["uniprot_accession"],
            "query_symbol": scenario["gene_symbol"],
        },
        "disease_context": scenario["disease_context"],
        "results": {
            "opentargets": _make_opentargets(scenario),
            "dgidb": _make_dgidb(scenario),
            "pubmed": _make_pubmed(scenario),
            "clinicaltrials": _make_clinicaltrials(scenario),
            "uniprot": _make_uniprot(scenario),
            "chembl": _make_chembl(scenario),
        },
        "fetched_at": NOW_EPOCH,
        "sources_available": 6,
        "sources_failed": 0,
    }


# ═════════════════════════════════════════════════════════════════════
# SCORING GENERATION
# ═════════════════════════════════════════════════════════════════════

def _dimension_scores(scenario: dict) -> list[dict]:
    """Generate 7 dimension scores for a scenario."""
    gene = scenario["gene_symbol"]
    composite = scenario["composite_score"]

    # Base dimension profiles per scenario type
    profiles = {
        "EGFR": {
            "genetic_evidence": (13.5, 15.0),
            "expression_biology": (12.8, 15.0),
            "druggability": (14.0, 15.0),
            "safety_selectivity": (11.5, 15.0),
            "competitive_landscape": (10.0, 15.0),
            "clinical_translational": (13.5, 15.0),
            "literature_consensus": (8.5, 10.0),
        },
        "ESR1": {
            "genetic_evidence": (11.5, 15.0),
            "expression_biology": (11.0, 15.0),
            "druggability": (12.5, 15.0),
            "safety_selectivity": (10.0, 15.0),
            "competitive_landscape": (9.0, 15.0),
            "clinical_translational": (12.5, 15.0),
            "literature_consensus": (7.8, 10.0),
        },
        "PIK3CA": {
            "genetic_evidence": (12.0, 15.0),
            "expression_biology": (10.5, 15.0),
            "druggability": (11.0, 15.0),
            "safety_selectivity": (8.5, 15.0),
            "competitive_landscape": (10.0, 15.0),
            "clinical_translational": (11.5, 15.0),
            "literature_consensus": (7.5, 10.0),
        },
        "GLP1R": {
            "genetic_evidence": (10.5, 15.0),
            "expression_biology": (12.0, 15.0),
            "druggability": (13.5, 15.0),
            "safety_selectivity": (13.0, 15.0),
            "competitive_landscape": (9.5, 15.0),
            "clinical_translational": (13.0, 15.0),
            "literature_consensus": (7.3, 10.0),
        },
        "PARP1": {
            "genetic_evidence": (11.0, 15.0),
            "expression_biology": (10.5, 15.0),
            "druggability": (12.5, 15.0),
            "safety_selectivity": (10.5, 15.0),
            "competitive_landscape": (9.5, 15.0),
            "clinical_translational": (12.0, 15.0),
            "literature_consensus": (7.5, 10.0),
        },
        "CD274": {
            "genetic_evidence": (8.5, 15.0),
            "expression_biology": (9.0, 15.0),
            "druggability": (11.0, 15.0),
            "safety_selectivity": (9.5, 15.0),
            "competitive_landscape": (5.5, 15.0),  # Low - extremely competitive
            "clinical_translational": (12.5, 15.0),
            "literature_consensus": (6.4, 10.0),
        },
    }

    profile = profiles[gene]

    # Sub-score templates per dimension
    sub_score_templates = {
        "genetic_evidence": [
            ("gwas_associations", "GWAS/genetic association signals"),
            ("somatic_mutations", "Somatic mutation frequency and recurrence"),
            ("causal_evidence", "Causal evidence from functional studies"),
        ],
        "expression_biology": [
            ("disease_expression", "Differential expression in disease tissue"),
            ("pathway_centrality", "Pathway centrality and network position"),
            ("biological_plausibility", "Biological mechanism plausibility"),
        ],
        "druggability": [
            ("binding_site_quality", "Drug binding site accessibility and quality"),
            ("existing_compounds", "Number and quality of existing drug compounds"),
            ("modality_options", "Available therapeutic modality options"),
        ],
        "safety_selectivity": [
            ("off_target_risk", "Off-target binding risk assessment"),
            ("essential_gene_risk", "Essential gene/viability risk"),
            ("therapeutic_window", "Predicted therapeutic window"),
        ],
        "competitive_landscape": [
            ("market_exclusivity", "Market exclusivity and IP position"),
            ("competitor_count", "Number of competing programs"),
            ("differentiation_potential", "Differentiation potential"),
        ],
        "clinical_translational": [
            ("clinical_precedent", "Clinical precedent and trial success rates"),
            ("biomarker_availability", "Biomarker availability for patient selection"),
            ("regulatory_path", "Regulatory pathway clarity"),
        ],
        "literature_consensus": [
            ("publication_volume", "Publication volume and citation impact"),
            ("expert_consensus", "Expert consensus and review articles"),
        ],
    }

    dimensions = []
    for dim_name, (score, max_score) in profile.items():
        templates = sub_score_templates[dim_name]
        sub_count = len(templates)
        sub_scores = []
        for idx, (sub_name, sub_desc) in enumerate(templates):
            sub_max = round(max_score / sub_count, 1)
            sub_val = round(score / sub_count + (0.3 if idx == 0 else -0.1 * idx), 2)
            sub_val = max(0.0, min(sub_val, sub_max))
            sub_scores.append({
                "name": sub_name,
                "value": sub_val,
                "max_value": sub_max,
                "description": sub_desc,
                "data_source": "opentargets" if "genetic" in dim_name else "dgidb" if "drug" in dim_name else "pubmed",
            })

        data_coverage = round(min(1.0, score / max_score + 0.1), 2)
        data_coverage = min(1.0, data_coverage)

        dimensions.append({
            "name": dim_name,
            "score": score,
            "max_score": max_score,
            "sub_scores": sub_scores,
            "data_coverage": data_coverage,
        })

    return dimensions


def generate_scoring(scenario_key: str, scenario: dict) -> dict:
    """Generate complete scoring.json for a scenario."""
    dimensions = _dimension_scores(scenario)
    evidence_hash = sha256_hash(f"{scenario['gene_symbol']}_{scenario['disease_context']}_{NOW_ISO}")

    return {
        "gene_symbol": scenario["gene_symbol"],
        "disease_context": scenario["disease_context"],
        "composite": {
            "score": scenario["composite_score"],
            "dimension_scores": dimensions,
            "weights": {
                "genetic_evidence": 15.0,
                "expression_biology": 15.0,
                "druggability": 15.0,
                "safety_selectivity": 15.0,
                "competitive_landscape": 15.0,
                "clinical_translational": 15.0,
                "literature_consensus": 10.0,
            },
            "formula_version": "v1.0",
        },
        "verdict": {
            "level": scenario["verdict_level"],
            "score": scenario["composite_score"],
            "dimension_violations": scenario["dimension_violations"],
            "forced_conditional": scenario["forced_conditional"],
            "rationale": scenario["verdict_rationale"],
        },
        "evidence_hash": evidence_hash,
        "scored_at": NOW_ISO,
    }


# ═════════════════════════════════════════════════════════════════════
# REASONING GENERATION
# ═════════════════════════════════════════════════════════════════════

def _make_claims(gene: str, disease: str, mode: str) -> list[dict]:
    """Generate realistic claims for a reasoning mode."""
    claim_templates = {
        "hypothesis": [
            {
                "text": f"{gene} inhibition may be synergistic with immune checkpoint blockade in {disease} due to shared downstream signaling pathways.",
                "confidence": 0.75,
                "sources": ["PubMed", "OpenTargets"],
            },
            {
                "text": f"Patients with {gene} alterations may respond differentially to combination therapies based on co-mutation status.",
                "confidence": 0.82,
                "sources": ["ClinicalTrials", "PubMed"],
            },
            {
                "text": f"Resistance to {gene}-targeted therapy may be overcome by targeting compensatory pathway activation.",
                "confidence": 0.68,
                "sources": ["PubMed", "ChEMBL"],
            },
            {
                "text": f"Liquid biopsy monitoring of {gene} status could enable adaptive treatment strategies.",
                "confidence": 0.71,
                "sources": ["PubMed", "ClinicalTrials"],
            },
        ],
        "synthesis": [
            {
                "text": f"Across 6 evidence sources, {gene} demonstrates strong target validation in {disease} with convergent genetic, pharmacological, and clinical evidence.",
                "confidence": 0.9,
                "sources": ["OpenTargets", "DGIdb", "PubMed", "ClinicalTrials"],
            },
            {
                "text": f"Drug-gene interaction data confirms multiple approved agents targeting {gene}, with established dose-response relationships.",
                "confidence": 0.88,
                "sources": ["DGIdb", "ChEMBL"],
            },
            {
                "text": f"Clinical trial landscape shows active investigation across multiple disease settings beyond {disease}.",
                "confidence": 0.85,
                "sources": ["ClinicalTrials", "PubMed"],
            },
        ],
        "contradiction": [
            {
                "text": f"While {gene} shows strong efficacy signals, safety data reveals dose-limiting toxicities in some patient subgroups.",
                "confidence": 0.72,
                "sources": ["ClinicalTrials", "PubMed"],
            },
            {
                "text": f"Preclinical models overestimate {gene} inhibitor efficacy compared to clinical response rates, suggesting incomplete target biology understanding.",
                "confidence": 0.65,
                "sources": ["PubMed", "ChEMBL"],
            },
            {
                "text": f"Some literature reports conflicting results on {gene} expression as a predictive biomarker versus prognostic marker.",
                "confidence": 0.6,
                "sources": ["PubMed", "OpenTargets"],
            },
        ],
        "gap": [
            {
                "text": f"Limited data on {gene} target engagement biomarkers for real-time monitoring of drug efficacy.",
                "confidence": 0.78,
                "sources": ["ClinicalTrials", "PubMed"],
            },
            {
                "text": f"Insufficient long-term safety data beyond 3-year follow-up for newer {gene}-targeted agents.",
                "confidence": 0.7,
                "sources": ["ClinicalTrials"],
            },
            {
                "text": f"Pediatric population data for {gene} inhibitors is notably absent.",
                "confidence": 0.82,
                "sources": ["ClinicalTrials", "PubMed"],
            },
        ],
        "confidence": [
            {
                "text": f"High confidence in {gene} as a validated target based on convergent multi-source evidence and clinical success.",
                "confidence": 0.88,
                "sources": ["OpenTargets", "DGIdb", "PubMed", "ClinicalTrials", "UniProt", "ChEMBL"],
            },
            {
                "text": f"Moderate confidence in differentiation opportunity given competitive landscape complexity.",
                "confidence": 0.65,
                "sources": ["ClinicalTrials", "ChEMBL"],
            },
            {
                "text": f"Data coverage is strong across all 6 evidence sources, supporting robust assessment.",
                "confidence": 0.85,
                "sources": ["OpenTargets", "DGIdb", "PubMed", "ClinicalTrials", "UniProt", "ChEMBL"],
            },
        ],
    }

    return claim_templates.get(mode, claim_templates["hypothesis"])


def generate_reasoning(scenario_key: str, scenario: dict) -> dict:
    """Generate complete reasoning.json for a scenario (mode_name -> ReasoningResult dict)."""
    gene = scenario["gene_symbol"]
    disease = scenario["disease_context"]

    modes = ["hypothesis", "synthesis", "contradiction", "gap", "confidence"]
    summaries = {
        "hypothesis": f"Generated 4 testable hypotheses for {gene} in {disease}, focusing on combination strategies, resistance mechanisms, and biomarker-driven treatment adaptation.",
        "synthesis": f"Synthesized evidence from 6 sources confirming strong target validation for {gene} in {disease}. Convergent genetic, pharmacological, and clinical data support therapeutic development.",
        "contradiction": f"Identified 3 areas of conflicting evidence regarding {gene} efficacy predictions, safety profiles, and biomarker utility in {disease}.",
        "gap": f"Flagged 3 key evidence gaps for {gene} in {disease}: target engagement biomarkers, long-term safety data, and pediatric population coverage.",
        "confidence": f"Overall confidence assessment for {gene} in {disease} is {'high' if scenario['verdict_level'] == 'GO' else 'moderate'}. Multi-source convergence is strong with {'no' if not scenario['dimension_violations'] else 'some'} significant dimension violations.",
    }

    result = {}
    for mode in modes:
        claims = _make_claims(gene, disease, mode)
        result[mode] = {
            "mode": mode,
            "gene_symbol": gene,
            "disease_context": disease,
            "claims": claims,
            "summary": summaries[mode],
            "raw_output": f"[AI Reasoning Output for {gene}/{disease} - {mode} mode]\n\n{summaries[mode]}\n\nKey findings:\n" + "\n".join(f"- {c['text']}" for c in claims),
            "tool_trace": {
                "rounds": [],
                "tool_calls": [],
                "total_rounds": 0,
                "final_text": summaries[mode],
            },
            "hallucination_issues": [],
            "created_at": NOW_ISO,
        }

    return result


# ═════════════════════════════════════════════════════════════════════
# PIPELINE REPORT GENERATION
# ═════════════════════════════════════════════════════════════════════

def generate_pipeline_report(scenario_key: str, scenario: dict) -> dict:
    """Generate minimal pipeline_report.json for a scenario."""
    gene = scenario["gene_symbol"]
    tissue = scenario["tissue_type"]

    # Tissue-specific cell counts and metrics
    cell_counts = {
        "lung": 5200, "tumor": 4800, "adipose": 3500,
    }
    gene_counts = {
        "lung": 22000, "tumor": 20500, "adipose": 18000,
    }
    mito_pcts = {
        "lung": 8.2, "tumor": 12.5, "adipose": 6.8,
    }

    n_cells = cell_counts.get(tissue, 4000)
    n_genes = gene_counts.get(tissue, 19000)
    mito_pct = mito_pcts.get(tissue, 10.0)

    return {
        "gene_symbol": gene,
        "tissue_type": tissue,
        "qc_metrics": {
            "n_cells_pre_qc": n_cells + 1200,
            "n_cells_post_qc": n_cells,
            "n_genes_detected": n_genes,
            "median_genes_per_cell": int(n_genes * 0.15),
            "median_counts_per_cell": int(n_genes * 0.8),
            "pct_mito_mean": mito_pct,
            "pct_mito_threshold": 20.0,
            "doublet_rate": 4.2,
        },
        "cell_type_annotations": {
            "method": "CellTypist",
            "model": f"Human_{tissue.capitalize()}_Atlas",
            "n_cell_types": 8 if tissue == "tumor" else 6,
            "top_cell_types": [
                {"name": "Epithelial cells", "count": int(n_cells * 0.35), "fraction": 0.35},
                {"name": "T cells", "count": int(n_cells * 0.2), "fraction": 0.2},
                {"name": "Macrophages", "count": int(n_cells * 0.15), "fraction": 0.15},
                {"name": "Fibroblasts", "count": int(n_cells * 0.12), "fraction": 0.12},
                {"name": "Endothelial cells", "count": int(n_cells * 0.08), "fraction": 0.08},
            ],
        },
        "differential_expression": {
            "method": "Wilcoxon rank-sum",
            "n_comparisons": 5,
            "significant_genes": {
                "total": 450,
                "upregulated": 280,
                "downregulated": 170,
            },
            "target_gene_de": {
                "gene": gene,
                "log2fc": 2.8 if gene != "CD274" else 1.2,
                "pval_adj": 1.5e-12 if gene != "CD274" else 3.2e-4,
                "in_top_50": True if gene != "CD274" else False,
            },
        },
        "pipeline_version": "v1.0",
        "completed_at": NOW_ISO,
    }


# ═════════════════════════════════════════════════════════════════════
# MAIN GENERATION
# ═════════════════════════════════════════════════════════════════════

def main():
    """Generate all 24 JSON files for 6 showcase scenarios."""
    print("Generating showcase scenario data...")
    print(f"Output directory: {SCENARIOS_DIR.resolve()}")
    print()

    total_files = 0

    for scenario_key, scenario in SCENARIOS.items():
        scenario_dir = SCENARIOS_DIR / scenario_key
        scenario_dir.mkdir(parents=True, exist_ok=True)

        gene = scenario["gene_symbol"]
        disease = scenario["disease_context"]
        print(f"  [{gene}/{disease}]")

        # Generate each data file
        generators = {
            "evidence": generate_evidence,
            "reasoning": generate_reasoning,
            "scoring": generate_scoring,
            "pipeline_report": generate_pipeline_report,
        }

        for file_name, generator in generators.items():
            data = generator(scenario_key, scenario)
            file_path = scenario_dir / f"{file_name}.json"
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
            total_files += 1
            print(f"    -> {file_name}.json ({file_path.stat().st_size:,} bytes)")

        print()

    print(f"Done. Generated {total_files} files across {len(SCENARIOS)} scenarios.")

    # Verification
    print("\nVerification:")
    missing = []
    for scenario_key in SCENARIOS:
        for file_name in ["evidence", "reasoning", "scoring", "pipeline_report"]:
            path = SCENARIOS_DIR / scenario_key / f"{file_name}.json"
            if not path.exists():
                missing.append(f"{scenario_key}/{file_name}.json")
            else:
                # Validate JSON
                with open(path) as f:
                    json.load(f)

    if missing:
        print(f"  MISSING: {missing}")
    else:
        print("  All 24 files exist and contain valid JSON.")

    # Check verdict requirements
    egfr_scoring = json.load(open(SCENARIOS_DIR / "egfr" / "scoring.json"))
    cd274_scoring = json.load(open(SCENARIOS_DIR / "cd274" / "scoring.json"))

    egfr_score = egfr_scoring["composite"]["score"]
    egfr_verdict = egfr_scoring["verdict"]["level"]
    cd274_score = cd274_scoring["composite"]["score"]
    cd274_verdict = cd274_scoring["verdict"]["level"]

    print(f"\n  EGFR: score={egfr_score}, verdict={egfr_verdict} {'PASS' if egfr_score >= 75 and egfr_verdict == 'GO' else 'FAIL'}")
    print(f"  CD274: score={cd274_score}, verdict={cd274_verdict} {'PASS' if 55 <= cd274_score <= 70 and cd274_verdict == 'CONDITIONAL' else 'FAIL'}")


if __name__ == "__main__":
    main()
