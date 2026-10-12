"""Product Registry & Customer-Specific Standards Management."""
import streamlit as st
import pandas as pd
from src.database.connection import get_db
from src.products.service import (
    list_products, get_product_by_id, create_product, update_product,
    list_customers, set_customer_product_spec, get_specs_for_product_and_customer
)
from src.document_processing.service import list_documents
from src.ui_components import inject_custom_styles, render_header, render_sidebar_auth_status, require_auth

st.set_page_config(page_title="Product Registry — Quality AI", page_icon="📦", layout="wide")
inject_custom_styles()
render_sidebar_auth_status()
user = require_auth()

render_header("Product Registry & Customer Specifications", "Catalog Management, Material BOMs, and Customer-Specific Standards")

tab_browse, tab_specs, tab_create = st.tabs(["📋 Product Catalog", "🏷️ Customer-Specific Specs", "➕ New Product Registration"])

# ----------------- TAB 1: BROWSE PRODUCTS -----------------
with tab_browse:
    c_search, c_filter = st.columns([2, 1])
    with c_search:
        search_query = st.text_input("Search by SKU, Name or Category", placeholder="e.g. NDT-800 or Dining")
    with c_filter:
        status_filter = st.selectbox("Status", ["All", "Active", "Archived"])

    products_list = list_products(status_filter=status_filter, search=search_query)

    if not products_list:
        st.info("No products match the search criteria.")
    else:
        for prod in products_list:
            with st.expander(f"📦 {prod['sku']} — {prod['name']} (Rev {prod['revision']})", expanded=False):
                col_info1, col_info2 = st.columns([1.5, 1])
                with col_info1:
                    st.markdown(f"**Category:** {prod['category']} | **Status:** `{prod['status']}`")
                    st.markdown(f"**Target Market:** {prod.get('target_market', 'N/A')}")
                    st.markdown(f"**Batch / Lot Prefix:** `{prod.get('batch_prefix', 'N/A')}`")
                    st.markdown(f"**Description:** {prod.get('description', 'N/A')}")
                    st.markdown(f"**Materials / BOM Summary:** {prod.get('materials_summary', 'N/A')}")
                with col_info2:
                    # Ingested documents count
                    docs = list_documents(product_id=prod["id"])
                    st.markdown(f"**Active Knowledge Documents:** {len(docs)}")
                    for d in docs:
                        st.markdown(f"• `{d['document_id']}` — {d['title']} (Rev {d['revision']})")

                # Edit form if user has permission
                if user.get("role") in ("Admin", "Quality Manager"):
                    st.divider()
                    st.markdown("##### ✏️ Edit Product Specifications")
                    with st.form(f"edit_form_{prod['id']}"):
                        e_name = st.text_input("Name", value=prod["name"])
                        e_cat = st.text_input("Category", value=prod["category"])
                        e_desc = st.text_area("Description", value=prod.get("description", ""))
                        e_mat = st.text_area("Materials BOM Summary", value=prod.get("materials_summary", ""))
                        e_rev = st.text_input("Revision", value=prod.get("revision", "1.0"))
                        e_stat = st.selectbox("Status", ["Active", "Archived"], index=0 if prod["status"] == "Active" else 1)
                        if st.form_submit_button("Save Changes"):
                            update_product(
                                product_id=prod["id"],
                                name=e_name,
                                category=e_cat,
                                description=e_desc,
                                materials_summary=e_mat,
                                batch_prefix=prod.get("batch_prefix"),
                                target_market=prod.get("target_market"),
                                revision=e_rev,
                                status=e_stat,
                                user_id=user["id"]
                            )
                            st.success("Product updated successfully!")
                            st.rerun()

# ----------------- TAB 2: CUSTOMER-SPECIFIC SPECS -----------------
with tab_specs:
    st.markdown("#### Configured Customer Requirements (e.g. IKEA Flat-Pack, Target ANSI/BIFMA)")
    all_products = list_products()
    all_customers = list_customers()

    if all_products and all_customers:
        p_sel = st.selectbox("Select Product to View Standards", all_products, format_func=lambda p: f"{p['sku']} — {p['name']}")
        
        specs = get_specs_for_product_and_customer(p_sel["id"])
        if specs:
            for s in specs:
                st.info(
                    f"**Customer:** {s['customer_name']} ({s['customer_code']} - {s['customer_type']})\n\n"
                    f"**Standard Code:** `{s['spec_code']}`\n\n"
                    f"**Requirements:** {s['specific_requirements']}\n\n"
                    f"**Notes:** {s.get('notes', 'None')}"
                )
        else:
            st.warning("No custom customer specifications linked yet for this product.")

        if user.get("role") in ("Admin", "Quality Manager"):
            st.divider()
            st.markdown("##### ➕ Configure New Customer Requirement")
            with st.form("add_cust_spec_form"):
                target_cust = st.selectbox("Customer", all_customers, format_func=lambda c: f"{c['code']} — {c['name']}")
                spec_code_inp = st.text_input("Specification Code", placeholder="e.g. IKEA-SPEC-W02")
                spec_req_inp = st.text_area("Specific Requirements", placeholder="Detail edge tolerances, drop test requirements, labeling rules...")
                spec_notes_inp = st.text_input("Operational Notes", placeholder="e.g. Required for all EU distribution centers.")
                if st.form_submit_button("Save Customer Specification"):
                    set_customer_product_spec(
                        product_id=p_sel["id"],
                        customer_id=target_cust["id"],
                        spec_code=spec_code_inp,
                        specific_requirements=spec_req_inp,
                        notes=spec_notes_inp,
                        user_id=user["id"]
                    )
                    st.success("Specification saved successfully!")
                    st.rerun()

# ----------------- TAB 3: NEW PRODUCT REGISTRATION -----------------
with tab_create:
    if user.get("role") not in ("Admin", "Quality Manager"):
        st.warning("🔒 Only Administrators and Quality Managers are authorized to create new products.")
    else:
        st.markdown("#### Register New Manufactured SKU")
        with st.form("new_product_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                new_sku = st.text_input("SKU Code (Unique)", placeholder="e.g. WDT-900").upper()
                new_name = st.text_input("Product Name", placeholder="e.g. Oslo Solid Ash Dining Table")
                new_cat = st.selectbox("Product Category", ["Dining Furniture", "Office Seating", "Storage & Cabinets", "Outdoor Furniture", "Lighting & Accents"])
                new_batch = st.text_input("Batch / Lot Prefix", placeholder="e.g. LOT-WDT")
            with col_b:
                new_market = st.selectbox("Target Market", ["Global", "European Union (IKEA)", "North America", "UK Only"])
                new_rev = st.text_input("Initial Revision", value="1.0")
                new_status = st.selectbox("Initial Status", ["Active", "Pending Approval"])

            new_desc = st.text_area("Product Engineering Description", placeholder="Comprehensive description of product structure, dimensions, and intended commercial use.")
            new_mat = st.text_area("Materials BOM Summary", placeholder="Detailed list of base materials, fasteners, lacquers, and certifications.")

            if st.form_submit_button("Register Product in Catalog", use_container_width=True):
                if not new_sku or not new_name:
                    st.error("SKU and Name are mandatory.")
                else:
                    try:
                        p_id = create_product(
                            sku=new_sku,
                            name=new_name,
                            category=new_cat,
                            description=new_desc,
                            materials_summary=new_mat,
                            batch_prefix=new_batch,
                            target_market=new_market,
                            revision=new_rev,
                            status=new_status,
                            user_id=user["id"]
                        )
                        st.success(f"Product {new_sku} registered successfully (ID: {p_id})!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error registering product: {e}")
