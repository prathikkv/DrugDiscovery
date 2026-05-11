# Phase 4: AI Reasoning Engine - Research

**Researched:** 2026-05-11
**Domain:** LLM tool-calling orchestration, multi-mode scientific reasoning, provenance tracking
**Confidence:** MEDIUM-HIGH

## Summary

Phase 4 builds the AI reasoning layer that transforms raw omics data and evidence into structured scientific insights. The core challenge is orchestrating an LLM (primarily Ollama qwen3:8b with Groq/Anthropic fallbacks) through 14+ tool calls across five distinct reasoning modes (hypothesis, synthesis, contradiction, gap, confidence), while maintaining full provenance and hallucination safeguards.

The existing codebase provides strong foundations: `bioorchestrator_real/utils/llm_provider.py` already implements a multi-provider abstraction (OllamaProvider, GroqProvider, AnthropicProvider) with standardized response format and tool schema conversion. `bioorchestrator_real/utils/ai_copilot.py` demonstrates a working agentic loop with 10 tool definitions and 3-round tool calling. The key work is: (1) expanding from 10 tools to 14+ that bridge omics pipeline and evidence APIs, (2) adding five structured reasoning modes with mode-specific system prompts, (3) implementing full provenance tracking with SHA256 prompt hashing and audit trail integration, (4) adding hallucination safeguards (citation checking, source counting), and (5) building a robust fallback chain with token management.

**Primary recommendation:** Extend the existing `llm_provider.py` abstraction (do not replace it) with a new `src/reasoning/` module containing the orchestrator, tool definitions, prompt registry, and provenance tracker. Use Ollama's native tool-calling via the `ollama` Python SDK (>=0.6.0), which supports OpenAI-compatible tool schemas and agentic loops. The existing `ai_copilot.py` pattern of "call, check tool_calls, execute, repeat" is the correct architecture -- adapt it with a 10-round limit and per-round provenance recording.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ollama | >=0.6.0 | Local LLM tool-calling (primary provider) | Official Python SDK. v0.6+ has native tool-calling with OpenAI-compatible tool schemas. Supports `response.message.tool_calls` with function name and arguments. Already used in existing `llm_provider.py`. |
| openai | >=2.30.0 | Groq API client (OpenAI-compatible) | Groq uses OpenAI-compatible API at `api.groq.com/openai/v1`. Already used by existing `GroqProvider`. llama-3.3-70b-versatile has 131K context window and supports parallel tool calls. |
| anthropic | >=0.95.0 | Anthropic Claude API (last-resort fallback) | Official SDK with native tool-use support. Already used by existing `AnthropicProvider`. Claude uses Anthropic-format tools directly (no conversion needed). |
| hashlib (stdlib) | 3.x | SHA256 hashing for prompt versioning and evidence hashing | Already used in `src/compliance/audit_trail.py` for hash chains. Zero dependencies. Used for prompt version tracking (REQ-304) and input evidence hashes (REQ-305). |
| pydantic | >=2.11.0 | Structured output parsing for reasoning results | Recommended in STACK.md. Use for: reasoning output models, tool argument validation, provenance record schema, structured claim+citation objects. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tiktoken | >=0.9.0 | Token counting for context management | Use for estimating token counts before sending to LLM. Required by REQ-308 for the 8K token threshold check. Works for OpenAI/Groq tokenization; approximate for Ollama models. |
| tenacity | >=9.1.4 | Retry with backoff for LLM calls | Already used across evidence sources. Use for retrying transient Ollama/Groq/Anthropic failures before triggering fallback chain (REQ-306). |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom orchestrator | LangChain | Already rejected in STACK.md: "Adds ~200MB of transitive dependencies, abstracts away the tool-calling control needed for multi-step scientific reasoning." Custom is correct here. |
| tiktoken | Approximate char/4 estimation | tiktoken gives exact counts for OpenAI models; char/4 is ~85% accurate. tiktoken is lightweight (<5MB) and worth the accuracy for the 8K threshold (REQ-308). |
| Pydantic models | Dataclasses | Pydantic provides validation, JSON serialization, and LLM output parsing. Dataclasses lack validation. Already in project stack. |

**Installation:**
```bash
pip install "ollama>=0.6.0" "openai>=2.30.0" "anthropic>=0.95.0" "pydantic>=2.11.0" tiktoken "tenacity>=9.1.4"
```

## Architecture Patterns

### Recommended Project Structure

