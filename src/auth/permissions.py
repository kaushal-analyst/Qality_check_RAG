"""Role-Based Access Control (RBAC) and permissions management."""
from enum import Enum
from typing import Dict, Set, Optional

class UserRole(str, Enum):
    ADMIN = "Admin"
    QUALITY_MANAGER = "Quality Manager"
    QUALITY_ENGINEER = "Quality Engineer"
    CUSTOMER = "Customer"
    MANAGEMENT_VIEWER = "Management Viewer"

# Permission definitions mapped to capabilities
ROLE_PERMISSIONS: Dict[UserRole, Set[str]] = {
    UserRole.ADMIN: {
        "manage_users",
        "manage_customers",
        "manage_products",
        "manage_documents",
        "manage_criteria",
        "evaluate_complaints",
        "approve_evaluations",
        "close_complaints",
        "view_all_complaints",
        "edit_complaints",
        "view_internal_notes",
        "view_audit_logs",
        "view_dashboard",
        "export_reports",
        "manage_capa"
    },
    UserRole.QUALITY_MANAGER: {
        "manage_products",
        "manage_documents",
        "manage_criteria",
        "evaluate_complaints",
        "approve_evaluations",
        "close_complaints",
        "view_all_complaints",
        "edit_complaints",
        "view_internal_notes",
        "view_audit_logs",
        "view_dashboard",
        "export_reports",
        "manage_capa"
    },
    UserRole.QUALITY_ENGINEER: {
        "view_products",
        "manage_documents",
        "evaluate_complaints",
        "view_all_complaints",
        "edit_complaints",
        "view_internal_notes",
        "view_dashboard",
        "export_reports",
        "manage_capa"
    },
    UserRole.MANAGEMENT_VIEWER: {
        "view_products",
        "view_all_complaints",
        "view_dashboard",
        "export_reports"
    },
    UserRole.CUSTOMER: {
        "submit_complaint",
        "view_own_complaints",
        "view_own_products"
    }
}

def has_permission(role: str, permission: str) -> bool:
    """Checks whether a given role holds the specified permission."""
    try:
        user_role = UserRole(role)
        return permission in ROLE_PERMISSIONS.get(user_role, set())
    except ValueError:
        return False

def can_access_customer_data(user_role: str, user_customer_id: Optional[int], target_customer_id: Optional[int]) -> bool:
    """Enforces customer data isolation. Customers can ONLY see their own data."""
    if user_role in (UserRole.ADMIN, UserRole.QUALITY_MANAGER, UserRole.QUALITY_ENGINEER, UserRole.MANAGEMENT_VIEWER):
        return True
    if user_role == UserRole.CUSTOMER:
        return user_customer_id is not None and user_customer_id == target_customer_id
    return False
