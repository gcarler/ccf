import uuid

from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _seed_sede(db_session):
    sede = models.Sede(
        id=uuid.uuid4(), nombre="Test Sede", ciudad="Bogota", es_activa=True
    )
    db_session.add(sede)
    db_session.commit()
    db_session.refresh(sede)
    return sede


def test_messaging_presence(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    resp = client.get("/api/messaging/presence/room1", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["room"] == "room1"


def test_messaging_send_notification(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
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
    headers = _auth_headers(client, email=admin.email, password="testpass123")

    notif = models.Notification(
        user_id=str(admin.id),
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
    headers = _auth_headers(client, email=admin.email, password="testpass123")

    notif = models.Notification(
        user_id=str(admin.id),
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
    headers = _auth_headers(client, email=admin.email, password="testpass123")

    notif = models.Notification(
        user_id=str(admin.id),
        title="Test Notif All",
        content="Contenido",
    )
    db_session.add(notif)
    db_session.commit()

    resp = client.post("/api/messaging/notifications/mark-all-read", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_messaging_history(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")

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


def test_messaging_send_message(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")

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
