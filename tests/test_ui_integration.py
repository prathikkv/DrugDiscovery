"""UI integration test suite for BioOrchestrator v2.

Tests cover:
1. Page module imports (7 tests)
2. Component module imports and exports (3 tests)
3. Showcase scenario data loading and validation (8 tests)
4. Style helper HTML generation (3 tests)
5. Data model compatibility with pre-cached JSON (2 tests)

Total: 23 tests

These tests do NOT require a running Streamlit server -- they test
importability, data models, and component logic directly.
"""

import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

import streamlit as st


# ── Helpers ──────────────────────────────────────────────────────────

SCENARIOS_DIR = Path("data/showcase_scenarios")
SCENARIO_GENES = ["egfr", "esr1", "pik3ca", "glp1r", "parp1", "cd274"]
DATA_FILES = ["evidence", "reasoning", "scoring", "pipeline_report"]
EXPECTED_SOURCES = ["opentargets", "dgidb", "pubmed", "clinicaltrials", "uniprot", "chembl"]


# ═════════════════════════════════════════════════════════════════════
# 1. PAGE IMPORT TESTS
# ═════════════════════════════════════════════════════════════════════


class TestPageImports:
    """Verify all 7 page modules import cleanly."""

    def test_login_page_imports(self):
        import src.pages.login  # noqa: F401

    def test_projects_page_imports(self):
        # projects.py accesses st.session_state["user"] at module level
        # (auth guard pattern). Pre-populate to allow import in bare mode.
        if "src.pages.projects" not in sys.modules:
            st.session_state["user"] = {
                "user_id": "test-user",
                "email": "test@example.com",
                "role": "scientist",
            }
        import src.pages.projects  # noqa: F401

    def test_omics_page_imports(self):
        import src.pages.omics  # noqa: F401

    def test_evidence_page_imports(self):
        import src.pages.evidence  # noqa: F401

    def test_insights_page_imports(self):
        import src.pages.insights  # noqa: F401

    def test_scorecard_page_imports(self):
        import src.pages.scorecard  # noqa: F401

    def test_audit_page_imports(self):
        import src.pages.audit  # noqa: F401


# ═════════════════════════════════════════════════════════════════════
# 2. COMPONENT IMPORT TESTS
# ═════════════════════════════════════════════════════════════════════


class TestComponentImports:
    """Verify component modules export expected symbols."""

    def test_styles_exports(self):
        from src.pages.components.styles import (
            inject_design_system,
            metric_card,
            verdict_badge,
        )

        assert callable(inject_design_system)
        assert callable(metric_card)
        assert callable(verdict_badge)

    def test_hitl_gate_exports(self):
        from src.pages.components.hitl_gate import hitl_gate

        assert callable(hitl_gate)

    def test_showcase_exports(self):
        from src.pages.components.showcase import (
            SHOWCASE_SCENARIOS,
            load_scenario,
        )

        assert isinstance(SHOWCASE_SCENARIOS, dict)
        assert callable(load_scenario)


# ═════════════════════════════════════════════════════════════════════
# 3. SHOWCASE SCENARIO TESTS
# ═════════════════════════════════════════════════════════════════════


class TestShowcaseScenarios:
    """Verify showcase scenario data integrity and loading."""

    def test_showcase_scenario_count(self):
        from src.pages.components.showcase import SHOWCASE_SCENARIOS

        assert len(SHOWCASE_SCENARIOS) == 6

    def test_showcase_scenario_keys(self):
        from src.pages.components.showcase import SHOWCASE_SCENARIOS

        required_keys = {"gene_symbol", "disease_context", "tissue_type", "description"}
        for name, meta in SHOWCASE_SCENARIOS.items():
            missing = required_keys - set(meta.keys())
            assert not missing, f"Scenario '{name}' missing keys: {missing}"

    def test_load_scenario_egfr(self):
        from src.pages.components.showcase import load_scenario

        data = load_scenario("EGFR/NSCLC")
        expected_keys = {"scenario", "evidence", "reasoning", "scoring", "pipeline_report"}
        assert set(data.keys()) == expected_keys, f"Got keys: {set(data.keys())}"

    def test_load_scenario_cd274(self):
        from src.pages.components.showcase import load_scenario

        data = load_scenario("CD274/Pan-cancer")
        expected_keys = {"scenario", "evidence", "reasoning", "scoring", "pipeline_report"}
        assert set(data.keys()) == expected_keys, f"Got keys: {set(data.keys())}"

    def test_all_scenarios_loadable(self):
        from src.pages.components.showcase import SHOWCASE_SCENARIOS, load_scenario

        for name in SHOWCASE_SCENARIOS:
            data = load_scenario(name)
            assert "scenario" in data, f"Scenario '{name}' missing 'scenario' key"
            assert "evidence" in data, f"Scenario '{name}' missing 'evidence' key"
            assert "reasoning" in data, f"Scenario '{name}' missing 'reasoning' key"
            assert "scoring" in data, f"Scenario '{name}' missing 'scoring' key"
            assert "pipeline_report" in data, f"Scenario '{name}' missing 'pipeline_report' key"

    def test_egfr_scoring_go_verdict(self):
        from src.pages.components.showcase import load_scenario

        data = load_scenario("EGFR/NSCLC")
        scoring = data["scoring"]
        assert scoring["composite"]["score"] >= 75, (
            f"EGFR composite score {scoring['composite']['score']} < 75"
        )
        assert scoring["verdict"]["level"] == "GO", (
            f"EGFR verdict is '{scoring['verdict']['level']}', expected 'GO'"
        )

    def test_cd274_scoring_conditional(self):
        from src.pages.components.showcase import load_scenario

        data = load_scenario("CD274/Pan-cancer")
        scoring = data["scoring"]
        score = scoring["composite"]["score"]
        assert 55 <= score <= 70, (
            f"CD274 composite score {score} not in range 55-70"
        )
        assert scoring["verdict"]["level"] == "CONDITIONAL", (
            f"CD274 verdict is '{scoring['verdict']['level']}', expected 'CONDITIONAL'"
        )

    def test_scenario_evidence_has_all_sources(self):
        from src.pages.components.showcase import SHOWCASE_SCENARIOS, load_scenario

        for name in SHOWCASE_SCENARIOS:
            data = load_scenario(name)
            evidence = data["evidence"]
            results = evidence["results"]
            for source in EXPECTED_SOURCES:
                assert source in results, (
                    f"Scenario '{name}' missing evidence source '{source}'"
                )
                assert results[source]["confidence"] > 0.0, (
                    f"Scenario '{name}' source '{source}' has zero confidence"
                )


