"""Authentication module -- registration, login, RBAC, and account lockout."""

from src.auth.models import Role, User
from src.auth.service import AuthService

__all__ = ["AuthService", "User", "Role"]
