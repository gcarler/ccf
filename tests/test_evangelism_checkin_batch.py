"""
Tests TKT-EVANGELISM-OFFLINE-SYNC-01: check-in en lote (``checkin-batch``) para
la sincronización diferida de la cola offline del Scanner QR (Gatekeeper).

Criterio de aceptación: backend idempotente que no duplica registros de
asistencia.
"""

import datetime
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
    from backend import models

    e = models.CrmEvent(
        id=uuid.uuid4(),
        name="Batch Event",
        description="Offline sync",
        event_type="service",
        event_date=datetime.datetime.now(datetime.timezone.utc),
        sede_id=sede_id,
    )
    db.add(e)
    db.flush()
    return e


def _batch_url(event_id):
    return f"/api/evangelism/events/{event_id}/sessions/2026-10-01/checkin-batch"


def _attendance_count(db, event_id):
    from backend import models

    return (
        db.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event_id,
            models.EventAttendance.session_date == datetime.date(2026, 10, 1),
            models.EventAttendance.attended.is_(True),
        )
        .count()
    )


def _make_persona(db, sede_id, name):
    from backend import models

    p = models.Persona(
        id=uuid.uuid4(),
        sede_id=sede_id,
        first_name=name,
        last_name="Gatekeeper",
        email=f"batch-{uuid.uuid4().hex[:6]}@test.local",
        church_role="Visitante",
    )
    db.add(p)
    return p


class TestCheckinBatchGuards:
    def test_batch_requires_auth(self, full):
        event = _make_event(full["db"], full["sede"].id)
        full["db"].commit()
        resp = full["c"].post(
            _batch_url(event.id),
            json={"items": [{"persona_id": str(uuid.uuid4())}]},
        )
        assert resp.status_code == 401

    def test_batch_invalid_date_400(self, full):
        event = _make_event(full["db"], full["sede"].id)
        full["db"].commit()
        resp = full["c"].post(
            f"/api/evangelism/events/{event.id}/sessions/bad-date/checkin-batch",
            headers=full["h"],
            json={"items": [{"persona_id": str(uuid.uuid4())}]},
        )
        assert resp.status_code == 400

    def test_batch_event_not_found_404(self, full):
        resp = full["c"].post(
            f"/api/evangelism/events/{uuid.uuid4()}/sessions/2026-10-01/checkin-batch",
            headers=full["h"],
            json={"items": [{"persona_id": str(uuid.uuid4())}]},
        )
        assert resp.status_code == 404

    def test_batch_empty_items_422(self, full):
        event = _make_event(full["db"], full["sede"].id)
        full["db"].commit()
        resp = full["c"].post(_batch_url(event.id), headers=full["h"], json={"items": []})
        assert resp.status_code == 422


class TestCheckinBatchSync:
    def test_batch_syncs_and_is_idempotent(self, full):
        """Criterio de aceptación: no duplica registros de asistencia."""
        db = full["db"]
        event = _make_event(db, full["sede"].id)
        personas = [_make_persona(db, full["sede"].id, f"Lote{i}") for i in range(3)]
        db.commit()

        items = [{"persona_id": str(p.id)} for p in personas]
        resp = full["c"].post(_batch_url(event.id), headers=full["h"], json={"items": items})
        assert resp.status_code == 200, resp.text[:300]
        data = resp.json()
        assert data["synced"] == 3
        assert data["duplicates"] == 0
        assert data["errors"] == 0
        assert _attendance_count(db, event.id) == 3

        # Reenvío del mismo lote: idempotente, todo duplicate, sin nuevas filas.
        resp2 = full["c"].post(_batch_url(event.id), headers=full["h"], json={"items": items})
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["synced"] == 0
        assert data2["duplicates"] == 3
        assert data2["errors"] == 0
        assert _attendance_count(db, event.id) == 3

    def test_batch_dedupes_repeated_identity_in_payload(self, full):
        """El schema descarta identidades repetidas dentro del mismo lote."""
        db = full["db"]
        event = _make_event(db, full["sede"].id)
        p = _make_persona(db, full["sede"].id, "Duplicada")
        db.commit()

        resp = full["c"].post(
            _batch_url(event.id),
            headers=full["h"],
            json={"items": [{"persona_id": str(p.id)}, {"persona_id": str(p.id)}]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["synced"] == 1
        assert data["duplicates"] == 0
        assert len(data["results"]) == 1
        assert _attendance_count(db, event.id) == 1

    def test_batch_item_error_does_not_abort_batch(self, full):
        """Un QR/persona inválida se reporta como error sin perder el lote."""
        db = full["db"]
        event = _make_event(db, full["sede"].id)
        p = _make_persona(db, full["sede"].id, "Mixta")
        db.commit()

        resp = full["c"].post(
            _batch_url(event.id),
            headers=full["h"],
            json={
                "items": [
                    {"persona_id": str(p.id)},
                    {"persona_id": str(uuid.uuid4())},  # inexistente → error
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["synced"] == 1
        assert data["errors"] == 1
        statuses = {r["status"] for r in data["results"]}
        assert statuses == {"synced", "error"}
        assert _attendance_count(db, event.id) == 1
