"""Admin Settings: User RBAC, Criteria Builder, Audit Logs, and Demo Reset."""
import streamlit as st
import pandas as pd
from src.auth.service import list_users, create_user
from src.products.service import list_products, list_customers
from src.quality_engine.criteria_manager import list_all_criteria, create_quality_criterion
from src.audit.logger import get_recent_audit_logs
from scripts.seed_demo_data import seed_all_demo_data
from src.ui_components import inject_custom_styles, render_header, render_sidebar_auth_status, require_auth

st.set_page_config(page_title="Admin Settings — Quality AI", page_icon="⚙️", layout="wide")
inject_custom_styles()
render_sidebar_auth_status()
user = require_auth("manage_users")

render_header("System Administration & Quality Criteria Builder", "User RBAC Management, Configurable Evaluation Rules, and Audit Trail")

tab_users, tab_crit, tab_audit, tab_env = st.tabs(["👥 User & Role RBAC", "📐 Quality Criteria Builder", "📜 Immutable Audit Log", "🔄 Environment Controls"])

products = list_products()
customers = list_customers()

# ----------------- TAB 1: USER & ROLE RBAC -----------------
with tab_users:
    st.markdown("#### System User Directory")
    users_list = list_users()
    df_u = pd.DataFrame(users_list)
    st.dataframe(
        df_u[["username", "full_name", "role", "email", "customer_name", "is_active", "created_at"]].rename(columns={
            "username": "Username",
            "full_name": "Full Name",
            "role": "Role",
            "email": "Email",
            "customer_name": "Mapped Customer",
            "is_active": "Active",
            "created_at": "Created"
        }),
        use_container_width=True,
        hide_index=True
    )

    st.divider()
    st.markdown("##### ➕ Create New System User")
    with st.form("create_user_form"):
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            new_uname = st.text_input("Username", placeholder="e.g. jdoe")
            new_fname = st.text_input("Full Name", placeholder="e.g. Jane Doe")
            new_pwd = st.text_input("Password", type="password", placeholder="Minimum 8 characters")
        with col_u2:
            new_email = st.text_input("Email Address", placeholder="e.g. jdoe@codespace-techlab.com")
            new_role = st.selectbox("Assigned Role", ["Admin", "Quality Manager", "Quality Engineer", "Customer", "Management Viewer"])
            new_cust = st.selectbox("Customer Mapping (For Customer role)", [None] + customers, format_func=lambda c: f"{c['code']} — {c['name']}" if c else "None (Internal Employee)")

        if st.form_submit_button("Register User", use_container_width=True):
            if not new_uname or not new_pwd or not new_email:
                st.error("Username, password, and email are required.")
            else:
                try:
                    create_user(
                        username=new_uname,
                        password=new_pwd,
                        full_name=new_fname,
                        email=new_email,
                        role=new_role,
                        customer_id=new_cust["id"] if new_cust else None,
                        created_by_user_id=user["id"]
                    )
                    st.success(f"User {new_uname} created successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating user: {e}")

