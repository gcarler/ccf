import uuid
from datetime import date, datetime, timezone

from backend import models
from backend.crud.crm_.health import calculate_pastoral_health, update_pastoral_health
from tests.conftest import auth_headers, seed_admin


def test_calculate_pastoral_health_attendance_details(db_session):
    """Test attendance score calculations with different opportunities and attendance types."""
    # Seed an admin to get a valid Sede
    _, admin_persona, sede = seed_admin(db_session)

    # 1. Create a Persona
    persona = models.Persona(
        id=uuid.uuid4(),
        first_name="Test",
        last_name="Scoring",
        email="test_score@example.com",
        sede_id=sede.id,
        is_baptized=False,
    )
    db_session.add(persona)
    db_session.commit()

    # Case A: 0 opportunities -> Attendance score should be 0
    score, status = calculate_pastoral_health(db_session, persona.id)
    assert score == 0
    assert status == "EN_RIESGO"

    # Case B: Asistencia opportunities (with different states and deleted_at filter)
    # Opportunity 1: Active, present
    asist1 = models.Asistencia(id=uuid.uuid4(), persona_id=persona.id, sesion_id=uuid.uuid4(), estado="presente")
    # Opportunity 2: Active, absent
    asist2 = models.Asistencia(id=uuid.uuid4(), persona_id=persona.id, sesion_id=uuid.uuid4(), estado="falto")
    # Opportunity 3: Deleted, present (should NOT count as opportunity)
    asist3 = models.Asistencia(
        id=uuid.uuid4(),
        persona_id=persona.id,
        sesion_id=uuid.uuid4(),
        estado="presente",
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add_all([asist1, asist2, asist3])
    db_session.commit()

    # Opps = 2, Attended = 1. Attendance score = 1 / 2 * 50 = 25.0
    score, status = calculate_pastoral_health(db_session, persona.id)
    assert score == 25
    assert status == "EN_RIESGO"

    # Case C: EventAttendance opportunities
    # Opportunity 4: Event, attended = True
    evt1 = models.EventAttendance(
        id=uuid.uuid4(),
        persona_id=persona.id,
        event_id=uuid.uuid4(),
        session_date=date.today(),
        status="present",
        attended=True,
    )
    # Opportunity 5: Event, attended = False
    evt2 = models.EventAttendance(
        id=uuid.uuid4(),
        persona_id=persona.id,
        event_id=uuid.uuid4(),
        session_date=date.today(),
        status="absent",
        attended=False,
    )
    db_session.add_all([evt1, evt2])
    db_session.commit()

    # Previous Opps = 2, Attended = 1
    # New Opps = 4 (2 + 2), New Attended = 2 (1 + 1). Attendance score = 2 / 4 * 50 = 25.0
    score, status = calculate_pastoral_health(db_session, persona.id)
    assert score == 25

    # Case D: CourseAttendance opportunities via Enrollment
    # Setup Enrollment (active)
    course_id = uuid.uuid4()
    enrollment = models.Enrollment(id=uuid.uuid4(), persona_id=persona.id, course_id=course_id, status="active")
    # Setup Enrollment (deleted - should NOT link CourseAttendance)
    enrollment_deleted = models.Enrollment(
        id=uuid.uuid4(),
        persona_id=persona.id,
        course_id=uuid.uuid4(),
        status="active",
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add_all([enrollment, enrollment_deleted])
    db_session.commit()

    # Opportunity 6: CourseAttendance, status = present
    course_att1 = models.CourseAttendance(
        id=uuid.uuid4(),
        enrollment_id=enrollment.id,
        session_date=datetime.now(timezone.utc),
        status="present",
    )
    # Opportunity 7: CourseAttendance under deleted enrollment (should NOT count)
    course_att2 = models.CourseAttendance(
        id=uuid.uuid4(),
        enrollment_id=enrollment_deleted.id,
        session_date=datetime.now(timezone.utc),
        status="present",
    )
    db_session.add_all([course_att1, course_att2])
    db_session.commit()

    # Total Opps = 5 (2 Asistencia + 2 EventAttendance + 1 CourseAttendance)
    # Total Attended = 3 (1 Asistencia + 1 EventAttendance + 1 CourseAttendance)
    # Attendance score = 3 / 5 * 50 = 30.0
    score, status = calculate_pastoral_health(db_session, persona.id)
    assert score == 30


def test_calculate_pastoral_health_milestone_and_communication(db_session):
    """Test milestone and communication score calculations, caps, and boundaries."""
    _, admin_persona, sede = seed_admin(db_session)

    persona = models.Persona(
        id=uuid.uuid4(),
        first_name="Jane",
        last_name="Doe",
        email="jane_doe@example.com",
        sede_id=sede.id,
        is_baptized=True,  # adds 1 milestone point (10 score points)
    )
    db_session.add(persona)
    db_session.commit()

    # 1. Milestone score testing
    # Active milestone
    milestone1 = models.SpiritualMilestone(
        id=uuid.uuid4(), persona_id=persona.id, sede_id=sede.id, type="Encuentro", event_date=date.today()
    )
    # Deleted milestone (should NOT count)
    milestone2 = models.SpiritualMilestone(
        id=uuid.uuid4(),
        persona_id=persona.id,
        sede_id=sede.id,
        type="Bautismo",
        event_date=date.today(),
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add_all([milestone1, milestone2])
    db_session.commit()

    # Milestones count = 1. is_baptized = True (+1). Total milestone points = 2 * 10 = 20 score points.
    score, status = calculate_pastoral_health(db_session, persona.id)
    assert score == 20  # attendance = 0, milestones = 20, comms = 0

    # Add 2 more milestones (total active = 3. points = 3 + 1 = 4 * 10 = 40, capped at 30).
    milestone3 = models.SpiritualMilestone(
        id=uuid.uuid4(), persona_id=persona.id, sede_id=sede.id, type="Discipulado", event_date=date.today()
    )
    milestone4 = models.SpiritualMilestone(
        id=uuid.uuid4(), persona_id=persona.id, sede_id=sede.id, type="Liderazgo", event_date=date.today()
    )
    db_session.add_all([milestone3, milestone4])
    db_session.commit()

    score, status = calculate_pastoral_health(db_session, persona.id)
    assert score == 30

    # 2. Communication score testing
    # Active communication log
    comm_log1 = models.CommunicationLog(
        id=uuid.uuid4(), persona_id=persona.id, channel="WhatsApp", content="Hello!", outcome="sent"
    )
    db_session.add(comm_log1)
    db_session.commit()

    # Total comms = 1 * 5 = 5. Total score = 30 (milestones) + 5 = 35.
    score, status = calculate_pastoral_health(db_session, persona.id)
    assert score == 35
    assert status == "EN_RIESGO"

    # CasoCRM + InteraccionCRM
    pipeline = models.PipelineCRM(id=uuid.uuid4(), sede_id=sede.id, nombre="Pipeline Test", tipo="NUEVOS_VISITANTES")
    etapa = models.EtapaPipeline(id=uuid.uuid4(), pipeline_id=pipeline.id, nombre="Etapa Test", orden=1)
    db_session.add_all([pipeline, etapa])
    db_session.commit()

    caso = models.CasoCRM(
        id=uuid.uuid4(),
        persona_id=persona.id,
        sede_id=sede.id,
        pipeline_id=pipeline.id,
        etapa_actual_id=etapa.id,
        titulo_caso="Caso Test",
        origen_canal="WEB_FORM",
    )
    # Deleted CasoCRM (should NOT link interacciones for score)
    caso_deleted = models.CasoCRM(
        id=uuid.uuid4(),
        persona_id=persona.id,
        sede_id=sede.id,
        pipeline_id=pipeline.id,
        etapa_actual_id=etapa.id,
        titulo_caso="Caso Deleted",
        origen_canal="WEB_FORM",
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add_all([caso, caso_deleted])
    db_session.commit()

    interact1 = models.InteraccionCRM(
        id=uuid.uuid4(),
        caso_id=caso.id,
        realizado_por_id=admin_persona.id,
        tipo="LLAMADA_OUTBOUND",
        resumen="Llamada exitosa",
    )
    interact2 = models.InteraccionCRM(
        id=uuid.uuid4(),
        caso_id=caso_deleted.id,
        realizado_por_id=admin_persona.id,
        tipo="LLAMADA_OUTBOUND",
        resumen="Should be ignored",
    )
    db_session.add_all([interact1, interact2])
    db_session.commit()

    # Total comms = 1 (comm_log) + 1 (interact1) = 2 * 5 = 10.
    # Total score = 30 (milestones) + 10 = 40.
    # Status boundaries: ESTABLE is 40 <= Score < 80.
    score, status = calculate_pastoral_health(db_session, persona.id)
    assert score == 40
    assert status == "ESTABLE"

    # Add more comm logs to cap out (capped at 20 points, total 4 logs/interactions)
    comm_log2 = models.CommunicationLog(
        id=uuid.uuid4(), persona_id=persona.id, channel="Email", content="Test", outcome="sent"
    )
    comm_log3 = models.CommunicationLog(
        id=uuid.uuid4(), persona_id=persona.id, channel="SMS", content="Test", outcome="sent"
    )
    comm_log4 = models.CommunicationLog(
        id=uuid.uuid4(), persona_id=persona.id, channel="Call", content="Test", outcome="sent"
    )
    db_session.add_all([comm_log2, comm_log3, comm_log4])
    db_session.commit()

    # Total comms = 5 (4 logs + 1 interaction) = 25 capped at 20.
    # Total score = 30 (milestones) + 20 = 50.
    score, status = calculate_pastoral_health(db_session, persona.id)
    assert score == 50
    assert status == "ESTABLE"


def test_update_pastoral_health_and_persistence(db_session):
    """Test that update_pastoral_health commits to DB and returns the updated persona."""
    _, admin_persona, sede = seed_admin(db_session)
    persona = models.Persona(
        id=uuid.uuid4(), first_name="Bob", last_name="Smith", email="bob@example.com", sede_id=sede.id, is_baptized=True
    )
    db_session.add(persona)
    db_session.commit()

    # Before update
    assert persona.health_score is None
    assert persona.health_status is None

    updated = update_pastoral_health(db_session, persona.id)

    assert updated.id == persona.id
    assert updated.health_score == 10  # 1 milestone (baptized) = 10
    assert updated.health_status == "EN_RIESGO"

    # Verify db persistence by querying again
    db_session.expire_all()
    queried = db_session.query(models.Persona).filter(models.Persona.id == persona.id).first()
    assert queried.health_score == 10
    assert queried.health_status == "EN_RIESGO"


def test_get_persona_api_endpoint(client, db_session):
    """Test that calling GET /api/crm/personas/{id} updates and serializes health fields."""
    user, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=user.email)

    # Create target persona in same sede
    target_persona = models.Persona(
        id=uuid.uuid4(),
        first_name="Target",
        last_name="Persona",
        email="target@example.com",
        sede_id=sede.id,
        is_baptized=True,
    )
    db_session.add(target_persona)
    db_session.commit()

    # Call API to get persona
    url = f"/api/crm/personas/{target_persona.id}"
    resp = client.get(url, headers=headers)
    assert resp.status_code == 200

    data = resp.json()
    assert data["id"] == str(target_persona.id)
    assert data["health_score"] == 10
    assert data["health_status"] == "EN_RIESGO"

    # Add 8 milestones to get > 80 score (COMPROMETIDO)
    # Milestone score = 30 (maxed).
    # Add 10 opportunities with 10 attended to get 50 attendance score.
    # Add 4 comms to get 20 comm score.
    # Total score = 50 + 30 + 20 = 100.
    for _ in range(5):
        milestone = models.SpiritualMilestone(
            id=uuid.uuid4(), persona_id=target_persona.id, sede_id=sede.id, type="Milestone", event_date=date.today()
        )
        db_session.add(milestone)

    for i in range(10):
        asist = models.Asistencia(
            id=uuid.uuid4(), persona_id=target_persona.id, sesion_id=uuid.uuid4(), estado="presente"
        )
        db_session.add(asist)

    for i in range(4):
        comm = models.CommunicationLog(
            id=uuid.uuid4(), persona_id=target_persona.id, channel="WhatsApp", content="Message", outcome="sent"
        )
        db_session.add(comm)

    db_session.commit()

    resp = client.get(url, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["health_score"] == 100
    assert data["health_status"] == "COMPROMETIDO"


def test_pastoral_health_adversarial_and_edge_cases(db_session):
    """Adversarial and edge case testing for Pastoral Health Score calculation."""
    # Seed an admin to get a valid Sede A
    _, _, sede_a = seed_admin(db_session)

    # 1. Edge Case: 0 Attendance Opportunities
    persona_zero = models.Persona(
        id=uuid.uuid4(),
        first_name="Zero",
        last_name="Opps",
        email="zero_opps@example.com",
        sede_id=sede_a.id,
        is_baptized=False,
    )
    db_session.add(persona_zero)
    db_session.commit()

    score, status = calculate_pastoral_health(db_session, persona_zero.id)
    assert score == 0
    assert status == "EN_RIESGO"

    # 2. Large inputs / boundary capping / None values
    persona_large = models.Persona(
        id=uuid.uuid4(),
        first_name="Large",
        last_name="Inputs",
        email="large_inputs@example.com",
        sede_id=sede_a.id,
        is_baptized=None,  # Tests None handling for is_baptized
    )
    db_session.add(persona_large)
    db_session.commit()

    # Add 50 milestones (capped at 30 points)
    for _ in range(50):
        milestone = models.SpiritualMilestone(
            id=uuid.uuid4(),
            persona_id=persona_large.id,
            sede_id=sede_a.id,
            type="Milestone",
            event_date=date.today(),
        )
        db_session.add(milestone)

    # Add 100 comm logs (capped at 20 points)
    for i in range(100):
        comm = models.CommunicationLog(
            id=uuid.uuid4(),
            persona_id=persona_large.id,
            channel="WhatsApp",
            content=f"Msg {i}",
            outcome="sent",
        )
        db_session.add(comm)

    # Add 100 Asistencia records (all present -> 50 points)
    for _ in range(100):
        asist = models.Asistencia(
            id=uuid.uuid4(),
            persona_id=persona_large.id,
            sesion_id=uuid.uuid4(),
            estado="presente",
        )
        db_session.add(asist)

    db_session.commit()

    # Total score should be 50 (attendance) + 30 (milestones) + 20 (comm) = 100
    score, status = calculate_pastoral_health(db_session, persona_large.id)
    assert score == 100
    assert status == "COMPROMETIDO"

    # 3. Mix of different attendance statuses (including case-insensitivity, trim, and unsupported statuses)
    persona_mixed = models.Persona(
        id=uuid.uuid4(),
        first_name="Mixed",
        last_name="Attendance",
        email="mixed_attendance@example.com",
        sede_id=sede_a.id,
        is_baptized=False,
    )
    db_session.add(persona_mixed)
    db_session.commit()

    # Valid attended Asistencias (5 records)
    valid_states = ["  asIsTiO  ", "PRESENTE", " present  ", "primera_vez  ", "  first_time"]
    for state in valid_states:
        asist = models.Asistencia(
            id=uuid.uuid4(),
            persona_id=persona_mixed.id,
            sesion_id=uuid.uuid4(),
            estado=state,
        )
        db_session.add(asist)

    # Invalid/unattended Asistencias (4 records, count as opportunities but not attended)
    invalid_states = ["falto", "justificado", "", "invalido"]
    for state in invalid_states:
        asist = models.Asistencia(
            id=uuid.uuid4(),
            persona_id=persona_mixed.id,
            sesion_id=uuid.uuid4(),
            estado=state,
        )
        db_session.add(asist)

    # EventAttendance: 1 attended=True, 2 attended=False (should not count as attended, but counts as opportunity)
    evt_t = models.EventAttendance(
        id=uuid.uuid4(), persona_id=persona_mixed.id, event_id=uuid.uuid4(), session_date=date.today(), status="present", attended=True
    )
    evt_f = models.EventAttendance(
        id=uuid.uuid4(), persona_id=persona_mixed.id, event_id=uuid.uuid4(), session_date=date.today(), status="absent", attended=False
    )
    evt_n = models.EventAttendance(
        id=uuid.uuid4(), persona_id=persona_mixed.id, event_id=uuid.uuid4(), session_date=date.today(), status="unknown", attended=False
    )
    db_session.add_all([evt_t, evt_f, evt_n])

    # CourseAttendance:
    # Setup Enrollment
    enrollment = models.Enrollment(id=uuid.uuid4(), persona_id=persona_mixed.id, course_id=uuid.uuid4(), status="active")
    db_session.add(enrollment)
    db_session.commit()

    # 1 present, 1 present-cased with spaces, 1 absent, 1 presente (should NOT count as present since it doesn't match 'present')
    course_att1 = models.CourseAttendance(
        id=uuid.uuid4(),
        enrollment_id=enrollment.id,
        session_date=datetime.now(timezone.utc),
        status="present",
    )
    course_att2 = models.CourseAttendance(
        id=uuid.uuid4(),
        enrollment_id=enrollment.id,
        session_date=datetime.now(timezone.utc),
        status="  PRESENT  ",
    )
    course_att3 = models.CourseAttendance(
        id=uuid.uuid4(),
        enrollment_id=enrollment.id,
        session_date=datetime.now(timezone.utc),
        status="absent",
    )
    course_att4 = models.CourseAttendance(
        id=uuid.uuid4(),
        enrollment_id=enrollment.id,
        session_date=datetime.now(timezone.utc),
        status="presente",
    )
    db_session.add_all([course_att1, course_att2, course_att3, course_att4])
    db_session.commit()

    # Total Opportunities:
    # Asistencia: 5 valid + 4 invalid = 9
    # EventAttendance: 3 (evt_t, evt_f, evt_n)
    # CourseAttendance: 4
    # Total Opps = 9 + 3 + 4 = 16.
    # Total Attended:
    # Asistencia: 5
    # EventAttendance: 1 (evt_t)
    # CourseAttendance: 2 (course_att1, course_att2)
    # Total Attended = 5 + 1 + 2 = 8.
    # Attendance Score: 8 / 16 * 50 = 25.0
    score, status = calculate_pastoral_health(db_session, persona_mixed.id)
    assert score == 25
    assert status == "EN_RIESGO"

    # 4. Status Boundaries and Rounding
    # Case A: Score exactly 39 (EN_RIESGO)
    persona_39 = models.Persona(
        id=uuid.uuid4(), first_name="P39", last_name="Test", email="p39@example.com", sede_id=sede_a.id, is_baptized=False
    )
    db_session.add(persona_39)
    # Opps = 50, Attended = 39 -> score = 39
    for i in range(50):
        db_session.add(models.Asistencia(
            id=uuid.uuid4(), persona_id=persona_39.id, sesion_id=uuid.uuid4(), estado="presente" if i < 39 else "falto"
        ))
    db_session.commit()
    score_39, status_39 = calculate_pastoral_health(db_session, persona_39.id)
    assert score_39 == 39
    assert status_39 == "EN_RIESGO"

    # Case B: Score exactly 40 (ESTABLE)
    persona_40 = models.Persona(
        id=uuid.uuid4(), first_name="P40", last_name="Test", email="p40@example.com", sede_id=sede_a.id, is_baptized=False
    )
    db_session.add(persona_40)
    # Opps = 50, Attended = 40 -> score = 40
    for i in range(50):
        db_session.add(models.Asistencia(
            id=uuid.uuid4(), persona_id=persona_40.id, sesion_id=uuid.uuid4(), estado="presente" if i < 40 else "falto"
        ))
    db_session.commit()
    score_40, status_40 = calculate_pastoral_health(db_session, persona_40.id)
    assert score_40 == 40
    assert status_40 == "ESTABLE"

    # Case C: Score exactly 79 (ESTABLE)
    persona_79 = models.Persona(
        id=uuid.uuid4(), first_name="P79", last_name="Test", email="p79@example.com", sede_id=sede_a.id, is_baptized=False
    )
    db_session.add(persona_79)
    # Milestones = 30 (max), Comms = 20 (max). Need attendance = 29.
    # Opps = 50, Attended = 29 -> score = 29.
    for i in range(50):
        db_session.add(models.Asistencia(
            id=uuid.uuid4(), persona_id=persona_79.id, sesion_id=uuid.uuid4(), estado="presente" if i < 29 else "falto"
        ))
    for _ in range(3):
        db_session.add(models.SpiritualMilestone(id=uuid.uuid4(), persona_id=persona_79.id, sede_id=sede_a.id, type="Milestone", event_date=date.today()))
    for i in range(4):
        db_session.add(models.CommunicationLog(id=uuid.uuid4(), persona_id=persona_79.id, channel="Call", content=f"C{i}", outcome="sent"))
    db_session.commit()
    score_79, status_79 = calculate_pastoral_health(db_session, persona_79.id)
    assert score_79 == 79
    assert status_79 == "ESTABLE"

    # Case D: Score exactly 80 (COMPROMETIDO)
    persona_80 = models.Persona(
        id=uuid.uuid4(), first_name="P80", last_name="Test", email="p80@example.com", sede_id=sede_a.id, is_baptized=False
    )
    db_session.add(persona_80)
    # Milestones = 30 (max), Comms = 20 (max). Need attendance = 30.
    # Opps = 50, Attended = 30 -> score = 30.
    for i in range(50):
        db_session.add(models.Asistencia(
            id=uuid.uuid4(), persona_id=persona_80.id, sesion_id=uuid.uuid4(), estado="presente" if i < 30 else "falto"
        ))
    for _ in range(3):
        db_session.add(models.SpiritualMilestone(id=uuid.uuid4(), persona_id=persona_80.id, sede_id=sede_a.id, type="Milestone", event_date=date.today()))
    for i in range(4):
        db_session.add(models.CommunicationLog(id=uuid.uuid4(), persona_id=persona_80.id, channel="Call", content=f"C{i}", outcome="sent"))
    db_session.commit()
    score_80, status_80 = calculate_pastoral_health(db_session, persona_80.id)
    assert score_80 == 80
    assert status_80 == "COMPROMETIDO"

    # Case E: Rounding behavior for .4 (down) and .5 (up)
    # persona_round_down: milestones = 30, comms = 0.
    # Need attendance score = 9.4 -> total = 39.4 -> rounds to 39.
    # Opps = 500, Attended = 94 -> 94/500 * 50 = 9.4.
    persona_round_down = models.Persona(
        id=uuid.uuid4(), first_name="RoundDown", last_name="Test", email="down@example.com", sede_id=sede_a.id, is_baptized=False
    )
    db_session.add(persona_round_down)
    for i in range(500):
        db_session.add(models.Asistencia(
            id=uuid.uuid4(), persona_id=persona_round_down.id, sesion_id=uuid.uuid4(), estado="presente" if i < 94 else "falto"
        ))
    for _ in range(3):
        db_session.add(models.SpiritualMilestone(id=uuid.uuid4(), persona_id=persona_round_down.id, sede_id=sede_a.id, type="Milestone", event_date=date.today()))
    db_session.commit()
    score_down, status_down = calculate_pastoral_health(db_session, persona_round_down.id)
    assert score_down == 39
    assert status_down == "EN_RIESGO"

    # persona_round_up: milestones = 30, comms = 0.
    # Need attendance score = 9.5 -> total = 39.5 -> rounds to 40.
    # Opps = 500, Attended = 95 -> 95/500 * 50 = 9.5.
    persona_round_up = models.Persona(
        id=uuid.uuid4(), first_name="RoundUp", last_name="Test", email="up@example.com", sede_id=sede_a.id, is_baptized=False
    )
    db_session.add(persona_round_up)
    for i in range(500):
        db_session.add(models.Asistencia(
            id=uuid.uuid4(), persona_id=persona_round_up.id, sesion_id=uuid.uuid4(), estado="presente" if i < 95 else "falto"
        ))
    for _ in range(3):
        db_session.add(models.SpiritualMilestone(id=uuid.uuid4(), persona_id=persona_round_up.id, sede_id=sede_a.id, type="Milestone", event_date=date.today()))
    db_session.commit()
    score_up, status_up = calculate_pastoral_health(db_session, persona_round_up.id)
    assert score_up == 40
    assert status_up == "ESTABLE"

    # 5. Multi-tenant Safety (Sede Isolation)
    # Create Sede B
    sede_b = models.Sede(
        id=uuid.uuid4(),
        nombre="Sede B",
        ciudad="Medellin",
        es_activa=True,
    )
    db_session.add(sede_b)
    db_session.commit()

    # Persona A in Sede A
    persona_a = models.Persona(
        id=uuid.uuid4(), first_name="Persona", last_name="A", email="persona_a@example.com", sede_id=sede_a.id, is_baptized=False
    )
    # Persona B in Sede B
    persona_b = models.Persona(
        id=uuid.uuid4(), first_name="Persona", last_name="B", email="persona_b@example.com", sede_id=sede_b.id, is_baptized=True
    )
    db_session.add_all([persona_a, persona_b])
    db_session.commit()

    # Add records for Persona B
    # 10 Asistencias (presente)
    for _ in range(10):
        db_session.add(models.Asistencia(id=uuid.uuid4(), persona_id=persona_b.id, sesion_id=uuid.uuid4(), estado="presente"))
    # 5 Milestones in Sede B
    for _ in range(5):
        db_session.add(models.SpiritualMilestone(id=uuid.uuid4(), persona_id=persona_b.id, sede_id=sede_b.id, type="Milestone", event_date=date.today()))
    # 5 Comm logs
    for i in range(5):
        db_session.add(models.CommunicationLog(id=uuid.uuid4(), persona_id=persona_b.id, channel="SMS", content="Test", outcome="sent"))
    db_session.commit()

    # Calculate pastoral health for Persona A (should remain unaffected: 0)
    score_a, status_a = calculate_pastoral_health(db_session, persona_a.id)
    assert score_a == 0
    assert status_a == "EN_RIESGO"

    # Calculate pastoral health for Persona B (milestones capped at 30, comms capped at 20, attendance 50 -> 100)
    score_b, status_b = calculate_pastoral_health(db_session, persona_b.id)
    assert score_b == 100
    assert status_b == "COMPROMETIDO"
