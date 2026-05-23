import datetime
from typing import List, Optional

from pydantic import BaseModel

new_routes = """
# --- EVENT SESSIONS & ASSIGNMENTS ---

class EventAssignmentSchema(BaseModel):
    member_id: int
    role: str

class EventSessionSync(BaseModel):
    session_date: datetime.date
    assignments: List[EventAssignmentSchema]

@router.get("/events/{event_id}/sessions/{session_date}")
def get_event_session_detail(
    event_id: int,
    session_date: datetime.date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    assignments_db = db.query(models.EventAssignment).filter(
        models.EventAssignment.event_id == event_id,
        models.EventAssignment.session_date == session_date
    ).all()

    assignments = []
    for a in assignments_db:
        assignments.append({
            "id": a.id,
            "member_id": a.member_id,
            "role": a.role,
            "member_name": f"{a.member.first_name} {a.member.last_name}" if a.member else "Unknown"
        })

    # Asistencia
    attendances_db = db.query(models.EventAttendance).filter(
        models.EventAttendance.event_id == event_id,
        models.EventAttendance.session_date == session_date
    ).all()

    liderazgo_roles = ["Apóstol", "Profeta", "Evangelista", "Pastor", "Maestro", "Líder"]

    metrics = {
        "Liderazgo": 0,
        "Servidor": 0,
        "Miembro Bautizado": 0,
        "Asistente": 0,
        "Visitante Servicios": 0,
        "Visitante Faro en Casa": 0,
        "Visitante Online": 0,
        "Otros": 0
    }

    attendee_list = []
    for att in attendances_db:
        member = att.member
        if not member:
            continue
        
        role = member.church_role or "Miembro"
        # Categorize
        if role in liderazgo_roles:
            metrics["Liderazgo"] += 1
        elif role == "Servidor":
            metrics["Servidor"] += 1
        elif role == "Miembro Bautizado":
            metrics["Miembro Bautizado"] += 1
        elif role in ["Asistentes", "Asistente"]:
            metrics["Asistente"] += 1
        elif "Visitante Servicios" in role:
            metrics["Visitante Servicios"] += 1
        elif "Visitante Faro" in role:
            metrics["Visitante Faro en Casa"] += 1
        elif "Online" in role:
            metrics["Visitante Online"] += 1
        else:
            metrics["Otros"] += 1

        attendee_list.append({
            "member_id": member.id,
            "name": f"{member.first_name} {member.last_name}",
            "role": role,
            "scanned_at": att.scanned_at.isoformat() if att.scanned_at else None
        })

    return {
        "event_id": event.id,
        "session_date": session_date.isoformat(),
        "assignments": assignments,
        "metrics": metrics,
        "attendees": attendee_list,
        "total_attendance": len(attendee_list)
    }

@router.post("/events/{event_id}/assignments")
def sync_event_assignments(
    event_id: int,
    payload: EventSessionSync,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    # Verify event exists
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Delete existing assignments for this session
    db.query(models.EventAssignment).filter(
        models.EventAssignment.event_id == event_id,
        models.EventAssignment.session_date == payload.session_date
    ).delete()

    # Create new
    for a in payload.assignments:
        new_assign = models.EventAssignment(
            event_id=event_id,
            session_date=payload.session_date,
            member_id=a.member_id,
            role=a.role
        )
        db.add(new_assign)
    
    db.commit()
    return {"success": True, "message": "Agenda configurada correctamente"}
"""

with open("backend/api/crm.py", "a", encoding="utf-8") as f:
    f.write(new_routes)
