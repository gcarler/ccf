"""Canonical Evangelism router and person scanner."""

import datetime
import hashlib
import secrets
import uuid
from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import models
from backend.api.evangelism_analytics import router as analytics_router
from backend.api.evangelism_events import router as events_router
from backend.api.evangelism_grupos import router as grupos_router
from backend.api.evangelism_main import estrategias_router, roles_router
from backend.api.evangelism_multiplication import router as multiplication_router
from backend.api.evangelism_notifications import router as notifications_router
from backend.api.evangelism_rankings import router as rankings_router
from backend.api.evangelism_reports import router as reports_router
from backend.api.evangelism_shared import utc_now
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.core.tenant import require_user_sede_id

router = APIRouter()
router.include_router(events_router)
router.include_router(grupos_router)
router.include_router(estrategias_router)
router.include_router(roles_router)
router.include_router(multiplication_router)
router.include_router(notifications_router)
router.include_router(rankings_router)
router.include_router(reports_router)
router.include_router(analytics_router)


def _get_scoped_scanner_persona(
    persona_id: uuid.UUID,
    db: Session,
    current_user: models.User,
) -> models.Persona:
    """Return a canonical persona only when it belongs to the caller's sede.

    Scanner tokens identify a person and therefore follow the same tenant
    boundary as the rest of Evangelism.  A 404 intentionally avoids exposing
    whether a persona exists in another sede.
    """
    user_sede_id = require_user_sede_id(db, current_user)
    persona = (
        db.query(models.Persona)
        .filter(
            models.Persona.id == persona_id,
            models.Persona.sede_id == user_sede_id,
        )
        .first()
    )
    if not persona:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return persona


def _generate_scanner_token(persona: models.Persona, db: Session) -> dict:
    """Generate a one-time-visible CCF-PER token for a canonical persona."""
    secret = secrets.token_hex(16)
    token = f"CCF-PER-{persona.id}-{secret}"
    expires_at = datetime.datetime.now(timezone.utc) + datetime.timedelta(days=365)
    persona.scanner_token_hash = hashlib.sha256(secret.encode()).hexdigest()
    persona.scanner_token_expires_at = expires_at
    db.commit()
    return {"token": token, "expires_at": expires_at.isoformat()}


@router.post("/scanner/generate/{persona_id}", response_model=dict)
def generate_scanner_token(
    persona_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("evangelism", "manage")),
):
    persona = _get_scoped_scanner_persona(persona_id, db, current_user)
    return _generate_scanner_token(persona, db)


@router.post("/scanner/validate/{token}", response_model=dict)
def validate_scanner_token(
    token: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("evangelism", "read")),
):
    if not token.startswith("CCF-PER-"):
        raise HTTPException(status_code=400, detail="Formato de código inválido")

    payload = token.removeprefix("CCF-PER-")
    if len(payload) < 38:
        raise HTTPException(status_code=400, detail="Token malformado")
    try:
        persona_id = uuid.UUID(payload[:36])
    except ValueError:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    if payload[36] != "-" or not payload[37:]:
        raise HTTPException(status_code=400, detail="Token malformado")
    secret = payload[37:]

    persona = _get_scoped_scanner_persona(persona_id, db, current_user)
    if not persona.scanner_token_hash:
        raise HTTPException(status_code=403, detail="La persona no tiene un token activo")

    expires_at = persona.scanner_token_expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at < datetime.datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="Token expirado")

    computed_hash = hashlib.sha256(secret.encode()).hexdigest()
    if not secrets.compare_digest(computed_hash, persona.scanner_token_hash):
        raise HTTPException(status_code=403, detail="Token de seguridad inválido")

    return {
        "valid": True,
        "persona_id": persona.id,
        "name": f"{persona.first_name} {persona.last_name}",
        "role": persona.church_role,
        "status": persona.spiritual_status,
        "timestamp": utc_now().isoformat(),
    }
