"""GxP validation suite: pharma showcase target retrovalidation (REQ-801).

Validates that the platform correctly scores 6 known drug targets within
expected ranges that reflect their real-world clinical validation status.

NO MOCKING: loads pre-cached data from data/showcase_scenarios/.
"""

import pytest

pytestmark = pytest.mark.validation

# Expected ranges per success criterion SC#1
EXPECTED_RANGES = {
    "egfr":   {"min": 75.0, "max": 100.0, "verdict": "GO",          "label": "NSCLC"},
    "esr1":   {"min": 70.0, "max": 100.0, "verdict": None,           "label": "ER+Breast"},
    "pik3ca": {"min": 68.0, "max": 100.0, "verdict": None,           "label": "HR+Breast"},
    "glp1r":  {"min": 72.0, "max": 100.0, "verdict": None,           "label": "Obesity"},
    "parp1":  {"min": 70.0, "max": 100.0, "verdict": None,           "label": "BRCA+Breast"},
    "cd274":  {"min": 55.0, "max":  70.0, "verdict": "CONDITIONAL",  "label": "Pan-cancer"},
}


@pytest.mark.parametrize("gene", EXPECTED_RANGES.keys())
def test_showcase_score_in_range(gene, showcase_scores):
    """Each showcase target scores within the expected range (SC#1)."""
    scoring = showcase_scores[gene]
    score = scoring["composite"]["score"]
    expected = EXPECTED_RANGES[gene]

    assert expected["min"] <= score <= expected["max"], (
        f"{gene.upper()} ({expected['label']}) scored {score:.1f}, "
        f"expected [{expected['min']}, {expected['max']}]"
    )


@pytest.mark.parametrize("gene,expected_verdict", [
    ("egfr",  "GO"),
    ("cd274", "CONDITIONAL"),
])
def test_showcase_verdict(gene, expected_verdict, showcase_scores):
    """EGFR must be GO and CD274 must be CONDITIONAL (SC#1 explicit verdicts)."""
    verdict = showcase_scores[gene]["verdict"]["level"]
    assert verdict == expected_verdict, (
        f"{gene.upper()} verdict is {verdict!r}, expected {expected_verdict!r}"
    )


def test_egfr_scores_highest_among_showcase(showcase_scores):
    """EGFR ranks #1 among all 6 showcase targets (REQ-801).

    Confirms the platform correctly identifies EGFR as the strongest
    NSCLC candidate among the available showcase targets.
    """
    scores = {
        gene: showcase_scores[gene]["composite"]["score"]
        for gene in EXPECTED_RANGES.keys()
    }
    top_gene = max(scores, key=lambda g: scores[g])
    assert top_gene == "egfr", (
        f"Expected EGFR to rank #1, but {top_gene.upper()} scored highest. "
        f"Scores: {scores}"
    )


def test_cd274_has_dimension_violation(showcase_scores):
    """CD274 CONDITIONAL verdict is driven by competitive_landscape dimension violation."""
    cd274 = showcase_scores["cd274"]
    violations = cd274["verdict"]["dimension_violations"]
    assert "competitive_landscape" in violations, (
        f"Expected competitive_landscape violation for CD274, got: {violations}"
    )


def test_all_showcase_scores_are_deterministic(showcase_scores):
    """All showcase scores have a non-empty evidence_hash (deterministic scoring)."""
    for gene, scoring in showcase_scores.items():
        evidence_hash = scoring.get("evidence_hash", "")
        assert len(evidence_hash) == 64, (
            f"{gene.upper()} evidence_hash is not a 64-char SHA256 hex: {evidence_hash!r}"
        )
