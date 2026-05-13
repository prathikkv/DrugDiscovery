"""Audit Trail page -- filterable audit records with hash chain verification.

Displays:
- Hash chain integrity verification (verify_chain button)
- Filterable audit records from AuditTrail.get_records()
- Expandable record detail views with full JSON and hash chain info
- Record count metrics

Provides regulatory compliance visibility for 21 CFR Part 11.
"""

import json

import streamlit as st

from src.compliance.audit_trail import AuditTrail
from src.pages.components.styles import insight_panel


# ── Auth Guard ───────────────────────────────────────────────────────

if "user" not in st.session_state:
    st.warning("Please log in to access the audit trail.")
    st.stop()

st.title("Audit Trail")
st.caption(
    "Complete audit trail with hash chain integrity verification "
    "for 21 CFR Part 11 compliance."
)


# ── Hash Chain Verification ──────────────────────────────────────────

st.subheader("Chain Integrity")

if st.button("Verify Chain Integrity", key="audit_verify_chain", type="primary"):
    audit = AuditTrail()
    result = audit.verify_chain()

    if result["valid"]:
        st.success(
            f"Chain integrity verified. {result['records_checked']} records checked."
        )
        st.markdown(
            insight_panel(
                f"<strong>Integrity Status: VALID</strong><br>"
                f"All {result['records_checked']} audit records have valid "
                f"SHA-256 hash chain linkage. No tampering detected."
            ),
            unsafe_allow_html=True,
        )
    else:
        st.error(
            f"Chain broken at record {result['first_broken']}: {result['error']}"
        )


# ── Filters ──────────────────────────────────────────────────────────

st.subheader("Audit Records")

filter_col1, filter_col2 = st.columns(2)

with filter_col1:
    resource_type_filter = st.selectbox(
        "Resource Type",
        options=["All", "project", "hitl_gate", "task", "reasoning"],
        key="audit_filter_resource_type",
    )

with filter_col2:
    record_limit = st.number_input(
        "Max Records",
        value=100,
        min_value=10,
        max_value=1000,
        step=10,
        key="audit_filter_limit",
    )

# ── Records Display ──────────────────────────────────────────────────

audit = AuditTrail()

# Apply filters
filter_kwargs = {"limit": record_limit}
if resource_type_filter != "All":
    filter_kwargs["resource_type"] = resource_type_filter

records = audit.get_records(**filter_kwargs)

# Record count metric
st.metric("Records Found", len(records))

if not records:
    st.info("No audit records found matching the selected filters.")
else:
    # Display as dataframe for overview
    display_data = []
    for record in records:
        display_data.append({
            "Seq": record.get("sequence_id", ""),
            "Timestamp": record.get("timestamp", "")[:19],
            "User": record.get("user_id", ""),
            "Action": record.get("action", ""),
            "Resource Type": record.get("resource_type", ""),
            "Resource ID": record.get("resource_id", "")[:20],
        })

    st.dataframe(
        display_data,
        use_container_width=True,
        hide_index=True,
        key="audit_records_table",
    )

    # Expandable detail view for each record
    st.subheader("Record Details")

    for record in records:
        seq_id = record.get("sequence_id", "?")
        action = record.get("action", "")
        resource_type = record.get("resource_type", "")

        with st.expander(
            f"Record #{seq_id}: {action} ({resource_type})",
            expanded=False,
        ):
            # Full details JSON
            details_json = record.get("details_json", "{}")
            try:
                details = json.loads(details_json) if isinstance(details_json, str) else details_json
                st.json(details)
            except (json.JSONDecodeError, TypeError):
                st.code(str(details_json))

            # Hash chain info
            st.markdown("**Hash Chain:**")
            st.code(
                f"Record Hash:   {record.get('record_hash', 'N/A')}\n"
                f"Previous Hash: {record.get('previous_hash', 'N/A')}",
                language=None,
            )

            # Signature info for SIGN actions
            if action == "SIGN":
                st.markdown("**Electronic Signature Record**")
                try:
                    sig_details = json.loads(details_json) if isinstance(details_json, str) else details_json
                    if isinstance(sig_details, dict):
                        st.markdown(f"- **Meaning:** {sig_details.get('meaning', 'N/A')}")
                        st.markdown(f"- **User:** {record.get('user_id', 'N/A')}")
                        st.markdown(f"- **Timestamp:** {record.get('timestamp', 'N/A')}")
                except (json.JSONDecodeError, TypeError):
                    pass
