# Phase 6: Deliverables - Research

**Researched:** 2026-05-12
**Domain:** Professional report generation (HTML + PDF dossiers), interactive visualizations, static chart export
**Confidence:** MEDIUM-HIGH

## Summary

Phase 6 transforms all upstream data -- evidence from 6 sources (Phase 3), AI reasoning with 5 modes (Phase 4), and 7-dimension scoring with verdicts (Phase 5) -- into consulting-grade Target Assessment Dossiers that a pharma VP can use for pipeline advancement decisions. The deliverable is dual-format: an interactive HTML dossier with embedded Plotly charts for exploration, and a static PDF dossier via fpdf2 with rendered chart images for archival and offline distribution.

The existing codebase already provides the complete data pipeline: `ScorecardResult` with 7 `DimensionScore` objects and `Verdict`, `AggregatedEvidence` with results from 6 sources, `ReasoningResult` with structured claims and summaries per mode, `AuditTrail` with hash-chained records, and Plotly radar charts via `build_single_radar()` / `build_comparative_radar()`. The existing `bioorchestrator_real/utils/plotting.py` already contains production-quality Plotly visualization functions for UMAP, volcano, heatmap, dot plot, and enrichment charts. Phase 6 must wire these into a cohesive dossier generation pipeline.

The critical technical concern is the Plotly 5.x / Kaleido compatibility issue: Kaleido v1.0.0 is incompatible with Plotly 5.x. The project must use `kaleido==0.2.1` (or `kaleido<1.0.0`) for static image export. This is a well-documented issue (plotly/plotly.py#5241). For the HTML dossier, Jinja2 templates render Plotly charts as interactive `<div>` elements via `fig.to_html(full_html=False, include_plotlyjs='cdn')`. For the PDF dossier, charts are converted to PNG bytes via `fig.to_image(format="png")` and embedded into fpdf2 pages via `pdf.image(io.BytesIO(png_bytes))`.

**Primary recommendation:** Build `src/reporting/` as a standalone package with three layers: (1) a `DossierData` model that collects all inputs into a single serializable container, (2) a `VisualizationBuilder` that creates all Plotly figures from pipeline data, and (3) dual renderers -- `HTMLDossierRenderer` using Jinja2 templates and `PDFDossierRenderer` using fpdf2 subclass with branded headers/footers. Keep chart export (PNG/SVG) as a utility function wrapping `fig.to_image()` and `fig.write_image()`.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fpdf2 | >=2.8.0 (latest 2.8.7) | PDF generation with tables, images, fonts, headers/footers | Pure Python, no system dependencies (no Cairo/Pango). Supports PNG/JPG embedding, rounded rectangles, table styling with FontFace, write_html for basic HTML rendering. Already in project stack. |
| jinja2 | >=3.1.6 | HTML dossier template rendering | Industry standard Python templating. FileSystemLoader for template management, filters for formatting, auto-escaping for security. Already in project stack. |
| plotly | 5.24.1 | Interactive charts (UMAP, heatmap, volcano, radar, evidence) | Already used in scoring module for radar charts and in bioorchestrator_real for all visualization types. Streamlit integration via st.plotly_chart. |
| kaleido | ==0.2.1 | Static image export (PNG/SVG) from Plotly figures | CRITICAL: Must pin to 0.2.1. Kaleido v1.0.0+ is incompatible with Plotly 5.x. Self-contained Chromium binary, no external Chrome needed. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pillow | (fpdf2 dependency) | Image processing for PNG embedding | Automatically installed with fpdf2; handles PNG alpha channel extraction for PDF SMask transparency |
| pydantic | >=2.11.0 | DossierData model, report configuration validation | Already used throughout project; validates dossier sections, chart configs |
| hashlib (stdlib) | 3.x | SHA256 hash of dossier content for audit trail | Already used in compliance module; hash final dossier for provenance |
| io (stdlib) | 3.x | BytesIO for in-memory Plotly-to-fpdf2 image pipeline | No disk writes for intermediate chart images |
| pathlib (stdlib) | 3.x | Output file path management | Already used throughout project |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| fpdf2 | weasyprint | weasyprint requires system Cairo/Pango C libraries -- installation fails on many macOS setups and complicates Docker. fpdf2 is pure Python. |
| fpdf2 | reportlab | reportlab open-source has limited table styling; commercial version is expensive. fpdf2 has better API for tables with FontFace. |
| Jinja2 + fpdf2 | fpdf2 write_html only | write_html supports only a subset of HTML5 (no CSS, limited nesting). Better to use Jinja2 for the HTML dossier and fpdf2's native API for PDF. |
| kaleido 0.2.1 | matplotlib backend | Would require rewriting all Plotly charts as matplotlib. Loses interactivity in HTML dossier. Plotly charts already exist. |

**Installation:**
```bash
pip install "fpdf2>=2.8.0" "jinja2>=3.1.6" "kaleido==0.2.1"
```

Note: plotly 5.24.1 and pydantic >=2.11.0 are already installed.

## Architecture Patterns

### Recommended Project Structure

```
src/reporting/
    __init__.py              # Public API: DossierGenerator, export_chart
    models.py                # DossierData, DossierConfig, SectionContent pydantic models
    data_collector.py        # Collect all upstream data into DossierData
    visualizations.py        # VisualizationBuilder: create all Plotly figures
    chart_export.py          # export_chart_png(), export_chart_svg() wrappers
    html_renderer.py         # HTMLDossierRenderer using Jinja2
    pdf_renderer.py          # PDFDossierRenderer using fpdf2 subclass
    templates/               # Jinja2 HTML templates
        base.html            # Base layout with plotly.js CDN, CSS styling
        dossier.html          # Full dossier template
        sections/
            executive_summary.html
            target_overview.html
            evidence_dimension.html
            ai_synthesis.html
            scorecard.html
            recommendations.html
            audit_trail.html
```

### Pattern 1: Dual-Format Renderer with Shared Data Model

**What:** A single `DossierData` container collects all upstream outputs. Two renderer classes consume this same container to produce HTML and PDF respectively. The data collection is done once; rendering is format-specific.

**When to use:** For every dossier generation request. The generator collects data, then calls the appropriate renderer(s).

**Example:**

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class SectionContent(BaseModel):
    """Content for one section of the dossier."""
    title: str
    narrative: str = ""  # AI-generated or template text
    data: dict = Field(default_factory=dict)  # Structured data for tables/charts
    charts: list[str] = Field(default_factory=list)  # Chart identifiers

class DossierData(BaseModel):
    """Complete data container for dossier generation."""
    gene_symbol: str
    disease_context: Optional[str] = None
    generated_at: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )
    # From Phase 5
    scorecard: dict  # ScorecardResult.model_dump()
    comparative: Optional[dict] = None  # ComparativeScorecard if multi-target
    # From Phase 3
    evidence: dict  # AggregatedEvidence serialized
    # From Phase 4
    reasoning: dict = Field(default_factory=dict)  # mode -> ReasoningResult
    # From Phase 2 (if available)
    pipeline_report: Optional[dict] = None
    # Sections
    sections: dict[str, SectionContent] = Field(default_factory=dict)
