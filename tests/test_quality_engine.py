"""Automated tests for quality evaluation scoring, rules, and mandatory failure overrides."""
import pytest
from src.quality_engine.scorer import compute_quality_score

def test_quality_score_all_pass():
    criteria_results = [
        {"criterion_code": "C1", "outcome": "Pass", "weight": 2.0, "is_mandatory": True},
        {"criterion_code": "C2", "outcome": "Pass", "weight": 1.0, "is_mandatory": False},
        {"criterion_code": "C3", "outcome": "Pass", "weight": 1.0, "is_mandatory": True}
    ]
    res = compute_quality_score(criteria_results)
    assert res["quality_score"] == 100.0
    assert res["scoring_status"] == "Pass"
    assert res["mandatory_failures_count"] == 0
    assert res["evidence_completeness_pct"] == 100.0

def test_mandatory_failure_override():
    """Critical Business Rule: Mandatory failure must override high average score."""
    criteria_results = [
        {"criterion_code": "C1", "outcome": "Pass", "weight": 5.0, "is_mandatory": False},
        {"criterion_code": "C2", "outcome": "Pass", "weight": 4.0, "is_mandatory": False},
        # C3 is mandatory and fails:
        {"criterion_code": "C3", "outcome": "Fail", "weight": 1.0, "is_mandatory": True}
    ]
    res = compute_quality_score(criteria_results)
    # Average score is (5*1 + 4*1 + 1*0) / 10 = 90.0%
    assert res["quality_score"] == 90.0
    # BUT scoring status MUST be 'Fail' because of mandatory failure!
    assert res["scoring_status"] == "Fail"
    assert res["mandatory_failures_count"] == 1
    assert "mandatory quality criterion" in res["explanation"]

def test_unevaluated_not_passing():
    """Unevaluated criteria must NOT be counted as passing."""
    criteria_results = [
        {"criterion_code": "C1", "outcome": "Pass", "weight": 1.0, "is_mandatory": False},
        {"criterion_code": "C2", "outcome": "Insufficient Evidence", "weight": 1.0, "is_mandatory": False},
        {"criterion_code": "C3", "outcome": "Not Evaluated", "weight": 1.0, "is_mandatory": False}
    ]
    res = compute_quality_score(criteria_results)
    # 1 pass (1.0), 2 unevaluated (0.0). Total weight = 3. Score = 33.3%
    assert res["quality_score"] < 40.0
    assert res["unevaluated_count"] == 2
    assert res["scoring_status"] == "Inconclusive"
