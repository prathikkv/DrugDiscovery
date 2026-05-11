"""Multi-mode reasoning engine orchestrator (REQ-301).

Top-level entry point that ties together all reasoning components:
- FallbackChain for LLM provider resilience
- PromptRegistry for versioned system prompts
- TokenManager for context window management
- ToolExecutor and run_tool_loop for agentic tool-calling
- Hallucination checker for output validation
- ProvenanceTracker for audit trail integration

Usage::

    engine = ReasoningEngine()
    result = engine.reason("EGFR", ReasoningMode.HYPOTHESIS)
    # result.claims, result.summary, result.hallucination_issues, etc.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from src.reasoning.fallback import FallbackChain
from src.reasoning.hallucination import validate_output
from src.reasoning.models import Claim, ReasoningMode, ReasoningResult, ToolTrace
from src.reasoning.prompts import PromptRegistry
from src.reasoning.provenance import ProvenanceTracker
from src.reasoning.token_manager import TokenManager
from src.reasoning.tool_executor import ToolExecutor
from src.reasoning.tool_loop import run_tool_loop
from src.reasoning.tools import TOOL_DEFINITIONS

logger = logging.getLogger(__name__)

# Mode-specific instructions for building the user message
_MODE_INSTRUCTIONS: dict[ReasoningMode, str] = {
    ReasoningMode.HYPOTHESIS: "generate testable hypotheses",
    ReasoningMode.SYNTHESIS: "synthesize findings across all sources",
    ReasoningMode.CONTRADICTION: "identify contradictions between sources",
    ReasoningMode.GAP: "identify gaps in the available evidence",
    ReasoningMode.CONFIDENCE: "assess confidence in the therapeutic potential",
}


class ReasoningEngine:
    """Multi-mode reasoning orchestrator for scientific target assessment.

    Coordinates the full reasoning pipeline: prompt selection, tool-calling
    loop via fallback chain, output parsing, hallucination validation, and
    provenance recording. Each call to ``reason()`` produces a structured
    ``ReasoningResult`` with claims, citations, and full audit provenance.

    Args:
        fallback_chain: LLM provider chain. Creates default if None.
        tool_executor: Tool call dispatcher. Creates default if None.
        prompt_registry: Versioned prompt registry. Creates default if None.
        provenance_tracker: Provenance recorder. Creates default if None.
        token_manager: Token counting/budgeting. Creates default if None.
        audit_trail: AuditTrail instance for provenance logging. Passed to
            default FallbackChain and ProvenanceTracker if they are None.
    """

    def __init__(
        self,
        fallback_chain: Optional[FallbackChain] = None,
        tool_executor: Optional[ToolExecutor] = None,
        prompt_registry: Optional[PromptRegistry] = None,
        provenance_tracker: Optional[ProvenanceTracker] = None,
        token_manager: Optional[TokenManager] = None,
        audit_trail: Optional[Any] = None,
    ) -> None:
        self.token_manager = token_manager or TokenManager()
        self.prompt_registry = prompt_registry or PromptRegistry()
        self.tool_executor = tool_executor or ToolExecutor()
        self.fallback_chain = fallback_chain or FallbackChain(audit_trail=audit_trail)
        self.provenance_tracker = provenance_tracker or ProvenanceTracker(
            audit_trail=audit_trail
        )
        self.audit_trail = audit_trail

    def reason(
        self,
        gene_symbol: str,
        mode: ReasoningMode,
        disease_context: Optional[str] = None,
        evidence: Optional[Any] = None,
        user_id: str = "system",
    ) -> ReasoningResult:
        """Run a full reasoning session for a gene in a given mode.

        This is the main entry point. Steps:
        1. Get versioned prompt for the mode
        2. Build user message with mode-specific instruction
        3. Hash evidence if provided
        4. Check token budget and truncate if needed
        5. Run tool loop with fallback chain
        6. Parse claims from LLM output
        7. Validate output for hallucinations
        8. Build and record provenance
        9. Return structured ReasoningResult

        Args:
            gene_symbol: Target gene to analyze (e.g., 'EGFR').
            mode: Reasoning analysis mode.
            disease_context: Optional disease/indication context.
            evidence: Optional AggregatedEvidence with pre-fetched data.
            user_id: User ID for audit trail (default 'system').

        Returns:
            ReasoningResult with claims, summary, tool trace, hallucination
            issues, and provenance metadata.
        """
        # Step a: Get versioned prompt
        system_prompt, prompt_hash = self.prompt_registry.get(mode)

        # Step b: Build user message
        mode_instruction = _MODE_INSTRUCTIONS.get(mode, "analyze the evidence")
        user_message = (
            f"Analyze the gene {gene_symbol}"
            f"{' in the context of ' + disease_context if disease_context else ''}.\n"
            f"Use the available tools to query data sources and {mode_instruction}.\n"
            f"Structure your response with clear claims, each citing its source "
            f"using [Source: SourceName] format."
        )

        # Step c: Hash evidence if provided
        input_evidence_hashes: dict[str, str] = {}
        if evidence is not None:
            try:
                input_evidence_hashes = (
                    self.provenance_tracker.hash_aggregated_evidence(evidence)
                )
                # Append a brief evidence summary to the user message
                evidence_summary = self._build_evidence_summary(evidence)
                if evidence_summary:
                    user_message += f"\n\nPre-fetched evidence summary:\n{evidence_summary}"
            except Exception as e:
                logger.warning("Failed to hash evidence: %s", e)

        # Step d: Check token budget
        if evidence is not None:
            evidence_text = user_message
            if self.token_manager.should_summarize(evidence_text):
                # Truncate evidence summary to fit
                user_message = self.token_manager.truncate_tool_result(
                    user_message, max_tokens=6000
                )

        # Step e: Run tool loop with fallback
        trace: Optional[ToolTrace] = None
        provider_name = "unknown"
        model_name = "unknown"
        fallback_events: list[dict] = []

        try:
            def _run_reasoning(provider):
                return run_tool_loop(
                    provider,
                    system_prompt,
                    user_message,
                    TOOL_DEFINITIONS,
                    self.tool_executor,
                    self.token_manager,
                    max_rounds=10,
                )

            trace = self.fallback_chain.execute_with_fallback(_run_reasoning)

            # Get provider info from fallback chain
            try:
                provider_obj, provider_name = self.fallback_chain.get_provider()
                model_name = getattr(provider_obj, "model", "unknown")
            except RuntimeError:
                pass

            # Collect fallback events
            fallback_events = [
                {"provider": name, "error": err}
                for name, err in self.fallback_chain.last_fallback_events
            ]

        except RuntimeError as e:
            # All providers failed
            logger.error("All LLM providers failed for %s/%s: %s", gene_symbol, mode.value, e)
            return ReasoningResult(
                mode=mode,
                gene_symbol=gene_symbol,
                disease_context=disease_context,
                claims=[],
                summary=f"Reasoning failed: {e}",
                raw_output=str(e),
                tool_trace=ToolTrace(),
                hallucination_issues=[],
            )

        # Step f: Parse claims from output
        claims = self._parse_claims(trace.final_text)

        # Step g: Hallucination check
        hallucination_issues = validate_output(trace.final_text, claims, trace)

        # Step h: Build provenance
        try:
            provenance = self.provenance_tracker.build_provenance(
                model_name=model_name,
                provider_name=provider_name,
                prompt_version=prompt_hash,
                input_evidence_hashes=input_evidence_hashes,
                tool_trace=trace,
                fallback_events=fallback_events,
            )

            # Record to audit trail
            self.provenance_tracker.record_to_audit(
                provenance, gene_symbol, mode.value, user_id
            )

            # Save trace to disk
            self.provenance_tracker.save_trace(provenance.trace_id, trace)
        except Exception as e:
            logger.warning("Failed to record provenance: %s", e)

        # Step i: Return ReasoningResult
        return ReasoningResult(
            mode=mode,
            gene_symbol=gene_symbol,
            disease_context=disease_context,
            claims=claims,
            summary=trace.final_text,
            raw_output=trace.final_text,
            tool_trace=trace,
            hallucination_issues=hallucination_issues,
        )

    def reason_all_modes(
        self,
        gene_symbol: str,
        disease_context: Optional[str] = None,
        evidence: Optional[Any] = None,
        user_id: str = "system",
    ) -> dict[ReasoningMode, ReasoningResult]:
        """Run reasoning in all 5 modes for a gene.

        Catches exceptions per mode so one mode failing does not prevent
        the others from completing.

        Args:
            gene_symbol: Target gene to analyze.
            disease_context: Optional disease/indication context.
            evidence: Optional AggregatedEvidence with pre-fetched data.
            user_id: User ID for audit trail.

        Returns:
            Dict mapping ReasoningMode -> ReasoningResult for each mode.
        """
        results: dict[ReasoningMode, ReasoningResult] = {}

        for mode in ReasoningMode:
            try:
                results[mode] = self.reason(
                    gene_symbol, mode, disease_context, evidence, user_id
                )
            except Exception as e:
                logger.error(
                    "Reasoning mode %s failed for %s: %s", mode.value, gene_symbol, e
                )
                results[mode] = ReasoningResult(
                    mode=mode,
                    gene_symbol=gene_symbol,
                    disease_context=disease_context,
                    claims=[],
                    summary=f"Mode {mode.value} failed: {e}",
                    raw_output=str(e),
                    tool_trace=ToolTrace(),
                    hallucination_issues=[],
                )

        return results

    @staticmethod
    def _parse_claims(text: str) -> list[Claim]:
        """Parse structured claims from LLM output text.

        Uses a heuristic parser that looks for numbered items (e.g., "1.", "2.")
        or bullet points ("- ", "* "), extracts text and ``[Source: X]`` citations
        per item, and assigns default confidence of 0.5 unless the LLM explicitly
        states a confidence value.

        This parser does NOT need to be perfect -- it extracts what it can.
        The raw output is always preserved in ReasoningResult.raw_output.

        Args:
            text: LLM reasoning output text.

        Returns:
            List of Claim objects parsed from the text.
        """
        claims: list[Claim] = []
        if not text:
            return claims

        # Split text into potential claim items
        # Match numbered items: "1.", "2." etc, or bullet points: "- ", "* "
        lines = text.split("\n")
        current_item: list[str] = []
        items: list[str] = []

        for line in lines:
            stripped = line.strip()
            # Check if this line starts a new item
            is_new_item = bool(
                re.match(r"^\d+[\.\)]\s", stripped)
                or re.match(r"^[-*]\s", stripped)
            )

            if is_new_item:
                if current_item:
                    items.append("\n".join(current_item))
                current_item = [stripped]
            elif current_item:
                current_item.append(stripped)

        # Don't forget the last item
        if current_item:
            items.append("\n".join(current_item))

        for item_text in items:
            if len(item_text) < 10:
                continue  # Skip trivially short items

            # Extract sources from [Source: X] citations
            sources = re.findall(r"\[Source:\s*(\w+)\]", item_text)

            # Try to extract a confidence value
            confidence = 0.5  # default
            conf_match = re.search(
                r"(?:confidence|score)[:\s]*(\d+\.?\d*)", item_text, re.IGNORECASE
            )
            if conf_match:
                try:
                    parsed_conf = float(conf_match.group(1))
                    if 0.0 <= parsed_conf <= 1.0:
                        confidence = parsed_conf
                except ValueError:
                    pass

            # Clean the text (remove citation markers for readability)
            clean_text = re.sub(r"\[Source:\s*\w+\]", "", item_text).strip()
            # Remove leading bullet/number
            clean_text = re.sub(r"^\d+[\.\)]\s*", "", clean_text)
            clean_text = re.sub(r"^[-*]\s*", "", clean_text)

            if clean_text:
                claims.append(
                    Claim(
                        text=clean_text,
                        confidence=confidence,
                        sources=list(dict.fromkeys(sources)),  # deduplicate, preserve order
                    )
                )

        return claims

    @staticmethod
    def _build_evidence_summary(evidence: Any) -> str:
        """Build a brief text summary of pre-fetched evidence.

        Extracts key findings from each source in the AggregatedEvidence
        that has confidence > 0, for inclusion in the user message.

        Args:
            evidence: AggregatedEvidence object.

        Returns:
            Summary text string, or empty string if no evidence available.
        """
        parts: list[str] = []

        try:
            for source_name, result in evidence.results.items():
                if result.confidence > 0 and result.data:
                    # Build a compact summary per source
                    data = result.data
                    summary_line = f"- {source_name} (confidence={result.confidence:.1f})"

                    # Add key detail based on source type
                    if "associations" in data:
                        count = len(data["associations"])
                        summary_line += f": {count} disease associations"
                    elif "interactions" in data:
                        count = data.get("interaction_count", len(data["interactions"]))
                        summary_line += f": {count} drug interactions"
                    elif "papers" in data:
                        count = data.get("total_count", len(data["papers"]))
                        summary_line += f": {count} publications"
                    elif "trials" in data:
                        count = data.get("total_count", len(data["trials"]))
                        summary_line += f": {count} clinical trials"
                    elif "protein_name" in data:
                        summary_line += f": {data['protein_name']}"

                    parts.append(summary_line)
        except Exception as e:
            logger.warning("Failed to build evidence summary: %s", e)

        return "\n".join(parts)
