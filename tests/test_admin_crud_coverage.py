"""Targeted unit tests to cover uncovered edge cases in backend/crud/admin.py.

Targets: lines 93, 120, 239, 274, 424, 520, 599, 603, 709, 711,
770, 774, 814, 943-963, 1112, 1114, 1116, 1180, 1184,
1220-1221, 1242-1243, 1250-1251, 1275-1279.
"""
import uuid
from unittest import mock as _mock

import pytest

from backend.crud.admin import (
    _assign_role_by_name,
    _is_global_admin,
    assign_user_module_role,
    award_milestone,
    change_user_role,
    create_admin_location,
    create_admin_role,
    create_admin_social,
    create_admin_user,
    deactivate_admin_user,
    delete_admin_role,
    delete_admin_variable,
    get_admin_role,
    get_admin_role_user_counts,
    get_admin_stats,
    get_user_permissions,
    list_admin_automations,
    list_admin_milestones,
    list_admin_personas,
    list_admin_roles,
    list_admin_variables,
    list_user_module_roles,
    list_users_with_roles,
    provision_personas_sin_cuenta,
    set_admin_variable,
    set_user_permissions,
    update_admin_location,
    update_admin_role,
    update_admin_social,
    update_admin_user,
)
from backend.models_auth import (
    Medalla,
    RolPlataforma,
    Usuario,
    UsuarioRolModulo,
)
from backend.models_crm import Persona
from tests.conftest import seed_admin


@pytest.fixture
def admin_user(db_session):
    """Create admin user and return (user, sede)."""
    admin, persona, sede = seed_admin(db_session)
    return admin, sede


# ═══════════════════════════════════════════════════════════════════════════════
# ROLES (lines 93, 120, 239)
# ═══════════════════════════════════════════════════════════════════════════════

def test_get_admin_role_not_found(db_session):
    """Line 77: returns None when role does not exist."""
    result = get_admin_role(db_session, uuid.uuid4())
    assert result is None


def test_create_admin_role_list_permissions(db_session):
    """Line 95: creates role with list-style permissions."""
    rol = create_admin_role(db_session, "TestRoleList", ["crm:read", "crm:write"])
    assert rol.nombre == "TestRoleList"
    assert rol.permisos == {"crm:read": "allow", "crm:write": "allow"}


def test_create_admin_role_empty_permissions(db_session):
    """Line 99: creates role with None permissions."""
    rol = create_admin_role(db_session, "TestRoleEmpty")
    assert rol.nombre == "TestRoleEmpty"
    assert rol.permisos == {}


def test_create_admin_role_duplicate(db_session):
    """Line 93: raises ValueError when role name already exists."""
    name = f"DupeRole_{uuid.uuid4().hex[:6]}"
    create_admin_role(db_session, name)
    with pytest.raises(ValueError, match="Role name already exists"):
        create_admin_role(db_session, name)


def test_update_admin_role_name(db_session):
    """Line 120: update role with new name (rol.nombre = nombre)."""
    rol = create_admin_role(db_session, f"UpdName_{uuid.uuid4().hex[:6]}")
    new_name = f"Renamed_{uuid.uuid4().hex[:6]}"
    updated = update_admin_role(db_session, rol.id, nombre=new_name)
    assert updated is not None
    assert updated.nombre == new_name


def test_update_admin_role_list_permissions(db_session):
    """Lines 122-123: update role with list permissions and dict filter."""
    rol = create_admin_role(db_session, f"UpdPerms_{uuid.uuid4().hex[:6]}")
    updated = update_admin_role(db_session, rol.id, permisos=["crm:read"])
    assert updated is not None
    assert updated.permisos == {"crm:read": "allow"}

    # Dict with empty values should be filtered out
    updated2 = update_admin_role(db_session, rol.id, permisos={"crm:read": "allow", "crm:write": ""})
    assert updated2 is not None
    assert updated2.permisos == {"crm:read": "allow"}


# ═══════════════════════════════════════════════════════════════════════════════
# _assign_role_by_name (lines 239)
# ═══════════════════════════════════════════════════════════════════════════════

