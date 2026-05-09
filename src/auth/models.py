"""Authentication data models -- User dataclass and Role enum."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Role(Enum):
    """User roles for role-based access control (REQ-501)."""

    ADMIN = "admin"
    ANALYST = "analyst"
    REVIEWER = "reviewer"


@dataclass
class User:
    """User representation (without password hash for security).

    The password_hash is intentionally excluded -- it should never
    leave the auth module boundary.
    """

    user_id: str
    email: str
    role: Role
    created_at: str
    is_active: bool
    failed_attempts: int
    locked_until: Optional[str]
