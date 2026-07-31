"""Tests for grupos_sesiones.py — session CRUD, listing, search."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, date

import pytest

from backend import models
from backend.models_evangelism import Sede, GrupoEvangelismo, SesionGrupo, CampaignSeason
from backend.models_crm import Persona
from backend.models_auth import Usuario, RolPlataforma
from backend.core.security import get_password_hash
from tests.conftest import auth_headers as _auth_headers


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def evan_user(db_session):
    """Create an evangelist user with explicit edit/manage permissions."""
    sede = db_session.query(Sede).first()
    if not sede:
        sede = Sede(id=uuid.uuid4(), nombre="Test", ciudad="Test", es_activa=True)
        db_session.add(sede)
        db_session.flush()

    role = RolPlataforma(
        id=uuid.uuid4(), nombre="EVANGELISTA",
        permisos={"evangelism:read": "allow", "evangelism:edit": "allow", "evangelism:manage": "allow"},
    )
    db_session.add(role)
    db_session.flush()

    p = Persona(id=uuid.uuid4(), first_name="Sess", last_name="User", sede_id=sede.id)
    db_session.add(p)
    db_session.flush()

    user = Usuario(
        id=p.id, sede_id=sede.id, username="sess",
        email="sess@test.com",
        password_hash=get_password_hash("test123"),
        rol_plataforma_id=role.id, is_active=True, is_email_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    return {"user": user, "sede": sede}


@pytest.fixture
def evan_full(client, evan_user, db_session):
    headers = _auth_headers(client, email="sess@test.com", password="test123")
    return {"c": client, "h": headers, "s": evan_user["sede"]}


class TestListSessions:
    def test_list_sessions_empty(self, evan_full):
        resp = evan_full["c"].get("/api/evangelism/sessions", headers=evan_full["h"])
        assert _ok(resp.status_code)
        assert resp.json() == []

    def test_list_sessions_with_data(self, evan_full, db_session):
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        p = Persona(id=uuid.uuid4(), first_name="SL", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()
        g = GrupoEvangelismo(id=uuid.uuid4(), nombre="SG", sede_id=s.id, lider_persona_id=p.id,
                            activo=True)
        db_session.add(g)
        db_session.flush()
        ses = SesionGrupo(id=uuid.uuid4(), grupo_id=g.id, session_date=date(2026, 7, 15),
                          status="Realizada")
        db_session.add(ses)
        db_session.commit()

        resp = c.get("/api/evangelism/sessions", headers=h)
        assert _ok(resp.status_code)
        assert len(resp.json()) >= 1

    def test_list_grupos_sessions(self, evan_full, db_session):
        """GET /grupos/sessions endpoint."""
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        p = Persona(id=uuid.uuid4(), first_name="GS", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()
        g = GrupoEvangelismo(id=uuid.uuid4(), nombre="GSG", sede_id=s.id, lider_persona_id=p.id)
        db_session.add(g)
        db_session.flush()
        ses = SesionGrupo(id=uuid.uuid4(), grupo_id=g.id, session_date=date(2026, 7, 15),
                          status="Realizada")
        db_session.add(ses)
        ses2 = SesionGrupo(id=uuid.uuid4(), grupo_id=g.id, session_date=date(2026, 6, 15),
                          status="Realizada")
        db_session.add(ses2)
        db_session.commit()

        resp = c.get("/api/evangelism/grupos/sessions", headers=h)
        assert _ok(resp.status_code)
        data = resp.json()
        assert len(data) >= 2


class TestSessionDetail:
    def test_get_session_detail(self, evan_full, db_session):
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        p = Persona(id=uuid.uuid4(), first_name="SD", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()
        g = GrupoEvangelismo(id=uuid.uuid4(), nombre="SDG", sede_id=s.id, lider_persona_id=p.id)
        db_session.add(g)
        db_session.flush()
        ses = SesionGrupo(id=uuid.uuid4(), grupo_id=g.id, session_date=date(2026, 7, 15),
                          status="Realizada")
        db_session.add(ses)
        db_session.commit()

        resp = c.get(f"/api/evangelism/sessions/{ses.id}", headers=h)
        assert _ok(resp.status_code), f"detail: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        assert "session" in data
        assert "attendance" in data

    def test_get_session_not_found(self, evan_full):
        assert evan_full["c"].get(f"/api/evangelism/sessions/{uuid.uuid4()}",
            headers=evan_full["h"]).status_code == 404


class TestCreateSession:
    def test_create_session(self, evan_full, db_session):
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        p = Persona(id=uuid.uuid4(), first_name="CS", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()
        g = GrupoEvangelismo(id=uuid.uuid4(), nombre="CSG", sede_id=s.id, lider_persona_id=p.id)
        db_session.add(g)
        db_session.commit()

        season = CampaignSeason(id=uuid.uuid4(), name="Summer", sede_id=s.id,
                               start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
        db_session.add(season)
        db_session.commit()

        resp = c.post("/api/evangelism/grupos/sessions",
            json={
                "session_date": "2026-07-15",
                "season_id": str(season.id),
                "grupo_id": str(g.id),
                "topic": "Test Session",
            },
            headers=h)
        assert _ok(resp.status_code), f"create: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        assert data["created_count"] >= 1

    def test_create_session_missing_date(self, evan_full):
        resp = evan_full["c"].post("/api/evangelism/grupos/sessions",
            json={"season_id": str(uuid.uuid4()), "grupo_id": str(uuid.uuid4())},
            headers=evan_full["h"])
        assert resp.status_code == 400

    def test_create_session_bad_date(self, evan_full):
        resp = evan_full["c"].post("/api/evangelism/grupos/sessions",
            json={"session_date": "bad-date", "season_id": str(uuid.uuid4())},
            headers=evan_full["h"])
        assert resp.status_code == 400

    def test_create_session_missing_season(self, evan_full):
        resp = evan_full["c"].post("/api/evangelism/grupos/sessions",
            json={"session_date": "2026-07-15", "grupo_id": str(uuid.uuid4())},
            headers=evan_full["h"])
        assert resp.status_code == 400


class TestDeleteSession:
    def test_delete_session(self, evan_full, db_session):
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        p = Persona(id=uuid.uuid4(), first_name="DS", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()
        g = GrupoEvangelismo(id=uuid.uuid4(), nombre="DSG", sede_id=s.id, lider_persona_id=p.id)
        db_session.add(g)
        db_session.flush()
        ses = SesionGrupo(id=uuid.uuid4(), grupo_id=g.id, session_date=date(2026, 7, 15),
                          status="Realizada")
        db_session.add(ses)
        db_session.commit()

        resp = c.delete(f"/api/evangelism/sessions/{ses.id}", headers=h)
        assert _ok(resp.status_code), f"delete: {resp.status_code} {resp.text[:200]}"

    def test_delete_not_found(self, evan_full):
        assert evan_full["c"].delete(f"/api/evangelism/sessions/{uuid.uuid4()}",
            headers=evan_full["h"]).status_code == 404


class TestSearchPersonas:
    def test_search_min_length(self, evan_full):
        resp = evan_full["c"].get("/api/evangelism/personas/search?q=ab",
            headers=evan_full["h"])
        assert _ok(resp.status_code)
        assert resp.json() == {"results": []}

    def test_search_too_short(self, evan_full):
        resp = evan_full["c"].get("/api/evangelism/personas/search?q=a",
            headers=evan_full["h"])
        assert _ok(resp.status_code)

    def test_search_with_results(self, evan_full, db_session):
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        p = Persona(id=uuid.uuid4(), first_name="Searchable", last_name="Person",
                   sede_id=s.id, email="search@test.com", phone="+573001234567")
        db_session.add(p)
        db_session.commit()

        resp = c.get("/api/evangelism/personas/search?q=search", headers=h)
        assert _ok(resp.status_code)
        data = resp.json()
        assert len(data["results"]) >= 1


class TestHabilitacion:
    def test_habilitar_session(self, evan_full, db_session):
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        p = Persona(id=uuid.uuid4(), first_name="Hab", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()
        g = GrupoEvangelismo(id=uuid.uuid4(), nombre="HabG", sede_id=s.id, lider_persona_id=p.id)
        db_session.add(g)
        db_session.flush()
        ses = SesionGrupo(id=uuid.uuid4(), grupo_id=g.id, session_date=date(2026, 7, 15),
                          status="Realizada")
        db_session.add(ses)
        db_session.commit()

        resp = c.patch(f"/api/evangelism/sessions/{ses.id}/habilitacion",
            json={"accion": "HABILITAR"}, headers=h)
        assert _ok(resp.status_code), f"habilitar: {resp.status_code} {resp.text[:200]}"

    def test_habilitar_invalid_action(self, evan_full, db_session):
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        p = Persona(id=uuid.uuid4(), first_name="HA", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()
        g = GrupoEvangelismo(id=uuid.uuid4(), nombre="HAG", sede_id=s.id, lider_persona_id=p.id)
        db_session.add(g)
        db_session.flush()
        ses = SesionGrupo(id=uuid.uuid4(), grupo_id=g.id, session_date=date(2026, 7, 15),
                          status="Realizada")
        db_session.add(ses)
        db_session.commit()

        resp = c.patch(f"/api/evangelism/sessions/{ses.id}/habilitacion",
            json={"accion": "INVALID"}, headers=h)
        assert resp.status_code == 400


class TestMinePending:
    def test_mine_pending_admin(self, evan_full):
        """Admin should see pending sessions."""
        resp = evan_full["c"].get("/api/evangelism/grupos/sessions/mine/pending",
            headers=evan_full["h"])
        assert _ok(resp.status_code)
