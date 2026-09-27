"""Pruebas de Calidad para Seguimiento Post-Evento, Campañas Multicanal y Asignación de Mentores.

TKT-EVT-FOLLOWUP-04:
- Valida motor de secuencias con cadencia de 3 pasos (24h, 72h, 7d).
- Valida asignación inteligente por cercanía/zona a mentores y líderes de Grupo de Vida.
- Valida balanceo de carga entre mentores.
- Valida aislamiento multi-tenant por sede_id (Axioma 3).
- Valida vinculación estricta con Persona y PersonaMentorship (Axioma 1).
- Valida despacho de pasos y registro de respuestas.
"""

from __future__ import annotations

import datetime
import uuid
from datetime import timedelta, timezone

from backend import models
from backend.models_crm import Persona
from backend.models_evangelism import GrupoEvangelismo
from backend.services.event_post_followup_service import (
    dispatch_followup_step,
    enroll_in_post_event_followup,
    match_best_mentor,
)
from tests.conftest import auth_headers, seed_admin


def _seed_followup_test_data(db, sede_id):
    now = datetime.datetime.now(timezone.utc)

    # 1. Crear evento
    event = models.CrmEvent(
        id=uuid.uuid4(),
        name="Gran Noche de Milagros",
        event_date=now - timedelta(days=1),
        location="Auditorio Central - Sector Norte",
        sede_id=sede_id,
        event_type="SPECIAL",
        status="PUBLISHED",
        requires_registration=True,
        capacity_max=200,
    )
    db.add(event)

    # 2. Crear líderes / mentores de Grupo de Vida
    leader_norte = Persona(
        id=uuid.uuid4(),
        first_name="Carlos",
        last_name="Mendoza",
        email="carlos.mendoza@ccf.org",
        phone="+573001112233",
        sede_id=sede_id,
        church_role="Líder de Grupo",
    )
    leader_sur = Persona(
        id=uuid.uuid4(),
        first_name="Marcela",
        last_name="Gómez",
        email="marcela.gomez@ccf.org",
        phone="+573004445566",
        sede_id=sede_id,
        church_role="Líder de Grupo",
    )
    db.add_all([leader_norte, leader_sur])
    db.flush()

    # 3. Crear Grupos de Vida en distintas zonas
    group_norte = GrupoEvangelismo(
        id=uuid.uuid4(),
        nombre="Grupo de Vida Norte 1",
        sede_id=sede_id,
        ubicacion="Sector Norte Suba",
        direccion="Calle 140 # 15-20",
        lider_persona_id=leader_norte.id,
        activo=True,
    )
    group_sur = GrupoEvangelismo(
        id=uuid.uuid4(),
        nombre="Grupo de Vida Sur 1",
        sede_id=sede_id,
        ubicacion="Sector Sur Kennedy",
        direccion="Carrera 78 # 40-10",
        lider_persona_id=leader_sur.id,
        activo=True,
    )
    db.add_all([group_norte, group_sur])
    db.flush()

    # 4. Crear Asistentes
    attendee_norte = Persona(
        id=uuid.uuid4(),
        first_name="Andrés",
        last_name="Pérez",
        email="andres.perez@example.com",
        phone="+573112223344",
        sede_id=sede_id,
        address="Calle 142 Suba",
        church_role="Visitante",
    )
    attendee_sur = Persona(
        id=uuid.uuid4(),
        first_name="Diana",
        last_name="Ríos",
        email="diana.rios@example.com",
        phone="+573156667788",
        sede_id=sede_id,
        address="Kennedy Central",
        church_role="Visitante",
    )
    db.add_all([attendee_norte, attendee_sur])
    db.flush()

    # 5. Registrar e ingresar check-in
    reg_norte = models.EventRegistration(
        id=uuid.uuid4(),
        event_id=event.id,
        persona_id=attendee_norte.id,
        registration_number=101,
        registration_status="CHECKED_IN",
        check_in_at=now - timedelta(hours=2),
        extras={},
    )
    reg_sur = models.EventRegistration(
        id=uuid.uuid4(),
        event_id=event.id,
        persona_id=attendee_sur.id,
        registration_number=102,
        registration_status="CHECKED_IN",
        check_in_at=now - timedelta(hours=2),
        extras={},
    )
    db.add_all([reg_norte, reg_sur])
    db.commit()

    return {
        "event": event,
        "leader_norte": leader_norte,
        "leader_sur": leader_sur,
        "group_norte": group_norte,
        "group_sur": group_sur,
        "attendee_norte": attendee_norte,
        "attendee_sur": attendee_sur,
        "reg_norte": reg_norte,
        "reg_sur": reg_sur,
    }


