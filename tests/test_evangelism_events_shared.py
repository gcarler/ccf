"""Tests for evangelism_events/_shared.py — permission helpers."""
from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from backend import models
from backend.api.evangelism_events._shared import (
    _get_persona_for_user,
    _get_user_role,
    is_event_manager_role,
    is_event_reader_role,
)


class TestGetUserRole:
    def test_admin_role(self):
        class MockUser:
            role = "ADMIN"
            rol_plataforma = None
        assert _get_user_role(MockUser()) == "admin"

    def test_no_role_fallback(self):
        class MockRol:
            nombre = "PASTOR"
        class MockUser:
            role = ""
            rol_plataforma = MockRol()
        assert _get_user_role(MockUser()) == "pastor"

    def test_no_role_at_all(self):
        class MockUser:
            role = ""
            rol_plataforma = None
        assert _get_user_role(MockUser()) == ""


class TestIsEventReader:
    def test_admin_is_reader(self):
        class MockUser:
            role = "ADMIN"
            rol_plataforma = None
        assert is_event_reader_role(MockUser()) is True

    def test_persona_not_reader(self):
        class MockUser:
            role = "persona"
            rol_plataforma = None
        assert is_event_reader_role(MockUser()) is False


class TestIsEventManager:
    def test_admin_is_manager(self):
        class MockUser:
            role = "ADMIN"
            rol_plataforma = None
        assert is_event_manager_role(MockUser()) is True

    def test_coordinador_not_manager(self):
        class MockUser:
            role = "coordinador"
            rol_plataforma = None
        assert is_event_manager_role(MockUser()) is False


class TestGetPersonaForUser:
    def test_none_id(self, db_session):
        assert _get_persona_for_user(db_session, None) is None

    def test_invalid_id(self, db_session):
        assert _get_persona_for_user(db_session, "not-a-uuid") is None

    def test_not_found(self, db_session):
        assert _get_persona_for_user(db_session, uuid.uuid4()) is None

    def test_found(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="Test", last_name="User")
        db_session.add(p)
        db_session.commit()
        result = _get_persona_for_user(db_session, p.id)
        assert result is not None
        assert result.id == p.id


class TestRequireEventAccess:
    def test_event_not_found(self, db_session):
        from backend.api.evangelism_events._shared import require_event_access
        class MockUser:
            id = uuid.uuid4()
            role = "ADMIN"
        with pytest.raises(HTTPException) as exc:
            require_event_access(db_session, MockUser(), uuid.uuid4())
        assert exc.value.status_code == 404
