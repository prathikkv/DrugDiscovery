"""TargetSight — Home / Landing Page."""

import streamlit as st

# ── Page-scoped CSS ───────────────────────────────────────────────────

st.markdown("""<style>

/* ── HERO ── */
.home-hero {
  background: linear-gradient(135deg, #070f1c 0%, #0d1b2a 45%, #102040 75%, #070f1c 100%);
  border-radius: 20px;
  padding: 72px 60px 64px;
  position: relative;
  overflow: hidden;
  margin-bottom: 52px;
  border: 1px solid rgba(255,255,255,0.05);
}
.h-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
  animation: hpulse 10s ease-in-out infinite;
}
.h-orb1 { width:420px;height:420px;background:#1a6fe0;opacity:.10;top:-120px;right:-60px; }
.h-orb2 { width:320px;height:320px;background:#38bdf8;opacity:.07;bottom:-90px;left:40px;animation-duration:13s;animation-direction:reverse; }
.h-orb3 { width:220px;height:220px;background:#f59e0b;opacity:.05;top:30px;left:42%;animation-duration:8s;animation-delay:2s; }
@keyframes hpulse { 0%,100%{transform:scale(1);}50%{transform:scale(1.14);} }

.h-eyebrow {
  font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.22em;
  color:#38bdf8;margin-bottom:18px;position:relative;z-index:1;
}
.h-title {
  font-size:3.8rem;font-weight:800;color:#fff;letter-spacing:-.04em;
  line-height:1.04;margin-bottom:20px;position:relative;z-index:1;
}
.h-title-accent { color:#38bdf8; }
.h-sub {
  font-size:1.05rem;color:rgba(255,255,255,.65);line-height:1.72;
  max-width:580px;margin-bottom:30px;position:relative;z-index:1;
}
.h-pills {
  display:flex;flex-wrap:wrap;gap:10px;margin-bottom:0;position:relative;z-index:1;
}
.h-pill {
  background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.13);
  color:rgba(255,255,255,.8);padding:6px 15px;border-radius:100px;
  font-size:.77rem;font-weight:500;
}
.h-pill.gp {
  background:rgba(245,158,11,.12);border-color:rgba(245,158,11,.3);color:#fbbf24;
}

/* ── THE CHALLENGE ── */
.challenge-intro {
  font-size:1rem;color:#475569;line-height:1.7;
  max-width:680px;margin:0 auto 36px;text-align:center;
}
.prob-card {
  background:#fff;border:1px solid #dde4ee;border-radius:14px;
  padding:28px 20px;text-align:center;height:100%;
  transition:transform .18s,box-shadow .18s;
}
.prob-card:hover{transform:translateY(-3px);box-shadow:0 12px 36px rgba(13,27,42,.1);}
.prob-stat {
  font-family:'IBM Plex Mono',monospace;font-size:2.5rem;font-weight:700;
  color:#1a6fe0;line-height:1;margin-bottom:10px;
}
.prob-stat.r{color:#dc2626;}.prob-stat.g{color:#f59e0b;}
.prob-lbl {
  font-size:.78rem;font-weight:700;color:#0d1b2a;text-transform:uppercase;
  letter-spacing:.07em;margin-bottom:6px;
}
.prob-desc{font-size:.8rem;color:#64748b;line-height:1.58;}
.challenge-close {
  text-align:center;margin-top:32px;padding:18px 24px;
  background:linear-gradient(90deg,#f0f7ff,#eaf5fe);border-radius:10px;
  border-left:4px solid #1a6fe0;font-size:1rem;font-weight:600;color:#0d1b2a;
}

/* ── OUR APPROACH ── */
.approach-wrap {
  background:#f8fafc;border-radius:16px;padding:44px 40px;
  border:1px solid #dde4ee;
}
.approach-text p {
  font-size:.94rem;color:#334155;line-height:1.78;margin-bottom:16px;
}
.approach-text p:last-child{margin-bottom:0;}
.approach-callout {
  background:linear-gradient(160deg,#0d1b2a,#112240);
  border-radius:14px;padding:32px 24px;text-align:center;
  display:flex;flex-direction:column;justify-content:center;align-items:center;
  min-height:200px;height:100%;
}
.ac-num {
  font-family:'IBM Plex Mono',monospace;font-size:3rem;font-weight:700;
  color:#38bdf8;line-height:1;margin-bottom:6px;
}
.ac-lbl {
  font-size:.78rem;font-weight:600;color:rgba(255,255,255,.7);
  text-transform:uppercase;letter-spacing:.1em;margin-bottom:14px;
}
.ac-vs{font-size:.78rem;color:rgba(255,255,255,.35);}
.ac-vs strong{color:rgba(255,255,255,.6);}

/* ── FEATURE CARDS ── */
.fc {
  background:#fff;border:1px solid #dde4ee;border-radius:14px;
  padding:22px 20px;height:100%;position:relative;overflow:hidden;
  transition:transform .18s,box-shadow .18s,border-color .18s;
}
.fc::before{content:'';position:absolute;top:0;left:0;right:0;height:4px;border-radius:14px 14px 0 0;}
.fc.b::before{background:#1a6fe0;}
.fc.t::before{background:#0891b2;}
.fc.gl::before{background:#f59e0b;}
.fc.p::before{background:#7c3aed;}
.fc.gr::before{background:#16a34a;}
.fc:hover{transform:translateY(-4px);box-shadow:0 14px 44px rgba(13,27,42,.12);border-color:#1a6fe0;}
.fi {
  width:42px;height:42px;border-radius:10px;display:flex;
  align-items:center;justify-content:center;font-size:1.3rem;margin-bottom:12px;
}
.fi.b{background:#eff6ff;}.fi.t{background:#ecfeff;}.fi.gl{background:#fffbeb;}
.fi.p{background:#f5f3ff;}.fi.gr{background:#f0fdf4;}
.fc-title{font-size:.94rem;font-weight:700;color:#0d1b2a;margin-bottom:7px;}
.fc-desc{font-size:.8rem;color:#64748b;line-height:1.62;margin-bottom:10px;}
.fc-tag{font-size:.73rem;font-weight:600;color:#1a6fe0;}

/* ── EVIDENCE SOURCES ── */
.src-card {
  background:#fff;border:1px solid #dde4ee;border-radius:12px;
  padding:18px 16px;transition:transform .18s,box-shadow .18s;height:100%;
}
.src-card:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(13,27,42,.09);}
.src-name{font-size:.88rem;font-weight:700;color:#0d1b2a;margin-bottom:5px;}
.src-badge {
  display:inline-block;font-size:.65rem;font-weight:600;text-transform:uppercase;
  letter-spacing:.06em;padding:3px 8px;border-radius:4px;margin-bottom:9px;
  background:#eff6ff;color:#1a6fe0;
}
.src-desc{font-size:.78rem;color:#64748b;line-height:1.56;}

/* ── PIPELINE ── */
.pipeline-row {
  display:flex;align-items:flex-start;gap:0;margin:20px 0 4px;
}
.pipe-step {
  flex:1;text-align:center;padding:0 8px;position:relative;
}
.pipe-step:not(:last-child)::after {
  content:'→';position:absolute;right:-8px;top:15px;
  color:#1a6fe0;font-size:1rem;font-weight:700;
}
.pipe-num {
  width:38px;height:38px;border-radius:50%;background:#1a6fe0;
  color:#fff;font-size:.82rem;font-weight:700;
  display:flex;align-items:center;justify-content:center;margin:0 auto 9px;
}
.pipe-title{font-size:.82rem;font-weight:700;color:#0d1b2a;margin-bottom:4px;}
.pipe-desc{font-size:.74rem;color:#64748b;line-height:1.5;}

/* ── METRICS ── */
.big-m {
  background:#fff;border:1px solid #dde4ee;border-radius:14px;
  padding:24px 14px;text-align:center;
}
.bm-val {
  font-family:'IBM Plex Mono',monospace;font-size:2.3rem;font-weight:700;
  color:#1a6fe0;line-height:1;margin-bottom:8px;
}
.bm-val.gld{color:#f59e0b;}.bm-val.grn{color:#16a34a;}.bm-val.sky{color:#0891b2;}
.bm-lbl{font-size:.72rem;font-weight:500;color:#64748b;text-transform:uppercase;letter-spacing:.07em;}

/* ── CTA DARK ── */
.cta-dark {
  background:linear-gradient(135deg,#070f1c,#0d1b2a);
  border-radius:20px;padding:56px 48px;text-align:center;margin-top:8px;
  border:1px solid rgba(255,255,255,.05);position:relative;overflow:hidden;
}
.cta-dark::before {
  content:'';position:absolute;width:500px;height:500px;border-radius:50%;
  background:#1a6fe0;opacity:.05;filter:blur(80px);top:-200px;right:-80px;
  pointer-events:none;
}
.cta-title {
  font-size:2.1rem;font-weight:800;color:#fff;
  letter-spacing:-.03em;margin-bottom:12px;position:relative;z-index:1;
}
.cta-sub {
  font-size:.95rem;color:rgba(255,255,255,.58);max-width:500px;
  margin:0 auto 32px;line-height:1.68;position:relative;z-index:1;
}

/* ── SHARED ── */
.section-gap{margin-top:52px;}
.section-sub{font-size:.9rem;color:#64748b;margin-bottom:24px;line-height:1.65;max-width:680px;}
</style>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# 1. HERO
# ══════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="home-hero">
  <div class="h-orb h-orb1"></div>
  <div class="h-orb h-orb2"></div>
  <div class="h-orb h-orb3"></div>
  <div class="h-eyebrow">Pharmaceutical R&amp;D Intelligence Platform</div>
  <div class="h-title">
    From Gene to<br><span class="h-title-accent">GO&thinsp;/&thinsp;NO-GO.</span>
  </div>
  <div class="h-sub">
    AI-orchestrated drug target identification and triage — from raw omics data to a
    fully auditable verdict in <strong style="color:rgba(255,255,255,.85)">minutes, not months.</strong>
  </div>
  <div class="h-pills">
    <span class="h-pill">6 Evidence Sources</span>
    <span class="h-pill">5 Reasoning Modes</span>
    <span class="h-pill">7-Dimension Scoring</span>
    <span class="h-pill gp">21 CFR Part 11 Ready</span>
    <span class="h-pill gp">GxP Compliant</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# 2. THE CHALLENGE
# ══════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-label">The Challenge</p>', unsafe_allow_html=True)
st.markdown("""
<p class="challenge-intro">
  Drug target identification is one of the most expensive, slow, and failure-prone steps
  in pharmaceutical R&amp;D — yet it is where every successful therapy begins.
</p>
""", unsafe_allow_html=True)

p1, p2, p3 = st.columns(3, gap="medium")
with p1:
    st.markdown("""
    <div class="prob-card">
      <div class="prob-stat">2–5 Yrs</div>
      <div class="prob-lbl">Manual validation time</div>
      <div class="prob-desc">
        Validating a single drug target through manual literature review, database queries,
        and internal assays typically consumes 2–5 years of researcher time.
      </div>
    </div>""", unsafe_allow_html=True)
with p2:
    st.markdown("""
    <div class="prob-card">
      <div class="prob-stat r">&gt;90%</div>
      <div class="prob-lbl">Clinical trial failure rate</div>
      <div class="prob-desc">
        Over 90% of drug candidates fail in clinical trials — a large proportion due to
        insufficient target validation and unrecognised safety or efficacy signals at the
        discovery stage.
      </div>
    </div>""", unsafe_allow_html=True)
with p3:
    st.markdown("""
    <div class="prob-card">
      <div class="prob-stat g">7+</div>
      <div class="prob-lbl">Disconnected databases</div>
      <div class="prob-desc">
        Researchers manually query OpenTargets, PubMed, UniProt, ChEMBL, DGIdb,
        ClinicalTrials.gov, and more — with no unified scoring or audit trail.
      </div>
    </div>""", unsafe_allow_html=True)

st.markdown("""
<div class="challenge-close">
  TargetSight was built to collapse this process from years into minutes —
  with a fully traceable evidence chain your regulatory team will trust.
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# 3. OUR APPROACH
# ══════════════════════════════════════════════════════════════════════

st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
st.markdown('<p class="section-label">Our Approach</p>', unsafe_allow_html=True)

ap_text, ap_callout = st.columns([3, 2], gap="large")
with ap_text:
    st.markdown("""
    <div class="approach-wrap">
      <div class="approach-text">
        <p>
          TargetSight is an AI-orchestrated research platform built at the intersection
          of <strong>computational biology</strong>, <strong>large language models</strong>,
          and <strong>pharmaceutical regulatory science</strong>. It automates the most
          time-consuming parts of target triage — database aggregation, single-cell omics
          analysis, and multi-source literature synthesis — and wraps them in a
          seven-dimension scoring framework tuned to how drug discovery teams actually
          make GO/NO-GO decisions.
        </p>
        <p>
          The platform runs five parallel AI reasoning modes simultaneously:
          Hypothesis generation, Evidence synthesis, Contradiction detection,
          Knowledge-gap identification, and Confidence calibration. Each mode calls
          live databases in an agentic loop up to 10 rounds deep before converging
          on a structured conclusion.
        </p>
        <p>
          Every reasoning step, gate approval, and scoring decision is logged,
          SHA-256 hash-chained, and electronically signed — producing a GxP-ready
          audit dossier that meets <strong>21 CFR Part 11</strong> out of the box.
          No post-hoc documentation. No manual assembly. Just science, accelerated.
        </p>
      </div>
    </div>
    """, unsafe_allow_html=True)
with ap_callout:
    st.markdown("""
    <div class="approach-callout" style="min-height:280px;">
      <div class="ac-num">15 min</div>
      <div class="ac-lbl">Time to first verdict</div>
      <div class="ac-vs">versus <strong>weeks to months</strong><br>with manual workflows</div>
      <br>
      <div style="width:100%;height:1px;background:rgba(255,255,255,.08);margin:18px 0;"></div>
      <div class="ac-num" style="font-size:1.9rem;color:#f59e0b;">21 CFR</div>
      <div class="ac-lbl">Part 11 audit trail</div>
      <div class="ac-vs">hash-chained signatures on <strong>every action</strong></div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# 4. PLATFORM CAPABILITIES
# ══════════════════════════════════════════════════════════════════════

st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
st.markdown('<p class="section-label">Platform Capabilities</p>', unsafe_allow_html=True)

fc1, fc2, fc3 = st.columns(3, gap="medium")

with fc1:
    st.markdown("""
    <div class="fc b">
      <div class="fi b">🔬</div>
      <div class="fc-title">Omics Analysis</div>
      <div class="fc-desc">
        End-to-end single-cell RNA-seq pipeline — QC filtering, normalisation,
        clustering, cell-type annotation, and differential expression analysis.
        Outputs ranked candidate targets with statistical confidence.
      </div>
      <div class="fc-tag">→ Omics Analysis</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="fc gl" style="margin-top:16px;">
      <div class="fi gl">🛡️</div>
      <div class="fc-title">Audit Trail</div>
      <div class="fc-desc">
        Every gate approval, reasoning run, and scoring decision is recorded in a
        SHA-256 hash chain with electronic signatures — 21 CFR Part 11 compliant
        from day one.
      </div>
      <div class="fc-tag">→ Audit Trail</div>
    </div>
    """, unsafe_allow_html=True)

with fc2:
    st.markdown("""
    <div class="fc t">
      <div class="fi t">🌐</div>
      <div class="fc-title">Evidence Explorer</div>
      <div class="fc-desc">
        Live aggregation from six authoritative databases — OpenTargets, DGIdb,
        PubMed, UniProt, ChEMBL, and ClinicalTrials.gov — with graceful degradation
        and intelligent cache fallback.
      </div>
      <div class="fc-tag">→ Evidence Explorer</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="fc b" style="margin-top:16px;">
      <div class="fi b">🎯</div>
      <div class="fc-title">Showcase Scenarios</div>
      <div class="fc-desc">
        Six pre-loaded pharma targets — EGFR, ESR1, PIK3CA, GLP1R, PARP1, and
        CD274 — with real-world evidence, ready to explore without uploading any data.
      </div>
      <div class="fc-tag">→ Projects</div>
    </div>
    """, unsafe_allow_html=True)

with fc3:
    st.markdown("""
    <div class="fc p">
      <div class="fi p">🧠</div>
      <div class="fc-title">AI Insights</div>
      <div class="fc-desc">
        Five parallel reasoning modes — Hypothesis, Synthesis, Contradiction, Gap,
        and Confidence — powered by a multi-provider LLM with an agentic tool-calling
        loop up to 10 rounds deep.
      </div>
      <div class="fc-tag">→ AI Insights</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="fc gr" style="margin-top:16px;">
      <div class="fi gr">📊</div>
      <div class="fc-title">Scorecard &amp; Verdict</div>
      <div class="fc-desc">
        Seven-dimension scoring — genetic evidence, druggability, safety, expression
        biology, competitive landscape, clinical translation, and literature consensus
        — producing a GO / CONDITIONAL / NO-GO verdict.
      </div>
      <div class="fc-tag">→ Scorecard</div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# 5. EVIDENCE SOURCES
# ══════════════════════════════════════════════════════════════════════

st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
st.markdown('<p class="section-label">Evidence Sources</p>', unsafe_allow_html=True)
st.markdown("""
<p class="section-sub">
  TargetSight queries six authoritative databases in parallel. Results are cached locally
  so the platform remains fully functional even when external APIs are temporarily
  unavailable.
</p>
""", unsafe_allow_html=True)

src1, src2, src3 = st.columns(3, gap="medium")

SOURCES = [
    ("OpenTargets", "Target–Disease", "Genetic, genomic, and clinical evidence linking genes to diseases. The gold-standard resource for target prioritisation across 60+ disease areas."),
    ("DGIdb", "Drug–Gene Interactions", "Curated drug–gene interaction data: known inhibitors, activators, and therapeutic annotations from FDA-approved drugs and late-stage candidates."),
    ("PubMed / NCBI", "Literature", "Full-text search across 35M+ biomedical abstracts. Surfaces disease associations, mechanism papers, and safety signals directly from the primary literature."),
    ("UniProt", "Protein Biology", "Protein function, structure, subcellular localisation, expression patterns, and pathway membership for every candidate target."),
    ("ChEMBL", "Bioactivity Data", "Small-molecule binding assays, IC₅₀/EC₅₀ measurements, and ADMET properties — key for early druggability assessment."),
    ("ClinicalTrials.gov", "Clinical Evidence", "Active and completed clinical trials: phase progression, safety signals, competitor pipelines, and unmet-need indicators."),
]

for i, col in enumerate([src1, src2, src3]):
    with col:
        for src in SOURCES[i * 2:(i + 1) * 2]:
            name, badge, desc = src
            st.markdown(f"""
            <div class="src-card" style="margin-bottom:14px;">
              <div class="src-name">{name}</div>
              <span class="src-badge">{badge}</span>
              <div class="src-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# 6. HOW IT WORKS
# ══════════════════════════════════════════════════════════════════════

st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
st.markdown('<p class="section-label">How It Works</p>', unsafe_allow_html=True)

st.markdown("""
<div class="pipeline-row">
  <div class="pipe-step">
    <div class="pipe-num">1</div>
    <div class="pipe-title">Create Project</div>
    <div class="pipe-desc">Choose Exploration or GxP Compliance mode</div>
  </div>
  <div class="pipe-step">
    <div class="pipe-num">2</div>
    <div class="pipe-title">Omics Pipeline</div>
    <div class="pipe-desc">Upload scRNA-seq data or load a showcase scenario</div>
  </div>
  <div class="pipe-step">
    <div class="pipe-num">3</div>
    <div class="pipe-title">Gather Evidence</div>
    <div class="pipe-desc">6 databases queried in parallel for your target gene</div>
  </div>
  <div class="pipe-step">
    <div class="pipe-num">4</div>
    <div class="pipe-title">AI Reasoning</div>
    <div class="pipe-desc">5 LLM modes synthesise all evidence simultaneously</div>
  </div>
  <div class="pipe-step">
    <div class="pipe-num">5</div>
    <div class="pipe-title">GO / NO-GO</div>
    <div class="pipe-desc">7-dimension scorecard + audit-ready dossier export</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# 7. PLATFORM AT A GLANCE
# ══════════════════════════════════════════════════════════════════════

st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
st.markdown('<p class="section-label">Platform at a Glance</p>', unsafe_allow_html=True)

m1, m2, m3, m4, m5, m6 = st.columns(6)
METRICS = [
    ("6", "", "Evidence Sources"),
    ("5", "", "Reasoning Modes"),
    ("7", "", "Scoring Dimensions"),
    ("6", "gld", "Pharma Scenarios"),
    ("✓", "grn", "21 CFR Part 11"),
    ("15 min", "sky", "Time to Verdict"),
]
for col, (val, cls, lbl) in zip([m1, m2, m3, m4, m5, m6], METRICS):
    with col:
        st.markdown(f"""
        <div class="big-m">
          <div class="bm-val {cls}">{val}</div>
          <div class="bm-lbl">{lbl}</div>
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# 8. CTA
# ══════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="cta-dark">
  <div class="cta-title">Ready to evaluate a target?</div>
  <div class="cta-sub">
    Start a new project from scratch, or load one of six pre-built pharma scenarios
    — EGFR, ESR1, PIK3CA, GLP1R, PARP1, or CD274 — for an instant demo.
  </div>
</div>
""", unsafe_allow_html=True)

cta1, cta2, cta3 = st.columns([1, 1, 2])
with cta1:
    st.page_link("src/pages/projects.py", label="New Project", icon=":material/folder_open:", use_container_width=True)
with cta2:
    st.page_link("src/pages/projects.py", label="Load Showcase", icon=":material/science:", use_container_width=True)
