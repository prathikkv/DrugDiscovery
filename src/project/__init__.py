"""Project management module -- CRUD operations with audit trail integration."""

from src.project.models import Project
from src.project.service import ProjectService

__all__ = ["ProjectService", "Project"]
