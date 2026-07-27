"""
Extended API + unit tests for backend.api.spiritual_life.
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest

from backend.api.spiritual_life import (
    _get_user_sede_id,
    _assert_persona_in_sede,
    _assert_milestone_in_sede,
)
from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="slife@test.com")
    headers = _auth_headers(client, email="slife@test.com", password="testpass123")
    return {"c": client, "h": headers}


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS — helper functions
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetUserSedeId:
    def test_with_admin_user(self, full, db_session):
        admin, _, sede = _seed_admin(db_session, email="sedecheck@test.com")
        result = _get_user_sede_id(db_session, admin.id)
        assert result is not None
        assert isinstance(result, uuid.UUID)

    def test_with_nonexistent_user(self, db_session):
        result = _get_user_sede_id(db_session, uuid.uuid4())
        assert result is None


class TestAssertPersonaInSede:
    def test_persona_not_found(self, db_session):
        with pytest.raises(Exception) as exc:
            _assert_persona_in_sede(db_session, uuid.uuid4(), None)
        assert "404" in str(exc.value)

    def test_persona_in_sede_match(self, db_session):
        sede = models.Sede(id=uuid.uuid4(), nombre="Test", ciudad="Bogota", es_activa=True)
        db_session.add(sede)
        db_session.flush()
        persona = models.Persona(id=uuid.uuid4(), first_name="Test", last_name="User", sede_id=sede.id)
        db_session.add(persona)
        db_session.commit()
        result = _assert_persona_in_sede(db_session, persona.id, sede.id)
        assert result.id == persona.id

    def test_persona_cross_sede_raises_404(self, db_session):
        sede_a = models.Sede(id=uuid.uuid4(), nombre="A", ciudad="Bogota", es_activa=True)
        sede_b = models.Sede(id=uuid.uuid4(), nombre="B", ciudad="Bogota", es_activa=True)
        db_session.add_all([sede_a, sede_b])
        db_session.flush()
        persona = models.Persona(id=uuid.uuid4(), first_name="Test", last_name="User", sede_id=sede_a.id)
        db_session.add(persona)
        db_session.commit()
        with pytest.raises(Exception) as exc:
            _assert_persona_in_sede(db_session, persona.id, sede_b.id)
        assert "404" in str(exc.value)


class TestAssertMilestoneInSede:
    def test_milestone_not_found(self, db_session):
        with pytest.raises(Exception) as exc:
            _assert_milestone_in_sede(db_session, uuid.uuid4(), None)
        assert "404" in str(exc.value)

    def test_milestone_found_and_in_sede(self, db_session):
        sede = models.Sede(id=uuid.uuid4(), nombre="Test", ciudad="Bogota", es_activa=True)
        db_session.add(sede)
        db_session.flush()
        persona = models.Persona(id=uuid.uuid4(), first_name="T", last_name="U", sede_id=sede.id)
        db_session.add(persona)
        db_session.flush()
        milestone = models.SpiritualMilestone(
            id=uuid.uuid4(), persona_id=persona.id, type="Bautismo_Aguas",
            event_date=date(2026, 1, 1), sede_id=sede.id,
        )
        db_session.add(milestone)
        db_session.commit()
        result = _assert_milestone_in_sede(db_session, milestone.id, sede.id)
        assert result.id == milestone.id

    def test_milestone_cross_sede_raises_404(self, db_session):
        sede_a = models.Sede(id=uuid.uuid4(), nombre="A", ciudad="Bogota", es_activa=True)
        sede_b = models.Sede(id=uuid.uuid4(), nombre="B", ciudad="Bogota", es_activa=True)
        db_session.add_all([sede_a, sede_b])
        db_session.flush()
        persona = models.Persona(id=uuid.uuid4(), first_name="T", last_name="U", sede_id=sede_a.id)
        db_session.add(persona)
        db_session.flush()
        milestone = models.SpiritualMilestone(
            id=uuid.uuid4(), persona_id=persona.id, type="Bautismo_Aguas",
            event_date=date(2026, 1, 1), sede_id=sede_a.id,
        )
        db_session.add(milestone)
        db_session.commit()
        with pytest.raises(Exception) as exc:
            _assert_milestone_in_sede(db_session, milestone.id, sede_b.id)
        assert "404" in str(exc.value)


# ═══════════════════════════════════════════════════════════════════════════════
# API TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestListMilestones:
    def test_list_empty(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/spiritual-life/milestones", headers=h)
        assert _ok(resp.status_code)
        assert resp.json() == []

    def test_list_with_persona_id(self, full, db_session):
        c, h = full["c"], full["h"]
        sede = db_session.query(models.Sede).first()
        persona = models.Persona(id=uuid.uuid4(), first_name="T", last_name="U", sede_id=sede.id)
        db_session.add(persona)
        db_session.commit()
        resp = c.get(f"/api/spiritual-life/milestones?persona_id={persona.id}", headers=h)
        assert _ok(resp.status_code)


class TestGetPersonaMilestones:
    def test_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.get(f"/api/spiritual-life/milestones/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404

    def test_invalid_uuid_422(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/spiritual-life/milestones/not-a-uuid", headers=h)
        assert resp.status_code == 422

    def test_with_persona(self, full, db_session):
        c, h = full["c"], full["h"]
        sede = db_session.query(models.Sede).first()
        persona = models.Persona(id=uuid.uuid4(), first_name="T", last_name="U", sede_id=sede.id)
        db_session.add(persona)
        db_session.commit()
        resp = c.get(f"/api/spiritual-life/milestones/{persona.id}", headers=h)
        assert _ok(resp.status_code)


class TestCreateMilestone:
    def test_create(self, full, db_session):
        c, h = full["c"], full["h"]
        sede = db_session.query(models.Sede).first()
        persona = models.Persona(id=uuid.uuid4(), first_name="T", last_name="U", sede_id=sede.id)
        db_session.add(persona)
        db_session.commit()
        resp = c.post(
            "/api/spiritual-life/milestones",
            json={
                "persona_id": str(persona.id),
                "type": "Bautismo_Aguas",
                "event_date": "2026-01-01",
            },
            headers=h,
        )
        assert _ok(resp.status_code), f"create: {resp.status_code} {resp.text}"
        assert resp.json()["type"] == "Bautismo_Aguas"

    def test_create_persona_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/spiritual-life/milestones",
            json={
                "persona_id": str(uuid.uuid4()),
                "type": "Bautismo_Aguas",
                "event_date": "2026-01-01",
            },
            headers=h,
        )
        assert resp.status_code == 404

    def test_create_with_minister(self, full, db_session):
        c, h = full["c"], full["h"]
        sede = db_session.query(models.Sede).first()
        persona = models.Persona(id=uuid.uuid4(), first_name="T", last_name="U", sede_id=sede.id)
        db_session.add(persona)
        minister = models.Persona(id=uuid.uuid4(), first_name="Min", last_name="ister", sede_id=sede.id)
        db_session.add(minister)
        db_session.commit()
        resp = c.post(
            "/api/spiritual-life/milestones",
            json={
                "persona_id": str(persona.id),
                "type": "Bautismo_Aguas",
                "event_date": "2026-01-01",
                "minister_id": str(minister.id),
            },
            headers=h,
        )
        assert _ok(resp.status_code), f"create_with_minister: {resp.status_code} {resp.text}"

    def test_create_minister_not_found(self, full, db_session):
        c, h = full["c"], full["h"]
        sede = db_session.query(models.Sede).first()
        persona = models.Persona(id=uuid.uuid4(), first_name="T", last_name="U", sede_id=sede.id)
        db_session.add(persona)
        db_session.commit()
        resp = c.post(
            "/api/spiritual-life/milestones",
            json={
                "persona_id": str(persona.id),
                "type": "Bautismo_Aguas",
                "event_date": "2026-01-01",
                "minister_id": str(uuid.uuid4()),
            },
            headers=h,
        )
        assert resp.status_code == 404


class TestGetSingleMilestone:
    def test_get_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.get(f"/api/spiritual-life/milestone/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404

    def test_get_existing(self, full, db_session):
        c, h = full["c"], full["h"]
        sede = db_session.query(models.Sede).first()
        persona = models.Persona(id=uuid.uuid4(), first_name="T", last_name="U", sede_id=sede.id)
        db_session.add(persona)
        db_session.flush()
        milestone = models.SpiritualMilestone(
            id=uuid.uuid4(), persona_id=persona.id, type="Bautismo_Aguas",
            event_date=date(2026, 1, 1), sede_id=sede.id,
        )
        db_session.add(milestone)
        db_session.commit()
        resp = c.get(f"/api/spiritual-life/milestone/{milestone.id}", headers=h)
        assert _ok(resp.status_code)
        assert resp.json()["type"] == "Bautismo_Aguas"


class TestUpdateMilestone:
    def test_update(self, full, db_session):
        c, h = full["c"], full["h"]
        sede = db_session.query(models.Sede).first()
        persona = models.Persona(id=uuid.uuid4(), first_name="T", last_name="U", sede_id=sede.id)
        db_session.add(persona)
        db_session.flush()
        milestone = models.SpiritualMilestone(
            id=uuid.uuid4(), persona_id=persona.id, type="Bautismo_Aguas",
            event_date=date(2026, 1, 1), sede_id=sede.id,
        )
        db_session.add(milestone)
        db_session.commit()
        resp = c.patch(
            f"/api/spiritual-life/milestone/{milestone.id}",
            json={"notes": "Updated notes"},
            headers=h,
        )
        assert _ok(resp.status_code), f"update: {resp.status_code} {resp.text}"
        assert resp.json()["notes"] == "Updated notes"

    def test_update_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.patch(
            f"/api/spiritual-life/milestone/{uuid.uuid4()}",
            json={"notes": "X"},
            headers=h,
        )
        assert resp.status_code == 404

    def test_update_empty_payload_422(self, full, db_session):
        c, h = full["c"], full["h"]
        sede = db_session.query(models.Sede).first()
        persona = models.Persona(id=uuid.uuid4(), first_name="T", last_name="U", sede_id=sede.id)
        db_session.add(persona)
        db_session.flush()
        milestone = models.SpiritualMilestone(
            id=uuid.uuid4(), persona_id=persona.id, type="Bautismo_Aguas",
            event_date=date(2026, 1, 1), sede_id=sede.id,
        )
        db_session.add(milestone)
        db_session.commit()
        resp = c.patch(
            f"/api/spiritual-life/milestone/{milestone.id}",
            json={},
            headers=h,
        )
        assert resp.status_code == 422

    def test_update_with_minister(self, full, db_session):
        c, h = full["c"], full["h"]
        sede = db_session.query(models.Sede).first()
        persona = models.Persona(id=uuid.uuid4(), first_name="T", last_name="U", sede_id=sede.id)
        db_session.add(persona)
        minister = models.Persona(id=uuid.uuid4(), first_name="Min", last_name="ister", sede_id=sede.id)
        db_session.add(minister)
        db_session.flush()
        milestone = models.SpiritualMilestone(
            id=uuid.uuid4(), persona_id=persona.id, type="Bautismo_Aguas",
            event_date=date(2026, 1, 1), sede_id=sede.id,
        )
        db_session.add(milestone)
        db_session.commit()
        resp = c.patch(
            f"/api/spiritual-life/milestone/{milestone.id}",
            json={"minister_id": str(minister.id)},
            headers=h,
        )
        assert _ok(resp.status_code)


class TestDeleteMilestone:
    def test_delete(self, full, db_session):
        c, h = full["c"], full["h"]
        sede = db_session.query(models.Sede).first()
        persona = models.Persona(id=uuid.uuid4(), first_name="T", last_name="U", sede_id=sede.id)
        db_session.add(persona)
        db_session.flush()
        milestone = models.SpiritualMilestone(
            id=uuid.uuid4(), persona_id=persona.id, type="Bautismo_Aguas",
            event_date=date(2026, 1, 1), sede_id=sede.id,
        )
        db_session.add(milestone)
        db_session.commit()
        resp = c.delete(f"/api/spiritual-life/milestone/{milestone.id}", headers=h)
        assert resp.status_code == 204

    def test_delete_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.delete(f"/api/spiritual-life/milestone/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404
