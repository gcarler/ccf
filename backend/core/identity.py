"""Canonical identity adapters shared by platform modules.

This module is the only cross-module entry point for resolving the current
user's sede or persona identity.  Feature modules must not import CRM CRUD
helpers for these lookups.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from backend.core.tenant import get_user_sede_id as _tenant_get_user_sede_id
from backend.models_crm import Persona


def _as_uuid(value: Any) -> uuid.UUID | None:
    """Return a UUID when ``value`` is a valid identity, otherwise ``None``."""
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (AttributeError, TypeError, ValueError):
        return None


def get_user_sede_id(db: Session, user_or_id: Any) -> uuid.UUID | None:
    """Resolve the canonical sede assigned to an authenticated identity."""
    return _as_uuid(_tenant_get_user_sede_id(db, user_or_id))


def resolve_persona_id_for_user(db: Session, user_id: Any) -> uuid.UUID | None:
    """Resolve a user's persona without crossing into CRM CRUD internals."""
    user_uuid = _as_uuid(getattr(user_id, "id", user_id))
    if user_uuid is None:
        return None

    return db.query(Persona.id).filter(Persona.id == user_uuid).scalar()


def resolve_persona_id_from_identity(
    db: Session, identity: Any
) -> uuid.UUID | None:
    """Resolve a persona identifier supplied by an identity-bearing payload."""
    return resolve_persona_id_for_user(db, identity)
