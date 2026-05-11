"""Token counting and context window management (REQ-308).

Provides token counting (via tiktoken when available, with character-based
fallback), summarization threshold detection, context window fitting
estimation, and tool result truncation.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_FALLBACK_WARNING_LOGGED = False


class TokenManager:
    """Token counting and context window management.

    Uses tiktoken's cl100k_base encoding when available. Falls back to
    a character-based approximation (len(text) // 4) if tiktoken is not
    installed, with a warning on first use.

    Args:
        max_context: Maximum context window size in tokens.
        output_reserve: Tokens reserved for model output.
    """

    def __init__(self, max_context: int = 8192, output_reserve: int = 2048) -> None:
        self.max_context = max_context
        self.output_reserve = output_reserve
        self.available = max_context - output_reserve

        # Lazy-load tiktoken
        self._enc = None
        try:
            import tiktoken

            self._enc = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            pass  # Fallback will be used; warning logged on first count

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken or character-based fallback.

        Args:
            text: The text to count tokens for.

        Returns:
            Estimated token count.
        """
        if self._enc is not None:
            return len(self._enc.encode(text))

        global _FALLBACK_WARNING_LOGGED
        if not _FALLBACK_WARNING_LOGGED:
            logger.warning(
                "tiktoken not installed -- using character-based approximation "
                "(len/4) for token counting. Install tiktoken for accurate counts."
            )
            _FALLBACK_WARNING_LOGGED = True

        return len(text) // 4

    def should_summarize(self, evidence_text: str, threshold: int = 8000) -> bool:
        """Check if evidence text exceeds the summarization threshold.

        Args:
            evidence_text: The evidence text to check.
            threshold: Token count threshold (default 8000).

        Returns:
            True if token count exceeds threshold.
        """
        return self.count_tokens(evidence_text) > threshold

    def fits_context(
        self, system: str, messages: list[dict], buffer: int = 500
    ) -> bool:
        """Estimate whether the current conversation fits in the context window.

        Counts tokens across the system prompt and all message content,
        comparing to available tokens minus a safety buffer.

        Args:
            system: The system prompt text.
            messages: List of message dicts with 'content' keys.
            buffer: Safety buffer in tokens.

        Returns:
            True if estimated total fits within available context.
        """
        total = self.count_tokens(system)
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += self.count_tokens(content)
            elif isinstance(content, list):
                # Handle Anthropic-style content blocks
                for block in content:
                    if isinstance(block, dict):
                        text = block.get("text", block.get("content", ""))
                        if isinstance(text, str):
                            total += self.count_tokens(text)
                    elif isinstance(block, str):
                        total += self.count_tokens(block)

        return total <= (self.available - buffer)

    def truncate_tool_result(self, result_text: str, max_tokens: int = 500) -> str:
        """Truncate tool result text to fit within a token budget.

        If the result exceeds max_tokens, truncates to approximately
        max_tokens worth of characters and appends a truncation marker.

        Args:
            result_text: The tool result text to potentially truncate.
            max_tokens: Maximum allowed tokens for the result.

        Returns:
            Original text if within budget, or truncated text with marker.
        """
        token_count = self.count_tokens(result_text)
        if token_count <= max_tokens:
            return result_text

        # Estimate characters per token for proportional truncation
        if self._enc is not None:
            # Use actual encoding to find the right cut point
            tokens = self._enc.encode(result_text)
            truncated_tokens = tokens[:max_tokens]
            truncated = self._enc.decode(truncated_tokens)
        else:
            # Fallback: estimate ~4 chars per token
            max_chars = max_tokens * 4
            truncated = result_text[:max_chars]

        return truncated + "... [truncated]"
