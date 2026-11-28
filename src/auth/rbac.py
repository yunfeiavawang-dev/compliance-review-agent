"""Role-Based Access Control for the KYC compliance review system.

Design rationale (enterprise deployment):
  - Financial institutions require fine-grained access control where
    "who can do what" is auditable and enforceable.
  - The buyer (IT/CISO) needs to see that the platform supports
    separation of duties — e.g. an analyst cannot approve their own
    high-risk case; only a compliance_officer or above can override
    an AI recommendation.
  - This skeleton is wired into the audit logger so every action
    records the actor's role, enabling regulatory reporting.

Production integration points:
  - SSO/OIDC: UserContext would be populated from JWT claims
  - Database: role assignments stored in a `user_roles` table
  - API gateway: @require_role enforced at the middleware layer
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class Role(str, Enum):
    """Organizational roles in the compliance review workflow."""
    ANALYST = "analyst"
    SENIOR_ANALYST = "senior_analyst"
    COMPLIANCE_OFFICER = "compliance_officer"
    ADMIN = "admin"


class Permission(str, Enum):
    """Granular permissions mapping to workflow actions."""
    # Case operations
    VIEW_CASE = "view_case"
    START_REVIEW = "start_review"
    SUBMIT_DECISION = "submit_decision"

    # Decision-level permissions (separation of duties)
    APPROVE_LOW_RISK = "approve_low_risk"
    APPROVE_MEDIUM_RISK = "approve_medium_risk"
    APPROVE_HIGH_RISK = "approve_high_risk"
    REJECT_CASE = "reject_case"
    ESCALATE_CASE = "escalate_case"
    OVERRIDE_AI = "override_ai"

    # Administrative
    VIEW_AUDIT_LOG = "view_audit_log"
    EXPORT_AUDIT_LOG = "export_audit_log"
    MANAGE_USERS = "manage_users"
    CONFIGURE_SYSTEM = "configure_system"

    # Data access (multi-tenant)
    ACCESS_OWN_TENANT = "access_own_tenant"
    ACCESS_ALL_TENANTS = "access_all_tenants"


# Role → permission mapping (least-privilege principle)
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ANALYST: {
        Permission.VIEW_CASE,
        Permission.START_REVIEW,
        Permission.APPROVE_LOW_RISK,
        Permission.ESCALATE_CASE,
        Permission.VIEW_AUDIT_LOG,
        Permission.ACCESS_OWN_TENANT,
    },
    Role.SENIOR_ANALYST: {
        Permission.VIEW_CASE,
        Permission.START_REVIEW,
        Permission.SUBMIT_DECISION,
        Permission.APPROVE_LOW_RISK,
        Permission.APPROVE_MEDIUM_RISK,
        Permission.REJECT_CASE,
        Permission.ESCALATE_CASE,
        Permission.VIEW_AUDIT_LOG,
        Permission.ACCESS_OWN_TENANT,
    },
    Role.COMPLIANCE_OFFICER: {
        Permission.VIEW_CASE,
        Permission.START_REVIEW,
        Permission.SUBMIT_DECISION,
        Permission.APPROVE_LOW_RISK,
        Permission.APPROVE_MEDIUM_RISK,
        Permission.APPROVE_HIGH_RISK,
        Permission.REJECT_CASE,
        Permission.ESCALATE_CASE,
        Permission.OVERRIDE_AI,
        Permission.VIEW_AUDIT_LOG,
        Permission.EXPORT_AUDIT_LOG,
        Permission.ACCESS_OWN_TENANT,
    },
    Role.ADMIN: set(Permission),  # full access
}


@dataclass
class UserContext:
    """Represents the authenticated user in the current session.

    In production, this is populated from the SSO token / session cookie.
    Fields like tenant_id and ip_address are captured for audit logging.
    """
    user_id: str
    username: str
    role: Role
    tenant_id: str = "default"
    email: Optional[str] = None
    ip_address: Optional[str] = None
    department: Optional[str] = None
    permissions: set[Permission] = field(default_factory=set)

    def __post_init__(self):
        if not self.permissions:
            self.permissions = ROLE_PERMISSIONS.get(self.role, set())

    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions

    def can_approve_risk_level(self, risk_rating: str) -> bool:
        """Check if the user can approve a case at the given risk level."""
        perm_map = {
            "low": Permission.APPROVE_LOW_RISK,
            "medium": Permission.APPROVE_MEDIUM_RISK,
            "high": Permission.APPROVE_HIGH_RISK,
        }
        required = perm_map.get(risk_rating)
        if required is None:
            return False
        return self.has_permission(required)


def get_current_user() -> UserContext:
    """Return the current authenticated user.

    DEMO: returns a mock user. In production this reads from the
    request context (Flask g, FastAPI Depends, or Streamlit session).
    """
    return UserContext(
        user_id="demo-user-001",
        username="demo_analyst",
        role=Role.SENIOR_ANALYST,
        tenant_id="pacific_rim_fg",
        email="analyst@pacificrim.example",
        ip_address="127.0.0.1",
    )


def require_role(*allowed_roles: Role) -> Callable:
    """Decorator that enforces role-based access on a function.

    Usage:
        @require_role(Role.COMPLIANCE_OFFICER, Role.ADMIN)
        def approve_high_risk_case(case_id: str, ...):
            ...

    In production, a PermissionDeniedError would return HTTP 403
    and log the unauthorized access attempt to the audit trail.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if user.role not in allowed_roles:
                raise PermissionError(
                    f"Access denied: {user.role.value} is not authorized. "
                    f"Required: {[r.value for r in allowed_roles]}"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_permission(permission: Permission) -> Callable:
    """Decorator that enforces a specific permission."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user.has_permission(permission):
                raise PermissionError(
                    f"Access denied: {user.username} lacks permission '{permission.value}'"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator
