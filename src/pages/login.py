"""TargetSight — Login page.

Apple-inspired light mode. Single-column centered, naturally scrollable.
Hero → Form → Product proof (dark scorecard) → Compliance → Footer.
"""

import streamlit as st

from src.auth.service import AuthService

# ── Full-page CSS ────────────────────────────────────────────────────

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&family=JetBrains+Mono:wght@500;600;700&display=swap');

/* ── PAGE FOUNDATION ── */
html { scroll-behavior: smooth; }
.stApp {
    background: #ffffff !important;
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
.main, .block-container { background: transparent !important; }
.block-container {
    max-width: 540px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding: 48px 28px 80px !important;
}
section[data-testid="stSidebar"] { display: none !important; }
footer { display: none !important; }
#MainMenu { display: none !important; }

/* ── WORDMARK ── */
.ts-nav {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 64px;
}
.ts-wordname {
    font-size: 1.2rem;
    font-weight: 800;
    color: #1d1d1f;
    letter-spacing: -0.03em;
    line-height: 1;
    font-family: 'Plus Jakarta Sans', sans-serif;
}
.ts-wordname span { color: #0d9488; }
.ts-tagline-sm {
    font-size: 0.52rem;
    color: #8a8a8e;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    font-weight: 600;
    margin-top: 5px;
    font-family: 'Plus Jakarta Sans', sans-serif;
}

/* ── HERO ── */
.ts-hero { margin-bottom: 56px; }
.ts-hero-eyebrow {
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    font-weight: 700;
    color: #0d9488;
    margin-bottom: 14px;
    font-family: 'Plus Jakarta Sans', sans-serif;
}
.ts-hero-title {
    font-size: 3.75rem;
    font-weight: 800;
    color: #1d1d1f;
    letter-spacing: -0.045em;
    line-height: 1.01;
    margin-bottom: 18px;
    font-family: 'Plus Jakarta Sans', sans-serif;
}
.ts-teal { color: #0d9488; }
.ts-hero-sub {
    font-size: 0.97rem;
    color: #6e6e73;
    line-height: 1.72;
    font-family: 'Plus Jakarta Sans', sans-serif;
}
.ts-hero-sub strong { color: #1d1d1f; font-weight: 600; }

/* ── FORM HEADER ── */
.form-hd { margin-bottom: 20px; }
.form-hd h2 {
    font-size: 1.35rem !important;
    font-weight: 700 !important;
    color: #1d1d1f !important;
    letter-spacing: -0.025em !important;
    margin-bottom: 4px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.form-hd p {
    font-size: 0.82rem;
    color: #8a8a8e;
    margin: 0;
    font-family: 'Plus Jakarta Sans', sans-serif;
}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #e8e8ed !important;
    gap: 0 !important;
    margin-bottom: 20px !important;
}
.stTabs [data-baseweb="tab"] {
    color: #8a8a8e !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
    background: transparent !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    letter-spacing: 0 !important;
}
.stTabs [aria-selected="true"] { color: #1d1d1f !important; background: transparent !important; }
.stTabs [data-baseweb="tab-highlight"] { background: #0d9488 !important; height: 2px !important; }
.stTabs [data-baseweb="tab-border"] { display: none !important; }
.stTabs [data-baseweb="tab-panel"] { padding: 0 !important; }

/* ── INPUTS ── */
.stTextInput > label, .stSelectbox > label {
    color: #6e6e73 !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.stTextInput > div > div > input {
    background: #ffffff !important;
    border: 1.5px solid #d2d2d7 !important;
    color: #1d1d1f !important;
    border-radius: 10px !important;
    padding: 12px 14px !important;
    font-size: 15px !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.stTextInput > div > div > input:focus {
    border-color: #0d9488 !important;
    box-shadow: 0 0 0 3px rgba(13,148,136,0.12) !important;
    outline: none !important;
}
.stTextInput > div > div > input::placeholder { color: #b0b0b5 !important; }
[data-baseweb="base-input"] { background: transparent !important; }

/* ── SELECTBOX ── */
.stSelectbox > div > div {
    background: #ffffff !important;
    border: 1.5px solid #d2d2d7 !important;
    color: #1d1d1f !important;
    border-radius: 10px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.stSelectbox svg { fill: #8a8a8e !important; }

/* ── BUTTON ── */
.stFormSubmitButton > button {
    background: #0d9488 !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    letter-spacing: -0.01em !important;
    border-radius: 10px !important;
    padding: 13px !important;
    box-shadow: none !important;
    transition: opacity 0.18s ease, transform 0.18s ease !important;
    margin-top: 6px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.stFormSubmitButton > button:hover { opacity: 0.86 !important; }
.stFormSubmitButton > button:active {
    opacity: 0.74 !important;
    transform: scale(0.99) !important;
}

/* Alerts */
[data-testid="stAlert"] { border-radius: 12px !important; }

/* ── PRODUCT PROOF SECTION ── */
.ts-proof { margin-top: 80px; }
.ts-proof-eyebrow {
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    color: #b0b0b5;
    font-weight: 600;
    text-align: center;
    margin-bottom: 22px;
    font-family: 'Plus Jakarta Sans', sans-serif;
}

/* Dark scorecard — terminal precision widget */
.score-card {
    background: #17181c;
    border: 1px solid rgba(255,255,255,0.07);
    border-left: 2.5px solid #14b8a6;
    border-radius: 14px;
    padding: 22px 22px 18px;
    box-shadow:
        0 2px 6px rgba(0,0,0,0.10),
        0 10px 36px rgba(0,0,0,0.15),
        0 28px 72px rgba(0,0,0,0.09);
}
.sc-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.58rem;
    color: #2dd4bf;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    font-weight: 700;
    margin-bottom: 16px;
    font-family: 'Plus Jakarta Sans', sans-serif;
}
.sc-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #16a34a;
    box-shadow: 0 0 6px rgba(22,163,74,0.8);
    animation: livepulse 2.5s ease-in-out infinite;
    flex-shrink: 0;
}
@keyframes livepulse {
    0%,100% { opacity: 0.7; }
    50%      { opacity: 1; box-shadow: 0 0 10px rgba(22,163,74,0.9); }
}
.sc-verdict { display: flex; align-items: baseline; gap: 14px; margin-bottom: 12px; }
.sc-go {
    background: #166534;
    color: #86efac;
    font-size: 0.68rem;
    font-weight: 700;
    padding: 3px 14px;
    border-radius: 4px;
    letter-spacing: 0.14em;
    border: 1px solid rgba(134,239,172,0.25);
    font-family: 'JetBrains Mono', monospace;
}
.sc-num {
    font-size: 2.4rem;
    font-weight: 700;
    color: #f8fafc;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1;
}
.sc-denom { font-size: 0.78rem; color: rgba(255,255,255,0.25); font-family: 'JetBrains Mono', monospace; }
.sc-bar-bg { background: rgba(255,255,255,0.07); border-radius: 3px; height: 5px; margin-bottom: 20px; overflow: hidden; }
.sc-bar {
    background: linear-gradient(90deg, #0d9488, #2dd4bf);
    border-radius: 3px; height: 5px;
    animation: barfill 1.8s cubic-bezier(0.4, 0, 0.2, 1);
}
@keyframes barfill { from { width: 0%; } }
.sc-grid { display: grid; grid-template-columns: 1fr auto; gap: 7px 16px; margin-bottom: 16px; }
.sc-dim { font-size: 0.72rem; color: rgba(255,255,255,0.4); font-family: 'Plus Jakarta Sans', sans-serif; }
.sc-val { font-size: 0.72rem; color: #2dd4bf; font-weight: 600; font-family: 'JetBrains Mono', monospace; text-align: right; }
.sc-hr { border: none; border-top: 1px solid rgba(255,255,255,0.06); margin: 10px 0; }
.sc-srcs { display: flex; flex-wrap: wrap; gap: 5px; }
.sc-src {
    background: rgba(20,184,166,0.08);
    color: rgba(45,212,191,0.8);
    border: 1px solid rgba(20,184,166,0.18);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.6rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    font-family: 'Plus Jakarta Sans', sans-serif;
}

/* ── COMPLIANCE ── */
.bp-compliance {
    font-size: 0.65rem;
    color: #8a8a8e;
    letter-spacing: 0.04em;
    display: flex;
    justify-content: center;
    gap: 20px;
    flex-wrap: wrap;
    padding: 28px 0 0;
    font-family: 'Plus Jakarta Sans', sans-serif;
}
.bp-compliance span { color: #34c759; }

/* ── FOOTER ── */
.login-footer {
    text-align: center;
    color: #b0b0b5;
    font-size: 0.62rem;
    padding: 20px 0 40px;
    letter-spacing: 0.04em;
    font-family: 'Plus Jakarta Sans', sans-serif;
}

/* ── RESPONSIVE ── */
@media (max-width: 600px) {
    .ts-hero-title { font-size: 2.8rem !important; }
    .block-container { padding: 36px 20px 60px !important; }
    .ts-nav { margin-bottom: 48px; }
}
</style>""", unsafe_allow_html=True)

# ── WORDMARK + HERO ───────────────────────────────────────────────────

st.markdown("""
<div class="ts-nav">
  <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" width="34" height="34">
    <polygon points="20,4 33.5,12 33.5,28 20,36 6.5,28 6.5,12"
      stroke="#0d9488" stroke-width="1.6" fill="none" stroke-linejoin="round"/>
    <polygon points="20,12.5 27.5,16.75 27.5,25.25 20,29.5 12.5,25.25 12.5,16.75"
      stroke="#0d9488" stroke-width="1.1" fill="none" opacity="0.35" stroke-linejoin="round"/>
    <circle cx="20" cy="20" r="2.4" fill="#0d9488"/>
  </svg>
  <div>
    <div class="ts-wordname">Target<span>Sight</span></div>
    <div class="ts-tagline-sm">Target Intelligence &middot; Redefined</div>
  </div>
</div>

<div class="ts-hero">
  <div class="ts-hero-eyebrow">Drug Discovery Intelligence</div>
  <div class="ts-hero-title">
    From Gene to<br>
    <span class="ts-teal">GO&thinsp;/&thinsp;NO-GO.</span>
  </div>
  <div class="ts-hero-sub">
    AI-powered target intelligence that compresses
    <strong>weeks of manual research into 15&nbsp;minutes</strong> &mdash;
    with a fully auditable evidence trail your regulatory team will trust.
  </div>
</div>
""", unsafe_allow_html=True)

# ── FORM ─────────────────────────────────────────────────────────────

if st.session_state.pop("session_expired", False):
    st.warning("Your session expired due to inactivity.")

st.markdown("""
<div class="form-hd">
  <h2>Sign in to TargetSight</h2>
  <p>Authorized pharmaceutical research use only</p>
</div>
""", unsafe_allow_html=True)

login_tab, register_tab = st.tabs(["Sign In", "Create Account"])

auth = AuthService()

# ── Sign In ──────────────────────────────────────────────────────────
with login_tab:
    with st.form("login_form"):
        email = st.text_input(
            "Email", placeholder="you@pharma.com", key="login_email"
        )
        password = st.text_input(
            "Password", type="password", placeholder="••••••••", key="login_password"
        )
        submitted = st.form_submit_button(
            "Sign In  →", use_container_width=True, type="primary"
        )

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

# ── Create Account ────────────────────────────────────────────────────
with register_tab:
    with st.form("register_form"):
        reg_email = st.text_input(
            "Email", placeholder="you@pharma.com", key="reg_email"
        )
        reg_password = st.text_input(
            "Password", type="password", placeholder="Min. 8 characters", key="reg_password"
        )
        reg_confirm = st.text_input(
            "Confirm password", type="password", placeholder="Repeat password", key="reg_confirm"
        )
        reg_role = st.selectbox(
            "Role",
            options=["analyst", "reviewer", "admin"],
            help="analyst: full access · reviewer: read-only · admin: all permissions",
            key="reg_role",
        )
        reg_submitted = st.form_submit_button(
            "Create Account", use_container_width=True, type="primary"
        )

    if reg_submitted:
        if not reg_email or not reg_password:
            st.error("Please fill in all required fields.")
        elif reg_password != reg_confirm:
            st.error("Passwords do not match.")
        else:
            result = auth.register(reg_email, reg_password, reg_role)
            if result["success"]:
                st.success("Account created. You can now sign in.")
            else:
                st.error(result["error"])

# ── PRODUCT PROOF — dark scorecard as terminal widget ─────────────────

st.markdown("""
<div class="ts-proof">
  <div class="ts-proof-eyebrow">Live analysis preview</div>
  <div class="score-card">
    <div class="sc-label">
      <span class="sc-dot"></span>
      EGFR &nbsp;&middot;&nbsp; Non-Small Cell Lung Cancer
    </div>
    <div class="sc-verdict">
      <span class="sc-go">GO</span>
      <span class="sc-num">82.5</span>
      <span class="sc-denom">&thinsp;/ 100</span>
    </div>
    <div class="sc-bar-bg">
      <div class="sc-bar" style="width:82.5%"></div>
    </div>
    <div class="sc-grid">
      <span class="sc-dim">Genetic Evidence</span>    <span class="sc-val">88</span>
      <span class="sc-dim">Druggability</span>         <span class="sc-val">91</span>
      <span class="sc-dim">Clinical Translation</span> <span class="sc-val">79</span>
      <span class="sc-dim">Safety &amp; Selectivity</span><span class="sc-val">74</span>
      <span class="sc-dim">Literature Consensus</span> <span class="sc-val">76</span>
    </div>
    <hr class="sc-hr">
    <div class="sc-srcs">
      <span class="sc-src">OpenTargets</span>
      <span class="sc-src">PubMed</span>
      <span class="sc-src">ChEMBL</span>
      <span class="sc-src">DGIdb</span>
      <span class="sc-src">UniProt</span>
      <span class="sc-src">ClinTrials</span>
    </div>
  </div>
</div>

<div class="bp-compliance">
  <span>&#10003;</span> 21 CFR Part 11
  <span>&#10003;</span> SHA-256 Audit Chain
  <span>&#10003;</span> GxP Compliant
</div>
""", unsafe_allow_html=True)

# ── FOOTER ───────────────────────────────────────────────────────────

st.markdown(
    "<div class='login-footer'>"
    "TargetSight&#8482; &nbsp;&middot;&nbsp; 21 CFR Part 11 Compliant &nbsp;&middot;&nbsp; "
    "SHA-256 Audit Chain &nbsp;&middot;&nbsp; For authorized pharmaceutical research use only."
    "</div>",
    unsafe_allow_html=True,
)
