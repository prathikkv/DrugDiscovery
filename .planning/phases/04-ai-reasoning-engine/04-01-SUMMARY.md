---
phase: 04-ai-reasoning-engine
plan: 01
subsystem: reasoning
tags: [pydantic, llm-tools, prompts, token-counting, tiktoken, sha256]

# Dependency graph
requires:
  - phase: 03-evidence-integration
    provides: "EvidenceResult, GeneIdentifiers models consumed by reasoning tools"
  - phase: 01-foundation
    provides: "AuditTrail.append_record() interface used by ProvenanceRecord.to_audit_details()"
provides:
  - "ReasoningMode enum (5 modes) for all reasoning operations"
  - "ReasoningResult, Claim, ToolTrace, ToolCallRecord, ProvenanceRecord Pydantic models"
  - "14 LLM tool definitions in Anthropic input_schema format"
  - "CITATION_TO_TOOL mapping for hallucination checker"
  - "PromptRegistry with SHA256-versioned prompts per mode"
  - "TokenManager for context window management"
affects: [04-02, 04-03, 05-scoring-framework]

# Tech tracking
tech-stack:
  added: [pydantic-v2, hashlib-sha256]
  patterns: [versioned-prompts, tool-definitions-anthropic-format, token-fallback]

key-files:
  created:
    - src/reasoning/__init__.py
    - src/reasoning/models.py
    - src/reasoning/tools.py
    - src/reasoning/prompts.py
    - src/reasoning/token_manager.py
  modified: []

key-decisions:
  - "Pydantic v2 BaseModel for all reasoning models (not dataclasses) for validation and serialization"
  - "SHA256 prompt versioning computed at PromptRegistry init time for zero-cost per-request hashing"
  - "tiktoken fallback to len//4 approximation with logged warning (tiktoken not currently installed)"
  - "ProvenanceRecord.to_audit_details() excludes reasoning chain per research recommendation"
  - "ToolTrace.tools_used() preserves insertion order while deduplicating via set"

patterns-established:
  - "Anthropic-native tool format: all tools defined as {name, description, input_schema}"
  - "Versioned prompt pattern: PromptRegistry.get() returns (text, sha256) tuple"
  - "Token budget pattern: TokenManager.fits_context() estimates before sending to LLM"
  - "[Source: ToolName] citation format required in all reasoning mode prompts"

# Metrics
duration: 5min
completed: 2026-05-11
---

# Phase 4 Plan 1: Reasoning Foundation Summary

**6 Pydantic models, 14 LLM tool definitions in Anthropic format, SHA256-versioned prompt registry for 5 reasoning modes, and token manager with tiktoken fallback**

## Performance

- **Duration:** 5 min
- **Started:** 2026-05-11T09:15:21Z
- **Completed:** 2026-05-11T09:20:46Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Complete type system for reasoning engine: ReasoningMode enum, ReasoningResult, Claim, ToolTrace, ToolCallRecord, ProvenanceRecord
- 14 disease-agnostic LLM tool definitions covering omics (4), evidence sources (6), and analysis (4)
- Versioned prompt registry with unique SHA256 hashes per mode, supporting custom prompt registration
- Token manager with graceful tiktoken fallback, context fitting estimation, and tool result truncation

## Task Commits

Each task was committed atomically:

1. **Task 1: Create reasoning data models and module structure** - `0708f48` (feat)
2. **Task 2: Create tool definitions, versioned prompt registry, and token manager** - `15dbc32` (feat)

## Files Created/Modified
- `src/reasoning/__init__.py` - Public API exports for reasoning module (10 symbols)
- `src/reasoning/models.py` - 6 Pydantic v2 models: ReasoningMode, ToolCallRecord, ToolTrace, Claim, ReasoningResult, ProvenanceRecord
- `src/reasoning/tools.py` - 14 LLM tool definitions in Anthropic format + CITATION_TO_TOOL mapping
- `src/reasoning/prompts.py` - PromptRegistry with SHA256 versioning, 5 mode-specific system prompts (200-400 words each)
- `src/reasoning/token_manager.py` - TokenManager with tiktoken/fallback counting, context fitting, truncation

## Decisions Made
- Pydantic v2 BaseModel (not dataclasses) for all reasoning models -- consistent with project's use of Pydantic and provides validation
- SHA256 prompt versioning computed at PromptRegistry init time -- no per-request hash overhead
- tiktoken fallback to `len(text) // 4` with logged warning -- graceful degradation when tiktoken not installed
- ProvenanceRecord.to_audit_details() excludes full reasoning chain -- stored separately per research recommendation to keep audit records compact
- ToolTrace.tools_used() preserves insertion order while deduplicating -- important for understanding tool call sequence

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All reasoning foundation types ready for 04-02 (reasoning engine with tool-calling loop)
- PromptRegistry and TokenManager ready for integration with LLM providers
- CITATION_TO_TOOL mapping ready for hallucination checker in 04-03
- No blockers for next plan

## Self-Check: PASSED

- All 5 created files verified on disk
- Both task commits (0708f48, 15dbc32) verified in git log

---
*Phase: 04-ai-reasoning-engine*
*Plan: 01*
*Completed: 2026-05-11*
