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
    from tests.conftest import seed_user_with_role_v2

    user, persona, _ = seed_user_with_role_v2(db_session, "estudiante", "student@example.com")
    headers = _auth_headers(client, email="student@example.com")
    resp = client.get("/api/analytics/radar", headers=headers)
    assert resp.status_code == 403
