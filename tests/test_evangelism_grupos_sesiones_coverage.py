"""
Coverage tests for evangelism_grupos/grupos_sesiones.py — target 80%+.
"""
import uuid
from datetime import datetime, timezone

import pytest

from backend import models
from backend.api.evangelism_grupos.grupos_sesiones import (
    _session_read_options,
)
from tests.conftest import seed_admin as _seed_admin, auth_headers as _auth_headers


@pytest.fixture
def full(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {
        "c": client, "h": headers, "db": db_session,
        "admin": admin, "persona": persona, "sede": sede,
    }


def _make_grupo(db, sede_id, persona_id=None):
    g = models.GrupoEvangelismo(
        id=uuid.uuid4(), nombre=f"G_{uuid.uuid4().hex[:4]}",
        sede_id=sede_id, lider_persona_id=persona_id, activo=True,
    )
    db.add(g)
    db.flush()
    return g


class TestGrupoSesionesHelpers:
    def test_session_read_options_returns_options(self, full):
        opts = _session_read_options(full["db"])
        assert opts is not None


class TestGrupoSesionesEndpoints:
    def test_list_sessions_empty(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/evangelism/grupos/sessions", headers=h)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_sessions_with_group(self, full):
        grupo = _make_grupo(full["db"], full["sede"].id, full["persona"].id)
        s = models.SesionGrupo(
            grupo_id=grupo.id, fecha_sesion=datetime.now(timezone.utc),
        )
        full["db"].add(s)
        full["db"].commit()
        c, h = full["c"], full["h"]
        resp = c.get(f"/api/evangelism/grupos/sessions?grupo_id={grupo.id}", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    def test_list_pending_sessions(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/evangelism/grupos/sessions/mine/pending", headers=h)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_pending_sessions_with_data(self, full):
        grupo = _make_grupo(full["db"], full["sede"].id, full["persona"].id)
        s = models.SesionGrupo(
            grupo_id=grupo.id, fecha_sesion=datetime.now(timezone.utc),
        )
        full["db"].add(s)
        full["db"].commit()
        c, h = full["c"], full["h"]
        resp = c.get("/api/evangelism/grupos/sessions/mine/pending", headers=h)
        assert resp.status_code == 200

    def test_groups_sessions_alias(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/evangelism/groups/sessions", headers=h)
        assert resp.status_code == 200

    def test_groups_pending_alias(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/evangelism/groups/sessions/mine/pending", headers=h)
        assert resp.status_code == 200
