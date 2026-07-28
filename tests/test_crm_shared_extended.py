"""
Direct unit tests for backend.api.crm._shared — testable utility functions.
"""
from __future__ import annotations

import uuid

import pytest

from backend.api.crm import _shared as shared
from backend import models


# ═══════════════════════════════════════════════════════════════════════════════
# BASIC HELPERS — no DB required
# ═══════════════════════════════════════════════════════════════════════════════


class TestPayloadKey:
    def test_returns_input(self):
        assert shared._payload_key("test") == "test"
        assert shared._payload_key("") == ""


class TestEnumValue:
    def test_enum_with_value_attr(self):
        class FakeEnum:
            value = "test_value"
        assert shared._enum_value(FakeEnum()) == "test_value"

    def test_enum_with_string(self):
        assert shared._enum_value("direct") == "direct"

    def test_enum_with_none(self):
        assert shared._enum_value(None) is None

    def test_enum_with_int(self):
        assert shared._enum_value(42) == 42


class TestCaseStatus:
    def test_case_status_from_status_attr(self):
        class MockCase:
            status = "active"
            estado = None
        assert shared._case_status(MockCase()) == "active"

    def test_case_status_closed_exito(self):
        class MockCase:
            status = None
            estado = "RESUELTO_EXITO"
        assert shared._case_status(MockCase()) == "closed"

    def test_case_status_closed_perdido(self):
        class MockCase:
            status = None
            estado = "CERRADO_PERDIDO"
        assert shared._case_status(MockCase()) == "closed"

    def test_case_status_active_default(self):
        class MockCase:
            status = None
            estado = "EN_PROGRESO"
        assert shared._case_status(MockCase()) == "active"

    def test_case_status_active_empty(self):
        class MockCase:
            status = None
            estado = ""
        assert shared._case_status(MockCase()) == "active"


class TestCaseStage:
    def test_case_stage_from_stage_attr(self):
        class MockCase:
            stage = "call"
            payload_web = None
            etapa_actual = None
            estado = ""
        assert shared._case_stage(MockCase()) == "call"

    def test_case_stage_from_payload(self):
        class MockCase:
            stage = None
            payload_web = {"stage": "visit"}
            etapa_actual = None
            estado = ""
        assert shared._case_stage(MockCase()) == "visit"

    def test_case_stage_from_etapa_llamar(self):
        class MockEtapa:
            nombre = "llamar_contacto"
        class MockCase:
            stage = None
            payload_web = None
            etapa_actual = MockEtapa()
            estado = ""
        assert shared._case_stage(MockCase()) == "call"

    def test_case_stage_from_etapa_visita(self):
        class MockEtapa:
            nombre = "visita_seguimiento"
        class MockCase:
            stage = None
            payload_web = None
            etapa_actual = MockEtapa()
            estado = ""
        assert shared._case_stage(MockCase()) == "visit"

    def test_case_stage_from_etapa_discip(self):
        class MockEtapa:
            nombre = "discipulado"
        class MockCase:
            stage = None
            payload_web = None
            etapa_actual = MockEtapa()
            estado = ""
        assert shared._case_stage(MockCase()) == "discipleship"

    def test_case_stage_from_estado_exito(self):
        class MockCase:
            stage = None
            payload_web = None
            etapa_actual = None
            estado = "RESUELTO_EXITO"
        assert shared._case_stage(MockCase()) == "consolidated"

    def test_case_stage_from_estado_perdido(self):
        class MockCase:
            stage = None
            payload_web = None
            etapa_actual = None
            estado = "CERRADO_PERDIDO"
        assert shared._case_stage(MockCase()) == "lost"

    def test_case_stage_default_new(self):
        class MockCase:
            stage = None
            payload_web = None
            etapa_actual = None
            estado = ""
        assert shared._case_stage(MockCase()) == "new"


class TestSerializePersonaPosition:
    def test_with_none_position(self):
        class MockPP:
            id = uuid.uuid4()
            persona_id = uuid.uuid4()
            position_id = uuid.uuid4()
            position = None
            start_date = None
            end_date = None
            is_active = True
            notes = None
            created_at = None
        result = shared._serialize_persona_position(MockPP())
        assert result["position_name"] is None
        assert result["category"] is None
        assert result["is_active"] is True

    def test_with_minimal_position(self):
        class MockPos:
            name = "Pastor"
            category = "ministry"
        class MockPP:
            id = uuid.uuid4()
            persona_id = uuid.uuid4()
            position_id = uuid.uuid4()
            position = MockPos()
            start_date = None
            end_date = None
            is_active = False
            notes = "Test"
            created_at = None
        result = shared._serialize_persona_position(MockPP())
        assert result["position_name"] == "Pastor"
        assert result["is_active"] is False
        assert result["notes"] == "Test"


class TestPersonaFullName:
    def test_with_persona(self):
        class MockPersona:
            nombre_completo = "Carlos Perez"
        assert shared._persona_full_name(MockPersona()) == "Carlos Perez"

    def test_with_none(self):
        assert shared._persona_full_name(None) == "Persona"


class TestSerializeMessageGroup:
    def test_empty_list(self):
        """Empty list would crash in sorted() with IndexError."""
        with pytest.raises(IndexError):
            shared._serialize_message_group([])


class TestResolveAssigneeForTask:
    def test_none_returns_none(self, db_session):
        assert shared._resolve_assignee_for_task(db_session, None, None) is None

    def test_empty_string_returns_none(self, db_session):
        assert shared._resolve_assignee_for_task(db_session, None, "") is None

    def test_invalid_format_raises_404(self, db_session):
        with pytest.raises(Exception) as exc:
            shared._resolve_assignee_for_task(db_session, None, "not-a-uuid")
        assert "404" in str(exc) or "404" in str(exc.value.status_code)


class TestPersonaMatchesSegment:
    def test_empty_segment(self):
        persona = {}
        assert shared._persona_matches_segment(persona, "", set()) is False

    def test_none_segment(self):
        persona = {"sede_id": str(uuid.uuid4())}
        assert shared._persona_matches_segment(persona, None, set()) is False


class TestResolveCampaignPersonas:
    def test_empty_segments(self, db_session):
        result = shared._resolve_campaign_personas(db_session, [])
        assert result == []
