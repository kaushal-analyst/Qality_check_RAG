"""Compliance Evidence, Risk Matrix, Root-Cause Hypotheses & CAPA Management."""
import streamlit as st
import pandas as pd
from src.products.service import list_products
from src.compliance.gap_analyzer import analyze_product_compliance_gaps
from src.complaint_management.service import list_complaints, get_complaint_by_id
from src.quality_engine.root_cause import get_complaint_hypotheses, update_hypothesis_status
from src.complaint_management.capa import list_capa_tasks, create_capa_task, update_capa_task_status
from src.database.connection import get_db
from src.ui_components import inject_custom_styles, render_header, render_sidebar_auth_status, require_auth

st.set_page_config(page_title="Compliance & Risk — Quality AI", page_icon="🛡️", layout="wide")
inject_custom_styles()
render_sidebar_auth_status()
user = require_auth()

render_header("Compliance Gaps, Risk Assessment & CAPA Tracking", "Missing Document Detection, 4-Tier Risk Matrix, Root-Cause Hypotheses, and CAPA Verification")

tab_gaps, tab_risk, tab_rca, tab_capa = st.tabs(["📑 Document Gap Analysis", "🚦 4-Tier Risk Matrix", "🔍 Root-Cause Hypotheses", "🛠️ Corrective & Preventive (CAPA)"])

products = list_products()
complaints = list_complaints()

