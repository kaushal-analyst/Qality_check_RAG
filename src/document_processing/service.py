"""Document ingestion, versioning, and indexing service."""
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from src.config import settings, UPLOADS_DIR
from src.database.connection import get_db
from src.audit.logger import log_audit_event
from src.document_processing.parsers import parse_document, calculate_file_hash
from src.document_processing.chunker import create_chunks
from src.retrieval.vector_store import index_chunks as index_vector_chunks
from src.retrieval.keyword_search import index_fts_chunks

def generate_document_id() -> str:
    """Generates a sequential document ID."""
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        return f"DOC-2026-{count + 1:04d}"

def ingest_document(
    file_bytes: bytes,
    file_name: str,
    product_id: int,
    category: str,
    title: str,
    revision: str = "1.0",
    customer_id: Optional[int] = None,
    effective_date: Optional[str] = None,
    expiry_date: Optional[str] = None,
    approval_status: str = "Approved",
    superseded_by_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    End-to-end document ingestion pipeline:
    Hash -> Store -> Parse -> Chunk -> Vector Index -> FTS5 Index -> Audit.
    """
    ext = Path(file_name).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise ValueError(f"File extension '{ext}' is not permitted. Allowed: {settings.ALLOWED_EXTENSIONS}")
        
    file_size = len(file_bytes)
    if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ValueError(f"File size exceeds maximum allowed of {settings.MAX_FILE_SIZE_MB}MB.")
        
    file_hash = calculate_file_hash(file_bytes)
    
    # Check if duplicate file already exists
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id, document_id, title, revision FROM documents WHERE file_hash = ? AND product_id = ?",
            (file_hash, product_id)
        ).fetchone()
        if existing:
            return {
                "success": False,
                "message": f"Identical file already ingested under {existing['document_id']} (Rev {existing['revision']})",
                "document_id": existing["document_id"],
                "id": existing["id"]
            }

    doc_id_str = generate_document_id()
    saved_filename = f"{doc_id_str}_{file_name}"
    saved_path = UPLOADS_DIR / saved_filename

    with open(saved_path, "wb") as f:
        f.write(file_bytes)

    # Parse file
    try:
        parsed_sections = parse_document(str(saved_path), ext)
        extraction_status = "Success"
        extraction_notes = f"Extracted {len(parsed_sections)} section(s)/page(s)."
    except Exception as e:
        parsed_sections = []
        extraction_status = "Failed"
        extraction_notes = f"Extraction failed: {str(e)}"

    # Record document in DB
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (
                document_id, product_id, customer_id, title, category, revision,
                file_hash, file_path, file_name, file_type, file_size,
                effective_date, expiry_date, approval_status, superseded_by_id,
                uploaded_by_user_id, extraction_status, extraction_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_id_str, product_id, customer_id, title, category, revision,
                file_hash, str(saved_path), file_name, ext, file_size,
                effective_date, expiry_date, approval_status, superseded_by_id,
                user_id, extraction_status, extraction_notes
            )
        )
        doc_db_id = cursor.lastrowid

    # If extraction succeeded, chunk and index
    chunks_created = 0
    if parsed_sections:
        chunks = create_chunks(
            parsed_sections=parsed_sections,
            doc_id=doc_id_str,
            product_id=product_id,
            customer_id=customer_id
        )
        
        # Save chunks in SQLite
        with get_db() as conn:
            for c in chunks:
                conn.execute(
                    """
                    INSERT INTO document_chunks (
                        chunk_id, document_id, product_id, customer_id,
                        chunk_index, page_number, section_title, content, token_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        c["chunk_id"], doc_db_id, product_id, customer_id,
                        c["chunk_index"], c["page_number"], c["section_title"],
                        c["content"], c["token_count"]
                    )
                )

        doc_meta = {
            "id": doc_db_id,
            "document_id": doc_id_str,
            "title": title,
            "category": category,
            "revision": revision,
            "approval_status": approval_status
        }

        # Index into ChromaDB
        index_vector_chunks(chunks, doc_meta)
        
        # Index into SQLite FTS5
        index_fts_chunks(chunks, doc_meta)
        
        chunks_created = len(chunks)

    log_audit_event(
        action="DOCUMENT_INGESTED",
        entity_type="document",
        entity_id=doc_id_str,
        user_id=user_id,
        details={
            "title": title,
            "revision": revision,
            "category": category,
            "chunks_count": chunks_created,
            "status": extraction_status
        }
    )

    return {
        "success": True,
        "document_id": doc_id_str,
        "id": doc_db_id,
        "chunks_indexed": chunks_created,
        "extraction_status": extraction_status,
        "message": f"Successfully ingested {title} ({doc_id_str}) with {chunks_created} indexed chunks."
    }

def list_documents(
    product_id: Optional[int] = None,
    category: Optional[str] = None,
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Lists ingested documents with optional filtering."""
    query = """
        SELECT d.*, p.name as product_name, p.sku as product_sku, c.name as customer_name,
               (SELECT COUNT(*) FROM document_chunks WHERE document_id = d.id) as chunk_count
        FROM documents d
        JOIN products p ON d.product_id = p.id
        LEFT JOIN customers c ON d.customer_id = c.id
        WHERE 1=1
    """
    params = []
    if product_id:
        query += " AND d.product_id = ?"
        params.append(product_id)
    if category and category != "All":
        query += " AND d.category = ?"
        params.append(category)
    if status and status != "All":
        query += " AND d.approval_status = ?"
        params.append(status)
    query += " ORDER BY d.created_at DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

def get_document_by_id(doc_id: int) -> Optional[Dict[str, Any]]:
    """Gets document details by ID."""
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT d.*, p.name as product_name, p.sku as product_sku, c.name as customer_name
            FROM documents d
            JOIN products p ON d.product_id = p.id
            LEFT JOIN customers c ON d.customer_id = c.id
            WHERE d.id = ?
            """,
            (doc_id,)
        ).fetchone()
        return dict(row) if row else None

def get_document_chunks(doc_id: int) -> List[Dict[str, Any]]:
    """Retrieves all chunks for a document."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM document_chunks WHERE document_id = ? ORDER BY chunk_index ASC",
            (doc_id,)
        ).fetchall()
        return [dict(row) for row in rows]
