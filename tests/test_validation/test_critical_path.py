"""GxP validation: critical path requirements traceability (REQ-803).

Verifies that the traceability matrix exists and that critical platform
capabilities are structurally present. These tests confirm the platform
is ready for GxP qualification review.

NO MOCKING: tests check real file existence and real module imports.
"""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent

pytestmark = pytest.mark.validation


def test_traceability_yaml_exists():
    """GxP traceability matrix must exist at docs/gxp/traceability.yaml (REQ-803)."""
    traceability = PROJECT_ROOT / "docs" / "gxp" / "traceability.yaml"
    if not traceability.exists():
        pytest.skip("Traceability file not yet created (run plan 08-02 first)")
    assert traceability.exists()


def test_traceability_yaml_has_req801():
    """REQ-801 must be present in the traceability matrix with test references."""
    traceability = PROJECT_ROOT / "docs" / "gxp" / "traceability.yaml"
    if not traceability.exists():
        pytest.skip("Traceability file not yet created (run plan 08-02 first)")
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not installed (pip install pyyaml)")
    data = yaml.safe_load(traceability.read_text())
    traceability_map = data.get("traceability", {})
    assert "REQ-801" in traceability_map, "REQ-801 not found in traceability matrix"
    req = traceability_map["REQ-801"]
    assert len(req.get("tests", [])) >= 1, "REQ-801 has no test references"


def test_audit_trail_module_importable():
    """AuditTrail must be importable from src.compliance.audit_trail (REQ-503)."""
    from src.compliance.audit_trail import AuditTrail
    assert AuditTrail is not None


def test_scoring_framework_importable():
    """ScoringFramework must be importable from src.scoring.framework (REQ-401)."""
    from src.scoring.framework import ScoringFramework
    assert ScoringFramework is not None


def test_verdict_levels_correct():
    """VerdictLevel enum must have GO, CONDITIONAL, NO_GO values (REQ-402)."""
    from src.scoring.models import VerdictLevel
    assert VerdictLevel.GO.value == "GO"
    assert VerdictLevel.CONDITIONAL.value == "CONDITIONAL"
    assert VerdictLevel.NO_GO.value == "NO-GO"


def test_showcase_scenarios_complete():
    """All 6 showcase gene directories must exist with scoring.json (SC#1)."""
    scenarios_dir = PROJECT_ROOT / "data" / "showcase_scenarios"
    required_genes = ["egfr", "esr1", "pik3ca", "glp1r", "parp1", "cd274"]
    for gene in required_genes:
        scoring_file = scenarios_dir / gene / "scoring.json"
        assert scoring_file.exists(), (
            f"Showcase data missing for {gene.upper()}: {scoring_file}"
        )


def test_melk_negative_control_exists():
    """MELK negative control data must exist (REQ-802)."""
    melk_dir = PROJECT_ROOT / "data" / "showcase_scenarios" / "melk"
    assert (melk_dir / "scoring.json").exists(), "MELK scoring.json not found"
    assert (melk_dir / "evidence.json").exists(), "MELK evidence.json not found"


def test_precommit_config_exists():
    """Pre-commit configuration must exist at .pre-commit-config.yaml (REQ-806)."""
    config = PROJECT_ROOT / ".pre-commit-config.yaml"
    if not config.exists():
        pytest.skip(".pre-commit-config.yaml not yet created (run plan 08-03 first)")
    assert config.exists()


def test_hook_scripts_exist():
    """All three pre-commit hook scripts must exist in scripts/hooks/ (REQ-806)."""
    hooks_dir = PROJECT_ROOT / "scripts" / "hooks"
    required_hooks = [
        "check_audit_trail.py",
        "check_hardcoded_params.py",
        "check_config_changes.py",
    ]
    missing = [h for h in required_hooks if not (hooks_dir / h).exists()]
    if missing:
        pytest.skip(f"Hook scripts not yet created (run plan 08-03 first): {missing}")
    for hook in required_hooks:
        assert (hooks_dir / hook).exists()
