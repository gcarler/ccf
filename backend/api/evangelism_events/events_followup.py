"""API Router para Seguimiento Post-Evento, Campañas Multicanal y Asignación de Mentores.

TKT-EVT-FOLLOWUP-04:
- GET /events/{event_id}/followup/overview: Métricas ejecutivas y definición de la secuencia.
- GET /events/{event_id}/followup/attendees: Lista filtrable de asistentes en seguimiento.
- POST /events/{event_id}/followup/auto-assign-mentors: Asignación masiva por zona y balanceo.
- PUT /events/{event_id}/followup/assign-mentor: Asignación / reasignación manual de mentor.
- POST /events/{event_id}/followup/trigger-step: Disparo manual de pasos (24h, 72h, 7d).
- POST /events/{event_id}/followup/record-response: Registro de respuesta del asistente.
- GET /events/{event_id}/followup/available-mentors: Mentores disponibles con su carga actual.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend import models
from backend.api.evangelism_events._shared import require_event_access
from backend.core.audit import record_admin_action
from backend.core.database import get_db
from backend.core.permissions import require_evangelism_edit, require_evangelism_read
from backend.core.rate_limit import academy_limiter
from backend.core.tenant import require_user_sede_id
from backend.services.event_post_followup_service import (
    auto_assign_event_mentors,
    dispatch_followup_step,
    get_available_mentors,
    get_followup_attendees,
    get_followup_overview,
    manual_assign_mentor,
    record_followup_response,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────


class ManualAssignMentorPayload(BaseModel):
    persona_id: UUID
    mentor_persona_id: UUID
    suggested_group_id: Optional[UUID] = None
    notes: Optional[str] = None


class TriggerStepPayload(BaseModel):
    step_number: int = Field(..., ge=1, le=3, description="Paso de la secuencia (1, 2 o 3)")
    persona_ids: Optional[list[UUID]] = Field(None, description="Lista opcional de personas a despachar")
    force: bool = Field(False, description="Forzar reenvío incluso si ya fue enviado")
    custom_content: Optional[str] = Field(None, description="Contenido de plantilla personalizado")


class RecordResponsePayload(BaseModel):
    persona_id: UUID
    notes: str = Field(..., min_length=2, description="Notas o respuesta del asistente")
    channel: Optional[str] = Field("WHATSAPP", description="Canal por el cual se recibió la respuesta")


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/events/{event_id}/followup/overview")
@academy_limiter.limit("60/minute")
def get_event_followup_overview(
    request: Request,
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    """Métricas cuantitativas de la secuencia de seguimiento post-evento y asignación de mentores."""
    event = require_event_access(db, current_user, event_id)
    return get_followup_overview(db, event)


@router.get("/events/{event_id}/followup/attendees")
@academy_limiter.limit("60/minute")
def list_event_followup_attendees(
    request: Request,
    event_id: UUID,
    status: Optional[str] = Query(None, description="Filtro por estado (ACTIVE, COMPLETED, PAUSED)"),
    step: Optional[int] = Query(None, ge=1, le=3, description="Filtro por paso actual (1, 2, 3)"),
    has_mentor: Optional[bool] = Query(None, description="Filtro por asignación de mentor"),
    search: Optional[str] = Query(None, description="Búsqueda por nombre, email o teléfono"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    """Nómina de asistentes en seguimiento con su estado de cadencia, mentor y grupo."""
    event = require_event_access(db, current_user, event_id)
    return get_followup_attendees(
        db,
        event,
        status_filter=status,
        step_filter=step,
        has_mentor_filter=has_mentor,
        search=search,
    )


@router.get("/events/{event_id}/followup/available-mentors")
@academy_limiter.limit("60/minute")
def list_available_mentors(
    request: Request,
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    """Lista de mentores y líderes de Grupo de Vida de la sede con su carga actual."""
    event = require_event_access(db, current_user, event_id)
    user_sede_id = require_user_sede_id(db, current_user)
    return get_available_mentors(db, event.sede_id or user_sede_id)


@router.post("/events/{event_id}/followup/auto-assign-mentors")
@academy_limiter.limit("30/minute")
def trigger_auto_assign_mentors(
    request: Request,
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_edit),
):
    """Ejecuta el algoritmo de asignación inteligente de mentores con balanceo de carga por zona."""
    event = require_event_access(db, current_user, event_id)
    user_sede_id = require_user_sede_id(db, current_user)

    result = auto_assign_event_mentors(
        db,
        event=event,
        user_sede_id=event.sede_id or user_sede_id,
        assigned_by_user_id=current_user.id,
    )
    db.commit()

    record_admin_action(
        db,
        actor=current_user,
        action="event_followup_auto_assign",
        resource_type="event",
        resource_id=str(event_id),
        metadata=result,
    )

    return result


@router.put("/events/{event_id}/followup/assign-mentor")
@academy_limiter.limit("30/minute")
def update_manual_mentor_assignment(
    request: Request,
    event_id: UUID,
    payload: ManualAssignMentorPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_edit),
):
    """Asignación manual o reasignación de mentor a un asistente específico."""
    event = require_event_access(db, current_user, event_id)

    try:
        result = manual_assign_mentor(
            db,
            event=event,
            persona_id=payload.persona_id,
            mentor_persona_id=payload.mentor_persona_id,
            suggested_group_id=payload.suggested_group_id,
            notes=payload.notes,
            current_user_id=current_user.id,
        )
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    record_admin_action(
        db,
        actor=current_user,
        action="event_followup_manual_assign",
        resource_type="event",
        resource_id=str(event_id),
        metadata={
            "persona_id": str(payload.persona_id),
            "mentor_persona_id": str(payload.mentor_persona_id),
        },
    )

    return result


@router.post("/events/{event_id}/followup/trigger-step")
@academy_limiter.limit("30/minute")
def trigger_sequence_step(
    request: Request,
    event_id: UUID,
    payload: TriggerStepPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_edit),
):
    """Despacha manualmente un paso específico de la secuencia (ej. 24h, 72h o 7d)."""
    event = require_event_access(db, current_user, event_id)

    regs_query = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.deleted_at.is_(None),
            models.EventRegistration.registration_status == "CHECKED_IN",
        )
    )
    if payload.persona_ids:
        regs_query = regs_query.filter(models.EventRegistration.persona_id.in_(payload.persona_ids))

    registrations = regs_query.all()
    if not registrations:
        return {
            "success": True,
            "dispatched_count": 0,
            "already_sent_count": 0,
            "message": "No se encontraron inscripciones con check-in para despachar.",
        }

    dispatched = 0
    already_sent = 0
    errors = []

    for reg in registrations:
        if not reg.persona:
            continue
        try:
            res = dispatch_followup_step(
                db,
                event=event,
                persona=reg.persona,
                registration=reg,
                step_number=payload.step_number,
                force=payload.force,
                custom_content=payload.custom_content,
            )
            if res.get("already_sent"):
                already_sent += 1
            else:
                dispatched += 1
        except Exception as exc:
            errors.append({"persona_id": str(reg.persona_id), "error": str(exc)})
            logger.warning("Error dispatching step %s to persona %s: %s", payload.step_number, reg.persona_id, exc)

    db.commit()

    record_admin_action(
        db,
        actor=current_user,
        action="event_followup_trigger_step",
        resource_type="event",
        resource_id=str(event_id),
        metadata={
            "step_number": payload.step_number,
            "dispatched": dispatched,
            "already_sent": already_sent,
        },
    )

    return {
        "success": True,
        "step_number": payload.step_number,
        "dispatched_count": dispatched,
        "already_sent_count": already_sent,
        "errors": errors,
        "message": f"Se despachó el paso {payload.step_number} a {dispatched} personas ({already_sent} ya lo tenían enviado).",
    }


@router.post("/events/{event_id}/followup/record-response")
@academy_limiter.limit("30/minute")
def record_attendee_response(
    request: Request,
    event_id: UUID,
    payload: RecordResponsePayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_edit),
):
    """Registra la respuesta o retroalimentación del asistente en la secuencia."""
    event = require_event_access(db, current_user, event_id)

    try:
        result = record_followup_response(
            db,
            event=event,
            persona_id=payload.persona_id,
            notes=payload.notes,
            channel=payload.channel,
        )
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    record_admin_action(
        db,
        actor=current_user,
        action="event_followup_record_response",
        resource_type="event",
        resource_id=str(event_id),
        metadata={"persona_id": str(payload.persona_id)},
    )

    return result
