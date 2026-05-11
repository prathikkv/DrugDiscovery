"""AI Reasoning Engine -- structured scientific analysis with tool-calling LLMs.

This module provides the core reasoning subsystem for BioOrchestrator:
- ReasoningMode: 5 analysis modes (hypothesis, synthesis, contradiction, gap, confidence)
- Data models: ReasoningResult, Claim, ToolTrace, ToolCallRecord, ProvenanceRecord
- Tool definitions: 14 LLM-callable tools in Anthropic format
- Prompt registry: Versioned system prompts with SHA256 hashing
- Token manager: Context window management and token counting
- FallbackChain: LLM provider resilience with audit logging
- ToolExecutor: Tool call dispatch to pipeline and evidence subsystems
- run_tool_loop: Agentic tool-calling loop with 10-round limit
- ProvenanceTracker: Evidence hashing and provenance recording
"""

from __future__ import annotations

from src.reasoning.fallback import FallbackChain
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
from src.reasoning.tool_loop import run_tool_loop
from src.reasoning.tools import CITATION_TO_TOOL, TOOL_DEFINITIONS

__all__ = [
    "ReasoningMode",
    "ReasoningResult",
    "Claim",
    "ToolTrace",
    "ToolCallRecord",
    "ProvenanceRecord",
    "TOOL_DEFINITIONS",
    "CITATION_TO_TOOL",
    "PromptRegistry",
    "TokenManager",
    "FallbackChain",
    "ToolExecutor",
    "run_tool_loop",
    "ProvenanceTracker",
]
