"""Root-Cause Analysis (RCA) hypothesis generator across 8 standard engineering categories."""
from typing import List, Dict, Any, Optional
from src.database.connection import get_db

RCA_CATEGORIES = [
    "Raw Materials",
    "Supplier Variation",
    "Manufacturing Process",
    "Machine Settings",
    "Packaging",
    "Transportation/Handling",
    "Inspection Gaps",
    "Documentation Errors"
]

def generate_root_cause_hypotheses(
    complaint: Dict[str, Any],
    evaluation_id: int,
    criteria_results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Generates structured root-cause hypotheses based on defect category,
    evidence, and failed criteria.
    """
    category = complaint.get("category", "")
    desc = complaint.get("description", "").lower()
    hypotheses = []

    # 1. Raw Materials & Supplier Variation
    if any(k in desc for k in ["wood", "grain", "knot", "foam", "fabric", "steel", "chemical", "odor", "glue", "resin"]):
        hypotheses.append({
            "category": "Raw Materials",
            "hypothesis_statement": "Substandard moisture content or material composition from raw material batch.",
            "supporting_evidence": f"Reported defect '{category}' exhibits material degradation.",
            "contradicting_evidence": "Incoming material batch inspection certificates not yet compared.",
            "missing_information": "Batch mill certificate and supplier lot inspection report.",
            "likelihood": "High"
        })

    # 2. Manufacturing Process & Machine Settings
    if any(k in desc for k in ["dimension", "tolerance", "cut", "drill", "hole", "alignment", "joint", "weld", "finish", "peel"]):
        hypotheses.append({
            "category": "Machine Settings",
            "hypothesis_statement": "Tool wear or calibration drift on CNC cutting / edge-banding machinery.",
            "supporting_evidence": "Geometric or surface dimensional deviation recorded.",
            "contradicting_evidence": "Daily calibration log showed green status at shift start.",
            "missing_information": "Shift machine calibration logs during the manufacturing run.",
            "likelihood": "High"
        })

    # 3. Packaging & Transportation/Handling
    if any(k in desc for k in ["box", "dented", "transit", "shipping", "scratched", "crushed", "package", "carton", "corner"]):
        hypotheses.append({
            "category": "Packaging",
            "hypothesis_statement": "Inadequate corner protection or substandard carton bursting strength during freight transit.",
            "supporting_evidence": "Outer physical damage reported upon delivery to customer/retailer.",
            "contradicting_evidence": "No transit shock indicator triggered on master pallets.",
            "missing_information": "Drop-test inspection records and freight carrier bill of lading.",
            "likelihood": "Medium"
        })

    # 4. Inspection Gaps
    failed_mand = [r for r in criteria_results if r.get("outcome") == "Fail"]
    if failed_mand:
        hypotheses.append({
            "category": "Inspection Gaps",
            "hypothesis_statement": "Final QC end-of-line sampling frequency was insufficient to catch batch defect variance.",
            "supporting_evidence": f"{len(failed_mand)} quality specification(s) breached on finished goods.",
            "contradicting_evidence": "AQL sampling inspection records show passing sample lots.",
            "missing_information": "Sampling frequency and QC inspector checklist from production date.",
            "likelihood": "High"
        })

    # Default fallback hypothesis if none triggered
    if not hypotheses:
        hypotheses.append({
            "category": "Manufacturing Process",
            "hypothesis_statement": "Assembly or operator handling variation during peak shift volume.",
            "supporting_evidence": "Customer complaint details unexpected physical variance.",
            "contradicting_evidence": "No operator non-conformance flag registered in shift log.",
            "missing_information": "Assembly station operator logs for batch.",
            "likelihood": "Medium"
        })

    # Persist hypotheses in root_cause_hypotheses table
    with get_db() as conn:
        for hyp in hypotheses:
            conn.execute(
                """
                INSERT INTO root_cause_hypotheses (
                    evaluation_id, complaint_id, category, hypothesis_statement,
                    supporting_evidence, contradicting_evidence, missing_information,
                    verification_status, likelihood
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Proposed', ?)
                """,
                (
                    evaluation_id, complaint["id"], hyp["category"], hyp["hypothesis_statement"],
                    hyp["supporting_evidence"], hyp["contradicting_evidence"], hyp["missing_information"],
                    hyp["likelihood"]
                )
            )

    return hypotheses

def get_complaint_hypotheses(complaint_id: int) -> List[Dict[str, Any]]:
    """Retrieves all root-cause hypotheses recorded for a complaint."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM root_cause_hypotheses WHERE complaint_id = ? ORDER BY id ASC",
            (complaint_id,)
        ).fetchall()
        return [dict(r) for r in rows]

def update_hypothesis_status(hypothesis_id: int, status: str, notes: Optional[str] = None) -> bool:
    """Updates verification status of a hypothesis (Proposed -> Under Investigation -> Confirmed/Rejected)."""
    with get_db() as conn:
        conn.execute(
            "UPDATE root_cause_hypotheses SET verification_status = ? WHERE id = ?",
            (status, hypothesis_id)
        )
    return True
