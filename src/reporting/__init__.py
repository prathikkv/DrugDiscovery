"""Reporting module for BioOrchestrator target assessment dossiers.

Provides data models, data collection, visualization, chart export
utilities, HTML dossier rendering, and PDF dossier rendering.
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
from src.reporting.pdf_renderer import PDFDossierRenderer, generate_dossier

__all__ = [
    "DossierData",
    "DossierConfig",
    "SectionContent",
    "collect_dossier_data",
    "VisualizationBuilder",
    "HTMLDossierRenderer",
    "PDFDossierRenderer",
    "generate_dossier",
    "export_chart_png",
    "export_chart_svg",
    "chart_to_png_bytes",
]
