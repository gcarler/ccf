import uuid
from datetime import date, datetime, timezone
import pytest
from backend import models
from backend.crud.crm_.health import calculate_pastoral_health, update_pastoral_health
from tests.conftest import seed_admin

def test_zero_attendance_opportunities(db_session):
    """Verify health score when a persona has 0 attendance opportunities but various milestone and communication inputs."""
    _, admin_persona, sede = seed_admin(db_session)
    
    # Persona A: No baptism, 0 opportunities, 0 milestones, 0 communications
    persona_a = models.Persona(
        id=uuid.uuid4(),
        first_name="Zero",
        last_name="TestA",
        email="zero_a@example.com",
        sede_id=sede.id,
        is_baptized=False
    )
    db_session.add(persona_a)
    db_session.commit()
    
    score, status = calculate_pastoral_health(db_session, persona_a.id)
    assert score == 0
    assert status == "EN_RIESGO"
    
    # Persona B: Baptized (+1 milestone point = 10 score), 0 opportunities, 0 milestones, 0 communications
    persona_b = models.Persona(
        id=uuid.uuid4(),
        first_name="Zero",
        last_name="TestB",
        email="zero_b@example.com",
        sede_id=sede.id,
        is_baptized=True
    )
    db_session.add(persona_b)
    db_session.commit()
    
    score, status = calculate_pastoral_health(db_session, persona_b.id)
    assert score == 10
    assert status == "EN_RIESGO"

    # Persona C: Baptized (+10), 3 milestones (+30, capped at 30 total milestone score), 4 communication logs (+20, capped at 20)
    # Total score should be 0 (attendance) + 30 (milestones) + 20 (comms) = 50. Status: ESTABLE
    persona_c = models.Persona(
        id=uuid.uuid4(),
        first_name="Zero",
        last_name="TestC",
        email="zero_c@example.com",
        sede_id=sede.id,
        is_baptized=True
    )
    db_session.add(persona_c)
    db_session.commit()
    
    for i in range(3):
        m = models.SpiritualMilestone(
            id=uuid.uuid4(), persona_id=persona_c.id, sede_id=sede.id, type=f"Type {i}", event_date=date.today()
        )
        db_session.add(m)
    for i in range(4):
        c = models.CommunicationLog(
            id=uuid.uuid4(), persona_id=persona_c.id, channel="WhatsApp", content=f"Msg {i}", outcome="sent"
        )
        db_session.add(c)
    db_session.commit()
    
    score, status = calculate_pastoral_health(db_session, persona_c.id)
    assert score == 50
    assert status == "ESTABLE"


def test_extreme_and_large_inputs(db_session):
    """Verify that very large inputs do not cause overflows and are capped correctly."""
    _, admin_persona, sede = seed_admin(db_session)
    
    persona = models.Persona(
        id=uuid.uuid4(),
        first_name="Large",
        last_name="Inputs",
        email="large_inputs@example.com",
        sede_id=sede.id,
        is_baptized=True
    )
    db_session.add(persona)
    db_session.commit()
    
    # Add 1,000 opportunities (500 present, 500 absent) -> attendance score = 25.0
    for i in range(500):
        a1 = models.Asistencia(id=uuid.uuid4(), persona_id=persona.id, sesion_id=uuid.uuid4(), estado="presente")
        a2 = models.Asistencia(id=uuid.uuid4(), persona_id=persona.id, sesion_id=uuid.uuid4(), estado="falto")
        db_session.add_all([a1, a2])
    db_session.commit()
    
    # Add 50 milestones (should cap milestone score to 30)
    for i in range(50):
        m = models.SpiritualMilestone(
            id=uuid.uuid4(), persona_id=persona.id, sede_id=sede.id, type=f"Type {i}", event_date=date.today()
        )
        db_session.add(m)
        
    # Add 100 communication logs (should cap communication score to 20)
    for i in range(100):
        c = models.CommunicationLog(
            id=uuid.uuid4(), persona_id=persona.id, channel="WhatsApp", content=f"Msg {i}", outcome="sent"
        )
        db_session.add(c)
    db_session.commit()
    
    score, status = calculate_pastoral_health(db_session, persona.id)
    # Expected: attendance = 25.0, milestone = 30, comm = 20. Total = 75. Status = ESTABLE
    assert score == 75
    assert status == "ESTABLE"


