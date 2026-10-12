"""Audit logging service for tracking system actions and compliance."""
import json
import sqlite3
from typing import Optional, Any, Dict
from src.database.connection import get_db

def log_audit_event(
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    user_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> int:
    """Records an immutable audit event in the database."""
    details_str = json.dumps(details, default=str) if details else None
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, action, entity_type, str(entity_id) if entity_id else None, details_str, ip_address)
        )
        return cursor.lastrowid

def get_recent_audit_logs(limit: int = 100, entity_type: Optional[str] = None) -> list[dict]:
    """Retrieves recent audit log entries."""
    query = """
        SELECT a.*, u.username, u.full_name, u.role
        FROM audit_logs a
        LEFT JOIN users u ON a.user_id = u.id
    """
    params = []
    if entity_type:
        query += " WHERE a.entity_type = ?"
        params.append(entity_type)
    query += " ORDER BY a.timestamp DESC LIMIT ?"
    params.append(limit)
    
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
