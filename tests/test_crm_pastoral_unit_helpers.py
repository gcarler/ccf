"""Unit tests for pastoral helper functions — pure logic, no DB."""
from __future__ import annotations

# We import the module-level functions via sys.path trick to avoid
# conftest's import of backend.models (which has missing models_cms imports)
import sys
import types

import pytest

# Create a mock module for backend.models_crm_pipeline
pipeline_mod = types.ModuleType("backend.models_crm_pipeline")

# Create the enum
import enum


class EstadoCasoEnum(str, enum.Enum):
    ABIERTO = "abierto"
    RESUELTO_EXITO = "resuelto_exito"
    CERRADO_PERDIDO = "cerrado_perdido"
    ESPERANDO_RESPUESTA = "esperando_respuesta"
    EN_PROGRESO = "en_progreso"


pipeline_mod.EstadoCasoEnum = EstadoCasoEnum

# Register the mock module
sys.modules["backend.models_crm_pipeline"] = pipeline_mod


# Now we can import the functions from pastoral.py
from backend.api.crm.pastoral import (
    _get_user_role,
    _seconds_between,
    _shape_workload_row,
    _stage_to_estado,
)


class TestGetUserRole:
    def test_role_attr(self):
        user = type("U", (), {"role": "ADMIN"})()
        assert _get_user_role(user) == "admin"

    def test_rol_plataforma_fallback(self):
        role = type("R", (), {"nombre": "pastor"})()
        user = type("U", (), {"role": "", "rol_plataforma": role})()
        assert _get_user_role(user) == "pastor"

    def test_empty_returns_empty(self):
        user = type("U", (), {"role": "", "rol_plataforma": None})()
        assert _get_user_role(user) == ""


class TestStageToEstado:
    def test_consolidated(self):
        assert _stage_to_estado("consolidated") == EstadoCasoEnum.RESUELTO_EXITO
        assert _stage_to_estado("integrated") == EstadoCasoEnum.RESUELTO_EXITO
        assert _stage_to_estado("converted") == EstadoCasoEnum.RESUELTO_EXITO

    def test_lost(self):
        assert _stage_to_estado("lost") == EstadoCasoEnum.CERRADO_PERDIDO
        assert _stage_to_estado("closed") == EstadoCasoEnum.CERRADO_PERDIDO

    def test_call_contacted(self):
        assert _stage_to_estado("call") == EstadoCasoEnum.ESPERANDO_RESPUESTA
        assert _stage_to_estado("contacted") == EstadoCasoEnum.ESPERANDO_RESPUESTA

    def test_visit_in_progress(self):
        assert _stage_to_estado("visit") == EstadoCasoEnum.EN_PROGRESO
        assert _stage_to_estado("in_process") == EstadoCasoEnum.EN_PROGRESO

    def test_default(self):
        assert _stage_to_estado("") == EstadoCasoEnum.ABIERTO
        assert _stage_to_estado("unknown") == EstadoCasoEnum.ABIERTO


class TestSecondsBetween:
    def test_valid(self):
        result = _seconds_between("2026-07-01T10:00:00Z", "2026-07-01T11:30:00Z")
        assert result == pytest.approx(5400, abs=1)

    def test_invalid(self):
        assert _seconds_between(None, "2026-07-01T10:00:00Z") is None

    def test_reversed(self):
        assert _seconds_between("2026-07-01T12:00:00Z", "2026-07-01T10:00:00Z") is None


class TestShapeWorkloadRow:
    def test_disponible(self):
        r = _shape_workload_row("u1", "A", 3, 2, 1, 0)
        assert r["load_status"] == "disponible"
        assert r["capacity_percent"] == 20

    def test_sobrecargado(self):
        r = _shape_workload_row("u1", "B", 20, 10, 4, 0)
        assert r["load_status"] == "sobrecargado"
