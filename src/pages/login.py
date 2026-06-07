"""TargetSight — Login page.

Light-mode enterprise layout:
- Left: TargetSight wordmark + brand statement + dark EGFR scorecard (contrast widget)
- Right: Floating white card with Stripe-style layered shadow
- Warm cream background (#f4f3f0), dark navy text, teal accents only in logo/button
"""

import streamlit as st

from src.auth.service import AuthService

# ── Full-page CSS ────────────────────────────────────────────────────

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&family=JetBrains+Mono:wght@500;600;700&display=swap');

/* ── PAGE FOUNDATION — LIGHT MODE ── */
.stApp {
    background-color: #f4f3f0 !important;
    background-image:
        radial-gradient(rgba(15,23,42,0.04) 1px, transparent 1px),
        radial-gradient(rgba(15,23,42,0.025) 1px, transparent 1px) !important;
    background-size: 28px 28px, 56px 56px !important;
    background-position: 0 0, 14px 14px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.main, .block-container { background: transparent !important; }
.block-container { max-width: 1300px !important; padding: 4vh 2.5rem 0 !important; }
section[data-testid="stSidebar"] { display: none !important; }
footer { display: none !important; }
#MainMenu { display: none !important; }

/* ── TARGETSIGHT WORDMARK ── */
.ts-wordmark {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 32px;
    position: relative;
    z-index: 2;
}
.ts-wordmark svg { flex-shrink: 0; }
.ts-wordname {
    font-size: 1.5rem;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.03em;
    line-height: 1;
    font-family: 'Plus Jakarta Sans', sans-serif;
}
.ts-wordname span { color: #0d9488; }
.ts-tagline-sm {
    font-size: 0.57rem;
    color: rgba(15,23,42,0.38);
    text-transform: uppercase;
    letter-spacing: 0.22em;
    font-weight: 600;
    margin-top: 5px;
    font-family: 'Plus Jakarta Sans', sans-serif;
}

/* ── BRAND PANEL ── */
.brand-panel {
    padding: 56px 40px 44px 8px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    position: relative;
    z-index: 1;
}
.bp-headline {
    font-size: 3.8rem !important;
    font-weight: 800 !important;
    color: #0f172a !important;
    line-height: 1.05 !important;
    letter-spacing: -0.04em !important;
    margin: 0 0 18px 0 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    position: relative;
    z-index: 2;
}
.bp-grad { color: #0d9488; }
.bp-sub {
    font-size: 1.0rem;
    color: #64748b;
    line-height: 1.75;
    max-width: 400px;
    margin-bottom: 22px;
    font-family: 'Plus Jakarta Sans', sans-serif;
    position: relative;
    z-index: 2;
}
.bp-sub em { color: #0d9488; font-style: normal; font-weight: 600; }

/* ── SCORECARD — STAYS DARK (Bloomberg terminal widget) ── */
.score-card {
    background: #17181c;
    border: 1px solid rgba(255,255,255,0.08);
    border-left: 2px solid #14b8a6;
    border-radius: 12px;
    padding: 20px 20px 16px;
    max-width: 390px;
    box-shadow:
        0 1px 3px rgba(0,0,0,0.10),
        0 8px 28px rgba(0,0,0,0.14),
        0 20px 56px rgba(0,0,0,0.10);
    margin-bottom: 20px;
    position: relative;
    z-index: 2;
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
.sc-bar { background: linear-gradient(90deg, #0d9488, #2dd4bf); border-radius: 3px; height: 5px;
          animation: barfill 1.8s cubic-bezier(0.4, 0, 0.2, 1); }
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

/* Compliance strip */
.bp-compliance {
    font-size: 0.65rem;
    color: #94a3b8;
    letter-spacing: 0.04em;
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
    font-family: 'Plus Jakarta Sans', sans-serif;
    position: relative;
    z-index: 2;
}
.bp-compliance span { color: #059669; }

/* ── FORM PANEL — WHITE FLOATING CARD ── */
.form-panel {
    background: #ffffff;
    border: 1px solid #e8e4de;
    border-radius: 16px;
    padding: 40px 36px 32px;
    box-shadow:
        0 1px 3px rgba(0,0,0,0.06),
        0 6px 20px rgba(0,0,0,0.07),
        0 16px 48px rgba(0,0,0,0.05);
    margin-top: 16px;
    position: relative;
    z-index: 1;
}
.form-hd { margin-bottom: 28px; }
.form-hd h2 {
    font-size: 1.55rem !important;
    font-weight: 800 !important;
    color: #0f172a !important;
    margin-bottom: 6px !important;
    letter-spacing: -0.02em !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.form-hd p {
    font-size: 0.83rem;
    color: #64748b;
    margin: 0;
    font-family: 'Plus Jakarta Sans', sans-serif;
}

/* ── WIDGET OVERRIDES ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #e2e8f0 !important;
    gap: 0 !important;
    margin-bottom: 22px !important;
}
.stTabs [data-baseweb="tab"] {
    color: #94a3b8 !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 10px 22px !important;
    background: transparent !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    letter-spacing: 0.01em !important;
}
.stTabs [aria-selected="true"] { color: #0f172a !important; background: transparent !important; }
.stTabs [data-baseweb="tab-highlight"] { background: #0d9488 !important; height: 2px !important; }
.stTabs [data-baseweb="tab-border"] { display: none !important; }
.stTabs [data-baseweb="tab-panel"] { padding: 0 !important; }

/* Inputs */
.stTextInput > label, .stSelectbox > label {
    color: #374151 !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.stTextInput > div > div > input {
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    color: #0f172a !important;
    border-radius: 10px !important;
    padding: 13px 16px !important;
    font-size: 14px !important;
    transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.stTextInput > div > div > input:focus {
    border-color: #0d9488 !important;
    box-shadow: 0 0 0 3px rgba(13,148,136,0.1) !important;
    background: #ffffff !important;
}
.stTextInput > div > div > input::placeholder { color: #94a3b8 !important; }
[data-baseweb="base-input"] { background: transparent !important; }

/* Selectbox */
.stSelectbox > div > div {
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    color: #0f172a !important;
    border-radius: 10px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.stSelectbox svg { fill: #64748b !important; }

/* Submit button */
.stFormSubmitButton > button {
    background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%) !important;
    border: none !important;
    color: #f0fdf4 !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    letter-spacing: 0.04em !important;
    border-radius: 10px !important;
    padding: 14px !important;
    box-shadow: 0 2px 12px rgba(13,148,136,0.28) !important;
    transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1) !important;
    margin-top: 4px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.stFormSubmitButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(13,148,136,0.38) !important;
}
.stFormSubmitButton > button:active {
    transform: translateY(0) scale(0.99) !important;
    box-shadow: 0 1px 6px rgba(13,148,136,0.2) !important;
}

/* Alerts */
[data-testid="stAlert"] { border-radius: 10px !important; }

/* Footer */
.login-footer {
    text-align: center;
    color: #94a3b8;
    font-size: 0.65rem;
    padding: 0 0 28px;
    letter-spacing: 0.05em;
    font-family: 'Plus Jakarta Sans', sans-serif;
}

/* Responsive */
@media (max-width: 768px) {
    .bp-headline { font-size: 2.6rem !important; }
    .brand-panel { padding: 36px 8px; }
    .form-panel { margin-top: 24px; padding: 28px 20px 24px; }
    .block-container { padding: 0 1rem !important; }
}
</style>""", unsafe_allow_html=True)

# ── Layout: 2 columns ────────────────────────────────────────────────

col_brand, col_form = st.columns([1.15, 0.85], gap="large")

# ── LEFT: Brand Panel ────────────────────────────────────────────────

with col_brand:
    st.markdown("""
<div class="brand-panel">

  <!-- TargetSight wordmark -->
  <div class="ts-wordmark">
    <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" width="38" height="38">
      <polygon points="20,4 33.5,12 33.5,28 20,36 6.5,28 6.5,12"
        stroke="#14b8a6" stroke-width="1.6" fill="none" stroke-linejoin="round"/>
      <polygon points="20,12.5 27.5,16.75 27.5,25.25 20,29.5 12.5,25.25 12.5,16.75"
        stroke="#14b8a6" stroke-width="1.1" fill="none" opacity="0.35" stroke-linejoin="round"/>
      <circle cx="20" cy="20" r="2.4" fill="#14b8a6"/>
    </svg>
    <div>
      <div class="ts-wordname">Target<span>Sight</span></div>
      <div class="ts-tagline-sm">Target Intelligence &middot; Redefined</div>
    </div>
  </div>

  <div class="bp-headline">
    From Gene to<br>
    <span class="bp-grad">GO&thinsp;/&thinsp;NO-GO.</span>
  </div>

  <div class="bp-sub">
    AI-powered target intelligence that compresses
    <em>weeks of manual research into 15 minutes</em> — with a fully
    auditable evidence trail your regulatory team will trust.
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
    <p>Sign in to your TargetSight account</p>
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
    "TargetSight&#8482; &nbsp;·&nbsp; 21 CFR Part 11 Compliant &nbsp;·&nbsp; "
    "SHA-256 Audit Chain &nbsp;·&nbsp; For authorized pharmaceutical research use only."
    "</div>",
    unsafe_allow_html=True,
)
