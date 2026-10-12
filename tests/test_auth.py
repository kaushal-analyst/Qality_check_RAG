"""Automated tests for user authentication, password hashing, and RBAC permissions."""
import pytest
from src.auth.service import hash_password, verify_password, authenticate_user, create_user
from src.auth.permissions import has_permission, can_access_customer_data, UserRole

def test_password_hashing():
    pwd = "SecretPassword123!"
    h1, salt1 = hash_password(pwd)
    assert len(h1) > 20
    assert len(salt1) > 10
    assert verify_password(h1, salt1, pwd) is True
    assert verify_password(h1, salt1, "WrongPassword") is False

def test_authentication_workflow():
    auth_success = authenticate_user("admin", "Quality2026!")
    assert auth_success is not None
    assert auth_success["username"] == "admin"
    assert auth_success["role"] == "Admin"
    assert "password_hash" not in auth_success

    auth_failed = authenticate_user("admin", "WrongPass123")
    assert auth_failed is None

def test_role_based_permissions():
    # Admin has all permissions
    assert has_permission(UserRole.ADMIN, "manage_users") is True
    assert has_permission(UserRole.ADMIN, "approve_evaluations") is True

    # Quality Manager cannot manage users, but can approve evaluations
    assert has_permission(UserRole.QUALITY_MANAGER, "manage_users") is False
    assert has_permission(UserRole.QUALITY_MANAGER, "approve_evaluations") is True

    # Quality Engineer can evaluate but cannot approve evaluations or manage users
    assert has_permission(UserRole.QUALITY_ENGINEER, "evaluate_complaints") is True
    assert has_permission(UserRole.QUALITY_ENGINEER, "approve_evaluations") is False

    # Customer can only submit and view own complaints
    assert has_permission(UserRole.CUSTOMER, "submit_complaint") is True
    assert has_permission(UserRole.CUSTOMER, "approve_evaluations") is False
    assert has_permission(UserRole.CUSTOMER, "view_all_complaints") is False

def test_customer_data_isolation():
    # Internal staff can access any customer's data
    assert can_access_customer_data("Admin", None, 1) is True
    assert can_access_customer_data("Quality Manager", None, 2) is True

    # Customer user can ONLY access their own customer ID
    assert can_access_customer_data("Customer", user_customer_id=1, target_customer_id=1) is True
    assert can_access_customer_data("Customer", user_customer_id=1, target_customer_id=2) is False