def test_assign_role_by_name_alias(db_session, admin_user):
    """Line 241: uses ROLE_ALIASES lookup (admin -> ADMINISTRADOR)."""
    admin, _ = admin_user
    rol = create_admin_role(db_session, "ADMINISTRADOR")
    _assign_role_by_name(db_session, admin, "admin")
    assert str(admin.rol_plataforma_id) == str(rol.id)


def test_assign_role_by_name_not_found(db_session, admin_user):
    """Line 250: raises ValueError for unknown role."""
    admin, _ = admin_user
    with pytest.raises(ValueError, match="not found"):
        _assign_role_by_name(db_session, admin, "NONEXISTENT_ROLE_XYZ")


def test_assign_role_by_name_empty(db_session, admin_user):
    """Line 239: early return when normalized role name is empty."""
    admin, _ = admin_user
    original_role_id = admin.rol_plataforma_id
    _assign_role_by_name(db_session, admin, "")
    assert admin.rol_plataforma_id == original_role_id


# ═══════════════════════════════════════════════════════════════════════════════
# create_admin_user (lines 274)
# ═══════════════════════════════════════════════════════════════════════════════

def test_create_admin_user_creates_default_role(db_session, admin_user):
    """Line 278: creates default_role when MIEMBRO does not exist."""
    admin, _ = admin_user
    db_session.query(RolPlataforma).filter(RolPlataforma.nombre == "MIEMBRO").delete()
    db_session.commit()

    result = create_admin_user(
        db_session, admin,
        username=f"test_member_{uuid.uuid4().hex[:6]}",
        email=f"test_member_{uuid.uuid4().hex[:6]}@test.com",
        password="TestPass123!",
        first_name="Test", last_name="Member",
    )
    assert result is not None
    assert result["email"] is not None


def test_create_admin_user_invalid_role(db_session, admin_user):
    """Lines 312-313: role assignment error is swallowed."""
    admin, _ = admin_user
    result = create_admin_user(
        db_session, admin,
        username=f"test_badrole_{uuid.uuid4().hex[:6]}",
        email=f"test_badrole_{uuid.uuid4().hex[:6]}@test.com",
        password="TestPass123!",
        first_name="Test", last_name="Bad",
        role="NONEXISTENT_ROLE_XYZ",
    )
    assert result is not None


def test_create_admin_user_no_sede(db_session, admin_user):
    """Line 274: raises ValueError when current_user has no sede_id.

    Uses mock.patch because Usuario.sede_id has a NOT NULL constraint.
    """
    admin, _ = admin_user
    with _mock.patch.object(admin, "sede_id", None):
        with pytest.raises(ValueError, match="Cannot determine admin's sede"):
            create_admin_user(
                db_session, admin,
                username=f"nosede_{uuid.uuid4().hex[:6]}",
                email=f"nosede_{uuid.uuid4().hex[:6]}@test.com",
                password="TestPass123!",
                first_name="No", last_name="Sede",
            )


# ═══════════════════════════════════════════════════════════════════════════════
# update_admin_user
# ═══════════════════════════════════════════════════════════════════════════════

def test_update_admin_user_email_updates_persona(db_session, admin_user):
    """Line 345: updating email also updates Persona.email."""
    admin, _ = admin_user
    new_email = f"updated_{uuid.uuid4().hex[:6]}@test.com"
    result = update_admin_user(
        db_session, admin, admin.id,
        email=new_email,
        password="NewPass123!",
        is_active=True,
        role="ADMINISTRADOR",
    )
    assert result is not None
    assert result["email"] == new_email
    persona = db_session.query(Persona).filter(Persona.id == admin.id).first()
    if persona:
        assert persona.email == new_email


# ═══════════════════════════════════════════════════════════════════════════════
# deactivate / change role
# ═══════════════════════════════════════════════════════════════════════════════

def test_deactivate_admin_user_not_found(db_session, admin_user):
    """Line 384: returns False when user not found."""
    admin, _ = admin_user
    result = deactivate_admin_user(db_session, admin, uuid.uuid4())
    assert result is False


def test_change_user_role_not_found(db_session, admin_user):
    """Line 424: returns None when target role not found."""
    admin, _ = admin_user
    result = change_user_role(db_session, admin, admin.id, uuid.uuid4())
    assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# list_users_with_roles (line 424 - modulares_by_user.setdefault)