```

### Pattern 2: fpdf2 Subclass for Branded PDF

**What:** Subclass `FPDF` to define consistent headers, footers, and page numbering. Override `header()` and `footer()` methods. The header includes the dossier title, gene symbol, and a horizontal rule. The footer includes page numbers and generation timestamp.

**When to use:** For the PDF renderer. This is the standard fpdf2 pattern for multi-page documents.

**Example:**

```python
from fpdf import FPDF, FontFace

class DossierPDF(FPDF):
    """Branded PDF for Target Assessment Dossiers."""

    def __init__(self, gene_symbol: str, disease_context: str = ""):
        super().__init__()
        self.gene_symbol = gene_symbol
        self.disease_context = disease_context
        # Professional sans-serif
        self.set_auto_page_break(auto=True, margin=25)

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(0, 113, 227)  # #0071e3 brand color
        self.cell(0, 8, f"Target Assessment Dossier: {self.gene_symbol}", align="L")
        self.ln(4)
        self.set_draw_color(0, 113, 227)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")
```

### Pattern 3: Plotly to fpdf2 In-Memory Image Pipeline

**What:** Convert Plotly figures to PNG bytes using `fig.to_image(format="png")`, wrap in `io.BytesIO`, and embed in fpdf2 via `pdf.image()`. No intermediate files on disk.

**When to use:** For every chart embedded in the PDF dossier.

**Example:**

```python
import io

