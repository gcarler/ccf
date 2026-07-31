"""Coverage for backend/api/crm/personas.py — target 90%."""

from __future__ import annotations

import uuid

from backend import models
from tests.conftest import auth_headers, seed_admin


def _create_persona(db_session, sede, **kw):
    p = models.Persona(
        id=uuid.uuid4(),
        first_name=kw.get("first_name", "API"),
        last_name="Test",
        email=kw.get("email", f"api_{uuid.uuid4().hex[:8]}@example.com"),
        sede_id=sede.id,
    )
    db_session.add(p)
    db_session.commit()
    return p


def test_list_personas(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)
    _create_persona(db_session, sede)
    response = client.get("/api/crm/personas", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_list_personas_page(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)
    _create_persona(db_session, sede)
    response = client.get("/api/crm/personas/page", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


def test_create_persona(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)
    payload = {"first_name": "Nuevo", "last_name": "Test", "email": "nuevo@example.com"}
    response = client.post("/api/crm/personas", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Nuevo"


def test_get_persona(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)
    p = _create_persona(db_session, sede)
    response = client.get(f"/api/crm/personas/{p.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "API"


def test_get_persona_not_found(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)
    response = client.get(f"/api/crm/personas/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


def test_update_persona_put(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)
    p = _create_persona(db_session, sede)
    payload = {"first_name": "Updated"}
    response = client.put(f"/api/crm/personas/{p.id}", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["first_name"] == "Updated"


def test_patch_persona(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)
    p = _create_persona(db_session, sede)
    payload = {"last_name": "Patched"}
    response = client.patch(f"/api/crm/personas/{p.id}", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["last_name"] == "Patched"


def test_delete_persona(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)
    p = _create_persona(db_session, sede)
    response = client.delete(f"/api/crm/personas/{p.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_my_ministry_profile(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)
    response = client.get("/api/crm/personas/me/profile", headers=headers)
    assert response.status_code == 200


def test_update_my_profile(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)
    payload = {"first_name": "SelfUpdated"}
    response = client.patch("/api/crm/personas/me/profile", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["first_name"] == "SelfUpdated"


def test_mentor_candidates(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)
    p = _create_persona(db_session, sede)
    candidate = _create_persona(db_session, sede, first_name="Mentor", email="mentor_cand@example.com")
    db_session.query(models.Persona).filter(models.Persona.id == candidate.id).update({"health_score": 95.0})
    db_session.commit()
    response = client.get(f"/api/crm/personas/{p.id}/mentor-candidates", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_assign_mentorship(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)
    p = _create_persona(db_session, sede)
    mentor = _create_persona(db_session, sede, first_name="Mentor", email="mentor_assign@example.com")
    payload = {"mentor_persona_id": str(mentor.id)}
    response = client.post(f"/api/crm/personas/{p.id}/mentorship", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"


def test_persona_donations(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)
    p = _create_persona(db_session, sede)
    response = client.get(f"/api/crm/personas/{p.id}/donations", headers=headers)
    assert response.status_code == 200


def test_persona_timeline(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)
    p = _create_persona(db_session, sede)
    response = client.get(f"/api/crm/personas/{p.id}/timeline", headers=headers)
    assert response.status_code == 200
