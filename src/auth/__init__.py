"""Enterprise RBAC (Role-Based Access Control) module.

Defines roles, permissions, and access control decorators for the
compliance review workflow. In production this would integrate with
the organization's SSO / IdP (e.g. SAML, OIDC) and persist role
assignments in the database.
"""

from src.auth.rbac import (
    Role,
    Permission,
    require_role,
    get_current_user,
    UserContext,
    ROLE_PERMISSIONS,
)

__all__ = [
    "Role",
    "Permission",
    "require_role",
    "get_current_user",
    "UserContext",
    "ROLE_PERMISSIONS",
]
