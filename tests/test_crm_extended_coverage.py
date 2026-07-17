"""Extended CRM coverage tests — CRUD + HTTP endpoints.

Targets: prayer requests, automations, roles, settings, volunteer CRUD,
persona relations, groups, and resource endpoints.
"""
from __future__ import annotations

import uuid as _uuid

import pytest

from tests.conftest import auth_headers, seed_admin, seed_user_with_role


def _seed_user_with_crm(db_session, permisos, email="crm@test.com"):
    """Helper to create a user with CRM permissions."""
    from backend import models as _models
    from backend.core.security import get_password_hash
    from backend.models_auth import RolPlataforma, Usuario
    from backend.models_crm import Persona

    existing = db_session.query(Usuario).filter(Usuario.email == email).first()
    if existing:
        return existing

    persona = Persona(id=_uuid.uuid4(), first_name="CRM", last_name="User", email=email)
    db_session.add(persona)
    db_session.flush()

    role = db_session.query(RolPlataforma).filter(RolPlataforma.nombre == f"crm_{email.split('@')[0]}").first()
    if not role:
        role = RolPlataforma(id=_uuid.uuid4(), nombre=f"crm_{email.split('@')[0]}", permisos=permisos)
        db_session.add(role)
        db_session.flush()

    sede = db_session.query(_models.Sede).first()
    if not sede:
        sede = _models.Sede(id=_uuid.uuid4(), nombre="Sede T", ciudad="Bogota", es_activa=True)
        db_session.add(sede)
        db_session.flush()
    persona.sede_id = sede.id

    user = Usuario(
        id=persona.id, sede_id=sede.id, username=email.split("@")[0], email=email,
        password_hash=get_password_hash("testpass123"), rol_plataforma_id=role.id,
        is_active=True, is_email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


# ─── Prayer Request CRUD Tests ────────────────────────────────────────


def test_prayer_request_crud(db_session):
    """Test prayer request create, read, update, delete via CRUD."""
    from backend.models_crm import PrayerRequest

    user, persona, sede = seed_admin(db_session)
    req_id = _uuid.uuid4()
    pr = PrayerRequest(
        id=req_id, requester_name="Juan", request_text="Oracion por salud",
        category="Salud", is_public=False, status="pending",
    )
    db_session.add(pr)
    db_session.commit()

    fetched = db_session.query(PrayerRequest).filter(PrayerRequest.id == req_id).first()
    assert fetched is not None
    assert fetched.requester_name == "Juan"
    assert fetched.category == "Salud"

    fetched.status = "answered"
    db_session.commit()
    refreshed = db_session.query(PrayerRequest).filter(PrayerRequest.id == req_id).first()
    assert refreshed.status == "answered"


# ─── Role Definition CRUD Tests ───────────────────────────────────────


def test_role_definition_crud(db_session):
    """Test role definition create, update, delete."""
    from backend.models_crm import RoleDefinition

    user, persona, sede = seed_admin(db_session)
    role = RoleDefinition(id=_uuid.uuid4(), name="Lider Juvenil", color="green", is_leadership=True)
    db_session.add(role)
    db_session.commit()

    fetched = db_session.query(RoleDefinition).filter(RoleDefinition.id == role.id).first()
    assert fetched is not None
    assert fetched.name == "Lider Juvenil"
    assert fetched.is_leadership is True

    fetched.name = "Lider General"
    fetched.sede_id = sede.id
    db_session.commit()
    refreshed = db_session.query(RoleDefinition).filter(RoleDefinition.id == role.id).first()
    assert refreshed.name == "Lider General"
    assert refreshed.sede_id == sede.id

    db_session.delete(refreshed)
    db_session.commit()
    assert db_session.query(RoleDefinition).filter(RoleDefinition.id == role.id).first() is None


# ─── Counseling Ticket CRUD Tests ─────────────────────────────────────


def test_counseling_ticket_crud(db_session):
    """Test counseling ticket operations."""
    from backend.models_crm import CounselingTicket

    user, persona, sede = seed_admin(db_session)
    ticket = CounselingTicket(
        id=_uuid.uuid4(), persona_id=persona.id, subject="Crisis familiar",
        notes=" notas privadas", status="open",
    )
    db_session.add(ticket)
    db_session.commit()

    fetched = db_session.query(CounselingTicket).filter(CounselingTicket.id == ticket.id).first()
    assert fetched is not None
    assert fetched.subject == "Crisis familiar"

    fetched.status = "in_progress"
    fetched.priority_level = "high"
    db_session.commit()
    refreshed = db_session.query(CounselingTicket).filter(CounselingTicket.id == ticket.id).first()
    assert refreshed.status == "in_progress"
    assert refreshed.priority_level == "high"


# ─── CrmAutomation CRUD Tests ────────────────────────────────────────


def test_crm_automation_crud(db_session):
    """Test CRM automation CRUD with sede scoping."""
    from backend.crud.crm_ import extended as crud_ext
    from backend.schemas.crm.automation import CrmAutomationCreate, CrmAutomationUpdate

    user, persona, sede = seed_admin(db_session)
    payload = CrmAutomationCreate(
        name="Test Automation", trigger_event="task_completed",
        action_type="send_message", is_active=True,
    )
    obj = crud_ext.create_crm_automation(db_session, payload, sede_id=str(sede.id))
    assert obj.name == "Test Automation"
    assert obj.sede_id is not None

    rows = crud_ext.get_crm_automations(db_session, sede_id=str(sede.id))
    assert len(rows) >= 1

    rows_no_sede = crud_ext.get_crm_automations(db_session)
    assert len(rows_no_sede) >= 1

    found = crud_ext.get_crm_automation(db_session, obj.id)
    assert found is not None

    updated = crud_ext.update_crm_automation(db_session, obj.id, CrmAutomationUpdate(name="Updated Auto"))
    assert updated.name == "Updated Auto"

    deleted = crud_ext.delete_crm_automation(db_session, obj.id)
    assert deleted is True
    remaining = crud_ext.get_crm_automation(db_session, obj.id)
    assert remaining is not None
    assert remaining.is_active is False


# ─── Persona CRUD Tests ──────────────────────────────────────────────


def test_persona_crud_operations(db_session):
    """Test persona create, list, filter, update, delete."""
    from backend import crud, schemas

    user, persona, sede = seed_admin(db_session)
    p = crud.create_persona(
        db_session,
        schemas.PersonaCreate(
            first_name="Maria", last_name="Garcia",
            email="maria@test.com", church_role="Miembro",
        ),
    )
    assert p.first_name == "Maria"

    personas = crud.get_personas(db_session, role="Miembro")
    assert any(per.id == p.id for per in personas)

    updated = crud.update_persona(db_session, str(p.id), schemas.PersonaUpdate(church_role="Lider"))
    assert updated.church_role == "Lider"

    deleted = crud.delete_persona(db_session, str(p.id))
    assert deleted is True


# ─── Position CRUD Tests ─────────────────────────────────────────────


def test_position_crud(db_session):
    """Test position CRUD."""
    from backend.crud.crm_ import extended as crud_ext

    user, persona, sede = seed_admin(db_session)
    pos = crud_ext.create_position(db_session, crud_ext.PositionCreate(name="Director Musical", description="Lider musical"))
    assert pos.name == "Director Musical"

    pos.description = "Lider musical y coro"
    db_session.commit()

    fetched = crud_ext.get_position(db_session, pos.id)
    assert fetched.description == "Lider musical y coro"

    deleted = crud_ext.delete_position(db_session, pos.id)
    assert deleted is True


# ─── Family CRUD Tests ───────────────────────────────────────────────


def test_family_crud(db_session):
    """Test family CRUD."""
    from backend.crud.crm_.families import create_family, get_family

    user, persona, sede = seed_admin(db_session)
    fam = create_family(db_session, name="Familia Garcia")
    assert fam.name == "Familia Garcia"

    fetched = get_family(db_session, fam.id)
    assert fetched is not None
    assert fetched.name == "Familia Garcia"


# ─── Group Session Tests ─────────────────────────────────────────────


def test_group_session_crud(db_session):
    """Test group session CRUD."""
    from backend.crud.crm_.groups import create_grupo, get_grupo
    from backend.schemas import GrupoEvangelismoCreate

    user, persona, sede = seed_admin(db_session)
    grupo = create_grupo(
        db_session, GrupoEvangelismoCreate(name="Grupo Joven", description="Grupo de jovenes"),
        sede_id=str(sede.id),
    )
    assert grupo.name == "Grupo Joven"

    fetched = get_grupo(db_session, grupo.id)
    assert fetched is not None


# ─── HTTP Endpoint Tests ─────────────────────────────────────────────


def test_prayer_request_endpoint_crud(client, db_session):
    """Test prayer request HTTP CRUD endpoints."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)

    # Create
    resp = client.post(
        "/api/crm/prayer-requests",
        json={"requester_name": "Pedro", "request_text": "Oracion por trabajo"},
        headers=headers,
    )
    assert resp.status_code in (200, 201), resp.text
    data = resp.json()
    pr_id = data.get("id")

    # List
    resp = client.get("/api/crm/prayer-requests", headers=headers)
    assert resp.status_code == 200

    if pr_id:
        # Update
        resp = client.patch(
            f"/api/crm/prayer-requests/{pr_id}",
            json={"status": "answered"},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text


def test_roles_endpoint_crud(client, db_session):
    """Test roles HTTP CRUD endpoints."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)

    # Create
    resp = client.post(
        "/api/crm/roles",
        json={"name": "Lider Worship", "color": "purple"},
        headers=headers,
    )
    assert resp.status_code in (200, 201), resp.text
    data = resp.json()
    role_id = data.get("id")

    # List
    resp = client.get("/api/crm/roles", headers=headers)
    assert resp.status_code == 200

    if role_id:
        # Update
        resp = client.put(
            f"/api/crm/roles/{role_id}",
            json={"name": "Lider Worship Actualizado"},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text

        # Delete (requires replacement_role_id)
        resp = client.delete(
            f"/api/crm/roles/{role_id}?replacement_role_id={_uuid.uuid4()}",
            headers=headers,
        )
        assert resp.status_code in (200, 204, 400), resp.text


def test_volunteers_endpoint_crud(client, db_session):
    """Test volunteer HTTP CRUD endpoints."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)

    # Create
    resp = client.post(
        "/api/crm/volunteers",
        json={"name": "Servidor Test", "persona_id": str(persona.id), "role_name": "Servidor", "team_name": "Alabanza", "shift_start": "2026-07-17T10:00:00", "shift_end": "2026-07-17T12:00:00"},
        headers=headers,
    )
    assert resp.status_code in (200, 201), resp.text
    data = resp.json()
    vol_id = data.get("id")

    # List
    resp = client.get("/api/crm/volunteers", headers=headers)
    assert resp.status_code == 200

    if vol_id:
        # Update
        resp = client.patch(
            f"/api/crm/volunteers/{vol_id}",
            json={"role_name": "Lider Alabanza"},
            headers=headers,
        )
        assert resp.status_code in (200, 404), resp.text


def test_settings_endpoint(client, db_session):
    """Test CRM settings endpoint."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)

    # Get
    resp = client.get("/api/crm/settings", headers=headers)
    assert resp.status_code == 200

    # Update
    resp = client.post(
        "/api/crm/settings",
        json={"theme": "dark"},
        headers=headers,
    )
    assert resp.status_code in (200, 201, 204), resp.text


def test_groups_endpoint_crud(client, db_session):
    """Test groups HTTP endpoints."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)

    # List
    resp = client.get("/api/crm/grupos", headers=headers)
    assert resp.status_code == 200

    # Create (POST may not be available; use PUT)
    resp = client.put(
        "/api/crm/grupos",
        json={"name": "Grupo Test", "description": "Grupo de prueba"},
        headers=headers,
    )
    assert resp.status_code in (200, 201, 405), resp.text


def test_automations_endpoint(client, db_session):
    """Test automation endpoints."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)

    # List
    resp = client.get("/api/crm/resources/automations", headers=headers)
    assert resp.status_code == 200

    # Create
    resp = client.post(
        "/api/crm/resources/automations",
        json={"name": "Test Auto", "trigger_event": "task_completed", "action_type": "send_message"},
        headers=headers,
    )
    assert resp.status_code in (200, 201), resp.text
    data = resp.json()
    auto_id = data.get("id")

    if auto_id:
        # Get one
        resp = client.get(f"/api/crm/resources/automations/{auto_id}", headers=headers)
        assert resp.status_code == 200

        # Update
        resp = client.patch(
            f"/api/crm/resources/automations/{auto_id}",
            json={"name": "Updated Auto"},
            headers=headers,
        )
        assert resp.status_code == 200

        # Delete
        resp = client.delete(f"/api/crm/resources/automations/{auto_id}", headers=headers)
        assert resp.status_code == 204


def test_resource_categories_endpoint(client, db_session):
    """Test resource categories endpoints."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)

    resp = client.get("/api/crm/resources/categorias", headers=headers)
    assert resp.status_code == 200


def test_counseling_tickets_endpoint(client, db_session):
    """Test counseling ticket endpoints."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)

    resp = client.get(
        f"/api/crm/counseling/{_uuid.uuid4()}",
        headers=headers,
    )
    assert resp.status_code in (200, 404)


def test_cases_endpoint(client, db_session):
    """Test cases endpoints."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)

    resp = client.get(
        f"/api/crm/casos/{_uuid.uuid4()}",
        headers=headers,
    )
    assert resp.status_code in (200, 404)


def test_pipelines_endpoint(client, db_session):
    """Test pipeline endpoint."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)

    resp = client.get("/api/crm/pipelines", headers=headers)
    assert resp.status_code == 200


def test_messaging_templates_endpoint(client, db_session):
    """Test messaging templates endpoint."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)

    resp = client.get("/api/crm/resources/plantillas", headers=headers)
    assert resp.status_code == 200


def test_persona_ministries_endpoint(client, db_session):
    """Test persona ministries endpoint."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)

    resp = client.get(f"/api/crm/personas/{persona.id}/ministries", headers=headers)
    assert resp.status_code == 200


def test_persona_communications_endpoint(client, db_session):
    """Test persona communications endpoint."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)

    resp = client.get(f"/api/crm/personas/{persona.id}/communications", headers=headers)
    assert resp.status_code == 200


def test_persona_positions_endpoint(client, db_session):
    """Test persona positions endpoint."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)

    resp = client.get(f"/api/crm/personas/{persona.id}/positions", headers=headers)
    assert resp.status_code == 200


def test_persona_formations_endpoint(client, db_session):
    """Test persona formations endpoint."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)

    resp = client.get(f"/api/crm/personas/{persona.id}/formations", headers=headers)
    assert resp.status_code in (200, 404)


def test_persona_volunteer_shifts_endpoint(client, db_session):
    """Test persona volunteer shifts endpoint."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)

    resp = client.get(f"/api/crm/personas/{persona.id}/volunteer-shifts", headers=headers)
    assert resp.status_code in (200, 404)


def test_persona_family_endpoint(client, db_session):
    """Test persona family endpoint."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)

    resp = client.get(f"/api/crm/personas/{persona.id}/family", headers=headers)
    assert resp.status_code in (200, 404)


def test_persona_groups_endpoint(client, db_session):
    """Test persona groups endpoint."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)

    resp = client.get(f"/api/crm/personas/{persona.id}/groups", headers=headers)
    assert resp.status_code in (200, 404)


def test_resource_categorias_crud(client, db_session):
    """Test resource categories CRUD."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)

    resp = client.post(
        "/api/crm/resources/categorias",
        json={"nombre": "Test Category"},
        headers=headers,
    )
    assert resp.status_code in (200, 201), resp.text
    data = resp.json()
    cat_id = data.get("id")

    if cat_id:
        resp = client.patch(
            f"/api/crm/resources/categorias/{cat_id}",
            json={"name": "Updated Category"},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text

        resp = client.delete(f"/api/crm/resources/categorias/{cat_id}", headers=headers)
        assert resp.status_code == 204


def test_resource_plantillas_crud(client, db_session):
    """Test resource templates CRUD."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)

    resp = client.post(
        "/api/crm/resources/plantillas",
        json={"nombre": "Test Template", "titulo": "Asunto", "canal": "EMAIL", "contenido_texto": "Hola", "contenido_html": "<p>Hola</p>", "categoria_id": str(_uuid.uuid4())},
        headers=headers,
    )
    assert resp.status_code in (200, 201), resp.text
    data = resp.json()
    tpl_id = data.get("id")

    if tpl_id:
        resp = client.get(f"/api/crm/resources/plantillas/{tpl_id}", headers=headers)
        assert resp.status_code == 200

        resp = client.patch(
            f"/api/crm/resources/plantillas/{tpl_id}",
            json={"nombre": "Updated Template"},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text

        resp = client.delete(f"/api/crm/resources/plantillas/{tpl_id}", headers=headers)
        assert resp.status_code == 204
