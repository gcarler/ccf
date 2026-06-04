from datetime import datetime

from fastapi.testclient import TestClient

from backend import models
from tests.conftest import seed_admin_v2, auth_headers_legacy


def seed_user(db_session, email="member@example.com", password="secret123"):
    user_obj, _, _ = seed_admin_v2(db_session, email, password)
    return user_obj.legacy_user


def auth_headers(client, email="member@example.com", password="secret123"):
    return auth_headers_legacy(email)


def test_ai_generate_requires_prompt(client: TestClient, db_session):
    seed_user(db_session)
    response = client.post(
        "/api/system/ai/generate",
        json={},
        headers=auth_headers(client),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Falta el prompt"


def test_agenda_events_feed_into_system_calendar(client: TestClient, db_session):
    seed_user(db_session)
    headers = auth_headers(client)

    create_response = client.post(
        "/api/agenda/events",
        json={
            "title": "Reunion de liderazgo",
            "description": "Planeacion semanal",
            "start_at": "2026-05-04T19:00:00",
            "end_at": "2026-05-04T20:30:00",
            "location": "Salon principal",
            "is_all_day": False,
        },
        headers=headers,
    )
    assert create_response.status_code == 200
    created_event = create_response.json()
    assert created_event["title"] == "Reunion de liderazgo"

    calendar_response = client.get("/api/system/calendar", headers=headers)
    assert calendar_response.status_code == 200
    payload = calendar_response.json()
    agenda_entry = next(
        item for item in payload if item["id"] == f"agenda-{created_event['id']}"
    )
    assert agenda_entry["title"] == "Reunion de liderazgo"
    assert agenda_entry["type"] == "agenda_event"
    assert agenda_entry["location"] == "Salon principal"
    assert agenda_entry["href"] == f"/agenda/events/{created_event['id']}"


def test_agenda_event_update_and_delete(client: TestClient, db_session):
    seed_user(db_session)
    headers = auth_headers(client)

    create_response = client.post(
        "/api/agenda/events",
        json={
            "title": "Reunion base",
            "description": "Inicial",
            "start_at": "2026-05-10T18:00:00",
            "end_at": "2026-05-10T19:00:00",
            "location": "Sala 1",
            "is_all_day": False,
        },
        headers=headers,
    )
    event_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/agenda/events/{event_id}",
        json={
            "title": "Reunion actualizada",
            "description": "Reprogramada",
            "start_at": "2026-05-11T18:00:00",
            "end_at": "2026-05-11T19:30:00",
            "location": "Sala 2",
            "is_all_day": False,
        },
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Reunion actualizada"
    assert update_response.json()["location"] == "Sala 2"

    delete_response = client.delete(f"/api/agenda/events/{event_id}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"

    fetch_response = client.get(f"/api/agenda/events/{event_id}", headers=headers)
    assert fetch_response.status_code == 404


def test_system_calendar_includes_evangelism_event_link(client: TestClient, db_session):
    seed_user(db_session)
    headers = auth_headers(client)

    evangelism_event = models.CrmEvent(
        name="Noche de alcance",
        description="Convocatoria abierta",
        event_date=datetime(2026, 5, 12, 19, 0, 0),
        location="Auditorio",
    )
    db_session.add(evangelism_event)
    db_session.commit()
    db_session.refresh(evangelism_event)

    calendar_response = client.get("/api/system/calendar", headers=headers)
    assert calendar_response.status_code == 200
    payload = calendar_response.json()
    entry = next(
        item for item in payload if item["id"] == f"evangelism-{evangelism_event.id}"
    )
    assert entry["type"] == "evangelism_event"
    assert entry["href"] == f"/evangelism/events/{evangelism_event.id}"
