"""Hallucination detection: citation validation and source counting (REQ-307).

Checks LLM reasoning output for:
- Phantom citations: claims citing a source whose tool was never called
- Uncited claims: substantive paragraphs without any source citation
- Insufficient sources: high-confidence claims with fewer than 3 supporting sources

Used by ReasoningEngine after each reasoning run to flag potential
hallucinations before returning results to downstream consumers.
"""

from __future__ import annotations

import re

from src.reasoning.models import Claim, ToolTrace
from src.reasoning.tools import CITATION_TO_TOOL


def check_citations(text: str, tool_trace: ToolTrace) -> list[dict]:
    """Validate that every citation in text references an actual tool call.

    Extracts all ``[Source: X]`` citations from the text, maps each to its
    corresponding tool name via CITATION_TO_TOOL, and checks whether that
    tool was actually called during the reasoning session. Also flags
    substantive paragraphs (>100 chars) without any citation.

    Args:
        text: The LLM reasoning output text.
        tool_trace: ToolTrace from the reasoning session.

    Returns:
        List of issue dicts, each with a ``type`` key (``phantom_citation``
        or ``uncited_claim``) and descriptive detail.
    """
    issues: list[dict] = []

    # Get set of tools actually called
    tools_called = set(tool_trace.tools_used())

    # Extract all [Source: X] citations
    citations = re.findall(r"\[Source:\s*(\w+)\]", text)

    for citation in citations:
        tool_name = CITATION_TO_TOOL.get(citation)
        if tool_name is None:
            # Citation references an unknown source
            issues.append({
                "type": "phantom_citation",
                "citation": citation,
                "detail": f"Cites {citation} but no tool mapping exists for this source",
            })
        elif tool_name not in tools_called:
            # Citation references a tool that was never called
            issues.append({
                "type": "phantom_citation",
                "citation": citation,
                "detail": f"Cites {citation} but tool {tool_name} was never called",
            })

    # Check for uncited substantive paragraphs
    paragraphs = text.split("\n\n")
    for para in paragraphs:
        if len(para) > 100 and "[Source:" not in para:
            issues.append({
                "type": "uncited_claim",
                "detail": f"Paragraph without citation: {para[:80]}...",
            })

    return issues


def check_confidence_sources(claims: list[Claim]) -> list[dict]:
    """Flag high-confidence claims with insufficient source support.

    Claims with confidence > 0.8 should be backed by at least 3 independent
    sources. This function identifies claims that exceed the confidence
    threshold but have fewer supporting sources than required.

    Args:
        claims: List of Claim objects from the reasoning output.

    Returns:
        List of issue dicts with type ``insufficient_sources``.
    """
    issues: list[dict] = []

    for claim in claims:
        if claim.confidence > 0.8:
            if len(claim.sources) < 3:
                issues.append({
                    "type": "insufficient_sources",
                    "claim": claim.text[:80],
                    "confidence": claim.confidence,
                    "sources_found": len(claim.sources),
                    "sources_required": 3,
                })

    return issues


def validate_output(
    text: str, claims: list[Claim], tool_trace: ToolTrace
) -> list[dict]:
    """Run all hallucination checks on reasoning output.

    Convenience function that combines citation validation and confidence-
    source checking into a single call.

    Args:
        text: The LLM reasoning output text.
        claims: List of Claim objects parsed from the output.
        tool_trace: ToolTrace from the reasoning session.

    Returns:
        Combined list of all issues found by both checkers.
    """
    issues = check_citations(text, tool_trace)
    issues.extend(check_confidence_sources(claims))
    return issues
