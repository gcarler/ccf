"""Cover remaining branches in grupos_sesiones.py."""
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
    p = Persona(id=uuid.uuid4(), first_name="SS2", last_name="U", sede_id=sede.id)
    db_session.add(p)
    db_session.flush()
    user = Usuario(
        id=p.id, sede_id=sede.id, username="sess2", email="sess2@test.com",
        password_hash=get_password_hash("test123"),
        rol_plataforma_id=role.id, is_active=True, is_email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    return {"user": user, "sede": sede}


@pytest.fixture
def evan_full(client, evan_user, db_session):
    headers = _auth_headers(client, email="sess2@test.com", password="test123")
    return {"c": client, "h": headers, "s": evan_user["sede"]}


def _setup_grupo(db_session, sede):
    p = Persona(id=uuid.uuid4(), first_name="Base", last_name="T", sede_id=sede.id)
    db_session.add(p)
    db_session.flush()
    g = GrupoEvangelismo(id=uuid.uuid4(), nombre="BaseG", sede_id=sede.id, lider_persona_id=p.id)
    db_session.add(g)
    db_session.flush()
    return g


class TestListSessionsFilters:
    def test_filter_by_grupo_id(self, evan_full, db_session):
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        g = _setup_grupo(db_session, s)
        ses = SesionGrupo(id=uuid.uuid4(), grupo_id=g.id, session_date=date(2026, 7, 15))
        db_session.add(ses)
        db_session.commit()
        resp = c.get(f"/api/evangelism/grupos/sessions?grupo_id={g.id}", headers=h)
        assert _ok(resp.status_code)

    def test_list_sessions_filter_strategy(self, evan_full, db_session):
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        resp = c.get(f"/api/evangelism/sessions?strategy_id={uuid.uuid4()}", headers=h)
        assert _ok(resp.status_code)

    def test_list_sessions_filter_house(self, evan_full, db_session):
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        resp = c.get(f"/api/evangelism/sessions?house_id={uuid.uuid4()}", headers=h)
        assert _ok(resp.status_code)


class TestCreateSessionEdge:
    def test_create_session_missing_grupo_id(self, evan_full):
        """POST /sessions without grupo_id -> 400 (endpoint validation)."""
        resp = evan_full["c"].post("/api/evangelism/sessions",
            json={"session_date": "2026-07-15", "topic": "Test"},
            headers=evan_full["h"])
        assert resp.status_code == 400

    def test_create_session_grupo_not_found(self, evan_full):
        resp = evan_full["c"].post("/api/evangelism/sessions",
            json={"session_date": "2026-07-15", "grupo_id": str(uuid.uuid4()),
                  "topic": "Test"},
            headers=evan_full["h"])
        assert resp.status_code == 404

    def test_create_session_valid(self, evan_full, db_session):
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        g = _setup_grupo(db_session, s)
        resp = c.post("/api/evangelism/sessions",
            json={"session_date": "2026-07-15", "grupo_id": str(g.id),
                  "topic": "Test", "status": "Realizada"},
            headers=h)
        assert _ok(resp.status_code), f"create session: {resp.status_code} {resp.text[:200]}"


class TestUpdateSession:
    def test_update_session(self, evan_full, db_session):
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        g = _setup_grupo(db_session, s)
        ses = SesionGrupo(id=uuid.uuid4(), grupo_id=g.id, session_date=date(2026, 7, 15))
        db_session.add(ses)
        db_session.commit()
        resp = c.put(f"/api/evangelism/sessions/{ses.id}",
            json={"topic": "Updated Topic"}, headers=h)
        assert _ok(resp.status_code), f"update: {resp.status_code} {resp.text[:200]}"

    def test_update_not_found(self, evan_full):
        resp = evan_full["c"].put(f"/api/evangelism/sessions/{uuid.uuid4()}",
            json={"topic": "Test"}, headers=evan_full["h"])
        assert resp.status_code == 404


class TestMinePendingEdge:
    def test_mine_pending_non_admin_no_persona(self, db_session, evan_user):
        """Non-admin user without persona returns []."""
        from backend.api.evangelism_grupos.grupos_sesiones import list_my_pending_groups_sessions

        # Create a user-like mock with non-admin role and no linked persona
        class MockRole:
            nombre = "MIEMBRO"

        class MockUser:
            id = uuid.uuid4()
            role = "miembro"
            rol_plataforma = MockRole()

        result = list_my_pending_groups_sessions(db_session, MockUser())
        # Should return empty list since no persona found
        assert result == []


class TestHabTodas:
    def test_habilitar_todas(self, evan_full, db_session):
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        # Create strategy with grupo
        strat = c.post("/api/evangelism/strategies",
            json={"name": f"HT-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])
        g = _setup_grupo(db_session, s)
        g.estrategia_id = sid
        db_session.commit()
        resp = c.post(f"/api/evangelism/strategies/{sid}/habilitar-todas", headers=h)
        assert _ok(resp.status_code)

    def test_deshabilitar_todas(self, evan_full, db_session):
        c, h, s = evan_full["c"], evan_full["h"], evan_full["s"]
        strat = c.post("/api/evangelism/strategies",
            json={"name": f"DT-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        sid = uuid.UUID(strat["id"])
        g = _setup_grupo(db_session, s)
        g.estrategia_id = sid
        db_session.commit()
        resp = c.post(f"/api/evangelism/strategies/{sid}/deshabilitar-todas", headers=h)
        assert _ok(resp.status_code)

    def test_habilitar_todas_no_grupos(self, evan_full):
        resp = evan_full["c"].post(f"/api/evangelism/strategies/{uuid.uuid4()}/habilitar-todas",
            headers=evan_full["h"])
        assert resp.status_code == 404
