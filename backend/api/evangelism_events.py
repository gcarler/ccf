from __future__ import annotations

import calendar
import uuid
import collections
import csv
import datetime
import io
import math
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.evangelism_shared import (ABSENTEES_PREVIEW_LIMIT,
                                           get_expected_members_for_event,
                                           normalize_role_scope_payload,
                                           parse_session_date, utc_now)
from backend.auth import (normalize_role, require_active_user, require_module_access,
                          require_pastor_or_admin)
from backend.core.audit import record_admin_action
from backend.core.database import get_db

router = APIRouter()


# ── Permission helpers ──

def _is_event_admin_or_pastor(user: models.User) -> bool:
    """Check if user is admin or pastor."""
    role = normalize_role(str(user.role))
    return role in {"admin", "pastor"}


def _is_event_assignee(db: Session, user: models.User, event_id: int) -> bool:
    """Check if user is assigned to this event (MC, preacher, offering, etc.)."""
    persona = db.query(models.Persona).filter(models.Persona.user_id == user.id).first()
    if not persona:
        return False
    assignment = db.query(models.EventAssignment).filter(
        models.EventAssignment.event_id == event_id,
        models.EventAssignment.persona_id == persona.id,
    ).first()
    return assignment is not None


def _require_event_access(db: Session, user: models.User, event_id: int):
    """Allow admin/pastor OR event assignees to access event data."""
    if _is_event_admin_or_pastor(user):
        return
    if _is_event_assignee(db, user, event_id):
        return
    raise HTTPException(
        status_code=403,
        detail="Permisos insuficientes. Solo admin, pastor o asignados al evento."
    )


