"""Cross-sede isolation tests for additional CRM entities.

Covers VolunteerShift, Donation and the canonical IDOR scenario for personas.
"""

from datetime import datetime, timezone

from backend import models
from tests.conftest import auth_headers, seed_admin


def _seed_two_sedes(db_session):
    admin_a, persona_a, sede_a = seed_admin(db_session, email="entityA@example.com", password="testpass123")
    admin_b, persona_b, sede_b = seed_admin(db_session, email="entityB@example.com", password="testpass123")
    return (admin_a, persona_a, sede_a), (admin_b, persona_b, sede_b)


def _persona_in(db, sede_id, email_suffix):
    import uuid as _uuid

    p = models.Persona(
        id=_uuid.uuid4(),
        first_name=f"User-{email_suffix}",
        last_name="Test",
        email=f"{email_suffix}@example.com",
        sede_id=sede_id,
        estado_vital="ACTIVO",
    )
    db.add(p)
    db.flush()
    return p


# ── IDOR: direct persona access by ID across sedes ────────────────────────


def test_idor_persona_cross_sede_returns_404(client, db_session):
    """S-04: accessing a persona by ID from a different sede yields 404."""
    (admin_a, _, sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_b = _persona_in(db_session, sede_b.id, "idor-b")

    headers_a = auth_headers(client, email="entityA@example.com")
    resp = client.get(f"/api/crm/personas/{persona_b.id}", headers=headers_a)
    assert resp.status_code == 404, f"IDOR leak: cross-sede persona access returned {resp.status_code}"
    assert "idor-b" not in resp.text, "Persona name leaked in cross-sede response"


# ── VolunteerShift isolation ───────────────────────────────────────────


def test_list_volunteers_blocks_cross_sede(client, db_session):
    (admin_a, _, sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_b = _persona_in(db_session, sede_b.id, "volunteer-b")
    shift_b = models.VolunteerShift(
        persona_id=persona_b.id,
        role_name="Musician",
        team_name="Worship",
        shift_start=datetime.now(timezone.utc),
        shift_end=datetime.now(timezone.utc),
        status="confirmed",
    )
    db_session.add(shift_b)
    db_session.commit()

    headers_a = auth_headers(client, email="entityA@example.com")
    resp = client.get("/api/crm/volunteers", headers=headers_a)
    assert resp.status_code == 200
    body = resp.json()
    items = body.get("items", [])
    assert all(str(item.get("persona_id")) != str(persona_b.id) for item in items), (
        "Cross-sede volunteer persona appeared in list"
    )


def test_get_volunteer_detail_blocks_cross_sede(client, db_session):
    (admin_a, _, sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_b = _persona_in(db_session, sede_b.id, "volunteer-detail-b")
    headers_a = auth_headers(client, email="entityA@example.com")
    resp = client.get(f"/api/crm/volunteers/{persona_b.id}", headers=headers_a)
    assert resp.status_code == 404, f"Cross-sede volunteer detail leaked: {resp.status_code}"


# ── Donation isolation (CRM persona donations) ─────────────────────────


def test_persona_donations_idor_cross_sede(client, db_session):
    """Cross-sede persona donations endpoint must not leak data."""
    (admin_a, _, sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_b = _persona_in(db_session, sede_b.id, "donation-b")
    donation = models.Donation(
        persona_id=persona_b.id,
        amount=5000.0,
        currency="COP",
        donation_type="Diezmo",
        status="completed",
        payment_method="Transferencia",
        sede_id=sede_b.id,
    )
    db_session.add(donation)
    db_session.commit()

    headers_a = auth_headers(client, email="entityA@example.com")
    resp = client.get(f"/api/crm/personas/{persona_b.id}/donations", headers=headers_a)
    assert resp.status_code == 404, f"Cross-sede donations leaked: {resp.status_code}"
    assert "5000" not in resp.text, "Donation amount leaked cross-sede"
