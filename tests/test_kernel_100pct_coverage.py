"""
Exhaustive 100% test suite for backend/api/kernel.py
Covers:
- get_my_kernel_profile & get_kernel_profile
- update_activity_status (ACTIVO/INACTIVO & invalid & 404)
- get_my_ministries, get_ministries, add_ministry, remove_ministry, set_primary_ministry
- get_my_church_role, get_church_role, update_church_role, get_church_role_history, get_personas_by_role
- platform_roles definitions, get_my_platform_roles, get_persona_platform_roles
- get_my_permissions, get_persona_permissions
- check_can_receive_assignment
"""
from __future__ import annotations

import uuid
import pytest
from backend import models
from tests.conftest import auth_headers as _auth_headers, seed_admin as _seed_admin


@pytest.fixture
def kernel_setup(client, db_session):
    user, persona, sede = _seed_admin(db_session, email="kernel_100pct@test.com")
    persona.estado_vital = "ACTIVO"
    db_session.commit()

    headers = _auth_headers(client, email="kernel_100pct@test.com", password="testpass123")
    return {
        "client": client,
        "headers": headers,
        "user": user,
        "persona": persona,
        "sede": sede,
        "db": db_session,
    }


class TestKernel100PctCoverage:
    def test_kernel_profiles(self, kernel_setup):
        c = kernel_setup["client"]
        h = kernel_setup["headers"]
        persona = kernel_setup["persona"]

        # Profile me
        res_me = c.get("/api/kernel/profile/me", headers=h)
        assert res_me.status_code == 200

        # Profile by persona_id
        res_p = c.get(f"/api/kernel/profile/{persona.id}", headers=h)
        assert res_p.status_code == 200

        # Profile 404
        res_404 = c.get(f"/api/kernel/profile/{uuid.uuid4()}", headers=h)
        assert res_404.status_code == 404

    def test_update_activity_status(self, kernel_setup):
        c = kernel_setup["client"]
        h = kernel_setup["headers"]
        persona = kernel_setup["persona"]

        # Invalid status
        res_inv = c.put(f"/api/kernel/status/{persona.id}", json={"status": "INVALID"}, headers=h)
        assert res_inv.status_code == 400

        # 404 persona
        res_404 = c.put(f"/api/kernel/status/{uuid.uuid4()}", json={"status": "ACTIVO"}, headers=h)
        assert res_404.status_code == 404

        # Update to ACTIVO
        res2 = c.put(f"/api/kernel/status/{persona.id}", json={"status": "ACTIVO"}, headers=h)
        assert res2.status_code == 200

        # Update to INACTIVO (executed last)
        res1 = c.put(f"/api/kernel/status/{persona.id}", json={"status": "INACTIVO"}, headers=h)
        assert res1.status_code == 200

    def test_ministries_flow(self, kernel_setup):
        c = kernel_setup["client"]
        h = kernel_setup["headers"]
        persona = kernel_setup["persona"]

        # My ministries
        res_me = c.get("/api/kernel/ministries/me", headers=h)
        assert res_me.status_code == 200

        # Add ministry
        res_add = c.post(
            f"/api/kernel/ministries/{persona.id}",
            json={"ministry": "PASTOR", "is_primary": True, "notes": "Pastor Principal"},
            headers=h,
        )
        assert res_add.status_code in (200, 201)

        # Get ministries by persona
        res_get = c.get(f"/api/kernel/ministries/{persona.id}", headers=h)
        assert res_get.status_code == 200

        # Set primary
        res_prim = c.put(f"/api/kernel/ministries/{persona.id}/PASTOR/primary", headers=h)
        assert res_prim.status_code == 200

        # Remove ministry
        res_del = c.delete(f"/api/kernel/ministries/{persona.id}/PASTOR", headers=h)
        assert res_del.status_code == 200

        # Remove non-existent ministry 404
        res_del_404 = c.delete(f"/api/kernel/ministries/{persona.id}/MAESTRO", headers=h)
        assert res_del_404.status_code == 404

    def test_church_role_flow(self, kernel_setup):
        c = kernel_setup["client"]
        h = kernel_setup["headers"]
        persona = kernel_setup["persona"]

        # My church role
        res_me = c.get("/api/kernel/church-role/me", headers=h)
        assert res_me.status_code == 200

        # Get church role by persona
        res_p = c.get(f"/api/kernel/church-role/{persona.id}", headers=h)
        assert res_p.status_code == 200

        # Update church role
        res_upd = c.put(
            f"/api/kernel/church-role/{persona.id}",
            json={"church_role": "LIDER", "reason": "Ascenso", "notes": "Excelente labor"},
            headers=h,
        )
        assert res_upd.status_code in (200, 201)

        # Invalid church role
        res_bad = c.put(
            f"/api/kernel/church-role/{persona.id}",
            json={"church_role": "SuperHero"},
            headers=h,
        )
        assert res_bad.status_code == 400

        # Get church role history
        res_hist = c.get(f"/api/kernel/church-role/{persona.id}/history", headers=h)
        assert res_hist.status_code == 200

        # Get personas by role
        res_by_role = c.get("/api/kernel/church-role-by/LIDER/personas", headers=h)
        assert res_by_role.status_code == 200

    def test_platform_roles_and_permissions(self, kernel_setup):
        c = kernel_setup["client"]
        h = kernel_setup["headers"]
        persona = kernel_setup["persona"]

        # Platform role definitions
        assert c.get("/api/kernel/platform-roles", headers=h).status_code == 200
        # My platform roles
        assert c.get("/api/kernel/platform-roles/me", headers=h).status_code == 200
        # Persona platform roles
        assert c.get(f"/api/kernel/platform-roles/{persona.id}", headers=h).status_code == 200

        # My permissions
        assert c.get("/api/kernel/permissions/me", headers=h).status_code == 200
        # Persona permissions
        assert c.get(f"/api/kernel/permissions/{persona.id}", headers=h).status_code == 200

        # Can assign check
        assert c.get(f"/api/kernel/can-assign/{persona.id}", headers=h).status_code == 200
