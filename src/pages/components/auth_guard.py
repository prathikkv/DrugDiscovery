"""Authentication and authorization guards for BioOrchestrator pages.

Call at the top of any page that requires authentication or a specific role.
These functions stop page rendering immediately if the check fails.

Usage:
    from src.pages.components.auth_guard import require_auth, require_role

    # Any authenticated user:
    require_auth()

    # Only admin or analyst:
    require_role(["admin", "analyst"])
"""

from __future__ import annotations

import streamlit as st


def require_auth() -> None:
    """Stop page render if the user is not authenticated.

    Displays an access-denied message and halts execution via st.stop().
    """
    if "user" not in st.session_state:
        st.error("You must be logged in to access this page.")
        st.info("Please log in using the Login page.")
        st.stop()


def require_role(allowed_roles: list[str]) -> None:
    """Stop page render if the authenticated user's role is not in allowed_roles.

    Also calls require_auth() first, so a single call is sufficient for
    pages that need both authentication and a specific role.

    Args:
        allowed_roles: List of role strings that may access this page.
                       e.g. ["admin", "analyst"]
    """
    require_auth()
    user_role = st.session_state["user"].get("role", "")
    if user_role not in allowed_roles:
        st.error(
            f"Access denied. This page requires role: **{', '.join(allowed_roles)}**. "
            f"Your role is **{user_role}**."
        )
        st.stop()
