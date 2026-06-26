from __future__ import annotations

import datetime
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.evangelism_events._shared import require_event_access
from backend.api.evangelism_shared import (
    ABSENTEES_PREVIEW_LIMIT,
    get_expected_members_for_event,
    parse_session_date,
    utc_now,
)
from backend.core.permissions import require_active_user, require_pastor_or_admin
from backend.core.database import get_db
from backend.crud._utils import _utcnow

router = APIRouter()


class EventAssignmentSchema(BaseModel):
    persona_id: str
    role: str


class EventSessionSync(BaseModel):
    session_date: datetime.date
    assignments: List[EventAssignmentSchema]


@router.get("/events/{event_id}/attendance", response_model=dict)
def get_event_attendance_report(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    require_event_access(db, current_user, event_id)
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
            "persona_name": (row.persona.nombre_completo if row.persona else "Miembro"),
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


@router.post("/attendance", response_model=schemas.EventAttendance)
def register_attendance(
    payload: schemas.EventAttendanceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    require_event_access(db, current_user, payload.event_id)
    return crud.create_event_attendance(db, payload)


@router.post("/attendance/bulk", response_model=dict)
def register_bulk_attendance(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    event_id = payload.get("event_id")
    if event_id:
        require_event_access(db, current_user, event_id)
    persona_ids = payload.get("persona_ids", [])
    try:
        session_date = parse_session_date(payload.get("attendance_date") or payload.get("session_date"))
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
        {row[0] for row in db.query(models.Persona.id).filter(models.Persona.id.in_(normalized_persona_uuids)).all()}
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


@router.get("/events/{event_id}/sessions/{session_date}")
def get_event_session_detail(
    event_id: int,
    session_date: datetime.date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    require_event_access(db, current_user, event_id)
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
            "persona_name": (a.persona.nombre_completo if a.persona else "Unknown"),
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
        "attendance_rate": (round(len(attendee_list) / len(expected_members) * 100, 1) if expected_members else 0),
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
    ).update({models.EventAssignment.deleted_at: _utcnow()}, synchronize_session=False)

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
