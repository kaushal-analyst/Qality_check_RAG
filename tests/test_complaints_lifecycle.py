"""Automated tests for complaint intake, lifecycle transitions, risk scoring, and CAPA workflows."""
import pytest
from src.complaint_management.service import (
    create_complaint, update_complaint_status, get_complaint_by_id, add_complaint_attachment
)
from src.compliance.risk_matrix import calculate_complaint_risk
from src.complaint_management.capa import create_capa_task, update_capa_task_status, list_capa_tasks
from src.products.service import get_product_by_sku

def test_complaint_lifecycle_and_audit():
    table = get_product_by_sku("NDT-800")
    assert table is not None

    # 1. Intake
    c_res = create_complaint(
        reporter_type="Internal Employee",
        product_id=table["id"],
        sku="NDT-800",
        category="Dimensional defects",
        description="Leg clearance measured 740mm on random audit sample.",
        severity="High",
        urgency="Urgent"
    )
    c_id = c_res["id"]
    assert c_res["status"] == "Submitted"

    # 2. Lifecycle transitions
    update_complaint_status(c_id, "Triaged", change_notes="Triaged by Lead Inspector")
    update_complaint_status(c_id, "Under Investigation", change_notes="Gauge check underway")
    update_complaint_status(c_id, "Manager Review", change_notes="Sent for manager signoff")
    update_complaint_status(c_id, "Closed", change_notes="Case closed successfully")

    # 3. Verify history audit trail
    complaint_data = get_complaint_by_id(c_id)
    assert complaint_data["current_status"] == "Closed"
    history = complaint_data["status_history"]
    assert len(history) == 5  # Submitted + Triaged + Under Investigation + Manager Review + Closed
    assert history[0]["to_status"] == "Submitted"
    assert history[-1]["to_status"] == "Closed"

def test_attachment_handling():
    table = get_product_by_sku("NDT-800")
    c_res = create_complaint(
        reporter_type="Customer",
        product_id=table["id"],
        sku="NDT-800",
        category="Packaging issues",
        description="Torn box",
        severity="Low",
        urgency="Low"
    )
    c_id = c_res["id"]
    att_id = add_complaint_attachment(c_id, b"Dummy photo content 12345", "damaged_box.jpg")
    assert att_id > 0

    c_record = get_complaint_by_id(c_id)
    assert len(c_record["attachments"]) == 1
    assert c_record["attachments"][0]["file_name"] == "damaged_box.jpg"

def test_risk_matrix_safety_trigger():
    table = get_product_by_sku("NDT-800")
    # Create complaint with chemical hazard to get real DB ID
    c_res = create_complaint(
        reporter_type="Customer",
        product_id=table["id"],
        sku="NDT-800",
        category="Chemical or material concerns",
        description="Strong chemical odor and suspected toxic formaldehyde emissions above regulatory limits.",
        severity="Critical",
        urgency="Urgent",
        quantity_affected=50
    )
    c_id = c_res["id"]
    complaint_rec = get_complaint_by_id(c_id)

    # Risk assessment with valid evaluation or fallback
    # First get or create an evaluation
    from src.quality_engine.rule_evaluator import evaluate_complaint
    eval_res = evaluate_complaint(c_id)
    eval_db_id = eval_res["evaluation_db_id"]

    risk = calculate_complaint_risk(complaint_rec, evaluation_id=eval_db_id)
    assert risk["safety_flag"] is True
    assert risk["overall_risk_level"] == "Critical"
    assert risk["escalation_required"] is True

def test_capa_task_workflow():
    table = get_product_by_sku("NDT-800")
    c_res = create_complaint(
        reporter_type="Field Inspector",
        product_id=table["id"],
        sku="NDT-800",
        category="Physical damage",
        description="Cracked table rail",
        severity="Medium",
        urgency="Medium"
    )
    c_id = c_res["id"]

    # Create CAPA
    capa_id = create_capa_task(
        complaint_id=c_id,
        capa_type="Corrective",
        title="Inspect Clamp Pressure on Assembly Line",
        description="Verify hydraulic pressure gauge and calibrate clamping stops.",
        department="Manufacturing",
        priority="High"
    )
    assert capa_id > 0

    # Advance CAPA to In Progress
    update_capa_task_status(capa_id, "In Progress", outcome_notes="Technician assigned.")
    # Close CAPA with effectiveness verification
    update_capa_task_status(
        capa_id,
        "Verified Effective",
        outcome_notes="Pressure reduced to 12 bar; 50 consecutive units verified crack-free.",
        effectiveness_verification="Re-inspection passed 100% on batch LOT-NDT-04."
    )

    capas = list_capa_tasks(complaint_id=c_id)
    assert len(capas) == 1
    assert capas[0]["status"] == "Verified Effective"
    assert "Re-inspection passed" in capas[0]["effectiveness_verification"]
