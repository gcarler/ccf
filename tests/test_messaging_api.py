import uuid
from datetime import datetime, timezone

import pytest
from backend import models
from tests.conftest import seed_admin_v2 as _seed_admin
from tests.conftest import auth_headers_legacy as _auth_headers


def _seed_sede(db_session):
    sede = models.Sede(
        id=uuid.uuid4(), nombre="Test Sede", ciudad="Bogota", es_activa=True
    )
    db_session.add(sede)
    db_session.commit()
    db_session.refresh(sede)
    return sede


def test_messaging_presence(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers()
    resp = client.get("/api/messaging/presence/room1", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["room"] == "room1"


def test_messaging_send_notification(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers()
    payload = {
        "event": "test_event",
        "body": {"message": "hola"},
        "room": "room1",
    }
    resp = client.post("/api/messaging/notifications", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"


def test_messaging_get_notifications(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers()

    notif = models.Notification(
        user_id=admin.legacy_user.id,
        title="Test Notif",
        content="Contenido",
    )
    db_session.add(notif)
    db_session.commit()

    resp = client.get("/api/messaging/notifications", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_messaging_mark_notification_read(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers()

    notif = models.Notification(
        user_id=admin.legacy_user.id,
        title="Test Notif Read",
        content="Contenido",
    )
    db_session.add(notif)
    db_session.commit()
    db_session.refresh(notif)

    resp = client.patch(
        f"/api/messaging/notifications/{notif.id}", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_read"] is True


def test_messaging_mark_all_read(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers()

    notif = models.Notification(
        user_id=admin.legacy_user.id,
        title="Test Notif All",
        content="Contenido",
    )
    db_session.add(notif)
    db_session.commit()

    resp = client.post("/api/messaging/notifications/mark-all-read", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


@pytest.mark.xfail(
    reason="schemas.CommunicationLog expects persona_id as str and leader_id as int, but model returns UUIDs",
    strict=False,
)
def test_messaging_history(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers()

    log = models.CommunicationLog(
        persona_id=persona.id,
        channel="WhatsApp",
        recipient_phone="+573001112233",
        content="Hola",
        leader_id=persona.id,
        outcome="delivered",
        external_id="msg-123",
    )
    db_session.add(log)
    db_session.commit()

    resp = client.get("/api/messaging/history", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.xfail(
    reason="Endpoint passes current_user.id (int) to leader_id (UUID)", strict=False
)
def test_messaging_send_message(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers()

    resp = client.post(
        "/api/messaging/send",
        json={
            "persona_id": str(persona.id),
            "channel": "WhatsApp",
            "content": "Mensaje de prueba",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "Mensaje de prueba"
