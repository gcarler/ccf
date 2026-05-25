"""
Backward-compatibility re-exports for auth module.

All role/permission logic has been centralized in ``backend.core.permissions``.
This module now re-exports everything for existing importers.
"""

from backend.core.permissions import (  # noqa: F401
    ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, DEFAULT_ROLES, PERMISSIONS,
    ROLE_ALIASES, SECRET_KEY, VALID_ROLES, _utcnow, authenticate_user,
    create_access_token, create_refresh_token, get_all_permissions,
    get_current_active_user, get_current_user, get_default_roles,
    get_user_effective_permissions, hash_password, is_crm_privileged,
    normalize_role, oauth2_scheme, record_session, require_active_user,
    require_admin, require_coordinator_or_admin, require_module_access,
    require_pastor_or_admin, require_permission, require_staff_or_admin,
    require_teacher_or_admin, role_in)
