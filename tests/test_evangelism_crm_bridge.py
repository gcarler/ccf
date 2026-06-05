from datetime import datetime, timedelta, timezone
import uuid

import pytest

from backend import models
from backend.services.evangelism_projection import proyectar_sesiones, FRECUENCIAS
from tests.conftest import seed_admin_v2, auth_headers_v2
from backend.services.evangelism_crm_bridge import (
    crear_caso_desde_asistencia,
    _obtener_o_crear_pipeline_nuevos_visitantes,
)
from backend.models_crm_core import (
    TipoPipelineEnum,
    EstadoCasoEnum,
    PrioridadCasoEnum,
    CanalOrigenEnum,
)


def _seed_sede(db_session):
    sede = models.Sede(nombre="Sede Test", ciudad="Bogota", es_activa=True)
    db_session.add(sede)
    db_session.commit()
    db_session.refresh(sede)
    return sede


def _seed_categoria(db_session):
    cat = models.CategoriaEstrategia(nombre="Test Cat", descripcion="desc")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


def test_proyectar_sesiones_semanal_2_meses(db_session):
    sede = _seed_sede(db_session)
    cat = _seed_categoria(db_session)

    fecha_inicio = datetime(2026, 1, 1, tzinfo=timezone.utc)
    fecha_fin = datetime(2026, 2, 19, tzinfo=timezone.utc)

    estrategia = models.EstrategiaEvangelismo(
        id=str(uuid.uuid4()),
        nombre="Proyeccion Test",
        categoria_id=cat.id,
        sede_id=sede.id,
        frecuencia="Semanal",
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        activa=True,
    )
    db_session.add(estrategia)
    db_session.commit()

    grupo = models.GrupoEvangelismo(
        estrategia_id=estrategia.id,
        sede_id=sede.id,
        nombre="Grupo Proyeccion",
        activo=True,
    )
    db_session.add(grupo)
    db_session.commit()

    count = proyectar_sesiones(
        db=db_session,
        estrategia_id=estrategia.id,
        sede_id=sede.id,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        frecuencia="Semanal",
        grupos_ids=[grupo.id],
    )
    assert count == 8

    sesiones = (
        db_session.query(models.SesionGrupo)
        .filter(models.SesionGrupo.grupo_id == grupo.id)
        .all()
    )
    assert len(sesiones) == 8
    for s in sesiones:
        assert s.estado == "PENDIENTE"


def test_asistencia_primera_vez_crea_caso_crm(db_session):
    sede = _seed_sede(db_session)
    cat = _seed_categoria(db_session)

    persona = models.Persona(first_name="Visitante", last_name="Nuevo", sede_id=sede.id)
    db_session.add(persona)
    db_session.commit()

    estrategia = models.EstrategiaEvangelismo(
        id=str(uuid.uuid4()),
        nombre="Test",
        categoria_id=cat.id,
        sede_id=sede.id,
        frecuencia="Semanal",
        activa=True,
    )
    db_session.add(estrategia)
    db_session.commit()

    grupo = models.GrupoEvangelismo(
        estrategia_id=estrategia.id,
        sede_id=sede.id,
        nombre="Grupo 1",
        activo=True,
    )
    db_session.add(grupo)
    db_session.commit()

    sesion = models.SesionGrupo(
        grupo_id=grupo.id,
        fecha_sesion=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
        estado="PENDIENTE",
        estado_habilitacion="HABILITADO",
    )
    db_session.add(sesion)
    db_session.commit()

    asistencia = models.Asistencia(
        sesion_id=sesion.id,
        persona_id=persona.id,
        estado="ASISTIO",
        es_primera_vez=True,
        requiere_seguimiento=False,
    )
    db_session.add(asistencia)
    db_session.commit()

    caso = crear_caso_desde_asistencia(db_session, asistencia, persona, grupo, sesion, sede.id)
    assert caso is not None
    assert caso.titulo_caso == "Consolidar: Visitante Nuevo"
    assert caso.prioridad == PrioridadCasoEnum.ALTA
    assert caso.estado == EstadoCasoEnum.ABIERTO
    assert caso.origen_canal == CanalOrigenEnum.EVANGELISMO
    assert caso.sla_vencimiento_contacto is not None


