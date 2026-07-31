"""Extended unit tests for evangelism_shared.py."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from backend import models
from backend.api import evangelism_shared as shared


class TestAttendanceSets:
    def test_attended(self):
        assert "ASISTIO" in shared.ATTENDED_STATES
        assert "FALTO" not in shared.ATTENDED_STATES

    def test_absent(self):
        assert "FALTO" in shared.ABSENT_STATES
        assert "ASISTIO" not in shared.ABSENT_STATES

    def test_excused(self):
        assert "EXCUSA" in shared.EXCUSED_STATES
        assert "ASISTIO" not in shared.EXCUSED_STATES

    def test_first_time(self):
        assert "first_time" in shared.FIRST_TIME_STATES


class TestSessionReadValue:
    def test_loaded(self):
        class M:
            __dict__ = {"estado": "REALIZADA"}

        assert shared.session_read_value(M(), "estado") == "REALIZADA"

    def test_missing(self):
        class M:
            __dict__ = {}

        assert shared.session_read_value(M(), "x", "default") == "default"


class TestSessionEstado:
    def test_default(self):
        class M:
            __dict__ = {}

        assert shared.session_estado_habilitacion(M()) == "HABILITADO"

    def test_with_value(self):
        class M:
            __dict__ = {"estado_habilitacion": "FINALIZADO"}

        assert shared.session_estado_habilitacion(M()) == "FINALIZADO"


class TestIsFunctions:
    def test_is_attended(self):
        assert shared.is_attended_status("ASISTIO") is True
        assert shared.is_attended_status("FALTO") is False

    def test_is_absent(self):
        assert shared.is_absent_status("FALTO") is True
        assert shared.is_absent_status("ASISTIO") is False

    def test_is_excused(self):
        assert shared.is_excused_status("EXCUSA") is True
        assert shared.is_excused_status("ASISTIO") is False


class TestUtcNow:
    def test_tz_aware(self):
        assert shared.utc_now().tzinfo is not None


class TestParseSessionDate:
    def test_from_datetime(self):
        assert shared.parse_session_date(datetime(2026, 7, 1, tzinfo=timezone.utc)).day == 1

    def test_from_string(self):
        from datetime import date

        assert shared.parse_session_date("2026-07-01") == date(2026, 7, 1)

    def test_none_raises(self):
        with pytest.raises(Exception):
            shared.parse_session_date(None)


class TestDBHelpers:
    def test_column_names(self, db_session):
        assert isinstance(shared._sessions_grupo_live_column_names(db_session), set)

    def test_has_estado(self, db_session):
        assert isinstance(shared.sessions_grupo_has_estado_habilitacion(db_session), bool)

    def test_get_persona_none(self, db_session):
        assert shared._get_persona_for_user(db_session, None) is None

    def test_get_persona_invalid(self, db_session):
        assert shared._get_persona_for_user(db_session, "bad") is None

    def test_get_persona_found(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="T", last_name="U")
        db_session.add(p)
        db_session.commit()
        assert shared._get_persona_for_user(db_session, p.id) is not None

    def test_get_visible_strategy(self, db_session):
        assert shared.get_visible_strategy(db_session, uuid.uuid4(), uuid.uuid4()) is None

    def test_get_visible_group(self, db_session):
        assert shared.get_visible_group(db_session, uuid.uuid4(), uuid.uuid4()) is None

    def test_get_visible_session(self, db_session):
        assert shared.get_visible_session(db_session, uuid.uuid4(), uuid.uuid4()) is None
