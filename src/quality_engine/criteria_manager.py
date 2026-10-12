"""Quality criteria configuration and management."""
from typing import List, Dict, Any, Optional
from src.database.connection import get_db
from src.audit.logger import log_audit_event

def create_quality_criterion(
    criterion_code: str,
    name: str,
    category: str,
    criterion_type: str,
    product_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    description: Optional[str] = None,
    measurement_unit: Optional[str] = None,
    expected_value: Optional[str] = None,
    min_allowed: Optional[float] = None,
    max_allowed: Optional[float] = None,
    evaluation_method: Optional[str] = None,
    weight: float = 1.0,
    severity: str = "Major",
    is_mandatory: bool = False,
    pass_threshold: float = 100.0,
    warning_threshold: float = 70.0,
    failure_threshold: float = 0.0,
    rule_version: str = "1.0",
    approval_status: str = "Approved",
    effective_date: Optional[str] = None,
    expiry_date: Optional[str] = None,
    user_id: Optional[int] = None
) -> int:
    """Creates or updates a quality evaluation criterion."""
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM quality_criteria WHERE criterion_code = ?", (criterion_code.strip().upper(),)).fetchone()
        if existing:
            return existing["id"]
        cursor = conn.execute(
            """
            INSERT INTO quality_criteria (
                criterion_code, name, description, product_id, customer_id, category,
                criterion_type, measurement_unit, expected_value, min_allowed, max_allowed,
                evaluation_method, weight, severity, is_mandatory, pass_threshold,
                warning_threshold, failure_threshold, rule_version, approval_status,
                effective_date, expiry_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                criterion_code.strip().upper(), name.strip(), description, product_id, customer_id,
                category, criterion_type, measurement_unit, expected_value, min_allowed, max_allowed,
                evaluation_method, weight, severity, 1 if is_mandatory else 0, pass_threshold,
                warning_threshold, failure_threshold, rule_version, approval_status,
                effective_date, expiry_date
            )
        )
        c_id = cursor.lastrowid

    log_audit_event(
        action="QUALITY_CRITERION_CREATED",
        entity_type="quality_criterion",
        entity_id=criterion_code,
        user_id=user_id,
        details={"name": name, "type": criterion_type, "mandatory": is_mandatory, "weight": weight}
    )
    return c_id

def get_applicable_criteria(product_id: int, customer_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Retrieves all approved, active criteria applicable to the given product and customer.
    Includes both product-specific criteria and global (product_id IS NULL) standards.
    """
    sql = """
        SELECT * FROM quality_criteria
        WHERE approval_status = 'Approved'
          AND (product_id = ? OR product_id IS NULL)
    """
    params = [product_id]
    
    if customer_id:
        sql += " AND (customer_id = ? OR customer_id IS NULL)"
        params.append(customer_id)
    else:
        sql += " AND customer_id IS NULL"
        
    sql += " ORDER BY is_mandatory DESC, weight DESC"

    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

def list_all_criteria() -> List[Dict[str, Any]]:
    """Lists all configured criteria with product and customer names."""
    sql = """
        SELECT c.*, p.name as product_name, p.sku as product_sku, cust.name as customer_name
        FROM quality_criteria c
        LEFT JOIN products p ON c.product_id = p.id
        LEFT JOIN customers cust ON c.customer_id = cust.id
        ORDER BY c.created_at DESC
    """
    with get_db() as conn:
        rows = conn.execute(sql).fetchall()
        return [dict(row) for row in rows]
