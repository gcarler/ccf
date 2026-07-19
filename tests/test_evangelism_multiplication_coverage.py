"""
Coverage tests for evangelism_multiplication.py — target 90%+.
"""
import uuid
from datetime import datetime, timezone

import pytest

from backend import models
from backend.api.evangelism_multiplication import (
    _count_personas,
    _serialize_grupo,
    MultiplicationCheckItem,
    MultiplicationHistoryItem,
    SplitRequest,
    SplitResponse,
    GrupoResumenMultiplicacion,
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


def _make_grupo(db, sede_id, lider_persona_id=None, activo=True):
    g = models.GrupoEvangelismo(
        id=uuid.uuid4(), nombre=f"Grupo_{uuid.uuid4().hex[:6]}",
        sede_id=sede_id, lider_persona_id=lider_persona_id,
        activo=activo, capacidad=20,
    )
    db.add(g)
    db.flush()
    return g


def _add_participante(db, grupo_id, persona_id):
    p = models.ParticipanteGrupo(
        grupo_id=grupo_id, persona_id=persona_id,
        activo=True, rol_base="miembro",
    )
    db.add(p)
    db.flush()


class TestMultiplicationSchemas:
    """Covers Pydantic schemas."""

    def test_split_request_creation(self):
        r = SplitRequest(grupo_id=uuid.uuid4(), nuevo_nombre="Test", nuevo_lider_id=str(uuid.uuid4()))
        assert r.nuevo_nombre == "Test"

    def test_multiplication_check_item(self):
        item = MultiplicationCheckItem(
            grupo_id=uuid.uuid4(), grupo_nombre="G1",
            lider_nombre="Leader", total_personas=10,
            excede_umbral=False, sugerencia="No",
        )
        assert item.grupo_nombre == "G1"

    def test_multiplication_history_item(self):
        item = MultiplicationHistoryItem(
            grupo_id=uuid.uuid4(), grupo_nombre="G1",
        )
        assert item.grupo_nombre == "G1"

    def test_grupo_resumen(self):
        res = GrupoResumenMultiplicacion(
            id=uuid.uuid4(), nombre="G1", activo=True, total_personas=5,
        )
        assert res.total_personas == 5

    def test_split_response(self):
        res = GrupoResumenMultiplicacion(
            id=uuid.uuid4(), nombre="G1", activo=True, total_personas=5,
        )
        sr = SplitResponse(ok=True, mensaje="OK", grupo_original=res, nuevo_grupo=res, personas_transferidas=3)
        assert sr.ok is True


class TestMultiplicationHelpers:
    """Covers helper functions."""

    def test_count_personas_zero(self, full):
        grupo = _make_grupo(full["db"], full["sede"].id)
        full["db"].commit()
        assert _count_personas(full["db"], grupo.id) == 0

    def test_count_personas_with_data(self, full):
        grupo = _make_grupo(full["db"], full["sede"].id, full["persona"].id)
        _add_participante(full["db"], grupo.id, full["persona"].id)
        full["db"].commit()
        assert _count_personas(full["db"], grupo.id) == 1

    def test_serialize_grupo(self, full):
        grupo = _make_grupo(full["db"], full["sede"].id, full["persona"].id)
        _add_participante(full["db"], grupo.id, full["persona"].id)
        full["db"].commit()
        data = _serialize_grupo(grupo, full["db"])
        assert data["nombre"] == grupo.nombre
        assert data["total_personas"] == 1


class TestMultiplicationEndpoints:
    """Covers the 3 endpoints."""

    def test_check_endpoint_empty(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/evangelism/multiplication/check", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_check_endpoint_with_grupo(self, full):
        grupo = _make_grupo(full["db"], full["sede"].id, full["persona"].id)
        _add_participante(full["db"], grupo.id, full["persona"].id)
        full["db"].commit()
        c, h = full["c"], full["h"]
        resp = c.get("/api/evangelism/multiplication/check?umbral=1", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    def test_history_endpoint_empty(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/evangelism/multiplication/history", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_history_endpoint_with_data(self, full):
        """A group with parent_group_id counts as multiplication history."""
        parent = _make_grupo(full["db"], full["sede"].id, full["persona"].id)
        child = _make_grupo(full["db"], full["sede"].id, full["persona"].id)
        child.parent_group_id = parent.id
        full["db"].commit()
        c, h = full["c"], full["h"]
        resp = c.get("/api/evangelism/multiplication/history", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    def test_split_endpoint_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/multiplication/split", headers=h, json={
            "grupo_id": str(uuid.uuid4()),
            "nuevo_nombre": "Nuevo Grupo",
            "nuevo_lider_id": str(full["persona"].id),
        })
        assert resp.status_code == 404

    def test_split_endpoint_inactive(self, full):
        grupo = _make_grupo(full["db"], full["sede"].id, full["persona"].id, activo=False)
        full["db"].commit()
        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/multiplication/split", headers=h, json={
            "grupo_id": str(grupo.id),
            "nuevo_nombre": "Nuevo Grupo",
            "nuevo_lider_id": str(full["persona"].id),
        })
        assert resp.status_code == 400
        assert "inactivo" in resp.text.lower()

    def test_split_endpoint_less_than_2_participants(self, full):
        grupo = _make_grupo(full["db"], full["sede"].id, full["persona"].id, activo=True)
        _add_participante(full["db"], grupo.id, full["persona"].id)
        full["db"].commit()
        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/multiplication/split", headers=h, json={
            "grupo_id": str(grupo.id),
            "nuevo_nombre": "Nuevo Grupo",
            "nuevo_lider_id": str(full["persona"].id),
        })
        assert resp.status_code == 400
        assert "2 personas" in resp.text.lower()

    def test_split_endpoint_success(self, full):
        grupo = _make_grupo(full["db"], full["sede"].id, full["persona"].id, activo=True)
        _add_participante(full["db"], grupo.id, full["persona"].id)
        # Need a second persona
        from backend.models_crm import Persona
        p2 = Persona(id=uuid.uuid4(), first_name="Segunda", last_name="Persona", sede_id=full["sede"].id)
        full["db"].add(p2)
        _add_participante(full["db"], grupo.id, p2.id)
        full["db"].commit()

        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/multiplication/split", headers=h, json={
            "grupo_id": str(grupo.id),
            "nuevo_nombre": "Grupo Hijo Test",
            "nuevo_lider_id": str(p2.id),
        })
        assert resp.status_code == 200, f"Expected 200 got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["ok"] is True
        assert data["personas_transferidas"] >= 1
