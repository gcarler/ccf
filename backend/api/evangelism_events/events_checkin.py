from __future__ import annotations

import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import models
from backend.api.evangelism_events._shared import require_event_access
from backend.core.database import get_db
from backend.core.permissions import require_active_user
from backend.core.tenant import require_user_sede_id

router = APIRouter()


class VisitorCreate(BaseModel):
    first_name: str
    last_name: str
    phone: Optional[str] = None
    email: Optional[str] = None


@router.post("/events/{event_id}/sessions/{session_date}/visitors")
def fast_checkin_visitor(
    event_id: UUID,
    session_date: str,
    visitor: VisitorCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    require_event_access(db, current_user, event_id)
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    try:
        session_day = datetime.datetime.strptime(session_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, expected YYYY-MM-DD")

    role_name = "Visitante Servicios"
    role = db.query(models.RoleDefinition).filter(models.RoleDefinition.name == role_name).first()
    if not role:
        role = models.RoleDefinition(name=role_name, is_system_locked=True)
        db.add(role)
        db.commit()
        db.refresh(role)

    existing_persona = None
    if visitor.email:
        existing_persona = db.query(models.Persona).filter(models.Persona.email == visitor.email).first()
    if not existing_persona and visitor.phone:
        existing_persona = db.query(models.Persona).filter(models.Persona.phone == visitor.phone).first()

    if existing_persona:
        new_visitor = existing_persona
        already_exists = True
    else:
        already_exists = False
        sede_id = event.sede_id or require_user_sede_id(db, current_user)
        new_visitor = models.Persona(
            first_name=visitor.first_name,
            last_name=visitor.last_name,
            phone=visitor.phone,
            email=visitor.email,
            sede_id=sede_id,
            church_role=role_name,
        )
        db.add(new_visitor)
        db.commit()
        db.refresh(new_visitor)

    # Si el visitante ya estaba registrado (por email o phone), devolvemos marcador
    # de duplicado SIN re-insertar EventAttendance (UNIQUE constraint
    # event_id + session_date + persona_id). Esto evita el 500 al hacer
    # check-in dos veces para la misma persona y misma sesión.
    if already_exists:
        return {
            "status": "success",
            "visitor_id": new_visitor.id,
            "message": "Visitante ya registrado. Asistencia actualizada.",
            "is_duplicate": True,
        }

    if role:
        db.add(models.PersonaRoleLink(persona_id=new_visitor.id, role_id=role.id))

    db.add(
        models.EventAttendance(
            event_id=event_id,
            session_date=session_day,
            persona_id=new_visitor.id,
            attended=True,
        )
    )

    # Create CRM follow-up records for new visitors
    from backend.services.evangelism_crm_bridge import crear_caso_nuevo_visitante
    crear_caso_nuevo_visitante(db, new_visitor, new_visitor.sede_id)

    db.commit()

    return {
        "status": "success",
        "visitor_id": new_visitor.id,
        "message": "Visitante registrado y marcado como presente",
        "is_duplicate": False,
    }
