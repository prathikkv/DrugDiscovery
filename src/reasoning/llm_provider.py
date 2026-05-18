"""LLM Provider abstraction — supports Ollama, Groq, and Anthropic backends."""
import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ProviderType(Enum):
    OLLAMA = "ollama"
    GROQ = "groq"
    ANTHROPIC = "anthropic"


@dataclass
class LLMConfig:
    provider: ProviderType
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 1500


# ── Tool schema conversion ──────────────────────────────────────────────────

def anthropic_to_openai_tools(anthropic_tools: list) -> list:
    """Convert Anthropic tool format to OpenAI/Ollama format.

    Anthropic: {"name", "description", "input_schema": {...}}
    OpenAI:    {"type": "function", "function": {"name", "description", "parameters": {...}}}
    """
    result = []
    for tool in anthropic_tools:
        result.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            }
        })
    return result


# ── Standardized response format ────────────────────────────────────────────
# All providers return:
# {
#   "text": str,
#   "tool_calls": [{"name": str, "arguments": dict, "id": str}],
#   "stop_reason": "tool_use" | "end_turn",
#   "raw_content": provider-specific (for message history)
# }


# ── Ollama Provider ─────────────────────────────────────────────────────────

class OllamaProvider:
    def __init__(self, model: str = "qwen3:8b",
                 base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.name = "Ollama"

    def chat_with_tools(self, system, messages, tools, max_tokens=1500):
        import ollama

        openai_tools = anthropic_to_openai_tools(tools) if tools else []

        ollama_messages = [{"role": "system", "content": system}]
        for msg in messages:
            converted = _to_ollama_msg(msg)
            if isinstance(converted, list):
                ollama_messages.extend(converted)
            else:
                ollama_messages.append(converted)

        kwargs = {
            "model": self.model,
            "messages": ollama_messages,
            "options": {"num_predict": max_tokens},
        }
        if openai_tools:
            kwargs["tools"] = openai_tools

        response = ollama.chat(**kwargs)
        return _parse_ollama(response)

    @staticmethod
    def is_available(base_url="http://localhost:11434"):
        try:
            import urllib.request
            req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    @staticmethod
    def has_model(model="qwen3:8b", base_url="http://localhost:11434"):
        try:
            import urllib.request
            import json as _json
            req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = _json.loads(resp.read())
                names = [m.get("name", "") for m in data.get("models", [])]
                return any(model.split(":")[0] in n for n in names)
        except Exception:
            return False


def _to_ollama_msg(msg):
    """Convert internal message to Ollama format."""
    role = msg["role"]
    content = msg.get("content", "")

    # Anthropic-style tool_result list → Ollama "tool" role
    if role == "user" and isinstance(content, list):
        results = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                results.append({
                    "role": "tool",
                    "content": str(block.get("content", "")),
                })
        return results if results else [{"role": "user", "content": str(content)}]

    # Anthropic assistant content blocks → plain text
    if role == "assistant" and isinstance(content, list):
        parts = []
        for block in content:
            if hasattr(block, "text"):
                parts.append(block.text)
            elif isinstance(block, dict) and "text" in block:
                parts.append(block["text"])
        return {"role": "assistant", "content": "\n".join(parts)}

    # Raw content from previous Ollama response
    if role == "assistant" and isinstance(content, dict):
        return {"role": "assistant", "content": content.get("content", "")}

    return {"role": role, "content": str(content)}


def _parse_ollama(response):
    """Parse Ollama response into standardized format."""
    message = response.get("message", {})

    tool_calls = []
    if message.get("tool_calls"):
        for tc in message["tool_calls"]:
            func = tc.get("function", {})
            tool_calls.append({
                "name": func.get("name", ""),
                "arguments": func.get("arguments", {}),
                "id": f"ollama_{func.get('name', '')}",
            })

    return {
        "text": message.get("content", ""),
        "tool_calls": tool_calls,
        "stop_reason": "tool_use" if tool_calls else "end_turn",
        "raw_content": message,
    }


# ── Groq Provider (OpenAI-compatible) ────────────────────────────────────────

class GroqProvider:
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model
        self.name = "Groq"

    def chat_with_tools(self, system, messages, tools, max_tokens=1500):
        from openai import OpenAI

        client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.groq.com/openai/v1",
        )

        openai_tools = anthropic_to_openai_tools(tools) if tools else None

        oai_messages = [{"role": "system", "content": system}]
        for msg in messages:
            converted = _to_openai_msg(msg)
            if isinstance(converted, list):
                oai_messages.extend(converted)
            else:
                oai_messages.append(converted)

        kwargs = {
            "model": self.model,
            "messages": oai_messages,
            "max_tokens": max_tokens,
        }
        if openai_tools:
            kwargs["tools"] = openai_tools

        response = client.chat.completions.create(**kwargs)
        return _parse_openai(response)


