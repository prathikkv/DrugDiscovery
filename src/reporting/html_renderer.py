"""HTML dossier renderer: produce self-contained interactive HTML reports.

Renders DossierData into a professional HTML file with embedded interactive
Plotly charts, consulting-grade CSS styling, and all 7 dossier sections.
Uses Jinja2 templates from the ``templates/`` directory.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.reporting.models import DossierConfig, DossierData
from src.reporting.visualizations import VisualizationBuilder

logger = logging.getLogger(__name__)


class HTMLDossierRenderer:
    """Renders DossierData as an interactive HTML file with embedded Plotly charts.

    The renderer uses Jinja2 templates in ``src/reporting/templates/`` and the
    VisualizationBuilder to produce a complete, self-contained HTML file that
    can be viewed offline in any browser.

    Attributes:
        config: Rendering configuration controlling chart sizes, plotly.js
            inclusion mode, and brand settings.
    """

    def __init__(self, config: DossierConfig | None = None) -> None:
        self.config = config or DossierConfig()
        self._env = Environment(
            loader=FileSystemLoader(Path(__file__).parent / "templates"),
            autoescape=select_autoescape(["html"]),
        )
        # Register custom Jinja2 filters
        self._env.filters["format_score"] = self._format_score
        self._env.filters["format_pct"] = self._format_pct
        self._env.filters["verdict_color"] = self._verdict_color

    def render(self, dossier_data: DossierData) -> str:
        """Render complete HTML dossier string.

        1. Builds all Plotly figures via VisualizationBuilder.
        2. Converts each figure to an HTML div string with interactive controls.
        3. Renders the Jinja2 dossier template with data and chart divs.

        Args:
            dossier_data: Complete dossier data container.

        Returns:
            Rendered HTML string.
        """
        # Build all Plotly figures
        viz_builder = VisualizationBuilder(dossier_data)
        figures = viz_builder.build_all()

        # Convert figures to HTML div strings
        chart_divs = self._figures_to_divs(figures)

        # Build plotly.js header (included in first chart or standalone)
        plotly_js_header = self._build_plotly_js_header(figures)

        # Render template
        template = self._env.get_template("dossier.html")
        html = template.render(
            dossier=dossier_data,
            charts=chart_divs,
            config=self.config,
            plotly_js_header=plotly_js_header,
        )

        logger.info(
            "Rendered HTML dossier for %s (%d chars, %d charts)",
            dossier_data.gene_symbol,
            len(html),
            len(chart_divs),
        )
        return html

    def render_to_file(self, dossier_data: DossierData, output_path: Path) -> Path:
        """Render and write HTML dossier to file.

        Creates parent directories if they do not exist.

        Args:
            dossier_data: Complete dossier data container.
            output_path: Destination file path.

        Returns:
            The output_path after successful write.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        html = self.render(dossier_data)
        output_path.write_text(html, encoding="utf-8")

        logger.info("Wrote HTML dossier: %s (%d bytes)", output_path, len(html))
        return output_path

    def _figures_to_divs(self, figures: dict[str, Any]) -> dict[str, str]:
        """Convert Plotly figures to HTML div strings.

        The first chart includes plotly.js (per config); subsequent charts
        set ``include_plotlyjs=False`` to avoid loading it multiple times.

        Args:
            figures: Dict of chart_id -> Plotly Figure.

        Returns:
            Dict of chart_id -> HTML div string (safe to embed via ``| safe``).
        """
        chart_divs: dict[str, str] = {}
        first = True

        plotly_config = {
            "displayModeBar": True,
            "toImageButtonOptions": {
                "format": "png",
                "height": 600,
                "width": 900,
                "scale": 2,
            },
        }

        for chart_id, fig in figures.items():
            try:
                if first:
                    include_js = self.config.include_plotlyjs
                    first = False
                else:
                    include_js = False

                div_html = fig.to_html(
                    full_html=False,
                    include_plotlyjs=include_js,
                    config=plotly_config,
                )
                chart_divs[chart_id] = div_html
            except Exception:
                logger.warning(
                    "Failed to convert chart '%s' to HTML div",
                    chart_id,
                    exc_info=True,
                )

        return chart_divs

    def _build_plotly_js_header(self, figures: dict[str, Any]) -> str:
        """Build plotly.js script header if no charts will include it inline.

        When there are no figures, returns an empty string.
        When figures exist, the first chart's div already includes plotly.js,
        so this returns an empty string as well. This method is a hook for
        future customization (e.g., loading plotly.js from a local file).

        Args:
            figures: Dict of chart_id -> Plotly Figure.

        Returns:
            HTML script tag string or empty string.
        """
        if not figures:
            # No charts -- no need for plotly.js at all
            return ""
        # plotly.js is included in the first chart div already
        return ""

    @staticmethod
    def _format_score(value: Any) -> str:
        """Format numeric score with one decimal place."""
        try:
            return f"{float(value):.1f}"
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _format_pct(value: Any) -> str:
        """Format 0-1 fraction as percentage string."""
        try:
            return f"{float(value) * 100:.0f}%"
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _verdict_color(value: str) -> str:
        """Map verdict level to CSS color."""
        colors = {
            "GO": "#00b300",
            "CONDITIONAL": "#ff9900",
            "NO-GO": "#dd0000",
        }
        return colors.get(str(value).upper(), "#666666")