# ----------------- TAB 1: DOCUMENT GAP ANALYSIS -----------------
with tab_gaps:
    st.markdown("#### Automated Specification & Chemical Compliance Gap Audit")
    if not products:
        st.info("No products registered.")
    else:
        sel_prod = st.selectbox("Select Product to Audit Compliance Gaps", products, format_func=lambda p: f"{p['sku']} — {p['name']}")
        
        gaps = analyze_product_compliance_gaps(sel_prod["id"])
        
        g_c1, g_c2, g_c3 = st.columns(3)
        with g_c1:
            st.markdown(
                f"""
                <div class="kpi-card" style="border-left-color: {'#10B981' if not gaps['requires_manager_review'] else '#EF4444'};">
                    <div class="kpi-title">Compliance Status</div>
                    <div style="font-size: 1.1rem; font-weight: 700; margin-top: 0.3rem;">{gaps['overall_status']}</div>
                    <div class="kpi-sub">{gaps['approved_documents_count']} of {gaps['total_documents']} documents approved</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with g_c2:
            st.markdown(
                f"""
                <div class="kpi-card" style="border-left-color: {'#10B981' if not gaps['chemical_documentation_gap'] else '#EF4444'};">
                    <div class="kpi-title">Chemical & REACH Status</div>
                    <div style="font-size: 1.1rem; font-weight: 700; margin-top: 0.3rem;">{'✅ Approved Declaration' if not gaps['chemical_documentation_gap'] else '⚠️ Missing REACH Doc'}</div>
                    <div class="kpi-sub">SVHC and formaldehyde limits</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with g_c3:
            st.markdown(
                f"""
                <div class="kpi-card" style="border-left-color: {'#10B981' if not gaps['expired_documents'] else '#F59E0B'};">
                    <div class="kpi-title">Expired Documents</div>
                    <div class="kpi-value">{len(gaps['expired_documents'])}</div>
                    <div class="kpi-sub">Outdated revisions requiring renewal</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
        
        if gaps["missing_categories"]:
            st.error(f"⚠️ **Missing Mandatory Document Categories for {sel_prod['sku']}:**")
            for cat in gaps["missing_categories"]:
                st.markdown(f"• **`{cat}`** — Not found in approved repository. Upload required.")
        else:
            st.success(f"✅ All mandatory document categories are present for {sel_prod['sku']}.")

        if gaps["expired_documents"]:
            st.warning("⚠️ **Expired Documents Identified:**")
            for exp in gaps["expired_documents"]:
                st.markdown(f"• `{exp['document_id']}` ({exp['title']}) expired on {exp['expiry_date']}.")

# ----------------- TAB 2: RISK MATRIX -----------------
with tab_risk:
    st.markdown("#### Complaint Risk Assessment Matrix")
    st.caption("Objective risk scoring: Severity (1-4) × [Frequency (1-4) + Units Affected (1-4)] / 2. Safety hazards trigger automatic Critical escalation.")

    with get_db() as conn:
        risk_df = pd.read_sql_query(
            """
            SELECT r.*, c.complaint_id as case_id, c.sku, c.category, c.current_status,
                   p.name as product_name
            FROM risk_assessments r
            JOIN complaints c ON r.complaint_id = c.id
            JOIN products p ON c.product_id = p.id
            ORDER BY r.risk_score DESC
            """,
            conn
        )

    if risk_df.empty:
        st.info("No risk assessments generated yet. Run evaluations from the 'Quality Evaluation' page to populate.")
    else:
        st.dataframe(
            risk_df[["case_id", "sku", "category", "severity_level", "overall_risk_level", "risk_score", "safety_flag", "escalation_required", "rationale"]].rename(columns={
                "case_id": "Case",
                "sku": "SKU",
                "category": "Category",
                "severity_level": "Severity",
                "overall_risk_level": "Risk Level",
                "risk_score": "Score",
                "safety_flag": "Safety Hazard",
                "escalation_required": "Escalation",
                "rationale": "Assessment Rationale"
            }),
            use_container_width=True,
            hide_index=True
        )

# ----------------- TAB 3: ROOT CAUSE HYPOTHESES -----------------
with tab_rca:
    st.markdown("#### AI-Assisted Root Cause Hypotheses Across 8 Disciplines")
    if not complaints:
        st.info("No complaints found.")
    else:
        sel_rca_c = st.selectbox(
            "Select Case to View Hypotheses",
            complaints,
            format_func=lambda c: f"{c['complaint_id']} — {c['product_sku']} ({c['category']})",
            key="rca_c_sel"
        )
        hyps = get_complaint_hypotheses(sel_rca_c["id"])

        if not hyps:
            st.info("No hypotheses recorded yet for this complaint. Hypotheses are generated during evaluation runs.")
        else:
            for h in hyps:
                with st.expander(f"🔬 [{h['category']}] {h['hypothesis_statement']} — Status: {h['verification_status']} (Likelihood: {h.get('likelihood', 'Medium')})", expanded=True):
                    st.markdown(f"**Supporting Evidence:** {h.get('supporting_evidence', 'N/A')}")
                    st.markdown(f"**Contradicting Evidence:** {h.get('contradicting_evidence', 'N/A')}")
                    st.markdown(f"**Missing Information:** {h.get('missing_information', 'N/A')}")
                    
                    if user.get("role") in ("Admin", "Quality Manager", "Quality Engineer"):
                        col_v1, col_v2 = st.columns([1, 2])
                        with col_v1:
                            new_v_stat = st.selectbox("Update Status", ["Proposed", "Under Investigation", "Confirmed", "Rejected"], index=["Proposed", "Under Investigation", "Confirmed", "Rejected"].index(h["verification_status"]), key=f"h_stat_{h['id']}")
                        with col_v2:
                            if st.button("Save Hypothesis Status", key=f"h_btn_{h['id']}"):
                                update_hypothesis_status(h["id"], new_v_stat)
                                st.success("Status updated.")
                                st.rerun()

# ----------------- TAB 4: CAPA MANAGEMENT -----------------
with tab_capa:
    st.markdown("#### Corrective & Preventive Actions (CAPA)")
    capa_list = list_capa_tasks()

    if capa_list:
        df_capa = pd.DataFrame(capa_list)
        st.dataframe(
            df_capa[["complaint_code", "sku", "capa_type", "title", "department", "priority", "status", "due_date", "effectiveness_verification"]].rename(columns={
                "complaint_code": "Case",
                "sku": "SKU",
                "capa_type": "Type",
                "title": "Title",
                "department": "Department",
                "priority": "Priority",
                "status": "Status",
                "due_date": "Due",
                "effectiveness_verification": "Verification of Effectiveness"
            }),
            use_container_width=True,
            hide_index=True
        )

        st.divider()
        st.markdown("##### ✏️ Update CAPA Progress & Effectiveness Verification")
        sel_capa_item = st.selectbox("Select Action Item", capa_list, format_func=lambda cp: f"[{cp['capa_type']}] {cp['title']} — {cp['status']} ({cp['complaint_code']})")

        with st.form("update_capa_form"):
            c_stat = st.selectbox("Progress Status", ["Open", "In Progress", "Implemented", "Verified Effective", "Closed"], index=["Open", "In Progress", "Implemented", "Verified Effective", "Closed"].index(sel_capa_item["status"]))
            c_notes = st.text_area("Implementation Outcome Notes", value=sel_capa_item.get("outcome_notes") or "")
            c_eff = st.text_area("Verification of Effectiveness (Required for signoff)", value=sel_capa_item.get("effectiveness_verification") or "")
            
            if st.form_submit_button("Update CAPA Task", use_container_width=True):
                update_capa_task_status(
                    capa_id=sel_capa_item["id"],
                    status=c_stat,
                    outcome_notes=c_notes,
                    effectiveness_verification=c_eff,
                    user_id=user["id"]
                )
                st.success("CAPA updated successfully!")
                st.rerun()

    # Manual CAPA Creation Form
    if complaints and user.get("role") in ("Admin", "Quality Manager", "Quality Engineer"):
        st.divider()
        st.markdown("##### ➕ Create New CAPA Task")
        with st.form("create_capa_form"):
            col_cp1, col_cp2 = st.columns(2)
            with col_cp1:
                cp_c_sel = st.selectbox("Complaint Case", complaints, format_func=lambda c: f"{c['complaint_id']} — {c['product_sku']}")
                cp_type = st.selectbox("CAPA Type", ["Containment", "Corrective", "Preventive"])
                cp_title = st.text_input("Action Title", placeholder="e.g. Quarantine incoming timber pallet")
                cp_dept = st.selectbox("Responsible Department", ["Quality Assurance", "Manufacturing Operations", "Warehouse & Logistics", "Supplier Management", "Packaging"])
            with col_cp2:
                cp_prio = st.selectbox("Priority", ["Critical", "High", "Medium", "Low"])
                cp_due = st.date_input("Due Date")
                cp_desc = st.text_area("Action Description & Methodology", placeholder="Detail operational containment or permanent engineering fix...")

            if st.form_submit_button("Create Action Task", use_container_width=True):
                if not cp_title.strip() or not cp_desc.strip():
                    st.error("Title and description are required.")
                else:
                    create_capa_task(
                        complaint_id=cp_c_sel["id"],
                        capa_type=cp_type,
                        title=cp_title,
                        description=cp_desc,
                        department=cp_dept,
                        priority=cp_prio,
                        due_date=str(cp_due),
                        user_id=user["id"]
                    )
                    st.success("CAPA Task created successfully!")
                    st.rerun()
