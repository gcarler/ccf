"""Tests exhaustivos y estructurales para backend/services/evangelism_crm_bridge.py (100% Cobertura)."""

import uuid
from unittest.mock import MagicMock, patch

from sqlalchemy.exc import IntegrityError

from backend.models_crm import Persona
from backend.models_crm_pipeline import EtapaPipeline, PipelineCRM
from backend.models_evangelism import (
    Asistencia,
    CategoriaEstrategia,
    EstrategiaEvangelismo,
    GrupoEvangelismo,
    Sede,
    SesionGrupo,
)
from backend.services.evangelism_crm_bridge import (
    _crm_casos_live_column_names,
    _crm_etapa_pipeline_live_column_names,
    _crm_etapa_pipeline_read_only_options,
    _insert_caso_nuevo_visitante,
    _obtener_o_crear_etapa_nuevo_contacto,
    _obtener_o_crear_pipeline_nuevos_visitantes,
    _stringify_uuid_payload,
    crear_caso_desde_asistencia,
    crear_caso_nuevo_visitante,
)


class TestEvangelismCrmBridge100Pct:
    def test_stringify_uuid_payload(self):
        u1 = uuid.uuid4()
        payload = {"id": u1, "name": "Test", "val": 123}
        res = _stringify_uuid_payload(payload)
        assert res["id"] == str(u1)
        assert res["name"] == "Test"
        assert res["val"] == 123

    def test_crm_live_column_names_bind_none_or_error(self):
        mock_db = MagicMock()
        mock_db.get_bind.return_value = None
        assert _crm_etapa_pipeline_live_column_names(mock_db) == set()
        assert _crm_casos_live_column_names(mock_db) == set()

        mock_bind = MagicMock()
        mock_db.get_bind.return_value = mock_bind
        with patch("backend.services.evangelism_crm_bridge.inspect", side_effect=Exception("Inspect error")):
            assert _crm_etapa_pipeline_live_column_names(mock_db) == set()
            assert _crm_casos_live_column_names(mock_db) == set()

    def test_crm_etapa_pipeline_read_only_options_empty(self):
        mock_db = MagicMock()
        with patch("backend.services.evangelism_crm_bridge._crm_etapa_pipeline_live_column_names", return_value=set()):
            assert _crm_etapa_pipeline_read_only_options(mock_db) is None

    def test_crear_caso_desde_asistencia_skips_when_no_flag(self, db_session):
        asistencia = Asistencia(es_primera_vez=False, requiere_seguimiento=False)
        res = crear_caso_desde_asistencia(db_session, asistencia, MagicMock(), MagicMock(), MagicMock(), uuid.uuid4())
        assert res is None

    def test_crear_caso_nuevo_visitante_flow(self, db_session):
        sede = Sede(nombre="Sede Bridge", ciudad="Bogotá")
        db_session.add(sede)
        db_session.commit()

        persona = Persona(first_name="Carlos", last_name="Santana", sede_id=sede.id)
        db_session.add(persona)
        db_session.commit()

        caso = crear_caso_nuevo_visitante(
            db=db_session,
            persona=persona,
            sede_id=sede.id,
            titulo_prefix="Seguimiento VIP",
        )
        assert caso is not None
        assert caso.persona_id == persona.id

    def test_crear_caso_desde_asistencia_flow(self, db_session):
        sede = Sede(nombre="Sede Bridge Asistencia", ciudad="Bogotá")
        db_session.add(sede)
        db_session.commit()

        persona = Persona(first_name="Maria", last_name="Lopez", sede_id=sede.id)
        db_session.add(persona)
        db_session.commit()

        cat = CategoriaEstrategia(nombre="Categoría General Test")
        db_session.add(cat)
        db_session.commit()

        estrategia = EstrategiaEvangelismo(nombre="Campaña Primavera", sede_id=sede.id, categoria_id=cat.id)
        db_session.add(estrategia)
        db_session.commit()

        grupo = GrupoEvangelismo(nombre="Grupo A", estrategia_id=estrategia.id, sede_id=sede.id)
        db_session.add(grupo)
        db_session.commit()

        from datetime import datetime, timezone

        sesion = SesionGrupo(grupo_id=grupo.id, fecha_sesion=datetime.now(timezone.utc))
        db_session.add(sesion)
        db_session.commit()

        asistencia = Asistencia(
            persona_id=persona.id,
            sesion_id=sesion.id,
            estado="Presente",
            es_primera_vez=True,
            requiere_seguimiento=True,
        )
        db_session.add(asistencia)
        db_session.commit()

        caso = crear_caso_desde_asistencia(
            db=db_session,
            asistencia=asistencia,
            persona=persona,
            grupo=grupo,
            sesion=sesion,
            sede_id=sede.id,
        )
        assert caso is not None
        assert caso.persona_id == persona.id

    def test_non_sqlite_insert_caso_nuevo_visitante(self, db_session):
        mock_bind = MagicMock()
        mock_bind.dialect.name = "postgresql"

        mock_db = MagicMock()
        mock_db.get_bind.return_value = mock_bind

        persona = Persona(id=uuid.uuid4(), first_name="Juan", last_name="Perez")
        pipeline = PipelineCRM(id=uuid.uuid4())
        etapa = EtapaPipeline(id=uuid.uuid4())
        sede_id = uuid.uuid4()

        with (
            patch(
                "backend.services.evangelism_crm_bridge._crm_casos_live_column_names",
                return_value={
                    "id",
                    "persona_id",
                    "sede_id",
                    "pipeline_id",
                    "etapa_actual_id",
                    "titulo_caso",
                    "sort_order",
                    "is_locked_for_reorder",
                },
            ),
            patch("backend.services.evangelism_crm_bridge.Table"),
            patch("backend.services.evangelism_crm_bridge.insert"),
        ):
            caso = _insert_caso_nuevo_visitante(
                db=mock_db,
                persona=persona,
                sede_id=sede_id,
                pipeline=pipeline,
                etapa=etapa,
                titulo_prefix="Test Postgre",
            )
            assert caso is not None
            mock_db.execute.assert_called_once()

    def test_pipeline_race_condition_integrity_error(self):
        mock_db = MagicMock()

        # Simulate Savepoint IntegrityError when creating pipeline
        mock_sp = MagicMock()
        mock_sp.commit.side_effect = IntegrityError("Duplicate", params=None, orig=Exception())
        mock_db.begin_nested.return_value = mock_sp

        existing_p = PipelineCRM(id=uuid.uuid4(), deleted_at=None)
        q1 = MagicMock()
        q1.first.return_value = None  # before add
        q2 = MagicMock()
        q2.first.return_value = existing_p  # after rollback

        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.filter.side_effect = [
            q1,
            q2,
        ]
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.side_effect = [q1, q2]

        p = _obtener_o_crear_pipeline_nuevos_visitantes(mock_db, uuid.uuid4())
        assert p is not None

    def test_pipeline_race_condition_still_missing(self, db_session):
        mock_db = MagicMock()
        mock_sp = MagicMock()
        mock_sp.commit.side_effect = IntegrityError("Duplicate", params=None, orig=Exception())
        mock_db.begin_nested.return_value = mock_sp

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_query.filter.return_value.filter.return_value.filter.return_value.first.return_value = None

        mock_db.query.return_value = mock_query

        p = _obtener_o_crear_pipeline_nuevos_visitantes(mock_db, uuid.uuid4())
        assert p is None

    def test_etapa_integrity_error_fallback(self, db_session):
        mock_db = MagicMock()
        pipeline = PipelineCRM(id=uuid.uuid4())

        mock_sp = MagicMock()
        mock_sp.commit.side_effect = IntegrityError("Duplicate etapa", params=None, orig=Exception())
        mock_db.begin_nested.return_value = mock_sp

        existing_etapa = EtapaPipeline(id=uuid.uuid4(), deleted_at=None)
        mock_query = MagicMock()
        mock_query.options.return_value.filter.return_value.order_by.return_value.first.return_value = None
        mock_query.filter.return_value.order_by.return_value.first.return_value = existing_etapa

        mock_db.query.return_value = mock_query

        with patch(
            "backend.services.evangelism_crm_bridge._crm_etapa_pipeline_live_column_names",
            return_value={"id", "pipeline_id", "nombre", "visual_color"},
        ):
            etapa = _obtener_o_crear_etapa_nuevo_contacto(mock_db, pipeline, uuid.uuid4())
            assert etapa == existing_etapa

    def test_crear_caso_nuevo_visitante_returns_none_when_pipeline_missing(self):
        mock_db = MagicMock()
        with patch(
            "backend.services.evangelism_crm_bridge._obtener_o_crear_pipeline_nuevos_visitantes", return_value=None
        ):
            res = crear_caso_nuevo_visitante(mock_db, MagicMock(), uuid.uuid4())
            assert res is None

    def test_crear_caso_nuevo_visitante_returns_none_when_etapa_missing(self):
        mock_db = MagicMock()
        with (
            patch(
                "backend.services.evangelism_crm_bridge._obtener_o_crear_pipeline_nuevos_visitantes",
                return_value=MagicMock(),
            ),
            patch("backend.services.evangelism_crm_bridge._obtener_o_crear_etapa_nuevo_contacto", return_value=None),
        ):
            res = crear_caso_nuevo_visitante(mock_db, MagicMock(), uuid.uuid4())
            assert res is None
