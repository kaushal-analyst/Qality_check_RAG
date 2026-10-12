"""Quality Manager sign-off, review, and approval workflow."""
from typing import Dict, Any, Optional
from src.database.connection import get_db
from src.audit.logger import log_audit_event
from src.complaint_management.service import update_complaint_status

def review_evaluation(
    evaluation_db_id: int,
    manager_decision: str,  # 'Approved', 'Rejected', 'Escalated'
    manager_notes: str,
    user_id: int,
    close_complaint: bool = False
) -> Dict[str, Any]:
    """
    Records a formal Quality Manager sign-off on an evaluation run,
    advances the complaint lifecycle, and records an immutable audit record.
    """
    if manager_decision not in ('Approved', 'Rejected', 'Escalated'):
        raise ValueError(f"Invalid decision '{manager_decision}'. Must be 'Approved', 'Rejected', or 'Escalated'.")

    with get_db() as conn:
        row = conn.execute(
            "SELECT evaluation_id, complaint_id, quality_score, scoring_status FROM evaluations WHERE id = ?",
            (evaluation_db_id,)
        ).fetchone()
        
        if not row:
            raise ValueError(f"Evaluation ID {evaluation_db_id} not found.")
            
        eval_dict = dict(row)
        complaint_id = eval_dict["complaint_id"]
        eval_code = eval_dict["evaluation_id"]

        conn.execute(
            """
            UPDATE evaluations
            SET manager_approval_status = ?, manager_notes = ?,
                reviewed_by_user_id = ?, reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (manager_decision, manager_notes.strip(), user_id, evaluation_db_id)
        )

    # Transition complaint lifecycle status
    if close_complaint and manager_decision == "Approved":
        update_complaint_status(complaint_id, "Closed", user_id, f"Closed with Quality Manager sign-off ({eval_code}).")
    elif manager_decision == "Escalated":
        update_complaint_status(complaint_id, "Escalated", user_id, f"Escalated for senior review: {manager_notes}")
    elif manager_decision == "Approved":
        update_complaint_status(complaint_id, "Approved", user_id, f"Evaluation approved: {manager_notes}")
    elif manager_decision == "Rejected":
        update_complaint_status(complaint_id, "Rejected", user_id, f"Evaluation findings rejected: {manager_notes}")

    log_audit_event(
        action=f"EVALUATION_{manager_decision.upper()}",
        entity_type="evaluation",
        entity_id=eval_code,
        user_id=user_id,
        details={"decision": manager_decision, "notes": manager_notes}
    )

    return {
        "success": True,
        "evaluation_id": eval_code,
        "decision": manager_decision,
        "complaint_id": complaint_id
    }
