"""
API tests for backend.api.crm.persona_relations.
Simple tests that don't require cross-sede persona validation.
"""
from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="relations@test.com")
    headers = _auth_headers(client, email="relations@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestPersonaRelations:
    def test_communications_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.get(f"/api/crm/personas/{uuid.uuid4()}/communications", headers=h)
        assert resp.status_code == 404

    def test_ministries_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.get(f"/api/crm/personas/{uuid.uuid4()}/ministries", headers=h)
        assert resp.status_code == 404

    def test_crm_profile_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.get(f"/api/crm/personas/{uuid.uuid4()}/crm-perfil", headers=h)
        assert resp.status_code == 404

    def test_family_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.get(f"/api/crm/personas/{uuid.uuid4()}/family", headers=h)
        assert resp.status_code == 404