# ═══════════════════════════════════════════════════════════════════════════════

def test_list_users_with_roles_persona_map(db_session, admin_user):
    """Line 520: persona_map building with user IDs."""
    admin, _ = admin_user
    users, total = list_users_with_roles(db_session, admin)
    assert total >= 1
    for u in users:
        assert "nombre" in u


def test_list_users_with_roles_modulares(db_session, admin_user):
    """Line 424: modulares_by_user.setdefault with modular roles."""
    admin, sede = admin_user
    rol = create_admin_role(db_session, f"ModRole_{uuid.uuid4().hex[:6]}", {"crm:read": "allow"})

    # Assign a modular role to the admin user
    umr = UsuarioRolModulo(user_id=admin.id, modulo="crm", rol_id=rol.id)
    db_session.add(umr)
    db_session.commit()

    users, total = list_users_with_roles(db_session, admin)
    assert total >= 1
    # The admin user should have roles_modulares populated
    admin_entry = next((u for u in users if u["user_id"] == str(admin.id)), None)
    if admin_entry:
        assert len(admin_entry["roles_modulares"]) >= 1
        assert admin_entry["roles_modulares"][0]["modulo"] == "crm"


# ═══════════════════════════════════════════════════════════════════════════════
# get_user_permissions (lines 599, 603)
# ═══════════════════════════════════════════════════════════════════════════════

def test_get_user_permissions_not_found(db_session, admin_user):
    """Lines 599-603: returns None for non-visible user."""
    admin, _ = admin_user
    result = get_user_permissions(db_session, admin, uuid.uuid4())
    assert result is None


def test_get_user_permissions_module_roles(db_session, admin_user):
    """Lines 614-635: iterates module_rows successfully."""
    admin, persona_sede = admin_user
    rol = create_admin_role(db_session, f"PermsRole_{uuid.uuid4().hex[:6]}", {"crm:read": "allow"})

    db_session.add(UsuarioRolModulo(user_id=admin.id, modulo="crm", rol_id=rol.id))
    db_session.commit()

    result = get_user_permissions(db_session, admin, admin.id)
    assert result is not None
    assert len(result["module_roles"]) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# set_user_permissions (line 520 - continue for None level)
# ═══════════════════════════════════════════════════════════════════════════════

def test_set_user_permissions_invalid_module(db_session, admin_user):
    """Line 709: raises ValueError for invalid module."""
    admin, _ = admin_user
    module_permission_map = {"crm": {"read": ["crm:read"], "write": ["crm:read", "crm:write"]}}

    def expand_fn(module, level):
        return module_permission_map[module][level]

    with pytest.raises(ValueError, match="Módulo inválido"):
        set_user_permissions(
            db_session, admin, admin.id,
            {"nonexistent": "read"},
            module_permission_map, expand_fn,
        )


def test_set_user_permissions_invalid_level(db_session, admin_user):
    """Line 711: raises ValueError for invalid level."""
    admin, _ = admin_user
    module_permission_map = {"crm": {"read": ["crm:read"], "write": ["crm:read", "crm:write"]}}

    def expand_fn(module, level):
        return module_permission_map[module][level]

    with pytest.raises(ValueError, match="Nivel inválido"):
        set_user_permissions(
            db_session, admin, admin.id,
            {"crm": "invalid_level"},
            module_permission_map, expand_fn,
        )


def test_set_user_permissions_skip_none_level(db_session, admin_user):
    """Line 520: skips entries with None level (continue)."""
    admin, _ = admin_user
    module_permission_map = {"crm": {"read": ["crm:read"], "write": ["crm:read", "crm:write"]}}

    def expand_fn(module, level):
        return module_permission_map[module][level]

    result = set_user_permissions(
        db_session, admin, admin.id,
        {"crm": "read", "chat": None},  # chat: None should be skipped
        module_permission_map, expand_fn,
    )
    assert result is not None
    assert result["status"] == "success"
    assert "crm:read" in result["override_permissions"]


# ═══════════════════════════════════════════════════════════════════════════════
# assign_user_module_role (lines 599, 603)
# ═══════════════════════════════════════════════════════════════════════════════

