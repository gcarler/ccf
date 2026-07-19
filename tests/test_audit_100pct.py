"""
Tests to bring crud/audit.py and core/audit.py to 100%.
"""
import uuid

import pytest


@pytest.fixture
def full(client, db_session):
    from tests.conftest import seed_admin
    admin, persona, sede = seed_admin(db_session)
    return {"db": db_session, "admin": admin, "persona": persona, "c": client}


class TestCrudAudit:
    """Covers crud/audit.py:20-25 (UUID validation), 40 (return), 51, 53."""

    def test_create_audit_log_valid_uuid(self, full):
        """Covers lines 20-24, 27-40 — create with valid actor UUID."""
        from backend.crud.audit import create_admin_audit_log
        result = create_admin_audit_log(
            full["db"],
            action="test_action",
            actor_persona_id=str(full["persona"].id),
            resource_type="test",
            resource_id="123",
            metadata={"key": "value"},
            ip_address="127.0.0.1",
        )
        assert result is not None
        assert result.action == "test_action"
        assert result.actor_persona_id == full["persona"].id

    def test_create_audit_log_invalid_uuid(self, full):
        """Covers line 25 — invalid UUID resolves to None."""
        from backend.crud.audit import create_admin_audit_log
        result = create_admin_audit_log(
            full["db"],
            action="test_bad_uuid",
            actor_persona_id="not-a-uuid",
        )
        assert result is not None
        assert result.actor_persona_id is None

    def test_create_audit_log_no_actor(self, full):
        """Covers lines 20-21 — actor_persona_id None."""
        from backend.crud.audit import create_admin_audit_log
        result = create_admin_audit_log(
            full["db"],
            action="test_no_actor",
            actor_persona_id=None,
        )
        assert result is not None

    def test_get_audit_logs_with_filters(self, full):
        """Covers lines 50-53 — filter by actor_persona_id and resource_type."""
        from backend.crud.audit import create_admin_audit_log, get_admin_audit_logs
        create_admin_audit_log(full["db"], action="a1", actor_persona_id=str(full["persona"].id), resource_type="type_a")
        create_admin_audit_log(full["db"], action="a2", actor_persona_id=str(full["persona"].id), resource_type="type_b")
        create_admin_audit_log(full["db"], action="a3", actor_persona_id=str(uuid.uuid4()), resource_type="type_a")

        # Filter by actor
        logs = get_admin_audit_logs(full["db"], limit=10, actor_persona_id=str(full["persona"].id))
        assert len(logs) >= 2

        # Filter by resource_type
        logs_type = get_admin_audit_logs(full["db"], limit=10, resource_type="type_b")
        assert len(logs_type) >= 1

    def test_get_audit_logs_no_filters(self, full):
        """Covers lines 49, 54 — no filters, just limit."""
        from backend.crud.audit import create_admin_audit_log, get_admin_audit_logs
        create_admin_audit_log(full["db"], action="no_filter_test")
        logs = get_admin_audit_logs(full["db"], limit=5)
        assert len(logs) >= 1


class TestCoreAudit:
    """Covers core/audit.py:20-24 (actor_id lookup), 31 (resource_id str)."""

    def test_record_admin_action(self, full):
        """Covers lines 20-31 — full flow with valid actor."""
        from backend.core.audit import record_admin_action
        record_admin_action(
            full["db"],
            actor=full["admin"],
            action="core_test",
            resource_type="test_type",
            resource_id="res-001",
            metadata={"origin": "test"},
            ip_address="10.0.0.1",
        )
        # Verify it was created
        from backend.crud.audit import get_admin_audit_logs
        logs = get_admin_audit_logs(full["db"], limit=5, actor_persona_id=str(full["persona"].id))
        assert any(log.action == "core_test" for log in logs)

    def test_record_admin_action_no_actor_id(self, full):
        """Covers lines 21-22 — return early if actor has no id."""
        from unittest.mock import MagicMock
        from backend.core.audit import record_admin_action
        # Actor without id should return silently
        fake_actor = MagicMock(spec=[])  # No 'id' attribute
        del fake_actor.id
        # Should not raise
        record_admin_action(full["db"], actor=fake_actor, action="noop", resource_type="test")
        # No exception = pass

    def test_record_admin_action_none_resource_id(self, full):
        """Covers line 29 — resource_id None."""
        from backend.core.audit import record_admin_action
        record_admin_action(
            full["db"],
            actor=full["admin"],
            action="none_id_test",
            resource_type="test",
            resource_id=None,
        )
        from backend.crud.audit import get_admin_audit_logs
        logs = get_admin_audit_logs(full["db"], limit=5, actor_persona_id=str(full["persona"].id))
        assert any(log.action == "none_id_test" for log in logs)
