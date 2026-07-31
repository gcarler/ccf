"""Tests for evangelism_crm_bridge.py — crm case creation from evangelism."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.models_crm import Persona
from backend.models_crm_pipeline import (
    EtapaPipeline,
    PipelineCRM,
    TipoPipelineEnum,
)
from backend.models_evangelism import Asistencia, GrupoEvangelismo, Sede, SesionGrupo
from backend.services.evangelism_crm_bridge import (
    _build_transient_caso,
    _insert_caso_nuevo_visitante,
    _obtener_o_crear_etapa_nuevo_contacto,
    _obtener_o_crear_pipeline_nuevos_visitantes,
    _stringify_uuid_payload,
    crear_caso_desde_asistencia,
    crear_caso_nuevo_visitante,
)


@pytest.fixture
def sede(db_session):
    s = db_session.query(Sede).first()
    if not s:
        s = Sede(id=uuid.uuid4(), nombre="Test", ciudad="Test", es_activa=True)
        db_session.add(s)
        db_session.commit()
    return s


@pytest.fixture
def persona(db_session, sede):
    p = Persona(id=uuid.uuid4(), first_name="Visit", last_name="Test", sede_id=sede.id)
    db_session.add(p)
    db_session.commit()
    return p


# ── Unit: _stringify_uuid_payload ─────────────────────────────────────────────


class TestStringifyUUIDPayload:
    def test_converts_uuids(self):
        uid = uuid.uuid4()
        result = _stringify_uuid_payload({"id": uid, "name": "test"})
        assert result["id"] == str(uid)
        assert result["name"] == "test"

    def test_preserves_non_uuid(self):
        result = _stringify_uuid_payload({"a": 1, "b": "hello"})
        assert result == {"a": 1, "b": "hello"}

    def test_empty_dict(self):
        assert _stringify_uuid_payload({}) == {}


# ── Unit: _build_transient_caso ───────────────────────────────────────────────


class TestBuildTransientCaso:
    def test_builds_caso(self, db_session, sede, persona):
        """Build a transient CasoCRM object (not persisted yet)."""
        pipeline = PipelineCRM(
            id=uuid.uuid4(),
            sede_id=sede.id,
            nombre="Test Pipeline",
            tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
            activo=True,
        )
        db_session.add(pipeline)
        db_session.flush()

        etapa = EtapaPipeline(
            id=uuid.uuid4(),
            pipeline_id=pipeline.id,
            nombre="Nuevo",
            orden=1,
            requiere_accion=True,
        )
        db_session.add(etapa)
        db_session.flush()

        caso = _build_transient_caso(
            caso_id=uuid.uuid4(),
            persona_id=persona.id,
            sede_id=sede.id,
            pipeline_id=pipeline.id,
            etapa=etapa,
            titulo_caso="Test: Visit Test",
            origen_grupo_id=None,
            origen_estrategia_id=None,
            origen_sesion_id=None,
            sla_vencimiento_contacto=datetime.now(timezone.utc) + timedelta(hours=48),
        )

        assert caso.persona_id == persona.id
        assert caso.sede_id == sede.id
        assert caso.pipeline_id == pipeline.id
        assert caso.etapa_actual_id == etapa.id
        assert caso.etapa_actual == etapa
        assert caso.titulo_caso == "Test: Visit Test"


# ── Integration: pipeline lifecycle ────────────────────────────────────────────


class TestPipelineLifecycle:
    def test_obtener_o_crear_pipeline_new(self, db_session, sede):
        pipeline = _obtener_o_crear_pipeline_nuevos_visitantes(db_session, sede.id)
        assert pipeline is not None
        assert pipeline.tipo == TipoPipelineEnum.NUEVOS_VISITANTES
        assert pipeline.sede_id == sede.id

    def test_obtener_o_crear_pipeline_existing(self, db_session, sede):
        existing = PipelineCRM(
            id=uuid.uuid4(),
            sede_id=sede.id,
            nombre="Nuevos Visitantes",
            tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
            activo=True,
        )
        db_session.add(existing)
        db_session.commit()

        pipeline = _obtener_o_crear_pipeline_nuevos_visitantes(db_session, sede.id)
        assert pipeline is not None
        assert pipeline.id == existing.id


class TestEtapaLifecycle:
    def test_obtener_o_crear_etapa_new(self, db_session, sede):
        pipeline = _obtener_o_crear_pipeline_nuevos_visitantes(db_session, sede.id)
        etapa = _obtener_o_crear_etapa_nuevo_contacto(db_session, pipeline, sede.id)
        assert etapa is not None
        assert etapa.nombre == "Nuevo Contacto"
        assert etapa.pipeline_id == pipeline.id

    def test_obtener_o_crear_etapa_existing(self, db_session, sede):
        pipeline = _obtener_o_crear_pipeline_nuevos_visitantes(db_session, sede.id)
        etapa1 = _obtener_o_crear_etapa_nuevo_contacto(db_session, pipeline, sede.id)
        etapa2 = _obtener_o_crear_etapa_nuevo_contacto(db_session, pipeline, sede.id)
        assert etapa2 is not None
        assert etapa2.id == etapa1.id


# ── Integration: insert caso ──────────────────────────────────────────────────


class TestInsertCaso:
    def test_insert_caso_sqlite_path(self, db_session, sede, persona):
        pipeline = _obtener_o_crear_pipeline_nuevos_visitantes(db_session, sede.id)
        etapa = _obtener_o_crear_etapa_nuevo_contacto(db_session, pipeline, sede.id)

        caso = _insert_caso_nuevo_visitante(
            db=db_session,
            persona=persona,
            sede_id=sede.id,
            pipeline=pipeline,
            etapa=etapa,
            titulo_prefix="Consolidar",
            origen_grupo_id=None,
            origen_estrategia_id=None,
            origen_sesion_id=None,
        )
        assert caso is not None
        assert caso.persona_id == persona.id
        assert isinstance(caso.id, uuid.UUID)

        db_session.refresh(caso)
        assert caso.deleted_at is None


# ── Integration: crear_caso from attendance ────────────────────────────────────


class TestCrearCasoDesdeAsistencia:
    def test_skip_if_not_first_time(self, db_session, sede, persona):
        g = GrupoEvangelismo(id=uuid.uuid4(), nombre="G", sede_id=sede.id, lider_persona_id=persona.id)
        db_session.add(g)
        db_session.flush()
        ses = SesionGrupo(id=uuid.uuid4(), grupo_id=g.id, fecha_sesion=datetime.now(timezone.utc), estado="REALIZADA")
        db_session.add(ses)
        db_session.flush()
        att = Asistencia(id=uuid.uuid4(), sesion_id=ses.id, persona_id=persona.id, estado="ASISTIO")

        result = crear_caso_desde_asistencia(db_session, att, persona, g, ses, sede.id)
        assert result is None

    def test_creates_caso_for_first_time(self, db_session, sede, persona):
        g = GrupoEvangelismo(id=uuid.uuid4(), nombre="G", sede_id=sede.id, lider_persona_id=persona.id)
        db_session.add(g)
        db_session.flush()
        ses = SesionGrupo(id=uuid.uuid4(), grupo_id=g.id, fecha_sesion=datetime.now(timezone.utc), estado="REALIZADA")
        db_session.add(ses)
        db_session.flush()
        att = Asistencia(
            id=uuid.uuid4(), sesion_id=ses.id, persona_id=persona.id, estado="first_time", es_primera_vez=True
        )

        result = crear_caso_desde_asistencia(db_session, att, persona, g, ses, sede.id)
        assert result is not None
        assert result.origen_canal is not None


class TestCrearCasoNuevoVisitante:
    def test_creates_caso(self, db_session, sede, persona):
        result = crear_caso_nuevo_visitante(
            db=db_session,
            persona=persona,
            sede_id=sede.id,
            titulo_prefix="Seguimiento",
            origen_grupo_id=None,
            origen_estrategia_id=None,
            origen_sesion_id=None,
        )
        assert result is not None
        assert result.persona_id == persona.id
        assert result.sede_id == sede.id
        assert "Seguimiento" in result.titulo_caso
