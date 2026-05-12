"""Chart export utilities: PNG, SVG file export and in-memory PNG bytes.

Provides functions for exporting Plotly figures to static image files
and in-memory byte buffers for embedding in PDF reports.
"""

from __future__ import annotations

import logging
from pathlib import Path

import plotly.graph_objects as go

logger = logging.getLogger(__name__)

# Runtime compatibility check for kaleido
try:
    import kaleido

    _kaleido_version = getattr(kaleido, "__version__", "unknown")
    logger.debug("kaleido %s loaded", _kaleido_version)
except ImportError:
    _kaleido_version = None
    logger.debug(
        "kaleido not installed; to_image/write_image will fail. "
        "Install with: pip install kaleido"
    )


def export_chart_png(
    fig: go.Figure,
    output_path: Path,
    width: int = 900,
    height: int = 550,
    scale: int = 2,
) -> Path:
    """Export Plotly figure to PNG file.

    Args:
        fig: Plotly Figure to export.
        output_path: Destination file path.
        width: Image width in pixels.
        height: Image height in pixels.
        scale: Scale factor for retina/print quality (default 2x).

    Returns:
        The output_path after successful write.

    Raises:
        ValueError: If kaleido is not installed.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig.write_image(
        str(output_path),
        format="png",
        width=width,
        height=height,
        scale=scale,
    )
    logger.info("Exported PNG: %s (%dx%d @%dx)", output_path, width, height, scale)
    return output_path


def export_chart_svg(
    fig: go.Figure,
    output_path: Path,
    width: int = 900,
    height: int = 550,
) -> Path:
    """Export Plotly figure to SVG file.

    Args:
        fig: Plotly Figure to export.
        output_path: Destination file path.
        width: Image width in pixels.
        height: Image height in pixels.

    Returns:
        The output_path after successful write.

    Raises:
        ValueError: If kaleido is not installed.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig.write_image(
        str(output_path),
        format="svg",
        width=width,
        height=height,
    )
    logger.info("Exported SVG: %s (%dx%d)", output_path, width, height)
    return output_path


def chart_to_png_bytes(
    fig: go.Figure,
    width: int = 900,
    height: int = 550,
    scale: int = 2,
) -> bytes:
    """Convert Plotly figure to PNG bytes (for in-memory PDF embedding).

    Args:
        fig: Plotly Figure to convert.
        width: Image width in pixels.
        height: Image height in pixels.
        scale: Scale factor for retina/print quality (default 2x).

    Returns:
        PNG image as bytes.

    Raises:
        ValueError: If kaleido is not installed.
    """
    return fig.to_image(format="png", width=width, height=height, scale=scale)
