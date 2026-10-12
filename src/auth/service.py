"""Authentication service with secure password hashing and session support."""
import hashlib
import os
import secrets
from typing import Optional, Dict, Any, List
from src.database.connection import get_db
from src.audit.logger import log_audit_event

def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hashes a password with PBKDF2-HMAC-SHA256 and a secure salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return key.hex(), salt

def verify_password(stored_hash: str, salt: str, password_attempt: str) -> bool:
    """Verifies a password attempt against stored hash and salt."""
    attempt_hash, _ = hash_password(password_attempt, salt)
    return secrets.compare_digest(stored_hash, attempt_hash)

def create_user(
    username: str,
    password: str,
    full_name: str,
    email: str,
    role: str,
    customer_id: Optional[int] = None,
    created_by_user_id: Optional[int] = None
) -> int:
    """Creates or updates a user record with securely hashed password."""
    pwd_hash, salt = hash_password(password)
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username.strip(),)).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE users SET password_hash = ?, salt = ?, full_name = ?, email = ?, role = ?, customer_id = ?, is_active = 1
                WHERE id = ?
                """,
                (pwd_hash, salt, full_name.strip(), email.strip(), role, customer_id, existing["id"])
            )
            return existing["id"]
        cursor = conn.execute(
            """
            INSERT INTO users (username, password_hash, salt, full_name, email, role, customer_id, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (username.strip(), pwd_hash, salt, full_name.strip(), email.strip(), role, customer_id)
        )
        user_id = cursor.lastrowid
        
    log_audit_event(
        action="USER_CREATED",
        entity_type="user",
        entity_id=str(user_id),
        user_id=created_by_user_id,
        details={"username": username, "role": role, "email": email}
    )
    return user_id

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticates a user against database credentials."""
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT id, username, password_hash, salt, full_name, email, role, customer_id, is_active
            FROM users WHERE username = ?
            """,
            (username.strip(),)
        ).fetchone()
        
        if not row:
            return None
        
        user_dict = dict(row)
        if not user_dict.get("is_active"):
            return None
            
        if verify_password(user_dict["password_hash"], user_dict["salt"], password):
            # Exclude hashes from returned dictionary
            del user_dict["password_hash"]
            del user_dict["salt"]
            log_audit_event(
                action="USER_LOGIN_SUCCESS",
                entity_type="user",
                entity_id=str(user_dict["id"]),
                user_id=user_dict["id"]
            )
            return user_dict
        else:
            log_audit_event(
                action="USER_LOGIN_FAILED",
                entity_type="user",
                entity_id=str(user_dict["id"]),
                details={"username": username}
            )
            return None

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Fetches user metadata by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username, full_name, email, role, customer_id, is_active, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        return dict(row) if row else None

def list_users() -> List[Dict[str, Any]]:
    """Lists all users in the system."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT u.id, u.username, u.full_name, u.email, u.role, u.customer_id, u.is_active, u.created_at,
                   c.name as customer_name
            FROM users u
            LEFT JOIN customers c ON u.customer_id = c.id
            ORDER BY u.id ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]
