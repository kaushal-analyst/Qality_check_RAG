"""Configurable 4-tier Risk Matrix and Escalation Assessment."""
from typing import Dict, Any, Optional
from src.database.connection import get_db

SEVERITY_WEIGHTS = {
    "Low": 1,
    "Medium": 2,
    "High": 3,
    "Critical": 4
}

def calculate_complaint_risk(
    complaint: Dict[str, Any],
    evaluation_id: int
) -> Dict[str, Any]:
    """
    Computes objective risk score based on severity, recurrence frequency,
    quantity affected, and safety flags.
    """
    sev_str = complaint.get("severity", "Medium")
    sev_val = SEVERITY_WEIGHTS.get(sev_str, 2)

    product_id = complaint["product_id"]
    category = complaint.get("category", "")
    quantity = complaint.get("quantity_affected", 1)

    # 1. Recurrence frequency in database for same product and category
    with get_db() as conn:
        repeat_count = conn.execute(
            """
            SELECT COUNT(*) FROM complaints
            WHERE product_id = ? AND category = ? AND id != ?
            """,
            (product_id, category, complaint["id"])
        ).fetchone()[0]

    if repeat_count == 0:
        freq_score = 1
    elif repeat_count <= 2:
        freq_score = 2
    elif repeat_count <= 5:
        freq_score = 3
    else:
        freq_score = 4

    # 2. Units affected score
    if quantity <= 1:
        unit_score = 1
    elif quantity <= 10:
        unit_score = 2
    elif quantity <= 50:
        unit_score = 3
    else:
        unit_score = 4

    # 3. Safety Flag Detection
    safety_keywords = ["chemical", "fumes", "toxic", "lead", "reach", "formaldehyde", "burn", "collapse", "sharp", "electric", "fire", "injury"]
    desc = complaint.get("description", "").lower()
    safety_flag = (
        category == "Chemical or material concerns"
        or any(k in desc for k in safety_keywords)
        or sev_str == "Critical"
    )

    # Risk Score calculation
    base_score = sev_val * ((freq_score + unit_score) / 2.0)
    
    if safety_flag:
        base_score = max(base_score, 12.0)
        overall_level = "Critical"
        escalation_req = 1
        rationale = f"CRITICAL: Potential product safety/chemical compliance hazard identified. Flagged for mandatory executive escalation."
    elif base_score >= 9.0 or sev_str == "Critical":
        overall_level = "Critical"
        escalation_req = 1
        rationale = f"High severity ({sev_str}) and repeated occurrence ({repeat_count} previous cases) trigger Critical escalation."
    elif base_score >= 6.0 or sev_str == "High":
        overall_level = "High"
        escalation_req = 1
        rationale = f"Elevated defect impact across {quantity} unit(s) with recurrent pattern ({repeat_count} previous reports)."
    elif base_score >= 3.0:
        overall_level = "Medium"
        escalation_req = 0
        rationale = "Moderate quality variance within standard investigation protocol."
    else:
        overall_level = "Low"
        escalation_req = 0
        rationale = "Isolated minor deviation with minimal customer impact."

    # Persist in risk_assessments table
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO risk_assessments (
                evaluation_id, complaint_id, severity_level, frequency_score,
                units_affected_score, overall_risk_level, risk_score,
                escalation_required, safety_flag, rationale
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evaluation_id, complaint["id"], sev_str, freq_score, unit_score,
                overall_level, round(base_score, 1), escalation_req,
                1 if safety_flag else 0, rationale
            )
        )

    return {
        "severity": sev_str,
        "frequency_score": freq_score,
        "repeat_incident_count": repeat_count,
        "units_affected_score": unit_score,
        "overall_risk_level": overall_level,
        "risk_score": round(base_score, 1),
        "escalation_required": bool(escalation_req),
        "safety_flag": safety_flag,
        "rationale": rationale
    }