def test_assign_user_module_role_user_not_found(db_session, admin_user):
    """Line 599: raises ValueError when user not found."""
    admin, _ = admin_user
    rol = create_admin_role(db_session, f"AssignRole_{uuid.uuid4().hex[:6]}", {"crm:read": "allow"})
    with pytest.raises(ValueError, match="User not found"):
        assign_user_module_role(db_session, admin, uuid.uuid4(), "crm", rol.id)


def test_assign_user_module_role_role_not_found(db_session, admin_user):
    """Line 603: raises ValueError when role not found."""
    admin, _ = admin_user
    with pytest.raises(ValueError, match="Role not found"):
        assign_user_module_role(db_session, admin, admin.id, "crm", uuid.uuid4())


def test_assign_user_module_role_insufficient_perms(db_session, admin_user):
    """Line 609: raises ValueError when role lacks module permissions."""
    admin, _ = admin_user
    rol = create_admin_role(db_session, f"NoPermRole_{uuid.uuid4().hex[:6]}", {"academy:read": "allow"})
    with pytest.raises(ValueError, match="debe incluir al menos un permiso"):
        assign_user_module_role(db_session, admin, admin.id, "crm", rol.id)


def test_assign_user_module_role_existing_update(db_session, admin_user):
    """Line 814: update existing assignment."""
    admin, _ = admin_user
    rol = create_admin_role(db_session, f"ModuleRole_{uuid.uuid4().hex[:6]}", {"crm:read": "allow"})

    result1 = assign_user_module_role(db_session, admin, admin.id, "crm", rol.id)
    assert result1 is not None
    assert result1.get("created") is True

    result2 = assign_user_module_role(db_session, admin, admin.id, "crm", rol.id)
    assert result2 is not None
    assert result2.get("updated") is True


# ═══════════════════════════════════════════════════════════════════════════════
# delete_admin_role
# ═══════════════════════════════════════════════════════════════════════════════

def test_delete_admin_role_with_users(db_session, admin_user):
    """delete_admin_role returns False when assigned to active users."""
    admin, _ = admin_user
    role_id = admin.rol_plataforma_id
    if role_id:
        result = delete_admin_role(db_session, role_id)
        assert result is False


def test_delete_admin_role_success(db_session):
    """Covers success path of delete_admin_role."""
    rol = create_admin_role(db_session, f"DelRoleOK_{uuid.uuid4().hex[:6]}")
    result = delete_admin_role(db_session, rol.id)
    assert result is True
    db_session.refresh(rol)
    assert rol.deleted_at is not None
    assert "[deleted:" in rol.nombre


# ═══════════════════════════════════════════════════════════════════════════════
# LOCATIONS (lines 709, 711 - update with address and is_active)
# ═══════════════════════════════════════════════════════════════════════════════

def test_update_admin_location_address_active(db_session):
    """Lines 709, 711: update location with address and is_active."""
    loc = create_admin_location(db_session, f"Loc_{uuid.uuid4().hex[:6]}")
    updated = update_admin_location(
        db_session, loc.id,
        address="123 Test St",
        is_active=False,
    )
    assert updated is not None
    assert updated.address == "123 Test St"
    assert updated.is_active is False


# ═══════════════════════════════════════════════════════════════════════════════
# SOCIALS (lines 770, 774 - update with platform and is_visible)
# ═══════════════════════════════════════════════════════════════════════════════

def test_update_admin_social_platform_visible(db_session):
    """Lines 770, 774: update social with platform and is_visible."""
    soc = create_admin_social(
        db_session,
        platform=f"Orig_{uuid.uuid4().hex[:6]}",
        url="https://example.com/orig",
    )
    new_platform = f"Updated_{uuid.uuid4().hex[:6]}"
    updated = update_admin_social(
        db_session, soc.id,
        platform=new_platform,
        is_visible=False,
    )
    assert updated is not None
    assert updated.platform == new_platform
    assert updated.is_visible is False


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM VARIABLES (line 814 - upsert update path)
# ═══════════════════════════════════════════════════════════════════════════════