def embed_plotly_chart(pdf: FPDF, fig, width: float = None) -> None:
    """Embed a Plotly figure as a PNG image in the PDF."""
    png_bytes = fig.to_image(
        format="png",
        width=800,
        height=500,
        scale=2,  # 2x for retina/print quality
    )
    img_buffer = io.BytesIO(png_bytes)
    pdf.image(img_buffer, w=width or pdf.epw)
```

### Pattern 4: Jinja2 Template with Plotly Div Embedding

**What:** For the HTML dossier, render Plotly charts as interactive `<div>` elements using `fig.to_html(full_html=False)`. The first chart includes `include_plotlyjs='cdn'`; subsequent charts use `include_plotlyjs=False` to avoid loading plotly.js multiple times.

**When to use:** For the HTML renderer.

**Example:**

```python
from jinja2 import Environment, FileSystemLoader

def render_html_dossier(dossier_data: DossierData, figures: dict) -> str:
    """Render interactive HTML dossier with embedded Plotly charts."""
    env = Environment(loader=FileSystemLoader("src/reporting/templates"))
    template = env.get_template("dossier.html")

    # Convert figures to HTML divs
    chart_divs = {}
    first = True
    for name, fig in figures.items():
        chart_divs[name] = fig.to_html(
            full_html=False,
            include_plotlyjs='cdn' if first else False,
        )
        first = False

    return template.render(
        dossier=dossier_data,
        charts=chart_divs,
    )
