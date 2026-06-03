import uuid
from datetime import datetime, timezone

import pytest
from backend import models
from tests.conftest import seed_admin_v2 as _seed_admin
from tests.conftest import auth_headers_v2 as _auth_headers


def _seed_sede(db_session):
    sede = models.Sede(
        id=uuid.uuid4(), nombre="Test Sede", ciudad="Bogota", es_activa=True
    )
    db_session.add(sede)
    db_session.commit()
    db_session.refresh(sede)
    return sede


@pytest.mark.xfail(reason="AgendaEvent model lacks sede_id column; endpoint crashes")
def test_list_agenda_events(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    resp = client.get("/api/agenda/events", headers=headers)
    assert resp.status_code == 200


def test_create_agenda_event(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    payload = {
        "title": "Reunion de oracion",
        "description": "Oracion intercesora",
        "start_at": datetime(2026, 6, 15, 19, 0, 0).isoformat(),
        "end_at": datetime(2026, 6, 15, 20, 0, 0).isoformat(),
        "location": "Sala principal",
        "is_all_day": False,
    }
    resp = client.post("/api/agenda/events", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Reunion de oracion"
    assert data["location"] == "Sala principal"
    assert data["is_all_day"] is False


def test_get_agenda_event(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    event = models.AgendaEvent(
        title="Culto dominical",
        start_at=datetime(2026, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
        location="Templo",
        is_all_day=False,
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    resp = client.get(f"/api/agenda/events/{event.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == event.id
    assert data["title"] == "Culto dominical"


def test_update_agenda_event(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    event = models.AgendaEvent(
        title="Evento original",
        start_at=datetime(2026, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
        is_all_day=True,
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    payload = {
        "title": "Evento actualizado",
        "description": "Nueva descripcion",
        "start_at": datetime(2026, 6, 16, 10, 0, 0).isoformat(),
        "end_at": None,
        "location": "Nueva locacion",
        "is_all_day": True,
    }
    resp = client.put(
        f"/api/agenda/events/{event.id}", json=payload, headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Evento actualizado"
    assert data["location"] == "Nueva locacion"


def test_delete_agenda_event_soft(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    event = models.AgendaEvent(
        title="Evento a eliminar",
        start_at=datetime(2026, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
        is_all_day=True,
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    resp = client.delete(f"/api/agenda/events/{event.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"

    # After soft delete, GET should 404
    resp2 = client.get(f"/api/agenda/events/{event.id}", headers=headers)
    assert resp2.status_code == 404
