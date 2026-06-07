"""Login and registration page — pharma-premium design.

Full-width dark hero with branding + EGFR scorecard preview.
Centered white card for the login/register form.
Sidebar hidden (no nav clutter before auth).

Password is NEVER stored in session state. Only user_id, email, and
role are persisted in st.session_state["user"] after successful login.
"""

import streamlit as st

from src.auth.service import AuthService

# ── Page-specific CSS ────────────────────────────────────────────────

LOGIN_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@600;700&family=Inter:wght@300;400;500;600;700;800&display=swap');

/* Hide sidebar on login page */
section[data-testid="stSidebar"] { display: none !important; }

/* Remove Streamlit container constraints */
.block-container {
    max-width: 100% !important;
    padding: 0 !important;
    margin: 0 !important;
}
.main > div { padding: 0 !important; }

/* ── Hero: full-width breakout ── */
.login-hero {
    position: relative;
    left: 50%;
    right: 50%;
    margin-left: -50vw;
    margin-right: -50vw;
    width: 100vw;
    background: linear-gradient(160deg, #0d1b2a 0%, #162032 45%, #0d1b2a 100%);
    overflow: hidden;
}
.login-hero::before {
    content: '';
    position: absolute;
    top: -80px; right: -80px;
    width: 400px; height: 400px;
    background: radial-gradient(circle, rgba(56,189,248,0.12) 0%, transparent 65%);
    pointer-events: none;
}
.login-hero::after {
    content: '';
    position: absolute;
    bottom: -60px; left: 8%;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(245,158,11,0.08) 0%, transparent 65%);
    pointer-events: none;
}
.login-hero-inner {
    display: flex;
    gap: 48px;
    max-width: 1100px;
    margin: 0 auto;
    padding: 64px 48px 56px;
    align-items: flex-start;
    position: relative;
    z-index: 1;
}

/* ── Left: Brand panel ── */
.login-brand { flex: 1.15; }
.login-eyebrow {
    font-size: 0.7rem;
    color: #38bdf8;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    font-weight: 700;
    margin-bottom: 16px;
}
.login-title {
    font-size: 3rem;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.05;
    margin-bottom: 6px;
    font-family: 'Inter', sans-serif;
}
.login-version {
    font-size: 0.82rem;
    color: rgba(255,255,255,0.38);
    margin-bottom: 20px;
    letter-spacing: 0.04em;
}
.login-tagline {
    font-size: 1.05rem;
    color: rgba(255,255,255,0.72);
    line-height: 1.7;
    margin-bottom: 28px;
    max-width: 430px;
}
.login-tagline strong { color: #38bdf8; font-weight: 700; }
.login-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 22px;
}
.lpill {
    background: rgba(255,255,255,0.09);
    color: rgba(255,255,255,0.80);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 20px;
    padding: 5px 15px;
    font-size: 0.77rem;
    font-weight: 500;
    letter-spacing: 0.01em;
}
.lpill.gold {
    background: rgba(245,158,11,0.18);
    color: #fcd34d;
    border-color: rgba(245,158,11,0.35);
}
.lpill.green {
    background: rgba(22,163,74,0.18);
    color: #86efac;
    border-color: rgba(22,163,74,0.35);
}
.login-compliance {
    font-size: 0.72rem;
    color: rgba(255,255,255,0.32);
    margin-top: 4px;
    letter-spacing: 0.02em;
}

/* ── Right: EGFR preview card ── */
.login-preview {
    flex: 0.85;
    min-width: 270px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.11);
    border-radius: 16px;
    padding: 28px 26px;
}
.lp-eyebrow {
    font-size: 0.62rem;
    color: #38bdf8;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    font-weight: 700;
    margin-bottom: 16px;
}
.lp-verdict {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 14px;
}
.lp-go {
    background: #16a34a;
    color: white;
    font-size: 0.78rem;
    font-weight: 800;
    padding: 4px 16px;
    border-radius: 20px;
    letter-spacing: 0.08em;
}
.lp-score {
    font-size: 1.65rem;
    font-weight: 700;
    color: white;
    font-family: 'IBM Plex Mono', monospace;
}
.lp-score-sub {
    font-size: 0.72rem;
    color: rgba(255,255,255,0.4);
    font-family: 'IBM Plex Mono', monospace;
}
.lp-bar {
    background: rgba(255,255,255,0.1);
    border-radius: 4px;
    height: 7px;
    margin-bottom: 22px;
    overflow: hidden;
}
.lp-fill {
    background: linear-gradient(90deg, #1a6fe0, #38bdf8);
    border-radius: 4px;
    height: 7px;
}
.lp-dims {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 7px 16px;
    margin-bottom: 20px;
}
.lp-dim-name { font-size: 0.76rem; color: rgba(255,255,255,0.60); }
.lp-dim-val {
    font-size: 0.76rem;
    color: #38bdf8;
    font-weight: 700;
    font-family: 'IBM Plex Mono', monospace;
    text-align: right;
}
.lp-divider {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.08);
    margin: 16px 0;
}
.lp-sources { display: flex; flex-wrap: wrap; gap: 6px; }
.lp-src {
    background: rgba(26,111,224,0.18);
    color: #93c5fd;
    border: 1px solid rgba(26,111,224,0.28);
    border-radius: 6px;
    padding: 3px 9px;
    font-size: 0.67rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}

