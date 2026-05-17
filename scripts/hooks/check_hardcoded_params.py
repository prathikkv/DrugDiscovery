#!/usr/bin/env python3
"""Pre-commit hook: detect hardcoded parameters in Python source files (REQ-806).

Scans for hardcoded credentials (API keys, passwords, tokens) and authorization
headers in Python source files. These should always come from environment
variables or src/config.py, not be embedded in source code.

Excludes: tests/, scripts/hooks/, docs/, data/ -- these files legitimately
contain pattern strings and examples.
"""

import re
import sys

# (pattern, message) pairs -- ordered from most specific to least
FORBIDDEN_PATTERNS = [
    (
        r'(?i)\b(api_key|api_secret|access_token|secret_key|password|passwd)\s*=\s*["\'][^"\']{4,}["\']',
        "Hardcoded credential detected (should use environment variable or src/config.py)",
    ),
    (
        r'(?i)\b(bearer|authorization)\s*[=:]\s*["\'][A-Za-z0-9+/=_\-]{20,}["\']',
        "Hardcoded authorization header value detected",
    ),
]

# Paths excluded from this check
EXCLUDE_PATHS = {
    "tests/",
    "scripts/",
    "docs/",
    "data/",
}

# File extensions to check
ALLOWED_EXTENSIONS = {".py"}


def main() -> int:
    """Check staged files for hardcoded parameters.

    Returns 0 if clean, 1 if any forbidden pattern detected.
    """
    errors: list[str] = []

    for filepath in sys.argv[1:]:
        # Only check Python source files
        if not any(filepath.endswith(ext) for ext in ALLOWED_EXTENSIONS):
            continue

        # Skip excluded paths
        if any(filepath.startswith(exc) for exc in EXCLUDE_PATHS):
            continue

        try:
            with open(filepath, encoding="utf-8", errors="replace") as f:
                for lineno, line in enumerate(f, start=1):
                    # Skip comment lines
                    stripped = line.lstrip()
                    if stripped.startswith("#"):
                        continue

                    for pattern, message in FORBIDDEN_PATTERNS:
                        if re.search(pattern, line):
                            errors.append(
                                f"{filepath}:{lineno}: {message}"
                            )
                            errors.append(f"  >>> {line.rstrip()}")
                            break  # One error per line is enough
        except OSError:
            continue

    if errors:
        print("Hardcoded parameters detected:")
        print()
        for error in errors:
            print(f"  {error}")
        print()
        print(
            "Move credentials to environment variables and read via os.getenv(). "
            "Move scoring thresholds and magic numbers to src/config.py."
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
