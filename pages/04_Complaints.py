"""Complaint Management Lifecycle: Intake, Attachments, Triage & Audit Trail."""
import streamlit as st
import pandas as pd
from datetime import date
from src.products.service import list_products, list_customers
from src.complaint_management.service import (
    create_complaint, update_complaint_status, list_complaints,
    get_complaint_by_id, add_complaint_attachment, VALID_STATUSES
)
from src.ui_components import inject_custom_styles, render_header, render_sidebar_auth_status, require_auth

st.set_page_config(page_title="Complaints — Quality AI", page_icon="📝", layout="wide")
inject_custom_styles()
render_sidebar_auth_status()
user = require_auth()

render_header("Complaint Lifecycle & Investigation Portal", "Intake, Multi-File Attachments, Status Transitions, and Audit History")

tab_list, tab_detail, tab_new, tab_bulk = st.tabs(["📋 Complaint Directory", "🔍 Case Detail & Workflow", "➕ New Complaint Intake", "📂 Bulk CSV Upload"])

COMPLAINT_CATEGORIES = [
    "Physical damage",
    "Dimensional defects",
    "Material defects",
    "Chemical or material concerns",
    "Color or finish defects",
    "Packaging issues",
    "Functional failure",
    "Labeling or documentation issues",
    "Delivery-related concerns",
    "Other or unknown"
]

products = list_products()
customers = list_customers()

# ----------------- TAB 1: COMPLAINTS DIRECTORY -----------------
with tab_list:
    c_f1, c_f2, c_f3 = st.columns([1.5, 1, 1])
    with c_f1:
        s_query = st.text_input("Search Case ID, SKU, or Description", placeholder="e.g. CMP-2026 or NDT-800")
    with c_f2:
        s_stat = st.selectbox("Status Filter", ["All"] + VALID_STATUSES)
    with c_f3:
        s_sev = st.selectbox("Severity Filter", ["All", "Critical", "High", "Medium", "Low"])

    # Enforce Customer Isolation if user is an external customer
    cust_filter_id = user.get("customer_id") if user.get("role") == "Customer" else None

    complaints = list_complaints(
        customer_id=cust_filter_id,
        status=s_stat,
        severity=s_sev,
        search=s_query
    )

    if not complaints:
        st.info("No complaints found matching current criteria.")
    else:
        df_c = pd.DataFrame(complaints)
        st.write(f"Showing **{len(df_c)}** complaint record(s):")
        st.dataframe(
            df_c[[
                "complaint_id", "product_sku", "customer_name", "category",
                "severity", "current_status", "quantity_affected", "date_received"
            ]].rename(columns={
                "complaint_id": "Case ID",
                "product_sku": "SKU",
                "customer_name": "Customer",
                "category": "Category",
                "severity": "Severity",
                "current_status": "Status",
                "quantity_affected": "Qty",
                "date_received": "Date"
            }),
            use_container_width=True,
            hide_index=True
        )

