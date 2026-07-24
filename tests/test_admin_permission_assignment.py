"""Tests for granular permission assignment in the Admin module.

Covers:
- /admin/permissions taxonomy
- /admin/roles/{id} permission updates
- /admin/users/{id}/permissions set/read effective permissions
- Permission hierarchy (manage implies edit/read)
- Validation of invalid modules/levels
- Sede isolation for permission assignment
- Clearing overrides
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend import models as m
from backend.core.permissions import (
    expand_module_permissions,
    get_user_effective_permissions,
)
from backend.models_auth import RolPlataforma
from backend.models_auth import UsuarioPermisoOverride
from tests.conftest import auth_headers, seed_admin, seed_user_with_role


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def _create_role(db: Session, nombre: str, permisos: dict) -> RolPlataforma:
    role = RolPlataforma(nombre=nombre, permisos=permisos)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


# ──────────────────────────────────────────────
# TESTS: Permission taxonomy & expansion
# ──────────────────────────────────────────────

class TestPermissionTaxonomy:
    def test_get_permissions_taxonomy(self, client: TestClient, db_session: Session):
        admin_user, _, _ = seed_admin(db_session, email="admin_tax@ccf.test", password="test123")
        headers = auth_headers(client, email=admin_user.email, password="test123")

        resp = client.get("/api/admin/permissions", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "permissions" in data
        assert "modules" in data
        assert "levels" in data
        assert "crm" in data["modules"]
        assert "academy" in data["modules"]
        assert "read" in data["levels"]
        assert "manage" in data["levels"]

    def test_expand_module_permissions_hierarchy(self):
        # manage expands to read + edit + manage for crm
        assert set(expand_module_permissions("crm", "manage")) == {
            "crm:read",
            "crm:edit",
            "crm:manage",
        }
        # edit expands to read + edit
        assert set(expand_module_permissions("crm", "edit")) == {"crm:read", "crm:edit"}
        # read expands to read
        assert set(expand_module_permissions("crm", "read")) == {"crm:read"}
        # academy study is its own level and expands only to study
        assert set(expand_module_permissions("academy", "study")) == {"academy:study"}
        # manage on academy does NOT include study because PERMISSION_LEVELS["manage"]
        # only contains read/edit/manage
        expanded = set(expand_module_permissions("academy", "manage"))
        assert "academy:read" in expanded
        assert "academy:edit" in expanded
        assert "academy:manage" in expanded
        assert "academy:study" not in expanded
        # wiki maps manage to edit
        assert set(expand_module_permissions("wiki", "manage")) == {"wiki:read", "wiki:edit"}

    def test_expand_module_permissions_unknown_module(self):
        assert expand_module_permissions("unknown", "manage") == []


# ──────────────────────────────────────────────
# TESTS: Role permission assignment
# ──────────────────────────────────────────────

class TestRolePermissionAssignment:
    def test_update_role_permissions(self, client: TestClient, db_session: Session):
        admin_user, _, _ = seed_admin(db_session, email="admin_role_perm@ccf.test", password="test123")
        role = _create_role(db_session, "CUSTOM_MANAGER_01", {"crm:read": "allow"})
        headers = auth_headers(client, email=admin_user.email, password="test123")

        resp = client.patch(
            f"/api/admin/roles/{role.id}",
            headers=headers,
            json={"permissions": {"crm:read": "allow", "crm:edit": "allow", "finance:read": "allow"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["permisos"]["crm:read"] == "allow"
        assert data["permisos"]["crm:edit"] == "allow"
        assert data["permisos"]["finance:read"] == "allow"

    def test_role_permissions_reflect_in_user_effective(self, client: TestClient, db_session: Session):
        admin_user, _, _ = seed_admin(db_session, email="admin_role_eff@ccf.test", password="test123")
        headers = auth_headers(client, email=admin_user.email, password="test123")

        role = _create_role(
            db_session,
            "PROJECTS_AND_ACADEMY_01",
            {"projects:read": "allow", "projects:edit": "allow", "academy:study": "allow"},
        )
        user, _, _ = seed_user_with_role(
            db_session,
            role_name="BASE_LECTOR_08",
            email="roletest@ccf.test",
            password="test123",
        )

        change_resp = client.patch(
            f"/api/admin/users/{user.id}/role?role_id={role.id}",
            headers=headers,
        )
        assert change_resp.status_code == 200

        perm_resp = client.get(
            f"/api/admin/users/{user.id}/permissions",
            headers=headers,
        )
        assert perm_resp.status_code == 200
        effective = perm_resp.json()["effective_permissions"]
        assert effective["projects:read"] == "allow"
        assert effective["projects:edit"] == "allow"
        assert effective["academy:study"] == "allow"


# ──────────────────────────────────────────────
# TESTS: User override permissions
# ──────────────────────────────────────────────

class TestUserPermissionOverrides:
    def test_set_user_permissions(self, client: TestClient, db_session: Session):
        admin_user, _, _ = seed_admin(db_session, email="admin_user_perm@ccf.test", password="test123")
        user, _, _ = seed_user_with_role(
            db_session,
            role_name="BASE_LECTOR_01",
            email="usertest@ccf.test",
            password="test123",
            permisos={"academy:study": "allow"},
        )
        headers = auth_headers(client, email=admin_user.email, password="test123")

        resp = client.put(
            f"/api/admin/users/{user.id}/permissions",
            headers=headers,
            json={"crm": "manage", "finance": "read"},
        )
        assert resp.status_code == 200
        data = resp.json()
        effective = data["effective_permissions"]
        assert effective["crm:read"] == "allow"
        assert effective["crm:edit"] == "allow"
        assert effective["crm:manage"] == "allow"
        assert effective["finance:read"] == "allow"

    def test_read_user_permissions_after_override(self, client: TestClient, db_session: Session):
        admin_user, _, _ = seed_admin(db_session, email="admin_read_perm@ccf.test", password="test123")
        user, _, _ = seed_user_with_role(
            db_session,
            role_name="BASE_LECTOR_02",
            email="readperm@ccf.test",
            password="test123",
            permisos={"academy:study": "allow"},
        )
        headers = auth_headers(client, email=admin_user.email, password="test123")

        client.put(
            f"/api/admin/users/{user.id}/permissions",
            headers=headers,
            json={"projects": "edit"},
        )

        resp = client.get(
            f"/api/admin/users/{user.id}/permissions",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["override_permissions"]["projects:read"] == "allow"
        assert data["override_permissions"]["projects:edit"] == "allow"
        assert data["effective_permissions"]["projects:read"] == "allow"
        assert data["effective_permissions"]["projects:edit"] == "allow"
        assert data["effective_permissions"]["academy:study"] == "allow"

    def test_clear_override_reverts_to_role_permissions(self, client: TestClient, db_session: Session):
        admin_user, _, _ = seed_admin(db_session, email="admin_clear_perm@ccf.test", password="test123")
        user, _, _ = seed_user_with_role(
            db_session,
            role_name="BASE_LECTOR_03",
            email="clearperm@ccf.test",
            password="test123",
            permisos={"academy:study": "allow"},
        )
        headers = auth_headers(client, email=admin_user.email, password="test123")

        client.put(
            f"/api/admin/users/{user.id}/permissions",
            headers=headers,
            json={"crm": "manage"},
        )
        resp = client.put(
            f"/api/admin/users/{user.id}/permissions",
            headers=headers,
            json={},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["override_permissions"] == {}
        assert "crm:read" not in data["effective_permissions"]
        assert data["effective_permissions"]["academy:study"] == "allow"

    def test_invalid_module_is_rejected(self, client: TestClient, db_session: Session):
        admin_user, _, _ = seed_admin(db_session, email="admin_invalid_mod@ccf.test", password="test123")
        user, _, _ = seed_user_with_role(
            db_session,
            role_name="BASE_LECTOR_04",
            email="invalidmod@ccf.test",
            password="test123",
        )
        headers = auth_headers(client, email=admin_user.email, password="test123")

        resp = client.put(
            f"/api/admin/users/{user.id}/permissions",
            headers=headers,
            json={"notamodule": "read"},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"].lower()
        assert "inválido" in detail or "invalid" in detail

    def test_invalid_level_for_module_is_rejected(self, client: TestClient, db_session: Session):
        admin_user, _, _ = seed_admin(db_session, email="admin_invalid_lvl@ccf.test", password="test123")
        user, _, _ = seed_user_with_role(
            db_session,
            role_name="BASE_LECTOR_05",
            email="invalidlvl@ccf.test",
            password="test123",
        )
        headers = auth_headers(client, email=admin_user.email, password="test123")

        # messaging only supports read/edit; manage is invalid
        resp = client.put(
            f"/api/admin/users/{user.id}/permissions",
            headers=headers,
            json={"messaging": "manage"},
        )
        assert resp.status_code == 400


# ──────────────────────────────────────────────
# TESTS: Effective permission resolution
# ──────────────────────────────────────────────

class TestEffectivePermissionResolution:
    def test_override_extends_base_role(self, client: TestClient, db_session: Session):
        admin_user, _, _ = seed_admin(db_session, email="admin_resolve@ccf.test", password="test123")
        user, _, _ = seed_user_with_role(
            db_session,
            role_name="BASE_MIEMBRO_01",
            email="resolve@ccf.test",
            password="test123",
            permisos={"academy:study": "allow", "profile:manage": "allow"},
        )
        headers = auth_headers(client, email=admin_user.email, password="test123")

        resp = client.put(
            f"/api/admin/users/{user.id}/permissions",
            headers=headers,
            json={"crm": "read"},
        )
        assert resp.status_code == 200
        effective = resp.json()["effective_permissions"]
        assert effective["academy:study"] == "allow"
        assert effective["profile:manage"] == "allow"
        assert effective["crm:read"] == "allow"

    def test_user_without_override_has_only_role_permissions(self, client: TestClient, db_session: Session):
        admin_user, _, _ = seed_admin(db_session, email="admin_no_override@ccf.test", password="test123")
        user, _, _ = seed_user_with_role(
            db_session,
            role_name="BASE_LECTOR_06",
            email="nooverride@ccf.test",
            password="test123",
            permisos={"crm:read": "allow"},
        )
        headers = auth_headers(client, email=admin_user.email, password="test123")

        resp = client.get(
            f"/api/admin/users/{user.id}/permissions",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["override_permissions"] == {}
        assert data["effective_permissions"]["crm:read"] == "allow"


# ──────────────────────────────────────────────
# TESTS: Sede isolation
# ──────────────────────────────────────────────

class TestSedeIsolation:
    def test_admin_cannot_set_permissions_for_foreign_sede_user(self, client: TestClient, db_session: Session):
        admin_user, _, admin_sede = seed_admin(db_session, email="admin_sede_a@ccf.test", password="test123")
        foreign_sede = m.Sede(nombre="Sede Extranjera", ciudad="Cali", es_activa=True)
        db_session.add(foreign_sede)
        db_session.commit()

        foreign_user, _, _ = seed_user_with_role(
            db_session,
            role_name="LECTOR_EXTERNO_01",
            email="foreign@ccf.test",
            password="test123",
            sede_id=foreign_sede.id,
        )
        headers = auth_headers(client, email=admin_user.email, password="test123")

        # GET should be 404 due to sede isolation
        assert client.get(
            f"/api/admin/users/{foreign_user.id}/permissions",
            headers=headers,
        ).status_code == 404

        # PUT should also be 404
        resp = client.put(
            f"/api/admin/users/{foreign_user.id}/permissions",
            headers=headers,
            json={"crm": "read"},
        )
        assert resp.status_code == 404


# ──────────────────────────────────────────────
# TESTS: Direct helper coverage
# ──────────────────────────────────────────────

def test_get_user_effective_permissions_with_override(db_session: Session):
    user, _, _ = seed_user_with_role(
        db_session,
        role_name="BASE_LECTOR_07",
        email="directhelper@ccf.test",
        password="test123",
        permisos={"profile:manage": "allow"},
    )
    override = UsuarioPermisoOverride(
        user_id=user.id,
        permisos={"finance:read": "allow", "finance:edit": "allow"},
    )
    db_session.add(override)
    db_session.commit()

    effective = get_user_effective_permissions(db_session, user)
    assert effective["finance:read"] == "allow"
    assert effective["finance:edit"] == "allow"
    assert effective["profile:manage"] == "allow"
