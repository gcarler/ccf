from __future__ import annotations

import datetime
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import models
from backend.api.evangelism_events._shared import require_event_access
from backend.core.database import get_db
from backend.core.permissions import require_evangelism_edit
from backend.core.tenant import require_user_sede_id

router = APIRouter()
logger = logging.getLogger(__name__)


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
    current_user: models.User = Depends(require_evangelism_edit),
):
    event = require_event_access(db, current_user, event_id)
    user_sede_id = require_user_sede_id(db, current_user)

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

    attendance_lookup = db.query(models.EventAttendance).join(models.Persona).filter(
        models.EventAttendance.event_id == event_id,
        models.EventAttendance.session_date == session_day,
    )
    identifiers = []
    if visitor.email:
        identifiers.append(models.Persona.email == visitor.email)
    if visitor.phone:
        identifiers.append(models.Persona.phone == visitor.phone)
    if identifiers and attendance_lookup.filter(or_(*identifiers)).first():
        existing_attendance = attendance_lookup.filter(or_(*identifiers)).first()
        return {
            "status": "success",
            "visitor_id": existing_attendance.persona_id,
            "message": "Visitante ya registrado. Asistencia actualizada.",
            "is_duplicate": True,
        }

    existing_persona = None
    if visitor.email:
        candidate = db.query(models.Persona).filter(models.Persona.email == visitor.email).first()
        if candidate and str(candidate.sede_id) == str(user_sede_id):
            existing_persona = candidate
    if not existing_persona and visitor.phone:
        candidate = db.query(models.Persona).filter(models.Persona.phone == visitor.phone).first()
        if candidate and str(candidate.sede_id) == str(user_sede_id):
            existing_persona = candidate

    if existing_persona:
        new_visitor = existing_persona
        is_new_visitor = False
    else:
        is_new_visitor = True
        sede_id = event.sede_id or user_sede_id
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

    # La idempotencia es de asistencia, no de persona: un miembro ya existente
    # puede asistir por primera vez a esta sesión.
    if is_new_visitor and role:
        db.add(models.PersonaRoleLink(persona_id=new_visitor.id, role_id=role.id))

    attendance = models.EventAttendance(
        event_id=event_id,
        session_date=session_day,
        persona_id=new_visitor.id,
        attended=True,
    )
    db.add(attendance)
    # Persist the core check-in before the optional CRM bridge. A bridge
    # integration failure must never make a successful attendance disappear.
    db.commit()

    # Create CRM follow-up records for new visitors.
    # This is auxiliary: if the CRM bridge is temporarily out of sync with
    # production schema, we keep the visitor registration successful.
    from backend.services.evangelism_crm_bridge import crear_caso_nuevo_visitante

    if is_new_visitor:
        try:
            crear_caso_nuevo_visitante(db, new_visitor, new_visitor.sede_id)
        except Exception as exc:
            logger.warning("Failed to create CRM follow-up for evangelism event visitor %s: %s", new_visitor.id, exc)

    return {
        "status": "success",
        "visitor_id": new_visitor.id,
        "message": "Visitante registrado y marcado como presente",
        "is_duplicate": False,
    }