def test_asistencia_requiere_seguimiento_crea_caso_crm(db_session):
    sede = _seed_sede(db_session)
    cat = _seed_categoria(db_session)

    persona = models.Persona(first_name="Seguimiento", last_name="Req", sede_id=sede.id)
    db_session.add(persona)
    db_session.commit()

    estrategia = models.EstrategiaEvangelismo(
        id=str(uuid.uuid4()),
        nombre="Test",
        categoria_id=cat.id,
        sede_id=sede.id,
        frecuencia="Semanal",
        activa=True,
    )
    db_session.add(estrategia)
    db_session.commit()

    grupo = models.GrupoEvangelismo(
        estrategia_id=estrategia.id,
        sede_id=sede.id,
        nombre="Grupo 2",
        activo=True,
    )
    db_session.add(grupo)
    db_session.commit()

    sesion = models.SesionGrupo(
        grupo_id=grupo.id,
        fecha_sesion=datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc),
        estado="PENDIENTE",
    )
    db_session.add(sesion)
    db_session.commit()

    asistencia = models.Asistencia(
        sesion_id=sesion.id,
        persona_id=persona.id,
        estado="ASISTIO",
        es_primera_vez=False,
        requiere_seguimiento=True,
    )
    db_session.add(asistencia)
    db_session.commit()

    caso = crear_caso_desde_asistencia(db_session, asistencia, persona, grupo, sesion, sede.id)
    assert caso is not None
    assert caso.origen_canal == CanalOrigenEnum.EVANGELISMO


def test_persona_tags_actualizados(db_session):
    sede = _seed_sede(db_session)
    cat = _seed_categoria(db_session)

    persona = models.Persona(first_name="Tag", last_name="Test", sede_id=sede.id)
    db_session.add(persona)
    db_session.commit()

    estrategia = models.EstrategiaEvangelismo(
        id=str(uuid.uuid4()),
        nombre="Test",
        categoria_id=cat.id,
        sede_id=sede.id,
        frecuencia="Semanal",
        activa=True,
    )
    db_session.add(estrategia)
    db_session.commit()

    grupo = models.GrupoEvangelismo(
        estrategia_id=estrategia.id,
        sede_id=sede.id,
        nombre="Grupo Tags",
        activo=True,
    )
    db_session.add(grupo)
    db_session.commit()

    sesion = models.SesionGrupo(
        grupo_id=grupo.id,
        fecha_sesion=datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc),
        estado="PENDIENTE",
    )
    db_session.add(sesion)
    db_session.commit()

    asistencia = models.Asistencia(
        sesion_id=sesion.id,
        persona_id=persona.id,
        estado="ASISTIO",
        es_primera_vez=True,
    )
    db_session.add(asistencia)
    db_session.commit()

    caso = crear_caso_desde_asistencia(db_session, asistencia, persona, grupo, sesion, sede.id)
    assert caso is not None

    # Simulate the tag update logic from the endpoint
    tags_nuevos = [
        f"VISITANTE_ESTRATEGIA_{estrategia.id}",
        f"GRUPO_{grupo.nombre}",
        f"SESION_{sesion.fecha_sesion.date().isoformat()}",
    ]
    persona.tags = list(set((persona.tags or []) + tags_nuevos))
    persona.origen_estrategia_id = estrategia.id
    persona.origen_grupo_id = grupo.id
    persona.origen_fecha = datetime.now(timezone.utc)
    persona.spiritual_status = "VISITANTE_EVANGELISMO"
    db_session.commit()
    db_session.refresh(persona)

    assert f"VISITANTE_ESTRATEGIA_{estrategia.id}" in persona.tags
    assert "GRUPO_Grupo Tags" in persona.tags
    assert f"SESION_{sesion.fecha_sesion.date().isoformat()}" in persona.tags
    assert persona.spiritual_status == "VISITANTE_EVANGELISMO"
    assert str(persona.origen_estrategia_id) == estrategia.id
    assert persona.origen_grupo_id == grupo.id


def test_sla_calculado_correctamente(db_session):
    sede = _seed_sede(db_session)
    cat = _seed_categoria(db_session)

    persona = models.Persona(first_name="SLA", last_name="Test", sede_id=sede.id)
    db_session.add(persona)
    db_session.commit()

    estrategia = models.EstrategiaEvangelismo(
        id=str(uuid.uuid4()),
        nombre="Test",
        categoria_id=cat.id,
        sede_id=sede.id,
        frecuencia="Semanal",
        activa=True,
    )
    db_session.add(estrategia)
    db_session.commit()

    grupo = models.GrupoEvangelismo(
        estrategia_id=estrategia.id,
        sede_id=sede.id,
        nombre="Grupo SLA",
        activo=True,
    )
    db_session.add(grupo)
    db_session.commit()

    sesion = models.SesionGrupo(
        grupo_id=grupo.id,
        fecha_sesion=datetime(2026, 6, 4, 10, 0, tzinfo=timezone.utc),
        estado="PENDIENTE",
    )
    db_session.add(sesion)
    db_session.commit()

    asistencia = models.Asistencia(
        sesion_id=sesion.id,
        persona_id=persona.id,
        estado="ASISTIO",
        es_primera_vez=True,
    )
    db_session.add(asistencia)
    db_session.commit()

    now = datetime.now(timezone.utc)
    caso = crear_caso_desde_asistencia(db_session, asistencia, persona, grupo, sesion, sede.id)
    assert caso is not None
    assert caso.sla_vencimiento_contacto is not None
    sla = caso.sla_vencimiento_contacto
    if sla.tzinfo is None:
        sla = sla.replace(tzinfo=timezone.utc)
    diff = sla - now
    assert timedelta(hours=47) < diff < timedelta(hours=49)


