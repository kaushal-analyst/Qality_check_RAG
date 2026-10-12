"""Hybrid retriever combining semantic vector search and SQLite FTS5 with Reciprocal Rank Fusion."""
from typing import List, Dict, Any, Optional
from src.retrieval.vector_store import query_vector_store
from src.retrieval.keyword_search import search_keyword
from src.database.connection import get_db

def retrieve_hybrid_evidence(
    query_text: str,
    product_id: int,
    customer_id: Optional[int] = None,
    top_k: int = 5,
    rrf_k: int = 60,
    include_unapproved: bool = False
) -> List[Dict[str, Any]]:
    """
    Executes hybrid retrieval using Reciprocal Rank Fusion (RRF).
    Guarantees product and customer isolation, and filters out unapproved/superseded specs.
    """
    if not query_text.strip():
        return []

    # 1. Fetch from Vector Store
    vector_hits = query_vector_store(
        query_text=query_text,
        product_id=product_id,
        customer_id=customer_id,
        top_k=top_k * 2
    )

    # 2. Fetch from Keyword Index (BM25)
    keyword_hits = search_keyword(
        query_text=query_text,
        product_id=product_id,
        customer_id=customer_id,
        limit=top_k * 2
    )

    # 3. Reciprocal Rank Fusion
    rrf_scores: Dict[str, float] = {}
    item_map: Dict[str, Dict[str, Any]] = {}

    for rank, hit in enumerate(vector_hits, start=1):
        cid = hit["chunk_id"]
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))
        item_map[cid] = hit

    for rank, hit in enumerate(keyword_hits, start=1):
        cid = hit["chunk_id"]
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))
        if cid not in item_map:
            item_map[cid] = hit

    # Sort items by RRF score descending
    sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

    # 4. Enrich with verified document metadata from database
    enriched_results = []
    with get_db() as conn:
        for cid in sorted_chunk_ids:
            hit = item_map[cid]
            doc_id_val = hit.get("metadata", {}).get("document_id")
            
            # Fetch document record
            doc_row = conn.execute(
                """
                SELECT d.id, d.document_id, d.title, d.category, d.revision, d.approval_status,
                       d.effective_date, d.expiry_date, c.page_number, c.section_title
                FROM document_chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.chunk_id = ?
                """,
                (cid,)
            ).fetchone()
            
            if not doc_row:
                continue
                
            doc_dict = dict(doc_row)
            
            # Filter approval status unless explicitly requested
            if not include_unapproved and doc_dict.get("approval_status") != "Approved":
                continue
                
            enriched_results.append({
                "chunk_id": cid,
                "content": hit["content"],
                "rrf_score": round(rrf_scores[cid], 5),
                "document_id": doc_dict["document_id"],
                "document_title": doc_dict["title"],
                "category": doc_dict["category"],
                "revision": doc_dict["revision"],
                "page_number": doc_dict.get("page_number", 1),
                "section_title": doc_dict.get("section_title", "General"),
                "effective_date": doc_dict.get("effective_date"),
                "expiry_date": doc_dict.get("expiry_date"),
                "approval_status": doc_dict.get("approval_status")
            })
            
            if len(enriched_results) >= top_k:
                break

    return enriched_results