def test_set_admin_variable_upsert(db_session):
    """Line 814: update existing variable (upsert path)."""
    key = f"upsert_{uuid.uuid4().hex[:6]}"
    var1 = set_admin_variable(db_session, key, "first")
    assert var1.value == "first"

    var2 = set_admin_variable(db_session, key, "second")
    assert var2.value == "second"

    db_session.refresh(var1)
    assert var1.value == "second"


# ═══════════════════════════════════════════════════════════════════════════════
# AUTOMATIONS (lines 943-963)
# ═══════════════════════════════════════════════════════════════════════════════

def test_list_admin_automations_empty(db_session):
    """Lines 943-963: basic listing (empty)."""
    rules, total = list_admin_automations(db_session)
    assert total >= 0
    assert isinstance(rules, list)
    assert len(rules) == total


def test_list_admin_automations_with_data(db_session):
    """Lines 943-963: listing with rules present (using models.AutomationRule)."""
    from backend.models_governance import AutomationRule

    rule = AutomationRule(
        id=uuid.uuid4(),
        name=f"Auto_{uuid.uuid4().hex[:6]}",
        trigger_type="new_case",
        is_active=True,
    )
    db_session.add(rule)
    db_session.commit()

    rules, total = list_admin_automations(db_session)
    assert total >= 1
    assert len(rules) >= 1
    assert rules[0].name == rule.name

    # Test with skip/limit params
    rules2, total2 = list_admin_automations(db_session, skip=0, limit=10)
    assert total2 == total
    assert len(rules2) <= 10


# ═══════════════════════════════════════════════════════════════════════════════
# VARIABLES (lines 1112, 1114, 1116)
# ═══════════════════════════════════════════════════════════════════════════════

def test_list_admin_variables_paginated(db_session):
    """Line 1048: paginated listing."""
    variables, total = list_admin_variables(db_session, skip=0, limit=10)
    assert total >= 0
    assert isinstance(variables, list)
    assert len(variables) <= 10


def test_delete_admin_variable_not_found(db_session):
    """Line 1112: returns False for non-existent key."""
    result = delete_admin_variable(db_session, "nonexistent_key_xyz")
    assert result is False


def test_delete_admin_variable_success(db_session):
    """Lines 1114-1116: soft-delete and rename key."""
    from backend.models_ops import SystemVariable

    var = SystemVariable(key=f"delvar_{uuid.uuid4().hex[:6]}", value="test")
    db_session.add(var)
    db_session.commit()

    result = delete_admin_variable(db_session, var.key)
    assert result is True

    db_session.refresh(var)
    assert var.deleted_at is not None
    assert "[deleted:" in var.key


# ═══════════════════════════════════════════════════════════════════════════════
# MILESTONES (lines 1180, 1184)
# ═══════════════════════════════════════════════════════════════════════════════

def test_list_admin_milestones_counts(db_session):
    """Lines 1180-1184: badge_counts grouping and badges loop."""
    badges, total = list_admin_milestones(db_session)
    assert total >= 0
    assert isinstance(badges, list)
    for b in badges:
        assert "id" in b
        assert "count" in b


def test_award_milestone_not_found(db_session):
    """Line 1220: badge not found raises ValueError."""
    with pytest.raises(ValueError, match="Badge not found"):
        award_milestone(db_session, str(uuid.uuid4()), str(uuid.uuid4()))


def test_award_milestone_persona_not_found(db_session, admin_user):
    """Lines 1242-1243: Persona not found."""
    admin, _ = admin_user
    badge = Medalla(id=uuid.uuid4(), name="Test Badge", description="Desc")
    db_session.add(badge)
    db_session.commit()

    with pytest.raises(ValueError, match="Persona not found"):
        award_milestone(db_session, str(uuid.uuid4()), str(badge.id))


def test_award_milestone_already_awarded(db_session, admin_user):
    """Lines 1250-1251: badge already awarded."""
    admin, _ = admin_user
    badge = Medalla(id=uuid.uuid4(), name="Test Badge2", description="Desc")
    db_session.add(badge)
    db_session.commit()

    result = award_milestone(db_session, str(admin.id), str(badge.id))
    assert result["status"] == "success"

    with pytest.raises(ValueError, match="already awarded"):
        award_milestone(db_session, str(admin.id), str(badge.id))


