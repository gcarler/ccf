"""Tests for grupos_sesiones.py — session CRUD + list."""
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
    admin, _, _ = _seed_admin(db_session, email="ses@test.com")
    headers = _auth_headers(client, email="ses@test.com", password="testpass123")
    return {"c": client, "h": headers, "s": db_session.query(models.Sede).first()}


class TestSesionesCRUD:
    def test_list_sessions(self, full):
        assert _ok(full["c"].get("/api/evangelism/grupos/sessions", headers=full["h"]).status_code)

    def test_list_mine_pending(self, full):
        assert _ok(full["c"].get("/api/evangelism/grupos/sessions/mine/pending",
            headers=full["h"]).status_code)

    def test_list_all(self, full):
        assert _ok(full["c"].get("/api/evangelism/sessions", headers=full["h"]).status_code)

    def test_get_session_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/sessions/{uuid.uuid4()}",
            headers=full["h"]).status_code == 404

    def test_delete_session_not_found(self, full):
        assert full["c"].delete(f"/api/evangelism/sessions/{uuid.uuid4()}",
            headers=full["h"]).status_code == 404

    def test_patch_habilitacion_not_found(self, full):
        assert full["c"].patch(f"/api/evangelism/sessions/{uuid.uuid4()}/habilitacion",
            json={"estado": "FINALIZADO"}, headers=full["h"]).status_code == 404

    def test_create_session(self, full, db_session):
        """Create session with correct schema."""
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="LS", last_name="T", sede_id=s.id)
        db_session.add(p)
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre=f"G-{uuid.uuid4().hex[:6]}",
            sede_id=s.id, lider_persona_id=p.id,
        )
        db_session.add(g)
        db_session.commit()
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        resp = c.post("/api/evangelism/sessions",
            json={"grupo_id": str(g.id), "session_date": now.isoformat(), "topic": "Test"},
            headers=h)
        assert _ok(resp.status_code), f"session: {resp.status_code} {resp.text}"
