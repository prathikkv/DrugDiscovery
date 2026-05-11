---
phase: 04-ai-reasoning-engine
plan: 02
subsystem: reasoning
tags: [fallback-chain, tool-executor, tool-loop, provenance, sha256, audit-trail]

# Dependency graph
requires:
  - phase: 04-ai-reasoning-engine
    plan: 01
    provides: "ToolTrace, ToolCallRecord, ProvenanceRecord models, TokenManager, TOOL_DEFINITIONS"
  - phase: 03-evidence-integration
    provides: "EvidenceAggregator, EvidenceResult, GeneResolver, all 6 evidence sources"
  - phase: 01-foundation
    provides: "AuditTrail.append_record() for fallback event and provenance logging"
provides:
  - "FallbackChain: LLM provider failover (Ollama -> Groq -> Anthropic) with audit logging"
  - "ToolExecutor: Dispatch table for all 14 tool names to handler methods"
  - "run_tool_loop: Agentic tool-calling loop with 10-round limit and ToolTrace output"
  - "ProvenanceTracker: SHA256 evidence hashing, provenance records, trace file persistence"
affects: [04-03, 05-scoring-framework]

# Tech tracking
tech-stack:
  added: [hashlib-sha256, uuid4]
  patterns: [fallback-chain, tool-dispatch, agentic-loop, provenance-tracking]

key-files:
  created:
    - src/reasoning/fallback.py
    - src/reasoning/tool_executor.py
    - src/reasoning/tool_loop.py
    - src/reasoning/provenance.py
  modified:
    - src/reasoning/__init__.py

key-decisions:
  - "FallbackChain builds providers lazily at init by checking availability (Ollama.is_available, env vars)"
  - "ToolExecutor uses lazy import for evidence sources to avoid circular dependency at module load"
  - "Tool results serialized with json.dumps(default=str) for robustness with datetime/Path objects"
  - "Provenance traces saved to disk files, not in audit trail details_json (keeps audit records lean)"
  - "GeneResolver created lazily in ToolExecutor to avoid import overhead when unused"

patterns-established:
  - "Fallback chain pattern: try providers in order, log each failure to audit, collect errors"
  - "Dispatch table pattern: dict mapping tool_name -> handler method for extensible routing"
  - "Lazy loading pattern: AnnData and pipeline_report cached on self after first access"
  - "Evidence tool compact summary: return top N results, not full payloads"
  - "Trace persistence: full ToolTrace saved as JSON file, referenced by trace_id UUID"

# Metrics
duration: 6min
completed: 2026-05-11
---

# Phase 4 Plan 2: Reasoning Runtime Summary

**FallbackChain for LLM resilience, ToolExecutor dispatching 14 tools, agentic tool-calling loop with 10-round ToolTrace, and ProvenanceTracker with SHA256 evidence hashing**

## Performance

- **Duration:** 6 min
- **Started:** 2026-05-11T09:24:52Z
- **Completed:** 2026-05-11T09:31:19Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- FallbackChain wraps Ollama/Groq/Anthropic with ordered failover and audit trail logging of every provider switch
- ToolExecutor routes all 14 tool names (4 omics, 6 evidence, 4 analysis) to handler methods with graceful error dicts
- run_tool_loop implements the agentic loop: LLM call -> extract tool calls -> execute -> feed results back -> repeat up to 10 rounds
- ProvenanceTracker computes SHA256 hashes of evidence data, builds ProvenanceRecords with full session metadata, and saves traces to disk

## Task Commits

Each task was committed atomically:

1. **Task 1: Create fallback chain and tool executor** - `b98bed1` (feat)
2. **Task 2: Create agentic tool-calling loop and provenance tracker** - `d9095e2` (feat)

## Files Created/Modified
- `src/reasoning/fallback.py` - FallbackChain class with ordered provider selection and audit logging
- `src/reasoning/tool_executor.py` - ToolExecutor with dispatch table for 14 tools, lazy AnnData/report loading
- `src/reasoning/tool_loop.py` - run_tool_loop function with round counting, ToolCallRecord tracing, context checks
- `src/reasoning/provenance.py` - ProvenanceTracker with SHA256 hashing, audit recording, trace file persistence
- `src/reasoning/__init__.py` - Updated exports: now 14 symbols total including all new components

## Decisions Made
- FallbackChain builds provider list at init time by probing availability (Ollama server check, env var presence) -- no providers is a warning, not an error, to allow construction before configuration
- ToolExecutor uses lazy imports for evidence sources (import inside handler methods) to avoid circular dependency at module load time and reduce startup overhead
- Tool results serialized with `json.dumps(default=str)` throughout to handle datetime, Path, and other non-JSON-native types robustly
- Full reasoning traces saved to `data/reasoning_traces/{trace_id}.json` files rather than embedding in audit trail `details_json` -- keeps audit records compact per research recommendation
- GeneResolver created lazily on first evidence tool call via `_get_gene_resolver()` to avoid unnecessary MyGene.info initialization

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All reasoning runtime infrastructure ready for 04-03 (reasoning engine orchestrator)
- FallbackChain, ToolExecutor, run_tool_loop, ProvenanceTracker all importable from src.reasoning
- ToolExecutor dispatches all 14 tools; evidence handlers use individual sources directly (not aggregator)
- No blockers for next plan

## Self-Check: PASSED

- All 5 files verified on disk (4 created + 1 modified)
- Both task commits (b98bed1, d9095e2) verified in git log

---
*Phase: 04-ai-reasoning-engine*
*Plan: 02*
*Completed: 2026-05-11*
