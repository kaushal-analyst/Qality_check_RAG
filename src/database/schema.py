"""Database schema DDL and table initialization for Code Space Techlab Quality AI."""
import sqlite3
from src.database.connection import get_db

SCHEMA_SQL = """
-- Users and Roles
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('Admin', 'Quality Manager', 'Quality Engineer', 'Customer', 'Management Viewer')),
    customer_id INTEGER,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
);

-- Customers and Retailers (e.g. IKEA, Target, Direct Clients)
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    customer_type TEXT NOT NULL CHECK(customer_type IN ('IKEA', 'Retailer', 'Direct Customer', 'Internal')),
    contact_name TEXT,
    contact_email TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Product Registry
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    materials_summary TEXT,
    batch_prefix TEXT,
    target_market TEXT,
    revision TEXT DEFAULT '1.0',
    status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Archived', 'Pending Approval')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Product-Customer Specific Requirements
CREATE TABLE IF NOT EXISTS product_customer_specs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    spec_code TEXT NOT NULL,
    specific_requirements TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, customer_id, spec_code),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

-- Document Registry
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT UNIQUE NOT NULL,
    product_id INTEGER NOT NULL,
    customer_id INTEGER,
    title TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN (
        'Product Specification',
        'Bill of Materials (BOM)',
        'Chemical Safety & REACH',
        'Manufacturing SOP',
        'Quality-Control Checklist',
        'Inspection & Lab Test',
        'Customer-Specific Requirement',
        'Regulatory & Certification',
        'Historical CAPA'
    )),
    revision TEXT NOT NULL DEFAULT '1.0',
    file_hash TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    effective_date TEXT,
    expiry_date TEXT,
    approval_status TEXT NOT NULL DEFAULT 'Approved' CHECK(approval_status IN ('Draft', 'Approved', 'Superseded', 'Rejected')),
    superseded_by_id INTEGER,
    uploaded_by_user_id INTEGER,
    extraction_status TEXT DEFAULT 'Success' CHECK(extraction_status IN ('Pending', 'Processing', 'Success', 'Failed')),
    extraction_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
    FOREIGN KEY (superseded_by_id) REFERENCES documents(id) ON DELETE SET NULL,
    FOREIGN KEY (uploaded_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Document Chunks for Retrieval
CREATE TABLE IF NOT EXISTS document_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id TEXT UNIQUE NOT NULL,
    document_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    customer_id INTEGER,
    chunk_index INTEGER NOT NULL,
    page_number INTEGER DEFAULT 1,
    section_title TEXT,
    content TEXT NOT NULL,
    token_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
);

-- Quality Evaluation Criteria (Configurable)
CREATE TABLE IF NOT EXISTS quality_criteria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    criterion_code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    product_id INTEGER,
    customer_id INTEGER,
    category TEXT NOT NULL CHECK(category IN (
        'Dimensional & Tolerances',
        'Material & Chemical',
        'Visual & Aesthetic',
        'Structural & Functional',
        'Packaging & Labeling',
        'Documentation & Compliance'
    )),
    criterion_type TEXT NOT NULL CHECK(criterion_type IN (
        'Numeric Range',
        'Boolean Check',
        'Qualitative',
        'Required Document',
        'Test Result'
    )),
    measurement_unit TEXT,
    expected_value TEXT,
    min_allowed REAL,
    max_allowed REAL,
    evaluation_method TEXT,
    weight REAL DEFAULT 1.0,
    severity TEXT NOT NULL DEFAULT 'Major' CHECK(severity IN ('Critical', 'Major', 'Minor')),
    is_mandatory INTEGER NOT NULL DEFAULT 0,
    pass_threshold REAL DEFAULT 100.0,
    warning_threshold REAL DEFAULT 70.0,
    failure_threshold REAL DEFAULT 0.0,
    source_doc_id INTEGER,
    rule_version TEXT DEFAULT '1.0',
    approval_status TEXT DEFAULT 'Approved' CHECK(approval_status IN ('Draft', 'Approved', 'Archived')),
    effective_date TEXT,
    expiry_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
    FOREIGN KEY (source_doc_id) REFERENCES documents(id) ON DELETE SET NULL
);

-- Complaint Records
CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id TEXT UNIQUE NOT NULL,
    date_received TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reporter_type TEXT NOT NULL CHECK(reporter_type IN ('Customer', 'Retailer', 'Internal Employee', 'Field Inspector')),
    customer_id INTEGER,
    product_id INTEGER NOT NULL,
    sku TEXT NOT NULL,
    order_batch_number TEXT,
    category TEXT NOT NULL CHECK(category IN (
        'Physical damage',
        'Dimensional defects',
        'Material defects',
        'Chemical or material concerns',
        'Color or finish defects',
        'Packaging issues',
        'Functional failure',
        'Labeling or documentation issues',
        'Delivery-related concerns',
        'Other or unknown'
    )),
    description TEXT NOT NULL,
    quantity_affected INTEGER DEFAULT 1,
    manufacturing_date TEXT,
    severity TEXT NOT NULL CHECK(severity IN ('Low', 'Medium', 'High', 'Critical')),
    urgency TEXT NOT NULL CHECK(urgency IN ('Low', 'Medium', 'Urgent')),
    current_status TEXT NOT NULL DEFAULT 'Submitted' CHECK(current_status IN (
        'Submitted',
        'Triaged',
        'Under Investigation',
        'Awaiting Evidence/Testing',
        'Manager Review',
        'Approved',
        'Rejected',
        'Escalated',
        'Closed'
    )),
    assigned_owner_id INTEGER,
    due_date TEXT,
    customer_visible_notes TEXT,
    internal_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_owner_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Complaint Attachments
CREATE TABLE IF NOT EXISTS complaint_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
);

-- Complaint Status Lifecycle History
CREATE TABLE IF NOT EXISTS complaint_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    changed_by_user_id INTEGER,
    change_notes TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Quality Evaluation Runs (Immutable Run Records)
CREATE TABLE IF NOT EXISTS evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluation_id TEXT UNIQUE NOT NULL,
    complaint_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    rule_version TEXT NOT NULL,
    quality_score REAL,
    scoring_status TEXT NOT NULL CHECK(scoring_status IN ('Pass', 'Warning', 'Fail', 'Inconclusive')),
    mandatory_failures_count INTEGER DEFAULT 0,
    warnings_count INTEGER DEFAULT 0,
    unevaluated_count INTEGER DEFAULT 0,
    evidence_completeness_pct REAL DEFAULT 0.0,
    overall_summary TEXT,
    missing_evidence_notes TEXT,
    manager_approval_status TEXT DEFAULT 'Pending Review' CHECK(manager_approval_status IN (
        'Pending Review',
        'Approved',
        'Rejected',
        'Escalated'
    )),
    manager_notes TEXT,
    reviewed_by_user_id INTEGER,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Criterion-Level Evaluation Results
CREATE TABLE IF NOT EXISTS evaluation_criteria_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluation_id INTEGER NOT NULL,
    criterion_id INTEGER NOT NULL,
    criterion_code TEXT NOT NULL,
    criterion_name TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK(outcome IN ('Pass', 'Fail', 'Warning', 'Not Evaluated', 'Insufficient Evidence')),
    score_awarded REAL NOT NULL,
    max_score REAL NOT NULL,
    observed_value TEXT,
    expected_value TEXT,
    finding_notes TEXT,
    supporting_evidence TEXT,
    citations_json TEXT,
    is_mandatory INTEGER NOT NULL,
    FOREIGN KEY (evaluation_id) REFERENCES evaluations(id) ON DELETE CASCADE,
    FOREIGN KEY (criterion_id) REFERENCES quality_criteria(id) ON DELETE CASCADE
);

-- Risk Assessments
CREATE TABLE IF NOT EXISTS risk_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluation_id INTEGER NOT NULL,
    complaint_id INTEGER NOT NULL,
    severity_level TEXT NOT NULL CHECK(severity_level IN ('Low', 'Medium', 'High', 'Critical')),
    frequency_score INTEGER DEFAULT 1,
    units_affected_score INTEGER DEFAULT 1,
    overall_risk_level TEXT NOT NULL CHECK(overall_risk_level IN ('Low', 'Medium', 'High', 'Critical')),
    risk_score REAL NOT NULL,
    escalation_required INTEGER DEFAULT 0,
    safety_flag INTEGER DEFAULT 0,
    rationale TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evaluation_id) REFERENCES evaluations(id) ON DELETE CASCADE,
    FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
);

-- Root-Cause Hypotheses
CREATE TABLE IF NOT EXISTS root_cause_hypotheses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluation_id INTEGER NOT NULL,
    complaint_id INTEGER NOT NULL,
    category TEXT NOT NULL CHECK(category IN (
        'Raw Materials',
        'Supplier Variation',
        'Manufacturing Process',
        'Machine Settings',
        'Packaging',
        'Transportation/Handling',
        'Inspection Gaps',
        'Documentation Errors'
    )),
    hypothesis_statement TEXT NOT NULL,
    supporting_evidence TEXT,
    contradicting_evidence TEXT,
    missing_information TEXT,
    verification_status TEXT DEFAULT 'Proposed' CHECK(verification_status IN ('Proposed', 'Under Investigation', 'Confirmed', 'Rejected')),
    likelihood TEXT DEFAULT 'Medium' CHECK(likelihood IN ('High', 'Medium', 'Low')),
    FOREIGN KEY (evaluation_id) REFERENCES evaluations(id) ON DELETE CASCADE,
    FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
);

-- CAPA Tasks (Corrective and Preventive Actions)
CREATE TABLE IF NOT EXISTS capa_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL,
    evaluation_id INTEGER,
    capa_type TEXT NOT NULL CHECK(capa_type IN ('Containment', 'Corrective', 'Preventive')),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    assigned_to_user_id INTEGER,
    department TEXT NOT NULL,
    priority TEXT NOT NULL CHECK(priority IN ('Critical', 'High', 'Medium', 'Low')),
    due_date TEXT,
    status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Open', 'In Progress', 'Implemented', 'Verified Effective', 'Closed')),
    outcome_notes TEXT,
    effectiveness_verification TEXT,
    verified_by_user_id INTEGER,
    verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
    FOREIGN KEY (evaluation_id) REFERENCES evaluations(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_to_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (verified_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Comprehensive Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    details_json TEXT,
    ip_address TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
"""

