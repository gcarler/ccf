"""Final batch of unit tests for evangelism_shared.py uncovered functions."""

from __future__ import annotations

import uuid

from backend.api import evangelism_shared as shared


class TestIsCRmAdminOrPastor:
    def test_admin(self):
        class M:
            role = "ADMIN"
            rol_plataforma = None

        assert shared._is_crm_admin_or_pastor(M()) is True

    def test_pastor(self):
        class M:
            role = "PASTOR"
            rol_plataforma = None

        assert shared._is_crm_admin_or_pastor(M()) is True

    def test_persona(self):
        class M:
            role = "persona"
            rol_plataforma = None

        assert shared._is_crm_admin_or_pastor(M()) is False


class TestNormalizeRoleScopePayload:
    def test_empty(self):
        assert isinstance(shared.normalize_role_scope_payload({}), dict)


class TestExpectedGroupRows:
    def test_no_group(self, db_session):
        assert shared.expected_group_rows(db_session, uuid.uuid4()) == []
