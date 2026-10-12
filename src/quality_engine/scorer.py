"""Weighted scoring engine with mandatory failure overrides and explainability."""
from typing import List, Dict, Any, Tuple

def compute_quality_score(
    criteria_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Computes explainable quality score:
    Score = sum(w_i * s_i) / sum(w_i) * 100
    Applies mandatory failure override where a failure in any mandatory check
    strictly caps the outcome to 'Fail'.
    """
    if not criteria_results:
        return {
            "quality_score": 0.0,
            "scoring_status": "Inconclusive",
            "mandatory_failures_count": 0,
            "warnings_count": 0,
            "unevaluated_count": 0,
            "evidence_completeness_pct": 0.0,
            "explanation": "No criteria evaluated."
        }

    total_weight = 0.0
    weighted_score_sum = 0.0
    mandatory_failures = 0
    warnings_count = 0
    unevaluated_count = 0
    evaluated_count = 0

    for res in criteria_results:
        weight = float(res.get("weight", 1.0))
        outcome = res.get("outcome", "Not Evaluated")
        is_mandatory = bool(res.get("is_mandatory", False))

        total_weight += weight

        if outcome == "Pass":
            weighted_score_sum += weight * 1.0
            evaluated_count += 1
        elif outcome == "Warning":
            weighted_score_sum += weight * 0.5
            warnings_count += 1
            evaluated_count += 1
        elif outcome == "Fail":
            weighted_score_sum += weight * 0.0
            evaluated_count += 1
            if is_mandatory:
                mandatory_failures += 1
        elif outcome in ("Not Evaluated", "Insufficient Evidence"):
            unevaluated_count += 1
            # In production QA, unevaluated criteria do NOT pass; weight is counted but score is 0
            weighted_score_sum += weight * 0.0

    raw_score = (weighted_score_sum / total_weight * 100.0) if total_weight > 0 else 0.0
    rounded_score = round(raw_score, 1)

    total_criteria = len(criteria_results)
    completeness = round((evaluated_count / total_criteria) * 100.0, 1) if total_criteria > 0 else 0.0

    # Determine status with mandatory failure override
    if mandatory_failures > 0:
        status = "Fail"
        explanation = (
            f"FAILED: {mandatory_failures} mandatory quality criterion/criteria failed. "
            f"Under Code Space Techlab policy, mandatory failures strictly override numerical scores."
        )
    elif unevaluated_count > (total_criteria * 0.5):
        status = "Inconclusive"
        explanation = (
            f"INCONCLUSIVE: {unevaluated_count} of {total_criteria} criteria lacked sufficient evidence. "
            "Additional laboratory test records or physical measurements are required."
        )
    elif rounded_score >= 85.0 and warnings_count == 0:
        status = "Pass"
        explanation = "PASS: Product meets approved specifications across all evaluated criteria."
    elif rounded_score >= 70.0:
        status = "Warning"
        explanation = f"WARNING: Marginal compliance score ({rounded_score}%). {warnings_count} minor warning(s) flagged."
    else:
        status = "Fail"
        explanation = f"FAIL: Overall score ({rounded_score}%) is below acceptable threshold."

    return {
        "quality_score": rounded_score,
        "scoring_status": status,
        "mandatory_failures_count": mandatory_failures,
        "warnings_count": warnings_count,
        "unevaluated_count": unevaluated_count,
        "evidence_completeness_pct": completeness,
        "explanation": explanation
    }
