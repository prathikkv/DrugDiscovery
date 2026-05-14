# Failure Mode and Effects Analysis (FMEA)
**Document ID:** FMEA-001
**Version:** 1.0
**Status:** Approved
**Date:** 2026-05-13
**Related FRS:** FRS-001

---

## Risk Assessment Table

RPN = Severity (S, 1-10) × Occurrence (O, 1-10) × Detection (D, 1-10)
Risk Priority: HIGH (RPN ≥ 100), MEDIUM (RPN 50-99), LOW (RPN < 50)

| ID | Function | Failure Mode | Effect | S | O | D | RPN | Risk | Recommended Action |
|----|----------|-------------|--------|:---:|:---:|:---:|:---:|------|-------------------|
| FM-001 | Audit trail append | Hash chain broken by direct DB edit | Undetected tampering; regulatory non-compliance | 10 | 2 | 2 | 40 | LOW | AuditTrail.verify_chain() runs in CI; DB is SQLite file with no exposed write API |
| FM-002 | Scoring framework | Wrong composite score returned | Incorrect GO/CONDITIONAL/NO-GO recommendation sent to client | 9 | 2 | 2 | 36 | LOW | Validation suite (`pytest -m validation`) asserts all 6 showcase targets within expected ranges |
| FM-003 | Evidence cache | Stale cache returned without flag | Analyst uses outdated evidence; decision based on old data | 7 | 3 | 4 | 84 | MEDIUM | Cache entries include fetched_at timestamp displayed in UI; TTL set to 24h; is_fallback flag shown |
| FM-004 | External API failure | OpenTargets/DGIdb/PubMed unavailable | Incomplete evidence profile; dimension coverage drops | 6 | 4 | 2 | 48 | LOW | Retry with 3x exponential backoff; stale cache fallback (REQ-210); confidence=0.0 flag shown |
| FM-005 | Auth lockout bypass | Lockout counter reset by race condition | Brute force attack succeeds | 8 | 2 | 3 | 48 | LOW | threading.Lock in AuthService serializes counter reads; tests cover concurrent lockout |
| FM-006 | Pipeline checkpoint | Checkpoint write fails mid-stage | Data loss; pipeline must restart from beginning | 7 | 3 | 3 | 63 | MEDIUM | Stage-level try/except with checkpoint.save() before advancing; resume logic checks stage list |
| FM-007 | Scoring dimension | Low data coverage not flagged | Neutral 0.5 score masks NO-GO signal | 8 | 3 | 2 | 48 | LOW | data_coverage < 0.3 triggers neutral substitution (logged); MELK fixture has all coverage >= 0.3 |
| FM-008 | Docker container | Container starts but app crashes on import | System appears deployed but non-functional | 7 | 3 | 2 | 42 | LOW | HEALTHCHECK polls /_stcore/health; `docker compose up --wait` fails if health check fails |
| FM-009 | Pre-commit hook | Hook fails on clean checkout (no DB) | Blocks all commits in fresh environment | 6 | 4 | 3 | 72 | MEDIUM | Audit trail hook checks staged file content only (grep patterns), never opens DB |
| FM-010 | GxP traceability | Test paths in traceability.yaml point to non-existent tests | Traceability audit fails; compliance gap | 8 | 3 | 2 | 48 | LOW | test_critical_path.py::test_traceability_yaml_has_req801 verifies format at runtime |

---

## Summary

| Risk Level | Count | Items | Action |
|-----------|-------|-------|--------|
| HIGH (RPN ≥ 100) | 0 | — | None — no high-risk items identified |
| MEDIUM (RPN 50-99) | 3 | FM-003, FM-006, FM-009 | Mitigations documented above |
| LOW (RPN < 50) | 7 | FM-001, 002, 004, 005, 007, 008, 010 | Monitored by automated test suite |

**Highest RPN:** FM-003 (Evidence cache stale return, RPN=84). Mitigated by UI timestamp display and is_fallback flag.

---

## Review Notes

- No failure mode exceeds RPN=100, indicating the system's automated test suite and architectural safeguards provide adequate risk mitigation.
- FM-009 (pre-commit hook failures on clean checkout) is the primary operability risk — mitigated by hook design that avoids DB access.
- This FMEA should be updated whenever a new failure mode is discovered in production (per SOP-004 Section 3.5).
