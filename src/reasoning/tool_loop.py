"""Agentic tool-calling loop with 10-round limit (REQ-302).

Implements the core reasoning loop: send messages to the LLM, process tool
calls, feed results back, repeat until the LLM stops calling tools or the
round limit is reached. Each round and tool call is recorded in a ToolTrace
for provenance tracking.

CRITICAL: Uses json.dumps(output, default=str) when serializing tool results
to handle datetime objects, Path objects, etc.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

from src.reasoning.models import ToolCallRecord, ToolTrace
from src.reasoning.token_manager import TokenManager
from src.reasoning.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)


def run_tool_loop(
    provider,
    system: str,
    initial_message: str,
    tools: list[dict],
    tool_executor: ToolExecutor,
    token_manager: Optional[TokenManager] = None,
    max_rounds: int = 10,
) -> ToolTrace:
    """Execute an agentic tool-calling loop with round limit and tracing.

    Follows the pattern from bioorchestrator_real/utils/ai_copilot.py but
    adapted for the reasoning engine with full per-round provenance tracking.

    Args:
        provider: LLM provider instance with chat_with_tools() method.
        system: System prompt text.
        initial_message: Initial user message to start the conversation.
        tools: List of tool definitions in Anthropic format.
        tool_executor: ToolExecutor instance for dispatching tool calls.
        token_manager: Optional TokenManager for context fitting checks.
        max_rounds: Maximum number of tool-calling rounds (default 10).

    Returns:
        ToolTrace with all rounds, tool calls, final text, and total rounds.
    """
    # Step 1: Build initial messages
    messages: list[dict] = [{"role": "user", "content": initial_message}]

    # Step 2: First LLM call
    result = provider.chat_with_tools(system, messages, tools)

    # Step 3: Create trace and record first response
    trace = ToolTrace()
    trace.rounds.append(result)

    # Step 4: Loop for up to max_rounds
    round_counter = 1

    for round_num in range(1, max_rounds + 1):
        # 4a: Check stop condition
        stop_reason = result.get("stop_reason", "end_turn")
        tool_calls = result.get("tool_calls", [])

        if stop_reason != "tool_use" or not tool_calls:
            # LLM is done calling tools
            break

        # 4b: Execute each tool call and collect results
        round_results: list[dict] = []
        for tc in tool_calls:
            start_time = time.time()
            output = tool_executor.execute(tc["name"], tc["arguments"])
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000

            record = ToolCallRecord(
                name=tc["name"],
                arguments=tc["arguments"],
                result=output,
                round_number=round_num,
                duration_ms=round(duration_ms, 2),
            )
            trace.tool_calls.append(record)
            round_results.append(output)

        # 4c: Build tool result messages for the provider
        # Anthropic-style format that llm_provider.py expects for cross-provider compatibility
        messages.append({"role": "assistant", "content": result["raw_content"]})
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tc["id"],
                    "content": json.dumps(round_results[i], default=str),
                }
                for i, tc in enumerate(tool_calls)
            ],
        })

        # 4d: Check context window if token_manager provided
        if token_manager is not None:
            if not token_manager.fits_context(system, messages):
                logger.warning(
                    "Tool loop: Context window exhausted at round %d. Stopping early.",
                    round_num,
                )
                break

        # 4e: Call provider for next round
        result = provider.chat_with_tools(system, messages, tools)

        # 4f: Record response and increment counter
        trace.rounds.append(result)
        round_counter = round_num + 1

    # Step 5: Set final text and total rounds
    trace.final_text = result.get("text", "")
    trace.total_rounds = round_counter

    # Step 6: Return the trace
    return trace