def test_pipeline_creado_automaticamente_si_no_existe(db_session):
    sede = _seed_sede(db_session)

    pipeline = (
        db_session.query(models.PipelineCRM)
        .filter(
            models.PipelineCRM.sede_id == sede.id,
            models.PipelineCRM.tipo == TipoPipelineEnum.NUEVOS_VISITANTES,
        )
        .first()
    )
    assert pipeline is None

    pipeline = _obtener_o_crear_pipeline_nuevos_visitantes(db_session, sede.id)
    assert pipeline is not None
    assert pipeline.tipo == TipoPipelineEnum.NUEVOS_VISITANTES
    assert pipeline.activo is True

    etapas = (
        db_session.query(models.EtapaPipeline)
        .filter(models.EtapaPipeline.pipeline_id == pipeline.id)
        .all()
    )
    assert len(etapas) == 1
    assert etapas[0].nombre == "Nuevo Contacto"


def test_pipeline_reutilizado_si_ya_existe(db_session):
    sede = _seed_sede(db_session)

    pipeline1 = _obtener_o_crear_pipeline_nuevos_visitantes(db_session, sede.id)
    pipeline2 = _obtener_o_crear_pipeline_nuevos_visitantes(db_session, sede.id)
    assert pipeline1.id == pipeline2.id


def test_respuesta_json_estructura_correcta(client, db_session):
    admin, _admin_persona, sede = seed_admin_v2(db_session)
    cat = _seed_categoria(db_session)

    persona = models.Persona(first_name="Visitante", last_name="Nuevo", sede_id=sede.id)
    db_session.add(persona)
    db_session.commit()

    estrategia = models.EstrategiaEvangelismo(
        id=str(uuid.uuid4()),
        nombre="Test",
        categoria_id=cat.id,
        sede_id=sede.id,
        frecuencia="Semanal",
        activa=True,
    )
    db_session.add(estrategia)
    db_session.commit()

    grupo = models.GrupoEvangelismo(
        estrategia_id=estrategia.id,
        sede_id=sede.id,
        nombre="Grupo Int",
        activo=True,
    )
    db_session.add(grupo)
    db_session.commit()

    sesion = models.SesionGrupo(
        grupo_id=grupo.id,
        fecha_sesion=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
        estado="PENDIENTE",
        estado_habilitacion="HABILITADO",
    )
    db_session.add(sesion)
    db_session.commit()

    headers = auth_headers_v2(client)

    response = client.post(
        f"/api/evangelism/sessions/{sesion.id}/attendance",
        json=[{"persona_id": str(persona.id), "status": "first_time"}],
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "evento_integracion" in data
    assert data["metadata"]["engine"] == "Mesh CCF"
    assert data["metadata"]["trazabilidad"] == "AUTOMATIC_EVENT_TRIGGER_SUCCESS"

    evento = data["evento_integracion"]
    assert evento is not None
    assert evento["origen_modulo"] == "EVANGELISMO"
    assert evento["grupo_id"] == str(grupo.id)
    assert evento["sesion_id"] == str(sesion.id)

    visitante = evento["visitante_kernel"]
    assert visitante["persona_id"] == str(persona.id)
    assert visitante["nombre"] == "Visitante Nuevo"
    assert visitante["rol_iglesia"] == "VISITANTE_EVANGELISMO"
    assert any(f"VISITANTE_ESTRATEGIA_{estrategia.id}" in t for t in visitante["tags_aplicados"])

    crm = evento["crm_consolidacion"]
    assert crm["pipeline"] == "NUEVOS_VISITANTES"
    assert crm["etapa_inicial"] == "Nuevo Contacto"
    assert crm["SLA_limite_horas"] == 48
    assert crm["sla_deadline"] is not None
