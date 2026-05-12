"""Pre-cached showcase scenario definitions and loader.

Provides 6 pharma-relevant target-disease showcase scenarios with
a loader function that reads pre-cached JSON files from disk.

Usage:
    from src.pages.components.showcase import SHOWCASE_SCENARIOS, load_scenario

    scenarios = list(SHOWCASE_SCENARIOS.keys())
    data = load_scenario("EGFR/NSCLC")  # Returns cached evidence/reasoning/scoring
"""

import json
from pathlib import Path

import streamlit as st


# ── Base directory for cached JSON files ──────────────────────────────

SCENARIOS_DIR = Path("data/showcase_scenarios")


# ── Showcase Scenario Definitions ─────────────────────────────────────

SHOWCASE_SCENARIOS: dict[str, dict] = {
    "EGFR/NSCLC": {
        "gene_symbol": "EGFR",
        "disease_context": "Non-Small Cell Lung Cancer",
        "tissue_type": "lung",
        "company": "AstraZeneca",
        "description": (
            "EGFR-targeted therapy in NSCLC -- gold standard target with "
            "extensive clinical validation (erlotinib, gefitinib, osimertinib)"
        ),
    },
    "ESR1/ER+Breast": {
        "gene_symbol": "ESR1",
        "disease_context": "ER-positive Breast Cancer",
        "tissue_type": "tumor",
        "company": "AstraZeneca",
        "description": (
            "Estrogen receptor in hormone-positive breast cancer -- "
            "fulvestrant/elacestrant target"
        ),
    },
    "PIK3CA/HR+Breast": {
        "gene_symbol": "PIK3CA",
        "disease_context": "HR-positive Breast Cancer",
        "tissue_type": "tumor",
        "company": "Roche",
        "description": (
            "PI3K catalytic subunit alpha -- alpelisib (Piqray) target "
            "for PIK3CA-mutant HR+/HER2- breast cancer"
        ),
    },
    "GLP1R/Obesity": {
        "gene_symbol": "GLP1R",
        "disease_context": "Obesity",
        "tissue_type": "adipose",
        "company": "Eli Lilly",
        "description": (
            "GLP-1 receptor -- semaglutide (Wegovy) and tirzepatide "
            "(Zepbound) target"
        ),
    },
    "PARP1/BRCA+Breast": {
        "gene_symbol": "PARP1",
        "disease_context": "BRCA-mutant Breast Cancer",
        "tissue_type": "tumor",
        "company": "Merck",
        "description": (
            "Poly(ADP-ribose) polymerase 1 -- olaparib (Lynparza) target "
            "in BRCA-mutant cancers"
        ),
    },
    "CD274/Pan-cancer": {
        "gene_symbol": "CD274",
        "disease_context": "Pan-cancer",
        "tissue_type": "tumor",
        "company": "Merck",
        "description": (
            "PD-L1 (programmed death-ligand 1) -- pembrolizumab (Keytruda) "
            "checkpoint immunotherapy target"
        ),
    },
}


def load_scenario(scenario_name: str) -> dict:
    """Load pre-cached JSON files for a showcase scenario.

    Args:
        scenario_name: Key from SHOWCASE_SCENARIOS (e.g. "EGFR/NSCLC").

    Returns:
        Dict with keys:
        - scenario: The metadata dict from SHOWCASE_SCENARIOS
        - evidence: Parsed evidence.json (if exists)
        - reasoning: Parsed reasoning.json (if exists)
        - scoring: Parsed scoring.json (if exists)
        - pipeline_report: Parsed pipeline_report.json (if exists)

    Raises:
        KeyError: If scenario_name is not in SHOWCASE_SCENARIOS.
    """
    if scenario_name not in SHOWCASE_SCENARIOS:
        raise KeyError(
            f"Unknown scenario '{scenario_name}'. "
            f"Valid scenarios: {list(SHOWCASE_SCENARIOS.keys())}"
        )

    scenario_meta = SHOWCASE_SCENARIOS[scenario_name]
    gene = scenario_meta["gene_symbol"]
    scenario_dir = SCENARIOS_DIR / gene.lower()

    result: dict = {"scenario": scenario_meta}

    # Load each JSON file if it exists
    json_files = ["evidence", "reasoning", "scoring", "pipeline_report"]
    for name in json_files:
        file_path = scenario_dir / f"{name}.json"
        if file_path.exists():
            with open(file_path, "r") as f:
                result[name] = json.load(f)

    return result


def get_project_key(key: str) -> str:
    """Build a project-scoped session state key.

    Uses the active_project_id from session_state to namespace keys,
    preventing cross-project state leakage.

    Args:
        key: The base key name (e.g. "selected_gene").

    Returns:
        Namespaced key like "project_abc123_selected_gene".
    """
    project_id = st.session_state.get("active_project_id", "none")
    return f"project_{project_id}_{key}"
