import uuid
from datetime import date

from backend import models
from tests.conftest import auth_headers, seed_admin


def _create_persona(db_session, sede, is_baptized=False, email_suffix="test"):
    persona = models.Persona(
        id=uuid.uuid4(),
        first_name="Endpoint",
        last_name="Test",
        email=f"endpoint_{email_suffix}@example.com",
        sede_id=sede.id,
        is_baptized=is_baptized,
    )
    db_session.add(persona)
    db_session.commit()
    return persona


def _get_persona_health(client, persona_id, headers):
    response = client.get(f"/api/crm/personas/{persona_id}", headers=headers)
    assert response.status_code == 200
    return response.json()


def test_get_persona_reflects_asistencia_change(client, db_session):
    """GET /api/crm/personas/{id} refleja una asistencia agregada."""
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client)
    persona = _create_persona(db_session, sede)

    data_before = _get_persona_health(client, persona.id, headers)
    assert data_before["health_score"] == 0
    assert data_before["health_status"] == "EN_RIESGO"

    asist = models.Asistencia(
        id=uuid.uuid4(),
        persona_id=persona.id,
        sesion_id=uuid.uuid4(),
        estado="presente",
    )
    db_session.add(asist)
    db_session.commit()

    data_after = _get_persona_health(client, persona.id, headers)
    assert data_after["health_score"] == 50
    assert data_after["health_status"] == "ESTABLE"


def test_get_persona_reflects_milestone_change(client, db_session):
    """GET /api/crm/personas/{id} refleja un milestone agregado."""
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client)
    persona = _create_persona(db_session, sede, is_baptized=True)

    data_before = _get_persona_health(client, persona.id, headers)
    assert data_before["health_score"] == 10
    assert data_before["health_status"] == "EN_RIESGO"

    milestone = models.SpiritualMilestone(
        id=uuid.uuid4(),
        persona_id=persona.id,
        sede_id=sede.id,
        type="Encuentro",
        event_date=date.today(),
    )
    db_session.add(milestone)
    db_session.commit()

    data_after = _get_persona_health(client, persona.id, headers)
    assert data_after["health_score"] == 20
    assert data_after["health_status"] == "EN_RIESGO"


def test_get_persona_reflects_communication_change(client, db_session):
    """GET /api/crm/personas/{id} refleja un communication log agregado."""
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client)
    persona = _create_persona(db_session, sede)

    data_before = _get_persona_health(client, persona.id, headers)
    assert data_before["health_score"] == 0
    assert data_before["health_status"] == "EN_RIESGO"

    log = models.CommunicationLog(
        id=uuid.uuid4(),
        persona_id=persona.id,
        channel="WhatsApp",
        content="Hola",
        outcome="sent",
    )
    db_session.add(log)
    db_session.commit()

    data_after = _get_persona_health(client, persona.id, headers)
    assert data_after["health_score"] == 5
    assert data_after["health_status"] == "EN_RIESGO"


def test_get_persona_reflects_combined_changes(client, db_session):
    """GET /api/crm/personas/{id} refleja asistencia, milestone y comunicación."""
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client)
    persona = _create_persona(db_session, sede, is_baptized=True)

    data_before = _get_persona_health(client, persona.id, headers)
    assert data_before["health_score"] == 10
    assert data_before["health_status"] == "EN_RIESGO"

    asist = models.Asistencia(
        id=uuid.uuid4(),
        persona_id=persona.id,
        sesion_id=uuid.uuid4(),
        estado="presente",
    )
    milestone = models.SpiritualMilestone(
        id=uuid.uuid4(),
        persona_id=persona.id,
        sede_id=sede.id,
        type="Discipulado",
        event_date=date.today(),
    )
    log = models.CommunicationLog(
        id=uuid.uuid4(),
        persona_id=persona.id,
        channel="Email",
        content="Seguimiento",
        outcome="sent",
    )
    db_session.add_all([asist, milestone, log])
    db_session.commit()

    data_after = _get_persona_health(client, persona.id, headers)
    # 50 asistencia + 20 milestones + 5 comunicación = 75
    assert data_after["health_score"] == 75
    assert data_after["health_status"] == "ESTABLE"