@router.get("/events/", response_model=List[schemas.CrmEvent])
def list_events(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    if normalize_role(str(current_user.role)) not in {"admin", "pastor"}:
        raise HTTPException(
            status_code=403, detail="Permisos insuficientes. Se requiere: crm:manage"
        )
    return crud.get_crm_events(db, skip=skip, limit=limit)


@router.post("/events/", response_model=schemas.CrmEvent)
def create_event(
    payload: schemas.CrmEventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    payload = schemas.CrmEventCreate(
        **normalize_role_scope_payload(payload.model_dump())
    )
    event = crud.create_crm_event(db, payload)
    record_admin_action(
        db,
        current_user,
        action="create_event",
        resource_type="event",
        resource_id=str(event.id),
    )
    return event


@router.put("/events/{event_id}", response_model=dict)
def update_event(
    event_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    payload = normalize_role_scope_payload(payload)
    editable = [
        "name",
        "description",
        "location",
        "event_type",
        "target_audience",
        "target_role_id",
        "target_role_ids",
        "target_member_ids",
        "status",
        "cancellation_reason",
        "start_time",
        "end_time",
        "day_of_week",
        "month_day",
        "fixed_date",
    ]
    for field in editable:
        if field in payload:
            val = payload[field]
            if field == "fixed_date" and isinstance(val, str) and val:
                val = datetime.datetime.fromisoformat(val.replace("Z", "+00:00"))
            setattr(event, field, val)
    db.commit()
    db.refresh(event)
    record_admin_action(
        db,
        current_user,
        action="update_event",
        resource_type="event",
        resource_id=str(event.id),
    )
    return {"id": event.id, "name": event.name, "status": "updated"}


@router.delete("/events/{event_id}", response_model=dict)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Cancela un evento (soft-delete: marca como CANCELLED)."""
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.status = "CANCELLED"
    event.cancellation_reason = "Eliminado por usuario"
    db.commit()
    record_admin_action(
        db,
        current_user,
        action="cancel_event",
        resource_type="event",
        resource_id=str(event_id),
    )
    return {"status": "cancelled", "id": event_id}


@router.get("/events/{event_id}", response_model=dict)
def get_event_detail(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    _require_event_access(db, current_user, event_id)
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    attendees_count = (
        db.query(models.EventAttendance)
        .filter(models.EventAttendance.event_id == event_id)
        .count()
    )
    event_status = event.status or "SCHEDULED"
    if (
        event_status == "SCHEDULED"
        and event.event_date
        and event.event_date < utc_now()
    ):
        event_status = "COMPLETED"

    return {
        "id": event.id,
        "name": event.name,
        "title": event.name,
        "description": event.description,
        "event_date": event.event_date.isoformat() if event.event_date else None,
        "location": event.location,
        "attendees_count": attendees_count,
        "status": event_status,
        "cancellation_reason": event.cancellation_reason,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


@router.get("/events/{event_id}/attendance", response_model=dict)
def get_event_attendance_report(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    _require_event_access(db, current_user, event_id)
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    rows = (
        db.query(models.EventAttendance)
        .filter(models.EventAttendance.event_id == event_id)
        .join(models.Persona)
        .order_by(models.Persona.nombre_completo.asc())
        .all()
    )
    counts: dict[str, int] = {"present": 0, "absent": 0}
    present = []
    absent = []

    for row in rows:
        status_label = "present" if row.attended else "absent"
        counts[status_label] = counts.get(status_label, 0) + 1
        payload = {
            "persona_id": row.persona_id,
            "persona_name": (
                row.persona.nombre_completo
                if row.persona
                else "Miembro"
            ),
            "status": status_label,
            "session_date": row.session_date.isoformat() if row.session_date else None,
            "check_in_at": row.scanned_at.isoformat() if row.scanned_at else None,
        }
        if row.attended:
            present.append(payload)
        else:
            absent.append(payload)

    return {
        "event_id": event.id,
        "event_name": event.name,
        "total_records": len(rows),
        "counts": counts,
        "present": present,
        "absent": absent,
        "expected_members": [],
        "expected_count": 0,
        "other": [],
    }


@router.get("/personas/{persona_id}/attendance-history", response_model=dict)
def get_persona_attendance_history(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("evangelism", "read")),
):
    persona = db.query(models.Persona).filter(models.Persona.id == persona_id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    is_self = persona.user_id == current_user.id
    is_staff = normalize_role(str(current_user.role)) in [
        "admin",
        "pastor",
        "coordinador",
    ]
    if not is_self and not is_staff:
        raise HTTPException(
            status_code=403, detail="No autorizado para ver este historial"
        )

    rows = (
        db.query(models.EventAttendance)
        .filter(models.EventAttendance.persona_id == persona_id)
        .join(models.CrmEvent)
        .order_by(
            models.CrmEvent.event_date.desc().nullslast(),
            models.CrmEvent.created_at.desc(),
        )
        .all()
    )

    history = []
    for row in rows:
        history.append(
            {
                "event_id": row.event_id,
                "event_name": row.event.name if row.event else None,
                "event_date": (
                    row.event.event_date.isoformat()
                    if row.event and row.event.event_date
                    else None
                ),
                "session_date": (
                    row.session_date.isoformat() if row.session_date else None
                ),
                "status": "present" if row.attended else "absent",
                "check_in_at": row.scanned_at.isoformat() if row.scanned_at else None,
            }
        )

    return {
        "persona_id": persona.id,
        "persona_name": persona.nombre_completo,
        "total_records": len(history),
        "history": history,
    }


@router.post("/attendance", response_model=schemas.EventAttendance)
def register_attendance(
    payload: schemas.EventAttendanceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    _require_event_access(db, current_user, payload.event_id)
    return crud.create_event_attendance(db, payload)


@router.post("/attendance/bulk", response_model=dict)
def register_bulk_attendance(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    event_id = payload.get("event_id")
    if event_id:
        _require_event_access(db, current_user, event_id)
    persona_ids = payload.get("persona_ids", [])
    try:
        session_date = parse_session_date(
            payload.get("attendance_date") or payload.get("session_date")
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not event_id:
        raise HTTPException(status_code=400, detail="event_id is required")
    if not isinstance(persona_ids, list):
        raise HTTPException(status_code=400, detail="persona_ids must be a list")

    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if str(event.status or "").upper() == "CANCELLED":
        raise HTTPException(
            status_code=409,
            detail="No se puede registrar asistencia en eventos cancelados",
        )

    normalized_persona_ids: list[str] = []
    invalid_persona_ids: list[object] = []
    for raw_persona_id in persona_ids:
        if isinstance(raw_persona_id, str):
            normalized_persona_ids.append(raw_persona_id)
        else:
            invalid_persona_ids.append(raw_persona_id)

    normalized_persona_ids = list(dict.fromkeys(normalized_persona_ids))
    normalized_persona_uuids = []
    for pid in normalized_persona_ids:
        try:
            normalized_persona_uuids.append(uuid.UUID(pid))
        except ValueError:
            pass

    valid_persona_uuids = (
        {
            row[0]
            for row in db.query(models.Persona.id)
            .filter(models.Persona.id.in_(normalized_persona_uuids))
            .all()
        }
        if normalized_persona_uuids
        else set()
    )
    valid_persona_ids = {str(uid) for uid in valid_persona_uuids}
    missing_persona_ids = sorted(set(normalized_persona_ids) - valid_persona_ids)
    selected_persona_uuids = sorted(valid_persona_uuids)

    existing_rows = (
        db.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event_id,
            models.EventAttendance.session_date == session_date,
        )
        .all()
    )
    existing_by_persona_id = {row.persona_id: row for row in existing_rows}

    created_count = 0
    marked_present_count = 0
    marked_absent_count = 0
    now = utc_now()

    for persona_uuid in selected_persona_uuids:
        row = existing_by_persona_id.get(persona_uuid)
        if row:
            was_attended = bool(row.attended)
            row.attended = True
            row.status = "present"
            row.source = payload.get("source") or row.source or "manual"
            row.scanned_at = now
            row.check_in_at = now
            row.check_out_at = None
            if not was_attended:
                marked_present_count += 1
        else:
            row = models.EventAttendance(
                event_id=event_id,
                session_date=session_date,
                persona_id=persona_uuid,
                attended=True,
                status="present",
                source=payload.get("source") or "manual",
                scanned_at=now,
                check_in_at=now,
            )
            db.add(row)
            created_count += 1

    for row in existing_rows:
        if row.persona_id in selected_persona_uuids:
            continue
        if row.attended or row.status != "absent":
            row.attended = False
            row.status = "absent"
            row.check_out_at = now
            marked_absent_count += 1

    db.commit()
    return {
        "status": "success",
        "recorded": len(selected_persona_uuids),
        "created": created_count,
        "marked_present": marked_present_count,
        "marked_absent": marked_absent_count,
        "invalid_persona_ids": invalid_persona_ids + missing_persona_ids,
        "session_date": session_date.isoformat(),
    }


class EventAssignmentSchema(BaseModel):
    persona_id: str
    role: str


class EventSessionSync(BaseModel):
    session_date: datetime.date
    assignments: List[EventAssignmentSchema]


class RoleDefinitionCreate(BaseModel):
    name: str
    color: str
    is_leadership: bool


class RoleDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    is_leadership: Optional[bool] = None


class EventAudienceUpdate(BaseModel):
    target_audience: schemas.EventAudienceType
    target_role_id: Optional[int] = None
    target_role_ids: Optional[List[int]] = None
    target_member_ids: Optional[List[str]] = None


class VisitorCreate(BaseModel):
    first_name: str
    last_name: str
    phone: Optional[str] = None
    email: Optional[str] = None


@router.get("/events/{event_id}/sessions/{session_date}")
def get_event_session_detail(
    event_id: int,
    session_date: datetime.date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    _require_event_access(db, current_user, event_id)
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    assignments_db = (
        db.query(models.EventAssignment)
        .filter(
            models.EventAssignment.event_id == event_id,
            models.EventAssignment.session_date == session_date,
        )
        .all()
    )
    assignments = [
        {
            "id": a.id,
            "persona_id": a.persona_id,
            "member_id": a.persona_id,
            "role": a.role,
            "persona_name": (
                a.persona.nombre_completo if a.persona else "Unknown"
            ),
        }
        for a in assignments_db
    ]

    attendances_db = (
        db.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event_id,
            models.EventAttendance.session_date == session_date,
        )
        .all()
    )

    roles_db = db.query(models.RoleDefinition).all()
    roles_map = {r.name: r for r in roles_db}
    metrics = {"Liderazgo": 0}
    for role in roles_db:
        if not role.is_leadership:
            metrics[role.name] = 0
    metrics["Otros"] = 0

    attendee_list = []
    for att in attendances_db:
        persona = att.persona
        if not persona:
            continue
        role_name = persona.church_role or "Miembro"
        role_def = roles_map.get(role_name)
        if role_def and role_def.is_leadership:
            metrics["Liderazgo"] += 1
        elif role_name in metrics:
            metrics[role_name] += 1
        else:
            metrics["Otros"] += 1
        attendee_list.append(
            {
                "persona_id": persona.id,
                "member_id": persona.id,
                "name": persona.nombre_completo,
                "role": role_name,
                "scanned_at": att.scanned_at.isoformat() if att.scanned_at else None,
            }
        )

    expected_members = get_expected_members_for_event(db, event)
    attended_ids = {attendee["persona_id"] for attendee in attendee_list}
    absentees_full = []
    for persona in expected_members:
        if persona.id not in attended_ids:
            absentees_full.append(
                {
                    "persona_id": persona.id,
                    "member_id": persona.id,
                    "name": persona.nombre_completo,
                    "role": persona.church_role,
                    "phone": persona.phone,
                }
            )

    total_absentees = len(absentees_full)
    absentees_preview = absentees_full[:ABSENTEES_PREVIEW_LIMIT]

    return {
        "event_id": event.id,
        "session_date": session_date.isoformat(),
        "assignments": assignments,
        "metrics": metrics,
        "attendees": attendee_list,
        "absentees": absentees_preview,
        "total_absentees": total_absentees,
        "absentees_truncated": total_absentees > ABSENTEES_PREVIEW_LIMIT,
        "total_attendance": len(attendee_list),
        "total_expected": len(expected_members),
        "attendance_rate": (
            round(len(attendee_list) / len(expected_members) * 100, 1)
            if expected_members
            else 0
        ),
    }


@router.post("/events/{event_id}/assignments")
def sync_event_assignments(
    event_id: int,
    payload: EventSessionSync,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    db.query(models.EventAssignment).filter(
        models.EventAssignment.event_id == event_id,
        models.EventAssignment.session_date == payload.session_date,
    ).delete()

    for assignment in payload.assignments:
        db.add(
            models.EventAssignment(
                event_id=event_id,
                session_date=payload.session_date,
                persona_id=assignment.persona_id,
                role=assignment.role,
            )
        )
    db.commit()
    return {"success": True, "message": "Agenda configurada correctamente"}


@router.get("/roles")
def get_roles(
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_active_user),
):
    return (
        db.query(models.RoleDefinition)
        .order_by(
            models.RoleDefinition.is_leadership.desc(), models.RoleDefinition.name.asc()
        )
        .all()
    )


@router.post("/roles")
def create_role(
    payload: RoleDefinitionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    exists = (
        db.query(models.RoleDefinition)
        .filter(models.RoleDefinition.name == payload.name)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="El rol ya existe")
    role = models.RoleDefinition(**payload.model_dump())
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.put("/roles/{role_id}")
def update_role(
    role_id: int,
    payload: RoleDefinitionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    role = (
        db.query(models.RoleDefinition)
        .filter(models.RoleDefinition.id == role_id)
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    if payload.name is not None:
        exists = (
            db.query(models.RoleDefinition)
            .filter(
                models.RoleDefinition.name == payload.name,
                models.RoleDefinition.id != role_id,
            )
            .first()
        )
        if exists:
            raise HTTPException(
                status_code=400, detail="Ya existe otro rol con ese nombre"
            )
        db.query(models.Persona).filter(models.Persona.church_role == role.name).update(
            {"church_role": payload.name}
        )
        role.name = payload.name

    if payload.color is not None:
        role.color = payload.color
    if payload.is_leadership is not None:
        role.is_leadership = payload.is_leadership

    db.commit()
    db.refresh(role)
    return role


@router.delete("/roles/{role_id}")
def delete_role(
    role_id: int,
    fallback_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    if fallback_id == role_id:
        raise HTTPException(
            status_code=400,
            detail="El rol de reemplazo no puede ser el mismo rol a eliminar",
        )

    role = (
        db.query(models.RoleDefinition)
        .filter(models.RoleDefinition.id == role_id)
        .first()
    )
    fallback = (
        db.query(models.RoleDefinition)
        .filter(models.RoleDefinition.id == fallback_id)
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="Rol a eliminar no encontrado")
    if not fallback:
        raise HTTPException(status_code=400, detail="Rol de reemplazo no valido")
    if role.is_system_locked:
        raise HTTPException(status_code=400, detail="No se puede eliminar un rol del sistema")

    # Reasignar miembros al rol de reemplazo
    db.query(models.Persona).filter(models.Persona.church_role == role.name).update(
        {"church_role": fallback.name}
    )

    # Soft-delete: marcar como inactivo y renombrar para liberar el unique constraint
    from datetime import datetime
    suffix = datetime.utcnow().strftime("_deleted_%Y%m%d_%H%M%S")
    role.name = f"{role.name}{suffix}"
    role.is_leadership = False
    db.commit()
    return {
        "success": True,
        "message": f"Rol '{role.name}' desactivado y miembros reasignados a '{fallback.name}'",
    }


@router.put("/events/{event_id}/audience")
def update_event_audience(
    event_id: int,
    payload: EventAudienceUpdate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    normalized = normalize_role_scope_payload(payload.model_dump())
    event.target_audience = normalized["target_audience"]
    event.target_role_id = normalized.get("target_role_id")
    event.target_role_ids = normalized.get("target_role_ids")
    event.target_member_ids = normalized.get("target_member_ids")
    db.commit()
    return {"success": True}


@router.get("/events/analytics/global")
def get_global_event_analytics(
    period: str = Query("MONTH"),
    event_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    from sqlalchemy import func

    query = db.query(
        models.EventAttendance.session_date,
        func.count(models.EventAttendance.id).label("attended_count"),
    ).join(models.CrmEvent)

    if event_type and event_type != "ALL":
        query = query.filter(models.CrmEvent.event_type == event_type)

    daily_stats = query.group_by(models.EventAttendance.session_date).all()
    bucket_map = {}

    for row in daily_stats:
        session_day = row.session_date
        if not session_day:
            continue
        if hasattr(session_day, "date"):
            session_day = session_day.date()

        if period == "WEEK":
            isocal = session_day.isocalendar()
            key = f"{isocal[0]}-W{isocal[1]:02d}"
            label = f"Sem {isocal[1]}, {isocal[0]}"
        elif period == "MONTH":
            key = session_day.strftime("%Y-%m")
            label = f"{calendar.month_abbr[session_day.month]} {session_day.year}"
        elif period == "BIMESTER":
            bimester = math.ceil(session_day.month / 2)
            key = f"{session_day.year}-B{bimester}"
            label = f"Bimestre {bimester}, {session_day.year}"
        elif period == "TRIMESTER":
            trimester = math.ceil(session_day.month / 3)
            key = f"{session_day.year}-Q{trimester}"
            label = f"Trim {trimester}, {session_day.year}"
        elif period == "SEMESTER":
            semester = math.ceil(session_day.month / 6)
            key = f"{session_day.year}-S{semester}"
            label = f"Semestre {semester}, {session_day.year}"
        elif period == "YEAR":
            key = f"{session_day.year}"
            label = f"{session_day.year}"
        else:
            key = session_day.strftime("%Y-%m")
            label = f"{calendar.month_abbr[session_day.month]} {session_day.year}"

        if key not in bucket_map:
            bucket_map[key] = {"key": key, "label": label, "total": 0, "sessions": 0}
        bucket_map[key]["total"] += row.attended_count
        bucket_map[key]["sessions"] += 1

    series = []
    for key in sorted(bucket_map.keys()):
        bucket = bucket_map[key]
        bucket["avg"] = (
            round(bucket["total"] / bucket["sessions"]) if bucket["sessions"] > 0 else 0
        )
        series.append(bucket)

    total_attendance = sum(bucket["total"] for bucket in bucket_map.values())
    total_sessions = sum(bucket["sessions"] for bucket in bucket_map.values())
    avg_per_session = (
        round(total_attendance / total_sessions) if total_sessions > 0 else 0
    )
    peak_period = (
        max(series, key=lambda item: item["total"])
        if series
        else {"label": "N/A", "total": 0}
    )

    trend = 0
    if len(series) >= 2:
        last = series[-1]["total"]
        previous = series[-2]["total"]
        if previous > 0:
            trend = round(((last - previous) / previous) * 100, 1)

    return {
        "kpis": {
            "total_attendance": total_attendance,
            "avg_per_session": avg_per_session,
            "peak_period": peak_period,
            "trend_percentage": trend,
        },
        "series": series,
    }


@router.get("/events/dashboard-stats")
def get_events_dashboard_stats(
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    events = db.query(models.CrmEvent).all()
    if not events:
        return []

    event_ids = [e.id for e in events]

    # Single query: get latest session date per event
    from sqlalchemy import func
    latest_dates = dict(
        db.query(
            models.EventAttendance.event_id,
            func.max(models.EventAttendance.session_date),
        )
        .filter(models.EventAttendance.event_id.in_(event_ids))
        .group_by(models.EventAttendance.event_id)
        .all()
    )

    # Single query: get attendance count per event per latest date
    latest_pairs = [(eid, dt) for eid, dt in latest_dates.items()]
    attendance_counts = {}
    if latest_pairs:
        from sqlalchemy import tuple_
        counts = (
            db.query(
                models.EventAttendance.event_id,
                models.EventAttendance.session_date,
                func.count(models.EventAttendance.id),
            )
            .filter(
                tuple_(
                    models.EventAttendance.event_id,
                    models.EventAttendance.session_date,
                ).in_(latest_pairs)
            )
            .group_by(
                models.EventAttendance.event_id,
                models.EventAttendance.session_date,
            )
            .all()
        )
        for event_id, session_date, cnt in counts:
            attendance_counts[(event_id, session_date)] = cnt

    stats = []
    for event in events:
        latest_date = latest_dates.get(event.id)
        if latest_date:
            attended = attendance_counts.get((event.id, latest_date), 0)
            expected = len(get_expected_members_for_event(db, event))
            rate = round((attended / expected) * 100, 1) if expected > 0 else 0
            stats.append({
                "event_id": event.id,
                "latest_session": latest_date.isoformat(),
                "attended": attended,
                "expected": expected,
                "rate": rate,
            })
        else:
            stats.append({
                "event_id": event.id,
                "latest_session": None,
                "attended": 0,
                "expected": 0,
                "rate": 0,
            })

    return stats


@router.get("/events/{event_id}/analytics")
def get_event_analytics(
    event_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    attendances = (
        db.query(models.EventAttendance)
        .filter(models.EventAttendance.event_id == event_id)
        .all()
    )
    sessions_by_month = collections.defaultdict(set)
    attendees_by_session = collections.defaultdict(int)

    for attendance in attendances:
        if attendance.session_date:
            month_key = attendance.session_date.strftime("%Y-%m")
            sessions_by_month[month_key].add(attendance.session_date)
            attendees_by_session[attendance.session_date] += 1

    monthly_data = []
    total_sessions = 0
    total_attendance_all = 0
    peak_month = {"month": "-", "avg": 0}

    for month in sorted(sessions_by_month.keys()):
        sessions = sessions_by_month[month]
        total_att_month = sum(attendees_by_session[session] for session in sessions)
        avg_att = round(total_att_month / len(sessions)) if sessions else 0
        monthly_data.append(
            {"month": month, "avg_attendance": avg_att, "total_sessions": len(sessions)}
        )
        total_sessions += len(sessions)
        total_attendance_all += total_att_month
        if avg_att > peak_month["avg"]:
            peak_month = {"month": month, "avg": avg_att}

    historical_avg = (
        round(total_attendance_all / total_sessions) if total_sessions > 0 else 0
    )
    trend = 0
    if len(monthly_data) >= 2:
        last = monthly_data[-1]["avg_attendance"]
        previous = monthly_data[-2]["avg_attendance"]
        if previous > 0:
            trend = round(((last - previous) / previous) * 100, 1)

    return {
        "monthly_data": monthly_data,
        "kpis": {
            "historical_avg": historical_avg,
            "peak_month": peak_month,
            "trend_percentage": trend,
        },
    }


@router.post("/events/{event_id}/sessions/{session_date}/visitors")
def fast_checkin_visitor(
    event_id: int,
    session_date: str,
    visitor: VisitorCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    _require_event_access(db, current_user, event_id)
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    try:
        session_day = datetime.datetime.strptime(session_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format, expected YYYY-MM-DD"
        )

    role_name = "Visitante Servicios"
    role = (
        db.query(models.RoleDefinition)
        .filter(models.RoleDefinition.name == role_name)
        .first()
    )
    if not role:
        role = models.RoleDefinition(name=role_name, is_system_locked=True)
        db.add(role)
        db.commit()
        db.refresh(role)

    existing_persona = None
    if visitor.email:
        existing_persona = (
            db.query(models.Persona).filter(models.Persona.email == visitor.email).first()
        )
    if not existing_persona and visitor.phone:
        existing_persona = (
            db.query(models.Persona).filter(models.Persona.phone == visitor.phone).first()
        )

    if existing_persona:
        new_visitor = existing_persona
        already_exists = True
    else:
        already_exists = False
        nombre_completo = f"{visitor.first_name} {visitor.last_name}".strip()
        new_visitor = models.Persona(
            nombre_completo=nombre_completo,
            phone=visitor.phone,
            email=visitor.email,
            church_role=role_name,
        )
        db.add(new_visitor)
        db.commit()
        db.refresh(new_visitor)

    if role:
        db.add(models.MemberRole(persona_id=new_visitor.id, role_id=role.id))

    db.add(
        models.EventAttendance(
            event_id=event_id,
            session_date=session_day,
            persona_id=new_visitor.id,
            attended=True,
        )
    )

    # Create CRM follow-up records for new visitors
    if not already_exists:
        # ConsolidationCase for follow-up tracking
        case = models.ConsolidationCase(
            persona_id=new_visitor.id,
            stage="new",
            status="active",
            source="evangelism_event",
        )
        db.add(case)

    db.commit()

    message = (
        "Visitante ya registrado. Asistencia actualizada."
        if already_exists
        else "Visitante registrado y marcado como presente"
    )
    return {
        "status": "success",
        "visitor_id": new_visitor.id,
        "message": message,
        "is_duplicate": already_exists,
    }


@router.get("/events/{event_id}/sessions/{session_date}/export")
def export_event_session_report(
    event_id: int,
    session_date: datetime.date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    attendances_db = (
        db.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event_id,
            models.EventAttendance.session_date == session_date,
        )
        .all()
    )
    attended_ids = {row.persona_id for row in attendances_db}
    expected_members = get_expected_members_for_event(db, event)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=",", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(
        ["Nombre Completo", "Telefono", "Email", "Rol", "Estado Asistencia"]
    )

    for persona in expected_members:
        status = "Presente" if persona.id in attended_ids else "Ausente"
        writer.writerow(
            [
                persona.nombre_completo,
                persona.phone or "",
                persona.email or "",
                persona.church_role or "Miembro",
                status,
            ]
        )

    expected_ids = {persona.id for persona in expected_members}
    for attendance in attendances_db:
        if attendance.persona_id not in expected_ids and attendance.persona:
            persona = attendance.persona
            writer.writerow(
                [
                    persona.nombre_completo,
                    persona.phone or "",
                    persona.email or "",
                    persona.church_role or "Visitante Servicios",
                    "Presente (Invitado/No Esperado)",
                ]
            )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=reporte_asistencia_{event.name}_{session_date}.csv"
        },
    )