```

### Anti-Patterns to Avoid

- **Writing charts to disk then reading back:** Use `io.BytesIO` for the Plotly-to-fpdf2 pipeline. Disk I/O is slower and creates cleanup concerns.
- **Using fpdf2's write_html for the entire PDF:** write_html has severe CSS limitations (no flexbox, no grid, minimal tag nesting). Use fpdf2's native API (cell, multi_cell, table, image) for PDF and reserve write_html for small HTML snippets within cells only.
- **Loading plotly.js multiple times in HTML:** Use `include_plotlyjs='cdn'` once, then `include_plotlyjs=False` for all subsequent charts in the same HTML document.
- **Using kaleido v1.x with Plotly 5.x:** This is a known incompatibility. Always pin `kaleido==0.2.1` or `kaleido<1.0.0`.
- **Generating dossier without collecting data first:** Always build the complete DossierData container before invoking either renderer. Do not have renderers fetching data.
- **Embedding SVG from Plotly into fpdf2:** fpdf2 does not properly render Plotly SVG because Plotly uses `<text>` SVG tags that fpdf2's SVG parser does not handle. Use PNG format for PDF embedding.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF page layout with headers/footers | Custom page tracking and margin math | fpdf2 subclass with header()/footer() overrides | fpdf2 handles automatic page breaks, restores fonts/colors after breaks, manages page numbering with {nb} placeholder |
| HTML template rendering | String concatenation or f-strings for HTML | Jinja2 Environment with FileSystemLoader | Auto-escaping prevents XSS in user-provided gene names/descriptions, template inheritance keeps layouts DRY, filters handle formatting |
| Chart static export | Custom matplotlib recreation of Plotly charts | kaleido 0.2.1 via fig.to_image() | Kaleido bundles Chromium for pixel-perfect rendering of Plotly figures including WebGL traces (Scattergl) |
| Table styling in PDF | Manual cell-by-cell color/font changes | fpdf2 table() context manager with FontFace headings_style | FontFace handles header colors, cell_fill_mode handles alternating row colors, col_widths handles column sizing |
| Professional color formatting | Manual RGB tuples everywhere | Constants module with named colors from design system (REQ-606: primary #0071e3) | Consistent brand identity, single source of truth for color changes |

**Key insight:** The dossier generation problem decomposes cleanly into data collection (serialize upstream outputs), visualization (create Plotly figures), and rendering (format-specific output). Keeping these three concerns separate makes the system testable without requiring upstream services.

## Common Pitfalls

### Pitfall 1: Kaleido Version Incompatibility with Plotly 5.x
**What goes wrong:** Installing `kaleido>=1.0.0` with `plotly==5.24.1` produces: "You have Plotly version 5.24.1, which is not compatible with this version of Kaleido (1.0.0)." All `fig.to_image()` and `fig.write_image()` calls fail silently or raise errors.
**Why it happens:** Kaleido v1.0.0 was a complete rewrite that dropped the `kaleido.scopes.plotly` API used by Plotly 5.x. Kaleido v1 requires Plotly 6.1.1+.
**How to avoid:** Pin `kaleido==0.2.1` in requirements. Add a startup assertion: `import kaleido; assert kaleido.__version__.startswith("0.")`.
**Warning signs:** `ImportError` from `kaleido.scopes`, empty PNG files, or `fig.to_image()` returning None.

### Pitfall 2: fpdf2 SVG Rendering of Plotly Charts
**What goes wrong:** Embedding Plotly-generated SVG into fpdf2 produces charts with missing axis labels, tick marks, and text elements.
**Why it happens:** Plotly places text content in `<text>` SVG elements with complex positioning attributes (`transform`, `text-anchor`, `dominant-baseline`). fpdf2's SVG parser does not support all SVG text attributes.
**How to avoid:** Always use PNG format for Plotly-to-PDF embedding. Use high `scale` parameter (2-3x) for print quality. Reserve SVG export for standalone chart downloads only.
**Warning signs:** Charts render correctly in browser but appear incomplete in PDF.

### Pitfall 3: BytesIO Object Closure After fpdf2 image()
**What goes wrong:** Calling `pdf.image(bytesio_obj)` may close the BytesIO stream. Subsequent attempts to read from the same BytesIO object fail.
**Why it happens:** fpdf2's PNG processing may close the stream after reading (documented in fpdf2 issue #881).
**How to avoid:** Create a fresh `io.BytesIO(png_bytes)` for each `pdf.image()` call. Do not reuse BytesIO objects.
**Warning signs:** `ValueError: I/O operation on closed file` on the second use of a BytesIO object.

### Pitfall 4: Multi-Page Table Splitting in fpdf2
**What goes wrong:** Large evidence tables split across pages with header row appearing only on page 1, making page 2+ unreadable.
**Why it happens:** Default table behavior. Must explicitly enable header repetition.
**How to avoid:** Use `pdf.table(repeat_headings=1)` or `first_row_as_headings=True` (which repeats by default). Verify with test data that exceeds a single page.
**Warning signs:** Tables on later pages start without column headers.

### Pitfall 5: Plotly.js CDN Loading in HTML Dossier
**What goes wrong:** HTML dossier works online but charts are blank when opened offline.
**Why it happens:** Using `include_plotlyjs='cdn'` requires internet connectivity. Pharma environments may be air-gapped.
**How to avoid:** Provide a configuration option: `include_plotlyjs=True` for self-contained HTML (~3MB larger but fully offline), `include_plotlyjs='cdn'` for smaller files when connectivity is guaranteed. Default to `True` for pharma deployments.
**Warning signs:** Charts show empty divs with no JavaScript errors (plotly.js simply never loads).

### Pitfall 6: Missing Audit Trail in Generated Dossiers
**What goes wrong:** Dossier is generated but the generation event is not recorded in the audit trail, breaking 21 CFR Part 11 compliance.
**Why it happens:** Developers focus on rendering and forget to call `audit_trail.append_record()` after generation.
**How to avoid:** Make audit trail logging a mandatory step in the `DossierGenerator.generate()` method. Include the dossier content hash in the audit record. Test that generation always produces an audit record.
**Warning signs:** Audit trail query for `resource_type="dossier"` returns no records.

## Code Examples

Verified patterns from official sources:

### fpdf2 Professional Table with Styling
```python
# Source: https://py-pdf.github.io/fpdf2/Tables.html
from fpdf import FPDF, FontFace

pdf = FPDF()
pdf.add_page()
pdf.set_font("Helvetica", size=10)

headings_style = FontFace(
    emphasis="BOLD",
    color=(255, 255, 255),
    fill_color=(0, 113, 227),  # #0071e3 brand blue
)

table_data = [
    ["Dimension", "Score", "Max", "Normalized", "Status"],
    ["Genetic Evidence", "12.5", "15", "0.833", "STRONG"],
    ["Expression Biology", "10.2", "15", "0.680", "MODERATE"],
]