def test_attendance_status_normalization_and_mix(db_session):
    """Test mixed attendance statuses and normalization logic for Asistencia, EventAttendance, CourseAttendance."""
    _, admin_persona, sede = seed_admin(db_session)
    
    persona = models.Persona(
        id=uuid.uuid4(),
        first_name="Status",
        last_name="Mix",
        email="status_mix@example.com",
        sede_id=sede.id,
        is_baptized=False
    )
    db_session.add(persona)
    db_session.commit()
    
    # 1. Asistencia statuses
    # Normalizations: lowercase, stripped. Supported: "asistio", "presente", "present", "primera_vez", "first_time"
    db_session.add_all([
        models.Asistencia(id=uuid.uuid4(), persona_id=persona.id, sesion_id=uuid.uuid4(), estado="  presente  "),
        models.Asistencia(id=uuid.uuid4(), persona_id=persona.id, sesion_id=uuid.uuid4(), estado="ASISTIO"),
        models.Asistencia(id=uuid.uuid4(), persona_id=persona.id, sesion_id=uuid.uuid4(), estado="present"),
        models.Asistencia(id=uuid.uuid4(), persona_id=persona.id, sesion_id=uuid.uuid4(), estado="PRIMERA_VEZ"),
        models.Asistencia(id=uuid.uuid4(), persona_id=persona.id, sesion_id=uuid.uuid4(), estado="first_time"),
        # Opps but not attended:
        models.Asistencia(id=uuid.uuid4(), persona_id=persona.id, sesion_id=uuid.uuid4(), estado="falto"),
        models.Asistencia(id=uuid.uuid4(), persona_id=persona.id, sesion_id=uuid.uuid4(), estado="ausente"),
        models.Asistencia(id=uuid.uuid4(), persona_id=persona.id, sesion_id=uuid.uuid4(), estado="excusa"),
        models.Asistencia(id=uuid.uuid4(), persona_id=persona.id, sesion_id=uuid.uuid4(), estado="  "),
    ])
    
    # 2. EventAttendance statuses
    db_session.add_all([
        models.EventAttendance(id=uuid.uuid4(), persona_id=persona.id, event_id=uuid.uuid4(), session_date=date.today(), status="present", attended=True),
        models.EventAttendance(id=uuid.uuid4(), persona_id=persona.id, event_id=uuid.uuid4(), session_date=date.today(), status="absent", attended=False),
        # Note: attended=None triggers Column default=True in SQLAlchemy, so we explicitly use attended=False here for the unattended check
        models.EventAttendance(id=uuid.uuid4(), persona_id=persona.id, event_id=uuid.uuid4(), session_date=date.today(), status="unknown", attended=False),
    ])
    
    # 3. CourseAttendance statuses via Enrollment
    course_id = uuid.uuid4()
    enrollment = models.Enrollment(id=uuid.uuid4(), persona_id=persona.id, course_id=course_id, status="active")
    db_session.add(enrollment)
    db_session.commit()
    
    db_session.add_all([
        models.CourseAttendance(id=uuid.uuid4(), enrollment_id=enrollment.id, session_date=datetime.now(timezone.utc), status="  present  "),
        models.CourseAttendance(id=uuid.uuid4(), enrollment_id=enrollment.id, session_date=datetime.now(timezone.utc), status="PRESENT"),
        models.CourseAttendance(id=uuid.uuid4(), enrollment_id=enrollment.id, session_date=datetime.now(timezone.utc), status="absent"),
        models.CourseAttendance(id=uuid.uuid4(), enrollment_id=enrollment.id, session_date=datetime.now(timezone.utc), status="tardy"),
    ])
    db_session.commit()
    
    # Calculate:
    # Asistencia: 9 opportunities, 5 attended.
    # EventAttendance: 3 opportunities, 1 attended.
    # CourseAttendance: 4 opportunities, 2 attended.
    # Total opportunities = 9 + 3 + 4 = 16.
    # Total attended = 5 + 1 + 2 = 8.
    # Attendance score = 8 / 16 * 50 = 25.0
    score, status = calculate_pastoral_health(db_session, persona.id)
    assert score == 25
    assert status == "EN_RIESGO"


