"""
Tests for evangelism_events/_shared.py — covers require_event_access, is_event_reader_role.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend import models
from backend.api.evangelism_events._shared import (
    is_event_manager_role,
    is_event_reader_role,
    require_event_access,
)
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture
def full(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {"c": client, "h": headers, "db": db_session, "admin": admin, "persona": persona, "sede": sede}


def _make_event(db, sede_id, titulo="Evento Test"):
    e = models.CrmEvent(
        id=uuid.uuid4(), name=titulo,
        sede_id=sede_id,
        event_date=datetime.now(timezone.utc) + timedelta(days=1),
        description="Test event",
    )
    db.add(e)
    db.flush()
    return e


class TestEventRoles:

    def test_admin_is_reader(self, full):
        assert is_event_reader_role(full["admin"]) is True

    def test_admin_is_manager(self, full):
        assert is_event_manager_role(full["admin"]) is True

    def test_miembro_is_not_manager(self, full):
        user = type("User", (), {"role": "miembro", "rol_plataforma": None})()
        assert is_event_manager_role(user) is False

    def test_miembro_is_not_reader(self, full):
        user = type("User", (), {"role": "miembro", "rol_plataforma": None})()
        assert is_event_reader_role(user) is False


class TestRequireEventAccess:

    def test_admin_access_own_event(self, full):
        event = _make_event(full["db"], full["sede"].id)
        full["db"].commit()
        result = require_event_access(full["db"], full["admin"], event.id)
        assert result is not None
        assert result.id == event.id

    def test_cross_sede_returns_404(self, full):
        other_sede_id = uuid.uuid4()
        event = _make_event(full["db"], other_sede_id)
        full["db"].commit()
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            require_event_access(full["db"], full["admin"], event.id)
        assert exc_info.value.status_code == 404

    def test_nonexistent_event_404(self, full):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            require_event_access(full["db"], full["admin"], uuid.uuid4())
        assert exc_info.value.status_code == 404
