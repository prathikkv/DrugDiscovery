"""Reporting module for BioOrchestrator target assessment dossiers.

Provides data models, data collection, visualization, and chart export
utilities consumed by HTML and PDF renderers.
"""

from src.reporting.models import DossierConfig, DossierData, SectionContent
from src.reporting.data_collector import collect_dossier_data
from src.reporting.visualizations import VisualizationBuilder
from src.reporting.chart_export import (
    chart_to_png_bytes,
    export_chart_png,
    export_chart_svg,
)

__all__ = [
    "DossierData",
    "DossierConfig",
    "SectionContent",
    "collect_dossier_data",
    "VisualizationBuilder",
    "export_chart_png",
    "export_chart_svg",
    "chart_to_png_bytes",
]
