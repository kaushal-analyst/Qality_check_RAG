"""Reporting & Export Center: Downloadable PDFs, Multi-Tab Excel, and CSVs."""
import streamlit as st
import json
from src.complaint_management.service import list_complaints, get_complaint_by_id
from src.reporting.pdf_generator import generate_complaint_investigation_pdf
from src.reporting.excel_generator import generate_management_dashboard_excel, generate_complaints_csv
from src.database.connection import get_db
from src.quality_engine.root_cause import get_complaint_hypotheses
from src.complaint_management.capa import list_capa_tasks
from src.ui_components import inject_custom_styles, render_header, render_sidebar_auth_status, require_auth

st.set_page_config(page_title="Reports & Exports — Quality AI", page_icon="📄", layout="wide")
inject_custom_styles()
render_sidebar_auth_status()
user = require_auth("export_reports")

render_header("Reporting & Download Center", "Generate Audit-Ready Investigation PDFs, Executive Multi-Tab Workbooks, and CSV Exports")

col_pdf, col_excel = st.columns(2)

# ----------------- SECTION 1: INVESTIGATION PDF REPORTS -----------------
with col_pdf:
    st.markdown("### 📄 Individual Complaint Investigation PDF")
    st.caption("Generate an official, audit-ready engineering report with defect description, deterministic evaluation findings, citations, risk matrix, CAPA actions, and manager sign-off.")

    complaints = list_complaints()
    if not complaints:
        st.info("No complaints found.")
    else:
        sel_c_report = st.selectbox(
            "Select Complaint Case for PDF Generation",
            complaints,
            format_func=lambda c: f"{c['complaint_id']} — {c['product_sku']} ({c['category']})"
        )

        full_c = get_complaint_by_id(sel_c_report["id"])

        # Fetch evaluation, criteria results, risk, hypotheses, and CAPAs
        with get_db() as conn:
            eval_row = conn.execute(
                "SELECT * FROM evaluations WHERE complaint_id = ? ORDER BY created_at DESC LIMIT 1",
                (full_c["id"],)
            ).fetchone()
            
            crit_results = []
            if eval_row:
                crit_rows = conn.execute(
                    "SELECT * FROM evaluation_criteria_results WHERE evaluation_id = ?",
                    (eval_row["id"],)
                ).fetchall()
                crit_results = [dict(cr) for cr in crit_rows]

            risk_row = conn.execute(
                "SELECT * FROM risk_assessments WHERE complaint_id = ? ORDER BY created_at DESC LIMIT 1",
                (full_c["id"],)
            ).fetchone()

        hyps = get_complaint_hypotheses(full_c["id"])
        capas = list_capa_tasks(complaint_id=full_c["id"])

        eval_dict = dict(eval_row) if eval_row else None
        risk_dict = dict(risk_row) if risk_row else None

        if st.button("🔨 Compile Official PDF Report", use_container_width=True):
            with st.spinner("Compiling ReportLab PDF document..."):
                pdf_data = generate_complaint_investigation_pdf(
                    complaint=full_c,
                    evaluation=eval_dict,
                    criteria_results=crit_results,
                    risk=risk_dict,
                    hypotheses=hyps,
                    capas=capas
                )
                st.session_state[f"pdf_{full_c['id']}"] = pdf_data
                st.success("PDF compiled successfully!")

        if f"pdf_{full_c['id']}" in st.session_state:
            st.download_button(
                label=f"⬇️ Download Investigation PDF ({full_c['complaint_id']}.pdf)",
                data=st.session_state[f"pdf_{full_c['id']}"],
                file_name=f"CodeSpaceTechlab_Quality_Report_{full_c['complaint_id']}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

# ----------------- SECTION 2: EXCEL & CSV WORKBOOKS -----------------
with col_excel:
    st.markdown("### 📊 Executive Multi-Tab Excel Workbook")
    st.caption("Consolidated spreadsheet containing formatted tables for Complaints, Evaluations, CAPA Action Items, and Product Catalog.")

    if st.button("🔨 Generate Executive Excel Workbook", use_container_width=True):
        with st.spinner("Compiling openpyxl workbook with styled headers..."):
            excel_data = generate_management_dashboard_excel()
            st.session_state["excel_mgmt"] = excel_data
            st.success("Excel workbook generated!")

    if "excel_mgmt" in st.session_state:
        st.download_button(
            label="⬇️ Download Executive Management Excel (.xlsx)",
            data=st.session_state["excel_mgmt"],
            file_name="CodeSpaceTechlab_Management_Quality_Summary.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    st.divider()
    st.markdown("### 📑 Raw Data CSV Exports")
    st.caption("Direct database export for ERP or business intelligence ingestion.")

    csv_data = generate_complaints_csv()
    st.download_button(
        label="⬇️ Download Full Complaints Table (.csv)",
        data=csv_data,
        file_name="complaints_export.csv",
        mime="text/csv",
        use_container_width=True
    )
