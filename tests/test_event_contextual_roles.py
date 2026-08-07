"""Plan clasificador contextual — contratos del servicio de roles contextuales.

Reconstruido desde su bytecode (restauración de trabajo perdido): los tests
fijan las firmas públicas de ``normalize_participant_role``,
``resolve_participant_role`` y ``DEFAULT_PARTICIPANT_ROLE``, el rechazo de
códigos desconocidos con 422, el override autorizado y el contrato
ORM/schema/endpoint público.
"""

from __future__ import annotations

import uuid

import pytest

from backend import models, schemas
from backend.services.event_registration_service import (
    DEFAULT_PARTICIPANT_ROLE,
    RegistrationError,
    normalize_participant_role,
    resolve_participant_role,
)


def _event(role: str | None = None) -> models.CrmEvent:
    return models.CrmEvent(id=uuid.uuid4(), participant_role_code=role)


def _reg(role: str | None = None) -> models.EventRegistration:
    return models.EventRegistration(id=uuid.uuid4(), participant_role_code=role)


def test_default_role_is_visitor_event():
    """Sin rol configurado, el default canónico es VISITANTE_EVENTO."""
    assert DEFAULT_PARTICIPANT_ROLE == "VISITANTE_EVENTO"
    assert normalize_participant_role(None) == DEFAULT_PARTICIPANT_ROLE
    assert normalize_participant_role("") == DEFAULT_PARTICIPANT_ROLE
    assert resolve_participant_role(_event()) == DEFAULT_PARTICIPANT_ROLE
    assert resolve_participant_role(_event(), reg=_reg()) == DEFAULT_PARTICIPANT_ROLE


def test_event_role_is_normalized():
    """El rol del evento se normaliza (trim + upper) al resolver."""
    event = _event(role=" visitante_evento ")
    assert resolve_participant_role(event) == "VISITANTE_EVENTO"
    assert normalize_participant_role("miembro") == "MIEMBRO"
    # El rol de la inscripción gana sobre el del evento.
    reg = _reg(role="VOLUNTARIO")
    assert resolve_participant_role(_event("MIEMBRO"), reg=reg) == "VOLUNTARIO"


def test_invalid_role_is_rejected():
    """Códigos fuera del catálogo → RegistrationError 422 (contrato §3)."""
    with pytest.raises(RegistrationError) as exc_info:
        normalize_participant_role("HACKER_ROLE")
    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "INVALID_PARTICIPANT_ROLE"


def test_authorized_override_wins():
    """El override explícito (admin) gana sobre inscripción y evento."""
    event = _event("MIEMBRO")
    reg = _reg("INVITADO")
    assert resolve_participant_role(event, reg=reg) == "INVITADO"
    assert resolve_participant_role(event, reg=reg, requested="SERVIDOR") == "SERVIDOR"
    assert resolve_participant_role(event) == "MIEMBRO"


def test_orm_and_response_contract_expose_contextual_role():
    """ORM y schemas de respuesta exponen participant_role_code."""
    event = _event("VOLUNTARIO")
    assert event.participant_role_code == "VOLUNTARIO"
    reg = _reg("VOLUNTARIO")
    assert reg.participant_role_code == "VOLUNTARIO"
    assert "participant_role_code" in schemas.EventRegistrationRead.model_fields
    assert "participant_role_code" in schemas.PublicEventRead.model_fields
    assert "participant_role_code" in schemas.CrmEvent.model_fields
    assert "participant_role_code" in schemas.CrmEventPreregistrationConfig.model_fields


def test_public_registration_does_not_accept_admin_role_override():
    """El endpoint público NO acepta override de rol (solo el admin lo hace)."""
    with pytest.raises(ValueError):
        schemas.PublicEventRegister(
            first_name="Ana",
            last_name="Pérez",
            participant_role_code="MIEMBRO",  # extra=forbid → rechazado
        )
