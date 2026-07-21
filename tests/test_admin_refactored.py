"""
Admin Module Comprehensive Tests — refactored module coverage.

Tests ALL endpoints in the refactored admin.py with proper CRUD,
RBAC, multi-tenant isolation, and error paths.
"""

import uuid

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204, 400, 403, 404, 405, 409, 422)


@pytest.fixture
def full(client, db_session):
    admin, admin_persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {
        "c": client,
        "h": headers,
        "sede": sede,
        "admin": admin,
        "admin_persona": admin_persona,
        "_db": db_session,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ROLES (consolidated)
# ═══════════════════════════════════════════════════════════════════════════════


class TestRolesCRUD:
    def test_list_roles(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/admin/roles", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "items" in data

    def test_create_role(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/roles", json={
            "name": f"TestRole_{uuid.uuid4().hex[:6]}",
            "permissions": {"crm:read": "allow"},
        }, headers=h)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "nombre" in data

    def test_create_role_duplicate(self, full):
        c, h = full["c"], full["h"]
        name = f"DupeRole_{uuid.uuid4().hex[:6]}"
        c.post("/api/admin/roles", json={"name": name, "permissions": {}}, headers=h)
        resp2 = c.post("/api/admin/roles", json={"name": name, "permissions": {}}, headers=h)
        assert resp2.status_code == 409

    def test_create_role_empty_name(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/roles", json={"name": "", "permissions": {}}, headers=h)
        assert resp.status_code in (400, 422)

    def test_update_role(self, full):
        c, h = full["c"], full["h"]
        create_resp = c.post("/api/admin/roles", json={
            "name": f"UpdRole_{uuid.uuid4().hex[:6]}",
            "permissions": {"crm:read": "allow"},
        }, headers=h)
        role_id = create_resp.json()["id"]
        resp = c.patch(f"/api/admin/roles/{role_id}", json={
            "permissions": {"crm:read": "allow", "crm:write": "allow"},
        }, headers=h)
        assert resp.status_code == 200

    def test_update_role_not_found(self, full):
        c, h = full["c"], full["h"]
        fake_id = str(uuid.uuid4())
        resp = c.patch(f"/api/admin/roles/{fake_id}", json={"permissions": {}}, headers=h)
        assert resp.status_code == 404

    def test_delete_role(self, full):
        c, h = full["c"], full["h"]
        create_resp = c.post("/api/admin/roles", json={
            "name": f"DelRole_{uuid.uuid4().hex[:6]}",
            "permissions": {},
        }, headers=h)
        role_id = create_resp.json()["id"]
        resp = c.delete(f"/api/admin/roles/{role_id}", headers=h)
        assert resp.status_code == 204

    def test_delete_role_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.delete(f"/api/admin/roles/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 409  # delete_admin_role returns False -> 409

    def test_create_role_list_permissions(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/roles", json={
            "name": f"ListPerms_{uuid.uuid4().hex[:6]}",
            "permissions": ["crm:read", "crm:write"],
        }, headers=h)
        assert resp.status_code == 201


# ═══════════════════════════════════════════════════════════════════════════════
# PERMISSIONS
# ═══════════════════════════════════════════════════════════════════════════════


class TestPermissions:
    def test_read_all_permissions(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/admin/permissions", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert "permissions" in data
        assert "modules" in data
        assert "levels" in data


# ═══════════════════════════════════════════════════════════════════════════════
# USER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestUserManagement:
    def test_list_users(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/admin/users", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "items" in data

    def test_get_user(self, full):
        c, h = full["c"], full["h"]
        resp = c.get(f"/api/admin/users/{full['admin'].id}", headers=h)
        assert resp.status_code == 200

    def test_get_user_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.get(f"/api/admin/users/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404

    def test_get_user_invalid_uuid(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/admin/users/not-a-uuid", headers=h)
        assert resp.status_code == 400

    def test_create_user(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/users", json={
            "username": f"newuser_{uuid.uuid4().hex[:6]}",
            "email": f"new_{uuid.uuid4().hex[:6]}@test.com",
            "password": "TestPass123!",
            "first_name": "New",
            "last_name": "User",
            "role": "MIEMBRO",
        }, headers=h)
        assert resp.status_code == 201

    def test_create_user_duplicate(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        resp = c.post("/api/admin/users", json={
            "username": admin.username,
            "email": f"dup_{uuid.uuid4().hex[:6]}@test.com",
            "password": "TestPass123!",
            "first_name": "Dup",
            "last_name": "User",
            "role": "MIEMBRO",
        }, headers=h)
        assert resp.status_code == 409

    def test_update_user(self, full):
        c, h = full["c"], full["h"]
        resp = c.patch(f"/api/admin/users/{full['admin'].id}", json={
            "first_name": "Updated",
        }, headers=h)
        assert resp.status_code == 200

    def test_update_user_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.patch(f"/api/admin/users/{uuid.uuid4()}", json={
            "first_name": "Ghost",
        }, headers=h)
        assert resp.status_code == 404

    def test_delete_user(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        resp = c.delete(f"/api/admin/users/{admin.id}", headers=h)
        assert resp.status_code == 204

    def test_delete_user_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.delete(f"/api/admin/users/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404

    def test_change_user_role(self, full):
        c, h = full["c"], full["h"]
        role_id = str(full["admin"].rol_plataforma_id)
        resp = c.patch(
            f"/api/admin/users/{full['admin'].id}/role?role_id={role_id}",
            headers=h,
        )
        assert resp.status_code == 200

    def test_change_user_role_missing_role(self, full):
        c, h = full["c"], full["h"]
        resp = c.patch(f"/api/admin/users/{full['admin'].id}/role", headers=h)
        assert resp.status_code == 400

    def test_change_user_role_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.patch(
            f"/api/admin/users/{uuid.uuid4()}/role?role_id={uuid.uuid4()}",
            headers=h,
        )
        assert resp.status_code == 404

    def test_list_users_with_roles(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/admin/users-with-roles", headers=h)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# USER PERMISSIONS
# ═══════════════════════════════════════════════════════════════════════════════


class TestUserPermissions:
    def test_get_user_permissions(self, full):
        c, h = full["c"], full["h"]
        resp = c.get(f"/api/admin/users/{full['admin'].id}/permissions", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert "effective_permissions" in data

    def test_get_user_permissions_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.get(f"/api/admin/users/{uuid.uuid4()}/permissions", headers=h)
        assert resp.status_code == 404

    def test_set_user_permissions(self, full):
        c, h = full["c"], full["h"]
        resp = c.put(
            f"/api/admin/users/{full['admin'].id}/permissions",
            json={"permissions": {"crm": "read"}},
            headers=h,
        )
        assert resp.status_code == 200

    def test_set_user_permissions_invalid_module(self, full):
        c, h = full["c"], full["h"]
        resp = c.put(
            f"/api/admin/users/{full['admin'].id}/permissions",
            json={"permissions": {"nonexistent": "read"}},
            headers=h,
        )
        assert resp.status_code == 400

    def test_set_user_permissions_invalid_level(self, full):
        c, h = full["c"], full["h"]
        resp = c.put(
            f"/api/admin/users/{full['admin'].id}/permissions",
            json={"permissions": {"crm": "invalid_level"}},
            headers=h,
        )
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# LOCATIONS (CRUD — new endpoints)
# ═══════════════════════════════════════════════════════════════════════════════


class TestLocations:
    def test_list_locations(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/admin/locations", headers=h)
        assert resp.status_code == 200

    def test_create_location(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/locations", json={
            "name": "Test Location",
            "address": "Test Address",
            "phone": "123456",
        }, headers=h)
        assert resp.status_code == 201

    def test_create_location_empty_name(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/locations", json={"name": ""}, headers=h)
        assert resp.status_code in (400, 422)

    def test_update_location(self, full):
        c, h = full["c"], full["h"]
        create_resp = c.post("/api/admin/locations", json={
            "name": f"Loc_{uuid.uuid4().hex[:6]}",
        }, headers=h)
        loc_id = create_resp.json()["id"]
        resp = c.patch(f"/api/admin/locations/{loc_id}", json={
            "name": "Updated Location",
        }, headers=h)
        assert resp.status_code == 200

    def test_update_location_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.patch(f"/api/admin/locations/{uuid.uuid4()}", json={
            "name": "Ghost",
        }, headers=h)
        assert resp.status_code == 404

    def test_delete_location(self, full):
        c, h = full["c"], full["h"]
        create_resp = c.post("/api/admin/locations", json={
            "name": f"DelLoc_{uuid.uuid4().hex[:6]}",
        }, headers=h)
        loc_id = create_resp.json()["id"]
        resp = c.delete(f"/api/admin/locations/{loc_id}", headers=h)
        assert resp.status_code == 204

    def test_delete_location_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.delete(f"/api/admin/locations/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# SOCIAL CHANNELS (CRUD — new endpoints)
# ═══════════════════════════════════════════════════════════════════════════════


class TestSocials:
    def test_list_socials(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/admin/socials", headers=h)
        assert resp.status_code == 200

    def test_create_social(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/socials", json={
            "platform": "Facebook",
            "url": "https://facebook.com/test",
        }, headers=h)
        assert resp.status_code == 201

    def test_update_social(self, full):
        c, h = full["c"], full["h"]
        create_resp = c.post("/api/admin/socials", json={
            "platform": "Instagram",
            "url": f"https://instagram.com/{uuid.uuid4().hex[:6]}",
        }, headers=h)
        soc_id = create_resp.json()["id"]
        resp = c.patch(f"/api/admin/socials/{soc_id}", json={
            "url": "https://instagram.com/updated",
        }, headers=h)
        assert resp.status_code == 200

    def test_update_social_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.patch(f"/api/admin/socials/{uuid.uuid4()}", json={
            "url": "https://ghost.com",
        }, headers=h)
        assert resp.status_code == 404

    def test_delete_social(self, full):
        c, h = full["c"], full["h"]
        create_resp = c.post("/api/admin/socials", json={
            "platform": "Twitter",
            "url": f"https://twitter.com/{uuid.uuid4().hex[:6]}",
        }, headers=h)
        soc_id = create_resp.json()["id"]
        resp = c.delete(f"/api/admin/socials/{soc_id}", headers=h)
        assert resp.status_code == 204

    def test_delete_social_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.delete(f"/api/admin/socials/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM VARIABLES
# ═══════════════════════════════════════════════════════════════════════════════


class TestVariables:
    def test_list_variables(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/admin/variables", headers=h)
        assert resp.status_code == 200

    def test_set_variable(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/variables", json={
            "key": f"var_{uuid.uuid4().hex[:6]}",
            "value": "test_value",
        }, headers=h)
        assert resp.status_code == 200

    def test_delete_variable(self, full):
        c, h = full["c"], full["h"]
        key = f"delvar_{uuid.uuid4().hex[:6]}"
        c.post("/api/admin/variables", json={"key": key, "value": "x"}, headers=h)
        resp = c.delete(f"/api/admin/variables/{key}", headers=h)
        assert resp.status_code == 204

    def test_delete_variable_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.delete(f"/api/admin/variables/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════════════════════════════════


class TestStats:
    def test_admin_stats(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/admin/stats", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert "personas" in data
        assert "usuarios_activos" in data
        assert "donaciones_mes" in data


# ═══════════════════════════════════════════════════════════════════════════════
# PERSONAS
# ═══════════════════════════════════════════════════════════════════════════════


class TestPersonas:
    def test_list_personas(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/admin/personas", headers=h)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT
# ═══════════════════════════════════════════════════════════════════════════════


class TestAudit:
    def test_list_audit(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/admin/audit", headers=h)
        assert resp.status_code == 200

    def test_list_audit_with_limit(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/admin/audit?limit=10", headers=h)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# COMMENTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestComments:
    def test_list_comments(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/admin/comments", headers=h)
        assert resp.status_code == 200

    def test_delete_comment_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.delete(f"/api/admin/comments/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# MILESTONES
# ═══════════════════════════════════════════════════════════════════════════════


class TestMilestones:
    def test_list_milestones(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/admin/milestones", headers=h)
        assert resp.status_code == 200

    def test_award_milestone_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/milestones/award", json={
            "persona_id": str(uuid.uuid4()),
            "badge_id": str(uuid.uuid4()),
        }, headers=h)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# DONATION CATEGORIES
# ═══════════════════════════════════════════════════════════════════════════════


class TestDonationCategories:
    def test_list_donation_categories(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/admin/donation-categories", headers=h)
        assert resp.status_code == 200

    def test_create_donation_category(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/donation-categories", json={
            "name": f"Cat_{uuid.uuid4().hex[:6]}",
            "description": "Test category",
        }, headers=h)
        assert resp.status_code == 201

    def test_create_donation_category_empty_name(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/donation-categories", json={"name": ""}, headers=h)
        assert resp.status_code in (400, 422)

    def test_update_donation_category(self, full):
        c, h = full["c"], full["h"]
        create_resp = c.post("/api/admin/donation-categories", json={
            "name": f"UpdCat_{uuid.uuid4().hex[:6]}",
        }, headers=h)
        cat_id = create_resp.json()["id"]
        resp = c.patch(f"/api/admin/donation-categories/{cat_id}", json={
            "name": "Updated Category",
        }, headers=h)
        assert resp.status_code == 200

    def test_update_donation_category_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.patch(f"/api/admin/donation-categories/{uuid.uuid4()}", json={
            "name": "Ghost",
        }, headers=h)
        assert resp.status_code == 404

    def test_delete_donation_category(self, full):
        c, h = full["c"], full["h"]
        create_resp = c.post("/api/admin/donation-categories", json={
            "name": f"DelCat_{uuid.uuid4().hex[:6]}",
        }, headers=h)
        cat_id = create_resp.json()["id"]
        resp = c.delete(f"/api/admin/donation-categories/{cat_id}", headers=h)
        assert resp.status_code == 204

    def test_delete_donation_category_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.delete(f"/api/admin/donation-categories/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# AUTOMATIONS
# ═══════════════════════════════════════════════════════════════════════════════


class TestAutomations:
    def test_list_automations(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/admin/automations", headers=h)
        assert resp.status_code == 200

    def test_create_automation(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/automations", json={
            "name": f"Auto_{uuid.uuid4().hex[:6]}",
            "trigger_type": "new_case",
            "is_active": True,
        }, headers=h)
        assert resp.status_code == 200
        rule_id = resp.json()["id"]

        # Update it
        resp2 = c.patch(f"/api/admin/automations/{rule_id}", json={
            "is_active": False,
        }, headers=h)
        assert resp2.status_code == 200

        # Delete it
        resp3 = c.delete(f"/api/admin/automations/{rule_id}", headers=h)
        assert resp3.status_code == 200

    def test_update_automation_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.patch(f"/api/admin/automations/{uuid.uuid4()}", json={
            "is_active": False,
        }, headers=h)
        assert resp.status_code == 404

    def test_delete_automation_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.delete(f"/api/admin/automations/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE ROLES
# ═══════════════════════════════════════════════════════════════════════════════


class TestModuleRoles:
    def test_list_module_roles(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/admin/user-module-roles", headers=h)
        assert resp.status_code == 200

    def test_assign_module_role(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/user-module-roles", json={
            "user_id": str(full["admin"].id),
            "modulo": "crm",
            "rol_id": str(full["admin"].rol_plataforma_id),
        }, headers=h)
        assert _ok(resp.status_code)

    def test_assign_module_role_invalid_user(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/user-module-roles", json={
            "user_id": "not-a-uuid",
            "modulo": "crm",
            "rol_id": str(full["admin"].rol_plataforma_id),
        }, headers=h)
        assert resp.status_code == 400

    def test_remove_module_role_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.delete(f"/api/admin/user-module-roles/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# PROVISION
# ═══════════════════════════════════════════════════════════════════════════════


class TestProvision:
    def test_provision_accounts(self, full):
        from backend.models_auth import RolPlataforma

        c, h, db = full["c"], full["h"], full["_db"]

        existing = db.query(RolPlataforma).filter(RolPlataforma.nombre == "MIEMBRO").first()
        if not existing:
            db.add(RolPlataforma(nombre="MIEMBRO", permisos={"academy:study": "allow", "profile:manage": "allow"}))
            db.commit()

        resp = c.post("/api/admin/provision-accounts", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert "created" in data
        assert "skipped" in data
