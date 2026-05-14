# SOP-003: Change Control
**Document ID:** SOP-003
**Version:** 1.0
**Date:** 2026-05-13
**Owner:** Project Owner

---

## 1. Purpose
Define the process for proposing, reviewing, approving, and deploying changes to BioOrchestrator v2.

## 2. Change Categories

| Category | Examples | Required Approvals |
|----------|----------|-------------------|
| Emergency fix | Security vulnerability, data corruption | Project Owner |
| Standard change | Bug fix, feature addition | Project Owner + Reviewer |
| Major change | Scoring weights, architecture, evidence sources | Project Owner + Reviewer + FMEA update |

## 3. Change Request Process

### 3.1 Propose Change
1. Document the change: what, why, affected components, risk assessment
2. Check FMEA-001 for any affected failure modes — update if needed
3. Create a git branch: `git checkout -b change/description-of-change`

### 3.2 Implement Change
1. All changes must pass pre-commit hooks: `pre-commit run --all-files`
2. Run full test suite: `pytest` (must pass, no new failures)
3. If scoring weights changed: re-run validation suite and confirm SC#1 ranges still pass
4. Update traceability.yaml if new requirements are introduced

### 3.3 Review and Approve
1. Reviewer executes test suite independently: `pytest -m validation -v`
2. Reviewer confirms FMEA impact assessed
3. Approval recorded in audit trail via admin action

### 3.4 Deploy
1. Merge to main branch
2. Tag release: `git tag v{major}.{minor}.{patch}`
3. Rebuild Docker image: `docker compose build`
4. Run smoke test: `docker compose run --rm test pytest -m validation`

## 4. Config Change Special Handling
Changes to `src/config.py`, `src/scoring/weights.py`, or `.streamlit/config.toml` trigger the `config-change-flag` pre-commit hook. The hook prints a warning — the developer must explicitly acknowledge the change before committing.
