"""BioOrchestrator v2 — Home / Landing Page.

First page shown after login. Orients new users, showcases capabilities,
and provides quick-start navigation into the platform.
"""

import streamlit as st


# ── Hero Section ──────────────────────────────────────────────────────

st.markdown("""
<div class="hero-section">
  <div class="hero-eyebrow">Pharmaceutical R&amp;D Intelligence</div>
  <div class="hero-title">BioOrchestrator v2</div>
  <div class="hero-subtitle">
    AI-powered drug target identification and triage platform — from raw omics data
    to a GO / NO-GO verdict with a fully auditable evidence trail.
  </div>
  <div class="hero-pills">
    <span class="stat-pill">6 Evidence Sources</span>
    <span class="stat-pill">5 Reasoning Modes</span>
    <span class="stat-pill">7-Dimension Scoring</span>
    <span class="stat-pill gold">21 CFR Part 11 Ready</span>
    <span class="stat-pill gold">GxP Compliant</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Platform Capabilities ─────────────────────────────────────────────

st.markdown('<p class="section-label">Platform Capabilities</p>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3, gap="medium")

with col1:
    st.markdown("""
    <div class="feature-card">
      <div class="feature-icon">🔬</div>
      <div class="feature-title">Omics Analysis</div>
      <div class="feature-desc">
        End-to-end single-cell RNA-seq pipeline — QC filtering, normalization,
        clustering, cell-type annotation, and differential expression analysis.
      </div>
      <div class="feature-tag">→ Omics Analysis</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="feature-card" style="margin-top:16px;">
      <div class="feature-icon">🛡️</div>
      <div class="feature-title">Audit Trail</div>
      <div class="feature-desc">
        Every action — gate approvals, reasoning runs, scoring decisions — recorded
        in a SHA-256 hash chain with electronic signatures for 21 CFR Part 11 compliance.
      </div>
      <div class="feature-tag">→ Audit Trail</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
      <div class="feature-icon">🌐</div>
      <div class="feature-title">Evidence Explorer</div>
      <div class="feature-desc">
        Live aggregation from six databases: OpenTargets, DGIdb, PubMed,
        UniProt, ChEMBL, and ClinicalTrials.gov — with graceful degradation
        and cache fallback.
      </div>
      <div class="feature-tag">→ Evidence Explorer</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="feature-card" style="margin-top:16px;">
      <div class="feature-icon">🎯</div>
      <div class="feature-title">Showcase Scenarios</div>
      <div class="feature-desc">
        Six pre-loaded pharma targets with real-world relevance:
        EGFR, ESR1, PIK3CA, GLP1R, PARP1, and CD274 — ready to demo
        without any data upload.
      </div>
      <div class="feature-tag">→ Projects</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
      <div class="feature-icon">🧠</div>
      <div class="feature-title">AI Insights</div>
      <div class="feature-desc">
        Five parallel reasoning modes (Hypothesis, Synthesis, Contradiction,
        Gap, Confidence) powered by a multi-provider LLM with an agentic
        tool-calling loop up to 10 rounds deep.
      </div>
      <div class="feature-tag">→ AI Insights</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="feature-card" style="margin-top:16px;">
      <div class="feature-icon">📊</div>
      <div class="feature-title">Scorecard &amp; Verdict</div>
      <div class="feature-desc">
        Seven-dimension scoring framework — genetic evidence, druggability,
        safety, expression biology, competitive landscape, clinical translation,
        and literature consensus — producing a GO / CONDITIONAL / NO-GO verdict.
      </div>
      <div class="feature-tag">→ Scorecard</div>
    </div>
    """, unsafe_allow_html=True)


# ── Platform Metrics ──────────────────────────────────────────────────

st.markdown('<p class="section-label">Platform at a Glance</p>', unsafe_allow_html=True)

m1, m2, m3, m4, m5 = st.columns(5)

with m1:
    st.markdown("""
    <div class="metric-card">
      <div class="metric-val">6</div>
      <div class="metric-label">Evidence Sources</div>
    </div>""", unsafe_allow_html=True)

with m2:
    st.markdown("""
    <div class="metric-card">
      <div class="metric-val">5</div>
      <div class="metric-label">Reasoning Modes</div>
    </div>""", unsafe_allow_html=True)

with m3:
    st.markdown("""
    <div class="metric-card">
      <div class="metric-val">7</div>
      <div class="metric-label">Scoring Dimensions</div>
    </div>""", unsafe_allow_html=True)

with m4:
    st.markdown("""
    <div class="metric-card">
      <div class="metric-val gold">6</div>
      <div class="metric-label">Pharma Scenarios</div>
    </div>""", unsafe_allow_html=True)

with m5:
    st.markdown("""
    <div class="metric-card">
      <div class="metric-val green">✓</div>
      <div class="metric-label">21 CFR Part 11</div>
    </div>""", unsafe_allow_html=True)


# ── How It Works ──────────────────────────────────────────────────────

st.markdown('<p class="section-label">How It Works</p>', unsafe_allow_html=True)

st.markdown("""
<div class="workflow-container">
  <div class="workflow-step">
    <div class="step-badge">1</div>
    <div class="step-title">Create Project</div>
    <div class="step-desc">Choose Exploration or GxP Compliance mode</div>
  </div>
  <div class="workflow-step">
    <div class="step-badge">2</div>
    <div class="step-title">Omics Pipeline</div>
    <div class="step-desc">Upload scRNA-seq data or use a showcase scenario</div>
  </div>
  <div class="workflow-step">
    <div class="step-badge">3</div>
    <div class="step-title">Gather Evidence</div>
    <div class="step-desc">6 databases queried in parallel for your target gene</div>
  </div>
  <div class="workflow-step">
    <div class="step-badge">4</div>
    <div class="step-title">AI Reasoning</div>
    <div class="step-desc">5 LLM reasoning modes synthesize all evidence</div>
  </div>
  <div class="workflow-step">
    <div class="step-badge">5</div>
    <div class="step-title">GO / NO-GO</div>
    <div class="step-desc">7-dimension scorecard + audit-ready dossier export</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── CTA ───────────────────────────────────────────────────────────────

st.markdown("""
<div class="cta-section">
  <div class="cta-title">Ready to evaluate a target?</div>
  <div class="cta-subtitle">
    Start a new project from scratch, or load a pre-built pharma scenario for an
    instant demo.
  </div>
</div>
""", unsafe_allow_html=True)

cta1, cta2, cta3 = st.columns([1, 1, 2])
with cta1:
    if st.button("New Project", type="primary", use_container_width=True):
        st.switch_page("pages/projects.py")
with cta2:
    if st.button("Load Showcase", type="secondary", use_container_width=True):
        st.switch_page("pages/projects.py")