# ═════════════════════════════════════════════════════════════════════
# 4. STYLE HELPER TESTS
# ═════════════════════════════════════════════════════════════════════


class TestStyleHelpers:
    """Verify CSS and HTML helper function output."""

    def test_metric_card_html(self):
        from src.pages.components.styles import metric_card

        html = metric_card("Total Genes", "42")
        assert 'class="metric-card"' in html
        assert "42" in html
        assert "Total Genes" in html

    def test_verdict_badge_go(self):
        from src.pages.components.styles import verdict_badge

        html = verdict_badge("GO")
        assert "badge-go" in html
        assert "GO" in html

    def test_verdict_badge_nogo(self):
        from src.pages.components.styles import verdict_badge

        html = verdict_badge("NO-GO")
        assert "badge-nogo" in html
        assert "NO-GO" in html


# ═════════════════════════════════════════════════════════════════════
# 5. DATA MODEL COMPATIBILITY TESTS
# ═════════════════════════════════════════════════════════════════════


class TestDataModelCompatibility:
    """Verify pre-cached JSON matches expected data model fields."""

    def test_scorecard_data_has_required_fields(self):
        """Each scoring.json has gene_symbol, composite, verdict, evidence_hash."""
        for gene_dir in SCENARIO_GENES:
            path = SCENARIOS_DIR / gene_dir / "scoring.json"
            assert path.exists(), f"Missing scoring.json for {gene_dir}"

            with open(path) as f:
                data = json.load(f)

            required = ["gene_symbol", "composite", "verdict", "evidence_hash"]
            for field in required:
                assert field in data, (
                    f"{gene_dir}/scoring.json missing field '{field}'"
                )

            # composite must have score and dimension_scores
            assert "score" in data["composite"], (
                f"{gene_dir}/scoring.json composite missing 'score'"
            )
            assert "dimension_scores" in data["composite"], (
                f"{gene_dir}/scoring.json composite missing 'dimension_scores'"
            )
            assert len(data["composite"]["dimension_scores"]) == 7, (
                f"{gene_dir}/scoring.json has {len(data['composite']['dimension_scores'])} "
                f"dimensions, expected 7"
            )

            # verdict must have level and rationale
            assert "level" in data["verdict"], (
                f"{gene_dir}/scoring.json verdict missing 'level'"
            )
            assert data["verdict"]["level"] in ("GO", "CONDITIONAL", "NO-GO"), (
                f"{gene_dir}/scoring.json verdict level "
                f"'{data['verdict']['level']}' is invalid"
            )

    def test_evidence_data_has_gene_identifiers(self):
        """Each evidence.json has gene.canonical_symbol."""
        for gene_dir in SCENARIO_GENES:
            path = SCENARIOS_DIR / gene_dir / "evidence.json"
            assert path.exists(), f"Missing evidence.json for {gene_dir}"

            with open(path) as f:
                data = json.load(f)

            assert "gene" in data, (
                f"{gene_dir}/evidence.json missing 'gene' key"
            )
            assert "canonical_symbol" in data["gene"], (
                f"{gene_dir}/evidence.json gene missing 'canonical_symbol'"
            )
            assert data["gene"]["canonical_symbol"] == gene_dir.upper(), (
                f"{gene_dir}/evidence.json canonical_symbol "
                f"'{data['gene']['canonical_symbol']}' != '{gene_dir.upper()}'"
            )
