"""Reporting module for BioOrchestrator target assessment dossiers.

Provides data models, data collection, visualization, chart export
utilities, and HTML dossier rendering.
"""

from src.reporting.models import DossierConfig, DossierData, SectionContent
from src.reporting.data_collector import collect_dossier_data
from src.reporting.visualizations import VisualizationBuilder
from src.reporting.chart_export import (
    chart_to_png_bytes,
    export_chart_png,
    export_chart_svg,
)
from src.reporting.html_renderer import HTMLDossierRenderer

__all__ = [
    "DossierData",
    "DossierConfig",
    "SectionContent",
    "collect_dossier_data",
    "VisualizationBuilder",
    "HTMLDossierRenderer",
    "export_chart_png",
    "export_chart_svg",
    "chart_to_png_bytes",
]
