# SOP-004: Incident Response
**Document ID:** SOP-004
**Version:** 1.0
**Date:** 2026-05-13
**Owner:** System Administrator

---

## 1. Purpose
Define procedures for detecting, responding to, and recovering from incidents affecting BioOrchestrator v2.

## 2. Incident Classification

| Severity | Definition | Response Time |
|----------|-----------|---------------|
| P0 - Critical | Audit trail broken, data loss, auth bypass | Immediate |
| P1 - High | Application down, scoring returns wrong verdicts | 1 hour |
| P2 - Medium | Slow performance, non-critical feature failure | 4 hours |
| P3 - Low | UI cosmetic issues, non-blocking bugs | Next sprint |

## 3. Incident Response Steps

### 3.1 Detection
- Automated: HEALTHCHECK failure triggers container restart and notification
- Manual: User reports unexpected behavior

### 3.2 Triage
1. Run audit trail integrity check:
   ```bash
   python -c "
   from src.compliance.audit_trail import AuditTrail
   t = AuditTrail()
   r = t.verify_chain()
   print('Audit trail:', 'VALID' if r['valid'] else f'BROKEN at record {r.get(\"first_bad_id\")}')
   "
   ```
2. Run validation suite: `pytest -m validation --tb=short`
3. Check application logs: `docker compose logs app --tail=100`

### 3.3 P0 Response: Audit Trail Broken
1. Stop the application immediately: `docker compose down`
2. Do NOT modify the database — preserve evidence for investigation
3. Restore from last known-good backup (SOP-002 Section 4)
4. Document the incident in a new audit record after restoration
5. Notify Project Owner within 1 hour

### 3.4 P1 Response: Wrong Scoring Verdicts
1. Preserve current state: `cp data/db/audit.db /tmp/incident_$(date +%Y%m%d_%H%M%S).db`
2. Run: `pytest -m validation -v --tb=long` — capture full output
3. Identify which showcase target is out of range
4. Check if scoring weights were recently changed (SOP-003)
5. Roll back if necessary via git: `git revert HEAD`

### 3.5 Post-Incident
1. Write incident report documenting: detection time, root cause, resolution, prevention
2. Update FMEA-001 if a new failure mode was discovered
3. Add regression test if the incident represents a new test gap
