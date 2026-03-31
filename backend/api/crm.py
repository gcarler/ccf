from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime
from backend import crud, schemas, models
from backend.core.database import get_db
from backend.auth import get_current_user, require_admin, require_pastor_or_admin
from backend.core.audit import record_admin_action

router = APIRouter(tags=["CRM"])

# --- MEMBERS ENDPOINTS ---

@router.get("/members", response_model=List[schemas.Member])
def list_members(
    search: Optional[str] = None, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Lista miembros con tipado estricto y búsqueda optimizada."""
    return crud.search_members(db, search=search)

@router.post("/members/", response_model=schemas.Member)
def create_member(
    payload: schemas.MemberCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Registra un nuevo miembro en el CRM."""
    return crud.create_member(db, payload)

@router.get("/members/me", response_model=dict)
def get_my_crm_card(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Devuelve la tarjeta de miembro del usuario actual."""
    member = crud.get_members(db, search=current_user.email)
    if member and len(member) > 0:
        m = member[0]
        return {
            "id": m.id,
            "first_name": m.first_name,
            "last_name": m.last_name,
            "church_role": m.church_role,
            "qr_code": f"CCF-MBR-{m.id}-{uuid.uuid4().hex[:6]}"
        }
    return {
        "id": 0,
        "first_name": current_user.username,
        "last_name": "Usuario",
        "church_role": current_user.role,
        "qr_code": f"CCF-USR-{current_user.id}-{uuid.uuid4().hex[:6]}"
    }

@router.get("/members/{member_id}", response_model=schemas.Member)
def get_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member

@router.patch("/members/{member_id}", response_model=schemas.Member)
def update_member(
    member_id: int,
    payload: schemas.MemberUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Actualiza datos de un miembro con persistencia y auditoría."""
    member = crud.update_member(db, member_id=member_id, payload=payload)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    record_admin_action(
        db, current_user,
        action="update_member",
        resource_type="member",
        resource_id=str(member.id),
        metadata=payload.model_dump(exclude_unset=True)
    )
    return member

@router.delete("/members/{member_id}", status_code=204)
def delete_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    db.delete(member)
    db.commit()
    return None

@router.get("/members/{member_id}/communications", response_model=List[schemas.CommunicationLog])
def get_member_communications(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return db.query(models.CommunicationLog).filter(models.CommunicationLog.member_id == member_id).all()

@router.get("/members/{member_id}/donations", response_model=List[schemas.Donation])
def list_member_donations(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.get_member_donations(db, member_id=member_id)

@router.get("/members/{member_id}/timeline", response_model=List[dict])
def get_member_growth_timeline(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Devuelve la línea de tiempo unificada (Academia, Consejería, Comunicaciones)."""
    return crud.get_member_timeline(db, member_id=member_id)

# --- FAMILIES ENDPOINTS ---

@router.get("/families/", response_model=List[schemas.Family])
def list_families(
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.get_families(db, skip=skip, limit=limit)

@router.post("/families/", response_model=dict)
def create_new_family(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    fam = crud.create_family(db, name)
    return {"id": fam.id, "name": fam.name}

@router.get("/family/{family_id}", response_model=List[dict])
def get_family(
    family_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.get_family_members(db, family_id=family_id)

# --- CONSOLIDATION & PIPELINE ---

@router.get("/consolidation/pipeline", response_model=List[dict])
def get_pipeline(
    stage: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    leads = crud.get_pipeline_leads(db, stage=stage)
    result = []
    for lead in leads:
        result.append({
            "id": lead.id,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "phone": lead.phone,
            "source": lead.source,
            "stage": lead.stage,
            "notes": lead.notes,
            "created_at": lead.created_at.isoformat(),
            "assigned_pastor_id": lead.assigned_pastor_id
        })
    return result

@router.patch("/consolidation/pipeline/{lead_id}", response_model=dict)
def update_pipeline_lead(
    lead_id: int,
    payload: schemas.ConsolidationPipelineUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    lead = crud.update_pipeline_lead(db, lead_id=lead_id, payload=payload)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"status": "success", "lead_id": lead.id, "stage": lead.stage}

@router.get("/pipeline/leads/{lead_id}/calls", response_model=List[dict])
def get_lead_calls(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    logs = crud.get_pastoral_call_logs(db, lead_id)
    return [{"id": l.id, "outcome": l.outcome, "notes": l.notes, "created_at": l.created_at} for l in logs]

# --- EVENTS & ATTENDANCE ---

@router.get("/events/", response_model=List[schemas.CrmEvent])
def list_events(
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.get_crm_events(db, skip=skip, limit=limit)

@router.post("/events/", response_model=schemas.CrmEvent)
def create_event(
    payload: schemas.CrmEventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    event = crud.create_crm_event(db, payload)
    record_admin_action(db, current_user, action="create_event", resource_type="event", resource_id=str(event.id))
    return event

@router.post("/attendance", response_model=schemas.EventAttendance)
def register_attendance(
    payload: schemas.EventAttendanceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.create_event_attendance(db, payload)

@router.post("/attendance/bulk", response_model=dict)
def register_bulk_attendance(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    event_id = payload.get("event_id")
    member_ids = payload.get("member_ids", [])
    if not event_id or not member_ids:
        raise HTTPException(status_code=400, detail="event_id and member_ids required")
    
    success_count = 0
    for mid in member_ids:
        try:
            row = models.EventAttendance(event_id=event_id, member_id=mid, status="present")
            db.add(row)
            success_count += 1
        except: continue
    db.commit()
    return {"status": "success", "recorded": success_count}

# --- COUNSELING & PRAYER ---

@router.get("/counseling/", response_model=List[schemas.CounselingTicket])
def list_counseling_tickets(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    return crud.get_counseling_tickets(db, status=status)

@router.post("/counseling/", response_model=schemas.CounselingTicket)
def create_counseling_ticket(
    payload: schemas.CounselingTicketCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    return crud.create_counseling_ticket(db, payload)

@router.patch("/counseling/{ticket_id}", response_model=schemas.CounselingTicket)
def update_counseling_ticket(
    ticket_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    ticket = db.query(models.CounselingTicket).filter(models.CounselingTicket.id == ticket_id).first()
    if not ticket: raise HTTPException(404, "Ticket not found")
    if "status" in payload: ticket.status = payload["status"]
    db.commit()
    db.refresh(ticket)
    return ticket

@router.get("/prayer-requests/", response_model=List[schemas.PrayerRequest])
def list_prayer_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.get_prayer_requests(db, status=status)

@router.post("/prayer-requests/", response_model=schemas.PrayerRequest)
def create_prayer_request(
    payload: schemas.PrayerRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.create_prayer_request(db, payload)

# --- GLORY HOUSES ---

@router.get("/glory-houses", response_model=List[schemas.GloryHouse])
def list_glory_houses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.get_glory_houses(db)

@router.post("/glory-houses", response_model=schemas.GloryHouse)
def create_glory_house(
    payload: schemas.GloryHouseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    return crud.create_glory_house(db, payload)

# --- MESSAGING & AUTOMATIONS ---

@router.post("/messaging/send", response_model=dict)
async def send_crm_message(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    from backend.services.messaging import MessagingGateway
    member_id = payload.get("member_id")
    channel = payload.get("channel", "WhatsApp")
    content = payload.get("content")
    if not member_id or not content: raise HTTPException(400, "member_id and content required")
    try:
        if channel.lower() == "whatsapp":
            log = await MessagingGateway.send_whatsapp(db, member_id, content, current_user.id)
        else:
            log = await MessagingGateway.send_sms(db, member_id, content, current_user.id)
        return {"status": "success", "log_id": log.id}
    except Exception as e: raise HTTPException(500, str(e))

# --- TASKS ---

@router.get("/tasks/mine", response_model=List[dict])
def list_my_crm_tasks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    tasks = crud.get_crm_tasks(db, assignee_id=current_user.id)
    return [{"id": t.id, "title": t.title, "status": t.status, "due_date": t.due_date} for t in tasks]

@router.post("/tasks/", response_model=schemas.CrmTask)
def create_crm_task(
    payload: schemas.CrmTaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    return crud.create_crm_task(db, payload)

@router.patch("/tasks/{task_id}", response_model=schemas.CrmTask)
def update_crm_task(
    task_id: int,
    payload: schemas.CrmTaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    task = crud.update_crm_task(db, task_id=task_id, payload=payload)
    if not task: raise HTTPException(404, "Task not found")
    return task

# --- VOLUNTEERS ---

@router.get("/volunteers/shifts", response_model=List[schemas.VolunteerShift])
def list_volunteer_shifts(
    member_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.get_volunteer_shifts(db, member_id=member_id)

@router.post("/volunteers/shifts", response_model=schemas.VolunteerShift)
def create_shift(
    payload: schemas.VolunteerShiftCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    return crud.create_volunteer_shift(db, payload)

# --- SETTINGS ---

@router.get("/settings", response_model=dict)
def get_crm_settings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    return {"churchName": "CCF Faro", "timezone": "UTC"}

@router.post("/settings", response_model=dict)
def update_crm_settings(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    return {"status": "success"}
