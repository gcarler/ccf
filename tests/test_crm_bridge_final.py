"""Final push for evangelism_crm_bridge.py — remaining uncovered lines."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from backend.models_evangelism import Sede
from backend.services.evangelism_crm_bridge import (
    _crm_casos_live_column_names,
)


@pytest.fixture
def sede(db_session):
    s = db_session.query(Sede).first()
    if not s:
        s = Sede(id=uuid.uuid4(), nombre="Test", ciudad="Test", es_activa=True)
        db_session.add(s)
        db_session.commit()
    return s


class TestCrmCasosLiveColumnNames:
    def test_success_path(self, db_session):
        """Line 57: returns column names from real DB."""
        result = _crm_casos_live_column_names(db_session)
        assert isinstance(result, set)

    def test_exception_path(self):
        """Lines 55-56: inspect exception returns empty set."""
        mock_db = MagicMock()
        mock_bind = MagicMock()
        mock_db.get_bind.return_value = mock_bind
        with patch("backend.services.evangelism_crm_bridge.inspect", side_effect=Exception("no table")):
            result = _crm_casos_live_column_names(mock_db)
        assert result == set()


class TestPipelineIntegrityErrorFinal:
    def _run_pipeline_integrity_test(self, db_session, sede, pipeline_return):
        """Helper to test pipeline IntegrityError path."""
        from backend.models_crm_pipeline import PipelineCRM, TipoPipelineEnum
        from backend.services.evangelism_crm_bridge import _obtener_o_crear_pipeline_nuevos_visitantes

        # Create pipeline so it exists in DB (needed for the query-after-error path)
        p1 = PipelineCRM(
            id=uuid.uuid4(),
            sede_id=sede.id,
            nombre="Nuevos Visitantes",
            tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
            activo=True,
        )
        db_session.add(p1)
        db_session.commit()

        # El código real usa `sp = db.begin_nested()` directo (sin `with`), así
        # que el side_effect del commit va en mock_bn.return_value.commit.
        with patch.object(db_session, "begin_nested") as mock_bn:
            mock_bn.return_value.commit.side_effect = IntegrityError("test", "test", "test")

            # Make the query return pipeline_return (None or p1) after IntegrityError
            original_query = db_session.query

            def query_side_effect(*args, **kwargs):
                class FakeQuery:
                    def filter(self, *a, **kw):
                        return self

                    def first(self):
                        return pipeline_return

                return FakeQuery()

            # El add del pipeline nuevo dentro del try dispararía autoflush y
            # chocaría con UNIQUE real (sede_id, tipo) contra p1; se mockea para
            # que el camino de error sea puro (sin tocar la DB).
            with patch.object(db_session, "query", side_effect=query_side_effect), \
                    patch.object(db_session, "add", return_value=None):
                return _obtener_o_crear_pipeline_nuevos_visitantes(db_session, sede.id)

    def test_integrity_error_pipeline_found(self, db_session, sede):
        """Lines 224-241: IntegrityError, pipeline found after rollback."""
        from backend.models_crm_pipeline import PipelineCRM

        result = self._run_pipeline_integrity_test(
            db_session,
            sede,
            PipelineCRM(
                id=uuid.uuid4(),
                sede_id=sede.id,
                nombre="Nuevos Visitantes",
                tipo=None,
                activo=True,
            ),
        )
        assert result is not None

    def test_integrity_error_pipeline_not_found(self, db_session, sede):
        """Line 236: pipeline still missing after IntegrityError -> return None."""
        result = self._run_pipeline_integrity_test(db_session, sede, None)
        assert result is None


class TestEtapaIntegrityErrorFinal:
    def test_integrity_error_returns_existing(self, db_session, sede):
        """Cover etapa IntegrityError + fallback paths (lines 319-365)."""
        from backend.services.evangelism_crm_bridge import (
            _obtener_o_crear_etapa_nuevo_contacto,
            _obtener_o_crear_pipeline_nuevos_visitantes,
        )

        # Create pipeline
        pipeline = _obtener_o_crear_pipeline_nuevos_visitantes(db_session, sede.id)
        assert pipeline is not None

        # Create an etapa so it exists
        etapa1 = _obtener_o_crear_etapa_nuevo_contacto(db_session, pipeline, sede.id)
        assert etapa1 is not None

        # Now mock begin_nested to raise IntegrityError. El código real usa
        # `sp = db.begin_nested()` directo (sin `with`), así que el side_effect
        # va en mock_bn.return_value.commit.
        with patch.object(db_session, "begin_nested") as mock_bn:
            mock_bn.return_value.commit.side_effect = IntegrityError("test", "test", "test")

            # Mock query to return None first (no etapa), then existing
            call_count = [0]

            def query_side_effect(*args, **kwargs):
                class FakeQuery:
                    def filter(self, *a, **kw):
                        return self

                    def order_by(self, *a, **kw):
                        return self

                    def options(self, *a, **kw):
                        return self

                    def first(self):
                        call_count[0] += 1
                        if call_count[0] == 1:
                            return None  # first call: no etapa found
                        return etapa1  # after IntegrityError: existing

                return FakeQuery()

            # El add de la etapa nueva dentro del try dispararía autoflush y
            # chocaría con UNIQUE real (pipeline_id, orden) contra etapa1.
            with patch.object(db_session, "query", side_effect=query_side_effect), \
                    patch.object(db_session, "add", return_value=None):
                etapa2 = _obtener_o_crear_etapa_nuevo_contacto(db_session, pipeline, sede.id)

        assert etapa2 is not None
        assert etapa2.id == etapa1.id

    def test_integrity_error_etapa_not_found(self, db_session, sede):
        """Lines 342-365: etapa still missing after error -> warning."""
        from backend.services.evangelism_crm_bridge import (
            _obtener_o_crear_etapa_nuevo_contacto,
            _obtener_o_crear_pipeline_nuevos_visitantes,
        )

        pipeline = _obtener_o_crear_pipeline_nuevos_visitantes(db_session, sede.id)
        assert pipeline is not None

        # El código real usa `sp = db.begin_nested()` directo (sin `with`), así
        # que el side_effect del commit va en mock_bn.return_value.commit.
        with patch.object(db_session, "begin_nested") as mock_bn:
            mock_bn.return_value.commit.side_effect = IntegrityError("test", "test", "test")

            # All queries return None. El código real consulta primero
            # _crm_etapa_pipeline_read_only_options (options()) y después
            # filter().order_by().first(); el mock debe cubrir esa cadena.
            with patch.object(db_session, "query") as mock_query:
                mock_query.return_value.options.return_value.filter.return_value.order_by.return_value.first.return_value = None
                mock_query.return_value.filter.return_value.order_by.return_value.first.return_value = None

                result = _obtener_o_crear_etapa_nuevo_contacto(db_session, pipeline, sede.id)

        assert result is None
