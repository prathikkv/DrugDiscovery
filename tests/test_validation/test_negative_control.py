"""GxP validation: MELK negative control must score NO-GO (REQ-802).

MELK (Maternal Embryonic Leucine Zipper Kinase) is a textbook discredited
target. CRISPR knockout studies (eLife 2017) showed no proliferation effect
in 13 cancer cell lines despite 30+ prior papers claiming therapeutic validity.

NO MOCKING: loads pre-cached data from data/showcase_scenarios/melk/.
"""

import pytest

pytestmark = pytest.mark.validation

MIN_NO_GO_SCORE = 35.0
MAX_NO_GO_SCORE = 45.0


def test_melk_no_go(melk_score):
    """MELK must receive a NO-GO verdict (REQ-802)."""
    verdict = melk_score["verdict"]["level"]
    assert verdict == "NO-GO", (
        f"MELK should be NO-GO (discredited target), got {verdict!r}"
    )


def test_melk_score_in_expected_range(melk_score):
    """MELK composite score must be in the 35-45 range (well below 50 NO-GO boundary)."""
    score = melk_score["composite"]["score"]
    assert MIN_NO_GO_SCORE <= score <= MAX_NO_GO_SCORE, (
        f"MELK scored {score:.1f}, expected [{MIN_NO_GO_SCORE}, {MAX_NO_GO_SCORE}]"
    )


def test_melk_safety_red_flags(melk_score):
    """MELK safety/selectivity dimension must flag as a violation (broad essentiality)."""
    violations = melk_score["verdict"]["dimension_violations"]
    assert "safety_selectivity" in violations, (
        f"Expected safety_selectivity violation for MELK (broad essentiality), "
        f"got violations: {violations}"
    )


def test_melk_scores_below_all_showcase_targets(melk_score, showcase_scores):
    """MELK must score below every showcase target (confirms discrimination ability)."""
    melk_composite = melk_score["composite"]["score"]
    showcase_composites = {
        gene: scoring["composite"]["score"]
        for gene, scoring in showcase_scores.items()
    }
    for gene, score in showcase_composites.items():
        assert melk_composite < score, (
            f"MELK ({melk_composite:.1f}) should score lower than {gene.upper()} "
            f"({score:.1f}) but does not"
        )


def test_melk_data_coverage_above_threshold(melk_score):
    """All MELK dimensions have data_coverage >= 0.3 (avoids neutral score substitution).

    Per Phase 5 decision: dimensions with coverage < 0.3 receive neutral 0.5 score,
    which would mask actual NO-GO signals. MELK evidence must be real, not neutral.
    """
    dimensions = melk_score["composite"]["dimension_scores"]
    for dim in dimensions:
        assert dim["data_coverage"] >= 0.3, (
            f"MELK {dim['name']} has data_coverage {dim['data_coverage']:.2f} < 0.3 -- "
            f"scoring framework would substitute neutral 0.5 score, masking NO-GO signal"
        )
