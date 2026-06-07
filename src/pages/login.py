"""Login page — Apple-grade pharma premium design.

Full-page dark immersive layout:
- Left: Big bold brand statement + animated glassmorphism scorecard
- Right: Clean dark form card
- Animated radial glow, floating scorecard, electric blue CTAs
"""

import streamlit as st

from src.auth.service import AuthService

# ── Full-page CSS ────────────────────────────────────────────────────

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@600;700&family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ── DARK FULL PAGE ── */
.stApp { background: #06090f !important; }
.main, .block-container { background: transparent !important; }
.block-container { max-width: 1300px !important; padding: 0 2.5rem !important; }
section[data-testid="stSidebar"] { display: none !important; }
footer { display: none !important; }
#MainMenu { display: none !important; }

/* ── GLOBAL GLOW BACKGROUND ── */
.stApp::before {
    content: '';
    position: fixed;
    top: -30%;
    left: -15%;
    width: 800px;
    height: 800px;
    background: radial-gradient(circle, rgba(26,111,224,0.10) 0%, transparent 60%);
    pointer-events: none;
    z-index: 0;
}
.stApp::after {
    content: '';
    position: fixed;
    bottom: -20%;
    right: -10%;
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, rgba(124,58,237,0.07) 0%, transparent 60%);
    pointer-events: none;
    z-index: 0;
}

