"""Cover remaining IntegrityError paths in evangelism_crm_bridge.py."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from backend.models_evangelism import Sede
from backend.services.evangelism_crm_bridge import (
    _crm_casos_live_column_names,
    _obtener_o_crear_etapa_nuevo_contacto,
    _obtener_o_crear_pipeline_nuevos_visitantes,
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
    def test_bind_none(self):
        """Line 50-52: bind is None returns empty set."""
        mock_db = MagicMock()
        mock_db.get_bind.return_value = None
        result = _crm_casos_live_column_names(mock_db)
        assert result == set()

    def test_inspect_exception(self):
        """Lines 53-57: inspect exception returns empty set."""
        mock_db = MagicMock()
        mock_bind = MagicMock()
        mock_db.get_bind.return_value = mock_bind
        with patch("backend.services.evangelism_crm_bridge.inspect", side_effect=Exception("no table")):
            result = _crm_casos_live_column_names(mock_db)
        assert result == set()


class TestPipelineIntegrityError:
    def test_integrity_error_returns_none(self, db_session, sede):
        """Lines 224-237: IntegrityError during pipeline creation."""
        # Create a pipeline first so there's something in the DB
        from backend.models_crm_pipeline import PipelineCRM, TipoPipelineEnum

        existing = PipelineCRM(
            id=uuid.uuid4(),
            sede_id=sede.id,
            nombre="Nuevos Visitantes",
            tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
            activo=True,
        )
        db_session.add(existing)
        db_session.commit()

        # Mock begin_nested so its commit raises IntegrityError. El código real
        # hace `sp = db.begin_nested()` y luego `sp.commit()` (sin `with`), así
        # que el side_effect debe ir en mock_bn.return_value.commit.
        with patch.object(db_session, "begin_nested") as mock_bn:
            mock_bn.return_value.commit.side_effect = IntegrityError("test", "test", "test")

            # Mock the query to return None, forcing creation attempt. El código
            # real usa un solo .filter(...) con múltiples condiciones.
            original_query = db_session.query
            with patch.object(db_session, "query") as mock_query:
                # Primera consulta (pipeline inexistente) -> None; después del
                # IntegrityError -> devuelve el pipeline ya creado.
                mock_query.return_value.filter.return_value.first.side_effect = [
                    None,  # First call: no pipeline found -> try to create
                    existing,  # After IntegrityError: find the existing one
                ]
                # Evitar autoflush real: el add del pipeline nuevo en el try
                # no debe tocar la DB (si no, UNIQUE real contra `existing`).
                with patch.object(db_session, "add", return_value=None):
                    result = _obtener_o_crear_pipeline_nuevos_visitantes(db_session, sede.id)

        # Should find the existing pipeline (it exists, just the creation failed)
        assert result is not None
        assert result.id == existing.id


class TestEtapaIntegrityError:
    def test_integrity_error_fallback_to_existing(self, db_session, sede):
        """Lines 319-347: IntegrityError during etapa creation."""
        pipeline = _obtener_o_crear_pipeline_nuevos_visitantes(db_session, sede.id)

        # First, create an etapa normally
        etapa1 = _obtener_o_crear_etapa_nuevo_contacto(db_session, pipeline, sede.id)
        assert etapa1 is not None

        # Mock to force IntegrityError on a new creation attempt. El código real
        # usa `sp = db.begin_nested()` directo (sin `with`), así que el
        # side_effect va en mock_bn.return_value.commit.
        with patch.object(db_session, "begin_nested") as mock_bn:
            mock_bn.return_value.commit.side_effect = IntegrityError("test", "test", "test")

            # Mock query to return None first (no etapa found) then the existing one
            with patch.object(db_session, "query") as mock_query:
                mock_filter = MagicMock()

                # Contador a nivel de closure: el except crea un FakeQuery nuevo
                # y necesita saber que ya hubo una primera consulta.
                call_count = [0]

                def side_effect_first(model):
                    # First call (etapa query) -> return None
                    # Second call (after IntegrityError) -> return existing
                    class FakeQuery:
                        def filter(self, *a, **kw):
                            return self

                        def order_by(self, *a, **kw):
                            return self

                        def first(self):
                            call_count[0] += 1
                            if call_count[0] == 1:
                                return None
                            return etapa1

                        def options(self, *a, **kw):
                            return self

                        def all(self):
                            return []

                    return FakeQuery()

                mock_query.side_effect = side_effect_first
                # El add de la etapa nueva dentro del try dispararía autoflush
                # y chocaría con UNIQUE real (pipeline_id, orden) contra etapa1.
                with patch.object(db_session, "add", return_value=None):
                    etapa2 = _obtener_o_crear_etapa_nuevo_contacto(db_session, pipeline, sede.id)

        assert etapa2 is not None
        assert etapa2.id == etapa1.id
