"""Login and registration page using AuthService.

Provides two tabs:
- Login: authenticate with email and password
- Register: create a new account with role selection

Password is NEVER stored in session state. Only user_id, email, and
role are persisted in st.session_state["user"] after successful login.
"""

import streamlit as st

from src.auth.service import AuthService


st.title("Welcome to BioOrchestrator v2")

login_tab, register_tab = st.tabs(["Login", "Register"])

auth = AuthService()

# ── Login Tab ────────────────────────────────────────────────────────

with login_tab:
    with st.form("login_form"):
        st.subheader("Sign In")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Login", use_container_width=True)

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

# ── Register Tab ─────────────────────────────────────────────────────

with register_tab:
    with st.form("register_form"):
        st.subheader("Create Account")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_password")
        reg_confirm = st.text_input(
            "Confirm Password", type="password", key="reg_confirm"
        )
        reg_role = st.selectbox(
            "Role",
            options=["analyst", "reviewer", "admin"],
            key="reg_role",
        )
        reg_submitted = st.form_submit_button(
            "Register", use_container_width=True
        )

    if reg_submitted:
        if not reg_email or not reg_password:
            st.error("Please fill in all fields.")
        elif reg_password != reg_confirm:
            st.error("Passwords do not match.")
        else:
            result = auth.register(reg_email, reg_password, reg_role)
            if result["success"]:
                st.success("Account created! You can now sign in.")
            else:
                st.error(result["error"])
