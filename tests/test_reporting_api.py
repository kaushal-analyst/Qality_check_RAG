"""Automated tests for PDF/Excel reporting and FastAPI endpoints."""
import pytest
from src.reporting.pdf_generator import generate_complaint_investigation_pdf
from src.reporting.excel_generator import generate_management_dashboard_excel, generate_complaints_csv
from src.complaint_management.service import get_complaint_by_id
from fastapi.testclient import TestClient
from src.api.router import api_app

def test_pdf_report_generation():
    # Retrieve complaint 1
    c = get_complaint_by_id(1)
    assert c is not None
    pdf_bytes = generate_complaint_investigation_pdf(
        complaint=c,
        evaluation={"quality_score": 75.0, "scoring_status": "Fail", "mandatory_failures_count": 1, "evidence_completeness_pct": 80.0},
        criteria_results=[{"criterion_code": "CRIT-01", "criterion_name": "Length", "observed_value": "738mm", "expected_value": "750mm", "outcome": "Fail"}],
        risk={"overall_risk_level": "High", "risk_score": 8.0, "repeat_incident_count": 1, "safety_flag": False, "rationale": "High severity."}
    )
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")

def test_excel_and_csv_generation():
    excel_bytes = generate_management_dashboard_excel()
    assert len(excel_bytes) > 2000
    # Check standard Excel zip signature
    assert excel_bytes.startswith(b"PK")

    csv_text = generate_complaints_csv()
    assert "complaint_id" in csv_text
    assert "NDT-800" in csv_text

def test_fastapi_endpoints():
    client = TestClient(api_app)
    # 1. Health check
    h_resp = client.get("/api/v1/health")
    assert h_resp.status_code == 200
    assert h_resp.json()["status"] == "ok"

    # 2. Products list
    p_resp = client.get("/api/v1/products")
    assert p_resp.status_code == 200
    assert len(p_resp.json()) >= 1

    # 3. Single complaint
    c_resp = client.get("/api/v1/complaints/1")
    assert c_resp.status_code == 200
    assert "complaint_id" in c_resp.json()
