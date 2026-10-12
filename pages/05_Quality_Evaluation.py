"""Quality Evaluation Engine: Deterministic Checks, RAG Grounding, and Manager Sign-Off."""
import streamlit as st
import pandas as pd
import json
from src.complaint_management.service import list_complaints, get_complaint_by_id
from src.quality_engine.rule_evaluator import evaluate_complaint
from src.quality_engine.approval import review_evaluation
from src.database.connection import get_db
from src.ui_components import inject_custom_styles, render_header, render_sidebar_auth_status, require_auth

st.set_page_config(page_title="Quality Evaluation — Quality AI", page_icon="⚖️", layout="wide")
inject_custom_styles()
render_sidebar_auth_status()
user = require_auth("evaluate_complaints")

render_header("Configurable Quality Evaluation Engine", "Deterministic Criteria Checks, Explainable Scoring, and Quality Manager Sign-Off")

complaints = list_complaints()

if not complaints:
    st.info("No complaints found in the system.")
    st.stop()

# Select case
sel_case = st.selectbox(
    "Select Complaint Case to Evaluate",
    complaints,
    format_func=lambda c: f"{c['complaint_id']} — {c['product_sku']} ({c['category']}) | Status: [{c['current_status']}]"
)

full_case = get_complaint_by_id(sel_case["id"])

# Case summary card
st.markdown(
    f"""
    <div class="kpi-card" style="margin-bottom: 1rem;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <span class="kpi-title">INSPECTION TARGET: {full_case['sku']} — {full_case['product_name']}</span>
                <h3 style="margin: 0.2rem 0; color: #0F172A;">{full_case['complaint_id']} (Batch: {full_case.get('order_batch_number', 'N/A')})</h3>
                <div style="font-size: 0.85rem; color: #475569;">Customer: <b>{full_case.get('customer_name', 'Direct')}</b> | Severity: <b>{full_case['severity']}</b></div>
            </div>
            <div style="text-align: right;">
                <span class="badge-info">Status: {full_case['current_status']}</span>
            </div>
        </div>
        <div style="margin-top: 0.8rem; font-size: 0.9rem; color: #334155; background: #F8FAFC; padding: 0.6rem; border-radius: 6px;">
            <b>Reported Defect:</b> {full_case['description']}
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Fetch latest existing evaluation if available
with get_db() as conn:
    latest_eval = conn.execute(
        """
        SELECT * FROM evaluations
        WHERE complaint_id = ?
        ORDER BY created_at DESC LIMIT 1
        """,
        (full_case["id"],)
    ).fetchone()

col_btn, col_msg = st.columns([1.2, 3])
with col_btn:
    run_eval_clicked = st.button("⚡ Run Quality Evaluation Engine", use_container_width=True)

if run_eval_clicked:
    with st.spinner("Retrieving approved specifications, executing deterministic rules, and mapping evidence..."):
        eval_run = evaluate_complaint(full_case["id"], user_id=user["id"])
        st.success(f"Evaluation Run {eval_run['evaluation_id']} completed successfully!")
        st.rerun()

# Display Evaluation Results if exists
if latest_eval:
    eval_dict = dict(latest_eval)
    
    st.markdown("### 📊 Evaluation Findings & Explainable Score")
    
    # KPI Row for evaluation
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        score_val = eval_dict.get("quality_score", 0.0)
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left-color: {'#10B981' if eval_dict['scoring_status'] == 'Pass' else '#EF4444'};">
                <div class="kpi-title">Quality Score</div>
                <div class="kpi-value">{score_val}%</div>
                <div class="kpi-sub">Weighted rule average</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m2:
        status_color = "#10B981" if eval_dict['scoring_status'] == "Pass" else ("#F59E0B" if eval_dict['scoring_status'] == "Warning" else "#EF4444")
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left-color: {status_color};">
                <div class="kpi-title">Scoring Outcome</div>
                <div class="kpi-value">{eval_dict['scoring_status']}</div>
                <div class="kpi-sub">Mandatory failures: {eval_dict.get('mandatory_failures_count', 0)}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m3:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left-color: #6366F1;">
                <div class="kpi-title">Evidence Completeness</div>
                <div class="kpi-value">{eval_dict.get('evidence_completeness_pct', 0.0)}%</div>
                <div class="kpi-sub">Evaluated vs missing</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m4:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left-color: #0F172A;">
                <div class="kpi-title">Manager Sign-Off</div>
                <div class="kpi-value" style="font-size: 1.3rem;">{eval_dict.get('manager_approval_status', 'Pending')}</div>
                <div class="kpi-sub">{eval_dict.get('manager_notes') or 'Awaiting review'}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Explanation Banner
    st.info(f"**Evaluation Summary:** {eval_dict.get('overall_summary')}")

    # Criterion-Level Table
    with get_db() as conn:
        crit_rows = conn.execute(
            """
            SELECT * FROM evaluation_criteria_results
            WHERE evaluation_id = ?
            ORDER BY is_mandatory DESC, id ASC
            """,
            (eval_dict["id"],)
        ).fetchall()

    if crit_rows:
        st.markdown("#### 🎯 Criterion-by-Criterion Verification Breakdown")
        crit_data = []
        for cr in crit_rows:
            r = dict(cr)
            crit_data.append({
                "Mandatory": "⚠️ YES" if r["is_mandatory"] else "No",
                "Code": r["criterion_code"],
                "Criterion Name": r["criterion_name"],
                "Observed Value": r.get("observed_value", "N/A"),
                "Expected / Limit": r.get("expected_value", "N/A"),
                "Outcome": r["outcome"],
                "Score": f"{r['score_awarded']}/{r['max_score']}",
                "Finding Notes": r.get("finding_notes", "")
            })

        st.dataframe(pd.DataFrame(crit_data), use_container_width=True, hide_index=True)

    # ----------------- QUALITY MANAGER SIGN-OFF MODULE -----------------
    st.divider()
    st.markdown("### ✍️ Quality Manager Review & Formal Sign-Off")

    if user.get("role") not in ("Admin", "Quality Manager"):
        st.warning("🔒 Only authorized Quality Managers can approve, reject, or escalate evaluation findings.")
    else:
        with st.form("manager_signoff_form"):
            col_dec1, col_dec2 = st.columns([1, 2])
            with col_dec1:
                decision = st.selectbox("Manager Decision", ["Approved", "Rejected", "Escalated"])
                close_box = st.checkbox("Close Complaint upon Approval", value=False)
            with col_dec2:
                notes = st.text_area("Manager Review Notes & Action Authorization", placeholder="Document verification observations, engineering signoff rationale, or escalation instructions...")

            submit_sign = st.form_submit_button("Formalize Sign-Off & Record in Audit Trail", use_container_width=True)

            if submit_sign:
                if not notes.strip():
                    st.error("Manager review notes are required for sign-off.")
                else:
                    review_evaluation(
                        evaluation_db_id=eval_dict["id"],
                        manager_decision=decision,
                        manager_notes=notes,
                        user_id=user["id"],
                        close_complaint=close_box
                    )
                    st.success(f"Evaluation {eval_dict['evaluation_id']} signed off with decision: {decision}!")
                    st.rerun()

else:
    st.info("No evaluation has been run on this complaint yet. Click 'Run Quality Evaluation Engine' above to begin.")
