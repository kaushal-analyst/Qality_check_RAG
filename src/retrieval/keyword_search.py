"""Keyword BM25 search using SQLite FTS5."""
import re
from typing import List, Dict, Any, Optional
from src.database.connection import get_db

def sanitize_fts_query(query: str) -> str:
    """Sanitizes user input into valid FTS5 tokens connected with OR/AND."""
    # Remove punctuation that breaks FTS5 syntax
    cleaned = re.sub(r'[^\w\s]', ' ', query)
    tokens = [t.strip() for t in cleaned.split() if len(t.strip()) > 1]
    if not tokens:
        return '""'
    # Join with OR for broad keyword recall
    return " OR ".join(f'"{t}"' for t in tokens)

def index_fts_chunks(chunks: List[Dict[str, Any]], doc_metadata: Dict[str, Any]):
    """Inserts or updates chunks into SQLite FTS5 table."""
    with get_db() as conn:
        for c in chunks:
            # Delete any existing row with this chunk_id
            conn.execute("DELETE FROM document_fts WHERE chunk_id = ?", (str(c["chunk_id"]),))
            conn.execute(
                """
                INSERT INTO document_fts (chunk_id, document_id, product_id, customer_id, section_title, content)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(c["chunk_id"]),
                    str(doc_metadata.get("document_id", "")),
                    str(c["product_id"]),
                    str(c.get("customer_id", 0) or 0),
                    str(c.get("section_title", "")),
                    str(c["content"])
                )
            )

def search_keyword(
    query_text: str,
    product_id: int,
    customer_id: Optional[int] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """Performs FTS5 BM25 ranking keyword search with product/customer isolation."""
    fts_query = sanitize_fts_query(query_text)
    if fts_query == '""':
        return []

    sql = """
        SELECT f.chunk_id, f.document_id, f.product_id, f.customer_id, f.section_title, f.content,
               bm25(document_fts) as rank_score,
               d.title as doc_title, d.revision, d.category, d.approval_status
        FROM document_fts f
        JOIN documents d ON d.document_id = f.document_id
        WHERE document_fts MATCH ?
          AND f.product_id = ?
    """
    params = [fts_query, str(product_id)]
    
    if customer_id:
        sql += " AND (f.customer_id = ? OR f.customer_id = '0')"
        params.append(str(customer_id))
        
    sql += " ORDER BY rank_score ASC LIMIT ?"
    params.append(limit)

    results = []
    with get_db() as conn:
        try:
            rows = conn.execute(sql, params).fetchall()
            for r in rows:
                row_dict = dict(r)
                # BM25 in SQLite: lower is better (negative or small positive). Normalize to positive score:
                raw_bm25 = row_dict.get("rank_score", 0.0)
                norm_score = 1.0 / (1.0 + abs(raw_bm25))
                results.append({
                    "chunk_id": row_dict["chunk_id"],
                    "content": row_dict["content"],
                    "metadata": {
                        "chunk_id": row_dict["chunk_id"],
                        "document_id": row_dict["document_id"],
                        "title": row_dict["doc_title"],
                        "revision": row_dict["revision"],
                        "category": row_dict["category"],
                        "approval_status": row_dict["approval_status"],
                        "section_title": row_dict["section_title"],
                        "product_id": int(row_dict["product_id"])
                    },
                    "score": norm_score,
                    "source": "keyword"
                })
        except Exception as e:
            print(f"FTS Search warning: {e}")
            return []
            
    return results
