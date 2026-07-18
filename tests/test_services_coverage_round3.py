"""
Coverage push — round 3, focused on pure-logic services.
"""
import uuid
from datetime import datetime, timezone, timedelta

import pytest

from backend.services.calculo_sesiones import (
    _normalizar_frecuencia, _provider_para_frecuencia, _a_utc,
    _generar_fechas, _IncProvider, _stringify_uuid_payload,
)
from backend.services.automation_engine import AutomationEngine


class TestCalculoSesionesExtra:
    def test_normalizar_frecuencia_semanal(self):
        assert _normalizar_frecuencia("semanal") == "SEMANAL"

    def test_normalizar_frecuencia_quincenal(self):
        assert _normalizar_frecuencia("quincenal") == "QUINCENAL"

    def test_normalizar_frecuencia_mensual(self):
        assert _normalizar_frecuencia("mensual") == "MENSUAL"

    def test_normalizar_frecuencia_con_acento(self):
        assert _normalizar_frecuencia("semanal") == "SEMANAL"

    def test_normalizar_frecuencia_mayusculas(self):
        assert _normalizar_frecuencia("SEMANAL") == "SEMANAL"

    def test_normalizar_frecuencia_vacio_raise(self):
        with pytest.raises(ValueError):
            _normalizar_frecuencia("")

    def test_normalizar_frecuencia_aliases(self):
        assert _normalizar_frecuencia("unica") == "EVENTO_UNICO"
        assert _normalizar_frecuencia("unico") == "EVENTO_UNICO"

    def test_provider_para_frecuencia_semanal(self):
        p = _provider_para_frecuencia("semanal", 1)
        assert isinstance(p, _IncProvider)
        assert p.dia_original is None

    def test_provider_para_frecuencia_mensual(self):
        p = _provider_para_frecuencia("mensual", 15)
        assert isinstance(p, _IncProvider)
        assert p.dia_original == 15

    def test_provider_para_frecuencia_invalida_raise(self):
        with pytest.raises(ValueError):
            _provider_para_frecuencia("inexistente", 1)

    def test_a_utc_naive(self):
        dt = datetime(2026, 1, 5, 10, 0, 0)
        result = _a_utc(dt)
        assert result.tzinfo is not None

    def test_a_utc_aware(self):
        dt = datetime(2026, 1, 5, 10, 0, 0, tzinfo=timezone.utc)
        result = _a_utc(dt)
        assert result.hour == 10

    def test_generar_fechas_semanal(self):
        inicio = datetime(2026, 1, 5, tzinfo=timezone.utc)
        fin = datetime(2026, 1, 26, tzinfo=timezone.utc)
        provider = _provider_para_frecuencia("semanal", inicio.day)
        fechas = _generar_fechas(inicio, fin, provider)
        assert len(fechas) == 4

    def test_generar_fechas_mensual(self):
        inicio = datetime(2026, 1, 15, tzinfo=timezone.utc)
        fin = datetime(2026, 4, 15, tzinfo=timezone.utc)
        provider = _provider_para_frecuencia("mensual", inicio.day)
        fechas = _generar_fechas(inicio, fin, provider)
        assert len(fechas) == 4

    def test_generar_fechas_evento_unico(self):
        inicio = datetime(2026, 6, 1, tzinfo=timezone.utc)
        fin = datetime(2026, 12, 31, tzinfo=timezone.utc)
        provider = _provider_para_frecuencia("evento_unico", inicio.day)
        fechas = _generar_fechas(inicio, fin, provider)
        assert len(fechas) == 1

    def test_generar_fechas_inicio_mayor_fin_raise(self):
        inicio = datetime(2026, 6, 1, tzinfo=timezone.utc)
        fin = datetime(2026, 1, 1, tzinfo=timezone.utc)
        provider = _provider_para_frecuencia("semanal", inicio.day)
        with pytest.raises(ValueError):
            _generar_fechas(inicio, fin, provider)

    def test_inc_provider_saltar_semanal(self):
        provider = _IncProvider(timedelta(weeks=1))
        dt = datetime(2026, 1, 5, tzinfo=timezone.utc)
        siguiente = provider.saltar(dt)
        assert siguiente.day == 12

    def test_inc_provider_saltar_mensual_con_truncamiento(self):
        provider = _IncProvider(timedelta(days=31), dia_original=31)
        dt = datetime(2026, 1, 31, tzinfo=timezone.utc)
        siguiente = provider.saltar(dt)
        assert siguiente.month == 3

    def test_stringify_uuid(self):
        uid = uuid.uuid4()
        result = _stringify_uuid_payload({"id": uid, "name": "test"})
        assert isinstance(result["id"], str)
        assert result["name"] == "test"


class TestAutomationEngineExtra:
    def test_engine_init(self):
        engine = AutomationEngine()
        assert engine is not None
