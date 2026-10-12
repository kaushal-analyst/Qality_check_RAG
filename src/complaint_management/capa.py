"""Corrective and Preventive Action (CAPA) management service."""
from typing import List, Dict, Any, Optional
from src.database.connection import get_db
from src.audit.logger import log_audit_event

def create_capa_task(
    complaint_id: int,
    capa_type: str,
    title: str,
    description: str,
    department: str,
    priority: str = "High",
    assigned_to_user_id: Optional[int] = None,
    evaluation_id: Optional[int] = None,
    due_date: Optional[str] = None,
    user_id: Optional[int] = None
) -> int:
    """Creates a new CAPA task linked to a complaint."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO capa_tasks (
                complaint_id, evaluation_id, capa_type, title, description,
                assigned_to_user_id, department, priority, due_date, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Open')
            """,
            (
                complaint_id, evaluation_id, capa_type, title.strip(), description.strip(),
                assigned_to_user_id, department, priority, due_date
            )
        )
        capa_id = cursor.lastrowid

    log_audit_event(
        action="CAPA_TASK_CREATED",
        entity_type="capa_task",
        entity_id=str(capa_id),
        user_id=user_id,
        details={"type": capa_type, "title": title, "priority": priority, "dept": department}
    )
    return capa_id

def update_capa_task_status(
    capa_id: int,
    status: str,
    outcome_notes: Optional[str] = None,
    effectiveness_verification: Optional[str] = None,
    verified_by_user_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> bool:
    """Updates CAPA progress and records effectiveness verification upon completion."""
    with get_db() as conn:
        if status in ("Verified Effective", "Closed"):
            conn.execute(
                """
                UPDATE capa_tasks
                SET status = ?, outcome_notes = ?, effectiveness_verification = ?,
                    verified_by_user_id = ?, verified_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, outcome_notes, effectiveness_verification, verified_by_user_id or user_id, capa_id)
            )
        else:
            conn.execute(
                """
                UPDATE capa_tasks
                SET status = ?, outcome_notes = ?
                WHERE id = ?
                """,
                (status, outcome_notes, capa_id)
            )

    log_audit_event(
        action="CAPA_TASK_UPDATED",
        entity_type="capa_task",
        entity_id=str(capa_id),
        user_id=user_id,
        details={"status": status, "outcome": outcome_notes}
    )
    return True

def list_capa_tasks(complaint_id: Optional[int] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lists CAPA tasks with assigned owner and complaint details."""
    sql = """
        SELECT c.*, cmp.complaint_id as complaint_code, cmp.sku, p.name as product_name,
               u.full_name as assigned_to_name, v.full_name as verified_by_name
        FROM capa_tasks c
        JOIN complaints cmp ON c.complaint_id = cmp.id
        JOIN products p ON cmp.product_id = p.id
        LEFT JOIN users u ON c.assigned_to_user_id = u.id
        LEFT JOIN users v ON c.verified_by_user_id = v.id
        WHERE 1=1
    """
    params = []
    if complaint_id:
        sql += " AND c.complaint_id = ?"
        params.append(complaint_id)
    if status and status != "All":
        sql += " AND c.status = ?"
        params.append(status)
    sql += " ORDER BY c.created_at DESC"

    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

def auto_suggest_capas(
    complaint_id: int,
    evaluation_id: int,
    risk_level: str,
    failed_criteria: List[Dict[str, Any]],
    user_id: Optional[int] = None
) -> List[int]:
    """Generates initial containment, corrective, and preventive action recommendations."""
    created_ids = []

    # 1. Immediate Containment Action
    c1 = create_capa_task(
        complaint_id=complaint_id,
        evaluation_id=evaluation_id,
        capa_type="Containment",
        title="Quarantine Production Lot & On-Hand Warehouse Stock",
        description="Immediately hold warehouse pallets and flag batch ID in ERP to prevent shipping pending root-cause verification.",
        department="Warehouse & Logistics",
        priority="Critical" if risk_level in ("Critical", "High") else "Medium",
        user_id=user_id
    )
    created_ids.append(c1)

    # 2. Corrective Action
    c2 = create_capa_task(
        complaint_id=complaint_id,
        evaluation_id=evaluation_id,
        capa_type="Corrective",
        title="Production Line Calibration & 100% In-Process Inspection",
        description="Inspect tooling, verify raw material batch certificates, and initiate 100% optical/dimensional inspection on current active run.",
        department="Manufacturing Operations",
        priority="High",
        user_id=user_id
    )
    created_ids.append(c2)

    # 3. Preventive Action
    c3 = create_capa_task(
        complaint_id=complaint_id,
        evaluation_id=evaluation_id,
        capa_type="Preventive",
        title="Update QC Acceptance Checklist & Tooling Preventive Maintenance Cycle",
        description="Review tolerance window in standard operating procedure (SOP) and decrease maintenance interval for cutting and assembly heads.",
        department="Quality Assurance",
        priority="Medium",
        user_id=user_id
    )
    created_ids.append(c3)

    return created_ids