```
src/
├── reasoning/
│   ├── __init__.py           # Public API: ReasoningEngine, ReasoningMode
│   ├── engine.py             # Multi-mode reasoning orchestrator (REQ-301)
│   ├── tool_loop.py          # Agentic tool-calling loop with 10-round limit (REQ-302)
│   ├── tools.py              # 14+ LLM tool definitions (REQ-303)
│   ├── tool_executor.py      # Tool dispatch: routes tool calls to pipeline/evidence
│   ├── prompts.py            # Versioned system prompts per mode with SHA256 (REQ-304)
│   ├── provenance.py         # Output provenance: model, prompt_version, hashes (REQ-305)
│   ├── fallback.py           # LLM fallback chain: Ollama -> Groq -> Anthropic (REQ-306)
│   ├── hallucination.py      # Citation checking, source counting (REQ-307)
│   ├── token_manager.py      # Token counting, evidence summarization (REQ-308)
│   └── models.py             # Pydantic models: ReasoningResult, Claim, ToolTrace
├── evidence/                 # (Phase 3 - exists)
│   └── aggregator.py         # Evidence fetch orchestrator
├── pipeline/                 # (Phase 2 - exists)
│   └── ...                   # Omics pipeline stages
└── compliance/               # (Phase 1 - exists)
    └── audit_trail.py        # Hash-chain audit trail
```

### Pattern 1: Multi-Mode Reasoning Orchestrator (REQ-301)

**What:** A single `ReasoningEngine` class that dispatches to five reasoning modes, each with a mode-specific system prompt that shapes LLM behavior toward that mode's analytical purpose.

**When to use:** Every reasoning request goes through this orchestrator.

**Example:**
```python
# Source: Derived from existing ai_copilot.py pattern + requirements
from enum import Enum
from dataclasses import dataclass

class ReasoningMode(Enum):
    HYPOTHESIS = "hypothesis"    # Generate testable hypotheses from evidence
    SYNTHESIS = "synthesis"      # Synthesize findings across sources
    CONTRADICTION = "contradiction"  # Identify conflicting evidence
    GAP = "gap"                  # Flag missing evidence and data gaps
    CONFIDENCE = "confidence"    # Assess confidence levels with justification

class ReasoningEngine:
    def __init__(self, fallback_chain, tool_executor, prompt_registry, audit_trail):
        self.fallback_chain = fallback_chain
        self.tool_executor = tool_executor
        self.prompts = prompt_registry
        self.audit = audit_trail

    def reason(
        self,
        gene_symbol: str,
        mode: ReasoningMode,
        disease_context: str | None = None,
        user_id: str = "system",
    ) -> ReasoningResult:
        # 1. Get versioned prompt for this mode
        system_prompt, prompt_hash = self.prompts.get(mode)

        # 2. Build initial user message
        user_msg = self._build_user_message(gene_symbol, disease_context)

        # 3. Run tool-calling loop (max 10 rounds)
        trace = self.tool_loop.run(
            system=system_prompt,
            initial_message=user_msg,
            tools=TOOL_DEFINITIONS,
            max_rounds=10,
        )

        # 4. Parse structured output, check hallucinations
        result = self._parse_and_validate(trace, mode)

        # 5. Record provenance in audit trail
        self._record_provenance(result, prompt_hash, user_id)

        return result
```

### Pattern 2: Agentic Tool-Calling Loop (REQ-302)

**What:** A loop that sends messages to the LLM, checks for tool calls, executes them, appends results, and repeats -- up to 10 rounds. Uses the existing provider abstraction.

**When to use:** Every LLM interaction that involves tools.

**Example:**
```python
# Source: Adapted from bioorchestrator_real/utils/ai_copilot.py query_live()
# and Ollama docs: https://docs.ollama.com/capabilities/tool-calling

def run_tool_loop(provider, system, messages, tools, max_rounds=10):
    """Execute agentic tool-calling loop with provenance tracking.

    Returns a ToolTrace with all rounds, tool calls, and final output.
    """
    trace = ToolTrace()
    result = provider.chat_with_tools(system, messages, tools)
    trace.add_round(result)

    for round_num in range(max_rounds):
        if result["stop_reason"] != "tool_use" or not result["tool_calls"]:
            break

        # Execute each tool call and collect results
        tool_results = []
        for tc in result["tool_calls"]:
            output = execute_tool(tc["name"], tc["arguments"])
            trace.add_tool_call(tc["name"], tc["arguments"], output)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc["id"],
                "content": json.dumps(output, default=str),
            })

        # Append to conversation
        messages.append({"role": "assistant", "content": result["raw_content"]})
        messages.append({"role": "user", "content": tool_results})

        # Next round
        result = provider.chat_with_tools(system, messages, tools)
        trace.add_round(result)

    trace.final_text = result["text"]
    return trace
```

### Pattern 3: LLM Fallback Chain (REQ-306)

**What:** Try Ollama first, fall back to Groq, then Anthropic. Each fallback is logged.

**When to use:** Wraps the tool-calling loop. Triggered when a provider raises an exception or is unavailable.