# ═══════════════════════════════════════════════════════════════════════════════
# PROVISION (lines 1275-1279)
# ═══════════════════════════════════════════════════════════════════════════════

def test_provision_personas_sin_cuenta_basic(db_session):
    """Lines 1275-1279: total_remaining and truncated logic."""
    from backend.models_auth import RolPlataforma
    from backend.models_crm import Persona
    from backend.models_evangelism import Sede

    rol = db_session.query(RolPlataforma).filter(RolPlataforma.nombre == "MIEMBRO").first()
    if not rol:
        db_session.add(RolPlataforma(nombre="MIEMBRO", permisos={"academy:study": "allow"}))
        db_session.commit()

    sede = db_session.query(Sede).first()
    if not sede:
        sede = Sede(nombre="Test Sede", ciudad="Test")
        db_session.add(sede)
        db_session.commit()

    p = Persona(
        id=uuid.uuid4(),
        first_name="Provision",
        last_name="Test",
        email=f"provision_{uuid.uuid4().hex[:6]}@test.com",
        sede_id=sede.id,
    )
    db_session.add(p)
    db_session.commit()

    result = provision_personas_sin_cuenta(db_session, batch_limit=50)
    assert result["created"] >= 1
    assert "truncated" in result
    assert "message" in result


# ═══════════════════════════════════════════════════════════════════════════════
# is_global_admin
# ═══════════════════════════════════════════════════════════════════════════════

def test_is_global_admin_superadmin(db_session):
    """_is_global_admin returns True for superadmin role."""
    user = db_session.query(Usuario).first()
    if not user:
        pytest.skip("Need an existing user")

    rol = db_session.query(RolPlataforma).filter(
        RolPlataforma.nombre == "SUPER_ADMINISTRADOR"
    ).first()
    if not rol:
        rol = RolPlataforma(id=uuid.uuid4(), nombre="SUPER_ADMINISTRADOR", permisos={})
        db_session.add(rol)
        db_session.commit()
    user.rol_plataforma_id = rol.id
    db_session.commit()
    db_session.refresh(user)

    assert _is_global_admin(user) is True


def test_is_global_admin_not_superadmin(db_session, admin_user):
    """_is_global_admin returns False for regular admin."""
    admin, _ = admin_user
    assert _is_global_admin(admin) is False


# ═══════════════════════════════════════════════════════════════════════════════
# get_admin_stats
# ═══════════════════════════════════════════════════════════════════════════════

def test_get_admin_stats_metrics(db_session):
    """Ensure stats query runs without error."""
    stats = get_admin_stats(db_session)
    assert "personas" in stats
    assert "usuarios_activos" in stats
    assert "donaciones_mes" in stats


# ═══════════════════════════════════════════════════════════════════════════════
# DONATION CATEGORIES (additional edge paths)
# ═══════════════════════════════════════════════════════════════════════════════

def test_list_admin_roles_with_counts(db_session):
    """get_admin_role_user_counts and list_admin_roles work."""
    counts = get_admin_role_user_counts(db_session)
    assert isinstance(counts, dict)

    roles, total = list_admin_roles(db_session)
    assert total >= 0
    assert isinstance(roles, list)


def test_list_user_module_roles_with_data(db_session, admin_user):
    """list_user_module_roles returns data when modular roles exist."""
    admin, _ = admin_user
    roles_list, total = list_user_module_roles(db_session)
    assert isinstance(roles_list, list)
    assert total >= 0

    # Add a modular role and verify
    rol = create_admin_role(db_session, f"ListMR_{uuid.uuid4().hex[:6]}", {"crm:read": "allow"})
    db_session.add(UsuarioRolModulo(user_id=admin.id, modulo="crm", rol_id=rol.id))
    db_session.commit()

    roles_list2, total2 = list_user_module_roles(db_session)
    assert total2 >= 1


def test_list_admin_personas_returns_list(db_session, admin_user):
    """list_admin_personas returns a tuple of (list, int)."""
    admin, sede = admin_user
    personas, total = list_admin_personas(db_session, sede.id)
    assert isinstance(personas, list)
    assert total >= 0
