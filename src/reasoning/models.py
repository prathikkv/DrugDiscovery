"""Reasoning data models: enums, results, claims, tool traces, and provenance.

Defines the type system for the AI reasoning engine. All reasoning operations
produce ReasoningResult instances with structured claims, tool-calling traces,
and provenance records suitable for audit trail integration.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ReasoningMode(str, Enum):
    """Reasoning analysis modes -- each drives a different system prompt and output structure."""

    HYPOTHESIS = "hypothesis"  # Generate testable hypotheses from evidence
    SYNTHESIS = "synthesis"  # Synthesize findings across sources
    CONTRADICTION = "contradiction"  # Identify conflicting evidence
    GAP = "gap"  # Flag missing evidence and data gaps
    CONFIDENCE = "confidence"  # Assess confidence levels with justification


class ToolCallRecord(BaseModel):
    """Record of a single LLM tool call execution."""

    name: str  # Tool function name (e.g., "query_opentargets")
    arguments: dict  # Arguments passed to the tool
    result: Optional[dict | str] = None  # Tool execution result
    round_number: int  # Which round of the tool loop (1-10)
    duration_ms: float = 0.0  # Execution time in milliseconds


class ToolTrace(BaseModel):
    """Full trace of an LLM tool-calling session across multiple rounds."""

    rounds: list[dict] = Field(default_factory=list)  # Raw LLM response per round
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)  # All tool calls executed
    total_rounds: int = 0  # Total rounds completed
    final_text: str = ""  # Final LLM text output after all rounds

    def tools_used(self) -> list[str]:
        """Return unique tool names from all tool calls."""
        seen: set[str] = set()
        result: list[str] = []
        for tc in self.tool_calls:
            if tc.name not in seen:
                seen.add(tc.name)
                result.append(tc.name)
        return result


class Claim(BaseModel):
    """A single structured claim with confidence and source citations."""

    text: str  # The claim text
    confidence: float  # Confidence score (0.0-1.0)
    sources: list[str]  # Source citations (e.g., ["OpenTargets", "PubMed"])
    evidence_snippets: list[str] = Field(default_factory=list)  # Supporting evidence text


class ReasoningResult(BaseModel):
    """Complete result from a reasoning analysis session."""

    mode: ReasoningMode  # Which reasoning mode was used
    gene_symbol: str  # Target gene analyzed
    disease_context: Optional[str] = None  # Optional disease context
    claims: list[Claim] = Field(default_factory=list)  # Structured claims with citations
    summary: str = ""  # Overall reasoning summary text
    raw_output: str = ""  # Raw LLM output text
    tool_trace: Optional[ToolTrace] = None  # Full tool-calling trace
    hallucination_issues: list[dict] = Field(default_factory=list)  # Issues found by checker
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )  # ISO 8601 timestamp


class ProvenanceRecord(BaseModel):
    """Provenance metadata for a reasoning session -- links to audit trail."""

    model_name: str  # e.g., "qwen3:8b"
    provider_name: str  # e.g., "Ollama", "Groq", "Claude"
    prompt_version: str  # SHA256 hash of the system prompt used
    input_evidence_hashes: dict[str, str] = Field(
        default_factory=dict
    )  # {source_name: sha256_of_evidence_data}
    tools_used: list[str] = Field(default_factory=list)  # Tool names invoked
    tool_rounds: int = 0  # Number of tool-calling rounds completed
    fallback_events: list[dict] = Field(
        default_factory=list
    )  # [{provider, error, timestamp}]
    trace_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )  # UUID for referencing full trace
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )  # ISO 8601 timestamp

    def to_audit_details(self) -> dict:
        """Return a dict suitable for AuditTrail.append_record(details=...).

        Includes model, provider, prompt version, evidence hashes, tools,
        rounds, fallback events, and trace_id. Does NOT include the full
        reasoning chain -- that is stored separately per research recommendation.
        """
        return {
            "model": self.model_name,
            "provider": self.provider_name,
            "prompt_version": self.prompt_version,
            "input_evidence_hashes": self.input_evidence_hashes,
            "tools_used": self.tools_used,
            "tool_rounds": self.tool_rounds,
            "fallback_events": self.fallback_events,
            "trace_id": self.trace_id,
        }
