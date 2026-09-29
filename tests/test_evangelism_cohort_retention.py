"""Pruebas de Calidad para Cohortes de Retención, LTV Espiritual y Auditoría Pastoral Multi-Sede.

TKT-EVT-COHORT-RETENTION-05 (Fase 5 Super-PRO Evangelismo):
- Valida motor analítico de cohortes temporales (30d, 60d, 90d post-evento).
- Valida retención en Grupos de Vida y Academia.
- Valida cálculo de Spiritual Maturity Index (SMI / LTV Espiritual) e hitos.
- Valida auditoría pastoral comparativa multi-sede y rankings (Axioma 3).
- Valida matriz temporal de cohortes mes a mes.
- Valida exportación ejecutiva en CSV con UTF-8 BOM.
- Valida endpoints REST vía TestClient.
"""

from __future__ import annotations

import datetime
import uuid
from datetime import timedelta, timezone

from backend import models
from backend.models_academy_core import Course, Enrollment
from backend.models_crm import Persona
from backend.models_evangelism import Asistencia, GrupoEvangelismo, Sede, SesionGrupo
from backend.services.event_cohort_retention_service import (
    calculate_event_cohort_retention,
    calculate_multi_sede_cohort_analysis,
    calculate_temporal_cohort_matrix,
    export_cohort_pastoral_report_csv,
    get_attendee_spiritual_journey,
)
from tests.conftest import auth_headers, seed_admin


def _seed_cohort_test_scenario(db):
    now = datetime.datetime.now(timezone.utc)

    # 1. Crear 2 Sedes
    sede_bogota = Sede(
        id=uuid.uuid4(),
        nombre="Sede Central Bogotá",
        ciudad="Bogotá",
        es_activa=True,
    )
    sede_medellin = Sede(
        id=uuid.uuid4(),
        nombre="Sede Medellín Poblado",
        ciudad="Medellín",
        es_activa=True,
    )
    db.add_all([sede_bogota, sede_medellin])
    db.flush()

    # 2. Evento en Bogotá (hace 45 días)
    event_bogota = models.CrmEvent(
        id=uuid.uuid4(),
        name="Cruzada Evangelística Bogotá",
        event_date=now - timedelta(days=45),
        location="Auditorio Central",
        sede_id=sede_bogota.id,
        event_type="SPECIAL",
        status="PUBLISHED",
        requires_registration=True,
        capacity_max=300,
    )
    # Evento en Medellín (hace 60 días)
    event_medellin = models.CrmEvent(
        id=uuid.uuid4(),
        name="Gran Fiesta de la Cosecha Medellín",
        event_date=now - timedelta(days=60),
        location="Centro de Convenciones",
        sede_id=sede_medellin.id,
        event_type="SPECIAL",
        status="PUBLISHED",
        requires_registration=True,
        capacity_max=200,
    )
    db.add_all([event_bogota, event_medellin])
    db.flush()

    # 3. Grupos de Vida y Sesiones
    grupo_bogota = GrupoEvangelismo(
        id=uuid.uuid4(),
        nombre="Grupo de Vida Cedritos",
        sede_id=sede_bogota.id,
        activo=True,
    )
    db.add(grupo_bogota)
    db.flush()

    # Sesión a los 10 días del evento de Bogotá
    sesion_10d = SesionGrupo(
        id=uuid.uuid4(),
        grupo_id=grupo_bogota.id,
        fecha_sesion=event_bogota.event_date + timedelta(days=10),
        estado="realizada",
    )
    # Sesión a los 40 días del evento de Bogotá
    sesion_40d = SesionGrupo(
        id=uuid.uuid4(),
        grupo_id=grupo_bogota.id,
        fecha_sesion=event_bogota.event_date + timedelta(days=40),
        estado="realizada",
    )
    db.add_all([sesion_10d, sesion_40d])
    db.flush()

    # 4. Curso de Academia
    uid_str = uuid.uuid4().hex[:6]
    curso_discipulado = Course(
        id=uuid.uuid4(),
        code=f"DISC-{uid_str}",
        slug=f"discipulado-{uid_str}",
        title="Discipulado Fundamental Nivel 1",
        description="Fundamentos bíblicos y doctrinales",
        modality="online",
    )
    db.add(curso_discipulado)
    db.flush()

    # 5. Asistentes en Bogotá
    # Asistente 1: Creció, asistió a grupo (10d y 40d), se bautizó, entró a academia -> SMI alto
    p1 = Persona(
        id=uuid.uuid4(),
        first_name="Alejandro",
        last_name="Torres",
        email="alejandro.torres@email.com",
        phone="+573101112233",
        sede_id=sede_bogota.id,
        is_baptized=True,
        baptism_date=datetime.date.today(),
        spiritual_status="Consolidado",
        church_role="Servidor",
    )
    # Asistente 2: Solo asistió a grupo a los 10d
    p2 = Persona(
        id=uuid.uuid4(),
        first_name="Beatriz",
        last_name="Pinzón",
        email="beatriz.pinzon@email.com",
        phone="+573104445566",
        sede_id=sede_bogota.id,
        is_baptized=False,
        spiritual_status="Nuevo",
        church_role="Visitante",
    )
    # Asistente 3: No asistió a grupos, solo vino al evento
    p3 = Persona(
        id=uuid.uuid4(),
        first_name="Camilo",
        last_name="Sesto",
        email="camilo.sesto@email.com",
        phone="+573107778899",
        sede_id=sede_bogota.id,
        is_baptized=False,
        spiritual_status="Nuevo",
        church_role="Visitante",
    )
    db.add_all([p1, p2, p3])
    db.flush()

    # Registros con check-in en Bogotá
    for p in [p1, p2, p3]:
        r = models.EventRegistration(
            id=uuid.uuid4(),
            event_id=event_bogota.id,
            persona_id=p.id,
            registration_status="CHECKED_IN",
            check_in_at=event_bogota.event_date,
        )
        db.add(r)
    db.flush()

    # Asistencias a grupo para p1 (10d y 40d)
    a1 = Asistencia(sesion_id=sesion_10d.id, persona_id=p1.id, estado="presente")
    a2 = Asistencia(sesion_id=sesion_40d.id, persona_id=p1.id, estado="presente")
    # Asistencia a grupo para p2 (10d)
    a3 = Asistencia(sesion_id=sesion_10d.id, persona_id=p2.id, estado="presente")
    db.add_all([a1, a2, a3])

    # Inscripción en academia para p1
    enr1 = Enrollment(
        id=uuid.uuid4(),
        persona_id=p1.id,
        course_id=curso_discipulado.id,
        status="completed",
        approved=True,
    )
    db.add(enr1)

    # 6. Asistente en Medellín (solo 1 asistente con check-in)
    p_med = Persona(
        id=uuid.uuid4(),
        first_name="Mateo",
        last_name="Restrepo",
        email="mateo.restrepo@email.com",
        phone="+573209990011",
        sede_id=sede_medellin.id,
        spiritual_status="Creyente",
    )
    db.add(p_med)
    db.flush()
    r_med = models.EventRegistration(
        id=uuid.uuid4(),
        event_id=event_medellin.id,
        persona_id=p_med.id,
        registration_status="CHECKED_IN",
        check_in_at=event_medellin.event_date,
    )
    db.add(r_med)
    db.commit()

    return {
        "sede_bogota": sede_bogota,
        "sede_medellin": sede_medellin,
        "event_bogota": event_bogota,
        "event_medellin": event_medellin,
        "p1": p1,
        "p2": p2,
        "p3": p3,
        "p_med": p_med,
    }


