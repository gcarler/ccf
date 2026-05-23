"""
Backward-compatibility re-exports for auth module.

All role/permission logic has been centralized in ``backend.core.permissions``.
This module now re-exports everything for existing importers.
"""

from backend.core.permissions import (  # noqa: F401
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    oauth2_scheme,
    ROLE_ALIASES,
    VALID_ROLES,
    PERMISSIONS,
    DEFAULT_ROLES,
    _utcnow,
    normalize_role,
    role_in,
    is_crm_privileged,
    get_all_permissions,
    get_default_roles,
    create_access_token,
    create_refresh_token,
    record_session,
    get_current_user,
    get_current_active_user,
    require_permission,
    require_active_user,
    require_admin,
    require_staff_or_admin,
    require_teacher_or_admin,
    require_coordinator_or_admin,
    require_pastor_or_admin,
    authenticate_user,
    hash_password,
)
