from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session


def _as_uuid(value: Any) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def get_user_sede_id(db: Session, user_or_id: Any) -> str | None:
    """Resolve the authenticated user's sede_id from canonical auth/persona links."""
    from backend.models_auth import Usuario
    from backend.models_crm import Persona

    direct_sede = getattr(user_or_id, "sede_id", None)
    if direct_sede:
        return str(direct_sede)

    user_id = getattr(user_or_id, "id", user_or_id)
    user_uuid = _as_uuid(user_id)

    if user_uuid:
        auth_sede = (
            db.query(Usuario.sede_id)
            .filter(Usuario.id == user_uuid)
            .scalar()
        )
        if auth_sede:
            return str(auth_sede)

        persona_sede = (
            db.query(Persona.sede_id)
            .filter(Persona.id == user_uuid)
            .scalar()
        )
        if persona_sede:
            return str(persona_sede)

    return None


def require_user_sede_id(db: Session, current_user: Any) -> str:
    sede_id = get_user_sede_id(db, current_user)
    if not sede_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario sin sede asignada",
        )
    return sede_id
