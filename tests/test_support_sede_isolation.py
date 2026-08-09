"""Adversarial multi-tenant tests for Support tickets."""

from __future__ import annotations

import uuid

from backend import models
from backend.core.security import get_password_hash
from backend.models_auth import RolPlataforma, Usuario
from tests.conftest import auth_headers, seed_admin


def _ticket(db_session, *, persona_id, sede_id, subject):
    row = models.SupportTicket(
        id=uuid.uuid4(),
        user_id=persona_id,
        sede_id=sede_id,
        subject=subject,
        description="Support test",
    )
    db_session.add(row)
    db_session.commit()
    return row


def test_support_admin_list_is_scoped_to_actor_sede(client, db_session):
    admin_a, persona_a, sede_a = seed_admin(db_session, email="support-scope-a@example.com")
    admin_b, persona_b, sede_b = seed_admin(db_session, email="support-scope-b@example.com")
    ticket_a = _ticket(db_session, persona_id=persona_a.id, sede_id=sede_a.id, subject="Private A")
    ticket_b = _ticket(db_session, persona_id=persona_b.id, sede_id=sede_b.id, subject="Private B")
    ticket_legacy = _ticket(db_session, persona_id=persona_a.id, sede_id=None, subject="Legacy global")

    response = client.get(
        "/api/support",
        headers=auth_headers(client, email=admin_b.email),
    )

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert str(ticket_b.id) in ids
    assert str(ticket_a.id) not in ids
    assert str(ticket_legacy.id) not in ids


def test_support_admin_cannot_update_cross_sede_ticket(client, db_session):
    admin_a, persona_a, sede_a = seed_admin(db_session, email="support-update-a@example.com")
    admin_b, persona_b, sede_b = seed_admin(db_session, email="support-update-b@example.com")
    ticket_a = _ticket(db_session, persona_id=persona_a.id, sede_id=sede_a.id, subject="Immutable A")
    legacy_ticket = _ticket(db_session, persona_id=persona_a.id, sede_id=None, subject="Legacy immutable")
    _ticket(db_session, persona_id=persona_b.id, sede_id=sede_b.id, subject="Mutable B")

    response = client.patch(
        f"/api/support/{ticket_a.id}",
        json={"status": "resolved"},
        headers=auth_headers(client, email=admin_b.email),
    )

    assert response.status_code == 404
    db_session.refresh(ticket_a)
    assert ticket_a.status == "open"

    legacy_response = client.patch(
        f"/api/support/{legacy_ticket.id}",
        json={"status": "resolved"},
        headers=auth_headers(client, email=admin_b.email),
    )

    assert legacy_response.status_code == 404
    db_session.refresh(legacy_ticket)
    assert legacy_ticket.status == "open"


def test_support_platform_permission_can_manage_legacy_global_ticket(client, db_session):
    role = RolPlataforma(
        id=uuid.uuid4(),
        nombre="Support Platform Operator",
        permisos={"system:config": "allow"},
    )
    db_session.add(role)
    persona = models.Persona(
        id=uuid.uuid4(),
        first_name="Platform",
        last_name="Operator",
        email="support-platform@example.com",
        sede_id=None,
    )
    db_session.add(persona)
    db_session.flush()
    # Usuario.sede_id is historically NOT NULL; the unscoped legacy path is
    # determined from Persona.sede_id, which is the Support tenant anchor.
    sede = models.Sede(id=uuid.uuid4(), nombre="Legacy Auth Sede", ciudad="Bogota", es_activa=True)
    db_session.add(sede)
    user = Usuario(
        id=persona.id,
        sede_id=sede.id,
        username="support-platform",
        email=persona.email,
        password_hash=get_password_hash("testpass123"),
        rol_plataforma_id=role.id,
        is_active=True,
        is_email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    ticket = _ticket(db_session, persona_id=persona.id, sede_id=None, subject="Global legacy")
    other_admin, other_persona, other_sede = seed_admin(db_session, email="support-platform-other@example.com")
    other_ticket = _ticket(
        db_session,
        persona_id=other_persona.id,
        sede_id=other_sede.id,
        subject="Global seated ticket",
    )

    list_response = client.get("/api/support", headers=auth_headers(client, email=user.email))
    assert list_response.status_code == 200
    listed_ids = {item["id"] for item in list_response.json()}
    assert {str(ticket.id), str(other_ticket.id)} <= listed_ids

    response = client.patch(
        f"/api/support/{ticket.id}",
        json={"status": "resolved"},
        headers=auth_headers(client, email=user.email),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"


def test_support_unscoped_non_admin_is_rejected(client, db_session):
    role = RolPlataforma(id=uuid.uuid4(), nombre="Support Member", permisos={"support:read": "allow"})
    db_session.add(role)
    persona = models.Persona(
        id=uuid.uuid4(),
        first_name="Unscoped",
        last_name="Member",
        email="support-unscoped@example.com",
        sede_id=None,
    )
    db_session.add(persona)
    db_session.flush()
    sede = models.Sede(id=uuid.uuid4(), nombre="Legacy Auth Sede 2", ciudad="Bogota", es_activa=True)
    db_session.add(sede)
    user = Usuario(
        id=persona.id,
        sede_id=sede.id,
        username="support-unscoped",
        email=persona.email,
        password_hash=get_password_hash("testpass123"),
        rol_plataforma_id=role.id,
        is_active=True,
        is_email_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    response = client.get("/api/support", headers=auth_headers(client, email=user.email))
    assert response.status_code == 403


def test_support_create_assigns_actor_sede(client, db_session):
    admin, _persona, sede = seed_admin(db_session, email="support-create-scope@example.com")

    response = client.post(
        "/api/support",
        json={"subject": "Scoped create", "description": "Created in actor tenant"},
        headers=auth_headers(client, email=admin.email),
    )

    assert response.status_code == 200
    row = db_session.query(models.SupportTicket).filter(models.SupportTicket.id == response.json()["id"]).one()
    assert str(row.sede_id) == str(sede.id)
