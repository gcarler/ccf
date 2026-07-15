from __future__ import annotations

from backend import crud, models, schemas
from tests.conftest import auth_headers, seed_admin


def _create_persona(db_session, first_name: str, last_name: str, email: str):
    persona = crud.create_persona(
        db_session,
        schemas.PersonaCreate(
            first_name=first_name,
            last_name=last_name,
            email=email,
            church_role="Miembro",
        ),
    )
    return persona


def test_persona_detail_includes_mesh_and_current_mentorship(client, db_session):
    admin, _, sede = seed_admin(db_session, email="crm-mentor-admin@test.com")
    headers = auth_headers(client, email=admin.email, password="testpass123")

    mentee = _create_persona(db_session, "Mentee", "One", "mentee-one@test.com")
    mentor = _create_persona(db_session, "Mentor", "One", "mentor-one@test.com")
    mentee.sede_id = sede.id
    mentor.sede_id = sede.id
    mentor.health_score = 92
    mentor.health_status = "COMPROMETIDO"
    db_session.commit()

    resp = client.post(
        f"/api/crm/personas/{mentee.id}/mentorship",
        headers=headers,
        json={"mentor_persona_id": str(mentor.id), "notes": "Seguimiento inicial"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["mentor_persona_id"] == str(mentor.id)
    assert payload["mentee_persona_id"] == str(mentee.id)
    assert payload["status"] == "active"

    detail = client.get(f"/api/crm/personas/{mentee.id}", headers=headers)
    assert detail.status_code == 200
    data = detail.json()
    assert data["current_mentorship"]["mentor_persona_id"] == str(mentor.id)
    assert data["mesh_insight"]["summary"]
    assert data["mesh_insight"]["recommendation"]
    assert len(data["mesh_insight"]["metrics"]) == 3
    assert {metric["key"] for metric in data["mesh_insight"]["metrics"]} == {
        "attendance",
        "academy",
        "volunteer",
    }


def test_mentor_candidates_returns_fit_candidates(client, db_session):
    admin, _, sede = seed_admin(db_session, email="crm-candidate-admin@test.com")
    headers = auth_headers(client, email=admin.email, password="testpass123")

    mentee = _create_persona(db_session, "Mentee", "Two", "mentee-two@test.com")
    mentor = _create_persona(db_session, "Mentor", "Two", "mentor-two@test.com")
    mentee.sede_id = sede.id
    mentor.sede_id = sede.id
    mentor.health_score = 90
    mentor.health_status = "COMPROMETIDO"
    db_session.commit()

    resp = client.get(f"/api/crm/personas/{mentee.id}/mentor-candidates", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert any(item["id"] == str(mentor.id) for item in data)
    selected = next(item for item in data if item["id"] == str(mentor.id))
    assert selected["fit_score"] >= 40
    assert selected["fit_reason"]


def test_assigning_same_mentor_updates_active_assignment(client, db_session):
    admin, _, sede = seed_admin(db_session, email="crm-mentorship-admin@test.com")
    headers = auth_headers(client, email=admin.email, password="testpass123")

    mentee = _create_persona(db_session, "Mentee", "Three", "mentee-three@test.com")
    mentor = _create_persona(db_session, "Mentor", "Three", "mentor-three@test.com")
    mentee.sede_id = sede.id
    mentor.sede_id = sede.id
    mentor.health_score = 95
    mentor.health_status = "COMPROMETIDO"
    db_session.commit()

    first = client.post(
        f"/api/crm/personas/{mentee.id}/mentorship",
        headers=headers,
        json={"mentor_persona_id": str(mentor.id), "notes": "Primer seguimiento"},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/crm/personas/{mentee.id}/mentorship",
        headers=headers,
        json={"mentor_persona_id": str(mentor.id), "notes": "Notas actualizadas"},
    )
    assert second.status_code == 200
    data = second.json()
    assert data["mentor_persona_id"] == str(mentor.id)
    assert data["notes"] == "Notas actualizadas"

    rows = (
        db_session.query(models.PersonaMentorship)
        .filter(models.PersonaMentorship.mentee_persona_id == mentee.id)
        .all()
    )
    assert len(rows) == 1
    assert rows[0].status == "active"
