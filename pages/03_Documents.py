"""Document Ingestion, Version Management, and Grounded RAG Query Assistant."""
import streamlit as st
import pandas as pd
from src.products.service import list_products, list_customers
from src.document_processing.service import ingest_document, list_documents, get_document_chunks, get_document_by_id
from src.rag.service import answer_quality_question
from src.ui_components import inject_custom_styles, render_header, render_sidebar_auth_status, require_auth

st.set_page_config(page_title="Documents & RAG — Quality AI", page_icon="📑", layout="wide")
inject_custom_styles()
render_sidebar_auth_status()
user = require_auth()

render_header("Knowledge Repository & Grounded RAG Assistant", "Document Ingestion Pipeline, Chunk Explorer, and Source-Cited Retrieval")

tab_upload, tab_inventory, tab_rag = st.tabs(["📤 Upload & Ingest Documents", "📑 Document Inventory & Chunks", "💬 RAG Knowledge Assistant"])

DOCUMENT_CATEGORIES = [
    "Product Specification",
    "Bill of Materials (BOM)",
    "Chemical Safety & REACH",
    "Manufacturing SOP",
    "Quality-Control Checklist",
    "Inspection & Lab Test",
    "Customer-Specific Requirement",
    "Regulatory & Certification",
    "Historical CAPA"
]

