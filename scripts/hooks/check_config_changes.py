#!/usr/bin/env python3
"""Pre-commit hook: flag configuration file changes for review (REQ-806).

When scoring weights, pipeline config, or Streamlit config files are staged,
prints a warning reminding the developer to document the change in the audit
trail. This hook DOES NOT block the commit (exits 0 always).

Per SOP-003 (Change Control): config changes require audit trail documentation.
"""

import sys

# Config files that trigger the warning
CONFIG_FILES = {
    "src/config.py",
    "src/scoring/weights.py",
    "src/pipeline/config.py",
    ".streamlit/config.toml",
    ".streamlit/secrets.toml",
}


def main() -> int:
    """Print warning if any staged file is a config file. Always exits 0."""
    # sys.argv[1:] contains the list of staged files matching the `files` pattern
    # from .pre-commit-config.yaml. If no files match, argv is empty.
    changed_configs = [f for f in sys.argv[1:] if f in CONFIG_FILES]

    if changed_configs:
        print()
        print("WARNING: Configuration files have been modified:")
        for f in changed_configs:
            print(f"  - {f}")
        print()
        print(
            "Per SOP-003 (Change Control), configuration changes must be documented "
            "in the audit trail before deployment. Ensure you have logged an audit "
            "record describing the change and its justification."
        )
        print()

    # Always exit 0 -- this is a warning, not a blocker
    return 0


if __name__ == "__main__":
    sys.exit(main())
