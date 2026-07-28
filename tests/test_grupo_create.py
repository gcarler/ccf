"""Create grupo with correct schema — no extra fields."""
from __future__ import annotations

import uuid

import pytest

from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="grpc@test.com")
    headers = _auth_headers(client, email="grpc@test.com", password="testpass123")
    s = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": s}


class TestGrupoCreate:
    def test_create_simple(self, full, db_session):
        """Create grupo with minimal fields (name only)."""
        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/grupos",
            json={"name": f"G-{uuid.uuid4().hex[:6]}"},
            headers=h)
        assert _ok(resp.status_code), f"create: {resp.status_code} {resp.text}"

    def test_create_with_strategy(self, full, db_session):
        c, h = full["c"], full["h"]
        # Create strategy first
        strat = c.post("/api/evangelism/strategies",
            json={"name": f"S-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        resp = c.post("/api/evangelism/grupos",
            json={"name": f"GS-{uuid.uuid4().hex[:6]}",
                  "evangelism_strategy_id": strat["id"]},
            headers=h)
        assert _ok(resp.status_code), f"create_with_strat: {resp.status_code} {resp.text}"

    def test_create_with_leader(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="L", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        resp = c.post("/api/evangelism/grupos",
            json={"name": f"GL-{uuid.uuid4().hex[:6]}", "leader_id": str(p.id)},
            headers=h)
        assert _ok(resp.status_code), f"create_with_leader: {resp.status_code} {resp.text}"

    def test_extra_field_422(self, full):
        """extra='forbid' means unexpected fields cause 422."""
        resp = full["c"].post("/api/evangelism/grupos",
            json={"name": "Test", "extra": "x"},
            headers=full["h"])
        assert resp.status_code == 422

    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/grupos/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_create_and_get(self, full):
        c, h = full["c"], full["h"]
        name = f"GG-{uuid.uuid4().hex[:6]}"
        g = c.post("/api/evangelism/grupos", json={"name": name}, headers=h).json()
        gid = g["id"]
        resp = c.get(f"/api/evangelism/grupos/{gid}", headers=h)
        assert _ok(resp.status_code)

    def test_update(self, full):
        c, h = full["c"], full["h"]
        g = c.post("/api/evangelism/grupos",
            json={"name": f"GU-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        resp = c.put(f"/api/evangelism/grupos/{g['id']}",
            json={"name": "Updated"}, headers=h)
        assert _ok(resp.status_code), f"update: {resp.status_code} {resp.text}"