def _to_openai_msg(msg):
    """Convert internal message to OpenAI format."""
    role = msg["role"]
    content = msg.get("content", "")

    # Anthropic tool_result list → OpenAI "tool" role messages
    if role == "user" and isinstance(content, list):
        results = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                results.append({
                    "role": "tool",
                    "tool_call_id": block.get("tool_use_id", ""),
                    "content": str(block.get("content", "")),
                })
        return results if results else [{"role": "user", "content": str(content)}]

    # Anthropic assistant content blocks (from Anthropic provider history)
    if role == "assistant" and isinstance(content, list):
        text_parts = []
        tc_list = []
        for block in content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
            elif hasattr(block, "type") and block.type == "tool_use":
                tc_list.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input),
                    }
                })
        result = {"role": "assistant", "content": "\n".join(text_parts) or None}
        if tc_list:
            result["tool_calls"] = tc_list
        return result

    # Raw content from previous Ollama/Groq response
    if role == "assistant" and isinstance(content, dict):
        return {"role": "assistant", "content": content.get("content", "")}

    return {"role": role, "content": str(content)}


def _parse_openai(response):
    """Parse OpenAI-format response into standardized format."""
    choice = response.choices[0]
    message = choice.message

    tool_calls = []
    if message.tool_calls:
        for tc in message.tool_calls:
            tool_calls.append({
                "name": tc.function.name,
                "arguments": json.loads(tc.function.arguments),
                "id": tc.id,
            })

    return {
        "text": message.content or "",
        "tool_calls": tool_calls,
        "stop_reason": "tool_use" if tool_calls else "end_turn",
        "raw_content": {"content": message.content or "", "tool_calls": message.tool_calls},
    }


# ── Anthropic Provider ──────────────────────────────────────────────────────

class AnthropicProvider:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model
        self.name = "Claude"

    def chat_with_tools(self, system, messages, tools, max_tokens=1500):
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)

        response = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            tools=tools,  # Anthropic format used directly
            messages=messages,
        )

        tool_calls = []
        text_parts = []
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append({
                    "name": block.name,
                    "arguments": block.input,
                    "id": block.id,
                })
            elif hasattr(block, "text"):
                text_parts.append(block.text)

        return {
            "text": "\n".join(text_parts),
            "tool_calls": tool_calls,
            "stop_reason": "tool_use" if response.stop_reason == "tool_use" else "end_turn",
            "raw_content": response.content,
        }


# ── Factory + Auto-detection ────────────────────────────────────────────────

def create_provider(config: LLMConfig):
    """Create an LLM provider from config."""
    if config.provider == ProviderType.OLLAMA:
        return OllamaProvider(
            model=config.model,
            base_url=config.base_url or "http://localhost:11434",
        )
    elif config.provider == ProviderType.GROQ:
        return GroqProvider(api_key=config.api_key, model=config.model)
    elif config.provider == ProviderType.ANTHROPIC:
        return AnthropicProvider(api_key=config.api_key, model=config.model)
    else:
        raise ValueError(f"Unknown provider: {config.provider}")


def auto_detect_provider() -> Optional[LLMConfig]:
    """Auto-detect the best available provider (zero config needed).

    Priority: Ollama (local) > Groq (free env var) > None (demo mode)
    """
    # 1. Check Ollama
    if OllamaProvider.is_available():
        for model in ["qwen3:8b", "qwen3:4b", "llama3.1:8b", "mistral:7b"]:
            if OllamaProvider.has_model(model):
                return LLMConfig(provider=ProviderType.OLLAMA, model=model)

    # 2. Check Groq env var
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        return LLMConfig(
            provider=ProviderType.GROQ,
            model="llama-3.3-70b-versatile",
            api_key=groq_key,
        )

    return None
