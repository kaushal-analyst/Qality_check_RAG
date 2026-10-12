"""Pydantic schemas for the REST API."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ComplaintCreateSchema(BaseModel):
    reporter_type: str = Field(..., example="Retailer")
    product_id: int = Field(..., example=1)
    sku: str = Field(..., example="NDT-800")
    category: str = Field(..., example="Dimensional defects")
    description: str = Field(..., example="Table leg length measured 745mm against 750mm spec.")
    severity: str = Field(..., example="High")
    urgency: str = Field(..., example="Medium")
    customer_id: Optional[int] = None
    order_batch_number: Optional[str] = "BATCH-2026-A1"
    quantity_affected: int = 2

class ComplaintStatusUpdateSchema(BaseModel):
    new_status: str = Field(..., example="Under Investigation")
    notes: Optional[str] = None

class KnowledgeQuerySchema(BaseModel):
    question: str = Field(..., example="What is the allowable moisture content tolerance for Nordic Oak?")
    product_id: int = Field(..., example=1)
    customer_id: Optional[int] = None
    top_k: int = 5

class EvaluationApprovalSchema(BaseModel):
    decision: str = Field(..., example="Approved")
    notes: str = Field(..., example="Evaluated against active Rev 1.2 spec. Corrective actions confirmed.")
    close_complaint: bool = False
