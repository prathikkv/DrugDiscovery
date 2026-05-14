"""Shared fixtures for GxP validation tests.

Validation tests load real pre-cached showcase data -- no mocking.
All fixtures return parsed JSON dicts from data/showcase_scenarios/.
"""

import json
from pathlib import Path

import pytest

SCENARIOS_DIR = Path(__file__).parent.parent.parent / "data" / "showcase_scenarios"


@pytest.fixture(scope="session")
def showcase_scores() -> dict[str, dict]:
    """Load all 6 showcase scoring.json files into memory (session scope for speed)."""
    genes = ["egfr", "esr1", "pik3ca", "glp1r", "parp1", "cd274"]
    return {
        gene: json.loads((SCENARIOS_DIR / gene / "scoring.json").read_text())
        for gene in genes
    }


@pytest.fixture(scope="session")
def melk_score() -> dict:
    """Load MELK negative control scoring.json."""
    return json.loads((SCENARIOS_DIR / "melk" / "scoring.json").read_text())