# ----------------- TAB 2: CRITERIA BUILDER -----------------
with tab_crit:
    st.markdown("#### Configured Evaluation Criteria")
    criteria = list_all_criteria()
    if criteria:
        df_cr = pd.DataFrame(criteria)
        st.dataframe(
            df_cr[["criterion_code", "name", "category", "criterion_type", "product_sku", "customer_name", "weight", "severity", "is_mandatory"]].rename(columns={
                "criterion_code": "Code",
                "name": "Criterion Name",
                "category": "Category",
                "criterion_type": "Type",
                "product_sku": "SKU",
                "customer_name": "Customer Scope",
                "weight": "Weight",
                "severity": "Severity",
                "is_mandatory": "Mandatory"
            }),
            use_container_width=True,
            hide_index=True
        )

    st.divider()
    st.markdown("##### ➕ Define New Quality Criterion")
    with st.form("new_criterion_form"):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            cr_code = st.text_input("Criterion Code", placeholder="e.g. CRIT-DIM-03").upper()
            cr_name = st.text_input("Criterion Name", placeholder="e.g. Tabletop Diagonal Squareness")
            cr_cat = st.selectbox("Category", [
                "Dimensional & Tolerances",
                "Material & Chemical",
                "Visual & Aesthetic",
                "Structural & Functional",
                "Packaging & Labeling",
                "Documentation & Compliance"
            ])
            cr_type = st.selectbox("Evaluation Method Type", [
                "Numeric Range",
                "Boolean Check",
                "Qualitative",
                "Required Document",
                "Test Result"
            ])
            cr_prod = st.selectbox("Applicable Product", [None] + products, format_func=lambda p: f"{p['sku']} — {p['name']}" if p else "Global (All Products)")

        with col_c2:
            cr_weight = st.number_input("Rule Weight", min_value=0.1, max_value=10.0, value=2.0, step=0.5)
            cr_sev = st.selectbox("Severity Classification", ["Critical", "Major", "Minor"])
            cr_mand = st.checkbox("Mandatory Requirement (Failure forces overall Fail)", value=True)
            cr_unit = st.text_input("Measurement Unit", placeholder="e.g. mm, %, mg/m3")
            cr_min = st.number_input("Minimum Allowed Value (If Numeric Range)", value=0.0, step=0.1)
            cr_max = st.number_input("Maximum Allowed Value (If Numeric Range)", value=0.0, step=0.1)
            cr_exp = st.text_input("Expected Value / Doc Category (If Document or Boolean)", placeholder="e.g. Chemical Safety & REACH")

        cr_desc = st.text_area("Engineering Acceptance Specification Description", placeholder="Detailed explanation of the standard, measuring tool, and acceptance limits...")

        if st.form_submit_button("Save New Quality Criterion", use_container_width=True):
            if not cr_code or not cr_name:
                st.error("Code and Name are required.")
            else:
                try:
                    create_quality_criterion(
                        criterion_code=cr_code,
                        name=cr_name,
                        category=cr_cat,
                        criterion_type=cr_type,
                        product_id=cr_prod["id"] if cr_prod else None,
                        description=cr_desc,
                        measurement_unit=cr_unit if cr_unit else None,
                        expected_value=cr_exp if cr_exp else None,
                        min_allowed=cr_min if cr_type == "Numeric Range" else None,
                        max_allowed=cr_max if cr_type == "Numeric Range" else None,
                        weight=cr_weight,
                        severity=cr_sev,
                        is_mandatory=cr_mand,
                        user_id=user["id"]
                    )
                    st.success(f"Criterion {cr_code} created successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating criterion: {e}")

# ----------------- TAB 3: AUDIT LOG -----------------
with tab_audit:
    st.markdown("#### Immutable System Audit Trail")
    st.caption("All user logins, document uploads, complaint status transitions, evaluations, and manager approvals are permanently logged.")

    logs = get_recent_audit_logs(limit=100)
    if logs:
        df_l = pd.DataFrame(logs)
        st.dataframe(
            df_l[["timestamp", "action", "entity_type", "entity_id", "username", "role", "details_json"]].rename(columns={
                "timestamp": "Timestamp",
                "action": "Action",
                "entity_type": "Entity",
                "entity_id": "Entity ID",
                "username": "User",
                "role": "Role",
                "details_json": "Details / Diff"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No audit logs found.")

# ----------------- TAB 4: DEMO RESET -----------------
with tab_env:
    st.markdown("#### Demo Environment Management")
    st.warning("⚠️ Resetting the demo environment will delete current records and re-seed the standard Code Space Techlab synthetic demo dataset (fictional products, IKEA specs, approved documents, criteria, and complaints).")

    if st.button("🔄 Reset & Re-Seed Synthetic Demo Data", type="primary", use_container_width=True):
        with st.spinner("Purging old records and re-seeding full demo suite..."):
            seed_all_demo_data(reset=True)
            st.success("Demo environment reset and re-seeded successfully!")
            st.rerun()
