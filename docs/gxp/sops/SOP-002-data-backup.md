# SOP-002: Data Backup and Recovery
**Document ID:** SOP-002
**Version:** 1.0
**Date:** 2026-05-13
**Owner:** System Administrator

---

## 1. Purpose
Define backup and recovery procedures for the BioOrchestrator v2 platform data.

## 2. Data Inventory

| Data Type | Location | Criticality | Backup Frequency |
|-----------|----------|-------------|------------------|
| Audit trail DB | data/db/audit.db | CRITICAL | Daily |
| Auth DB | data/db/auth.db | HIGH | Daily |
| Project data | data/projects/ | HIGH | Daily |
| Evidence cache | data/cache/ | MEDIUM | Weekly |
| Showcase scenarios | data/showcase_scenarios/ | LOW | On change |

## 3. Backup Procedure

### 3.1 Daily Backup (Automated)
```bash
DATE=$(date +%Y%m%d)
BACKUP_DIR=/backups/bioorchestrator/$DATE

mkdir -p $BACKUP_DIR
cp data/db/audit.db $BACKUP_DIR/audit.db.bak
cp data/db/auth.db $BACKUP_DIR/auth.db.bak
cp -r data/projects/ $BACKUP_DIR/projects.bak/
echo "Backup completed: $BACKUP_DIR"
```

### 3.2 Backup Verification
```bash
python -c "
from src.compliance.audit_trail import AuditTrail
import os; date = os.environ.get('DATE', '$(date +%Y%m%d)')
trail = AuditTrail(db_path=f'/backups/bioorchestrator/{date}/audit.db.bak')
result = trail.verify_chain()
assert result['valid'], f'Backup audit chain broken: {result}'
print('Audit backup integrity: VERIFIED')
"
```

## 4. Recovery Procedure

### 4.1 Restore from Backup
```bash
# 1. Stop application first
docker compose down

# 2. Restore databases
DATE=20260513  # Replace with target backup date
cp /backups/bioorchestrator/$DATE/audit.db.bak data/db/audit.db
cp /backups/bioorchestrator/$DATE/auth.db.bak data/db/auth.db

# 3. Restart application
docker compose up -d
```

### 4.2 Post-Recovery Verification
1. Log in with admin credentials
2. Navigate to Audit Trail — verify chain integrity badge shows "Valid"
3. Confirm project data is accessible
4. Run: `docker compose run --rm test pytest -m validation`