**Example:**
```python
# Source: Derived from existing llm_provider.py auto_detect_provider() pattern

class FallbackChain:
    """Try providers in order: Ollama -> Groq -> Anthropic."""

    def __init__(self, audit_trail=None):
        self.providers = self._build_chain()
        self.audit = audit_trail

    def _build_chain(self):
        chain = []
        # 1. Ollama (local, preferred)
        if OllamaProvider.is_available():
            chain.append(OllamaProvider(model="qwen3:8b"))
        # 2. Groq (fast cloud)
        groq_key = os.environ.get("GROQ_API_KEY")
        if groq_key:
            chain.append(GroqProvider(api_key=groq_key, model="llama-3.3-70b-versatile"))
        # 3. Anthropic (last resort)
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            chain.append(AnthropicProvider(api_key=anthropic_key))
        return chain

    def get_provider(self) -> tuple[object, str]:
        """Return first available provider and its name."""
        for provider in self.providers:
            return provider, provider.name
        raise RuntimeError("No LLM provider available")

    def execute_with_fallback(self, fn, *args, **kwargs):
        """Execute fn(provider, ...) with fallback on failure."""
        errors = []
        for provider in self.providers:
            try:
                return fn(provider, *args, **kwargs)
            except Exception as e:
                errors.append((provider.name, str(e)))
                if self.audit:
                    self.audit.append_record(
                        user_id="system",
                        action="llm_fallback",
                        resource_type="reasoning",
                        resource_id=provider.name,
                        details={"error": str(e), "next": self.providers[len(errors)].name if len(errors) < len(self.providers) else "none"},
                    )
        raise RuntimeError(f"All providers failed: {errors}")
```

### Pattern 4: Versioned Prompt Registry (REQ-304)

**What:** Store system prompts as strings with pre-computed SHA256 hashes. Each reasoning mode has its own prompt. Prompt changes produce new hashes automatically.

**When to use:** Every LLM call must record which prompt version was used.

**Example:**
```python
# Source: Derived from hashlib patterns in src/compliance/audit_trail.py

import hashlib

class PromptRegistry:
    """Versioned system prompts with SHA256 tracking."""

    def __init__(self):
        self._prompts = {}
        self._register_defaults()

    def _register_defaults(self):
        for mode in ReasoningMode:
            text = PROMPT_TEMPLATES[mode]
            sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
            self._prompts[mode] = (text, sha)

    def get(self, mode: ReasoningMode) -> tuple[str, str]:
        """Return (prompt_text, sha256_hash) for a reasoning mode."""
        return self._prompts[mode]

    def register(self, mode: ReasoningMode, text: str) -> str:
        """Register a new prompt version. Returns SHA256 hash."""
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self._prompts[mode] = (text, sha)
        return sha
```

### Pattern 5: Provenance Record (REQ-305)

**What:** Every AI output gets a provenance tag with model name, prompt version, input evidence hashes, tools used, and reasoning chain. Stored in the existing audit trail.

**When to use:** After every reasoning run completes.

**Example:**
```python
# Source: Derived from src/compliance/audit_trail.py append_record()

@dataclass
class ProvenanceRecord:
    model_name: str              # e.g., "qwen3:8b", "llama-3.3-70b-versatile"
    provider_name: str           # e.g., "Ollama", "Groq", "Claude"
    prompt_version: str          # SHA256 of the system prompt used
    input_evidence_hashes: dict  # {source_name: sha256_of_evidence_data}
    tools_used: list[str]        # ["get_expression", "query_opentargets", ...]
    tool_rounds: int             # Number of tool-calling rounds completed
    reasoning_chain: list[dict]  # Full trace: [{role, content/tool_calls}]
    fallback_events: list[dict]  # [{provider, error, timestamp}]
    timestamp: str               # ISO 8601 timestamp

    def to_audit_details(self) -> dict:
        """Convert to dict for audit trail storage."""
        return {
            "model": self.model_name,
            "provider": self.provider_name,
            "prompt_version": self.prompt_version,
            "input_evidence_hashes": self.input_evidence_hashes,
            "tools_used": self.tools_used,
            "tool_rounds": self.tool_rounds,
            "fallback_events": self.fallback_events,
        }
```

### Anti-Patterns to Avoid

- **Custom ReAct parser:** REQ-302 explicitly says "Ollama native tool-calling API (not custom ReAct parser)." Do NOT parse text output for tool call patterns. Use `response.message.tool_calls` (Ollama SDK) or `response["tool_calls"]` (existing provider abstraction).

- **Unbounded tool loops:** Always enforce max_rounds=10 (REQ-302). Runaway loops burn tokens and time. Exit early if the LLM stops requesting tools.

- **Storing prompts in database:** Prompts are code, not data. Store them in Python files (`prompts.py`), version with git, hash with SHA256. The hash goes in the audit trail, not the full prompt text (which is in source control).

