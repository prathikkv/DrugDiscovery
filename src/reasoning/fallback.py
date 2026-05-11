"""LLM provider fallback chain with audit logging (REQ-306).

Wraps the existing Ollama, Groq, and Anthropic providers from
bioorchestrator_real/utils/llm_provider.py into a resilient chain that
tries providers in order: Ollama -> Groq -> Anthropic. Each fallback
event is recorded to the audit trail for provenance tracking.

IMPORTANT (Research Pitfall 4): Do NOT switch providers mid-loop.
If a provider fails during a tool-calling round, restart the ENTIRE
reasoning on the next provider.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Optional

from bioorchestrator_real.utils.llm_provider import (
    AnthropicProvider,
    GroqProvider,
    OllamaProvider,
)

logger = logging.getLogger(__name__)


class FallbackChain:
    """LLM provider fallback chain with ordered provider selection and audit logging.

    Tries providers in order: Ollama (local) -> Groq (cloud, free) -> Anthropic (cloud).
    Each provider is only added to the chain if it is available (Ollama running)
    or configured (API key set). Fallback events are recorded to the audit trail.

    Args:
        audit_trail: Optional AuditTrail instance for recording fallback events.
        ollama_model: Ollama model name (default: qwen3:8b).
        groq_model: Groq model name (default: llama-3.3-70b-versatile).
        anthropic_model: Anthropic model name (default: claude-sonnet-4-20250514).
    """

    def __init__(
        self,
        audit_trail: Optional[Any] = None,
        ollama_model: str = "qwen3:8b",
        groq_model: str = "llama-3.3-70b-versatile",
        anthropic_model: str = "claude-sonnet-4-20250514",
    ) -> None:
        self.audit = audit_trail
        self.providers: list = []
        self.last_fallback_events: list[tuple[str, str]] = []

        # Build provider chain by checking availability in order
        # a. Ollama: check if server is running
        if OllamaProvider.is_available():
            self.providers.append(OllamaProvider(model=ollama_model))
            logger.info("FallbackChain: Ollama provider available (model=%s)", ollama_model)

        # b. Groq: check for API key
        groq_key = os.environ.get("GROQ_API_KEY")
        if groq_key:
            self.providers.append(GroqProvider(api_key=groq_key, model=groq_model))
            logger.info("FallbackChain: Groq provider available (model=%s)", groq_model)

        # c. Anthropic: check for API key
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            self.providers.append(AnthropicProvider(api_key=anthropic_key, model=anthropic_model))
            logger.info("FallbackChain: Anthropic provider available (model=%s)", anthropic_model)

        if not self.providers:
            logger.warning(
                "FallbackChain: No LLM providers available. "
                "Start Ollama or set GROQ_API_KEY / ANTHROPIC_API_KEY."
            )

    def get_provider(self) -> tuple[object, str]:
        """Return the first available provider and its name.

        Returns:
            Tuple of (provider_instance, provider_name).

        Raises:
            RuntimeError: If no providers are available.
        """
        if not self.providers:
            raise RuntimeError("No LLM provider available")
        provider = self.providers[0]
        return (provider, provider.name)

    def execute_with_fallback(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute a function with automatic provider fallback.

        Tries each provider in order. On failure, logs the error, records
        a fallback event in the audit trail, and moves to the next provider.

        IMPORTANT: Per research Pitfall 4, do NOT switch providers mid-loop.
        If a provider fails during a tool-calling round, this restarts the
        ENTIRE reasoning on the next provider.

        Args:
            fn: Callable that takes (provider, *args, **kwargs) and returns a result.
            *args: Additional positional arguments passed to fn.
            **kwargs: Additional keyword arguments passed to fn.

        Returns:
            The result from the first successful provider.

        Raises:
            RuntimeError: If all providers fail, with collected error messages.
        """
        if not self.providers:
            raise RuntimeError("No LLM provider available")

        errors: list[tuple[str, str]] = []
        self.last_fallback_events = []

        for i, provider in enumerate(self.providers):
            try:
                result = fn(provider, *args, **kwargs)
                return result
            except Exception as e:
                error_str = str(e)
                errors.append((provider.name, error_str))
                logger.warning(
                    "FallbackChain: Provider %s failed: %s",
                    provider.name,
                    error_str,
                )

                # Determine next provider name
                next_provider_name = (
                    self.providers[i + 1].name
                    if i + 1 < len(self.providers)
                    else "none"
                )

                # Store fallback event for provenance tracker
                self.last_fallback_events.append((provider.name, error_str))

                # Record fallback event to audit trail
                if self.audit is not None:
                    try:
                        self.audit.append_record(
                            user_id="system",
                            action="llm_fallback",
                            resource_type="ai_reasoning",
                            resource_id=provider.name,
                            details={
                                "error": error_str,
                                "from_provider": provider.name,
                                "to_provider": next_provider_name,
                            },
                        )
                    except Exception as audit_err:
                        logger.warning(
                            "FallbackChain: Failed to record audit event: %s",
                            audit_err,
                        )

        # All providers failed
        error_summary = "; ".join(f"{name}: {err}" for name, err in errors)
        raise RuntimeError(f"All LLM providers failed: {error_summary}")

    @property
    def available_providers(self) -> list[str]:
        """Return list of available provider names."""
        return [p.name for p in self.providers]