# ----------------- TAB 2: CASE DETAIL & WORKFLOW -----------------
with tab_detail:
    st.markdown("#### Investigate Case & Advance Lifecycle Stage")
    if not complaints:
        st.info("No complaints available.")
    else:
        sel_case = st.selectbox(
            "Select Case to Inspect",
            complaints,
            format_func=lambda c: f"{c['complaint_id']} — [{c['current_status']}] {c['product_sku']} ({c['category']})"
        )

        full_case = get_complaint_by_id(sel_case["id"])

        col_left, col_right = st.columns([1.6, 1])

        with col_left:
            st.markdown(f"### Case: `{full_case['complaint_id']}`")
            st.markdown(f"**Product:** {full_case['product_name']} (`{full_case['sku']}`) | **Category:** {full_case['category']}")
            st.markdown(f"**Customer:** {full_case.get('customer_name', 'Direct / Internal')} | **Reporter:** {full_case['reporter_type']}")
            st.markdown(f"**Order / Batch Number:** `{full_case.get('order_batch_number', 'N/A')}`")
            st.markdown(f"**Severity / Urgency:** `{full_case['severity']}` / `{full_case['urgency']}` | **Units Affected:** {full_case['quantity_affected']}")
            
            st.markdown("##### 📝 Defect Description")
            st.info(full_case["description"])

            # Customer vs Internal Notes Separation
            st.markdown("##### 💬 Communication & Notes")
            c_note1, c_note2 = st.columns(2)
            with c_note1:
                st.caption("🌐 Customer-Visible Notes:")
                st.write(full_case.get("customer_visible_notes") or "*No customer-facing remarks recorded.*")
            with c_note2:
                if user.get("role") != "Customer":
                    st.caption("🔒 Internal Quality Notes (Confidential):")
                    st.write(full_case.get("internal_notes") or "*No internal notes recorded.*")
                else:
                    st.caption("🔒 Internal Notes: Hidden from external users.")

            # Attachments
            st.markdown("##### 📎 Attached Evidence & Photos")
            atts = full_case.get("attachments", [])
            if atts:
                for a in atts:
                    st.markdown(f"• 📄 `{a['file_name']}` ({round(a['file_size']/1024, 1)} KB, uploaded {a['uploaded_at']})")
            else:
                st.write("*No attachments uploaded.*")

            # Upload attachment
            with st.expander("➕ Add File / Photo Attachment"):
                att_file = st.file_uploader("Upload inspection photo, lab sheet or PDF", key=f"att_up_{full_case['id']}")
                if st.button("Upload Attachment", key=f"att_btn_{full_case['id']}"):
                    if att_file:
                        add_complaint_attachment(full_case["id"], att_file.read(), att_file.name, user["id"])
                        st.success("Attachment recorded.")
                        st.rerun()

        with col_right:
            st.markdown(f"### Current Status: `{full_case['current_status']}`")

            # Lifecycle transition controls
            if user.get("role") in ("Admin", "Quality Manager", "Quality Engineer"):
                st.markdown("##### ⚡ Advance Lifecycle Status")
                next_status = st.selectbox("New Lifecycle Stage", VALID_STATUSES, index=VALID_STATUSES.index(full_case["current_status"]))
                change_notes = st.text_input("Stage Transition Reason / Remarks", placeholder="e.g. Dimensions verified with caliper.")
                
                if st.button("Update Case Status", use_container_width=True):
                    update_complaint_status(full_case["id"], next_status, user["id"], change_notes)
                    st.success(f"Status changed to {next_status}!")
                    st.rerun()

            # Lifecycle History & Audit Trail
            st.divider()
            st.markdown("##### 📜 Case Audit History")
            history = full_case.get("status_history", [])
            for h in history:
                st.markdown(
                    f"**{h['timestamp']}** — `{h.get('from_status') or 'Init'}` ➔ **`{h['to_status']}`**<br/>"
                    f"<span style='font-size:0.8rem; color:#64748B;'>By: {h.get('changed_by_name', 'System')} | {h.get('change_notes', '')}</span>",
                    unsafe_allow_html=True
                )
                st.markdown("<hr style='margin: 0.3rem 0; border: none; border-top: 1px dashed #E2E8F0;'/>", unsafe_allow_html=True)

