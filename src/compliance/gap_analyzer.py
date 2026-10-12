"""Compliance gap analyzer detecting missing documents, chemical declarations, and conflicts."""
from typing import Dict, Any, List
from datetime import datetime, date
from src.database.connection import get_db

REQUIRED_DOCUMENT_CATEGORIES = [
    "Product Specification",
    "Bill of Materials (BOM)",
    "Chemical Safety & REACH",
    "Quality-Control Checklist",
    "Inspection & Lab Test"
]

def analyze_product_compliance_gaps(product_id: int) -> Dict[str, Any]:
    """
    Checks active document repository for missing required categories, expired files,
    and specification conflicts for a given product.
    """
    with get_db() as conn:
        docs = conn.execute(
            """
            SELECT id, document_id, title, category, revision, effective_date,
                   expiry_date, approval_status
            FROM documents
            WHERE product_id = ?
            """,
            (product_id,)
        ).fetchall()
        
    doc_list = [dict(d) for d in docs]
    approved_docs = [d for d in doc_list if d["approval_status"] == "Approved"]
    
    # Check present categories
    present_categories = {d["category"] for d in approved_docs}
    missing_categories = [cat for cat in REQUIRED_DOCUMENT_CATEGORIES if cat not in present_categories]

    # Check expired documents
    expired_docs = []
    today_str = date.today().isoformat()
    for d in approved_docs:
        exp = d.get("expiry_date")
        if exp and exp < today_str:
            expired_docs.append({
                "document_id": d["document_id"],
                "title": d["title"],
                "category": d["category"],
                "expiry_date": exp
            })

    # Identify potential chemical documentation gaps
    chemical_doc_present = "Chemical Safety & REACH" in present_categories
    chemical_gap = not chemical_doc_present

    # Compliance status summary
    if missing_categories or expired_docs:
        overall_status = "Non-compliant / Gaps Identified"
    else:
        overall_status = "Compliant against evaluated documentation"

    return {
        "product_id": product_id,
        "overall_status": overall_status,
        "total_documents": len(doc_list),
        "approved_documents_count": len(approved_docs),
        "missing_categories": missing_categories,
        "expired_documents": expired_docs,
        "chemical_documentation_gap": chemical_gap,
        "requires_manager_review": bool(missing_categories or expired_docs or chemical_gap)
    }
