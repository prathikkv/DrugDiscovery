"""Reusable HITL (Human-in-the-Loop) gate with dual-mode behavior.

Provides a blocking approval checkpoint that behaves differently based
on the active project mode:

- **Exploration mode**: Auto-approves with audit trail logging.
- **Compliance mode**: Renders a blocking gate UI with e-signature
  dialog (21 CFR Part 11 compliant).

Usage:
    from src.pages.components.hitl_gate import hitl_gate

    if hitl_gate("qc_review", "QC Review Gate", "omics_pipeline",
                 "Approve QC results before proceeding",
                 {"Cells Passed": "12,345", "Genes Detected": "18,200"}):
        # Proceed with downstream analysis
        ...
"""

import streamlit as st

from src.compliance.audit_trail import AuditTrail
from src.compliance.electronic_signature import ElectronicSignature
from src.pages.components.styles import metric_card


def hitl_gate(
    gate_id: str,
    gate_title: str,
    module: str,
    description: str,
    data_summary: dict[str, str] | None = None,
) -> bool:
    """Render a HITL approval gate with mode-dependent behavior.

    Args:
        gate_id: Unique identifier for this gate (used in session_state keys).
        gate_title: Display title for the gate (e.g. "QC Review Gate").
        module: Module name for audit trail (e.g. "omics_pipeline").
        description: Short description shown to the user.
        data_summary: Optional dict of label->value pairs shown as metric cards.

    Returns:
        True if the gate has been approved, False otherwise.
        In compliance mode, calls st.stop() to block page progression
        when not yet approved, so the return value is always True when
        the function returns normally.
    """
    # Gate state key in session_state
    state_key = f"hitl_{gate_id}_approved"

    # Already approved -- return immediately
    if st.session_state.get(state_key, False):
        return True

    # Determine mode from project config
    project_config = st.session_state.get("project_config", {})
    mode = project_config.get("mode", "exploration")

    if mode == "exploration":
        return _auto_approve(gate_id, gate_title, module, state_key)
    else:
        return _compliance_gate(gate_id, gate_title, module, description,
                                data_summary, state_key)


def _auto_approve(
    gate_id: str,
    gate_title: str,
    module: str,
    state_key: str,
) -> bool:
    """Auto-approve in exploration mode with audit trail logging."""
    audit = AuditTrail()
    audit.append_record(
        user_id=st.session_state.get("user", {}).get("user_id", "system"),
        action="AUTO_APPROVE",
        resource_type="hitl_gate",
        resource_id=gate_id,
        details={
            "gate_title": gate_title,
            "module": module,
            "mode": "exploration",
        },
    )
    st.session_state[state_key] = True
    return True


def _compliance_gate(
    gate_id: str,
    gate_title: str,
    module: str,
    description: str,
    data_summary: dict[str, str] | None,
    state_key: str,
) -> bool:
    """Render blocking gate UI in compliance mode.

    Uses session_state flags for dialog trigger state (not button state
    directly) to survive st.rerun() cycles.
    """
    show_esign_key = f"show_esign_{gate_id}"
    esign_action_key = f"esign_action_{gate_id}"

    with st.container(border=True):
        st.subheader(f":material/verified_user: {gate_title}")
        st.caption(description)

        # Show data summary as metric cards if provided
        if data_summary:
            cards_html = '<div class="metrics-row">'
            for label, value in data_summary.items():
                cards_html += metric_card(label, value)
            cards_html += '</div>'
            st.markdown(cards_html, unsafe_allow_html=True)

        st.divider()

        # Approve / Reject buttons
        col_approve, col_reject = st.columns(2)
        with col_approve:
            if st.button(
                "Approve",
                key=f"hitl_{gate_id}_approve_btn",
                type="primary",
                use_container_width=True,
            ):
                st.session_state[show_esign_key] = True
                st.session_state[esign_action_key] = True
                st.rerun()

        with col_reject:
            if st.button(
                "Reject",
                key=f"hitl_{gate_id}_reject_btn",
                type="secondary",
                use_container_width=True,
            ):
                st.session_state[show_esign_key] = True
                st.session_state[esign_action_key] = False
                st.rerun()

    # Check dialog trigger OUTSIDE the button block (survives rerun)
    if st.session_state.get(show_esign_key, False):
        approved = st.session_state.get(esign_action_key, True)
        _show_esign_dialog(gate_id, gate_title, module, approved)

    # Block page progression
    st.info(
        "This gate requires approval before you can proceed. "
        "Please review the data above and click Approve or Reject."
    )
    st.stop()

    # Never reached, but satisfies return type
    return False  # pragma: no cover


@st.dialog("Electronic Signature Required", width="medium")
def _show_esign_dialog(
    gate_id: str,
    gate_title: str,
    module: str,
    approved: bool,
) -> None:
    """E-signature dialog for compliance mode gate approval/rejection.

    Blocks until password re-authentication succeeds. Records the
    signature in the audit trail via ElectronicSignature.sign().
    """
    action_text = "APPROVED" if approved else "REJECTED"

    st.markdown(
        f"**Action:** {action_text} -- {gate_title}",
    )
    st.caption(
        "Re-enter your password to electronically sign this decision. "
        "This signature is recorded in the audit trail per 21 CFR Part 11."
    )

    password = st.text_input(
        "Password",
        type="password",
        key=f"hitl_{gate_id}_esign_password",
    )

    meaning = f"{action_text}: {gate_title} (module: {module})"

    if st.button(
        "Sign",
        key=f"hitl_{gate_id}_esign_sign_btn",
        type="primary",
        use_container_width=True,
    ):
        if not password:
            st.error("Password is required.")
            return

        user = st.session_state.get("user", {})
        user_id = user.get("user_id", "")

        if not user_id:
            st.error("No authenticated user found.")
            return

        audit = AuditTrail()
        esig = ElectronicSignature(audit)
        result = esig.sign(
            user_id=user_id,
            password=password,
            resource_type="hitl_gate",
            resource_id=gate_id,
            meaning=meaning,
        )

        if result["success"]:
            # Set gate state based on approval/rejection
            state_key = f"hitl_{gate_id}_approved"
            st.session_state[state_key] = approved

            # Clean up dialog trigger flags
            show_esign_key = f"show_esign_{gate_id}"
            esign_action_key = f"esign_action_{gate_id}"
            if show_esign_key in st.session_state:
                del st.session_state[show_esign_key]
            if esign_action_key in st.session_state:
                del st.session_state[esign_action_key]

            st.rerun()
        else:
            st.error(f"Signature failed: {result['error']}")