# ----------------- TAB 3: NEW COMPLAINT INTAKE -----------------
with tab_new:
    st.markdown("#### Submit Quality Complaint or Defect Incident")
    if not products:
        st.warning("No products registered.")
    else:
        with st.form("intake_form", clear_on_submit=True):
            col_in1, col_in2 = st.columns(2)
            with col_in1:
                sel_p = st.selectbox("Affected Product (SKU)", products, format_func=lambda p: f"{p['sku']} — {p['name']}", key="intake_p")
                
                # If external customer, lock to their customer entity
                if user.get("role") == "Customer" and user.get("customer_id"):
                    cust_obj = next((c for c in customers if c["id"] == user["customer_id"]), None)
                    sel_c = cust_obj
                    st.text_input("Customer", value=cust_obj["name"] if cust_obj else "Customer", disabled=True)
                else:
                    sel_c = st.selectbox("Customer / Retailer", [None] + customers, format_func=lambda c: f"{c['code']} — {c['name']}" if c else "Direct / Unspecified", key="intake_c")

                rep_type = st.selectbox("Reporter Type", ["Customer", "Retailer", "Internal Employee", "Field Inspector"])
                batch_no = st.text_input("Batch / Lot / Order Number", placeholder="e.g. LOT-NDT-2026-03")
                cat_sel = st.selectbox("Defect Category", COMPLAINT_CATEGORIES)

            with col_in2:
                qty_aff = st.number_input("Quantity Affected", min_value=1, value=1)
                mfg_date = st.date_input("Manufacturing Date", value=None)
                sev_sel = st.selectbox("Initial Severity", ["Low", "Medium", "High", "Critical"])
                urg_sel = st.selectbox("Urgency", ["Low", "Medium", "Urgent"])
                due_d = st.date_input("Investigation Target Due Date", value=date.today() + pd.Timedelta(days=14))

            c_desc = st.text_area("Detailed Defect Description & Measurements", placeholder="Provide exact physical measurements, observed defect symptoms, and assembly failure details...")
            
            c_vis = st.text_area("Customer-Visible Remarks (Optional)", placeholder="Information to share with customer...")
            c_int = st.text_area("Internal Confidential Notes (Optional)", placeholder="Internal root cause notes...")

            intake_submit = st.form_submit_button("🚀 Submit Complaint for Triage", use_container_width=True)

            if intake_submit:
                if not c_desc.strip():
                    st.error("Defect description is mandatory.")
                else:
                    try:
                        res = create_complaint(
                            reporter_type=rep_type,
                            product_id=sel_p["id"],
                            sku=sel_p["sku"],
                            category=cat_sel,
                            description=c_desc,
                            severity=sev_sel,
                            urgency=urg_sel,
                            customer_id=sel_c["id"] if sel_c else None,
                            order_batch_number=batch_no,
                            quantity_affected=qty_aff,
                            manufacturing_date=str(mfg_date) if mfg_date else None,
                            due_date=str(due_d) if due_d else None,
                            customer_visible_notes=c_vis,
                            internal_notes=c_int,
                            user_id=user["id"]
                        )
                        st.success(f"Complaint logged successfully! Assigned Case ID: **{res['complaint_id']}**")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to record complaint: {e}")

# ----------------- TAB 4: BULK CSV UPLOAD -----------------
with tab_bulk:
    st.markdown("#### Bulk Ingest Complaints from CSV / Excel")
    st.caption("Upload historical or batch complaint records. Expected columns: `sku`, `category`, `description`, `severity`, `urgency`, `quantity`, `batch_number`.")

    bulk_file = st.file_uploader("Select CSV File", type=["csv"], key="bulk_csv_file")
    if bulk_file:
        try:
            df_bulk = pd.read_csv(bulk_file)
            st.dataframe(df_bulk.head(5), use_container_width=True)
            
            if st.button("Process Bulk Ingestion"):
                count_ok = 0
                for _, row in df_bulk.iterrows():
                    sku_val = str(row.get("sku", "")).strip().upper()
                    matched_p = next((p for p in products if p["sku"] == sku_val), None)
                    if matched_p:
                        create_complaint(
                            reporter_type=str(row.get("reporter_type", "Customer")),
                            product_id=matched_p["id"],
                            sku=matched_p["sku"],
                            category=str(row.get("category", "Other or unknown")),
                            description=str(row.get("description", "Bulk imported complaint")),
                            severity=str(row.get("severity", "Medium")),
                            urgency=str(row.get("urgency", "Medium")),
                            order_batch_number=str(row.get("batch_number", "")),
                            quantity_affected=int(row.get("quantity", 1)),
                            user_id=user["id"]
                        )
                        count_ok += 1
                st.success(f"Successfully imported {count_ok} complaints from CSV!")
                st.rerun()
        except Exception as e:
            st.error(f"Error parsing CSV: {e}")