def test_auto_enroll_and_intelligent_mentor_matching_zone(db_session):
    """Verifica que el algoritmo empareje asistentes con líderes de su zona geográfica."""
    admin, _, sede = seed_admin(db_session)
    data = _seed_followup_test_data(db_session, sede.id)
    event = data["event"]
    att_norte = data["attendee_norte"]
    reg_norte = data["reg_norte"]
    att_sur = data["attendee_sur"]
    reg_sur = data["reg_sur"]

    # Inscribir asistente norte
    res_norte = enroll_in_post_event_followup(db_session, event, att_norte, registration=reg_norte, auto_assign_mentor=True)
    assert res_norte["status"] == "ACTIVE"
    assert res_norte["mentor_persona_id"] == str(data["leader_norte"].id)
    assert res_norte["suggested_group_id"] == str(data["group_norte"].id)
    assert res_norte["matched_by_zone"] is True
    assert res_norte["step_1"]["status"] == "SCHEDULED"
    assert res_norte["step_2"]["status"] == "SCHEDULED"
    assert res_norte["step_3"]["status"] == "SCHEDULED"

    # Inscribir asistente sur
    res_sur = enroll_in_post_event_followup(db_session, event, att_sur, registration=reg_sur, auto_assign_mentor=True)
    assert res_sur["mentor_persona_id"] == str(data["leader_sur"].id)
    assert res_sur["suggested_group_id"] == str(data["group_sur"].id)
    assert res_sur["matched_by_zone"] is True

    # Verificar que se creó el registro en PersonaMentorship (Axioma 1)
    mentorship = (
        db_session.query(models.PersonaMentorship)
        .filter(models.PersonaMentorship.mentee_persona_id == att_norte.id)
        .first()
    )
    assert mentorship is not None
    assert mentorship.mentor_persona_id == data["leader_norte"].id
    assert mentorship.status == "active"


def test_mentor_load_balancing(db_session):
    """Verifica que ante zonas iguales, el balanceador priorice al mentor con menor carga."""
    admin, _, sede = seed_admin(db_session)
    data = _seed_followup_test_data(db_session, sede.id)
    event = data["event"]
    sede_id = event.sede_id

    # Crear dos mentores en la misma zona
    m1 = Persona(id=uuid.uuid4(), first_name="Líder", last_name="Uno", sede_id=sede_id, church_role="Líder")
    m2 = Persona(id=uuid.uuid4(), first_name="Líder", last_name="Dos", sede_id=sede_id, church_role="Líder")
    db_session.add_all([m1, m2])
    db_session.flush()

    g1 = GrupoEvangelismo(id=uuid.uuid4(), nombre="G1", sede_id=sede_id, ubicacion="Centro", direccion="Cra 7", lider_persona_id=m1.id, activo=True)
    g2 = GrupoEvangelismo(id=uuid.uuid4(), nombre="G2", sede_id=sede_id, ubicacion="Centro", direccion="Cra 7", lider_persona_id=m2.id, activo=True)
    db_session.add_all([g1, g2])
    db_session.flush()

    # m1 ya tiene 3 personas asignadas
    for _ in range(3):
        fake_mentee = Persona(id=uuid.uuid4(), first_name="Fake", last_name="Mentee", sede_id=sede_id)
        db_session.add(fake_mentee)
        db_session.flush()
        db_session.add(models.PersonaMentorship(sede_id=sede_id, mentee_persona_id=fake_mentee.id, mentor_persona_id=m1.id, status="active"))
    db_session.commit()

    # Nuevo asistente en "Centro"
    new_att = Persona(id=uuid.uuid4(), first_name="Nuevo", last_name="Centro", sede_id=sede_id, address="Centro Cra 7")
    db_session.add(new_att)
    db_session.flush()

    best_m, best_g, matched = match_best_mentor(db_session, event, new_att, user_sede_id=sede_id)
    # Debe asignar m2 porque tiene 0 mentees, mientras m1 tiene 3
    assert best_m.id == m2.id
    assert best_g.id == g2.id
    assert matched is True