def test_boundaries_and_rounding(db_session):
    """Test boundary scores, capping, and banker's vs standard rounding effects on status transitions."""
    _, admin_persona, sede = seed_admin(db_session)
    
    # Milestones = 30, Comms = 0.
    # We want total score = 39.4 -> round(39.4) = 39.
    # Need attendance score = 9.4 -> 47 / 250 * 50.
    persona_under = models.Persona(id=uuid.uuid4(), first_name="Under", last_name="Bound", email="under@example.com", sede_id=sede.id, is_baptized=False)
    db_session.add(persona_under)
    for _ in range(3):
        db_session.add(models.SpiritualMilestone(id=uuid.uuid4(), persona_id=persona_under.id, sede_id=sede.id, type="Milestone", event_date=date.today()))
    for i in range(250):
        estado = "presente" if i < 47 else "falto"
        db_session.add(models.Asistencia(id=uuid.uuid4(), persona_id=persona_under.id, sesion_id=uuid.uuid4(), estado=estado))
    db_session.commit()
    
    score_under, status_under = calculate_pastoral_health(db_session, persona_under.id)
    assert score_under == 39
    assert status_under == "EN_RIESGO"
    
    # We want total score = 39.5 -> round(39.5) = 40.
    # Need attendance score = 9.5 -> 19 / 100 * 50.
    persona_exact = models.Persona(id=uuid.uuid4(), first_name="Exact", last_name="Bound", email="exact@example.com", sede_id=sede.id, is_baptized=False)
    db_session.add(persona_exact)
    for _ in range(3):
        db_session.add(models.SpiritualMilestone(id=uuid.uuid4(), persona_id=persona_exact.id, sede_id=sede.id, type="Milestone", event_date=date.today()))
    for i in range(100):
        estado = "presente" if i < 19 else "falto"
        db_session.add(models.Asistencia(id=uuid.uuid4(), persona_id=persona_exact.id, sesion_id=uuid.uuid4(), estado=estado))
    db_session.commit()
    
    score_exact, status_exact = calculate_pastoral_health(db_session, persona_exact.id)
    assert score_exact == 40
    assert status_exact == "ESTABLE"
    
    # We want total score = 79.4 -> round(79.4) = 79.
    # Need attendance score = 29.4 -> 147 / 250 * 50. Milestones = 30, Comms = 20.
    persona_stable_high = models.Persona(id=uuid.uuid4(), first_name="StableHigh", last_name="Bound", email="stablehigh@example.com", sede_id=sede.id, is_baptized=False)
    db_session.add(persona_stable_high)
    for _ in range(3):
        db_session.add(models.SpiritualMilestone(id=uuid.uuid4(), persona_id=persona_stable_high.id, sede_id=sede.id, type="Milestone", event_date=date.today()))
    for _ in range(4):
        db_session.add(models.CommunicationLog(id=uuid.uuid4(), persona_id=persona_stable_high.id, channel="Call", content="Test", outcome="sent"))
    for i in range(250):
        estado = "presente" if i < 147 else "falto"
        db_session.add(models.Asistencia(id=uuid.uuid4(), persona_id=persona_stable_high.id, sesion_id=uuid.uuid4(), estado=estado))
    db_session.commit()
    
    score_sh, status_sh = calculate_pastoral_health(db_session, persona_stable_high.id)
    assert score_sh == 79
    assert status_sh == "ESTABLE"

    # We want total score = 79.5 -> round(79.5) = 80.
    # Need attendance score = 29.5 -> 59 / 100 * 50. Milestones = 30, Comms = 20.
    persona_comp = models.Persona(id=uuid.uuid4(), first_name="Comp", last_name="Bound", email="comp@example.com", sede_id=sede.id, is_baptized=False)
    db_session.add(persona_comp)
    for _ in range(3):
        db_session.add(models.SpiritualMilestone(id=uuid.uuid4(), persona_id=persona_comp.id, sede_id=sede.id, type="Milestone", event_date=date.today()))
    for _ in range(4):
        db_session.add(models.CommunicationLog(id=uuid.uuid4(), persona_id=persona_comp.id, channel="Call", content="Test", outcome="sent"))
    for i in range(100):
        estado = "presente" if i < 59 else "falto"
        db_session.add(models.Asistencia(id=uuid.uuid4(), persona_id=persona_comp.id, sesion_id=uuid.uuid4(), estado=estado))
    db_session.commit()
    
    score_comp, status_comp = calculate_pastoral_health(db_session, persona_comp.id)
    assert score_comp == 80
    assert status_comp == "COMPROMETIDO"


