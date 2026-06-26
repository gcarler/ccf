from __future__ import annotations

from typing import List

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.permissions import require_module_access
from backend.core.database import get_db
from backend.crud.crm import get_user_sede_id
from backend.crud.projects import get_user_persona_id

router = APIRouter(prefix="/agenda", tags=["agenda"])


@router.get("/events", response_model=List[schemas.AgendaEvent])
def list_agenda_events(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("spiritual_life", "read")),
):
    sede_id = get_user_sede_id(db, current_user.id)
    query = (
        db.query(models.AgendaEvent)
        .outerjoin(models.Persona, models.AgendaEvent.created_by_persona_id == models.Persona.id)
        .filter(models.AgendaEvent.deleted_at.is_(None))
        .filter(
            or_(
                models.AgendaEvent.created_by_persona_id.is_(None),
                models.Persona.sede_id == sede_id,
            )
        )
    )
    return query.order_by(models.AgendaEvent.start_at.asc(), models.AgendaEvent.id.asc()).all()


@router.post("/events", response_model=schemas.AgendaEvent)
def create_agenda_event(
    payload: schemas.AgendaEventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("spiritual_life", "read")),
):
    creator_persona_id = get_user_persona_id(db, current_user.id)
    agenda_event = models.AgendaEvent(
        title=payload.title,
        description=payload.description,
        start_at=payload.start_at,
        end_at=payload.end_at,
        location=payload.location,
        is_all_day=payload.is_all_day,
        created_by_persona_id=creator_persona_id,
    )
    db.add(agenda_event)
    db.commit()
    db.refresh(agenda_event)
    return agenda_event


@router.get("/events/{event_id}", response_model=schemas.AgendaEvent)
def get_agenda_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("spiritual_life", "read")),
):
    sede_id = get_user_sede_id(db, current_user.id)
    agenda_event = (
        db.query(models.AgendaEvent)
        .outerjoin(models.Persona, models.AgendaEvent.created_by_persona_id == models.Persona.id)
        .filter(
            models.AgendaEvent.id == event_id,
            models.AgendaEvent.deleted_at.is_(None),
            or_(
                models.AgendaEvent.created_by_persona_id.is_(None),
                models.Persona.sede_id == sede_id,
            ),
        )
        .first()
    )
    if not agenda_event:
        raise HTTPException(status_code=404, detail="Agenda event not found")
    return agenda_event


@router.put("/events/{event_id}", response_model=schemas.AgendaEvent)
def update_agenda_event(
    event_id: str,
    payload: schemas.AgendaEventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("spiritual_life", "read")),
):
    sede_id = get_user_sede_id(db, current_user.id)
    agenda_event = (
        db.query(models.AgendaEvent)
        .outerjoin(models.Persona, models.AgendaEvent.created_by_persona_id == models.Persona.id)
        .filter(
            models.AgendaEvent.id == event_id,
            models.AgendaEvent.deleted_at.is_(None),
            or_(
                models.AgendaEvent.created_by_persona_id.is_(None),
                models.Persona.sede_id == sede_id,
            ),
        )
        .first()
    )
    if not agenda_event:
        raise HTTPException(status_code=404, detail="Agenda event not found")

    agenda_event.title = payload.title
    agenda_event.description = payload.description
    agenda_event.start_at = payload.start_at
    agenda_event.end_at = payload.end_at
    agenda_event.location = payload.location
    agenda_event.is_all_day = payload.is_all_day
    db.commit()
    db.refresh(agenda_event)
    return agenda_event


@router.delete("/events/{event_id}", response_model=dict)
def delete_agenda_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("spiritual_life", "read")),
):
    sede_id = get_user_sede_id(db, current_user.id)
    agenda_event = (
        db.query(models.AgendaEvent)
        .outerjoin(models.Persona, models.AgendaEvent.created_by_persona_id == models.Persona.id)
        .filter(
            models.AgendaEvent.id == event_id,
            models.AgendaEvent.deleted_at.is_(None),
            or_(
                models.AgendaEvent.created_by_persona_id.is_(None),
                models.Persona.sede_id == sede_id,
            ),
        )
        .first()
    )
    if not agenda_event:
        raise HTTPException(status_code=404, detail="Agenda event not found")

    agenda_event.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "deleted", "id": event_id}
