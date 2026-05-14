# Validation Master Plan (VMP)
**Document ID:** VMP-001
**Version:** 1.0
**Status:** Approved
**Date:** 2026-05-13
**System:** BioOrchestrator v2 — Drug Target Intelligence Platform

---

## 1. Purpose and Scope

This Validation Master Plan (VMP) defines the validation strategy, approach, and deliverables for the BioOrchestrator v2 platform. The platform is a consulting-grade drug target intelligence system that scores gene targets for pharma clients, providing GO/CONDITIONAL/NO-GO recommendations backed by multi-source evidence and a 21 CFR Part 11 compliant audit trail.

**In scope:**
- Target scoring framework (7 dimensions, 24 sub-scores, REQ-401 through REQ-406)
- Evidence integration layer (6 external sources, REQ-201 through REQ-211)
- Authentication and access control (REQ-501 through REQ-508)
- Audit trail integrity (REQ-502, REQ-503)
- Pharma showcase validation (REQ-801, REQ-802)
- Deployment and compliance (REQ-803 through REQ-806)

**Out of scope:** AI reasoning model accuracy (REQ-301 through REQ-308) is validated separately via qualitative review.

---

## 2. Validation Approach

This platform is classified as **GAMP 5 Category 4** (configured software). The validation approach follows a V-model:

| Level | Document | Test Tier |
|-------|----------|-----------|
| User requirements | URS-001 | Validation suite (`pytest -m validation`) |
| Functional requirements | FRS-001 | Integration tests (`pytest -m integration`) |
| Design specifications | Codebase + SUMMARYs | Unit tests (`pytest -m unit`) |

---

## 3. Acceptance Criteria

All five success criteria must be met before the system is considered validated:

1. **SC#1 (REQ-801, REQ-802):** Pharma showcase suite passes — all 6 targets within expected ranges, MELK NO-GO below 50.
2. **SC#2 (REQ-803):** Three-tier testing operational — unit < 30s, integration < 5min, validation suite covers REQ-8xx.
3. **SC#3 (REQ-804):** This VMP plus URS-001, FRS-001, FMEA-001, traceability.yaml, and SOP-001 through SOP-005 are complete.
4. **SC#4 (REQ-806):** Pre-commit hooks active on every commit.
5. **SC#5 (REQ-803):** Application runs via `docker compose up` with all tests passing in container.

---

## 4. Roles and Responsibilities

| Role | Responsibility |
|------|----------------|
| System Developer | Implementation, test authoring, documentation |
| Project Owner | Requirement sign-off, acceptance criteria approval |
| Reviewer | UAT execution, SOP review |

---

## 5. Deliverables

| Document | File | Status |
|----------|------|--------|
| Validation Master Plan | docs/gxp/VMP.md | Complete |
| User Requirements Specification | docs/gxp/URS.md | Complete |
| Functional Requirements Specification | docs/gxp/FRS.md | Complete |
| Failure Mode and Effects Analysis | docs/gxp/FMEA.md | Complete |
| Requirements Traceability Matrix | docs/gxp/traceability.yaml | Complete |
| SOP-001: System Operation | docs/gxp/sops/SOP-001-system-operation.md | Complete |
| SOP-002: Data Backup and Recovery | docs/gxp/sops/SOP-002-data-backup.md | Complete |
| SOP-003: Change Control | docs/gxp/sops/SOP-003-change-control.md | Complete |
| SOP-004: Incident Response | docs/gxp/sops/SOP-004-incident-response.md | Complete |
| SOP-005: User Management | docs/gxp/sops/SOP-005-user-management.md | Complete |

---

## 6. Validation Schedule

| Activity | Milestone |
|----------|-----------|
| Phase 8 planning complete | 2026-05-13 |
| Validation suite implementation | Phase 8 Plan 01 |
| GxP documentation | Phase 8 Plan 02 (this document) |
| Deployment validation | Phase 8 Plan 03 |
| System go-live | Post Phase 8 completion |
