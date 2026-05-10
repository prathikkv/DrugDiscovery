---
phase: 03-evidence-integration
plan: 02
subsystem: evidence
tags: [graphql, opentargets, dgidb, pubmed, entrez, tenacity, retry, biopython]

# Dependency graph
requires:
  - phase: 03-evidence-integration
    provides: "EvidenceSource Protocol, EvidenceResult/GeneIdentifiers models, EvidenceCache"
provides:
  - "OpenTargetsSource: target info, tractability, known drugs, disease associations via GraphQL"
  - "DGIdbSource: drug-gene interactions, druggability categories via GraphQL"
  - "PubMedSource: recent papers with abstracts via Entrez, AI summary via LLM"
affects: [03-03, 03-04, 05-scoring]

# Tech tracking
tech-stack:
  added: []
  patterns: [graphql-source-with-retry, entrez-batch-fetch, lazy-llm-import, graceful-fetch-degradation]

key-files:
  created:
    - src/evidence/sources/opentargets.py
    - src/evidence/sources/dgidb.py
    - src/evidence/sources/pubmed.py
  modified: []

key-decisions:
  - "OpenTargets fetches top 25 associations (not all) for performance; disease_context flags relevance in-place"
  - "DGIdb confidence levels: 1.0 with interactions, 0.5 if gene found but no interactions, 0.0 on error"
  - "PubMed AI summary uses lazy import of src.execution.llm (Phase 4); returns None gracefully if unavailable"
  - "LLM_SUMMARY_MODEL env var controls summary model (default gpt-4o-mini) for cost/speed flexibility"

patterns-established:
  - "GraphQL source pattern: BASE_URL + QUERY constants, _query() with retry decorator, fetch() with top-level try/except"
  - "Confidence scoring pattern: 1.0=success, 0.5=partial, 0.3=valid-empty, 0.0=error"
  - "Lazy dependency pattern: import inside method body, catch ImportError, return None"
  - "Entrez batch fetch: esearch for PMIDs then efetch for full records in one call"

# Metrics
duration: 4min
completed: 2026-05-10
---

# Phase 3 Plan 2: Evidence Sources (OpenTargets, DGIdb, PubMed) Summary

**Three evidence sources implementing EvidenceSource Protocol: OpenTargets GraphQL for target/tractability/drugs/associations, DGIdb GraphQL for drug-gene interactions and druggability, PubMed Entrez for recent literature with AI summary**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-10T16:01:04Z
- **Completed:** 2026-05-10T16:04:55Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- OpenTargets source fetching target info (symbol, name, biotype), tractability scores, known drugs with mechanisms, and top 25 disease associations via Platform API v4 GraphQL
- DGIdb source fetching drug-gene interactions with druggability categories, interaction types/scores, and supporting publications via v5 GraphQL
- PubMed source searching recent literature (last 5 years), batch-fetching abstracts via Entrez, and generating AI summary of findings (non-fatal if LLM unavailable)
- All three sources use tenacity retry (3 attempts, exponential backoff) on transient HTTP errors and catch all exceptions in fetch() returning EvidenceResult(confidence=0.0)

## Task Commits

Each task was committed atomically:

1. **Task 1: OpenTargets GraphQL evidence source** - `4960060` (feat)
2. **Task 2: DGIdb GraphQL evidence source** - `788cb88` (feat)
3. **Task 3: PubMed/Entrez evidence source** - `d336c54` (feat)

## Files Created/Modified
- `src/evidence/sources/opentargets.py` - OpenTargets Platform API v4 GraphQL source with target info and disease associations
- `src/evidence/sources/dgidb.py` - DGIdb v5 GraphQL source with drug-gene interactions and druggability categories
- `src/evidence/sources/pubmed.py` - PubMed/Entrez source with batch abstract fetch and AI summary generation

## Decisions Made
- OpenTargets fetches top 25 disease associations by score (not all) for performance; disease_context is used to flag relevance rather than filter
- DGIdb uses tiered confidence: 1.0 when interactions found, 0.5 when gene exists but has no interactions (valid result), 0.0 only on actual errors
- PubMed AI summary uses lazy import of `src.execution.llm` module (Phase 4); gracefully returns None if module not yet available
- LLM_SUMMARY_MODEL env var allows configuring the summary model (defaults to gpt-4o-mini for cost/speed balance)
- Entrez module-level email/api_key setup is thread-safe per Bio.Entrez documentation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. NCBI_API_KEY is optional (raises rate limit from 3 to 10 req/s if set).

## Next Phase Readiness
- Three primary evidence sources operational and Protocol-compliant
- Plan 03-03 can implement ChEMBL, ClinicalTrials, and HPA sources using the same patterns
- Plan 03-04 can build the aggregator consuming all source implementations
- AI summary will activate automatically when Phase 4 implements `src.execution.llm`
- All 41 existing tests continue to pass (no regressions)

## Self-Check: PASSED

All 3 created files verified on disk. All 3 task commits (4960060, 788cb88, d336c54) verified in git log.

---
*Phase: 03-evidence-integration*
*Completed: 2026-05-10*