# FTS5 Virtual Table for Keyword Search (BM25)
FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS document_fts USING fts5(
    chunk_id UNINDEXED,
    document_id UNINDEXED,
    product_id UNINDEXED,
    customer_id UNINDEXED,
    section_title,
    content,
    tokenize = 'porter unicode61'
);
"""

def init_db():
    """Initializes tables, FTS index, and indices."""
    with get_db() as conn:
        conn.executescript(SCHEMA_SQL)
        try:
            conn.executescript(FTS_SQL)
        except sqlite3.OperationalError as e:
            # FTS5 might already exist or need special handling
            if "already exists" not in str(e):
                raise
        
        # Create helpful performance indices
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);",
            "CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);",
            "CREATE INDEX IF NOT EXISTS idx_documents_product ON documents(product_id);",
            "CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(file_hash);",
            "CREATE INDEX IF NOT EXISTS idx_chunks_doc ON document_chunks(document_id);",
            "CREATE INDEX IF NOT EXISTS idx_chunks_product ON document_chunks(product_id);",
            "CREATE INDEX IF NOT EXISTS idx_criteria_product ON quality_criteria(product_id);",
            "CREATE INDEX IF NOT EXISTS idx_complaints_product ON complaints(product_id);",
            "CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(current_status);",
            "CREATE INDEX IF NOT EXISTS idx_evaluations_complaint ON evaluations(complaint_id);",
            "CREATE INDEX IF NOT EXISTS idx_capa_complaint ON capa_tasks(complaint_id);",
            "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);"
        ]
        for idx in indices:
            conn.execute(idx)
