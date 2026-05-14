# SOP-001: System Operation
**Document ID:** SOP-001
**Version:** 1.0
**Date:** 2026-05-13
**Owner:** System Administrator

---

## 1. Purpose
Define procedures for starting, stopping, and monitoring the BioOrchestrator v2 platform.

## 2. Prerequisites
- Docker Desktop installed and running
- Repository cloned at project root
- `.env` file with required API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY)

## 3. Starting the Application

### 3.1 Standard Start
```bash
cd /path/to/bioorchestrator
docker compose up -d
```
Wait for health check to pass (up to 60 seconds):
```bash
docker compose ps  # App status should show "healthy"
```
Access the application at: http://localhost:8501

### 3.2 Verify Startup
1. Navigate to http://localhost:8501
2. Confirm login page renders without errors
3. Log in with admin credentials
4. Navigate to Audit Trail page and confirm records are loading

## 4. Stopping the Application
```bash
docker compose down
```

## 5. Running Tests
```bash
# Unit tests only (fast, <30s)
docker compose run --rm test pytest -m unit

# All tests
docker compose run --rm test pytest

# Validation suite only
docker compose run --rm test pytest -m validation -v
```

## 6. Daily Checks
- [ ] Application responds at http://localhost:8501
- [ ] Audit trail page loads without integrity errors
- [ ] No ERROR-level log entries in `docker compose logs app`
