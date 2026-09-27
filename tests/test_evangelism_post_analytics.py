"""Tests canónicos para Analytics Post-Evento, Embudo de Asistencia y Conversión CRM (TKT-EVT-ANALYTICS-03)."""

from __future__ import annotations

import datetime
import uuid
from datetime import timedelta, timezone

from backend import models
from backend.models_crm import Persona
from backend.models_crm_pipeline import CanalOrigenEnum, CasoCRM, EtapaPipeline, PipelineCRM, TipoPipelineEnum
from backend.models_evangelism import GrupoEvangelismo, ParticipanteGrupo
from tests.conftest import auth_headers, seed_admin, seed_user_with_role


def _seed_test_data(db, sede_id):
    """Seed helper para crear evento, personas y registros de prueba."""
    now_utc = datetime.datetime.now(timezone.utc)

    # 1. Evento de evangelismo con aforo 100
    event = models.CrmEvent(
        id=uuid.uuid4(),
        name="Gran Conferencia Evangelística Faro 2026",
        description="Evento masivo de cosecha y consolidación",
        event_type="SPECIAL",
        event_date=now_utc - timedelta(days=5),
        capacity_max=100,
        requires_registration=True,
        sede_id=sede_id,
        created_at=now_utc,
    )
    db.add(event)

    # 2. Pipeline y Etapas CRM
    pipeline = PipelineCRM(
        id=uuid.uuid4(),
        nombre="Consolidación Evangelismo",
        tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
        sede_id=sede_id,
        activo=True,
        created_at=now_utc,
    )
    db.add(pipeline)

    etapa1 = EtapaPipeline(
        id=uuid.uuid4(),
        pipeline_id=pipeline.id,
        nombre="Contacto Inicial",
        orden=1,
        created_at=now_utc,
    )
    etapa2 = EtapaPipeline(
        id=uuid.uuid4(),
        pipeline_id=pipeline.id,
        nombre="En Discipulado",
        orden=2,
        created_at=now_utc,
    )
    db.add_all([etapa1, etapa2])

    # 3. Grupo de Vida
    grupo = GrupoEvangelismo(
        id=uuid.uuid4(),
        nombre="Grupo de Vida Norte 01",
        codigo="GV-NORTE-01",
        sede_id=sede_id,
        activo=True,
        created_at=now_utc,
    )
    db.add(grupo)

    # 4. Cuatro personas con distintos perfiles
    # Persona 1: Nuevo Visitante, asistió, tiene caso CRM
    p1 = Persona(
        id=uuid.uuid4(),
        first_name="Carlos",
        last_name="Mendoza",
        email="carlos.mendoza@test.ccf",
        phone="+573001112233",
        church_role="Visitante Servicios",
        sede_id=sede_id,
        created_at=now_utc,
    )
    # Persona 2: Nuevo Visitante, asistió, en Grupo de Vida
    p2 = Persona(
        id=uuid.uuid4(),
        first_name="Diana",
        last_name="Gomez",
        email="diana.gomez@test.ccf",
        phone="+573002223344",
        church_role="Visitante Servicios",
        sede_id=sede_id,
        created_at=now_utc,
    )
    # Persona 3: Miembro activo, asistió (retenido)
    p3 = Persona(
        id=uuid.uuid4(),
        first_name="Esteban",
        last_name="Rios",
        email="esteban.rios@test.ccf",
        phone="+573003334455",
        church_role="Miembro",
        sede_id=sede_id,
        created_at=now_utc,
    )
    # Persona 4: Registrado pero NO asistió (No-show)
    p4 = Persona(
        id=uuid.uuid4(),
        first_name="Fabiola",
        last_name="Torres",
        email="fabiola.torres@test.ccf",
        phone="+573004445566",
        church_role="Visitante Servicios",
        sede_id=sede_id,
        created_at=now_utc,
    )
    # Persona 5: Walk-in (sin pre-registro)
    p5 = Persona(
        id=uuid.uuid4(),
        first_name="Gabriel",
        last_name="Navarro",
        email="gabriel.navarro@test.ccf",
        phone="+573005556677",
        church_role="Invitado",
        sede_id=sede_id,
        created_at=now_utc,
    )
    db.add_all([p1, p2, p3, p4, p5])

    # 5. Pre-registros
    reg1 = models.EventRegistration(
        id=uuid.uuid4(),
        event_id=event.id,
        persona_id=p1.id,
        registration_number=1,
        registration_status="CONFIRMED",
        check_in_at=now_utc - timedelta(days=5, hours=2),
        created_at=now_utc - timedelta(days=6),
    )
    reg2 = models.EventRegistration(
        id=uuid.uuid4(),
        event_id=event.id,
        persona_id=p2.id,
        registration_number=2,
        registration_status="CONFIRMED",
        check_in_at=now_utc - timedelta(days=5, hours=2),
        created_at=now_utc - timedelta(days=6),
    )
    reg3 = models.EventRegistration(
        id=uuid.uuid4(),
        event_id=event.id,
        persona_id=p3.id,
        registration_number=3,
        registration_status="CONFIRMED",
        check_in_at=now_utc - timedelta(days=5, hours=2),
        created_at=now_utc - timedelta(days=6),
    )
    reg4 = models.EventRegistration(
        id=uuid.uuid4(),
        event_id=event.id,
        persona_id=p4.id,
        registration_number=4,
        registration_status="CONFIRMED",
        check_in_at=None,
        created_at=now_utc - timedelta(days=6),
    )
    db.add_all([reg1, reg2, reg3, reg4])

    # 6. Walk-in de P5 mediante EventAttendance
    att5 = models.EventAttendance(
        id=uuid.uuid4(),
        event_id=event.id,
        persona_id=p5.id,
        session_date=(now_utc - timedelta(days=5)).date(),
        attended=True,
        check_in_at=now_utc - timedelta(days=5),
        scanned_at=now_utc - timedelta(days=5),
    )
    db.add(att5)

    # 7. Asignación de P2 a Grupo de Vida
    part2 = ParticipanteGrupo(
        id=uuid.uuid4(),
        grupo_id=grupo.id,
        persona_id=p2.id,
        rol_base="MIEMBRO",
        activo=True,
        fecha_ingreso=now_utc,
    )
    db.add(part2)

    # 8. Caso CRM para P1
    caso1 = CasoCRM(
        id=uuid.uuid4(),
        persona_id=p1.id,
        sede_id=sede_id,
        pipeline_id=pipeline.id,
        etapa_actual_id=etapa1.id,
        titulo_caso=f"Consolidación: {event.name}",
        origen_canal=CanalOrigenEnum.EVANGELISMO,
        origen_evento_id=event.id,
        fecha_creacion=now_utc,
    )
    db.add(caso1)

    db.commit()

    return {
        "event": event,
        "personas": [p1, p2, p3, p4, p5],
        "grupo": grupo,
        "pipeline": pipeline,
        "etapas": [etapa1, etapa2],
    }


