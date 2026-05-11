"""Comprehensive test suite for the AI reasoning subsystem.

Tests all reasoning components without requiring a live LLM or network access.
Uses unittest.mock for LLM provider interactions and evidence sources.

Test categories:
1. Model tests (5): enums, records, traces, claims, provenance
2. Tool definition tests (3): count, format, citation coverage
3. Prompt registry tests (3): all modes, hash changes, determinism
4. Token manager tests (3): counting, summarization, truncation
5. Tool executor tests (3): dispatch, missing data, evidence mock
6. Hallucination checker tests (4): valid, phantom, uncited, confidence
7. Provenance tests (3): hash, determinism, build record
8. Fallback chain tests (2): construction, mock execution
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.reasoning.fallback import FallbackChain
from src.reasoning.hallucination import (
    check_citations,
    check_confidence_sources,
    validate_output,
)
from src.reasoning.models import (
    Claim,
    ProvenanceRecord,
    ReasoningMode,
    ReasoningResult,
    ToolCallRecord,
    ToolTrace,
)
from src.reasoning.prompts import PromptRegistry
from src.reasoning.provenance import ProvenanceTracker
from src.reasoning.token_manager import TokenManager
from src.reasoning.tool_executor import ToolExecutor
from src.reasoning.tools import CITATION_TO_TOOL, TOOL_DEFINITIONS


# ============================================================================
# 1. Model tests (5)
# ============================================================================


class TestModels:
    """Tests for reasoning data models."""

    def test_reasoning_mode_enum(self):
        """Verify all 5 modes exist with correct string values."""
        assert ReasoningMode.HYPOTHESIS.value == "hypothesis"
        assert ReasoningMode.SYNTHESIS.value == "synthesis"
        assert ReasoningMode.CONTRADICTION.value == "contradiction"
        assert ReasoningMode.GAP.value == "gap"
        assert ReasoningMode.CONFIDENCE.value == "confidence"
        assert len(ReasoningMode) == 5

    def test_tool_call_record_creation(self):
        """Create ToolCallRecord, verify fields."""
        record = ToolCallRecord(
            name="query_opentargets",
            arguments={"gene_symbol": "EGFR"},
            result={"gene": "EGFR", "associations": []},
            round_number=1,
            duration_ms=42.5,
        )
        assert record.name == "query_opentargets"
        assert record.arguments == {"gene_symbol": "EGFR"}
        assert record.result == {"gene": "EGFR", "associations": []}
        assert record.round_number == 1
        assert record.duration_ms == 42.5

    def test_tool_trace_tools_used(self):
        """Create ToolTrace with multiple tool calls, verify tools_used() returns unique names."""
        trace = ToolTrace(
            rounds=[],
            tool_calls=[
                ToolCallRecord(name="query_opentargets", arguments={}, result={}, round_number=1),
                ToolCallRecord(name="query_dgidb", arguments={}, result={}, round_number=1),
                ToolCallRecord(name="query_opentargets", arguments={}, result={}, round_number=2),
                ToolCallRecord(name="query_pubmed", arguments={}, result={}, round_number=2),
            ],
            total_rounds=2,
            final_text="test output",
        )
        used = trace.tools_used()
        assert used == ["query_opentargets", "query_dgidb", "query_pubmed"]
        # Verifies deduplication and order preservation
        assert len(used) == 3

    def test_claim_model(self):
        """Create Claim with sources, verify Pydantic validation."""
        claim = Claim(
            text="EGFR is a validated therapeutic target",
            confidence=0.85,
            sources=["OpenTargets", "DGIdb"],
            evidence_snippets=["snippet 1"],
        )
        assert claim.text == "EGFR is a validated therapeutic target"
        assert claim.confidence == 0.85
        assert claim.sources == ["OpenTargets", "DGIdb"]
        assert claim.evidence_snippets == ["snippet 1"]

        # Verify default empty lists
        claim2 = Claim(text="simple", confidence=0.5, sources=[])
        assert claim2.evidence_snippets == []

    def test_provenance_record_to_audit_details(self):
        """Create ProvenanceRecord, verify to_audit_details() output."""
        record = ProvenanceRecord(
            model_name="qwen3:8b",
            provider_name="Ollama",
            prompt_version="abc123def456" * 5 + "abcd",
            input_evidence_hashes={"opentargets": "hash1"},
            tools_used=["query_opentargets", "query_dgidb"],
            tool_rounds=3,
            fallback_events=[],
            trace_id="test-uuid-1234",
        )
        details = record.to_audit_details()

        # Verify expected keys are present
        assert "model" in details
        assert "provider" in details
        assert "prompt_version" in details
        assert "tools_used" in details
        assert "trace_id" in details

        # Verify values
        assert details["model"] == "qwen3:8b"
        assert details["provider"] == "Ollama"
        assert details["trace_id"] == "test-uuid-1234"
        assert details["tool_rounds"] == 3

        # Verify full reasoning chain is NOT included
        assert "reasoning_chain" not in details
        assert "raw_output" not in details


# ============================================================================
# 2. Tool definition tests (3)
# ============================================================================


class TestToolDefinitions:
    """Tests for LLM tool definitions."""

    def test_tool_definitions_count(self):
        """Assert len(TOOL_DEFINITIONS) == 14."""
        assert len(TOOL_DEFINITIONS) == 14

    def test_tool_definitions_format(self):
        """Each tool has required keys and valid input_schema."""
        for tool in TOOL_DEFINITIONS:
            assert "name" in tool, f"Tool missing 'name': {tool}"
            assert "description" in tool, f"Tool {tool.get('name')} missing 'description'"
            assert "input_schema" in tool, f"Tool {tool['name']} missing 'input_schema'"

            schema = tool["input_schema"]
            assert schema["type"] == "object", f"Tool {tool['name']} schema type != object"
            assert "properties" in schema, f"Tool {tool['name']} schema missing 'properties'"
            assert isinstance(schema["properties"], dict)

    def test_citation_to_tool_coverage(self):
        """Every tool in TOOL_DEFINITIONS has a corresponding entry in CITATION_TO_TOOL."""
        tool_names = {t["name"] for t in TOOL_DEFINITIONS}
        citation_tools = set(CITATION_TO_TOOL.values())

        for tool_name in tool_names:
            assert tool_name in citation_tools, (
                f"Tool '{tool_name}' has no CITATION_TO_TOOL mapping"
            )


# ============================================================================
# 3. Prompt registry tests (3)
# ============================================================================


class TestPromptRegistry:
    """Tests for versioned prompt registry."""

    def test_prompt_registry_all_modes(self):
        """PromptRegistry returns (text, hash) for all 5 modes, all hashes are 64-char hex."""
        registry = PromptRegistry()
        for mode in ReasoningMode:
            text, sha = registry.get(mode)
            assert isinstance(text, str)
            assert len(text) > 50, f"Prompt for {mode.value} too short"
            assert len(sha) == 64, f"Hash for {mode.value} is not 64 chars: {len(sha)}"
            # Verify it's a valid hex string
            int(sha, 16)

    def test_prompt_registry_hash_changes_with_text(self):
        """Register a custom prompt, verify hash differs from default."""
        registry = PromptRegistry()
        _, default_hash = registry.get(ReasoningMode.HYPOTHESIS)

        custom_hash = registry.register(
            ReasoningMode.HYPOTHESIS, "Custom hypothesis prompt for testing."
        )
        assert custom_hash != default_hash
        assert len(custom_hash) == 64

        # Verify the new text is returned
        text, sha = registry.get(ReasoningMode.HYPOTHESIS)
        assert text == "Custom hypothesis prompt for testing."
        assert sha == custom_hash

    def test_prompt_registry_deterministic(self):
        """Same prompt text produces same hash across multiple calls."""
        registry = PromptRegistry()
        _, hash1 = registry.get(ReasoningMode.SYNTHESIS)
        _, hash2 = registry.get(ReasoningMode.SYNTHESIS)
        assert hash1 == hash2

        # Also test register determinism
        h3 = registry.register(ReasoningMode.GAP, "fixed prompt text")
        h4 = registry.register(ReasoningMode.GAP, "fixed prompt text")
        assert h3 == h4


# ============================================================================
# 4. Token manager tests (3)
# ============================================================================


class TestTokenManager:
    """Tests for token counting and context management."""

    def test_token_manager_count(self):
        """Count tokens for known text, verify > 0."""
        tm = TokenManager()
        count = tm.count_tokens("Hello, this is a test of token counting.")
        assert count > 0
        assert isinstance(count, int)

    def test_token_manager_should_summarize(self):
        """Text >8K tokens returns True, short text returns False."""
        tm = TokenManager()

        short_text = "Short text."
        assert tm.should_summarize(short_text) is False

        # Create a text that exceeds 8000 tokens (~32K chars with fallback)
        long_text = "word " * 40000
        assert tm.should_summarize(long_text) is True

    def test_token_manager_truncate(self):
        """Truncate a long result, verify it ends with '... [truncated]' and is shorter."""
        tm = TokenManager()

        # Create text that exceeds 500 tokens
        long_text = "data " * 5000
        truncated = tm.truncate_tool_result(long_text, max_tokens=500)

        assert truncated.endswith("... [truncated]")
        assert len(truncated) < len(long_text)

        # Short text should not be truncated
        short_text = "brief result"
        assert tm.truncate_tool_result(short_text, max_tokens=500) == short_text


# ============================================================================
# 5. Tool executor tests (3)
# ============================================================================


class TestToolExecutor:
    """Tests for tool call dispatch."""

    def test_tool_executor_dispatch_exists(self):
        """ToolExecutor has handlers for all 14 tool names."""
        executor = ToolExecutor()
        tool_names = [t["name"] for t in TOOL_DEFINITIONS]

        assert len(executor._dispatch) == 14
        for name in tool_names:
            assert name in executor._dispatch, f"Missing handler for {name}"

    def test_tool_executor_missing_data(self):
        """Execute a tool with no project_dir, verify error dict is returned (not exception)."""
        executor = ToolExecutor(project_dir=None)
        result = executor.execute("get_gene_expression", {"gene": "EGFR"})

        assert isinstance(result, dict)
        assert "error" in result
        # Should mention pipeline results not available
        assert "Pipeline" in result["error"] or "pipeline" in result["error"].lower()

    def test_tool_executor_evidence_tool(self):
        """Mock an evidence source, execute query_opentargets, verify it returns data."""
        executor = ToolExecutor()

        # Mock the GeneResolver and OpenTargetsSource
        mock_gene_ids = MagicMock()
        mock_gene_ids.canonical_symbol = "EGFR"

        mock_result = MagicMock()
        mock_result.confidence = 0.9
        mock_result.data = {
            "associations": [
                {"disease_name": "Lung cancer", "overall_score": 0.95},
            ],
            "known_drugs": ["erlotinib"],
            "tractability": ["small_molecule"],
        }
        mock_result.error = None

        with patch.object(executor, "_get_gene_resolver") as mock_resolver:
            mock_resolver.return_value.resolve.return_value = mock_gene_ids

            with patch("src.reasoning.tool_executor.ToolExecutor._handle_query_opentargets") as mock_handler:
                mock_handler.return_value = {
                    "gene": "EGFR",
                    "association_count": 1,
                    "top_associations": [{"disease": "Lung cancer", "score": 0.95}],
                    "known_drug_count": 1,
                    "tractability": ["small_molecule"],
                }
                # Need to rebind the dispatch to use the mock
                executor._dispatch["query_opentargets"] = mock_handler

                result = executor.execute("query_opentargets", {"gene_symbol": "EGFR"})

                assert isinstance(result, dict)
                assert result["gene"] == "EGFR"
                assert result["association_count"] == 1


# ============================================================================
# 6. Hallucination checker tests (4)
# ============================================================================


class TestHallucinationChecker:
    """Tests for citation validation and source counting."""

    def test_check_citations_valid(self):
        """Text with valid citations (matching tools in trace) returns no phantom issues."""
        trace = ToolTrace(
            rounds=[],
            tool_calls=[
                ToolCallRecord(name="query_opentargets", arguments={}, result={}, round_number=1),
                ToolCallRecord(name="query_dgidb", arguments={}, result={}, round_number=1),
            ],
            total_rounds=1,
            final_text="test",
        )
        text = "EGFR has associations [Source: OpenTargets] and drugs [Source: DGIdb]"
        issues = check_citations(text, trace)
        phantom = [i for i in issues if i["type"] == "phantom_citation"]
        assert len(phantom) == 0

    def test_check_citations_phantom(self):
        """Text citing a source whose tool was never called returns phantom_citation issue."""
        trace = ToolTrace(
            rounds=[],
            tool_calls=[
                ToolCallRecord(name="query_opentargets", arguments={}, result={}, round_number=1),
            ],
            total_rounds=1,
            final_text="test",
        )
        text = "EGFR has papers [Source: PubMed] and trials [Source: ClinicalTrials]"
        issues = check_citations(text, trace)
        phantom = [i for i in issues if i["type"] == "phantom_citation"]
        assert len(phantom) == 2  # PubMed and ClinicalTrials not called

        cited_sources = {i["citation"] for i in phantom}
        assert "PubMed" in cited_sources
        assert "ClinicalTrials" in cited_sources

    def test_check_citations_uncited(self):
        """Long paragraph without citation returns uncited_claim issue."""
        trace = ToolTrace(
            rounds=[],
            tool_calls=[],
            total_rounds=1,
            final_text="test",
        )
        # Create a paragraph longer than 100 chars without any [Source:] marker
        long_para = "A" * 120
        text = f"Short intro [Source: OpenTargets]\n\n{long_para}"
        issues = check_citations(text, trace)
        uncited = [i for i in issues if i["type"] == "uncited_claim"]
        assert len(uncited) == 1

    def test_check_confidence_insufficient_sources(self):
        """Claim with confidence=0.9 and only 1 source returns insufficient_sources issue."""
        claims = [
            Claim(text="High confidence claim", confidence=0.9, sources=["OpenTargets"]),
            Claim(text="Low confidence claim", confidence=0.5, sources=["DGIdb"]),
            Claim(text="Another high claim", confidence=0.85, sources=["PubMed", "ChEMBL"]),
        ]
        issues = check_confidence_sources(claims)
        # First claim: conf 0.9, 1 source (<3) -> flagged
        # Second claim: conf 0.5, below threshold -> not flagged
        # Third claim: conf 0.85, 2 sources (<3) -> flagged
        assert len(issues) == 2
        assert all(i["type"] == "insufficient_sources" for i in issues)
        assert issues[0]["sources_found"] == 1
        assert issues[1]["sources_found"] == 2


# ============================================================================
# 7. Provenance tests (3)
# ============================================================================


class TestProvenance:
    """Tests for evidence hashing and provenance recording."""

    def test_provenance_hash_evidence(self):
        """Hash a dict, verify 64-char hex string."""
        tracker = ProvenanceTracker()
        h = tracker.hash_evidence({"gene": "EGFR", "score": 0.95})
        assert len(h) == 64
        # Verify it's a valid hex string
        int(h, 16)

    def test_provenance_hash_deterministic(self):
        """Same data produces same hash."""
        tracker = ProvenanceTracker()
        data = {"gene": "EGFR", "associations": [1, 2, 3]}
        h1 = tracker.hash_evidence(data)
        h2 = tracker.hash_evidence(data)
        assert h1 == h2

        # Different data produces different hash
        h3 = tracker.hash_evidence({"gene": "KRAS"})
        assert h3 != h1

    def test_provenance_build_record(self):
        """Build a provenance record from a ToolTrace, verify all fields populated."""
        tracker = ProvenanceTracker()
        trace = ToolTrace(
            rounds=[{"text": "test"}],
            tool_calls=[
                ToolCallRecord(name="query_opentargets", arguments={}, result={}, round_number=1),
                ToolCallRecord(name="query_dgidb", arguments={}, result={}, round_number=2),
            ],
            total_rounds=2,
            final_text="analysis complete",
        )

        record = tracker.build_provenance(
            model_name="qwen3:8b",
            provider_name="Ollama",
            prompt_version="abc123",
            input_evidence_hashes={"opentargets": "hash1"},
            tool_trace=trace,
            fallback_events=[],
        )

        assert isinstance(record, ProvenanceRecord)
        assert record.model_name == "qwen3:8b"
        assert record.provider_name == "Ollama"
        assert record.prompt_version == "abc123"
        assert record.tools_used == ["query_opentargets", "query_dgidb"]
        assert record.tool_rounds == 2
        assert record.input_evidence_hashes == {"opentargets": "hash1"}
        assert len(record.trace_id) > 0
        assert len(record.timestamp) > 0


# ============================================================================
# 8. Fallback chain tests (2)
# ============================================================================


class TestFallbackChain:
    """Tests for LLM provider fallback chain."""

    def test_fallback_chain_construction(self):
        """FallbackChain constructs (may have 0 providers in test env)."""
        # Patch out the provider availability checks to avoid connecting
        with patch("src.reasoning.fallback.OllamaProvider.is_available", return_value=False):
            chain = FallbackChain()
            # May have 0 providers if no API keys set (expected in test env)
            assert isinstance(chain.providers, list)
            assert isinstance(chain.available_providers, list)

    def test_fallback_chain_execute_with_mock(self):
        """Mock a provider, verify execute_with_fallback calls the function correctly."""
        mock_provider = MagicMock()
        mock_provider.name = "MockProvider"
        mock_provider.model = "mock-model"

        with patch("src.reasoning.fallback.OllamaProvider.is_available", return_value=False):
            chain = FallbackChain()

        # Inject mock provider
        chain.providers = [mock_provider]

        mock_trace = ToolTrace(
            rounds=[{"text": "mock response"}],
            tool_calls=[],
            total_rounds=1,
            final_text="mock response",
        )

        def mock_fn(provider):
            assert provider.name == "MockProvider"
            return mock_trace

        result = chain.execute_with_fallback(mock_fn)
        assert result == mock_trace
        assert result.final_text == "mock response"
