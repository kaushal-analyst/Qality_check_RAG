"""Product and Customer Management Service."""
from typing import Optional, List, Dict, Any
from src.database.connection import get_db
from src.audit.logger import log_audit_event

# ----------------- Customer Management -----------------

def create_customer(
    code: str,
    name: str,
    customer_type: str,
    contact_name: Optional[str] = None,
    contact_email: Optional[str] = None,
    notes: Optional[str] = None,
    user_id: Optional[int] = None
) -> int:
    """Creates or retrieves a customer entity."""
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM customers WHERE code = ?", (code.strip().upper(),)).fetchone()
        if existing:
            return existing["id"]
        cursor = conn.execute(
            """
            INSERT INTO customers (code, name, customer_type, contact_name, contact_email, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (code.strip().upper(), name.strip(), customer_type, contact_name, contact_email, notes)
        )
        customer_id = cursor.lastrowid
        
    log_audit_event("CUSTOMER_CREATED", "customer", str(customer_id), user_id, {"code": code, "name": name})
    return customer_id

def list_customers() -> List[Dict[str, Any]]:
    """Retrieves all registered customers."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM customers ORDER BY name ASC").fetchall()
        return [dict(row) for row in rows]

def get_customer_by_id(customer_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves customer details by ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        return dict(row) if row else None

# ----------------- Product Management -----------------

def create_product(
    sku: str,
    name: str,
    category: str,
    description: Optional[str] = None,
    materials_summary: Optional[str] = None,
    batch_prefix: Optional[str] = None,
    target_market: Optional[str] = None,
    revision: str = "1.0",
    status: str = "Active",
    user_id: Optional[int] = None
) -> int:
    """Registers or retrieves a product in the catalog."""
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM products WHERE sku = ?", (sku.strip().upper(),)).fetchone()
        if existing:
            return existing["id"]
        cursor = conn.execute(
            """
            INSERT INTO products (sku, name, category, description, materials_summary, batch_prefix, target_market, revision, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (sku.strip().upper(), name.strip(), category.strip(), description, materials_summary, batch_prefix, target_market, revision, status)
        )
        product_id = cursor.lastrowid

    log_audit_event("PRODUCT_CREATED", "product", str(product_id), user_id, {"sku": sku, "name": name})
    return product_id

def update_product(
    product_id: int,
    name: str,
    category: str,
    description: Optional[str],
    materials_summary: Optional[str],
    batch_prefix: Optional[str],
    target_market: Optional[str],
    revision: str,
    status: str,
    user_id: Optional[int] = None
) -> bool:
    """Updates an existing product's metadata."""
    with get_db() as conn:
        conn.execute(
            """
            UPDATE products
            SET name = ?, category = ?, description = ?, materials_summary = ?, batch_prefix = ?,
                target_market = ?, revision = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (name.strip(), category.strip(), description, materials_summary, batch_prefix, target_market, revision, status, product_id)
        )
    log_audit_event("PRODUCT_UPDATED", "product", str(product_id), user_id, {"status": status, "revision": revision})
    return True

def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves full product profile by ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return dict(row) if row else None

def get_product_by_sku(sku: str) -> Optional[Dict[str, Any]]:
    """Retrieves product by unique SKU."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM products WHERE sku = ?", (sku.strip().upper(),)).fetchone()
        return dict(row) if row else None

def list_products(status_filter: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lists products with optional filtering and search."""
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    if status_filter and status_filter != "All":
        query += " AND status = ?"
        params.append(status_filter)
    if search:
        query += " AND (sku LIKE ? OR name LIKE ? OR category LIKE ?)"
        term = f"%{search.strip()}%"
        params.extend([term, term, term])
    query += " ORDER BY name ASC"
    
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

# ----------------- Customer-Product Specific Specs -----------------

def set_customer_product_spec(
    product_id: int,
    customer_id: int,
    spec_code: str,
    specific_requirements: str,
    notes: Optional[str] = None,
    user_id: Optional[int] = None
) -> int:
    """Configures customer-specific specifications for a product (e.g. IKEA custom packaging, extra strength test)."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO product_customer_specs (product_id, customer_id, spec_code, specific_requirements, notes)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(product_id, customer_id, spec_code) DO UPDATE SET
                specific_requirements = excluded.specific_requirements,
                notes = excluded.notes
            """,
            (product_id, customer_id, spec_code.strip(), specific_requirements.strip(), notes)
        )
        spec_id = cursor.lastrowid
    log_audit_event("CUSTOMER_SPEC_CONFIGURED", "product_customer_spec", str(spec_id), user_id, {"product_id": product_id, "customer_id": customer_id})
    return spec_id

def get_specs_for_product_and_customer(product_id: int, customer_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Retrieves all customer-specific requirements for a given product."""
    query = """
        SELECT s.*, c.name as customer_name, c.code as customer_code, c.customer_type
        FROM product_customer_specs s
        JOIN customers c ON s.customer_id = c.id
        WHERE s.product_id = ?
    """
    params = [product_id]
    if customer_id:
        query += " AND s.customer_id = ?"
        params.append(customer_id)
        
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
