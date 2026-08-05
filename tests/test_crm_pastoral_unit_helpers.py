"""Unit tests for pastoral helper functions — pure logic, no DB.

Los helpers ``_seconds_between`` y ``_shape_workload_row`` fueron migrados a
``backend.api.workspace_shared._incidents`` y ``backend.api.system``
respectivamente; sus tests viven en ``test_workspace_incidents.py`` y
``test_system_final.py``.  Aquí solo cubrimos los helpers que SI viven en
``backend.api.crm.pastoral``: ``_get_user_role`` y ``_stage_to_estado``.
"""
from __future__ import annotations

from backend.api.crm.pastoral import _get_user_role, _stage_to_estado
from backend.models_crm_pipeline import EstadoCasoEnum


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
