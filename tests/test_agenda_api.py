from datetime import datetime, timedelta, timezone

from tests.conftest import auth_headers, seed_admin


def _event_payload(title="Reunion de oracion"):
    starts_at = datetime(2026, 6, 15, 19, 0, tzinfo=timezone.utc)
    return {
        "title": title,
        "description": "Oracion intercesora",
        "start_at": starts_at.isoformat(),
        "end_at": (starts_at + timedelta(hours=1)).isoformat(),
        "location": "Sala principal",
        "is_all_day": False,
    }


def _create_event(client, headers, title="Reunion de oracion"):
    response = client.post("/api/agenda/events", json=_event_payload(title), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_agenda_event_lifecycle(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)

    event = _create_event(client, headers)
    assert event["title"] == "Reunion de oracion"

    listed = client.get("/api/agenda/events", headers=headers)
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()] == [event["id"]]

    detail = client.get(f"/api/agenda/events/{event['id']}", headers=headers)
    assert detail.status_code == 200

    updated_payload = _event_payload("Evento actualizado")
    updated_payload["location"] = "Nueva locacion"
    updated = client.put(
        f"/api/agenda/events/{event['id']}",
        json=updated_payload,
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "Evento actualizado"

    archived = client.delete(f"/api/agenda/events/{event['id']}", headers=headers)
    assert archived.status_code == 204
    assert client.get(f"/api/agenda/events/{event['id']}", headers=headers).status_code == 404


def test_agenda_resource_participant_and_reservation_flow(client, db_session):
    admin, persona, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    event = _create_event(client, headers, "Evento con recursos")

    resource = client.post(
        "/api/agenda/resources",
        headers=headers,
        json={
            "name": "Auditorio",
            "resource_type": "ROOM",
            "capacity": 100,
            "is_active": True,
        },
    )
    assert resource.status_code == 201, resource.text

    participant = client.post(
        "/api/agenda/participants",
        headers=headers,
        json={"event_id": event["id"], "persona_id": str(persona.id)},
    )
    assert participant.status_code == 201, participant.text

    starts_at = datetime(2026, 6, 15, 19, 0, tzinfo=timezone.utc)
    reservation_payload = {
        "event_id": event["id"],
        "resource_id": resource.json()["id"],
        "starts_at": starts_at.isoformat(),
        "ends_at": (starts_at + timedelta(hours=1)).isoformat(),
    }
    reservation = client.post(
        "/api/agenda/reservations", headers=headers, json=reservation_payload
    )
    assert reservation.status_code == 201, reservation.text

    conflict = client.post(
        "/api/agenda/reservations", headers=headers, json=reservation_payload
    )
    assert conflict.status_code == 409
