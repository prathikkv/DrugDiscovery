#!/usr/bin/env python3
"""Pre-commit hook: detect direct audit trail manipulation in staged files (REQ-806).

Scans staged Python files for SQL patterns that directly DELETE or UPDATE
records in the audit_records table, which would violate the append-only
integrity guarantee required by 21 CFR Part 11 (REQ-503).

This hook checks file CONTENT only -- it never opens a database connection
and does not fail on clean checkouts with no database present.
"""

import re
import sys

# Patterns indicating direct audit table bypass
AUDIT_BYPASS_PATTERNS = [
    (
        r"(?i)\bDELETE\s+FROM\s+audit_records\b",
        "Direct DELETE from audit_records table (violates append-only audit trail)",
    ),
    (
        r"(?i)\bUPDATE\s+audit_records\b",
        "Direct UPDATE on audit_records table (violates append-only audit trail)",
    ),
    (
        r"(?i)DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?audit_records\b",
        "DROP TABLE audit_records (would destroy audit trail)",
    ),
]

# Exclude hook scripts themselves and test fixtures from the check
EXCLUDE_PATHS = {
    "scripts/hooks/",
    "tests/",
    "docs/",
}


def main() -> int:
    """Scan staged files for audit trail bypass patterns.

    Filenames are passed as argv[1:] by the pre-commit framework.
    Returns 0 if no issues found, 1 if any bypass pattern detected.
    """
    errors: list[str] = []

    for filepath in sys.argv[1:]:
        # Skip excluded paths
        if any(filepath.startswith(exc) for exc in EXCLUDE_PATHS):
            continue

        try:
            with open(filepath, encoding="utf-8", errors="replace") as f:
                for lineno, line in enumerate(f, start=1):
                    for pattern, message in AUDIT_BYPASS_PATTERNS:
                        if re.search(pattern, line):
                            errors.append(f"{filepath}:{lineno}: {message}")
                            errors.append(f"  >>> {line.rstrip()}")
        except OSError:
            # File may have been deleted -- skip it
            continue

    if errors:
        print("Audit trail integrity check FAILED:")
        print()
        for error in errors:
            print(f"  {error}")
        print()
        print(
            "The audit trail is append-only (21 CFR Part 11 / REQ-503). "
            "Do not modify audit_records directly. "
            "Use AuditTrail.log() to append new records."
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