# ----------------- TAB 1: UPLOAD & INGEST -----------------
with tab_upload:
    st.markdown("#### Ingest Engineering Documents, Test Reports & Standards")
    st.caption("Supported formats: PDF, DOCX, XLSX, CSV, TXT, MD, JPG, PNG (Max 50MB). Files are parsed, chunked, and dual-indexed in ChromaDB & SQLite FTS5.")

    products = list_products()
    customers = list_customers()

    if not products:
        st.warning("Please register at least one product before uploading documents.")
    else:
        with st.form("upload_doc_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                sel_product = st.selectbox("Associated Product (SKU)", products, format_func=lambda p: f"{p['sku']} — {p['name']}")
                doc_title = st.text_input("Document Title", placeholder="e.g. NDT-800 Packaging Specification")
                doc_cat = st.selectbox("Document Category", DOCUMENT_CATEGORIES)
                doc_rev = st.text_input("Document Revision", value="1.0")

            with col2:
                sel_cust = st.selectbox("Customer Scope (Optional)", [None] + customers, format_func=lambda c: f"{c['code']} — {c['name']}" if c else "All / Global Standard")
                eff_date = st.date_input("Effective Date")
                exp_date = st.date_input("Expiry Date (Optional)", value=None)
                appr_status = st.selectbox("Approval Status", ["Approved", "Draft", "Superseded"])

            uploaded_file = st.file_uploader("Select Specification File", type=["pdf", "docx", "xlsx", "csv", "txt", "md", "jpg", "jpeg", "png"])
            submit_doc = st.form_submit_button("⚡ Process & Index Document", use_container_width=True)

            if submit_doc:
                if not uploaded_file or not doc_title:
                    st.error("Please provide a file and document title.")
                else:
                    with st.spinner("Parsing file, calculating hash, chunking content, and generating embeddings..."):
                        try:
                            file_bytes = uploaded_file.read()
                            res = ingest_document(
                                file_bytes=file_bytes,
                                file_name=uploaded_file.name,
                                product_id=sel_product["id"],
                                category=doc_cat,
                                title=doc_title,
                                revision=doc_rev,
                                customer_id=sel_cust["id"] if sel_cust else None,
                                effective_date=str(eff_date) if eff_date else None,
                                expiry_date=str(exp_date) if exp_date else None,
                                approval_status=appr_status,
                                user_id=user["id"]
                            )
                            if res["success"]:
                                st.success(f"✅ {res['message']}")
                                st.info(f"Assigned ID: `{res['document_id']}` | Indexed Chunks: `{res['chunks_indexed']}`")
                            else:
                                st.warning(f"⚠️ {res['message']}")
                        except Exception as e:
                            st.error(f"Ingestion failed: {e}")

# ----------------- TAB 2: INVENTORY & CHUNK EXPLORER -----------------
with tab_inventory:
    st.markdown("#### Active Knowledge Documents in Repository")
    all_docs = list_documents()

    if not all_docs:
        st.info("No documents found.")
    else:
        df_docs = pd.DataFrame(all_docs)
        st.dataframe(
            df_docs[["document_id", "product_sku", "title", "category", "revision", "approval_status", "chunk_count", "effective_date"]].rename(columns={
                "document_id": "Doc ID",
                "product_sku": "SKU",
                "title": "Title",
                "category": "Category",
                "revision": "Rev",
                "approval_status": "Status",
                "chunk_count": "Chunks",
                "effective_date": "Effective"
            }),
            use_container_width=True,
            hide_index=True
        )

        st.divider()
        st.markdown("#### 🔬 Inspect Chunks & Provenance for Document")
        sel_doc_id = st.selectbox("Select Document", all_docs, format_func=lambda d: f"{d['document_id']} — {d['title']} (Rev {d['revision']})")
        
        chunks = get_document_chunks(sel_doc_id["id"])
        st.write(f"Total structured chunks indexed: **{len(chunks)}**")
        
        for c in chunks:
            with st.expander(f"Chunk #{c['chunk_index']} — Page {c['page_number']} | Section: {c.get('section_title', 'General')} ({c.get('token_count', 0)} tokens)"):
                st.code(c["content"], language="text")

# ----------------- TAB 3: RAG ASSISTANT -----------------
with tab_rag:
    st.markdown("#### 💬 Grounded AI Quality Assistant")
    st.caption("Ask questions about product specifications, chemical thresholds, IKEA packaging requirements, or test methods. Every answer is grounded in retrieved chunks with exact citations.")

    if not products:
        st.info("No products registered.")
    else:
        rag_col1, rag_col2 = st.columns([1, 2])
        with rag_col1:
            rag_prod = st.selectbox("Select SKU Scope", products, format_func=lambda p: f"{p['sku']} — {p['name']}", key="rag_sku_sel")
            rag_cust = st.selectbox("Customer Context (Optional)", [None] + customers, format_func=lambda c: f"{c['code']} — {c['name']}" if c else "General / Internal", key="rag_cust_sel")
            
            sample_questions = [
                "What is the allowable moisture content tolerance for this table?",
                "What packaging and corner protector requirements apply per IKEA standards?",
                "What are the formaldehyde emission limits under EN 717-1 for this product?",
                "What is the allowable clearance height tolerance range?",
                "What is the gas lift BIFMA durability standard for this chair?"
            ]
            st.markdown("##### 💡 Suggested Questions:")
            for sq in sample_questions:
                if st.button(sq, key=f"btn_{sq[:25]}"):
                    st.session_state["rag_query_input"] = sq

        with rag_col2:
            default_query = st.session_state.get("rag_query_input", "")
            user_question = st.text_area("Enter your quality inquiry:", value=default_query, height=100, placeholder="e.g. Does a 738mm leg height meet the approved engineering specification?")
            
            if st.button("🔍 Retrieve Evidence & Synthesize Grounded Answer", use_container_width=True):
                if not user_question.strip():
                    st.error("Please enter a question.")
                else:
                    with st.spinner("Executing hybrid retrieval (vector + BM25) and verifying citations..."):
                        rag_output = answer_quality_question(
                            question=user_question,
                            product_id=rag_prod["id"],
                            customer_id=rag_cust["id"] if rag_cust else None,
                            top_k=5
                        )

                        st.markdown("### 📋 AI Quality Finding")
                        st.markdown(rag_output["answer"])

                        # Citations & Evidence Verification Banner
                        v = rag_output["verification"]
                        if v["is_grounded"]:
                            st.success(f"✅ Grounding Verified: All {v['citation_count']} citation(s) exist in retrieved database records.")
                        else:
                            st.warning(f"⚠️ Unverified Citations Flagged: {v['unverified_citations']}")

                        # Retrieved Evidence Inspection
                        with st.expander(f"📚 Retrieved Source Evidence Chunks ({len(rag_output['retrieved_evidence'])})", expanded=False):
                            for idx, ch in enumerate(rag_output["retrieved_evidence"], 1):
                                st.markdown(
                                    f"**Item {idx}:** `{ch['document_id']}` — *{ch['document_title']}* (Rev {ch['revision']}) | "
                                    f"Page {ch['page_number']} — {ch['section_title']} (RRF Match Score: `{ch['rrf_score']}`)"
                                )
                                st.caption(ch["content"])
                                st.divider()