def test_multi_tenant_isolation_in_mentorship(db_session):
    """Verifica que nunca se asigne un mentor de otra sede (Axioma 3)."""
    admin, _, sede = seed_admin(db_session)
    data = _seed_followup_test_data(db_session, sede.id)
    event = data["event"]

    other_sede = models.Sede(id=uuid.uuid4(), nombre="Sede Otra Ciudad", ciudad="Medellín")
    db_session.add(other_sede)
    db_session.flush()

    foreign_leader = Persona(id=uuid.uuid4(), first_name="Líder", last_name="Foráneo", sede_id=other_sede.id, church_role="Líder")
    db_session.add(foreign_leader)
    db_session.flush()

    foreign_group = GrupoEvangelismo(
        id=uuid.uuid4(),
        nombre="Grupo Otra Sede",
        sede_id=other_sede.id,
        ubicacion="Suba",  # Misma palabra clave pero en otra sede
        lider_persona_id=foreign_leader.id,
        activo=True,
    )
    db_session.add(foreign_group)
    db_session.commit()

    att = data["attendee_norte"]
    best_m, best_g, _ = match_best_mentor(db_session, event, att, user_sede_id=event.sede_id)
    assert best_m.id != foreign_leader.id
    assert best_g.id != foreign_group.id
    assert best_m.sede_id == event.sede_id


def test_dispatch_followup_steps_cadence(db_session):
    """Verifica la ejecución y avance de cada paso de la cadencia (24h -> 72h -> 7d)."""
    admin, _, sede = seed_admin(db_session)
    data = _seed_followup_test_data(db_session, sede.id)
    event = data["event"]
    att = data["attendee_norte"]
    reg = data["reg_norte"]

    enroll_in_post_event_followup(db_session, event, att, registration=reg, auto_assign_mentor=True)

    # 1. Despachar Paso 1
    res1 = dispatch_followup_step(db_session, event, att, reg, step_number=1)
    assert res1["success"] is True
    assert res1["step_number"] == 1
    followup = reg.extras["followup_sequence"]
    assert followup["step_1"]["status"] == "SENT"
    assert followup["current_step"] == 2
    assert followup["status"] == "ACTIVE"

    # Reintento sin forzar no debe reenviar
    res1_dup = dispatch_followup_step(db_session, event, att, reg, step_number=1, force=False)
    assert res1_dup["already_sent"] is True

    # 2. Despachar Paso 2
    res2 = dispatch_followup_step(db_session, event, att, reg, step_number=2)
    assert res2["success"] is True
    followup = reg.extras["followup_sequence"]
    assert followup["step_2"]["status"] == "SENT"
    assert followup["current_step"] == 3
    assert followup["status"] == "ACTIVE"

    # 3. Despachar Paso 3
    res3 = dispatch_followup_step(db_session, event, att, reg, step_number=3)
    assert res3["success"] is True
    followup = reg.extras["followup_sequence"]
    assert followup["step_3"]["status"] == "SENT"
    assert followup["status"] == "COMPLETED"


def test_followup_endpoints_via_client(db_session, client):
    """Valida los endpoints REST de overview, attendees y asignación inteligente."""
    admin, _, sede = seed_admin(db_session)
    data = _seed_followup_test_data(db_session, sede.id)
    event_id = str(data["event"].id)

    # Inscribir participantes
    enroll_in_post_event_followup(db_session, data["event"], data["attendee_norte"], registration=data["reg_norte"])

    headers = auth_headers(client)

    # 1. GET overview
    res_overview = client.get(f"/api/evangelism/events/{event_id}/followup/overview", headers=headers)
    assert res_overview.status_code == 200, res_overview.text
    ov_data = res_overview.json()
    assert "total_enrolled" in ov_data
    assert "steps_summary" in ov_data
    assert "sequence_definition" in ov_data
    assert len(ov_data["sequence_definition"]) == 3

    # 2. GET attendees
    res_att = client.get(f"/api/evangelism/events/{event_id}/followup/attendees", headers=headers)
    assert res_att.status_code == 200, res_att.text
    att_list = res_att.json()
    assert isinstance(att_list, list)
    assert len(att_list) >= 1

    # 3. POST auto-assign-mentors
    res_assign = client.post(f"/api/evangelism/events/{event_id}/followup/auto-assign-mentors", headers=headers)
    assert res_assign.status_code == 200, res_assign.text
    assign_data = res_assign.json()
    assert assign_data["success"] is True
    assert "assigned_count" in assign_data

    # 4. POST record-response
    res_resp = client.post(
        f"/api/evangelism/events/{event_id}/followup/record-response",
        json={"persona_id": str(data["attendee_norte"].id), "notes": "Confirmó asistencia a Grupo de Vida", "channel": "WHATSAPP"},
        headers=headers,
    )
    assert res_resp.status_code == 200, res_resp.text
    assert res_resp.json()["success"] is True

    # 5. GET available-mentors
    res_mentors = client.get(f"/api/evangelism/events/{event_id}/followup/available-mentors", headers=headers)
    assert res_mentors.status_code == 200, res_mentors.text
    mentors_list = res_mentors.json()
    assert isinstance(mentors_list, list)
