"""Design system CSS injection and HTML helpers for BioOrchestrator v2.

Adapted from bioorchestrator_real/app.py reference CSS (lines 44-360).
Provides consulting-grade aesthetics with Apple-inspired design tokens.

Usage:
    from src.pages.components.styles import inject_design_system
    inject_design_system()  # Call once in app.py after st.set_page_config()
"""

import streamlit as st


# ── Design System CSS ─────────────────────────────────────────────────

DESIGN_SYSTEM_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --blue: #0071e3;
    --dark: #1d1d1f;
    --text2: #6e6e73;
    --bg: #ffffff;
    --bg2: #f5f5f7;
    --bg3: #e8e8ed;
    --green: #1a7a35;
    --orange: #c96800;
    --red: #c0392b;
    --purple: #7a28c6;
    --teal: #0e7c86;
    /* Spacing (8pt grid) */
    --space-xs: 4px;
    --space-sm: 8px;
    --space-md: 16px;
    --space-lg: 24px;
    --space-xl: 32px;
}

.block-container { max-width: 1100px; padding-top: 1rem; }
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Inter', system-ui, sans-serif;
    color: var(--dark);
    line-height: 1.7;
}

/* ── Dark Sidebar ───────────────────────────── */
section[data-testid="stSidebar"] {
    background: var(--dark) !important;
}
section[data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }
section[data-testid="stSidebar"] * {
    color: rgba(255,255,255,0.7) !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: white !important;
}
/* Compact sidebar spacing */
section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
    gap: 0 !important;
}
section[data-testid="stSidebar"] .stElementContainer {
    margin: 0 !important;
    padding: 0 !important;
}
section[data-testid="stSidebar"] button {
    background: transparent !important;
    border: none !important;
    color: rgba(255,255,255,0.7) !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
    margin-bottom: 2px !important;
    font-size: 0.82rem !important;
    font-weight: 400 !important;
    transition: all 0.15s ease !important;
    width: 100% !important;
}
section[data-testid="stSidebar"] button,
section[data-testid="stSidebar"] button > div,
section[data-testid="stSidebar"] button p {
    text-align: left !important;
    justify-content: flex-start !important;
}
section[data-testid="stSidebar"] button:hover {
    background: rgba(255,255,255,0.1) !important;
    color: white !important;
}
section[data-testid="stSidebar"] button:focus {
    box-shadow: none !important;
}
section[data-testid="stSidebar"] p.section-label {
    color: rgba(255,255,255,0.35) !important;
    border-bottom: none !important;
    font-size: 0.68rem !important;
    margin: 16px 0 6px 12px !important;
    padding-bottom: 0 !important;
}

/* ── Metric Cards ───────────────────────────── */
.metrics-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: var(--space-md);
    margin: var(--space-lg) 0;
}
.metric-card {
    background: var(--bg);
    border: 1px solid var(--bg3);
    border-radius: 12px;
    padding: 20px var(--space-md);
    text-align: center;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}
.metric-val {
    font-family: 'IBM Plex Mono', 'SF Mono', monospace;
    font-size: 1.75rem;
    font-weight: 600;
    color: var(--blue);
    line-height: 1.15;
}
.metric-label {
    font-size: 0.72rem;
    color: var(--text2);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 6px;
    line-height: 1.3;
}

/* ── Panels ─────────────────────────────────── */
.insight-panel {
    background: rgba(0,113,227,0.04);
    border-left: 4px solid var(--blue);
    border-radius: 0 12px 12px 0;
    padding: var(--space-md) 20px;
    margin: var(--space-md) 0;
    font-size: 0.92rem;
    color: var(--dark);
    line-height: 1.7;
}
.insight-panel strong { color: var(--blue); }
.alert-panel {
    background: rgba(192,57,43,0.04);
    border-left: 4px solid var(--red);
    border-radius: 0 12px 12px 0;
    padding: var(--space-md) 20px;
    margin: var(--space-md) 0;
    font-size: 0.92rem;
    line-height: 1.7;
}
.alert-panel strong { color: var(--red); }
.warning-panel {
    background: rgba(201,104,0,0.04);
    border-left: 4px solid var(--orange);
    border-radius: 0 12px 12px 0;
    padding: var(--space-md) 20px;
    margin: var(--space-md) 0;
    font-size: 0.92rem;
    line-height: 1.7;
}
.warning-panel strong { color: var(--orange); }

