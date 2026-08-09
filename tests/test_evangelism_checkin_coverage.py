"""
Coverage tests for evangelism_events/events_checkin.py — target 80%+.
"""

import uuid

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture
def full(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {
        "c": client,
        "h": headers,
        "db": db_session,
        "admin": admin,
        "persona": persona,
        "sede": sede,
    }


def _make_event(db, sede_id):
    from datetime import datetime, timezone

    from backend import models

    e = models.CrmEvent(
        id=uuid.uuid4(),
        name="Test Event",
        description="Desc",
        event_type="service",
        event_date=datetime.now(timezone.utc),
        sede_id=sede_id,
    )
    db.add(e)
    db.flush()
    return e


class TestCheckinEndpoint:
    def test_checkin_visitor_invalid_date(self, full):
        c, h = full["c"], full["h"]
        # Create event first to reach date validation
        event = _make_event(full["db"], full["sede"].id)
        full["db"].commit()
        resp = c.post(
            f"/api/evangelism/events/{event.id}/sessions/invalid-date/visitors",
            headers=h,
            json={"first_name": "Test", "last_name": "Visitor"},
        )
        assert resp.status_code in (400, 422)

    def test_checkin_visitor_event_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            f"/api/evangelism/events/{uuid.uuid4()}/sessions/2026-07-20/visitors",
            headers=h,
            json={"first_name": "Test", "last_name": "Visitor"},
        )
        assert resp.status_code == 404

    def test_checkin_visitor_success_new(self, full):
        event = _make_event(full["db"], full["sede"].id)
        full["db"].commit()
        c, h = full["c"], full["h"]
        resp = c.post(
            f"/api/evangelism/events/{event.id}/sessions/2026-07-20/visitors",
            headers=h,
            json={"first_name": "Nuevo", "last_name": "Visitante", "phone": "3001234567"},
        )
        assert resp.status_code in (200, 201), f"Expected 2xx, got {resp.status_code}: {resp.text[:200]}"

    def test_checkin_visitor_duplicate(self, full):
        event = _make_event(full["db"], full["sede"].id)
        full["db"].commit()
        c, h = full["c"], full["h"]
        c.post(
            f"/api/evangelism/events/{event.id}/sessions/2026-07-20/visitors",
            headers=h,
            json={"first_name": "Dup", "last_name": "Visitor", "phone": "3007654321"},
        )
        resp = c.post(
            f"/api/evangelism/events/{event.id}/sessions/2026-07-20/visitors",
            headers=h,
            json={"first_name": "Dup", "last_name": "Visitor", "phone": "3007654321"},
        )
        assert resp.status_code in (200, 201)


class TestAttendanceCloseEndpoint:
    """Regresión: POST /events/{id}/attendance/close no debe crashear.

    El bug: el endpoint pasaba ``sede_id=`` a ``close_event_attendance``,
    que no lo acepta → TypeError (500) al cerrar asistencia.

    Se mockea ``ensure_event_crm_followup`` para aislar el cableado del
    endpoint (lo que corregimos) de la maquinaria del bridge CRM: en el
    SQLite in-memory de los tests la primera creación del followup
    (pipeline/etapa/caso con savepoints) no persiste la transacción
    compuesta, por lo que sin el mock las aserciones de estado y la
    idempotencia no serían verificables aquí.
    """

    def test_close_attendance_endpoint_ok(self, full):
        from unittest.mock import patch

        from backend import models

        db = full["db"]
        event = _make_event(db, full["sede"].id)
        persona = models.Persona(
            id=uuid.uuid4(),
            sede_id=full["sede"].id,
            first_name="Asist",
            last_name="Test",
            email=f"close{uuid.uuid4().hex[:6]}@test.local",
            church_role="Visitante",
        )
        db.add(persona)
        db.flush()
        reg = models.EventRegistration(
            id=uuid.uuid4(),
            event_id=event.id,
            persona_id=persona.id,
            registration_status="CONFIRMED",
            qr_token_hash="qr-close-regression",
        )
        db.add(reg)
        db.commit()

        with patch("backend.services.event_registration_service.ensure_event_crm_followup") as mock_followup:
            resp = full["c"].post(
                f"/api/evangelism/events/{event.id}/attendance/close",
                headers=full["h"],
            )
            assert mock_followup.called
        assert resp.status_code == 200, f"{resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        assert data["closed"] is True
        assert data["absent"] == 1

        db.expire_all()
        fresh = db.query(models.EventRegistration).filter(models.EventRegistration.id == reg.id).first()
        assert fresh.registration_status == "ABSENT"

        # Idempotente: segundo cierre no vuelve a marcar ausentes.
        resp2 = full["c"].post(
            f"/api/evangelism/events/{event.id}/attendance/close",
            headers=full["h"],
        )
        assert resp2.status_code == 200
        assert resp2.json()["idempotent"] is True