with pdf.table(
    headings_style=headings_style,
    cell_fill_color=245,
    cell_fill_mode="ROWS",
    col_widths=(35, 15, 15, 20, 15),
    text_align=("LEFT", "CENTER", "CENTER", "CENTER", "CENTER"),
    line_height=6,
) as table:
    for row_data in table_data:
        table.row(row_data)
```

### fpdf2 Embed Plotly Chart as PNG
```python
# Sources: https://py-pdf.github.io/fpdf2/Maths.html, https://py-pdf.github.io/fpdf2/Images.html
import io
from fpdf import FPDF

def embed_chart(pdf: FPDF, fig, width: float = None, caption: str = "") -> None:
    """Embed a Plotly figure as high-resolution PNG in PDF."""
    png_bytes = fig.to_image(
        format="png",
        width=900,
        height=550,
        scale=2,  # Retina/print quality
    )
    pdf.image(io.BytesIO(png_bytes), w=width or pdf.epw)
    if caption:
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(128, 128, 128)
        pdf.cell(0, 5, caption, align="C")
        pdf.ln(4)
```

### Plotly Interactive Chart for HTML Embedding
```python
# Source: https://plotly.com/python/interactive-html-export/
import plotly.graph_objects as go

def chart_to_html_div(fig: go.Figure, first_chart: bool = False) -> str:
    """Convert Plotly figure to an HTML div string for embedding."""
    return fig.to_html(
        full_html=False,
        include_plotlyjs='cdn' if first_chart else False,
        config={
            'displayModeBar': True,
            'toImageButtonOptions': {
                'format': 'png',
                'filename': 'chart_export',
                'height': 600,
                'width': 900,
                'scale': 2,
            },
        },
    )
```

### Jinja2 Template for Dossier Section
```html
{# Source: Jinja2 standard template patterns #}
{% macro evidence_section(dim_name, dim_score, sub_scores, narrative) %}
<div class="evidence-section">
    <h3>{{ dim_name }}</h3>
    <div class="score-bar">
        <div class="score-fill"
             style="width: {{ (dim_score.score / dim_score.max_score * 100)|round }}%">
            {{ dim_score.score }}/{{ dim_score.max_score }}
        </div>
    </div>
    <table class="sub-scores">
        <tr><th>Sub-Score</th><th>Value</th><th>Max</th><th>Source</th></tr>
        {% for sub in sub_scores %}
        <tr>
            <td>{{ sub.name }}</td>
            <td>{{ sub.value }}</td>
            <td>{{ sub.max_value }}</td>
            <td>{{ sub.data_source }}</td>
        </tr>
        {% endfor %}
    </table>
    {% if narrative %}
    <div class="narrative">{{ narrative }}</div>
    {% endif %}
</div>
{% endmacro %}
```

### Chart Export Utility (PNG/SVG)
```python
# Source: https://plotly.com/python/static-image-export/
import plotly.graph_objects as go
from pathlib import Path

def export_chart(
    fig: go.Figure,
    output_path: Path,
    format: str = "png",
    width: int = 900,
    height: int = 550,
    scale: int = 2,
) -> Path:
    """Export a Plotly figure to PNG or SVG file.

    Args:
        fig: Plotly Figure object
        output_path: Where to save (extension determines format)
        format: 'png' or 'svg'
        width: Image width in pixels
        height: Image height in pixels
        scale: Resolution multiplier (2 for retina)

    Returns:
        Path to the saved file
    """
    fig.write_image(
        str(output_path),
        format=format,
        width=width,
        height=height,
        scale=scale,
    )
    return output_path
```

### fpdf2 Rounded Rectangle for Score Cards
```python
# Source: https://py-pdf.github.io/fpdf2/Shapes.html
from fpdf import FPDF

def draw_verdict_badge(pdf: FPDF, verdict_level: str, x: float, y: float):
    """Draw a colored verdict badge (GO/CONDITIONAL/NO-GO)."""
    color_map = {
        "GO": (0, 180, 0),
        "CONDITIONAL": (255, 165, 0),
        "NO-GO": (220, 0, 0),
    }
    r, g, b = color_map.get(verdict_level, (128, 128, 128))
    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 12)
    # Rounded rectangle badge
    pdf.rect(x, y, 40, 12, round_corners=True, style="F")
    pdf.set_xy(x, y + 1)
    pdf.cell(40, 10, verdict_level, align="C")
