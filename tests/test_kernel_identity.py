"""Tests for CCF Kernel — Protocolo de Identidad y Roles."""

import uuid as _uuid

import pytest
from sqlalchemy.orm import Session

from backend import models
from backend.core.security import get_password_hash
from backend.models_kernel import (
    ActivityStatus, ChurchRole, MinistryOffice, PlatformRole,
    PlatformRoleDefinition, UserMinistry, UserPlatformRole,
    UserRoleAssignment, UserRoleHistory,
)


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def test_user(db_session: Session) -> models.User:
    """Crear un usuario de prueba con Persona vinculada."""
    user = models.User(
        username="kernel_test_user",
        email="kernel_test@ccf.test",
        password_hash=get_password_hash("testpass123"),
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    persona = models.Persona(
        id=_uuid.uuid4(),
        user_id=user.id,
        first_name="Kernel",
        last_name="Test",
        email="kernel_test@ccf.test",
    )
    db_session.add(persona)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def inactive_user(db_session: Session) -> models.User:
    """Crear un usuario inactivo de prueba con Persona vinculada."""
    user = models.User(
        username="kernel_inactive_user",
        email="kernel_inactive@ccf.test",
        password_hash=get_password_hash("testpass123"),
        role="estudiante",
        is_active=False,
    )
    db_session.add(user)
    db_session.flush()
    persona = models.Persona(
        id=_uuid.uuid4(),
        user_id=user.id,
        first_name="Kernel",
        last_name="Inactive",
        email="kernel_inactive@ccf.test",
        estado_vital="INACTIVO",
    )
    db_session.add(persona)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def platform_roles(db_session: Session):
    """Seed platform role definitions (migration does this in production)."""
    for role, perms in [
        (PlatformRole.ADMINISTRADOR, {"*": ["create", "read", "update", "delete", "admin"]}),
        (PlatformRole.GESTOR, {"crm": ["create", "read", "update"], "projects": ["create", "read", "update"]}),
        (PlatformRole.EDITOR, {"cms": ["read", "update"], "projects": ["read", "update"]}),
        (PlatformRole.LECTOR, {"crm": ["read"], "projects": ["read"]}),
    ]:
        db_session.add(PlatformRoleDefinition(role=role, permissions=perms))
    db_session.commit()


# ──────────────────────────────────────────────
# Estado Vital
# ──────────────────────────────────────────────

class TestEstadoVital:
    def test_active_user_is_active(self, db_session, test_user):
        from backend.crud.kernel import is_user_active
        assert is_user_active(db_session, test_user.id) is True

    def test_inactive_user_is_not_active(self, db_session, inactive_user):
        from backend.crud.kernel import is_user_active
        assert is_user_active(db_session, inactive_user.id) is False

    def test_inactive_user_cannot_receive_assignment(self, db_session, inactive_user):
        from backend.crud.kernel import can_receive_assignment
        assert can_receive_assignment(db_session, inactive_user.id) is False

    def test_active_user_can_receive_assignment(self, db_session, test_user):
        from backend.crud.kernel import can_receive_assignment
        assert can_receive_assignment(db_session, test_user.id) is True

    def test_set_user_inactive(self, db_session, test_user):
        from backend.crud.kernel import set_user_activity_status
        result = set_user_activity_status(db_session, test_user.id, "INACTIVO", changed_by_id=1)
        assert result is not None
        assert result.is_active is False
        # Verify cannot receive assignments after deactivation
        from backend.crud.kernel import can_receive_assignment
        assert can_receive_assignment(db_session, test_user.id) is False

    def test_set_user_back_to_active(self, db_session, inactive_user):
        from backend.crud.kernel import set_user_activity_status
        result = set_user_activity_status(db_session, inactive_user.id, "ACTIVO", changed_by_id=1)
        assert result is not None
        assert result.is_active is True


# ──────────────────────────────────────────────
# Dimensión A: Ministerios
# ──────────────────────────────────────────────

class TestDimensionAMinisterios:
    def test_add_ministry(self, db_session, test_user):
        from backend.crud.kernel import add_user_ministry, get_user_ministries
        result = add_user_ministry(db_session, test_user.id, MinistryOffice.PASTOR, is_primary=True)
        assert result is not None
        assert result["ministry"] == "PASTOR"
        assert result["is_primary"] is True

        ministries = get_user_ministries(db_session, test_user.id)
        assert len(ministries) == 1

    def test_add_duplicate_ministry_fails(self, db_session, test_user):
        from backend.crud.kernel import add_user_ministry
        add_user_ministry(db_session, test_user.id, MinistryOffice.MAESTRO)
        result = add_user_ministry(db_session, test_user.id, MinistryOffice.MAESTRO)
        assert result is None

    def test_add_multiple_ministries(self, db_session, test_user):
        from backend.crud.kernel import add_user_ministry, get_user_ministries
        add_user_ministry(db_session, test_user.id, MinistryOffice.PASTOR, is_primary=True)
        add_user_ministry(db_session, test_user.id, MinistryOffice.MAESTRO)

        ministries = get_user_ministries(db_session, test_user.id)
        assert len(ministries) == 2

    def test_set_primary_ministry(self, db_session, test_user):
        from backend.crud.kernel import add_user_ministry, set_primary_ministry, get_user_ministries
        add_user_ministry(db_session, test_user.id, MinistryOffice.MAESTRO, is_primary=True)
        add_user_ministry(db_session, test_user.id, MinistryOffice.PASTOR)

        # Change primary
        assert set_primary_ministry(db_session, test_user.id, MinistryOffice.PASTOR) is True

        ministries = get_user_ministries(db_session, test_user.id)
        primary = [m for m in ministries if m["is_primary"]]
        assert len(primary) == 1
        assert primary[0]["ministry"] == "PASTOR"

    def test_remove_ministry(self, db_session, test_user):
        from backend.crud.kernel import add_user_ministry, remove_user_ministry, get_user_ministries
        add_user_ministry(db_session, test_user.id, MinistryOffice.EVANGELISTA)
        assert remove_user_ministry(db_session, test_user.id, MinistryOffice.EVANGELISTA) is True

        ministries = get_user_ministries(db_session, test_user.id)
        assert len(ministries) == 0


# ──────────────────────────────────────────────
# Dimensión B: Roles en la Iglesia
# ──────────────────────────────────────────────

class TestDimensionBRolesIglesia:
    def test_set_church_role(self, db_session, test_user):
        from backend.crud.kernel import set_user_church_role, get_user_church_role, get_church_role_history
        result = set_user_church_role(
            db_session, test_user.id, ChurchRole.VISITANTE_ONLINE,
            changed_by_id=1, reason="Primera visita por web"
        )
        assert result is not None
        assert result["church_role"] == "VISITANTE_ONLINE"

        role = get_user_church_role(db_session, test_user.id)
        assert role is not None
        assert role["church_role"] == "VISITANTE_ONLINE"

    def test_church_role_history(self, db_session, test_user):
        from backend.crud.kernel import set_user_church_role, get_church_role_history
        set_user_church_role(db_session, test_user.id, ChurchRole.VISITANTE_ONLINE, changed_by_id=1)
        set_user_church_role(db_session, test_user.id, ChurchRole.SIMPATIZANTE, changed_by_id=1, reason="Asistió 3 semanas")

        history = get_church_role_history(db_session, test_user.id)
        assert len(history) == 2
        assert history[0]["to_role"] == "SIMPATIZANTE"
        assert history[1]["to_role"] == "VISITANTE_ONLINE"

    def test_update_existing_church_role(self, db_session, test_user):
        from backend.crud.kernel import set_user_church_role, get_user_church_role, get_church_role_history
        set_user_church_role(db_session, test_user.id, ChurchRole.VISITANTE_ONLINE, changed_by_id=1)
        set_user_church_role(db_session, test_user.id, ChurchRole.MIEMBRO_BAUTIZADO, changed_by_id=1)

        role = get_user_church_role(db_session, test_user.id)
        assert role["church_role"] == "MIEMBRO_BAUTIZADO"

        # History should have both transitions
        history = get_church_role_history(db_session, test_user.id)
        assert len(history) == 2


# ──────────────────────────────────────────────
# Dimensión C: Roles de Plataforma
# ──────────────────────────────────────────────

class TestDimensionCRolesPlataforma:
    def test_get_platform_role_definitions(self, db_session, platform_roles):
        from backend.crud.kernel import get_platform_role_definitions
        definitions = get_platform_role_definitions(db_session)
        assert len(definitions) == 4

    def test_assign_platform_role(self, db_session, test_user, platform_roles):
        from backend.crud.kernel import assign_platform_role, get_user_platform_roles
        result = assign_platform_role(
            db_session, test_user.id, "GESTOR", assigned_by_id=1
        )
        assert result is not None
        assert result["role"] == "GESTOR"

        roles = get_user_platform_roles(db_session, test_user.id)
        assert len(roles) == 1

    def test_assign_duplicate_platform_role_fails(self, db_session, test_user, platform_roles):
        from backend.crud.kernel import assign_platform_role
        assign_platform_role(db_session, test_user.id, "LECTOR", assigned_by_id=1)
        result = assign_platform_role(db_session, test_user.id, "LECTOR", assigned_by_id=1)
        assert result is None

    def test_revoke_platform_role(self, db_session, test_user, platform_roles):
        from backend.crud.kernel import assign_platform_role, revoke_platform_role, get_user_platform_roles
        assign_platform_role(db_session, test_user.id, "EDITOR", assigned_by_id=1)
        assert revoke_platform_role(db_session, test_user.id, "EDITOR") is True

        roles = get_user_platform_roles(db_session, test_user.id)
        assert len(roles) == 0

    def test_effective_permissions_single_role(self, db_session, test_user, platform_roles):
        from backend.crud.kernel import assign_platform_role, get_user_effective_permissions
        assign_platform_role(db_session, test_user.id, "LECTOR", assigned_by_id=1)

        perms = get_user_effective_permissions(db_session, test_user.id)
        assert "crm" in perms
        assert "read" in perms["crm"]

    def test_effective_permissions_multiple_roles(self, db_session, test_user, platform_roles):
        from backend.crud.kernel import assign_platform_role, get_user_effective_permissions
        assign_platform_role(db_session, test_user.id, "LECTOR", assigned_by_id=1)
        assign_platform_role(db_session, test_user.id, "EDITOR", assigned_by_id=1)

        perms = get_user_effective_permissions(db_session, test_user.id)
        # LECTOR + EDITOR = read + update on cms, projects
        assert "cms" in perms
        assert "update" in perms["cms"]

    def test_admin_wildcard_permissions(self, db_session, test_user, platform_roles):
        from backend.crud.kernel import assign_platform_role, get_user_effective_permissions
        assign_platform_role(db_session, test_user.id, "ADMINISTRADOR", assigned_by_id=1)

        perms = get_user_effective_permissions(db_session, test_user.id)
        assert "*" in perms
        assert "create" in perms["*"]
        assert "admin" in perms["*"]


# ──────────────────────────────────────────────
# RBAC Engine
# ──────────────────────────────────────────────

class TestKernelRBAC:
    def test_inactive_user_has_no_permissions(self, db_session, inactive_user, platform_roles):
        from backend.core.kernel_rbac import has_permission
        from backend.crud.kernel import assign_platform_role

        assign_platform_role(db_session, inactive_user.id, "ADMINISTRADOR", assigned_by_id=1)
        # Even with admin role, inactive users have no permissions
        assert has_permission(db_session, inactive_user, "system:config") is False

    def test_has_permission_via_kernel_role(self, db_session, test_user, platform_roles):
        from backend.core.kernel_rbac import has_permission
        from backend.crud.kernel import assign_platform_role

        assign_platform_role(db_session, test_user.id, "GESTOR", assigned_by_id=1)
        assert has_permission(db_session, test_user, "crm:read") is True
        assert has_permission(db_session, test_user, "crm:edit") is True
        assert has_permission(db_session, test_user, "crm:manage") is True

    def test_permission_hierarchy_manage_implies_read(self, db_session, test_user, platform_roles):
        from backend.core.kernel_rbac import has_permission
        from backend.crud.kernel import assign_platform_role

        assign_platform_role(db_session, test_user.id, "GESTOR", assigned_by_id=1)
        # GESTOR has crm:manage, which should imply crm:read
        assert has_permission(db_session, test_user, "crm:read") is True
        assert has_permission(db_session, test_user, "crm:edit") is True


# ──────────────────────────────────────────────
# Perfil Completo
# ──────────────────────────────────────────────

class TestKernelProfile:
    def test_get_kernel_profile(self, db_session, test_user, platform_roles):
        from backend.crud.kernel import add_user_ministry, assign_platform_role, get_kernel_profile, set_user_church_role
        from backend.models_kernel import MinistryOffice, ChurchRole

        add_user_ministry(db_session, test_user.id, MinistryOffice.PASTOR, is_primary=True)
        set_user_church_role(db_session, test_user.id, ChurchRole.LIDER, changed_by_id=1)
        assign_platform_role(db_session, test_user.id, "GESTOR", assigned_by_id=1)

        profile = get_kernel_profile(db_session, test_user.id)
        assert profile is not None
        assert profile["user_id"] == test_user.id
        assert profile["estado_vital"] == "ACTIVO"
        assert len(profile["dimension_a_ministerios"]) == 1
        assert profile["dimension_b_rol_iglesia"] is not None
        assert len(profile["dimension_c_roles_plataforma"]) == 1
        assert "permisos_efectivos" in profile
