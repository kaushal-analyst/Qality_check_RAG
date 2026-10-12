"""Pydantic data models for request validation and type safety."""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserBase(BaseModel):
    username: str
    full_name: str
    email: str
    role: str
    customer_id: Optional[int] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: Any
    updated_at: Any

class CustomerModel(BaseModel):
    id: Optional[int] = None
    code: str
    name: str
    customer_type: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[Any] = None

class ProductModel(BaseModel):
    id: Optional[int] = None
    sku: str
    name: str
    category: str
    description: Optional[str] = None
    materials_summary: Optional[str] = None
    batch_prefix: Optional[str] = None
    target_market: Optional[str] = None
    revision: str = "1.0"
    status: str = "Active"
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None

class DocumentModel(BaseModel):
    id: Optional[int] = None
    document_id: str
    product_id: int
    customer_id: Optional[int] = None
    title: str
    category: str
    revision: str = "1.0"
    file_hash: str
    file_path: str
    file_name: str
    file_type: str
    file_size: int
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None
    approval_status: str = "Approved"
    superseded_by_id: Optional[int] = None
    uploaded_by_user_id: Optional[int] = None
    extraction_status: str = "Success"
    extraction_notes: Optional[str] = None
    created_at: Optional[Any] = None

class DocumentChunkModel(BaseModel):
    id: Optional[int] = None
    chunk_id: str
    document_id: int
    product_id: int
    customer_id: Optional[int] = None
    chunk_index: int
    page_number: int = 1
    section_title: Optional[str] = None
    content: str
    token_count: int = 0

class QualityCriterionModel(BaseModel):
    id: Optional[int] = None
    criterion_code: str
    name: str
    description: Optional[str] = None
    product_id: Optional[int] = None
    customer_id: Optional[int] = None
    category: str
    criterion_type: str
    measurement_unit: Optional[str] = None
    expected_value: Optional[str] = None
    min_allowed: Optional[float] = None
    max_allowed: Optional[float] = None
    evaluation_method: Optional[str] = None
    weight: float = 1.0
    severity: str = "Major"
    is_mandatory: bool = False
    pass_threshold: float = 100.0
    warning_threshold: float = 70.0
    failure_threshold: float = 0.0
    source_doc_id: Optional[int] = None
    rule_version: str = "1.0"
    approval_status: str = "Approved"
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None

class ComplaintModel(BaseModel):
    id: Optional[int] = None
    complaint_id: str
    date_received: Optional[Any] = None
    reporter_type: str
    customer_id: Optional[int] = None
    product_id: int
    sku: str
    order_batch_number: Optional[str] = None
    category: str
    description: str
    quantity_affected: int = 1
    manufacturing_date: Optional[str] = None
    severity: str
    urgency: str
    current_status: str = "Submitted"
    assigned_owner_id: Optional[int] = None
    due_date: Optional[str] = None
    customer_visible_notes: Optional[str] = None
    internal_notes: Optional[str] = None
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None

class EvaluationCriterionResultModel(BaseModel):
    criterion_id: int
    criterion_code: str
    criterion_name: str
    outcome: str  # Pass, Fail, Warning, Not Evaluated, Insufficient Evidence
    score_awarded: float
    max_score: float
    observed_value: Optional[str] = None
    expected_value: Optional[str] = None
    finding_notes: Optional[str] = None
    supporting_evidence: Optional[str] = None
    citations: List[Dict[str, Any]] = []
    is_mandatory: bool = False

class EvaluationResult(BaseModel):
    evaluation_id: str
    complaint_id: int
    product_id: int
    rule_version: str
    quality_score: Optional[float] = None
    scoring_status: str  # Pass, Warning, Fail, Inconclusive
    mandatory_failures_count: int = 0
    warnings_count: int = 0
    unevaluated_count: int = 0
    evidence_completeness_pct: float = 0.0
    overall_summary: str
    missing_evidence_notes: Optional[str] = None
    criteria_results: List[EvaluationCriterionResultModel] = []
    risk_level: str = "Low"
    safety_flag: bool = False

class RootCauseHypothesisModel(BaseModel):
    id: Optional[int] = None
    evaluation_id: int
    complaint_id: int
    category: str
    hypothesis_statement: str
    supporting_evidence: Optional[str] = None
    contradicting_evidence: Optional[str] = None
    missing_information: Optional[str] = None
    verification_status: str = "Proposed"
    likelihood: str = "Medium"

class CapaTaskModel(BaseModel):
    id: Optional[int] = None
    complaint_id: int
    evaluation_id: Optional[int] = None
    capa_type: str  # Containment, Corrective, Preventive
    title: str
    description: str
    assigned_to_user_id: Optional[int] = None
    department: str
    priority: str
    due_date: Optional[str] = None
    status: str = "Open"
    outcome_notes: Optional[str] = None
    effectiveness_verification: Optional[str] = None
    verified_by_user_id: Optional[int] = None
