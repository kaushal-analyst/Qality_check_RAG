"""Operational and Executive Quality Dashboard with Plotly Visualizations."""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.database.connection import get_db
from src.ui_components import inject_custom_styles, render_header, render_sidebar_auth_status, require_auth

st.set_page_config(page_title="Executive Dashboard — Quality AI", page_icon="📊", layout="wide")
inject_custom_styles()
render_sidebar_auth_status()
user = require_auth("view_dashboard")

render_header("Executive & Operational Quality Dashboard", "Real-Time Manufacturing Metrics, Risk Indicators, and Defect Trends")

# ----------------- Database Queries & Filters -----------------
with get_db() as conn:
    products = conn.execute("SELECT id, name, sku FROM products ORDER BY name ASC").fetchall()
    customers = conn.execute("SELECT id, name, code FROM customers ORDER BY name ASC").fetchall()

# Sidebar Filters
st.sidebar.markdown("### 🔍 Dashboard Filters")
selected_product = st.sidebar.selectbox("Filter Product", ["All Products"] + [f"{p['sku']} — {p['name']}" for p in products])
selected_customer = st.sidebar.selectbox("Filter Customer", ["All Customers"] + [f"{c['code']} — {c['name']}" for c in customers])
selected_severity = st.sidebar.selectbox("Filter Severity", ["All Severities", "Critical", "High", "Medium", "Low"])
selected_status = st.sidebar.selectbox("Filter Status", ["All Statuses", "Submitted", "Triaged", "Under Investigation", "Manager Review", "Approved", "Closed"])

# Build SQL Query with Filters
base_query = """
    SELECT c.*, p.name as product_name, p.sku as product_sku,
           cust.name as customer_name, cust.code as customer_code,
           e.quality_score, e.scoring_status, e.manager_approval_status,
           r.overall_risk_level, r.risk_score
    FROM complaints c
    JOIN products p ON c.product_id = p.id
    LEFT JOIN customers cust ON c.customer_id = cust.id
    LEFT JOIN evaluations e ON e.complaint_id = c.id
    LEFT JOIN risk_assessments r ON r.complaint_id = c.id
    WHERE 1=1
"""
params = []

# Enforce Customer Data Isolation if user is an external Customer!
if user.get("role") == "Customer" and user.get("customer_id"):
    base_query += " AND c.customer_id = ?"
    params.append(user["customer_id"])

if selected_product != "All Products":
    sku_filter = selected_product.split(" — ")[0]
    base_query += " AND p.sku = ?"
    params.append(sku_filter)

if selected_customer != "All Customers":
    code_filter = selected_customer.split(" — ")[0]
    base_query += " AND cust.code = ?"
    params.append(code_filter)

if selected_severity != "All Severities":
    base_query += " AND c.severity = ?"
    params.append(selected_severity)

if selected_status != "All Statuses":
    base_query += " AND c.current_status = ?"
    params.append(selected_status)

base_query += " ORDER BY c.created_at DESC"

with get_db() as conn:
    df = pd.read_sql_query(base_query, conn, params=params)

# ----------------- KPI Cards Row -----------------
total_complaints = len(df)
open_complaints = len(df[df["current_status"].isin(["Submitted", "Triaged", "Under Investigation", "Manager Review"])]) if not df.empty else 0
high_critical_risk = len(df[df["severity"].isin(["Critical", "High"])]) if not df.empty else 0
evaluated_count = len(df[df["quality_score"].notna()]) if not df.empty else 0
evaluated_pct = round((evaluated_count / total_complaints * 100), 1) if total_complaints > 0 else 0.0

# Average quality score across evaluated complaints
avg_score = round(df["quality_score"].dropna().mean(), 1) if not df.empty and not df["quality_score"].dropna().empty else "N/A"

# Repeat complaints calculation (same product and category count > 1)
repeat_count = 0
if not df.empty:
    counts = df.groupby(["product_sku", "category"]).size()
    repeat_count = int((counts[counts > 1]).sum())

k1, k2, k3, k4, k5, k6 = st.columns(6)

