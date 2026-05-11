"""AI Reasoning Engine -- structured scientific analysis with tool-calling LLMs.

This module provides the core reasoning subsystem for BioOrchestrator:
- ReasoningMode: 5 analysis modes (hypothesis, synthesis, contradiction, gap, confidence)
- Data models: ReasoningResult, Claim, ToolTrace, ToolCallRecord, ProvenanceRecord
- Tool definitions: 14 LLM-callable tools in Anthropic format
- Prompt registry: Versioned system prompts with SHA256 hashing
- Token manager: Context window management and token counting
"""

from __future__ import annotations

from src.reasoning.models import (
    Claim,
    ProvenanceRecord,
    ReasoningMode,
    ReasoningResult,
    ToolCallRecord,
    ToolTrace,
)
from src.reasoning.prompts import PromptRegistry
from src.reasoning.token_manager import TokenManager
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
]
