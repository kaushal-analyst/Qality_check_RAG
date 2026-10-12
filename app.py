"""Streamlit Entrypoint & Authentication Portal for Code Space Techlab Quality AI."""
import streamlit as st
import sys
from pathlib import Path

# Ensure root is on path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.schema import init_db
from src.auth.service import authenticate_user
from src.ui_components import inject_custom_styles, render_header, render_sidebar_auth_status

st.set_page_config(
    page_title="Code Space Techlab — AI Quality Control",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database schema
init_db()
inject_custom_styles()
render_sidebar_auth_status()

# Session state initialization
if "authenticated_user" not in st.session_state:
    st.session_state["authenticated_user"] = None

render_header("AI Quality Control & Complaint Management System", "Modular RAG, Deterministic QA Rules, and CAPA Investigation Platform")

user = st.session_state.get("authenticated_user")

if not user:
    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.markdown(
            """
            ### Welcome to Code Space Techlab Quality Portal
            This enterprise application supports manufacturing supply operations for **IKEA**, commercial retailers, and direct customers.

            #### Core Capabilities:
            * **Product-Wise Knowledge Repository:** Structured specs, chemical declarations, and customer requirements.
            * **Hybrid RAG Investigation:** Semantic search (ChromaDB) + BM25 keyword matching (SQLite FTS5) with strict source citations.
            * **Configurable Evaluation Engine:** Deterministic rule calculations, tolerance checks, and mandatory failure overrides.
            * **Compliance & Risk Assessment:** Automated detection of missing documents, chemical compliance gaps, and safety hazards.
            * **Root-Cause Analysis & CAPA:** AI-assisted hypotheses across 8 engineering disciplines with verification tracking.
            * **Executive Dashboards & Downloads:** Live database analytics with PDF, Excel, and CSV export capabilities.
            """
        )

    with col2:
        st.markdown("### 🔐 User Login")
        with st.form("login_form"):
            username_input = st.text_input("Username", value="admin")
            password_input = st.text_input("Password", type="password", value="Quality2026!")
            submit_btn = st.form_submit_button("Sign In ➔", use_container_width=True)

            if submit_btn:
                auth_res = authenticate_user(username_input, password_input)
                if auth_res:
                    st.session_state["authenticated_user"] = auth_res
                    st.success(f"Welcome back, {auth_res['full_name']} ({auth_res['role']})!")
                    st.rerun()
                else:
                    st.error("Invalid username or password. Please verify credentials.")

        st.markdown("#### ⚡ 1-Click Demo Login")
        st.caption("Click any role button below to sign in instantly without typing credentials:")

        q_col1, q_col2 = st.columns(2)
        with q_col1:
            if st.button("👑 Admin (Full Access)", use_container_width=True):
                st.session_state["authenticated_user"] = authenticate_user("admin", "Quality2026!")
                st.rerun()
            if st.button("🔬 Quality Engineer", use_container_width=True):
                st.session_state["authenticated_user"] = authenticate_user("engineer1", "Quality2026!")
                st.rerun()
            if st.button("📊 Management Viewer", use_container_width=True):
                st.session_state["authenticated_user"] = authenticate_user("viewer1", "Quality2026!")
                st.rerun()
        with q_col2:
            if st.button("📋 Quality Manager", use_container_width=True):
                st.session_state["authenticated_user"] = authenticate_user("manager1", "Quality2026!")
                st.rerun()
            if st.button("🏢 Customer (IKEA Rep)", use_container_width=True):
                st.session_state["authenticated_user"] = authenticate_user("ikea_rep", "Quality2026!")
                st.rerun()

        st.markdown(
            """
            <div style="margin-top: 1rem; padding: 0.8rem; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;">
                <div style="font-weight: 700; font-size: 0.85rem; color: #0F172A; margin-bottom: 0.4rem;">🔑 Pre-Seeded User Credentials (Password: <code>Quality2026!</code>)</div>
                <table style="width: 100%; font-size: 0.8rem; border-collapse: collapse;">
                    <thead>
                        <tr style="border-bottom: 1px solid #CBD5E1; text-align: left; color: #475569;">
                            <th style="padding: 3px 6px;">Username</th>
                            <th style="padding: 3px 6px;">Role</th>
                            <th style="padding: 3px 6px;">Permissions / Scope</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr style="border-bottom: 1px solid #E2E8F0;">
                            <td style="padding: 4px 6px;"><b><code>admin</code></b></td>
                            <td style="padding: 4px 6px;"><span class="badge-info">Admin</span></td>
                            <td style="padding: 4px 6px;">Full system access, criteria, users, logs</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #E2E8F0;">
                            <td style="padding: 4px 6px;"><b><code>manager1</code></b></td>
                            <td style="padding: 4px 6px;"><span class="badge-pass">Quality Manager</span></td>
                            <td style="padding: 4px 6px;">Review & approve evaluations, close cases</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #E2E8F0;">
                            <td style="padding: 4px 6px;"><b><code>engineer1</code></b></td>
                            <td style="padding: 4px 6px;"><span class="badge-warn">Quality Engineer</span></td>
                            <td style="padding: 4px 6px;">Investigate, evaluate rules, CAPA actions</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #E2E8F0;">
                            <td style="padding: 4px 6px;"><b><code>ikea_rep</code></b></td>
                            <td style="padding: 4px 6px;"><span class="badge-info">Customer</span></td>
                            <td style="padding: 4px 6px;">Customer-isolated: IKEA cases only</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 6px;"><b><code>viewer1</code></b></td>
                            <td style="padding: 4px 6px;"><span class="badge-info">Viewer</span></td>
                            <td style="padding: 4px 6px;">Read-only dashboards and report exports</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            """,
            unsafe_allow_html=True
        )

else:
    st.success(f"✅ Authenticated as **{user['full_name']}** | Role: **{user['role']}**")

    # Enterprise module navigation cards
    st.markdown("### 🚀 Platform Modules")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            """
            <div class="kpi-card" style="border-left-color: #2563EB;">
                <div class="kpi-title">OPERATIONS</div>
                <div style="font-size: 1.2rem; font-weight: 700; margin: 0.5rem 0;">📊 Executive Dashboard</div>
                <div class="kpi-sub">KPIs, trend charts, risk funnels, and repeat defect Pareto distributions.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.page_link("pages/01_Dashboard.py", label="Open Dashboard", icon="📊", use_container_width=True)

    with c2:
        st.markdown(
            """
            <div class="kpi-card" style="border-left-color: #059669;">
                <div class="kpi-title">PRODUCT SPECS</div>
                <div style="font-size: 1.2rem; font-weight: 700; margin: 0.5rem 0;">📦 Product Registry</div>
                <div class="kpi-sub">SKU catalog, material declarations, and IKEA customer-specific standards.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.page_link("pages/02_Products.py", label="Open Products", icon="📦", use_container_width=True)

    with c3:
        st.markdown(
            """
            <div class="kpi-card" style="border-left-color: #D97706;">
                <div class="kpi-title">KNOWLEDGE REPO</div>
                <div style="font-size: 1.2rem; font-weight: 700; margin: 0.5rem 0;">📑 Documents & RAG</div>
                <div class="kpi-sub">Ingestion, chunk preview, vector embeddings, and semantic citations.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.page_link("pages/03_Documents.py", label="Open Documents", icon="📑", use_container_width=True)

    with c4:
        st.markdown(
            """
            <div class="kpi-card" style="border-left-color: #DC2626;">
                <div class="kpi-title">INVESTIGATION</div>
                <div style="font-size: 1.2rem; font-weight: 700; margin: 0.5rem 0;">📝 Complaints Lifecycle</div>
                <div class="kpi-sub">Intake, bulk CSV upload, attachments, triage, and audit trail.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.page_link("pages/04_Complaints.py", label="Open Complaints", icon="📝", use_container_width=True)

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
    c5, c6, c7, c8 = st.columns(4)

    with c5:
        st.markdown(
            """
            <div class="kpi-card" style="border-left-color: #7C3AED;">
                <div class="kpi-title">EVALUATION ENGINE</div>
                <div style="font-size: 1.2rem; font-weight: 700; margin: 0.5rem 0;">⚖️ Quality Evaluation</div>
                <div class="kpi-sub">Deterministic scoring, tolerance rules, and Quality Manager sign-off.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.page_link("pages/05_Quality_Evaluation.py", label="Open Evaluation", icon="⚖️", use_container_width=True)

    with c6:
        st.markdown(
            """
            <div class="kpi-card" style="border-left-color: #0891B2;">
                <div class="kpi-title">RISK & CAPA</div>
                <div style="font-size: 1.2rem; font-weight: 700; margin: 0.5rem 0;">🛡️ Compliance & Risk</div>
                <div class="kpi-sub">Missing document gaps, 4-tier risk matrix, root-causes, and CAPAs.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.page_link("pages/06_Compliance.py", label="Open Compliance", icon="🛡️", use_container_width=True)

    with c7:
        st.markdown(
            """
            <div class="kpi-card" style="border-left-color: #475569;">
                <div class="kpi-title">EXPORTS</div>
                <div style="font-size: 1.2rem; font-weight: 700; margin: 0.5rem 0;">📄 Reports & Downloads</div>
                <div class="kpi-sub">Investigation PDF reports, executive multi-tab Excel, and CSVs.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.page_link("pages/07_Reports.py", label="Open Reports", icon="📄", use_container_width=True)

    with c8:
        st.markdown(
            """
            <div class="kpi-card" style="border-left-color: #334155;">
                <div class="kpi-title">ADMINISTRATION</div>
                <div style="font-size: 1.2rem; font-weight: 700; margin: 0.5rem 0;">⚙️ Admin Settings</div>
                <div class="kpi-sub">User RBAC management, criteria builder, and system audit logs.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.page_link("pages/08_Admin_Settings.py", label="Open Settings", icon="⚙️", use_container_width=True)