def test_post_event_analytics_calculations(db_session, client):
    """Verifica métricas de asistencia real vs registrada, aforo y no-show."""
    admin, _, sede = seed_admin(db_session)
    data = _seed_test_data(db_session, sede.id)
    event_id = str(data["event"].id)

    headers = auth_headers(client)
    res = client.get(f"/api/evangelism/events/{event_id}/post-event-analytics", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()

    # Validar estructura y datos del evento
    assert body["event_id"] == event_id
    assert body["event_name"] == data["event"].name
    assert body["capacity_max"] == 100

    # Validar métricas de asistencia
    m = body["attendance_metrics"]
    # 4 registrados pre-evento (p1, p2, p3, p4) + p5 walk-in = 5 total convocados/efectivos
    assert m["total_attended"] == 4  # p1, p2, p3, p5 asistieron
    assert m["total_absent"] == 1  # p4 fue no-show
    assert m["total_walk_ins"] == 1  # p5
    assert m["attendance_rate"] > 0
    assert m["no_show_rate"] > 0
    assert m["capacity_utilization"] == 4.0  # 4 / 100 * 100 = 4.0%


def test_post_event_conversion_funnel(db_session, client):
    """Verifica que el embudo de conversión contenga las 6 etapas calculadas correctamente."""
    admin, _, sede = seed_admin(db_session)
    data = _seed_test_data(db_session, sede.id)
    event_id = str(data["event"].id)

    headers = auth_headers(client)
    res = client.get(f"/api/evangelism/events/{event_id}/post-event-analytics", headers=headers)
    assert res.status_code == 200
    body = res.json()

    funnel = body["conversion_funnel"]
    assert len(funnel) == 6

    stages = [f["stage_id"] for f in funnel]
    assert stages == [
        "registered",
        "attended",
        "new_visitors",
        "crm_consolidation",
        "life_groups",
        "retained_members",
    ]

    # Validar consistencia de cálculo
    for step in funnel:
        assert "count" in step
        assert "pct_of_total" in step
        assert "conversion_from_previous" in step
        assert "dropoff_from_previous" in step
        assert 0.0 <= step["pct_of_total"] <= 100.0


def test_post_event_visitor_retention_and_crm_breakdown(db_session, client):
    """Verifica el cálculo de retención de nuevos visitantes y el desglose de CRM."""
    admin, _, sede = seed_admin(db_session)
    data = _seed_test_data(db_session, sede.id)
    event_id = str(data["event"].id)

    headers = auth_headers(client)
    res = client.get(f"/api/evangelism/events/{event_id}/post-event-analytics", headers=headers)
    assert res.status_code == 200
    body = res.json()

    ret = body["visitor_retention"]
    assert ret["new_visitors_count"] >= 1
    assert "retained_30d_rate" in ret
    assert "health_status" in ret
    assert ret["health_status"] in ("EXCELLENT", "HEALTHY", "ATTENTION_NEEDED", "CRITICAL")

    crm_b = body["crm_breakdown"]
    assert crm_b["total_cases_created"] >= 1
    assert len(crm_b["cases_by_stage"]) > 0
    assert "pending_followup_count" in crm_b


def test_post_event_csv_export(db_session, client):
    """Verifica la exportación del reporte ejecutivo post-evento en CSV con UTF-8 BOM."""
    admin, _, sede = seed_admin(db_session)
    data = _seed_test_data(db_session, sede.id)
    event_id = str(data["event"].id)

    headers = auth_headers(client)
    res = client.get(f"/api/evangelism/events/{event_id}/export/post-event-analytics", headers=headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "attachment; filename=" in res.headers["content-disposition"]

    content = res.text
    # Validar BOM UTF-8 y encabezados
    assert content.startswith("\ufeff")
    assert "REPORTE EJECUTIVO POST-EVENTO" in content
    assert "EMBUDO DE CONVERSIÓN MINISTERIAL" in content
    assert "DETALLE DE ASISTENTES Y SEGUIMIENTO PASTORAL" in content
    assert "Carlos Mendoza" in content


def test_pastoral_executive_summary(db_session, client):
    """Verifica el endpoint de resumen ejecutivo transversal para pastores."""
    admin, _, sede = seed_admin(db_session)
    _seed_test_data(db_session, sede.id)

    headers = auth_headers(client)
    res = client.get("/api/evangelism/events/pastoral-executive-summary", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()

    assert "sede_id" in body
    assert "kpis" in body
    assert body["kpis"]["total_events"] >= 1
    assert "total_attended" in body["kpis"]
    assert "event_summaries" in body
    assert len(body["event_summaries"]) >= 1


def test_channel_attendees_to_crm_idempotent(db_session, client):
    """Verifica la canalización masiva y selectiva a CRM con idempotencia y auditoría."""
    admin, _, sede = seed_admin(db_session)
    data = _seed_test_data(db_session, sede.id)
    event_id = str(data["event"].id)
    headers = auth_headers(client)

    # 1. Canalizar asistentes que aún no tienen caso (p2 y p5)
    res = client.post(
        f"/api/evangelism/events/{event_id}/crm-channel",
        json={},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["success"] is True
    assert body["created_cases"] >= 1

    # 2. Segunda ejecución (debe ser idempotente, 0 duplicados)
    res2 = client.post(
        f"/api/evangelism/events/{event_id}/crm-channel",
        json={},
        headers=headers,
    )
    assert res2.status_code == 200
    assert res2.json()["created_cases"] == 0


def test_post_event_analytics_tenant_isolation(db_session, client):
    """Axioma 3: Una sede ajena no puede acceder a analítica post-evento de otra sede."""
    admin1, _, sede1 = seed_admin(db_session)
    data = _seed_test_data(db_session, sede1.id)
    event_id = str(data["event"].id)

    # Crear admin en otra sede
    other_sede = models.Sede(id=uuid.uuid4(), nombre="Sede Barranquilla", ciudad="Barranquilla", es_activa=True)
    db_session.add(other_sede)
    db_session.commit()

    seed_user_with_role(
        db_session,
        role_name="SUPER_ADMIN",
        email="pastor.baq@ccf.com",
        password="password123",
        sede_id=other_sede.id,
    )

    headers_other = auth_headers(client, email="pastor.baq@ccf.com", password="password123")
    res = client.get(f"/api/evangelism/events/{event_id}/post-event-analytics", headers=headers_other)
    assert res.status_code in (403, 404)