/* ── BRAND PANEL ── */
.brand-panel {
    padding: 80px 40px 60px 8px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-height: 90vh;
    position: relative;
    z-index: 1;
}
.bp-eyebrow {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.62rem;
    color: #38bdf8;
    text-transform: uppercase;
    letter-spacing: 0.24em;
    font-weight: 700;
    margin-bottom: 28px;
}
.bp-eyebrow::before {
    content: '';
    display: block;
    width: 24px;
    height: 2px;
    background: linear-gradient(90deg, #1a6fe0, #38bdf8);
    border-radius: 2px;
    flex-shrink: 0;
}
.bp-headline {
    font-size: 4.4rem !important;
    font-weight: 900 !important;
    color: #ffffff !important;
    line-height: 1.0 !important;
    letter-spacing: -0.04em !important;
    margin: 0 0 20px 0 !important;
}
.bp-grad {
    background: linear-gradient(135deg, #38bdf8 0%, #1a6fe0 50%, #818cf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.bp-sub {
    font-size: 1.05rem;
    color: rgba(255,255,255,0.48);
    line-height: 1.75;
    max-width: 400px;
    margin-bottom: 40px;
}
.bp-sub em { color: #38bdf8; font-style: normal; font-weight: 600; }

/* ── SCORECARD CARD (glassmorphism + float) ── */
.score-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 20px;
    padding: 26px 24px 22px;
    max-width: 390px;
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    box-shadow: 0 24px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.05);
    animation: floatcard 7s ease-in-out infinite;
    margin-bottom: 32px;
    position: relative;
    overflow: hidden;
}
.score-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #1a6fe0, #38bdf8, transparent);
    opacity: 0.7;
}
@keyframes floatcard {
    0%, 100% { transform: translateY(0px) rotate(0deg); }
    33%       { transform: translateY(-6px) rotate(0.2deg); }
    66%       { transform: translateY(-3px) rotate(-0.1deg); }
}
.sc-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.58rem;
    color: #38bdf8;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    font-weight: 700;
    margin-bottom: 16px;
}
.sc-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #16a34a;
    box-shadow: 0 0 8px #16a34a;
    animation: livepulse 2s ease-in-out infinite;
}
@keyframes livepulse {
    0%,100% { box-shadow: 0 0 4px #16a34a; }
    50%      { box-shadow: 0 0 12px #16a34a, 0 0 20px rgba(22,163,74,0.4); }
}
.sc-verdict { display: flex; align-items: baseline; gap: 14px; margin-bottom: 12px; }
.sc-go {
    background: linear-gradient(135deg, #16a34a, #15803d);
    color: white;
    font-size: 0.7rem;
    font-weight: 800;
    padding: 4px 16px;
    border-radius: 20px;
    letter-spacing: 0.12em;
    box-shadow: 0 2px 12px rgba(22,163,74,0.4);
}
.sc-num {
    font-size: 2.4rem;
    font-weight: 700;
    color: white;
    font-family: 'IBM Plex Mono', monospace;
    line-height: 1;
}
.sc-denom { font-size: 0.8rem; color: rgba(255,255,255,0.28); font-family: 'IBM Plex Mono', monospace; }
.sc-bar-bg { background: rgba(255,255,255,0.07); border-radius: 4px; height: 6px; margin-bottom: 22px; overflow: hidden; }
.sc-bar { background: linear-gradient(90deg, #1a6fe0, #38bdf8); border-radius: 4px; height: 6px;
          animation: barfill 1.8s ease-out; }
@keyframes barfill { from { width: 0%; } }
.sc-grid { display: grid; grid-template-columns: 1fr auto; gap: 8px 16px; margin-bottom: 18px; }
.sc-dim { font-size: 0.73rem; color: rgba(255,255,255,0.45); }
.sc-val { font-size: 0.73rem; color: #38bdf8; font-weight: 700; font-family: 'IBM Plex Mono', monospace; text-align: right; }
.sc-hr { border: none; border-top: 1px solid rgba(255,255,255,0.07); margin: 12px 0; }
.sc-srcs { display: flex; flex-wrap: wrap; gap: 5px; }
.sc-src {
    background: rgba(26,111,224,0.14);
    color: rgba(147,197,253,0.9);
    border: 1px solid rgba(26,111,224,0.22);
    border-radius: 5px;
    padding: 2px 8px;
    font-size: 0.6rem;
    font-weight: 600;
    letter-spacing: 0.03em;
}

/* Compliance strip */
.bp-compliance {
    font-size: 0.67rem;
    color: rgba(255,255,255,0.2);
    letter-spacing: 0.04em;
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
}
.bp-compliance span { color: rgba(22,163,74,0.55); }

/* ── FORM PANEL ── */
.form-panel {
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-height: 90vh;
    padding: 80px 8px 60px 24px;
    position: relative;
    z-index: 1;
}
.form-hd { margin-bottom: 28px; }
.form-hd h2 {
    font-size: 1.55rem !important;
    font-weight: 800 !important;
    color: #ffffff !important;
    margin-bottom: 6px !important;
    letter-spacing: -0.02em !important;
}
.form-hd p { font-size: 0.83rem; color: rgba(255,255,255,0.35); margin: 0; }

/* Dark Streamlit widget overrides */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid rgba(255,255,255,0.08) !important;
    gap: 0 !important;
    margin-bottom: 22px !important;
}
.stTabs [data-baseweb="tab"] {
    color: rgba(255,255,255,0.32) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 10px 22px !important;
    background: transparent !important;
}
.stTabs [aria-selected="true"] {
    color: #ffffff !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab-highlight"] { background: #1a6fe0 !important; height: 2px !important; }
.stTabs [data-baseweb="tab-border"] { display: none !important; }
.stTabs [data-baseweb="tab-panel"] { padding: 0 !important; }

/* Inputs */
.stTextInput > label {
    color: rgba(255,255,255,0.42) !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}
.stTextInput > div > div > input {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    color: #f1f5f9 !important;
    border-radius: 12px !important;
    padding: 13px 16px !important;
    font-size: 14px !important;
    transition: all 0.2s !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextInput > div > div > input:focus {
    border-color: rgba(26,111,224,0.6) !important;
    box-shadow: 0 0 0 3px rgba(26,111,224,0.18) !important;
    background: rgba(26,111,224,0.05) !important;
}
.stTextInput > div > div > input::placeholder { color: rgba(255,255,255,0.18) !important; }
[data-baseweb="base-input"] { background: transparent !important; }

/* Selectbox */
.stSelectbox > label {
    color: rgba(255,255,255,0.42) !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}
.stSelectbox > div > div {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    color: #f1f5f9 !important;
    border-radius: 12px !important;
}
.stSelectbox svg { fill: rgba(255,255,255,0.4) !important; }

/* Submit button */
.stFormSubmitButton > button {
    background: linear-gradient(135deg, #1a6fe0 0%, #0d4db8 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    letter-spacing: 0.04em !important;
    border-radius: 12px !important;
    padding: 14px !important;
    box-shadow: 0 4px 24px rgba(26,111,224,0.38) !important;
    transition: all 0.2s ease !important;
    margin-top: 4px !important;
}
.stFormSubmitButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 36px rgba(26,111,224,0.52) !important;
}
.stFormSubmitButton > button:active { transform: translateY(0) !important; }

/* Error / success */
[data-testid="stAlert"] { border-radius: 12px !important; }

/* Footer */
.login-footer {
    text-align: center;
    color: rgba(255,255,255,0.14);
    font-size: 0.67rem;
    padding: 0 0 32px;
    letter-spacing: 0.04em;
}

/* Responsive */
@media (max-width: 768px) {
    .bp-headline { font-size: 2.8rem !important; }
    .brand-panel, .form-panel { min-height: auto; padding: 40px 8px; }
    .block-container { padding: 0 1rem !important; }
}
</style>""", unsafe_allow_html=True)

# ── Layout: 2 columns ────────────────────────────────────────────────

col_brand, col_form = st.columns([1.15, 0.85], gap="large")

# ── LEFT: Brand Panel ────────────────────────────────────────────────

with col_brand:
    st.markdown("""
<div class="brand-panel">

  <div class="bp-eyebrow">Pharmaceutical AI Platform</div>

  <div class="bp-headline">
    Drug Discovery.<br>
    <span class="bp-grad">Reimagined.</span>
  </div>

  <div class="bp-sub">
    AI-powered target intelligence that compresses weeks of manual
    research into <em>15 minutes</em>. From gene symbol to
    GO/NO-GO verdict with a complete audit trail.
  </div>

  <!-- Animated scorecard -->
  <div class="score-card">
    <div class="sc-label">
      <span class="sc-dot"></span>
      EGFR &nbsp;·&nbsp; Non-Small Cell Lung Cancer
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
      <span class="sc-dim">Genetic Evidence</span>   <span class="sc-val">88</span>
      <span class="sc-dim">Druggability</span>        <span class="sc-val">91</span>
      <span class="sc-dim">Clinical Translation</span><span class="sc-val">79</span>
      <span class="sc-dim">Safety &amp; Selectivity</span><span class="sc-val">74</span>
      <span class="sc-dim">Literature Consensus</span><span class="sc-val">76</span>
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

  <div class="bp-compliance">
    <span>✓</span> 21 CFR Part 11
    <span>✓</span> SHA-256 Audit Chain
    <span>✓</span> GxP Compliant
  </div>

</div>
""", unsafe_allow_html=True)

# ── RIGHT: Form Panel ────────────────────────────────────────────────

with col_form:
    if st.session_state.pop("session_expired", False):
        st.warning("Your session expired due to inactivity.")

    st.markdown("""
<div class="form-panel">
  <div class="form-hd">
    <h2>Welcome back</h2>
    <p>Sign in to your BioOrchestrator account</p>
  </div>
</div>
""", unsafe_allow_html=True)

    login_tab, register_tab = st.tabs(["Sign In", "Create Account"])

    auth = AuthService()

    # ── Sign In ──────────────────────────────────────────────────────
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

    # ── Create Account ────────────────────────────────────────────────
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

# ── Footer ───────────────────────────────────────────────────────────

st.markdown(
    "<div class='login-footer'>"
    "BioOrchestrator v2 &nbsp;·&nbsp; 21 CFR Part 11 Compliant &nbsp;·&nbsp; "
    "For authorized pharmaceutical research use only."
    "</div>",
    unsafe_allow_html=True,
)
