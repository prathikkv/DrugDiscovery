# Production Readiness Checklist

Run through every item before launching to your first paying customer.

---

## Security

- [ ] Register as a new user → confirm only `user_id`, `email`, and `role` are stored in session (never plaintext password)
- [ ] Log in as `reviewer` role, navigate to `/omics` URL → should see "Access denied" (role gate working)
- [ ] Log in, wait 31 minutes (or set `SESSION_TIMEOUT_MINUTES=1`), confirm redirect to login with "Your session expired" banner
- [ ] Enter wrong password 5× → confirm "Account locked for 15 minutes" message
- [ ] Confirm `.env` is NOT tracked by git: `git status` should not show `.env`

---

## Core Pipeline

- [ ] Open EGFR/NSCLC showcase scenario → confirm GO verdict and score ≥ 75
- [ ] Run `pytest tests/test_e2e_smoke.py -v` → all tests pass (no API key needed)
- [ ] Open Evidence Explorer with a real gene (e.g., BRCA1/breast cancer) → confirm 6 sources populate
- [ ] Run AI Insights → confirm all 5 reasoning modes complete and claims appear
- [ ] Export PDF dossier from Scorecard page → confirm file downloads and opens correctly

---

## Audit Trail

- [ ] Complete a full workflow (Evidence → Insights → Scorecard)
- [ ] Go to Audit Trail page → click "Verify Chain Integrity" → result shows **VALID**
- [ ] Switch to Compliance mode in a project → trigger a HITL gate → confirm e-signature dialog appears
- [ ] Confirm the e-signature record appears in Audit Trail with a 64-char SHA-256 hash

---

## Test Suite

- [ ] `pytest tests/test_e2e_smoke.py -v` → all pass (no keys needed)
- [ ] `pytest tests/test_audit_trail.py -v` → all 11 tests pass including concurrency test
- [ ] `pytest tests/test_auth.py -v` → all pass
- [ ] `pytest tests/test_scoring/ -v` → all pass
- [ ] `RUN_REAL_APIS=1 pytest tests/test_real_apis.py -v` → OpenTargets returns confidence > 0
- [ ] `ANTHROPIC_API_KEY=sk-ant-... pytest tests/test_llm_integration.py -v` → claims returned, no hallucinations

---

## CI/CD

- [ ] Push a commit to `main` → GitHub Actions CI runs automatically
- [ ] All 3 CI jobs pass: **Lint** (ruff), **Tests** (unit + integration + smoke), **Docker Build**
- [ ] Fix any ruff errors before merging: `ruff check src/ tests/`

---

## Docker Deployment

- [ ] `docker compose up` → app starts at `http://localhost:8501` within 60 seconds
- [ ] Health check: `curl http://localhost:8501/_stcore/health` → returns `ok`
- [ ] Run tests inside Docker: `docker compose run --rm test pytest -m integration`
- [ ] Verify Docker image size is reasonable: `docker images bioorchestrator`

---

## Render.com Deployment (Production HTTPS)

1. Push latest code to GitHub
2. Go to [render.com](https://render.com) → **New Web Service** → Connect your GitHub repo
3. Render auto-detects `render.yaml` — review the config
4. In the **Environment** tab, set:
   - `ANTHROPIC_API_KEY` = your actual key
   - `SENTRY_DSN` = your Sentry DSN (optional)
5. Click **Deploy** → wait ~5 minutes for build
6. Access your live HTTPS URL: `https://bioorchestrator.onrender.com`
7. Run through the Core Pipeline checklist against the live URL

- [ ] Render deploy succeeds — no build errors in logs
- [ ] HTTPS URL loads the BioOrchestrator login page
- [ ] EGFR showcase scenario produces GO verdict on live deploy

---

## Backup

- [ ] Run `python scripts/backup_db.py` → archive created in `data/backups/`
- [ ] Verify archive is not corrupted: `tar -tzf data/backups/db_backup_*.tar.gz`
- [ ] Confirm only the 7 most recent backups are kept after repeated runs

---

## Optional: Observability (Sentry)

- [ ] Set `SENTRY_DSN` environment variable
- [ ] Start the app → confirm "Sentry initialized" appears in logs
- [ ] Trigger a deliberate `1/0` exception in dev → confirm error appears in Sentry dashboard within 60s

---

*BioOrchestrator v2 · Pre-Launch Production Checklist*