def test_event_cohort_retention_calculation(db_session):
    """Verifica el cálculo de retención 30d, 60d, 90d y Spiritual Maturity Index (SMI)."""
    data = _seed_cohort_test_scenario(db_session)
    event_bogota = data["event_bogota"]

    cohort_result = calculate_event_cohort_retention(db_session, event_bogota)

    # 3 asistentes con check-in
    assert cohort_result["total_cohort_size"] == 3

    # Retención a 30 días: p1 y p2 asistieron a sesión a los 10 días -> 2 de 3 = 66.7%
    ret_30 = cohort_result["retention_metrics"]["day_30"]
    assert ret_30["count"] == 2
    assert ret_30["percentage"] == 66.7

    # Retención a 60 días: p1 asistió a sesión a los 40 días -> al menos 1
    ret_60 = cohort_result["retention_metrics"]["day_60"]
    assert ret_60["count"] >= 1

    # Resumen de LTV Espiritual
    ltv = cohort_result["spiritual_ltv_summary"]
    assert ltv["baptism_rate_pct"] > 0
    assert ltv["academy_rate_pct"] > 0
    assert ltv["avg_spiritual_maturity_score"] > 0

    # P1 debe tener el mayor score de madurez (bautizado, academia, servidor, grupo)
    attendees = cohort_result["attendees_cohort"]
    assert len(attendees) == 3
    p1_data = next(a for a in attendees if a["persona_id"] == str(data["p1"].id))
    assert p1_data["spiritual_maturity_score"] >= 80.0
    assert p1_data["maturity_level"] == "MULTIPLICADOR"