```

## Dossier Section Structure

The Target Assessment Dossier contains these required sections per REQ-702:

### 1. Executive Summary (1 page)
- Gene symbol, disease context, generation date
- Overall composite score with verdict badge (GO/CONDITIONAL/NO-GO)
- 3-5 sentence overview synthesized from AI reasoning (SYNTHESIS mode)
- Key strengths and risks bullet points
- Radar chart (single target) embedded

### 2. Target Overview (1 page)
- Gene identifiers: canonical symbol, Ensembl ID, UniProt accession
- Protein function (from UniProt evidence)
- Disease association context
- Known synonyms / aliases

### 3. Seven Evidence Dimensions (5-10 pages)
One subsection per dimension, each containing:
- Dimension score with sub-score breakdown table
- Data coverage indicator
- AI-generated narrative (from SYNTHESIS mode claims relevant to dimension)
- Relevant visualization (where applicable):
  - Genetic Evidence: association strength chart
  - Expression Biology: expression heatmap, UMAP overlay
  - Druggability: compound activity chart
  - Safety/Selectivity: tissue expression breadth
  - Competitive Landscape: clinical trial phase distribution
  - Clinical/Translational: trial timeline
  - Literature Consensus: publication trend chart

### 4. AI Synthesis (2-3 pages)
- Full synthesis narrative from SYNTHESIS mode
- Key claims with confidence scores and source citations
- Contradiction analysis (from CONTRADICTION mode)
- Evidence gaps (from GAP mode)
- Hypothesis suggestions (from HYPOTHESIS mode)

### 5. Scorecard (1-2 pages)
- Full 7-dimension scoring table with sub-scores
- Composite score computation breakdown (weights, normalized values)
- Verdict rationale with dimension minimum violations
- Comparative radar chart (if multiple targets assessed)

### 6. Recommendations (1 page)
- GO/CONDITIONAL/NO-GO recommendation with rationale
- Key risks and mitigations
- Suggested next steps / experiments
- Data gaps to address

### 7. Audit Trail (1-2 pages)
- Evidence source versions and fetch timestamps
- Evidence hash for reproducibility
- AI model, prompt versions, tool calls used
- Scoring formula version and weight configuration
- Generation timestamp and user who triggered it

## Visualization Requirements

### Required Charts (REQ-703)

| Chart Type | Library | Data Source | HTML Format | PDF Format |
|------------|---------|------------|-------------|------------|
| UMAP plot (cell type) | Plotly Scattergl | Pipeline AnnData obsm['X_umap'] | Interactive div | Static PNG |
| UMAP plot (gene expression overlay) | Plotly Scattergl | Pipeline AnnData .X or .raw.X | Interactive div | Static PNG |
| Expression heatmap | Plotly Heatmap | Pipeline DE results | Interactive div | Static PNG |
| Volcano plot | Plotly Scattergl | Pipeline DE results | Interactive div | Static PNG |
| Radar chart (single target) | Plotly Scatterpolar | ScorecardResult.composite.dimension_scores | Interactive div | Static PNG |
| Radar chart (comparative) | Plotly Scatterpolar | ComparativeScorecard.scorecards | Interactive div | Static PNG |
| Evidence dimension bar chart | Plotly Bar | ScorecardResult dimension scores | Interactive div | Static PNG |
| Score breakdown table | fpdf2 table / HTML table | DimensionScore sub_scores | HTML table | fpdf2 table |

### Chart Export (REQ-704)

Individual charts exportable as PNG or SVG via:
- HTML dossier: Plotly's built-in modebar download button (configured via `config.toImageButtonOptions`)
- Standalone export: `export_chart(fig, path, format="png"|"svg")`

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Orca for static export | Kaleido for static export | Plotly 4.9+ / 2020 | Orca required separate npm/electron install; kaleido is pip-installable |
| kaleido 0.x (bundled Chromium) | kaleido 1.x (external Chrome) | Late 2024 | v1 requires Chrome installed, has 50x performance regression in some cases. We stay on 0.2.1 for Plotly 5 compat. |
| fpdf (original) | fpdf2 | 2020+ | fpdf2 is the maintained fork with tables, Unicode, images in cells, rounded corners |
| reportlab for PDF | fpdf2 for PDF | Project decision | fpdf2 is pure Python with no system deps, simpler API, sufficient for consulting-grade reports |
| HTML-to-PDF via wkhtmltopdf | Dual rendering (native HTML + native PDF) | Project architecture | Avoids system dependency, gives full control over both formats |

**Deprecated/outdated:**
- **Orca:** Deprecated in favor of kaleido. Do not use.
- **kaleido.scopes.plotly:** Removed in kaleido v1. Only exists in kaleido 0.x which is what we use.
- **fpdf (original):** Unmaintained since 2015. fpdf2 is the active fork.

## Open Questions

1. **Pipeline data availability for dossier**
   - What we know: The pipeline saves `final.h5ad` and `pipeline_report.json` in `project_dir/results/`. Visualization functions in plotting.py expect specific data structures (coords dicts, numpy arrays).
   - What's unclear: How to efficiently extract UMAP coordinates and expression data from the h5ad file for Plotly without loading the entire AnnData into memory (8GB constraint).
   - Recommendation: Build a data extraction layer that lazily loads only the needed `.obsm['X_umap']`, `.obs['cell_type']`, and gene expression vectors from the h5ad file using AnnData's backed mode or selective column loading.

2. **White-label customization scope**
   - What we know: FEATURES.md mentions "White-label deliverable customization" as a differentiator. REQ-606 defines a design system with primary color #0071e3.
   - What's unclear: Is white-labeling in v1 scope? If so, how deep (logo only? color scheme? custom fonts?).
   - Recommendation: Build the PDF renderer with color/logo constants in a config dataclass. This makes future white-labeling trivial without overengineering now. Default to BioOrchestrator branding.

3. **AI narrative generation for evidence dimension sections**
   - What we know: ReasoningEngine produces ReasoningResult with claims and summaries. Each claim has sources and confidence.
   - What's unclear: Whether the existing SYNTHESIS mode output is structured enough to split into per-dimension narratives, or if a new "dossier narrative" prompt is needed.
   - Recommendation: Filter ReasoningResult claims by source to group them into relevant dimensions. If a claim cites "OpenTargets" evidence, it belongs in the Genetic Evidence or Druggability section. This avoids a new LLM call and reuses existing reasoning output.

## Sources

### Primary (HIGH confidence)
- [fpdf2 official documentation](https://py-pdf.github.io/fpdf2/) - Tables, Images, HTML, Shapes, Tutorial sections verified
- [fpdf2 PyPI](https://pypi.org/project/fpdf2/) - Version 2.8.7 confirmed latest
- [Plotly static image export docs](https://plotly.com/python/static-image-export/) - write_image/to_image API verified
- [Plotly interactive HTML export docs](https://plotly.com/python/interactive-html-export/) - to_html API with include_plotlyjs parameter verified
- [plotly/plotly.py#5241](https://github.com/plotly/plotly.py/issues/5241) - Kaleido v1 / Plotly 5.x incompatibility confirmed

### Secondary (MEDIUM confidence)
- [Kaleido GitHub](https://github.com/plotly/Kaleido) - v1 vs v0 API differences, Chrome dependency
- [fpdf2 Charts & Graphs](https://py-pdf.github.io/fpdf2/Maths.html) - Plotly-to-PDF embedding via kaleido/BytesIO verified
- [fpdf2 issue #881](https://github.com/py-pdf/fpdf2/issues/881) - BytesIO closure behavior documented
- Existing codebase (`bioorchestrator_real/utils/plotting.py`) - UMAP, volcano, heatmap, dotplot patterns confirmed in source

### Tertiary (LOW confidence)
- Kaleido v1 performance regression claims (50x slower) - from GitHub issue #400, community reports, not independently verified
- AnnData backed mode memory usage - training data knowledge, not verified against current anndata 0.11.4

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - fpdf2, Plotly 5, kaleido 0.2.1, Jinja2 all verified via official docs and PyPI
- Architecture: MEDIUM-HIGH - Dual-renderer pattern is well-established; specific data model design is project-specific
- Pitfalls: HIGH - Kaleido/Plotly 5 incompatibility confirmed via GitHub issue; fpdf2 SVG limitation confirmed via official docs; BytesIO closure documented
- Visualization patterns: HIGH - Existing codebase already has production Plotly visualization functions

**Research date:** 2026-05-12
**Valid until:** 2026-06-12 (stable libraries, no breaking changes expected in 30 days)
