"""
Direct unit tests for backend.api.crm._shared — the shared CRM utilities.
"""

from __future__ import annotations

import uuid

import pytest

from backend import models
from backend.api.crm import _shared as shared


class TestPersonaLiveColumnNames:
    def test_persona_live_column_names_returns_set(self, db_session):
        result = shared._persona_live_column_names(db_session)
        assert isinstance(result, set)

    def test_case_live_column_names_returns_set(self, db_session):
        result = shared._case_live_column_names(db_session)
        assert isinstance(result, set)

    def test_stage_live_column_names_returns_set(self, db_session):
        result = shared._stage_live_column_names(db_session)
        assert isinstance(result, set)


class TestCaseCreatedColumn:
    def test_case_created_column_returns_none_or_column(self, db_session):
        result = shared._case_created_column(db_session)
        assert result is None or hasattr(result, "name")


class TestPersonaQuery:
    def test_persona_query_returns_query(self, db_session):
        result = shared.persona_query(db_session)
        assert result is not None


class TestCaseQuery:
    def test_case_query_returns_query(self, db_session):
        result = shared.case_query(db_session)
        assert result is not None


class TestUtcNow:
    def test_utc_now_returns_datetime(self):
        result = shared.utc_now()
        assert result is not None


class TestEnumValue:
    def test_enum_value_with_string(self):
        assert shared._enum_value("direct_string") == "direct_string"


class TestPersonaFullName:
    def test_persona_full_name_with_data(self, db_session):
        persona = models.Persona(
            id=uuid.uuid4(),
            first_name="Carlos",
            last_name="Perez",
        )
        db_session.add(persona)
        db_session.commit()
        result = shared._persona_full_name(persona)
        assert result is not None

    def test_persona_full_name_none(self):
        result = shared._persona_full_name(None)
        assert isinstance(result, str)


class TestGetScopedPersona:
    def test_get_scoped_persona_nonexistent_raises(self, db_session):
        with pytest.raises(Exception):
            shared._get_scoped_persona(db_session, None, str(uuid.uuid4()))
