"""Integration tests — correct schema fields for all working endpoints."""

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
    admin, _, _ = _seed_admin(db_session, email="deep@test.com")
    headers = _auth_headers(client, email="deep@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestDeep:
    def test_strategy(self, full):
        assert _ok(
            full["c"]
            .post("/api/evangelism/strategies", json={"name": f"S-{uuid.uuid4().hex[:6]}"}, headers=full["h"])
            .status_code
        )

    def test_grupo(self, full):
        assert _ok(
            full["c"]
            .post("/api/evangelism/grupos", json={"name": f"G-{uuid.uuid4().hex[:6]}"}, headers=full["h"])
            .status_code
        )

    def test_session(self, full, db_session):
        c, h = full["c"], full["h"]
        s = db_session.query(models.Sede).first()
        p = models.Persona(id=uuid.uuid4(), first_name="L", last_name="T", sede_id=s.id)
        db_session.add(p)
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(),
            nombre=f"GS-{uuid.uuid4().hex[:6]}",
            sede_id=s.id,
            lider_persona_id=p.id,
        )
        db_session.add(g)
        db_session.commit()
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        assert _ok(
            c.post(
                "/api/evangelism/sessions",
                json={"grupo_id": str(g.id), "session_date": now.isoformat(), "topic": "Test"},
                headers=h,
            ).status_code
        )
