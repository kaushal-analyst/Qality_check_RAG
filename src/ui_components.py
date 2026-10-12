"""Reusable UI styling, branding, and role-aware navigation helpers for Streamlit."""
import streamlit as st
from typing import Optional, Dict, Any
from src.auth.permissions import has_permission

CUSTOM_CSS = """
<style>
    /* Clean Enterprise Palette */
    :root {
        --primary-navy: #0F172A;
        --accent-blue: #2563EB;
        --border-color: #E2E8F0;
        --bg-card: #FFFFFF;
        --text-muted: #64748B;
    }

    /* Top banner */
    .cst-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        padding: 1.2rem 1.6rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .cst-header h1 {
        margin: 0;
        font-size: 1.6rem;
        font-weight: 700;
        color: #F8FAFC !important;
    }
    .cst-header p {
        margin: 0.2rem 0 0 0;
        font-size: 0.85rem;
        color: #94A3B8 !important;
    }

    /* KPI Cards */
    .kpi-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1.1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border-left: 4px solid #2563EB;
    }
    .kpi-title {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        color: #64748B;
        letter-spacing: 0.05em;
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0F172A;
        margin: 0.2rem 0;
    }
    .kpi-sub {
        font-size: 0.75rem;
        color: #94A3B8;
    }

    /* Badge Pills */
    .badge-pass {
        background-color: #DCFCE7;
        color: #166534;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.75rem;
        display: inline-block;
    }
    .badge-fail {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.75rem;
        display: inline-block;
    }
    .badge-warn {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.75rem;
        display: inline-block;
    }
    .badge-info {
        background-color: #E0F2FE;
        color: #075985;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.75rem;
        display: inline-block;
    }

    /* Sidebar User Tag */
    .user-profile-badge {
        background: #F1F5F9;
        border-radius: 8px;
        padding: 0.8rem;
        border: 1px solid #E2E8F0;
        margin-bottom: 1rem;
    }
</style>
"""

def inject_custom_styles():
    """Injects custom enterprise CSS into Streamlit page."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

def render_header(title: str, subtitle: str = "Enterprise AI Quality Control & Traceability Platform"):
    """Renders consistent top brand header banner."""
    st.markdown(
        f"""
        <div class="cst-header">
            <h1>🛡️ Code Space Techlab — {title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_sidebar_auth_status():
    """Renders user authentication badge in Streamlit sidebar."""
    user = st.session_state.get("authenticated_user")
    with st.sidebar:
        if user:
            st.markdown(
                f"""
                <div class="user-profile-badge">
                    <div style="font-size: 0.75rem; color: #64748B; font-weight: 600;">ACTIVE SESSION</div>
                    <div style="font-weight: 700; color: #0F172A; font-size: 0.95rem;">{user.get('full_name')}</div>
                    <div style="font-size: 0.8rem; color: #2563EB; font-weight: 600;">Role: {user.get('role')}</div>
                    <div style="font-size: 0.75rem; color: #94A3B8;">{user.get('email')}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("🚪 Log Out", use_container_width=True):
                st.session_state["authenticated_user"] = None
                st.session_state.clear()
                st.rerun()
        else:
            st.info("🔒 Please log in on the Home page.")
            
        st.divider()
        st.markdown(
            """
            <div style="font-size: 0.75rem; color: #64748B;">
                <b>Code Space Techlab QA v1.0</b><br/>
                Hybrid RAG + Rule Engine<br/>
                ChromaDB & SQLite FTS5
            </div>
            """,
            unsafe_allow_html=True
        )

def require_auth(required_permission: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Enforces login and role permissions before rendering a page."""
    user = st.session_state.get("authenticated_user")
    if not user:
        st.warning("⚠️ Access Restricted: You must be logged in to view this page.")
        st.info("Please navigate to the main **Home** page to authenticate with your credentials.")
        st.stop()
        return None

    if required_permission:
        if not has_permission(user.get("role", ""), required_permission):
            st.error(f"⛔ Unauthorized: Your role ('{user.get('role')}') lacks permission '{required_permission}'.")
            st.stop()
            return None

    return user