- **Building a new LLM abstraction:** The existing `llm_provider.py` already handles Ollama/Groq/Anthropic with tool schema conversion and a standardized response format. Extend it, do not replace it.

- **Using LangChain:** Already rejected in STACK.md. The custom provider abstraction is 300 lines and does exactly what is needed without 200MB of dependencies.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token counting | Custom char/word estimator | `tiktoken` library | Accurate BPE token counting for the 8K threshold check. Custom estimators are off by 15-20%. tiktoken is <5MB. |
| Tool schema conversion | Manual JSON construction | Existing `anthropic_to_openai_tools()` in `llm_provider.py` | Already handles Anthropic-to-OpenAI format conversion for Ollama and Groq. Tested and working. |
| Multi-provider abstraction | New LLM framework | Existing `OllamaProvider`, `GroqProvider`, `AnthropicProvider` | Already standardizes `chat_with_tools()` across 3 providers. Returns `{text, tool_calls, stop_reason, raw_content}`. |
| SHA256 hashing | Custom hash function | `hashlib.sha256` (stdlib) | Already used in `audit_trail.py`. Standard, correct, zero dependencies. |
| Retry with backoff | Custom retry loops | `tenacity` library | Already used across all 6 evidence sources. Decorator-based, configurable, battle-tested. |
| Audit trail recording | New logging system | Existing `AuditTrail.append_record()` | Hash-chain audit trail already built (Phase 1). Use `resource_type="ai_reasoning"` for reasoning provenance records. |

**Key insight:** The existing codebase already solves 60% of the infrastructure problems. The custom `llm_provider.py` is the right abstraction level. Adding LangChain or building a new framework would be wasted effort on an 8GB RAM machine.

## Common Pitfalls

### Pitfall 1: Qwen3:8b Tool-Calling Unreliability

**What goes wrong:** Qwen3 models have known issues with tool calling in Ollama. GitHub issue #14601 documents malformed tool definitions (Go struct serialization instead of JSON) and interference between the `think` parameter and tool calling. Smaller Qwen3 models showed non-monotonic performance in benchmarks (0.6B > 4B > 1.7B).

**Why it happens:** The Ollama-Qwen3 template serialization had bugs. The `/think`/`/no_think` flags interfere with tool-calling prompts. Model size does not predict tool-calling quality.