/* ── Status Badges ──────────────────────────── */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
}
.badge-go { background: var(--green); color: white; }
.badge-conditional { background: var(--orange); color: white; }
.badge-nogo { background: var(--red); color: white; }

/* ── Section Labels ─────────────────────────── */
.section-label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text2);
    margin: var(--space-xl) 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--bg3);
}

/* ── Dataframe Styling ──────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--bg3);
    border-radius: 12px;
    overflow: hidden;
}

/* ── Button Enhancements ────────────────────── */
.stMainBlockContainer button[kind="primary"] {
    border-radius: 8px !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em !important;
    transition: all 0.15s ease !important;
}
.stMainBlockContainer button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(0,113,227,0.25) !important;
}

/* ── Expander Styling ───────────────────────── */
details[data-testid="stExpander"] {
    border: 1px solid var(--bg3) !important;
    border-radius: 12px !important;
}
details[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    color: var(--dark) !important;
}

/* ── Micro-Interactions ─────────────────────── */
.metric-card, .insight-panel, .alert-panel, .warning-panel { transition: all 0.15s ease; }

/* ── Print Styles ───────────────────────────── */
@media print {
    section[data-testid="stSidebar"] { display: none !important; }
    .block-container { max-width: 100% !important; padding: 0 !important; }
    button { display: none !important; }
}

/* ── Styled Table ───────────────────────────── */
.styled-table {
    width: 100%;
    border-collapse: collapse;
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif;
    font-size: 0.85rem;
}
.styled-table thead th {
    background: var(--bg2);
    color: var(--text2);
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 10px 14px;
    text-align: left;
}
.styled-table tbody td {
    padding: 10px 14px;
    border-bottom: 1px solid var(--bg2);
    color: var(--text2);
}
.styled-table tbody td strong { color: var(--dark); }
.styled-table tbody tr:hover { background: var(--bg2); }
.styled-table-wrap {
    border: 1px solid var(--bg3);
    border-radius: 12px;
    overflow: hidden;
    margin: 16px 0;
}
</style>"""


def inject_design_system() -> None:
    """Inject the design system CSS into the page.

    Call once in app.py immediately after st.set_page_config().
    Applies globally to all pages via st.markdown with unsafe_allow_html.
    """
    st.markdown(DESIGN_SYSTEM_CSS, unsafe_allow_html=True)


def metric_card(label: str, value: str) -> str:
    """Return HTML for a styled metric card div.

    Args:
        label: Short uppercase label (e.g. "TOTAL GENES").
        value: Display value (e.g. "1,234" or "87%").

    Returns:
        HTML string for a metric card. Use with st.markdown(html, unsafe_allow_html=True).
    """
    return (
        f'<div class="metric-card">'
        f'<div class="metric-val">{value}</div>'
        f'<div class="metric-label">{label}</div>'
        f'</div>'
    )


def verdict_badge(level: str) -> str:
    """Return HTML span with appropriate badge class based on verdict level.

    Args:
        level: One of "GO", "CONDITIONAL", or "NO-GO".

    Returns:
        HTML span with the correct badge class.
    """
    level_upper = level.upper().strip()
    class_map = {
        "GO": "badge-go",
        "CONDITIONAL": "badge-conditional",
        "NO-GO": "badge-nogo",
    }
    badge_class = class_map.get(level_upper, "badge")
    return f'<span class="badge {badge_class}">{level_upper}</span>'


def insight_panel(text: str) -> str:
    """Return HTML for a blue insight panel with left border.

    Args:
        text: Panel content (may include HTML).

    Returns:
        HTML string for the panel.
    """
    return f'<div class="insight-panel">{text}</div>'


def alert_panel(text: str) -> str:
    """Return HTML for a red alert panel with left border.

    Args:
        text: Panel content (may include HTML).

    Returns:
        HTML string for the panel.
    """
    return f'<div class="alert-panel">{text}</div>'


def warning_panel(text: str) -> str:
    """Return HTML for an orange warning panel with left border.

    Args:
        text: Panel content (may include HTML).

    Returns:
        HTML string for the panel.
    """
    return f'<div class="warning-panel">{text}</div>'
