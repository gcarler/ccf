"""Tests para permisos granulares — auth_user_module_roles + PlatformRoleDefinition.

Cubre:
1. RolPlataforma CRUD via /admin/auth-role-definitions
2. UsuarioRolModulo CRUD via /admin/user-module-roles
3. PlatformRoleDefinition CRUD via /kernel/admin/platform-role-definitions
4. PersonaPlatformRole CRUD via /kernel/admin/persona-platform-roles
5. Carga de permisos efectivos via /kernel/permissions/me y /kernel/permissions/{persona_id}
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.core.security import get_password_hash


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def _login_as_admin(client: TestClient, db_session: Session) -> str:
    """Create admin user and return Bearer token."""
    from backend import models as m
    user = db_session.query(m.User).filter(m.User.role == "admin").first()
    if not user:
        user = m.User(
            username="permadmin",
            email="permadmin@ccf.test",
            password_hash=get_password_hash("test123"),
            role="admin",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    resp = client.post(
        "/api/auth/login",
        data={"username": "permadmin@ccf.test", "password": "test123", "grant_type": "password"},
    )
    assert resp.status_code == 200, f"login failed: {resp.text}"
    return resp.json()["access_token"]


def _create_persona(db_session: Session) -> str:
    """Create a test persona and return its UUID."""
    from backend import models as m
    p = m.Persona(first_name="Perm", last_name="Test", email=f"permtest_{uuid.uuid4().hex[:8]}@ccf.test")
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return str(p.id)


def _create_auth_user(db_session: Session, persona_id: str) -> str:
    """Create auth_v2 user linked to persona, return UUID."""
    from backend.models_auth import Usuario, RolPlataforma
    rol = db_session.query(RolPlataforma).first()
    if not rol:
        rol = RolPlataforma(nombre="LECTOR", permisos={"profile:manage": "allow"})
        db_session.add(rol)
        db_session.commit()
        db_session.refresh(rol)
    from backend import models as m
    sede = db_session.query(m.Sede).first()
    if not sede:
        sede = m.Sede(nombre="TestSede", ciudad="Bogota", es_activa=True)
        db_session.add(sede)
        db_session.commit()
        db_session.refresh(sede)
    user = Usuario(
        id=uuid.UUID(persona_id),
        sede_id=sede.id if hasattr(sede, 'id') else uuid.uuid4(),
        username=f"permuser_{uuid.uuid4().hex[:8]}",
        email=f"permuser_{uuid.uuid4().hex[:8]}@ccf.test",
        password_hash=get_password_hash("test123"),
        rol_plataforma_id=rol.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return str(user.id)


def _seed_auth_roles(db_session: Session):
    """Seed RolPlataforma definitions needed by tests."""
    from backend.models_auth import RolPlataforma
    roles_to_seed = [
        ("ADMINISTRADOR", {"*": ["create", "read", "update", "delete", "admin"]}),
        ("GESTOR", {"crm": ["create", "read", "update"], "projects": ["create", "read", "update"]}),
        ("EDITOR", {"cms": ["read", "update"], "projects": ["read", "update"]}),
        ("LECTOR", {"crm": ["read"], "projects": ["read"]}),
    ]
    for nombre, permisos in roles_to_seed:
        if not db_session.query(RolPlataforma).filter(RolPlataforma.nombre == nombre).first():
            db_session.add(RolPlataforma(nombre=nombre, permisos=permisos))
    db_session.commit()


# ──────────────────────────────────────────────
# TESTS
# ──────────────────────────────────────────────

class TestAuthRoleDefinitions:
    """CRUD de RolPlataforma via /admin/auth-role-definitions."""

    def test_list_auth_roles(self, client: TestClient, db_session: Session):
        _seed_auth_roles(db_session)
        token = _login_as_admin(client, db_session)
        resp = client.get("/api/admin/auth-role-definitions", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        nombres = [r["nombre"] for r in data]
        assert "ADMINISTRADOR" in nombres
        assert "LECTOR" in nombres

    def test_create_auth_role(self, client: TestClient, db_session: Session):
        token = _login_as_admin(client, db_session)
        resp = client.post(
            "/api/admin/auth-role-definitions",
            headers={"Authorization": f"Bearer {token}"},
            json={"nombre": "TEST_ROL", "permisos": {"crm:read": "allow"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["nombre"] == "TEST_ROL"
        assert data["permisos"] == {"crm:read": "allow"}

    def test_create_duplicate_auth_role_fails(self, client: TestClient, db_session: Session):
        token = _login_as_admin(client, db_session)
        client.post(
            "/api/admin/auth-role-definitions",
            headers={"Authorization": f"Bearer {token}"},
            json={"nombre": "DUP_ROL", "permisos": {}},
        )
        resp = client.post(
            "/api/admin/auth-role-definitions",
            headers={"Authorization": f"Bearer {token}"},
            json={"nombre": "DUP_ROL", "permisos": {}},
        )
        assert resp.status_code == 409

    def test_update_auth_role(self, client: TestClient, db_session: Session):
        token = _login_as_admin(client, db_session)
        # Create a role
        create_resp = client.post(
            "/api/admin/auth-role-definitions",
            headers={"Authorization": f"Bearer {token}"},
            json={"nombre": "ROL_UPDATE", "permisos": {"crm:read": "allow"}},
        )
        role_id = create_resp.json()["id"]
        # Update it
        resp = client.patch(
            f"/api/admin/auth-role-definitions/{role_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"permisos": {"crm:read": "allow", "crm:edit": "allow"}},
        )
        assert resp.status_code == 200
        assert len(resp.json()["permisos"]) == 2

    def test_delete_auth_role(self, client: TestClient, db_session: Session):
        token = _login_as_admin(client, db_session)
        create_resp = client.post(
            "/api/admin/auth-role-definitions",
            headers={"Authorization": f"Bearer {token}"},
            json={"nombre": "ROL_DEL", "permisos": {}},
        )
        role_id = create_resp.json()["id"]
        resp = client.delete(
            f"/api/admin/auth-role-definitions/{role_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204


class TestUserModuleRoles:
    """CRUD de UsuarioRolModulo via /admin/user-module-roles."""

    def test_assign_and_list_module_role(self, client: TestClient, db_session: Session):
        _seed_auth_roles(db_session)
        token = _login_as_admin(client, db_session)
        persona_id = _create_persona(db_session)
        auth_user_id = _create_auth_user(db_session, persona_id)

        # Get a rol_id to assign
        roles_resp = client.get("/api/admin/auth-role-definitions", headers={"Authorization": f"Bearer {token}"})
        rol_id = roles_resp.json()[0]["id"]

        # Assign module role
        resp = client.post(
            "/api/admin/user-module-roles",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": auth_user_id, "modulo": "crm", "rol_id": rol_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["modulo"] == "crm"
        assert data["user_id"] == auth_user_id

        # List module roles
        list_resp = client.get("/api/admin/user-module-roles", headers={"Authorization": f"Bearer {token}"})
        assert list_resp.status_code == 200
        assignments = list_resp.json()
        assert any(a["user_id"] == auth_user_id and a["modulo"] == "crm" for a in assignments)

    def test_reassign_module_role_updates(self, client: TestClient, db_session: Session):
        _seed_auth_roles(db_session)
        token = _login_as_admin(client, db_session)
        persona_id = _create_persona(db_session)
        auth_user_id = _create_auth_user(db_session, persona_id)
        roles_resp = client.get("/api/admin/auth-role-definitions", headers={"Authorization": f"Bearer {token}"})
        roles = roles_resp.json()
        rol_id_a = roles[0]["id"]
        rol_id_b = roles[1]["id"] if len(roles) > 1 else roles[0]["id"]

        # Assign first role
        client.post(
            "/api/admin/user-module-roles",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": auth_user_id, "modulo": "finances", "rol_id": rol_id_a},
        )
        # Reassign same module -> should update
        resp = client.post(
            "/api/admin/user-module-roles",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": auth_user_id, "modulo": "finances", "rol_id": rol_id_b},
        )
        assert resp.status_code == 200
        assert resp.json().get("updated") is True

    def test_delete_module_role(self, client: TestClient, db_session: Session):
        _seed_auth_roles(db_session)
        token = _login_as_admin(client, db_session)
        persona_id = _create_persona(db_session)
        auth_user_id = _create_auth_user(db_session, persona_id)
        roles_resp = client.get("/api/admin/auth-role-definitions", headers={"Authorization": f"Bearer {token}"})
        rol_id = roles_resp.json()[0]["id"]

        create_resp = client.post(
            "/api/admin/user-module-roles",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": auth_user_id, "modulo": "projects", "rol_id": rol_id},
        )
        assignment_id = create_resp.json()["id"]

        resp = client.delete(
            f"/api/admin/user-module-roles/{assignment_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204


def _seed_platform_role_defs(db_session: Session):
    """Seed kernel PlatformRoleDefinition entries needed by tests."""
    from backend.models_kernel import PlatformRoleDefinition, PlatformRole
    for role, perms in [
        (PlatformRole.ADMINISTRADOR, {"*": ["create", "read", "update", "delete", "admin"]}),
        (PlatformRole.GESTOR, {"crm": ["create", "read", "update"]}),
        (PlatformRole.EDITOR, {"cms": ["read", "update"]}),
        (PlatformRole.LECTOR, {"crm": ["read"]}),
    ]:
        if not db_session.query(PlatformRoleDefinition).filter(PlatformRoleDefinition.role == role).first():
            db_session.add(PlatformRoleDefinition(role=role, permissions=perms))
    db_session.commit()


class TestPlatformRoleDefinitions:
    """CRUD de PlatformRoleDefinition via /kernel/admin/platform-role-definitions."""

    def test_list_platform_role_defs(self, client: TestClient, db_session: Session):
        _seed_platform_role_defs(db_session)
        token = _login_as_admin(client, db_session)
        resp = client.get("/api/kernel/admin/platform-role-definitions", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        roles = [r["role"] for r in data]
        assert "ADMINISTRADOR" in roles or "LECTOR" in roles

    def test_create_platform_role_def(self, client: TestClient, db_session: Session):
        token = _login_as_admin(client, db_session)
        resp = client.post(
            "/api/kernel/admin/platform-role-definitions",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "TEST_PLATFORM_ROLE", "permissions": {"crm": ["read"]}, "description": "Test role"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "TEST_PLATFORM_ROLE"
        assert data["permissions"] == {"crm": ["read"]}

    def test_update_platform_role_def(self, client: TestClient, db_session: Session):
        token = _login_as_admin(client, db_session)
        create_resp = client.post(
            "/api/kernel/admin/platform-role-definitions",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "UPDATABLE_ROLE", "permissions": {"crm": ["read"]}},
        )
        def_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/kernel/admin/platform-role-definitions/{def_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"permissions": {"crm": ["read", "update"]}},
        )
        assert resp.status_code == 200
        assert resp.json()["permissions"]["crm"] == ["read", "update"]


class TestPersonaPlatformRoles:
    """Asignación de roles de plataforma a personas via Kernel API."""

    def test_assign_and_list_persona_platform_roles(self, client: TestClient, db_session: Session):
        _seed_platform_role_defs(db_session)
        token = _login_as_admin(client, db_session)
        persona_id = _create_persona(db_session)
        _create_auth_user(db_session, persona_id)

        # Assign platform role to persona
        resp = client.post(
            f"/api/kernel/platform-roles/{persona_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"platform_role": "EDITOR"},
        )
        assert resp.status_code == 200, f"assign failed: {resp.text}"

        # List all persona assignments via admin endpoint
        list_resp = client.get(
            "/api/kernel/admin/persona-platform-roles",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_resp.status_code == 200
        assignments = list_resp.json()
        assert any(a["persona_id"] == persona_id for a in assignments)

    def test_revoke_persona_platform_role(self, client: TestClient, db_session: Session):
        _seed_platform_role_defs(db_session)
        token = _login_as_admin(client, db_session)
        persona_id = _create_persona(db_session)
        _create_auth_user(db_session, persona_id)

        # Assign
        client.post(
            f"/api/kernel/platform-roles/{persona_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"platform_role": "EDITOR"},
        )

        # Find assignment ID
        list_resp = client.get(
            "/api/kernel/admin/persona-platform-roles",
            headers={"Authorization": f"Bearer {token}"},
        )
        assignment = next(a for a in list_resp.json() if a["persona_id"] == persona_id)

        # Revoke
        resp = client.delete(
            f"/api/kernel/admin/persona-platform-roles/{assignment['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        # Verify revoked
        list_resp2 = client.get(
            "/api/kernel/admin/persona-platform-roles",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert not any(a["persona_id"] == persona_id for a in list_resp2.json())
