from datetime import datetime, timedelta

from backend import models


def test_public_registration_creates_member_and_attendance(client, db_session):
    event = models.CrmEvent(
        name="Evento Publico",
        description="Registro desde QR",
        event_date=datetime.now() + timedelta(days=1),
        location="Auditorio principal",
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    response = client.post(
        "/api/public/register",
        json={
            "event_id": str(event.id),
            "first_name": "Ana",
            "last_name": "Perez",
            "email": "ana@example.com",
            "phone": "+57 300 000 0000",
            "accept_contact": True,
        },
    )

    assert response.status_code == 200

    member = (
        db_session.query(models.Member)
        .filter(models.Member.email == "ana@example.com")
        .first()
    )
    assert member is not None
    assert member.first_name == "Ana"
    assert member.last_name == "Perez"
    assert member.spiritual_status == "Nuevo"
    assert member.church_role == "Visitante"

    attendance = (
        db_session.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event.id,
            models.EventAttendance.member_id == member.id,
        )
        .first()
    )
    assert attendance is not None
    assert attendance.attended is True
    assert attendance.session_date == event.event_date.date()


def test_public_registration_reuses_existing_member(client, db_session):
    event = models.CrmEvent(
        name="Evento Recurrente",
        description="Registro repetido",
        event_date=datetime.now() + timedelta(days=1),
        location="Auditorio principal",
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    payload = {
        "event_id": str(event.id),
        "first_name": "Laura",
        "last_name": "Gomez",
        "email": "laura@example.com",
        "phone": "+57 301 111 1111",
        "accept_contact": True,
    }

    first = client.post("/api/public/register", json=payload)
    second = client.post("/api/public/register", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200

    members = (
        db_session.query(models.Member)
        .filter(models.Member.email == "laura@example.com")
        .all()
    )
    assert len(members) == 1

    attendances = (
        db_session.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event.id,
            models.EventAttendance.member_id == members[0].id,
        )
        .all()
    )
    assert len(attendances) == 1
    assert attendances[0].session_date == event.event_date.date()


def test_public_registration_missing_event_returns_404(client, db_session):
    response = client.post(
        "/api/public/register",
        json={
            "event_id": "00000000-0000-0000-0000-000000009999",
            "first_name": "Nadia",
            "last_name": "Lopez",
            "email": "nadia@example.com",
            "phone": "+57 302 222 2222",
            "accept_contact": True,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Evento no encontrado."
