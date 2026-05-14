# SOP-005: User Management
**Document ID:** SOP-005
**Version:** 1.0
**Date:** 2026-05-13
**Owner:** System Administrator

---

## 1. Purpose
Define procedures for creating, managing, and deactivating user accounts in BioOrchestrator v2.

## 2. User Roles

| Role | Permissions | Typical User |
|------|------------|--------------|
| admin | All operations, user management, config changes | System administrator |
| analyst | Create projects, run analyses, view all results | Pharma scientist, consultant |
| reviewer | View results, approve HITL gates (read-only otherwise) | Principal investigator, VP |

## 3. Account Creation

### 3.1 Admin Creates Account
1. Log in to the application as admin
2. Navigate to Admin > User Management (or use CLI below)
3. Provide: email address, temporary password, role assignment
4. Notify user of credentials via secure channel

### 3.2 CLI Account Creation
```bash
python -c "
from src.auth.service import AuthService
auth = AuthService()
user = auth.register(email='analyst@pharma.com', password='TempPass123!', role='analyst')
print(f'Created user: {user.user_id}')
"
```
All account creation actions are logged in the audit trail automatically.

## 4. Account Lockout Resolution
If an analyst is locked out after 5 failed attempts:
```bash
python -c "
from src.auth.service import AuthService
auth = AuthService()
auth.unlock_account(email='analyst@pharma.com')  # admin only
print('Account unlocked')
"
```
The unlock action is recorded in the audit trail with the admin's user_id.

## 5. Account Deactivation
```bash
python -c "
from src.auth.service import AuthService
auth = AuthService()
auth.deactivate_account(email='departed@pharma.com')
print('Account deactivated -- user can no longer log in')
"
```
Deactivation is soft-delete only (consistent with Phase 1 project soft-delete pattern).

## 6. Access Review
- Frequency: Monthly (or after each client engagement)
- Review: Confirm all active accounts are still authorized
- Action: Deactivate any accounts for departed users or expired contractors
- Record: Log the review outcome in the audit trail
