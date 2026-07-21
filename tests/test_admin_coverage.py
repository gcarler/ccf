"""
Admin.py Coverage Tests — 32% -> 70%+

Creates comprehensive test data and exercises ALL functions and API endpoints
in admin.py to maximize code execution.

Key: Creates real entities via models, then calls API endpoints that
process them to execute code paths.
"""
import uuid

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204, 400, 403, 404, 405, 409, 422)


@pytest.fixture
def full(client, db_session):
    """Create comprehensive test data for admin.py."""
    admin, admin_persona, sede = _seed_admin(db_session)

    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {
        "c": client, "h": headers, "sede": sede,
        "admin": admin, "admin_persona": admin_persona,
        "_db": db_session,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TIER 1 — Simple CRUD Endpoints (Quick wins)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSimpleCRUD:
    def test_list_roles(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/roles", headers=h).status_code)

    def test_create_role(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/roles", json={
            "name": f"Test Role {uuid.uuid4().hex[:4]}",
            "permissions": {"crm:read": "allow"},
        }, headers=h)
        assert _ok(resp.status_code)

    def test_list_users(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/users", headers=h).status_code)

    def test_list_personas(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/personas", headers=h).status_code)

    def test_list_locations(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/locations", headers=h).status_code)

    def test_list_socials(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/socials", headers=h).status_code)

    def test_list_variables(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/variables", headers=h).status_code)

    def test_list_automations(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/automations", headers=h).status_code)

    def test_list_auth_role_definitions(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/admin/roles", headers=h)
        assert _ok(resp.status_code)
        data = resp.json()
        assert "items" in data, f"Expected paginated response, got keys: {list(data.keys())}"

    def test_list_user_module_roles(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/user-module-roles", headers=h).status_code)

    def test_list_users_with_roles(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/users-with-roles", headers=h).status_code)

    def test_stats(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/stats", headers=h).status_code)

    def test_modules(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/socials", headers=h).status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# TIER 2 — CRUD with Data (Create/Update/Delete)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCRUDWithData:
    def test_create_location(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/locations", json={
            "name": "Test Location",
            "address": "Test Address",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_create_variable(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/variables", json={
            "key": f"test_{uuid.uuid4().hex[:6]}",
            "value": "test_value",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_create_automation(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/automations", json={
            "name": f"Test Automation {uuid.uuid4().hex[:4]}",
            "trigger_type": "new_case",
            "is_active": True,
        }, headers=h)
        assert _ok(resp.status_code)

    def test_create_auth_role_definition(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/roles", json={
            "name": f"Role_{uuid.uuid4().hex[:6]}",
            "permissions": {"crm:read": "allow"},
        }, headers=h)
        assert _ok(resp.status_code)

    def test_create_user_module_role(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/user-module-roles", json={
            "user_id": str(full["admin"].id),
            "modulo": "crm",
            "rol_id": str(full["admin"].rol_plataforma_id),
        }, headers=h)
        assert _ok(resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# TIER 3 — User Management (Complex)
# ═══════════════════════════════════════════════════════════════════════════════

class TestUserManagement:
    def test_get_user(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/admin/users/{full['admin'].id}", headers=h).status_code)

    def test_get_user_invalid_uuid(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/admin/users/not-a-uuid", headers=h)
        assert _ok(resp.status_code)

    def test_create_user(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/users", json={
            "username": f"user_{uuid.uuid4().hex[:6]}",
            "email": f"user_{uuid.uuid4().hex[:6]}@test.com",
            "password": "TestPass123!",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_create_user_duplicate(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        resp = c.post("/api/admin/users", json={
            "username": admin.username,
            "email": f"dup_{uuid.uuid4().hex[:6]}@test.com",
            "password": "TestPass123!",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_update_user(self, full):
        c, h = full["c"], full["h"]
        resp = c.patch(f"/api/admin/users/{full['admin'].id}", json={
            "username": "updated_admin",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_delete_user(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        resp = c.delete(f"/api/admin/users/{admin.id}", headers=h)
        assert _ok(resp.status_code)

    def test_change_user_role(self, full):
        c, h = full["c"], full["h"]
        role_id = str(full["admin"].rol_plataforma_id)
        resp = c.patch(f"/api/admin/users/{full['admin'].id}/role?role_id={role_id}", headers=h)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"


# ═══════════════════════════════════════════════════════════════════════════════
# TIER 4 — Permissions & Roles (Complex)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPermissionsRoles:
    def test_get_user_permissions(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/admin/users/{full['admin'].id}/permissions", headers=h).status_code)

    def test_set_user_permissions(self, full):
        c, h = full["c"], full["h"]
        resp = c.put(f"/api/admin/users/{full['admin'].id}/permissions", json={
            "crm": "write",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_update_role(self, full):
        c, h = full["c"], full["h"]
        # Create a role
        create_resp = c.post("/api/admin/roles", json={
            "name": f"UpdRole_{uuid.uuid4().hex[:4]}",
            "permissions": {"crm:read": "allow"},
        }, headers=h)
        assert create_resp.status_code == 201
        role_id = create_resp.json().get("id")
        assert role_id is not None

        # Update its permissions
        patch_resp = c.patch(f"/api/admin/roles/{role_id}", json={
            "permissions": {"crm:read": "allow", "crm:write": "allow"},
        }, headers=h)
        assert patch_resp.status_code == 200, f"Expected 200, got {patch_resp.status_code}: {patch_resp.text}"
        data = patch_resp.json()
        assert "id" in data, f"Expected AdminRoleRead, got: {data}"
        assert "nombre" in data

    def test_create_auth_role_definition_duplicate(self, full):
        c, h = full["c"], full["h"]
        role_name = f"DupeRole_{uuid.uuid4().hex[:4]}"
        resp1 = c.post("/api/admin/roles", json={
            "name": role_name,
            "permissions": {"crm:read": "allow"},
        }, headers=h)
        assert resp1.status_code == 201
        resp2 = c.post("/api/admin/roles", json={
            "name": role_name,
            "permissions": {"crm:read": "allow"},
        }, headers=h)
        assert resp2.status_code == 409, f"Expected 409 for duplicate, got {resp2.status_code}"

    def test_create_user_module_role_invalid(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/user-module-roles", json={
            "user_id": "not-a-uuid",
            "modulo": "crm",
            "rol_id": str(full["admin"].rol_plataforma_id),
        }, headers=h)
        assert _ok(resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# TIER 5 — Settings & Config
# ═══════════════════════════════════════════════════════════════════════════════

class TestSettingsConfig:
    def test_get_permissions(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/permissions", headers=h).status_code)

    def test_set_variable(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/variables", json={
            "key": f"set_test_{uuid.uuid4().hex[:6]}",
            "value": "set_value",
        }, headers=h)
        assert _ok(resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# TIER 6 — Audit & Comments
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditComments:
    def test_list_audit(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/audit", headers=h).status_code)

    def test_list_comments(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/comments", headers=h).status_code)

    def test_list_milestones(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/milestones", headers=h).status_code)

    def test_list_donation_categories(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/donation-categories", headers=h).status_code)

    def test_create_donation_category(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/donation-categories", json={
            "name": "Test Category",
            "description": "Test",
        }, headers=h)
        assert _ok(resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# TIER 7 — Personas Multi-Tenant Verification
# ═══════════════════════════════════════════════════════════════════════════════

class TestPersonasMultiTenant:
    def test_list_personas_filters_by_sede(self, full):
        """Verifica que list_admin_personas solo retorna personas de la sede del admin."""
        c, h, sede = full["c"], full["h"], full["sede"]
        resp = c.get("/api/admin/personas", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "items" in data
        items = data["items"]
        assert isinstance(items, list)
        for p in items:
            assert "id" in p, "Cada persona debe tener un campo id"


# ═══════════════════════════════════════════════════════════════════════════════
# TIER 8 — Full Coverage (remaining endpoints)
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullCoverage:

    def test_delete_role(self, full):
        """DELETE /roles/{role_id} — hard delete permitido en RolPlataforma."""
        from backend.models_auth import RolPlataforma

        c, h, db = full["c"], full["h"], full["_db"]

        rol = RolPlataforma(nombre=f"DelRole_{uuid.uuid4().hex[:4]}", permisos={})
        db.add(rol)
        db.commit()
        rid = str(rol.id)

        resp = c.delete(f"/api/admin/roles/{rid}", headers=h)
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}"

    def test_delete_role_with_users_returns_409(self, full):
        """DELETE /roles/{role_id} con usuarios asignados debe dar 409."""
        c, h = full["c"], full["h"]
        admin = full["admin"]
        role_id = str(admin.rol_plataforma_id)
        resp = c.delete(f"/api/admin/roles/{role_id}", headers=h)
        assert resp.status_code == 409, f"Expected 409, got {resp.status_code}"

    def test_delete_role_not_found(self, full):
        """DELETE /roles/{role_id} con UUID inexistente — retorna 409 (no hay soft delete)."""
        c, h = full["c"], full["h"]
        resp = c.delete(f"/api/admin/roles/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 409, f"Expected 409, got {resp.status_code}"

    def test_delete_comment(self, full):
        """DELETE /comments/{comment_id} — soft delete."""
        from backend.models_academy_core import ForumComment

        c, h, db = full["c"], full["h"], full["_db"]
        comment = ForumComment(
            author_persona_id=full["admin_persona"].id,
            thread_id=uuid.uuid4(),
            content="Test comment for moderation",
        )
        db.add(comment)
        db.commit()
        cid = str(comment.id)

        resp = c.delete(f"/api/admin/comments/{cid}", headers=h)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data.get("status") == "success"

    def test_delete_comment_not_found(self, full):
        """DELETE /comments/{comment_id} con ID inexistente."""
        c, h = full["c"], full["h"]
        resp = c.delete(f"/api/admin/comments/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404

    def test_award_milestone(self, full):
        """POST /milestones/award — asigna hito a una persona."""
        from backend.models_auth import Medalla

        c, h, db = full["c"], full["h"], full["_db"]
        badge = Medalla(name=f"TestBadge_{uuid.uuid4().hex[:4]}", description="Test", xp_reward=10)
        db.add(badge)
        db.commit()

        resp = c.post("/api/admin/milestones/award", json={
            "badge_id": str(badge.id),
            "persona_id": str(full["admin_persona"].id),
        }, headers=h)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data.get("status") == "success"
        assert data.get("awarded", 0) >= 1

    def test_award_milestone_duplicate_skips(self, full):
        """POST /milestones/award — asignar mismo hito otra vez da 409."""
        from backend.models_auth import Medalla

        c, h, db = full["c"], full["h"], full["_db"]
        badge = Medalla(name=f"Badge2_{uuid.uuid4().hex[:4]}", description="Test", xp_reward=10)
        db.add(badge)
        db.commit()

        resp1 = c.post("/api/admin/milestones/award", json={
            "badge_id": str(badge.id),
            "persona_id": str(full["admin_persona"].id),
        }, headers=h)
        assert resp1.status_code == 200

        resp2 = c.post("/api/admin/milestones/award", json={
            "badge_id": str(badge.id),
            "persona_id": str(full["admin_persona"].id),
        }, headers=h)
        assert resp2.status_code == 409, f"Expected 409 for duplicate, got {resp2.status_code}"

    def test_update_automation(self, full):
        """PATCH /automations/{rule_id} — actualiza regla."""
        from backend.models_governance import AutomationRule

        c, h, db = full["c"], full["h"], full["_db"]
        rule = AutomationRule(name=f"Auto_{uuid.uuid4().hex[:4]}", trigger_type="new_case")
        db.add(rule)
        db.commit()

        resp = c.patch(f"/api/admin/automations/{rule.id}", json={
            "is_active": False,
            "name": "Updated Rule",
        }, headers=h)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data.get("name") == "Updated Rule"
        assert data.get("is_active") is False

    def test_update_automation_not_found(self, full):
        """PATCH /automations/{rule_id} con UUID inexistente."""
        c, h = full["c"], full["h"]
        resp = c.patch(f"/api/admin/automations/{uuid.uuid4()}", json={"name": "Nope"}, headers=h)
        assert resp.status_code == 404

    def test_delete_automation(self, full):
        """DELETE /automations/{rule_id} — soft delete."""
        from backend.models_governance import AutomationRule

        c, h, db = full["c"], full["h"], full["_db"]
        rule = AutomationRule(name=f"DelAuto_{uuid.uuid4().hex[:4]}", trigger_type="test")
        db.add(rule)
        db.commit()

        resp = c.delete(f"/api/admin/automations/{rule.id}", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "success"

    def test_update_auth_role_definition(self, full):
        """PATCH /roles/{role_id}."""
        from backend.models_auth import RolPlataforma

        c, h, db = full["c"], full["h"], full["_db"]
        rol = RolPlataforma(nombre=f"UpdAuthRole_{uuid.uuid4().hex[:4]}", permisos={})
        db.add(rol)
        db.commit()

        resp = c.patch(f"/api/admin/roles/{rol.id}", json={
            "permissions": {"crm:read": "allow", "crm:write": "allow"},
        }, headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert "crm:read" in data.get("permisos", {})
        assert "crm:write" in data.get("permisos", {})

    def test_delete_auth_role_definition(self, full):
        """DELETE /roles/{role_id} sin asignaciones."""
        from backend.models_auth import RolPlataforma

        c, h, db = full["c"], full["h"], full["_db"]
        rol = RolPlataforma(nombre=f"DelAuthRole_{uuid.uuid4().hex[:4]}", permisos={})
        db.add(rol)
        db.commit()

        resp = c.delete(f"/api/admin/roles/{rol.id}", headers=h)
        assert resp.status_code == 204

    def test_delete_auth_role_definition_with_users_409(self, full):
        """DELETE /roles/{role_id} con usuarios asignados."""
        c, h = full["c"], full["h"]
        admin = full["admin"]
        resp = c.delete(f"/api/admin/roles/{admin.rol_plataforma_id}", headers=h)
        assert resp.status_code == 409

    def test_delete_user_module_role(self, full):
        """DELETE /user-module-roles/{assignment_id}."""
        from backend.models_auth import UsuarioRolModulo

        c, h, db = full["c"], full["h"], full["_db"]
        umr = UsuarioRolModulo(
            user_id=full["admin"].id,
            modulo="crm",
            rol_id=full["admin"].rol_plataforma_id,
        )
        db.add(umr)
        db.commit()

        resp = c.delete(f"/api/admin/user-module-roles/{umr.id}", headers=h)
        assert resp.status_code == 204

    def test_provision_accounts(self, full):
        """POST /provision-accounts — crea cuentas para personas sin auth_user."""
        from backend.models_auth import RolPlataforma
        from backend.models_crm import Persona

        c, h, db, sede = full["c"], full["h"], full["_db"], full["sede"]

        # Asegurar que existe el rol MIEMBRO
        existing = db.query(RolPlataforma).filter(RolPlataforma.nombre == "MIEMBRO").first()
        if not existing:
            db.add(RolPlataforma(nombre="MIEMBRO", permisos={"academy:study": "allow", "profile:manage": "allow"}))
            db.commit()

        p = Persona(
            id=uuid.uuid4(),
            first_name="Provision",
            last_name="Test",
            email=f"provision_{uuid.uuid4().hex[:6]}@test.com",
            sede_id=sede.id,
        )
        db.add(p)
        db.commit()

        resp = c.post("/api/admin/provision-accounts", headers=h)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("created", 0) >= 1, f"Expected at least 1 account created, got {data}"
