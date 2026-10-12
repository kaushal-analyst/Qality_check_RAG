"""FastAPI application providing headless REST API access to all quality services."""
from fastapi import FastAPI, HTTPException, status, Depends
from typing import List, Dict, Any, Optional
from src.api.schemas import (
    ComplaintCreateSchema, ComplaintStatusUpdateSchema,
    KnowledgeQuerySchema, EvaluationApprovalSchema
)
from src.complaint_management.service import (
    create_complaint, get_complaint_by_id, list_complaints, update_complaint_status
)
from src.products.service import get_product_by_id, list_products
from src.quality_engine.rule_evaluator import evaluate_complaint
from src.quality_engine.approval import review_evaluation
from src.rag.service import answer_quality_question

api_app = FastAPI(
    title="Code Space Techlab Quality AI API",
    version="1.0.0",
    description="REST API for automated quality evaluation, RAG knowledge retrieval, and complaint lifecycle."
)

@api_app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "service": "Code Space Techlab Quality AI"}

@api_app.get("/api/v1/products")
def get_products():
    return list_products()

@api_app.get("/api/v1/products/{product_id}")
def get_single_product(product_id: int):
    prod = get_product_by_id(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    return prod

@api_app.post("/api/v1/complaints")
def submit_complaint(payload: ComplaintCreateSchema):
    res = create_complaint(
        reporter_type=payload.reporter_type,
        product_id=payload.product_id,
        sku=payload.sku,
        category=payload.category,
        description=payload.description,
        severity=payload.severity,
        urgency=payload.urgency,
        customer_id=payload.customer_id,
        order_batch_number=payload.order_batch_number,
        quantity_affected=payload.quantity_affected
    )
    return res

@api_app.get("/api/v1/complaints/{complaint_id}")
def retrieve_complaint(complaint_id: int):
    c = get_complaint_by_id(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return c

@api_app.patch("/api/v1/complaints/{complaint_id}")
def change_complaint_status(complaint_id: int, payload: ComplaintStatusUpdateSchema):
    success = update_complaint_status(complaint_id, payload.new_status, change_notes=payload.notes)
    if not success:
        raise HTTPException(status_code=404, detail="Complaint not found or invalid status")
    return {"success": True, "new_status": payload.new_status}

@api_app.post("/api/v1/complaints/{complaint_id}/evaluate")
def run_evaluation(complaint_id: int):
    try:
        eval_result = evaluate_complaint(complaint_id)
        return eval_result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_app.post("/api/v1/knowledge/query")
def query_knowledge_base(payload: KnowledgeQuerySchema):
    ans = answer_quality_question(
        question=payload.question,
        product_id=payload.product_id,
        customer_id=payload.customer_id,
        top_k=payload.top_k
    )
    return ans

@api_app.post("/api/v1/evaluations/{evaluation_id}/approve")
def approve_eval(evaluation_id: int, payload: EvaluationApprovalSchema):
    res = review_evaluation(
        evaluation_db_id=evaluation_id,
        manager_decision=payload.decision,
        manager_notes=payload.notes,
        user_id=1,  # Admin/System default
        close_complaint=payload.close_complaint
    )
    return res
