"""Complaint lifecycle management service."""
from typing import Optional, List, Dict, Any
from pathlib import Path
from src.database.connection import get_db
from src.audit.logger import log_audit_event
from src.config import UPLOADS_DIR

VALID_STATUSES = [
    'Submitted',
    'Triaged',
    'Under Investigation',
    'Awaiting Evidence/Testing',
    'Manager Review',
    'Approved',
    'Rejected',
    'Escalated',
    'Closed'
]

def generate_complaint_id() -> str:
    """Generates sequential complaint ID CMP-2026-XXXX."""
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
        return f"CMP-2026-{count + 1:04d}"

def create_complaint(
    reporter_type: str,
    product_id: int,
    sku: str,
    category: str,
    description: str,
    severity: str,
    urgency: str,
    customer_id: Optional[int] = None,
    order_batch_number: Optional[str] = None,
    quantity_affected: int = 1,
    manufacturing_date: Optional[str] = None,
    assigned_owner_id: Optional[int] = None,
    due_date: Optional[str] = None,
    customer_visible_notes: Optional[str] = None,
    internal_notes: Optional[str] = None,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """Creates a new complaint and logs initial status transition."""
    complaint_id_str = generate_complaint_id()
    
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO complaints (
                complaint_id, reporter_type, customer_id, product_id, sku,
                order_batch_number, category, description, quantity_affected,
                manufacturing_date, severity, urgency, current_status,
                assigned_owner_id, due_date, customer_visible_notes, internal_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Submitted', ?, ?, ?, ?)
            """,
            (
                complaint_id_str, reporter_type, customer_id, product_id, sku.strip().upper(),
                order_batch_number, category, description.strip(), quantity_affected,
                manufacturing_date, severity, urgency, assigned_owner_id,
                due_date, customer_visible_notes, internal_notes
            )
        )
        c_db_id = cursor.lastrowid
        
        # Log initial status history
        conn.execute(
            """
            INSERT INTO complaint_status_history (complaint_id, from_status, to_status, changed_by_user_id, change_notes)
            VALUES (?, NULL, 'Submitted', ?, 'Initial complaint intake')
            """,
            (c_db_id, user_id)
        )

    log_audit_event(
        action="COMPLAINT_CREATED",
        entity_type="complaint",
        entity_id=complaint_id_str,
        user_id=user_id,
        details={
            "sku": sku,
            "category": category,
            "severity": severity,
            "quantity": quantity_affected
        }
    )

    return {
        "success": True,
        "complaint_id": complaint_id_str,
        "id": c_db_id,
        "status": "Submitted"
    }

def update_complaint_status(
    complaint_db_id: int,
    new_status: str,
    user_id: Optional[int] = None,
    change_notes: Optional[str] = None
) -> bool:
    """Updates complaint lifecycle status and preserves immutable audit trail."""
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{new_status}'. Must be one of {VALID_STATUSES}")

    with get_db() as conn:
        row = conn.execute("SELECT current_status, complaint_id FROM complaints WHERE id = ?", (complaint_db_id,)).fetchone()
        if not row:
            return False
            
        old_status = row["current_status"]
        complaint_id_str = row["complaint_id"]
        
        if old_status == new_status:
            return True
            
        conn.execute(
            "UPDATE complaints SET current_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_status, complaint_db_id)
        )
        
        conn.execute(
            """
            INSERT INTO complaint_status_history (complaint_id, from_status, to_status, changed_by_user_id, change_notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (complaint_db_id, old_status, new_status, user_id, change_notes)
        )

    log_audit_event(
        action="COMPLAINT_STATUS_CHANGED",
        entity_type="complaint",
        entity_id=complaint_id_str,
        user_id=user_id,
        details={"from_status": old_status, "to_status": new_status, "notes": change_notes}
    )
    return True

def add_complaint_attachment(
    complaint_db_id: int,
    file_bytes: bytes,
    file_name: str,
    user_id: Optional[int] = None
) -> int:
    """Stores and records an attachment (photo, inspection sheet, PDF) for a complaint."""
    ext = Path(file_name).suffix.lower()
    save_path = UPLOADS_DIR / f"CMP_{complaint_db_id}_{file_name}"
    with open(save_path, "wb") as f:
        f.write(file_bytes)

    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO complaint_attachments (complaint_id, file_name, file_path, file_type, file_size)
            VALUES (?, ?, ?, ?, ?)
            """,
            (complaint_db_id, file_name, str(save_path), ext, len(file_bytes))
        )
        att_id = cursor.lastrowid

    log_audit_event(
        action="COMPLAINT_ATTACHMENT_ADDED",
        entity_type="complaint",
        entity_id=str(complaint_db_id),
        user_id=user_id,
        details={"file_name": file_name, "file_size": len(file_bytes)}
    )
    return att_id

def list_complaints(
    product_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    search: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Lists complaints with relational joins and multi-dimensional filters."""
    query = """
        SELECT c.*, p.name as product_name, p.sku as product_sku,
               cust.name as customer_name, cust.code as customer_code,
               u.full_name as assigned_owner_name
        FROM complaints c
        JOIN products p ON c.product_id = p.id
        LEFT JOIN customers cust ON c.customer_id = cust.id
        LEFT JOIN users u ON c.assigned_owner_id = u.id
        WHERE 1=1
    """
    params = []
    if product_id:
        query += " AND c.product_id = ?"
        params.append(product_id)
    if customer_id:
        query += " AND c.customer_id = ?"
        params.append(customer_id)
    if status and status != "All":
        query += " AND c.current_status = ?"
        params.append(status)
    if severity and severity != "All":
        query += " AND c.severity = ?"
        params.append(severity)
    if search:
        query += " AND (c.complaint_id LIKE ? OR c.description LIKE ? OR c.sku LIKE ? OR c.order_batch_number LIKE ?)"
        s = f"%{search.strip()}%"
        params.extend([s, s, s, s])
    query += " ORDER BY c.created_at DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

def get_complaint_by_id(complaint_db_id: int) -> Optional[Dict[str, Any]]:
    """Gets complete complaint record including attachments and status history."""
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT c.*, p.name as product_name, p.sku as product_sku, p.category as product_category,
                   cust.name as customer_name, cust.code as customer_code,
                   u.full_name as assigned_owner_name
            FROM complaints c
            JOIN products p ON c.product_id = p.id
            LEFT JOIN customers cust ON c.customer_id = cust.id
            LEFT JOIN users u ON c.assigned_owner_id = u.id
            WHERE c.id = ?
            """,
            (complaint_db_id,)
        ).fetchone()
        
        if not row:
            return None
            
        c_dict = dict(row)
        
        # Attachments
        att_rows = conn.execute("SELECT * FROM complaint_attachments WHERE complaint_id = ?", (complaint_db_id,)).fetchall()
        c_dict["attachments"] = [dict(r) for r in att_rows]
        
        # History
        hist_rows = conn.execute(
            """
            SELECT h.*, u.full_name as changed_by_name
            FROM complaint_status_history h
            LEFT JOIN users u ON h.changed_by_user_id = u.id
            WHERE h.complaint_id = ?
            ORDER BY h.timestamp ASC
            """,
            (complaint_db_id,)
        ).fetchall()
        c_dict["status_history"] = [dict(r) for r in hist_rows]
        
        return c_dict
