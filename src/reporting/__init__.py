"""Reporting module for BioOrchestrator target assessment dossiers.

Provides data models, data collection, visualization, and chart export
utilities consumed by HTML and PDF renderers.
"""

from src.reporting.models import DossierConfig, DossierData, SectionContent
from src.reporting.data_collector import collect_dossier_data

__all__ = [
    "DossierData",
    "DossierConfig",
    "SectionContent",
    "collect_dossier_data",
]
