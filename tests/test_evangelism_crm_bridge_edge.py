"""Edge case tests for evangelism_crm_bridge.py — PG paths, IntegrityError, etc."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from backend import models
from backend.models_evangelism import Sede, Asistencia, GrupoEvangelismo, SesionGrupo
from backend.models_crm_pipeline import (
    PipelineCRM,
    EtapaPipeline,
    TipoPipelineEnum,
)
from backend.models_crm import Persona
from backend.services.evangelism_crm_bridge import (
    _crm_etapa_pipeline_live_column_names,
    _crm_casos_live_column_names,
    _crm_etapa_pipeline_read_only_options,
    _insert_caso_nuevo_visitante,
    _obtener_o_crear_pipeline_nuevos_visitantes,
    _obtener_o_crear_etapa_nuevo_contacto,
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
    p = Persona(id=uuid.uuid4(), first_name="Edge", last_name="Test", sede_id=sede.id)
    db_session.add(p)
    db_session.commit()
    return p


class TestLiveColumnNames:
    def test_etapa_bind_none(self):
        """Line 41: bind is None returns empty set."""
        mock_db = MagicMock()
        mock_db.get_bind.return_value = None
        result = _crm_etapa_pipeline_live_column_names(mock_db)
        assert result == set()

    def test_etapa_inspect_exception(self):
        """Line 44-45: inspect exception returns empty set."""
        mock_db = MagicMock()
        mock_bind = MagicMock()
        mock_db.get_bind.return_value = mock_bind
        with patch("backend.services.evangelism_crm_bridge.inspect", side_effect=Exception("no table")):
            result = _crm_etapa_pipeline_live_column_names(mock_db)
        assert result == set()

    def test_casos_bind_none(self):
        """Line 50-52: bind is None returns empty set."""
        mock_db = MagicMock()
        mock_db.get_bind.return_value = None
        result = _crm_casos_live_column_names(mock_db)
        assert result == set()


class TestReadOnlyOptions:
    def test_no_selectable_names(self):
        """Line 77: no selectable names returns None."""
        mock_db = MagicMock()
        mock_bind = MagicMock()
        mock_db.get_bind.return_value = mock_bind
        with patch("backend.services.evangelism_crm_bridge._crm_etapa_pipeline_live_column_names",
                   return_value=set()):
            result = _crm_etapa_pipeline_read_only_options(mock_db)
        assert result is None

class TestPipelineIntegrityError:
    def test_integrity_error_on_create(self, db_session, sede):
        """Cover IntegrityError path in _obtener_o_crear_pipeline_nuevos_visitantes."""
        # First create a pipeline so the query finds it
        existing = PipelineCRM(
            id=uuid.uuid4(), sede_id=sede.id, nombre="Nuevos Visitantes",
            tipo=TipoPipelineEnum.NUEVOS_VISITANTES, activo=True,
        )
        db_session.add(existing)
        db_session.commit()

        # Now mock db.add to raise IntegrityError, then the function should find existing
        with patch.object(db_session, "add") as mock_add:
            def mock_add_side_effect(obj):
                if hasattr(obj, 'tipo') and getattr(obj, 'tipo', None) == TipoPipelineEnum.NUEVOS_VISITANTES:
                    if getattr(obj, 'id', None) != existing.id:
                        raise IntegrityError("test", "test", "test")
            mock_add.side_effect = mock_add_side_effect

            pipeline = _obtener_o_crear_pipeline_nuevos_visitantes(db_session, sede.id)
            assert pipeline is not None
            # Should return the existing pipeline (not the one that failed)
            assert pipeline.id == existing.id


class TestEtapaIntegrityError:
    def test_integrity_error_returns_existing(self, db_session, sede):
        """Cover IntegrityError in _obtener_o_crear_etapa_nuevo_contacto."""
        pipeline = _obtener_o_crear_pipeline_nuevos_visitantes(db_session, sede.id)

        # First create an etapa normally
        etapa1 = _obtener_o_crear_etapa_nuevo_contacto(db_session, pipeline, sede.id)
        assert etapa1 is not None

        # Now mock begin_nested to raise IntegrityError, and the etapa exists already
        with patch.object(db_session, "begin_nested") as mock_bn:
            mock_sp = MagicMock()
            mock_bn.return_value.__enter__.return_value = mock_sp

            # Make the sp.commit raise IntegrityError
            def mock_commit():
                raise IntegrityError("test", "test", "test")
            mock_sp.commit.side_effect = mock_commit

            etapa2 = _obtener_o_crear_etapa_nuevo_contacto(db_session, pipeline, sede.id)
            assert etapa2 is not None
            assert etapa2.id == etapa1.id


class TestCrearCasoEdgeCases:
    def test_pipeline_none_skips(self, db_session, sede, persona):
        """Lines 385-386: pipeline creation fails -> return None."""
        g = GrupoEvangelismo(id=uuid.uuid4(), nombre="G", sede_id=sede.id, lider_persona_id=persona.id)
        db_session.add(g)
        db_session.flush()
        ses = SesionGrupo(id=uuid.uuid4(), grupo_id=g.id, fecha_sesion=datetime.now(timezone.utc), estado="REALIZADA")
        db_session.add(ses)
        db_session.flush()
        att = Asistencia(id=uuid.uuid4(), sesion_id=ses.id, persona_id=persona.id,
                        estado="first_time", es_primera_vez=True)

        with patch("backend.services.evangelism_crm_bridge._obtener_o_crear_pipeline_nuevos_visitantes",
                   return_value=None):
            result = crear_caso_desde_asistencia(db_session, att, persona, g, ses, sede.id)
            assert result is None

    def test_etapa_none_skips(self, db_session, sede, persona):
        """Lines 390-391: etapa creation fails -> return None."""
        g = GrupoEvangelismo(id=uuid.uuid4(), nombre="G", sede_id=sede.id, lider_persona_id=persona.id)
        db_session.add(g)
        db_session.flush()
        ses = SesionGrupo(id=uuid.uuid4(), grupo_id=g.id, fecha_sesion=datetime.now(timezone.utc), estado="REALIZADA")
        db_session.add(ses)
        db_session.flush()
        att = Asistencia(id=uuid.uuid4(), sesion_id=ses.id, persona_id=persona.id,
                        estado="first_time", es_primera_vez=True)

        with patch("backend.services.evangelism_crm_bridge._obtener_o_crear_etapa_nuevo_contacto",
                   return_value=None):
            result = crear_caso_desde_asistencia(db_session, att, persona, g, ses, sede.id)
            assert result is None

    def test_crear_caso_nuevo_pipeline_none(self, db_session, sede, persona):
        """Lines 422-423: pipeline None returns None."""
        with patch("backend.services.evangelism_crm_bridge._obtener_o_crear_pipeline_nuevos_visitantes",
                   return_value=None):
            result = crear_caso_nuevo_visitante(
                db=db_session, persona=persona, sede_id=sede.id,
            )
            assert result is None

    def test_crear_caso_nuevo_etapa_none(self, db_session, sede, persona):
        """Lines 427-428: etapa None returns None."""
        with patch("backend.services.evangelism_crm_bridge._obtener_o_crear_etapa_nuevo_contacto",
                   return_value=None):
            result = crear_caso_nuevo_visitante(
                db=db_session, persona=persona, sede_id=sede.id,
            )
            assert result is None
