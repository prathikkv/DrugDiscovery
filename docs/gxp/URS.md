# User Requirements Specification (URS)
**Document ID:** URS-001
**Version:** 1.0
**Status:** Approved
**Date:** 2026-05-13
**Related VMP:** VMP-001

---

## 1. Intended Use

BioOrchestrator v2 is used by pharmaceutical scientists and consultants to evaluate drug target genes for therapeutic development. Users upload single-cell RNA-seq data and specify target genes; the system returns a structured GO/CONDITIONAL/NO-GO recommendation with supporting evidence, scoring breakdown, and a full audit trail.

---

## 2. User Types

| User Type | Access Level | Primary Activities |
|-----------|-------------|-------------------|
| Analyst | Read + Write | Run analyses, view reports |
| Admin | Full | User management, config changes |
| Reviewer | Read-only | Review results, approve gates |

---

## 3. Operational Requirements

### 3.1 Target Scoring (Phase 5)
- **UR-401:** The system shall score each target on a 0-100 composite scale using 7 evidence dimensions.
- **UR-402:** The system shall render GO (>=75), CONDITIONAL (50-74), or NO-GO (<50) verdicts automatically.
- **UR-403:** Users shall be able to adjust dimension weights via a HITL gate and see the updated score immediately.

### 3.2 Evidence Integration (Phase 3)
- **UR-201:** The system shall query 6 external evidence sources for any gene symbol.
- **UR-202:** Results for a gene queried within 24 hours shall be returned from cache without external API calls.
- **UR-203:** Ambiguous gene names (e.g., PD-L1, HER2) shall resolve to canonical identifiers before querying.

### 3.3 Authentication and Access (Phase 1)
- **UR-501:** Users shall authenticate with email and password.
- **UR-502:** Accounts shall lock after 5 failed login attempts.
- **UR-503:** Every state-changing action shall produce an immutable, tamper-detectable audit record.

### 3.4 Pharma Validation (Phase 8)
- **UR-801:** The system shall correctly rank EGFR as the top target among available NSCLC showcase targets.
- **UR-802:** The system shall assign NO-GO to MELK, a known discredited target (CRISPR evidence contradicts prior claims).
- **UR-803:** The system shall maintain a three-tier test suite: unit (<30s), integration (<5min), validation.
- **UR-804:** GxP documentation (VMP, URS, FRS, FMEA, traceability, 5 SOPs) shall be maintained in docs/gxp/.
- **UR-806:** Pre-commit hooks shall enforce audit trail integrity, no hardcoded parameters, and config change flagging.

---

## 4. Data Requirements

- Input: Gene symbol (string), disease context (optional string), scRNA-seq data (.h5ad, .h5, 10x folder)
- Output: ScorecardResult JSON, HTML/PDF dossier, audit trail records
- Retention: Audit records are append-only and never deleted
- Integrity: Evidence hash stored with each score for reproducibility verification

---

## 5. Performance Requirements

- Evidence fetch: < 60 seconds for all 6 sources
- Cache hit: < 2 seconds
- Unit test suite: < 30 seconds total
- Integration test suite: < 5 minutes total
