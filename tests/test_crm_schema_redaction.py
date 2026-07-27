"""Tests for schema-level redaction of sensitive CRM fields.

The redaction logic lives in ``backend.schemas.crm.base`` and relies on the
``user_role_context`` set by the authentication layer. Non-privileged roles
(lector, miembro, editor, etc.) must see masked values; privileged roles
(admin, pastor) must see the original values.
"""

import uuid as _uuid

import pytest

from backend.core.context import user_role_context
from backend.schemas.crm.base import CounselingTicket, Persona


@pytest.fixture(autouse=True)
def _clear_role_context():
    """Ensure each test starts with a clean role context."""
    token = user_role_context.set(None)
    yield
    user_role_context.reset(token)


class TestCounselingTicketRedaction:
    def _ticket(self, notes: str = "secret notes") -> CounselingTicket:
        return CounselingTicket(
            id=_uuid.uuid4(),
            persona_id=_uuid.uuid4(),
            subject="Test subject",
            notes=notes,
            status="open",
            priority_level="NORMAL",
            created_at="2026-01-01T00:00:00+00:00",
        )

    def test_non_privileged_role_gets_redacted_notes(self):
        for role in ("lector", "editor", "miembro", "estudiante"):
            user_role_context.set(role)
            ticket = self._ticket()
            ticket.restrict_counseling_notes()
            assert ticket.notes == "[RESTRINGIDO - SOLO PASTORES/ADMIN]", f"failed for role={role}"

    def test_pastor_sees_original_notes(self):
        user_role_context.set("pastor")
        ticket = self._ticket("pastoral notes")
        ticket.restrict_counseling_notes()
        assert ticket.notes == "pastoral notes"

    def test_admin_sees_original_notes(self):
        user_role_context.set("admin")
        ticket = self._ticket("admin notes")
        ticket.restrict_counseling_notes()
        assert ticket.notes == "admin notes"


class TestPersonaRedaction:
    def _persona(self) -> Persona:
        return Persona(
            id=_uuid.uuid4(),
            first_name="John",
            last_name="Doe",
            created_at="2026-01-01T00:00:00+00:00",
            pastoral_notes="very sensitive",
            spiritual_health=0.85,
            talents="music, preaching",
            spiritual_gifts="teaching",
        )

    def test_non_privileged_role_gets_redacted_persona_fields(self):
        for role in ("lector", "editor", "miembro"):
            user_role_context.set(role)
            persona = self._persona()
            persona.restrict_crm_fields()
            assert persona.pastoral_notes == "[RESTRINGIDO]"
            assert persona.spiritual_health == 0.0
            assert persona.talents == "[RESTRINGIDO]"
            assert persona.spiritual_gifts == "[RESTRINGIDO]"

    def test_pastor_sees_original_persona_fields(self):
        user_role_context.set("pastor")
        persona = self._persona()
        persona.restrict_crm_fields()
        assert persona.pastoral_notes == "very sensitive"
        assert persona.spiritual_health == 0.85
        assert persona.talents == "music, preaching"
        assert persona.spiritual_gifts == "teaching"

    def test_admin_sees_original_persona_fields(self):
        user_role_context.set("admin")
        persona = self._persona()
        persona.restrict_crm_fields()
        assert persona.pastoral_notes == "very sensitive"
