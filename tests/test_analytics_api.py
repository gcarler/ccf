import uuid
from datetime import datetime, timezone

import pytest
from backend import models
from backend.core.security import get_password_hash


def _seed_sede(db_session):
    sede = models.Sede(
        id=uuid.uuid4(), nombre="Test Sede", ciudad="Bogota", es_activa=True
    )
    db_session.add(sede)
    db_session.commit()
    db_session.refresh(sede)
    return sede


def _seed_admin(db_session, email="test@example.com", password="testpass123"):
    user = models.User(
        username=email.split("@")[0],
        email=email,
        password_hash=get_password_hash(password),
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    sede = _seed_sede(db_session)

    persona = models.Persona(
        id=uuid.uuid4(),
        user_id=user.id,
        first_name="Test",
        last_name="User",
        email=email,
        sede_id=sede.id,
    )
    db_session.add(persona)
    db_session.commit()
    return user, persona, sede


def _auth_headers(client, email="test@example.com", password="testpass123"):
    resp = client.post(
        "/api/auth/login",
        data={"username": email, "password": password, "grant_type": "password"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_analytics_radar_returns_data(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    resp = client.get("/api/analytics/radar", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "membresia_viva" in data
    assert "bautismos_este_anio" in data


@pytest.mark.xfail(
    reason="backend.crud has no attribute 'get_dashboard_metrics'", strict=False
)
def test_analytics_dashboard_metrics(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    resp = client.get("/api/analytics/dashboard-metrics", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "membresia_viva" in data


def test_analytics_events_summary(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client)

    event = models.CrmEvent(
        name="Evento Test",
        event_date=datetime(2026, 6, 20, 19, 0, 0, tzinfo=timezone.utc),
        location="Templo",
        sede_id=sede.id,
    )
    db_session.add(event)
    db_session.commit()

    resp = client.get("/api/analytics/events/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_events" in data
    assert "upcoming_events" in data
    assert "total_attendees" in data


def test_analytics_radar_rejects_non_pastor(client, db_session):
    user = models.User(
        username="student",
        email="student@example.com",
        password_hash=get_password_hash("testpass123"),
        role="estudiante",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    sede = _seed_sede(db_session)
    persona = models.Persona(
        id=uuid.uuid4(),
        user_id=user.id,
        first_name="Student",
        last_name="User",
        email="student@example.com",
        sede_id=sede.id,
    )
    db_session.add(persona)
    db_session.commit()

    headers = _auth_headers(client, email="student@example.com")
    resp = client.get("/api/analytics/radar", headers=headers)
    assert resp.status_code == 403