def test_multi_sede_cohort_analysis(db_session):
    """Verifica la auditoría pastoral multi-sede y el ranking de efectividad pastoral."""
    data = _seed_cohort_test_scenario(db_session)

    multi_sede_result = calculate_multi_sede_cohort_analysis(db_session)

    kpis = multi_sede_result["global_kpis"]
    assert kpis["total_sedes"] >= 2
    assert kpis["total_cohort_size"] == 4  # 3 Bogotá + 1 Medellín
    assert kpis["avg_retention_30d_pct"] > 0

    ranking = multi_sede_result["sedes_ranking"]
    assert len(ranking) >= 2
    # Cada sede debe tener asignado su rank_position
    assert ranking[0]["rank_position"] == 1
    assert ranking[1]["rank_position"] == 2
    assert "pastoral_efficiency_score" in ranking[0]


def test_temporal_cohort_matrix(db_session):
    """Verifica la generación de la matriz de cohortes temporales mensual."""
    data = _seed_cohort_test_scenario(db_session)
    sede_bogota = data["sede_bogota"]

    matrix_result = calculate_temporal_cohort_matrix(db_session, sede_id=sede_bogota.id, months_count=3)

    assert "cohorts" in matrix_result
    assert len(matrix_result["cohorts"]) == 3
    for c in matrix_result["cohorts"]:
        assert "m1_30d" in c
        assert "m2_60d" in c
        assert "m3_90d" in c


def test_attendee_spiritual_journey(db_session):
    """Verifica el endpoint de historial y línea de tiempo espiritual del asistente."""
    data = _seed_cohort_test_scenario(db_session)
    p1 = data["p1"]

    journey = get_attendee_spiritual_journey(db_session, p1.id)

    assert journey["persona_id"] == str(p1.id)
    assert journey["spiritual_maturity_score"] >= 80.0
    assert journey["maturity_level"] == "MULTIPLICADOR"
    assert journey["events_attended_count"] >= 1
    assert journey["group_meetings_attended_count"] >= 2
    assert journey["academy_courses_count"] >= 1
    assert len(journey["milestones"]) >= 4


def test_export_cohort_pastoral_report_csv(db_session):
    """Verifica que el reporte exportable incluya UTF-8 BOM y todas las secciones ejecutivas."""
    _seed_cohort_test_scenario(db_session)

    csv_data = export_cohort_pastoral_report_csv(db_session)

    # Debe iniciar con el UTF-8 Byte Order Mark para compatibilidad con Excel
    assert csv_data.startswith("\ufeff")
    assert "COMUNIDAD CRISTIANA EL FARO" in csv_data
    assert "RESUMEN EJECUTIVO GLOBAL" in csv_data
    assert "RANKING Y AUDITORÍA PASTORAL INTER-SEDES" in csv_data
    assert "MATRIZ TEMPORAL DE RETENCIÓN POR COHORTES MENSUALES" in csv_data


def test_cohort_endpoints_via_client(client, db_session):
    """Verifica los endpoints REST de cohortes con TestClient y autenticación."""
    data = _seed_cohort_test_scenario(db_session)
    event_bogota = data["event_bogota"]
    sede_bogota = data["sede_bogota"]

    admin_user, _, _ = seed_admin(db_session)
    admin_user.sede_id = sede_bogota.id
    db_session.flush()
    headers = auth_headers(client)

    # 1. GET /api/evangelism/events/{event_id}/cohort-retention
    res1 = client.get(
        f"/api/evangelism/events/{event_bogota.id}/cohort-retention",
        headers=headers,
    )
    assert res1.status_code == 200, res1.text
    body1 = res1.json()
    assert body1["total_cohort_size"] == 3
    assert "retention_metrics" in body1

    # 2. GET /api/evangelism/cohorts/multi-sede
    res2 = client.get(
        "/api/evangelism/cohorts/multi-sede",
        headers=headers,
    )
    assert res2.status_code == 200, res2.text
    body2 = res2.json()
    assert "global_kpis" in body2
    assert "sedes_ranking" in body2

    # 3. GET /api/evangelism/cohorts/matrix
    res3 = client.get(
        "/api/evangelism/cohorts/matrix?months=4",
        headers=headers,
    )
    assert res3.status_code == 200, res3.text
    body3 = res3.json()
    assert "cohorts" in body3

    # 4. GET /api/evangelism/cohorts/attendees/{persona_id}/spiritual-journey
    res4 = client.get(
        f"/api/evangelism/cohorts/attendees/{data['p1'].id}/spiritual-journey",
        headers=headers,
    )
    assert res4.status_code == 200, res4.text
    body4 = res4.json()
    assert body4["spiritual_maturity_score"] >= 80.0

    # 5. GET /api/evangelism/cohorts/export
    res5 = client.get(
        "/api/evangelism/cohorts/export",
        headers=headers,
    )
    assert res5.status_code == 200, res5.text
    assert res5.headers["content-type"].startswith("text/csv")
    assert "attachment" in res5.headers["content-disposition"]