with k1:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">Total Cases</div>
            <div class="kpi-value">{total_complaints}</div>
            <div class="kpi-sub">In database</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with k2:
    st.markdown(
        f"""
        <div class="kpi-card" style="border-left-color: #F59E0B;">
            <div class="kpi-title">Active Open</div>
            <div class="kpi-value">{open_complaints}</div>
            <div class="kpi-sub">Unresolved cases</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with k3:
    st.markdown(
        f"""
        <div class="kpi-card" style="border-left-color: #EF4444;">
            <div class="kpi-title">High / Critical</div>
            <div class="kpi-value">{high_critical_risk}</div>
            <div class="kpi-sub">Require escalation</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with k4:
    st.markdown(
        f"""
        <div class="kpi-card" style="border-left-color: #10B981;">
            <div class="kpi-title">Evaluated</div>
            <div class="kpi-value">{evaluated_pct}%</div>
            <div class="kpi-sub">{evaluated_count} of {total_complaints} runs</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with k5:
    st.markdown(
        f"""
        <div class="kpi-card" style="border-left-color: #6366F1;">
            <div class="kpi-title">Avg Quality Score</div>
            <div class="kpi-value">{avg_score}%</div>
            <div class="kpi-sub">On active criteria</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with k6:
    st.markdown(
        f"""
        <div class="kpi-card" style="border-left-color: #EC4899;">
            <div class="kpi-title">Repeat Defects</div>
            <div class="kpi-value">{repeat_count}</div>
            <div class="kpi-sub">Recurrent incidents</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

if df.empty:
    st.info("No complaint records match the current filter criteria.")
    st.stop()

# ----------------- Visualizations Row 1 -----------------
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.markdown("#### 📦 Complaints by Product & SKU")
    prod_counts = df.groupby(["product_sku", "product_name"]).size().reset_index(name="count")
    fig_prod = px.bar(
        prod_counts,
        x="product_sku",
        y="count",
        color="product_sku",
        hover_data=["product_name"],
        labels={"product_sku": "SKU", "count": "Complaint Volume"},
        color_discrete_sequence=px.colors.qualitative.Prism
    )
    fig_prod.update_layout(showlegend=False, margin=dict(l=20, r=20, t=20, b=20), height=320)
    st.plotly_chart(fig_prod, use_container_width=True)

with col_chart2:
    st.markdown("#### 🎯 Defect Category Breakdown")
    cat_counts = df["category"].value_counts().reset_index()
    cat_counts.columns = ["Category", "Count"]
    fig_cat = px.pie(
        cat_counts,
        names="Category",
        values="Count",
        hole=0.45,
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    fig_cat.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=320)
    st.plotly_chart(fig_cat, use_container_width=True)

# ----------------- Visualizations Row 2 -----------------
col_chart3, col_chart4 = st.columns(2)

with col_chart3:
    st.markdown("#### 🚦 Severity vs Current Lifecycle Status")
    status_order = ["Submitted", "Triaged", "Under Investigation", "Manager Review", "Approved", "Closed"]
    fig_status = px.histogram(
        df,
        x="current_status",
        color="severity",
        category_orders={"current_status": status_order},
        color_discrete_map={"Low": "#10B981", "Medium": "#F59E0B", "High": "#F97316", "Critical": "#EF4444"},
        labels={"current_status": "Lifecycle Stage", "count": "Cases"}
    )
    fig_status.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=320)
    st.plotly_chart(fig_status, use_container_width=True)

with col_chart4:
    st.markdown("#### 🏢 Customer & Retailer Distribution")
    cust_df = df["customer_name"].fillna("Direct/Unknown").value_counts().reset_index()
    cust_df.columns = ["Customer", "Complaints"]
    fig_cust = px.bar(
        cust_df,
        x="Complaints",
        y="Customer",
        orientation="h",
        color="Customer",
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    fig_cust.update_layout(showlegend=False, margin=dict(l=20, r=20, t=20, b=20), height=320)
    st.plotly_chart(fig_cust, use_container_width=True)

# ----------------- Interactive Underlying Records Table -----------------
st.markdown("### 📋 Underlying Complaint Records")
display_cols = [
    "complaint_id", "product_sku", "customer_name", "category",
    "severity", "current_status", "quantity_affected", "quality_score",
    "scoring_status", "date_received"
]
st.dataframe(
    df[display_cols].rename(columns={
        "complaint_id": "Case ID",
        "product_sku": "SKU",
        "customer_name": "Customer",
        "category": "Defect Category",
        "severity": "Severity",
        "current_status": "Status",
        "quantity_affected": "Qty",
        "quality_score": "Score (%)",
        "scoring_status": "Outcome",
        "date_received": "Received"
    }),
    use_container_width=True,
    hide_index=True
)
