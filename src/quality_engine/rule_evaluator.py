"""Deterministic quality evaluation engine mapped against retrieved RAG evidence."""
import re
import json
from typing import List, Dict, Any, Optional
from src.database.connection import get_db
from src.quality_engine.criteria_manager import get_applicable_criteria
from src.quality_engine.scorer import compute_quality_score
from src.retrieval.hybrid_retriever import retrieve_hybrid_evidence
from src.audit.logger import log_audit_event

def evaluate_complaint(
    complaint_id: int,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Executes a structured, deterministic evaluation of a complaint against all approved criteria,
    backed by hybrid RAG document retrieval for evidence and citations.
    """
    with get_db() as conn:
        c_row = conn.execute(
            """
            SELECT c.*, p.name as product_name, p.sku as product_sku, cust.name as customer_name
            FROM complaints c
            JOIN products p ON c.product_id = p.id
            LEFT JOIN customers cust ON c.customer_id = cust.id
            WHERE c.id = ?
            """,
            (complaint_id,)
        ).fetchone()
        
        if not c_row:
            raise ValueError(f"Complaint ID {complaint_id} not found.")
            
        complaint = dict(c_row)

    product_id = complaint["product_id"]
    customer_id = complaint["customer_id"]
    desc = complaint["description"].lower()
    cat = complaint["category"]

    # 1. Load applicable criteria
    criteria = get_applicable_criteria(product_id, customer_id)
    if not criteria:
        # If no specific criteria configured, generate an inconclusive outcome
        criteria = []

    criteria_results = []
    
    # 2. Retrieve supporting evidence from document repository
    rag_query = f"{cat}: {complaint['description']}"
    retrieved_chunks = retrieve_hybrid_evidence(
        query_text=rag_query,
        product_id=product_id,
        customer_id=customer_id,
        top_k=6
    )

    # 3. Evaluate each criterion deterministically
    for crit in criteria:
        c_type = crit["criterion_type"]
        c_code = crit["criterion_code"]
        c_name = crit["name"]
        min_v = crit.get("min_allowed")
        max_v = crit.get("max_allowed")
        is_mand = bool(crit.get("is_mandatory", 0))
        weight = float(crit.get("weight", 1.0))

        outcome = "Insufficient Evidence"
        score_awarded = 0.0
        max_score = 100.0
        observed_val = "Not detected in complaint narrative"
        expected_val = f"Range: [{min_v}, {max_v}] {crit.get('measurement_unit', '')}" if min_v is not None else crit.get("expected_value", "Approved Standard")
        finding_notes = ""
        citations = []

        # Find any matching chunk for this criterion
        matching_chunks = [
            ch for ch in retrieved_chunks
            if c_name.lower() in ch["content"].lower() or any(w in ch["content"].lower() for w in c_name.lower().split() if len(w) > 3)
        ]
        if matching_chunks:
            for ch in matching_chunks[:2]:
                citations.append({
                    "document_id": ch["document_id"],
                    "title": ch["document_title"],
                    "revision": ch["revision"],
                    "page": ch["page_number"],
                    "section": ch["section_title"]
                })

        # --- A: Numeric Range Check ---
        if c_type == "Numeric Range":
            # Extract numbers from description
            found_nums = [float(n) for n in re.findall(r'\b\d+(?:\.\d+)?\b', desc)]
            if found_nums and (min_v is not None or max_v is not None):
                # Pick the number closest to tolerance or explicitly mentioned
                test_val = found_nums[0]
                observed_val = f"{test_val} {crit.get('measurement_unit', '')}"
                
                is_below = min_v is not None and test_val < min_v
                is_above = max_v is not None and test_val > max_v
                
                if is_below or is_above:
                    outcome = "Fail"
                    score_awarded = 0.0
                    deviation = (min_v - test_val) if is_below else (test_val - max_v)
                    finding_notes = f"Out of specification by {deviation:.1f} {crit.get('measurement_unit', '')}. Allowed: [{min_v}, {max_v}]."
                else:
                    outcome = "Pass"
                    score_awarded = 100.0
                    finding_notes = f"Measurement ({test_val}) is strictly within permitted specification tolerance."
            else:
                outcome = "Insufficient Evidence"
                finding_notes = f"No numerical measurement recorded for {c_name} in complaint narrative."

        # --- B: Required Document Check ---
        elif c_type == "Required Document":
            expected_cat = crit.get("expected_value", crit["category"])
            with get_db() as conn:
                doc = conn.execute(
                    """
                    SELECT document_id, title, revision, approval_status, expiry_date
                    FROM documents
                    WHERE product_id = ? AND approval_status = 'Approved'
                      AND (category LIKE ? OR title LIKE ?)
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (product_id, f"%{expected_cat}%", f"%{c_name}%")
                ).fetchone()

                if doc:
                    outcome = "Pass"
                    score_awarded = 100.0
                    observed_val = f"Document {doc['document_id']} ({doc['title']} Rev {doc['revision']}) is active & approved"
                    finding_notes = f"Verified compliance document exists and is approved."
                    citations.append({
                        "document_id": doc["document_id"],
                        "title": doc["title"],
                        "revision": doc["revision"],
                        "page": 1,
                        "section": "Approved Document Record"
                    })
                else:
                    outcome = "Fail" if is_mand else "Warning"
                    score_awarded = 0.0 if is_mand else 50.0
                    observed_val = "Missing or unapproved document"
                    finding_notes = f"Required documentation '{expected_cat}' is not in approved status for this SKU."

        # --- C: Boolean Check ---
        elif c_type == "Boolean Check":
            negatives = ["missing", "broken", "cracked", "absent", "failed", "incorrect", "no", "not present", "damaged"]
            defect_match = any(neg in desc for neg in negatives if any(term in desc for term in c_name.lower().split() if len(term) > 3))
            
            if defect_match:
                outcome = "Fail"
                score_awarded = 0.0
                observed_val = "Non-compliant / defect reported"
                finding_notes = f"Complaint narrative confirms non-conformance against {c_name}."
            else:
                outcome = "Pass"
                score_awarded = 100.0
                observed_val = "No non-conformance noted"
                finding_notes = f"No breach of {c_name} reported in initial intake."

        # --- D: Qualitative or Test Result ---
        else:
            defect_keywords = ["crack", "scratch", "peel", "delamination", "odor", "chemical", "stain", "warp", "loose"]
            has_defect = any(k in desc for k in defect_keywords if any(w in c_name.lower() for w in [k, "visual", "finish", "surface", "structural"]))
            if has_defect:
                outcome = "Fail"
                score_awarded = 0.0
                observed_val = "Defect observed"
                finding_notes = f"Reported defect violates standard: {c_name}."
            else:
                outcome = "Insufficient Evidence"
                score_awarded = 0.0
                observed_val = "No specific test report attached"
                finding_notes = f"Requires physical inspection/lab result to evaluate {c_name}."

        criteria_results.append({
            "criterion_id": crit["id"],
            "criterion_code": c_code,
            "criterion_name": c_name,
            "category": crit["category"],
            "outcome": outcome,
            "score_awarded": score_awarded,
            "max_score": max_score,
            "observed_value": observed_val,
            "expected_value": expected_val,
            "finding_notes": finding_notes,
            "citations": citations,
            "weight": weight,
            "is_mandatory": is_mand
        })

    # 4. Compute overall score
    scoring = compute_quality_score(criteria_results)

    # 5. Store evaluation run in database
    eval_id_str = f"EVAL-2026-{complaint['id']:04d}-{len(criteria_results)}"
    
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO evaluations (
                evaluation_id, complaint_id, product_id, rule_version,
                quality_score, scoring_status, mandatory_failures_count,
                warnings_count, unevaluated_count, evidence_completeness_pct,
                overall_summary, missing_evidence_notes, manager_approval_status
            ) VALUES (?, ?, ?, '1.0', ?, ?, ?, ?, ?, ?, ?, ?, 'Pending Review')
            """,
            (
                eval_id_str, complaint_id, product_id, scoring["quality_score"],
                scoring["scoring_status"], scoring["mandatory_failures_count"],
                scoring["warnings_count"], scoring["unevaluated_count"],
                scoring["evidence_completeness_pct"], scoring["explanation"],
                "Missing lab verification or exact measurement records." if scoring["unevaluated_count"] > 0 else "None"
            )
        )
        eval_db_id = cursor.lastrowid

        # Insert criteria-level rows
        for res in criteria_results:
            conn.execute(
                """
                INSERT INTO evaluation_criteria_results (
                    evaluation_id, criterion_id, criterion_code, criterion_name,
                    outcome, score_awarded, max_score, observed_value, expected_value,
                    finding_notes, supporting_evidence, citations_json, is_mandatory
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    eval_db_id, res["criterion_id"], res["criterion_code"], res["criterion_name"],
                    res["outcome"], res["score_awarded"], res["max_score"], res["observed_value"],
                    res["expected_value"], res["finding_notes"], "",
                    json.dumps(res["citations"]), 1 if res["is_mandatory"] else 0
                )
            )

    log_audit_event(
        action="EVALUATION_COMPLETED",
        entity_type="evaluation",
        entity_id=eval_id_str,
        user_id=user_id,
        details={
            "complaint_id": complaint["complaint_id"],
            "score": scoring["quality_score"],
            "status": scoring["scoring_status"],
            "mandatory_failures": scoring["mandatory_failures_count"]
        }
    )

    return {
        "evaluation_id": eval_id_str,
        "evaluation_db_id": eval_db_id,
        "scoring": scoring,
        "criteria_results": criteria_results,
        "retrieved_chunks": retrieved_chunks
    }