def test_multi_tenant_and_cross_persona_isolation(db_session):
    """Verify that there is no leakage of attendance, milestone, or communication records across different Personas or Sedes."""
    _, admin_persona, sede_a = seed_admin(db_session, email="admin_a@example.com")
    
    # Create Sede B
    sede_b = models.Sede(id=uuid.uuid4(), nombre="Sede B", ciudad="Medellin", es_activa=True)
    db_session.add(sede_b)
    db_session.commit()
    
    # Persona A in Sede A
    persona_a = models.Persona(
        id=uuid.uuid4(),
        first_name="Persona",
        last_name="A",
        email="persona_a@example.com",
        sede_id=sede_a.id,
        is_baptized=False
    )
    # Persona B in Sede B
    persona_b = models.Persona(
        id=uuid.uuid4(),
        first_name="Persona",
        last_name="B",
        email="persona_b@example.com",
        sede_id=sede_b.id,
        is_baptized=False
    )
    db_session.add_all([persona_a, persona_b])
    db_session.commit()
    
    # 1. Add records to Persona B (milestones, attendance, comm logs, CRM case/interaction)
    # Attendance for B: 2 opportunities, 2 attended
    db_session.add(models.Asistencia(id=uuid.uuid4(), persona_id=persona_b.id, sesion_id=uuid.uuid4(), estado="presente"))
    db_session.add(models.EventAttendance(id=uuid.uuid4(), persona_id=persona_b.id, event_id=uuid.uuid4(), session_date=date.today(), status="present", attended=True))
    # Milestones for B: 2 active milestones
    db_session.add(models.SpiritualMilestone(id=uuid.uuid4(), persona_id=persona_b.id, sede_id=sede_b.id, type="Milestone1", event_date=date.today()))
    db_session.add(models.SpiritualMilestone(id=uuid.uuid4(), persona_id=persona_b.id, sede_id=sede_b.id, type="Milestone2", event_date=date.today()))
    # Comm logs for B: 2 logs
    db_session.add(models.CommunicationLog(id=uuid.uuid4(), persona_id=persona_b.id, channel="WhatsApp", content="Hello B", outcome="sent"))
    db_session.add(models.CommunicationLog(id=uuid.uuid4(), persona_id=persona_b.id, channel="Email", content="Hello B", outcome="sent"))
    # CRM interactions for B: 1 case with 1 interaction
    pipeline = models.PipelineCRM(id=uuid.uuid4(), sede_id=sede_b.id, nombre="Pipeline B", tipo="NUEVOS_VISITANTES")
    etapa = models.EtapaPipeline(id=uuid.uuid4(), pipeline_id=pipeline.id, nombre="Etapa B", orden=1)
    db_session.add_all([pipeline, etapa])
    db_session.commit()
    
    caso = models.CasoCRM(id=uuid.uuid4(), persona_id=persona_b.id, sede_id=sede_b.id, pipeline_id=pipeline.id, etapa_actual_id=etapa.id, titulo_caso="Caso B", origen_canal="WEB_FORM")
    db_session.add(caso)
    db_session.commit()
    
    interact = models.InteraccionCRM(id=uuid.uuid4(), caso_id=caso.id, realizado_por_id=admin_persona.id, tipo="LLAMADA_OUTBOUND", resumen="Interaccion B")
    db_session.add(interact)
    db_session.commit()
    
    # Calculate for Persona A: should be exactly 0 (no records linked to Persona A)
    score_a, status_a = calculate_pastoral_health(db_session, persona_a.id)
    assert score_a == 0
    assert status_a == "EN_RIESGO"
    
    # Calculate for Persona B:
    # Attendance: 2 opps, 2 attended -> 50 score
    # Milestones: 2 milestones -> 20 score
    # Communication: 2 logs + 1 interaction = 3 * 5 = 15 score
    # Total = 50 + 20 + 15 = 85. Status = COMPROMETIDO
    score_b, status_b = calculate_pastoral_health(db_session, persona_b.id)
    assert score_b == 85
    assert status_b == "COMPROMETIDO"
