# Functional Requirements Specification (FRS)
**Document ID:** FRS-001
**Version:** 1.0
**Status:** Approved
**Date:** 2026-05-13
**Related URS:** URS-001

---

## 1. Purpose

This FRS describes the technical implementation of each user requirement in URS-001.

---

## 2. Functional Specifications

### FR-401: Composite Scoring
**Implements:** UR-401 (REQ-401)
**Input:** AggregatedEvidence (6 EvidenceResult objects)
**Processing:** ScoringFramework.score_target() calls 7 DimensionCalculators, each producing a DimensionScore. Composite = sum(dim_score) for standard weights (6 x 15.0 + 1 x 10.0 = 100.0 total).
**Output:** ScorecardResult with composite.score (0-100), 7 DimensionScores, 24 SubScores
**Module:** src/scoring/framework.py
**Error handling:** Dimensions with data_coverage < 0.3 receive neutral 0.5 sub-score to avoid conflating missing data with negative evidence.

### FR-402: Verdict Thresholds
**Implements:** UR-402 (REQ-402)
**Logic:** VerdictEngine applies thresholds: GO >= 75.0, CONDITIONAL 50.0-74.9, NO-GO < 50.0. Dimension minimums (safety_selectivity < 20% of max forces CONDITIONAL regardless of composite).
**Module:** src/scoring/verdict.py

### FR-403: HITL Weight Adjustment
**Implements:** UR-403
**Implementation:** WeightConfig Pydantic model (src/scoring/models.py) allows per-dimension weight overrides. score_target(weights=custom) recomputes all dimensions with new weights. UI exposes sliders in scorecard page HITL gate.
**Module:** src/pages/scorecard.py, src/scoring/models.py

### FR-201: Evidence Aggregation
**Implements:** UR-201 (REQ-201)
**Implementation:** EvidenceAggregator.gather_all() parallelises across 6 sources with asyncio.gather(). Each source has a dedicated EvidenceSource subclass.
**Module:** src/evidence/aggregator.py, src/evidence/sources/

### FR-202: Evidence Cache
**Implements:** UR-202 (REQ-202)
**Implementation:** SQLite-backed EvidenceCache stores results keyed by (gene_symbol, source_name). TTL = 86400s (24h). Cache hit returns without calling external APIs.
**Module:** src/evidence/cache.py

### FR-501: Authentication
**Implements:** UR-501 (REQ-501)
**Implementation:** AuthService.register(email, password, role) stores bcrypt hash. AuthService.login(email, password) verifies hash and returns JWT token.
**Module:** src/auth/service.py

### FR-502: Account Lockout
**Implements:** UR-502 (REQ-502)
**Implementation:** AuthService tracks failed_attempts in auth DB. After 5 failures, locked_until = now + 15min. threading.Lock serializes counter to prevent race conditions.
**Module:** src/auth/service.py

### FR-503: Audit Trail Integrity
**Implements:** UR-503 (REQ-503)
**Implementation:** AuditTrail (src/compliance/audit_trail.py) writes append-only records to SQLite. Each record stores SHA-256 hash of (previous_hash || timestamp || user_id || action || resource_type || resource_id || details). First record uses genesis hash (64 zeros). AuditTrail.verify_chain() detects any tampering by recomputing hashes.
**Thread safety:** threading.Lock serializes the read-previous-hash + write sequence.

### FR-801: EGFR Ranking (REQ-801)
**Implements:** UR-801
**Validation:** tests/test_validation/test_pharma_showcase.py::test_egfr_scores_highest_among_showcase loads pre-cached scoring.json files for all 6 showcase targets and asserts EGFR has the highest composite score.

### FR-802: MELK Negative Control (REQ-802)
**Implements:** UR-802
**Validation:** tests/test_validation/test_negative_control.py::test_melk_no_go loads data/showcase_scenarios/melk/scoring.json and asserts verdict.level == "NO-GO" and composite.score in [35, 45].
**MELK scientific basis:** CRISPR knockout study (eLife 2017, Huang et al.) showed no proliferation effect in 13 cancer cell lines. OTSSP167 inhibitor effects attributed to off-target kinase activity.

### FR-806: Pre-Commit Hooks (REQ-806)
**Implements:** UR-806
**Implementation:** .pre-commit-config.yaml with repo:local hooks. Three hooks: (1) audit-trail-integrity checks staged Python files for direct SQL DELETE/UPDATE on audit_records table, (2) no-hardcoded-params uses pygrep regex for credentials and magic numbers, (3) config-change-flag warns (exit 0) when config files are staged.

---

## 3. Interface Specifications

| Interface | Type | Protocol | Location |
|-----------|------|----------|----------|
| Streamlit UI | HTTP | Browser to Streamlit server | src/app.py, src/pages/ |
| Evidence APIs | HTTPS | REST/GraphQL | src/evidence/sources/ |
| Audit database | SQLite | File I/O | data/db/audit.db |
| Auth database | SQLite | File I/O | data/db/auth.db |

---

## 4. Non-Functional Specifications

| Requirement | Specification | Verification |
|-------------|---------------|--------------|
| Unit test performance | < 30 seconds total | `time pytest -m unit` |
| Integration test performance | < 5 minutes total | CI pipeline timing |
| Evidence fetch latency | < 60 seconds | EvidenceAggregator timeout config |
| Audit chain integrity | 100% tamper detectable | AuditTrail.verify_chain() |
| Container startup | < 60 seconds to healthy | Docker HEALTHCHECK |
