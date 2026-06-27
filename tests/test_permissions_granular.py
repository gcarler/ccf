"""Tests para permisos granulares sobre los modelos Auth v3.

Cubre:
1. RolPlataforma CRUD via /admin/auth-role-definitions
2. UsuarioRolModulo CRUD via /admin/user-module-roles
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
    from tests.conftest import seed_admin
    admin, persona, sede = seed_admin(db_session, email="permadmin@ccf.test", password="test123")

    resp = client.post(
        "/api/v3/auth/login",
        json={"email": "permadmin@ccf.test", "password": "test123"},
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
    """Create an Auth v3 user linked to a persona and return its UUID."""
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

