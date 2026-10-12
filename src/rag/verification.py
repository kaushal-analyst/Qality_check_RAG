"""Verification engine validating citations and preventing hallucinations."""
import re
from typing import List, Dict, Any
from src.database.connection import get_db

def verify_citations(response_text: str, retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Scans the response for document citations and verifies they correspond to actual chunks retrieved.
    """
    valid_doc_ids = {c["document_id"] for c in retrieved_chunks}
    
    # Extract citations like [Doc: DOC-123 ...] or DOC-XXXX-XXX
    extracted_doc_ids = set(re.findall(r'DOC-[A-Za-z0-9\-]+', response_text))
    
    verified_citations = []
    unverified_citations = []
    
    for doc_id in extracted_doc_ids:
        if doc_id in valid_doc_ids:
            verified_citations.append(doc_id)
        else:
            # Check if it exists in DB at all
            with get_db() as conn:
                row = conn.execute("SELECT id, title FROM documents WHERE document_id = ?", (doc_id,)).fetchone()
                if row:
                    unverified_citations.append(f"{doc_id} (in database but not in retrieved context)")
                else:
                    unverified_citations.append(f"{doc_id} (HALLUCINATED / Non-existent)")

    is_grounded = len(unverified_citations) == 0
    
    return {
        "is_grounded": is_grounded,
        "verified_citations": verified_citations,
        "unverified_citations": unverified_citations,
        "citation_count": len(extracted_doc_ids)
    }

def check_evidence_sufficiency(retrieved_chunks: List[Dict[str, Any]], min_score: float = 0.01) -> bool:
    """Checks whether retrieved chunks meet the minimum threshold for evidence sufficiency."""
    if not retrieved_chunks:
        return False
    # Check max RRF score
    max_score = max(c.get("rrf_score", 0.0) for c in retrieved_chunks)
    return max_score >= min_score