/* ── Form section ── */
.login-form-header {
    text-align: center;
    margin-bottom: 4px;
    padding: 0 8px;
}
.login-form-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #0d1b2a;
    margin-bottom: 5px;
}
.login-form-sub { font-size: 0.83rem; color: #64748b; }

/* ── Footer ── */
.login-footer {
    text-align: center;
    color: #94a3b8;
    font-size: 0.7rem;
    padding: 24px 0 20px;
    line-height: 1.8;
}
.login-footer strong { color: #64748b; }

/* Responsive: stack vertically on small screens */
@media (max-width: 768px) {
    .login-hero-inner { flex-direction: column; padding: 40px 24px 36px; gap: 28px; }
    .login-preview { min-width: unset; }
    .login-title { font-size: 2.2rem; }
}
</style>"""

# ── Hero HTML ─────────────────────────────────────────────────────────

HERO_HTML = """
<div class="login-hero">
  <div class="login-hero-inner">

    <!-- LEFT: Branding -->
    <div class="login-brand">
      <div class="login-eyebrow">Pharmaceutical R&amp;D Intelligence</div>
      <div class="login-title">BioOrchestrator</div>
      <div class="login-version">v2 · Enterprise Platform</div>
      <div class="login-tagline">
        From gene symbol to GO/NO-GO verdict in <strong>15 minutes</strong>.<br>
        Replaces 2–4 weeks of manual target triage across 6 databases.
      </div>
      <div class="login-pills">
        <span class="lpill">6 Evidence Sources</span>
        <span class="lpill">5 AI Reasoning Modes</span>
        <span class="lpill">7-Dimension Scoring</span>
        <span class="lpill gold">★ 21 CFR Part 11</span>
        <span class="lpill green">✓ GxP Compliant</span>
      </div>
      <div class="login-compliance">
        SHA-256 Hash Chain · Electronic Signatures · Tamper-Evident Audit Trail
      </div>
    </div>

    <!-- RIGHT: EGFR Scorecard Preview -->
    <div class="login-preview">
      <div class="lp-eyebrow">Live Analysis · EGFR / Non-Small Cell Lung Cancer</div>
      <div class="lp-verdict">
        <span class="lp-go">GO</span>
        <span class="lp-score">82.5<span class="lp-score-sub"> / 100</span></span>
      </div>
      <div class="lp-bar"><div class="lp-fill" style="width:82.5%"></div></div>
      <div class="lp-dims">
        <span class="lp-dim-name">Genetic Evidence</span><span class="lp-dim-val">88</span>
        <span class="lp-dim-name">Druggability</span><span class="lp-dim-val">91</span>
        <span class="lp-dim-name">Safety &amp; Selectivity</span><span class="lp-dim-val">74</span>
        <span class="lp-dim-name">Clinical Translation</span><span class="lp-dim-val">79</span>
        <span class="lp-dim-name">Literature Consensus</span><span class="lp-dim-val">76</span>
      </div>
      <hr class="lp-divider">
      <div class="lp-sources">
        <span class="lp-src">OpenTargets</span>
        <span class="lp-src">PubMed</span>
        <span class="lp-src">ChEMBL</span>
        <span class="lp-src">DGIdb</span>
        <span class="lp-src">UniProt</span>
        <span class="lp-src">ClinTrials</span>
      </div>
    </div>

  </div>
</div>
"""

# ── Page ─────────────────────────────────────────────────────────────

st.markdown(LOGIN_CSS, unsafe_allow_html=True)
st.markdown(HERO_HTML, unsafe_allow_html=True)

if st.session_state.pop("session_expired", False):
    st.warning("Your session expired due to inactivity. Please log in again.")

st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

# Centered form card
_, center, _ = st.columns([1, 2, 1])

auth = AuthService()

with center:
    st.markdown(
        """<div class="login-form-header">
          <div class="login-form-title">Welcome back</div>
          <div class="login-form-sub">Sign in to your BioOrchestrator account</div>
        </div>""",
        unsafe_allow_html=True,
    )

    login_tab, register_tab = st.tabs(["Sign In", "Create Account"])

    # ── Sign In ──────────────────────────────────────────────────────
    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email address", placeholder="you@company.com", key="login_email")
            password = st.text_input("Password", type="password", placeholder="••••••••", key="login_password")
            submitted = st.form_submit_button("Sign In →", use_container_width=True, type="primary")

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                result = auth.login(email, password)
                if result["success"]:
                    st.session_state["user"] = {
                        "user_id": result["user_id"],
                        "email": email,
                        "role": result["role"],
                    }
                    st.rerun()
                else:
                    st.error(result["error"])

    # ── Create Account ────────────────────────────────────────────────
    with register_tab:
        with st.form("register_form"):
            reg_email = st.text_input("Email address", placeholder="you@company.com", key="reg_email")
            reg_password = st.text_input("Password", type="password", placeholder="Min. 8 characters", key="reg_password")
            reg_confirm = st.text_input("Confirm password", type="password", placeholder="Repeat password", key="reg_confirm")
            reg_role = st.selectbox(
                "Role",
                options=["analyst", "reviewer", "admin"],
                help="analyst: full access · reviewer: read-only · admin: all permissions",
                key="reg_role",
            )
            reg_submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")

        if reg_submitted:
            if not reg_email or not reg_password:
                st.error("Please fill in all required fields.")
            elif reg_password != reg_confirm:
                st.error("Passwords do not match.")
            else:
                result = auth.register(reg_email, reg_password, reg_role)
                if result["success"]:
                    st.success("Account created! You can now sign in.")
                else:
                    st.error(result["error"])

# ── Footer ─────────────────────────────────────────────────────────────

st.markdown(
    """<div class="login-footer">
      <strong>BioOrchestrator v2</strong> · 21 CFR Part 11 Compliant ·
      SHA-256 Audit Chain · GxP Ready<br>
      For authorized pharmaceutical research use only.
    </div>""",
    unsafe_allow_html=True,
)