**How to avoid:** (1) Pin Ollama version to one known to have the fix (PR #14695 merged the JSON serialization fix). (2) Test tool calling with qwen3:8b early in implementation -- the existing prior decision R-005 flags this: "qwen3:8b tool-calling reliability unknown -- needs testing in Phase 4." (3) If qwen3:8b fails, the fallback chain (REQ-306) catches it automatically. (4) Consider setting `think=False` for tool-calling rounds if thinking mode interferes with tool output parsing.

**Warning signs:** LLM returns text descriptions of what tools it "would" call instead of actual `tool_calls` in the response. Empty `tool_calls` list despite the model describing tool invocations in its text output.

### Pitfall 2: Context Window Overflow

**What goes wrong:** Evidence from 6 sources + omics data can easily exceed 8K tokens. Qwen3:8b has a default context of 4K in Ollama (configurable to 40K), but performance degrades with long contexts. Tool results accumulate across rounds, consuming context rapidly.

**Why it happens:** Each evidence source returns 500-2000 tokens of data. Six sources = 3000-12000 tokens. Plus system prompt (~1000 tokens), user message (~200 tokens), and previous tool results accumulating across rounds.

**How to avoid:** (1) Implement REQ-308: summarize evidence exceeding 8K tokens before including in context. (2) Set Ollama context via `num_ctx` option (use 8192 or 16384, not the full 40K -- quality degrades at high context on small models). (3) Reserve 2K tokens for output as specified by REQ-308. (4) Truncate tool results to essential fields before appending to conversation. (5) Use tiktoken to count tokens before each LLM call.

**Warning signs:** LLM produces truncated or garbled output. Ollama returns errors about context length. Quality of reasoning degrades as more tool rounds are added.

### Pitfall 3: Hallucination in Claims Without Citation

**What goes wrong:** LLM makes claims that sound plausible but are not grounded in tool call results. Common with synthesis and hypothesis modes where the LLM has latitude to reason beyond the data.

**Why it happens:** LLMs are trained to be helpful and will fill gaps with plausible-sounding information. Without explicit grounding constraints, claims may reference knowledge from training data rather than from tool results.

**How to avoid:** (1) System prompts must explicitly require citations: "Every claim must reference a specific tool result using [Source: ToolName] format." (2) Post-processing validation: parse output for `[Source: X]` citations, verify each citation corresponds to an actual tool call in the trace. (3) For confidence >0.8, verify 3+ independent sources (REQ-307). (4) Flag uncited claims as LOW confidence automatically.

**Warning signs:** Claims about specific numerical values that do not appear in any tool result. Citations to sources that were never queried. Statements about mechanisms or pathways not mentioned in evidence data.

### Pitfall 4: Fallback Chain Token Format Mismatch

**What goes wrong:** When falling back from Ollama to Groq to Anthropic, the conversation history format differs between providers. Tool results formatted for Ollama may not parse correctly for Groq, and Anthropic uses a different tool result format entirely.

**Why it happens:** Ollama uses `{"role": "tool", "content": "...", "tool_name": "..."}`. Groq/OpenAI uses `{"role": "tool", "content": "...", "tool_call_id": "..."}`. Anthropic uses `{"type": "tool_result", "tool_use_id": "...", "content": "..."}` inside a user message.

**How to avoid:** The existing `llm_provider.py` already handles this via `_to_ollama_msg()`, `_to_openai_msg()`, and direct Anthropic format. The key is: do NOT start a tool loop on one provider and switch mid-loop. If a provider fails, restart the entire reasoning from scratch on the next provider in the chain.

**Warning signs:** Groq/Anthropic returns errors about malformed messages. Tool results appear as raw JSON in the conversation instead of being processed by the model.

### Pitfall 5: Audit Trail Size from Full Reasoning Chains

**What goes wrong:** REQ-305 requires storing the "complete reasoning chain" in the audit trail. A 10-round tool loop with 14 tools can produce 50KB+ of data per reasoning request. This bloats the SQLite audit trail.

**Why it happens:** Each tool call includes arguments and results. Evidence data payloads are large (PubMed abstracts, OpenTargets associations, etc.).

**How to avoid:** (1) Store a reference (hash) to the full reasoning chain, not the chain itself, in the audit trail `details_json`. (2) Store full reasoning chains in a separate table or file, indexed by the hash. (3) Alternatively, truncate tool results in the stored chain to first 500 chars each, with a hash of the full result for verification. (4) The audit trail `details_json` column should contain provenance metadata (model, prompt_version, tools_used, hashes) while the full trace lives elsewhere.

**Warning signs:** Audit database grows rapidly (>100MB after a few dozen reasoning runs). SQLite queries on the audit table slow down.

## Code Examples

### Tool Definition Format (REQ-303)

```python
# Source: Adapted from bioorchestrator_real/utils/ai_copilot.py TOOLS list
# and Ollama docs: https://docs.ollama.com/capabilities/tool-calling

# Tools use Anthropic-format input_schema (converted to OpenAI format by llm_provider.py)
TOOL_DEFINITIONS = [
    # -- Omics data tools (4) --
    {
        "name": "get_gene_expression",
        "description": "Get expression statistics for a gene across all cell types in the loaded scRNA-seq dataset. Returns mean expression and percent of cells expressing the gene per cell type.",
        "input_schema": {
            "type": "object",
            "properties": {
                "gene": {"type": "string", "description": "Gene symbol (e.g., 'EGFR', 'GIPR')"}
            },
            "required": ["gene"]
        }
    },
    {
        "name": "get_enrichment",
        "description": "Get fold enrichment values for a gene across cell types. Shows which cell types have above-average expression.",
        "input_schema": {
            "type": "object",
            "properties": {
                "gene": {"type": "string", "description": "Gene symbol"}
            },
            "required": ["gene"]
        }
    },
    {
        "name": "get_de_results",
        "description": "Get differential expression results for a cell type vs all others. Returns top DE genes with log2FC and significance.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_type": {"type": "string", "description": "Cell type name (e.g., 'Pericyte')"},
                "n_top": {"type": "integer", "description": "Number of top genes (default: 10)", "default": 10},
                "direction": {"type": "string", "enum": ["up", "down", "all"], "default": "up"}
            },
            "required": []
        }
    },
    {
        "name": "get_cell_composition",
        "description": "Get cell type counts and proportions in the dataset.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    # -- Evidence source tools (6) --
    {
        "name": "query_opentargets",
        "description": "Query OpenTargets Platform for genetic associations, tractability, known drugs, and disease links for a gene.",
        "input_schema": {
            "type": "object",
            "properties": {
                "gene_symbol": {"type": "string", "description": "Gene symbol (e.g., 'EGFR')"},
                "disease_context": {"type": "string", "description": "Optional disease name to filter associations"}
            },
            "required": ["gene_symbol"]
        }
    },
    {
        "name": "query_dgidb",
        "description": "Query DGIdb for drug-gene interactions and druggability classification.",
        "input_schema": {
            "type": "object",
            "properties": {
                "gene_symbol": {"type": "string", "description": "Gene symbol"}
            },
            "required": ["gene_symbol"]
        }
    },
    {
        "name": "query_pubmed",
        "description": "Search PubMed for recent publications about a gene, with abstracts and AI summary.",
        "input_schema": {
            "type": "object",
            "properties": {
                "gene_symbol": {"type": "string", "description": "Gene symbol"},
                "disease_context": {"type": "string", "description": "Optional disease to narrow search"}
            },
            "required": ["gene_symbol"]
        }
    },
    {
        "name": "query_clinicaltrials",
        "description": "Search ClinicalTrials.gov for active and completed trials involving a gene target.",
        "input_schema": {
            "type": "object",
            "properties": {
                "gene_symbol": {"type": "string", "description": "Gene symbol"},
                "disease_context": {"type": "string", "description": "Optional disease/indication"}
            },
            "required": ["gene_symbol"]
        }
    },
    {
        "name": "query_uniprot",
        "description": "Query UniProt for protein function, domains, subcellular location, and structure availability.",
        "input_schema": {
            "type": "object",
            "properties": {
                "gene_symbol": {"type": "string", "description": "Gene symbol"}
            },
            "required": ["gene_symbol"]
        }
    },
    {
        "name": "query_chembl",
        "description": "Query ChEMBL for bioactivity data, existing compounds, and mechanism of action.",
        "input_schema": {
            "type": "object",
            "properties": {
                "gene_symbol": {"type": "string", "description": "Gene symbol"}
            },
            "required": ["gene_symbol"]
        }
    },
    # -- Additional analysis tools (4+) --
    {
        "name": "get_qc_summary",
        "description": "Get QC filtering summary showing cell counts at each filtering stage.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_cell_type_markers",
        "description": "Get top differentially expressed marker genes for a cell type, ranked by log2 fold change.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_type": {"type": "string", "description": "Cell type name"},
                "n_top": {"type": "integer", "description": "Number of top markers", "default": 5}
            },
            "required": []
        }
    },
    {
        "name": "get_pipeline_summary",
        "description": "Get overall pipeline summary including dataset info, processing parameters, and key findings.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_batch_correction",
        "description": "Get batch correction details including method, batch variable, and donor count.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
]
# Total: 14 tool definitions (4 omics + 6 evidence + 4 analysis)
```

### Token Management (REQ-308)

```python
# Source: tiktoken docs + REQ-308 requirements

import tiktoken

class TokenManager:
    """Manage context window: count tokens, summarize if needed."""

    def __init__(self, max_context=8192, output_reserve=2048):
        self.max_context = max_context
        self.output_reserve = output_reserve
        self.available = max_context - output_reserve  # 6144 tokens for input
        # Use cl100k_base as approximation (works for most models)
        self._enc = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self._enc.encode(text))

    def should_summarize(self, evidence_text: str) -> bool:
        return self.count_tokens(evidence_text) > 8000  # REQ-308 threshold

    def summarize_evidence(self, evidence_text: str, provider) -> str:
        """Summarize evidence to fit context window."""
        prompt = (
            "Summarize the following evidence data concisely, preserving all "
            "key findings, numerical values, and source attributions. "
            "Keep it under 2000 tokens."
        )
        result = provider.chat_with_tools(
            system=prompt,
            messages=[{"role": "user", "content": evidence_text}],
            tools=[],  # No tools for summarization
        )
        return result["text"]
```

### Hallucination Check (REQ-307)

```python
# Source: REQ-307 requirements + citation-grounding research patterns

import re

def check_citations(text: str, tool_trace: ToolTrace) -> list[dict]:
    """Verify every claim cites a tool call result.

    Returns list of issues found.
    """
    issues = []

    # Extract all [Source: X] citations from the text
    citations = re.findall(r'\[Source:\s*(\w+)\]', text)
    tools_called = {tc["name"] for tc in tool_trace.all_tool_calls}

    # Map citation labels to tool names
    CITATION_TO_TOOL = {
        "OpenTargets": "query_opentargets",
        "DGIdb": "query_dgidb",
        "PubMed": "query_pubmed",
        "ClinicalTrials": "query_clinicaltrials",
        "UniProt": "query_uniprot",
        "ChEMBL": "query_chembl",
        "Expression": "get_gene_expression",
        "Enrichment": "get_enrichment",
        "DE": "get_de_results",
        "QC": "get_qc_summary",
    }

    for citation in citations:
        tool_name = CITATION_TO_TOOL.get(citation)
        if tool_name and tool_name not in tools_called:
            issues.append({
                "type": "phantom_citation",
                "citation": citation,
                "detail": f"Cites {citation} but tool {tool_name} was never called",
            })

    # Check for uncited claims (paragraphs without any [Source:] tag)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    for para in paragraphs:
        if not re.search(r'\[Source:', para) and len(para) > 100:
            issues.append({
                "type": "uncited_claim",
                "detail": f"Paragraph without citation: {para[:80]}...",
            })

    return issues


def check_confidence_sources(claims: list[dict], tool_trace: ToolTrace) -> list[dict]:
    """REQ-307: claims with confidence >0.8 require 3+ independent sources."""
    issues = []
    for claim in claims:
        if claim.get("confidence", 0) > 0.8:
            sources = claim.get("sources", [])
            if len(sources) < 3:
                issues.append({
                    "type": "insufficient_sources",
                    "claim": claim.get("text", "")[:80],
                    "confidence": claim["confidence"],
                    "sources_found": len(sources),
                    "sources_required": 3,
                })
    return issues
```

### Ollama Tool-Calling (native SDK, REQ-302)

```python
# Source: https://docs.ollama.com/capabilities/tool-calling
# Note: The existing llm_provider.py OllamaProvider already wraps this.
# This shows the underlying SDK pattern for reference.

import ollama

# Native Ollama SDK tool calling
response = ollama.chat(
    model="qwen3:8b",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Analyze EGFR expression patterns"},
    ],
    tools=openai_format_tools,  # OpenAI-compatible tool schemas
    options={"num_ctx": 8192, "num_predict": 1500},
)

# Check for tool calls
if response.message.tool_calls:
    for tc in response.message.tool_calls:
        name = tc.function.name
        args = tc.function.arguments  # Already a Python dict
        result = execute_tool(name, args)

        # Append to messages for next round
        messages.append(response.message)  # Assistant message with tool_calls
        messages.append({
            "role": "tool",
            "content": json.dumps(result),
            "tool_name": name,  # Ollama-specific field
        })
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom ReAct text parsing | Native tool_calls in API response | Ollama 0.4+ (Nov 2024) | No regex parsing needed. LLM returns structured tool calls. REQ-302 explicitly requires this. |
| Manual JSON tool schemas | Python function auto-parsing (Ollama 0.4+) | Ollama 0.4 (Nov 2024) | Can pass Python functions directly as tools. BUT: for cross-provider compatibility, stick with explicit JSON schemas (what existing llm_provider.py uses). |
| Single provider, no fallback | Multi-provider fallback chains | Industry standard 2024+ | Essential for reliability. Local Ollama may be down or produce poor results. Cloud fallbacks provide safety net. |
| Prompt text in code without versioning | SHA256-hashed prompt versions in audit trails | Regulatory-driven 2024+ | Required for 21 CFR Part 11 compliance. Every AI output must trace to exact prompt version. |
| Streaming tool calls (new) | Accumulated tool_calls from stream chunks | Ollama 0.6+ | Streaming + tool calling is now supported. Not needed for this phase (non-interactive batch reasoning), but available for future copilot integration. |

**Deprecated/outdated:**
- Custom ReAct parsers: Replaced by native tool_calls. Do not build.
- ollama Python SDK < 0.4: Tool calling was unreliable before 0.4. Pin to >=0.6.0.
- LLM_SUMMARY_MODEL env var pattern (from PubMed source): Phase 4 replaces this with the fallback chain. The `src.execution.llm` lazy import in `pubmed.py` should be resolved to use the reasoning engine's provider.

## Open Questions

1. **Qwen3:8b tool-calling quality with 14 tools**
   - What we know: Qwen3:8b is untested with this many tools. Benchmark data exists for 0.6B and 4B variants (0.880 score on simple calls), but 8B was not benchmarked. Prior decision R-005 explicitly flags this as unknown.
   - What's unclear: Whether qwen3:8b can reliably select the right tool from 14 options, especially for the more nuanced reasoning modes (contradiction, gap).
   - Recommendation: Implement early and test. If tool selection is poor, consider (a) reducing tool count by grouping related tools, (b) using `think=True` to let the model reason about tool selection, or (c) falling back to Groq's llama-3.3-70b which has 131K context and likely better tool selection.

2. **Ollama `num_ctx` setting for tool-calling quality vs. performance**
   - What we know: Ollama defaults to 4K context for qwen3:8b. The model supports up to 40K (32K native + YaRN to 128K). Setting too high degrades quality and speed on 8GB RAM.
   - What's unclear: The sweet spot between context size and quality for tool-calling with evidence data on constrained hardware.
   - Recommendation: Start with `num_ctx=8192`. This provides room for system prompt (~1K), user message (~200), and 5-6 tool result rounds (~1K each) while reserving 2K for output. Test with 16384 if evidence data is consistently truncated.

3. **Evidence data serialization for tool results**
   - What we know: The evidence aggregator returns `AggregatedEvidence` with nested dicts per source. Some sources return large payloads (PubMed abstracts, OpenTargets associations).
   - What's unclear: The optimal serialization of evidence data as tool results -- full JSON? Summary only? Selected fields?
   - Recommendation: Tool executor should return compact summaries of evidence, not full payloads. For example, OpenTargets: top 5 associations with scores, tractability labels, drug count. PubMed: paper count, top 3 titles, AI summary if available. Keep each tool result under 500 tokens.

4. **Where to store full reasoning traces (REQ-305)**
   - What we know: The audit trail uses SQLite with a `details_json` TEXT column. Full reasoning traces (10 rounds, 14 tools) could be 50KB+.
   - What's unclear: Whether to store full traces in the audit trail, a separate SQLite table, or JSON files.
   - Recommendation: Store provenance metadata (model, prompt_hash, tools_used, input_hashes) in the audit trail `details_json`. Store full reasoning traces in a separate `data/reasoning_traces/` directory as JSON files, referenced by a trace_id in the audit record. This keeps the audit trail lean while preserving full provenance.

5. **Integration with existing `ai_copilot.py` vs. new module**
   - What we know: `bioorchestrator_real/utils/ai_copilot.py` has 10 tools and a 3-round loop. The new reasoning engine needs 14+ tools and 10-round limit with 5 modes.
   - What's unclear: Whether to extend the copilot or build a separate module.
   - Recommendation: Build a new `src/reasoning/` module. The copilot is for interactive Q&A (Streamlit chat). The reasoning engine is for structured analytical modes (batch processing). Different concerns, different prompts, different output formats. The copilot can be updated later (Phase 7 UI) to use the reasoning engine's tools.

## Sources

### Primary (HIGH confidence)
- **Existing codebase** (`bioorchestrator_real/utils/llm_provider.py`, `ai_copilot.py`, `data_queries.py`) -- verified by reading source code. Foundation for tool-calling architecture.
- **Existing codebase** (`src/evidence/aggregator.py`, `models.py`, `interface.py`) -- verified by reading source code. Evidence integration layer the reasoning engine queries through.
- **Existing codebase** (`src/compliance/audit_trail.py`) -- verified by reading source code. Hash-chain audit trail for provenance recording.
- **Ollama tool calling docs** (https://docs.ollama.com/capabilities/tool-calling) -- Official documentation for tool definition format, multi-turn protocol, and agentic loops.

### Secondary (MEDIUM confidence)
- **Ollama Python SDK 0.4 blog** (https://ollama.com/blog/functions-as-tools) -- Official blog post on function-as-tool support. Response format: `response.message.tool_calls` with function name and arguments dict.
- **Ollama Python SDK GitHub** (https://github.com/ollama/ollama-python) -- Official repository. Confirms v0.6+ support for web search and tool calling improvements.
- **Groq tool use docs** (https://console.groq.com/docs/tool-use/overview) -- Official documentation. llama-3.3-70b-versatile supports parallel tool calls. 131K context, 32K output. OpenAI-compatible API.
- **Groq model specs** (https://console.groq.com/docs/model/llama-3.3-70b-versatile) -- Context window 131,072, max output 32,768, ~280 tok/sec.
- **Qwen3:8b Ollama GitHub issue #14601** (https://github.com/ollama/ollama/issues/14601) -- Known Qwen3 tool-calling bugs: malformed JSON serialization, think/no_think interference. Fix merged via PR #14695.
- **Tool calling benchmark** (https://mikeveerman.be/blog/github-2026-02-06-tool-calling-benchmark/) -- 21-model benchmark. Qwen3:0.6b and 4b scored 0.880 (tied #1). Non-monotonic performance across Qwen3 sizes. 8B not benchmarked.
- **Caktus Group Ollama tool calling tutorial** (https://www.caktusgroup.com/blog/2025/12/03/learning-llm-basics-ollama-function-calling/) -- Confirmed tool result format: `{"role": "tool", "content": result, "tool_name": name}`. Complete agentic loop example.
- **STACK.md** (project planning doc) -- Verified library versions, alternatives-rejected decisions, 8GB RAM constraint.

### Tertiary (LOW confidence)
- **tiktoken token counting** -- Recommended based on training data knowledge. cl100k_base encoding is accurate for OpenAI models, approximate for Qwen3/Llama (different tokenizers). For the 8K threshold check, ~90% accuracy is sufficient.
- **Prompt versioning with SHA256** -- Pattern synthesized from multiple web search results about LLM audit trails and compliance. No single authoritative source. The approach (hash prompt text, store hash in audit record) is straightforward and well-established.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All libraries already in use or already in STACK.md. Versions verified.
- Architecture: MEDIUM-HIGH -- Tool-calling loop pattern proven in existing `ai_copilot.py`. Five-mode orchestrator is a natural extension. Provenance tracking uses existing audit trail.
- Pitfalls: MEDIUM -- Qwen3:8b tool-calling reliability is the primary unknown (flagged as R-005 prior decision). Other pitfalls (context overflow, hallucination) are well-understood in the industry. Token format mismatch is already handled by existing provider abstraction.

**Research date:** 2026-05-11
**Valid until:** 2026-06-11 (30 days -- Ollama SDK and model ecosystem move fast; re-check Qwen3 tool-calling status if implementation is delayed)
