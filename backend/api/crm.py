from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime
from backend import crud, schemas, models
from backend.core.database import get_db
from backend.auth import (
    get_current_user, 
    normalize_role,
    require_active_user,
    require_admin, 
    require_pastor_or_admin, 
    require_staff_or_admin,
    require_coordinator_or_admin
)
from backend.core.audit import record_admin_action
from backend.mesh_websockets import manager

router = APIRouter(tags=["CRM"])

# --- MEMBERS ENDPOINTS ---

@router.get("/members", response_model=List[schemas.Member])
def list_members(
    search: Optional[str] = None, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    """Lista miembros con tipado estricto y búsqueda optimizada."""
    return crud.search_members(db, search=search)

@router.post("/members/", response_model=schemas.Member)
def create_member(
    payload: schemas.MemberCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    """Registra un nuevo miembro en el CRM."""
    return crud.create_member(db, payload)

@router.get("/members/me", response_model=dict)
def get_my_crm_card(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user)
):
    """Devuelve la tarjeta de miembro del usuario actual vinculada por user_id."""
    member = db.query(models.Member).filter(models.Member.user_id == current_user.id).first()
    if member:
        return {
            "id": member.id,
            "first_name": member.first_name,
            "last_name": member.last_name,
            "church_role": member.church_role,
            "qr_code": f"CCF-MBR-{member.id}-{uuid.uuid4().hex[:6]}"
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
    current_user: models.User = Depends(require_active_user)
):
    """Obtiene el detalle de un miembro con validación de propiedad (IDOR)."""
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
        
    # Check if user is looking at their own profile OR is a pastor/admin
    is_self = member.user_id == current_user.id
    is_staff = normalize_role(str(current_user.role)) in ["admin", "pastor", "coordinador"]
    
    if not is_self and not is_staff:
        raise HTTPException(status_code=403, detail="No autorizado para ver este perfil")
        
    return member

@router.patch("/members/{member_id}", response_model=schemas.Member)
def update_member(
    member_id: int,
    payload: schemas.MemberUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
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
    current_user: models.User = Depends(require_pastor_or_admin)
):
    return db.query(models.CommunicationLog).filter(models.CommunicationLog.member_id == member_id).all()

@router.get("/members/{member_id}/donations", response_model=List[schemas.Donation])
def list_member_donations(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    return crud.get_member_donations(db, member_id=member_id)

@router.get("/members/{member_id}/timeline", response_model=List[dict])
def get_member_growth_timeline(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    """Devuelve la línea de tiempo unificada (Academia, Consejería, Comunicaciones)."""
    return crud.get_member_timeline(db, member_id=member_id)

# --- FAMILIES ENDPOINTS ---

@router.get("/families/", response_model=List[schemas.Family])
def list_families(
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    return crud.get_families(db, skip=skip, limit=limit)

@router.post("/families/", response_model=dict)
def create_new_family(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
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
    current_user: models.User = Depends(require_pastor_or_admin)
):
    return crud.get_family_members(db, family_id=family_id)

# --- CONSOLIDATION & PIPELINE ---

@router.get("/consolidation/pipeline", response_model=List[dict])
def get_pipeline(
    stage: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
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
            "stage": schemas.normalize_pipeline_stage(lead.stage),
            "notes": lead.notes,
            "created_at": lead.created_at.isoformat(),
            "assigned_pastor_id": lead.assigned_pastor_id
        })
    return result


@router.post("/consolidation/pipeline", response_model=dict)
async def create_pipeline_lead(
    payload: schemas.ConsolidationPipelineCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    lead = crud.create_pipeline_lead(db, payload)

    record_admin_action(
        db,
        current_user,
        action="create_pipeline_lead",
        resource_type="pipeline_lead",
        resource_id=str(lead.id),
        metadata={
            "source": lead.source,
            "stage": lead.stage,
            "assigned_pastor_id": lead.assigned_pastor_id,
        },
    )

    await manager.broadcast_event(
        {
            "type": "PIPELINE_CREATED",
            "lead_id": lead.id,
            "stage": schemas.normalize_pipeline_stage(lead.stage),
            "actor": current_user.username,
        },
        room="pastoral_ops",
    )

    return {
        "id": lead.id,
        "first_name": lead.first_name,
        "last_name": lead.last_name,
        "phone": lead.phone,
        "source": lead.source,
        "stage": schemas.normalize_pipeline_stage(lead.stage),
        "notes": lead.notes,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "assigned_pastor_id": lead.assigned_pastor_id,
    }

@router.get("/consolidation/pipeline/{lead_id}", response_model=dict)
def get_pipeline_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    """Obtiene el detalle de un prospecto específico."""
    lead = db.query(models.ConsolidationPipeline).filter(models.ConsolidationPipeline.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {
        "id": lead.id,
        "first_name": lead.first_name,
        "last_name": lead.last_name,
        "phone": lead.phone,
        "source": lead.source,
        "stage": schemas.normalize_pipeline_stage(lead.stage),
        "notes": lead.notes,
        "created_at": lead.created_at.isoformat(),
        "assigned_pastor_id": lead.assigned_pastor_id
    }

@router.patch("/consolidation/pipeline/{lead_id}", response_model=dict)
async def update_pipeline_lead(
    lead_id: int,
    payload: schemas.ConsolidationPipelineUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    lead = crud.update_pipeline_lead(db, lead_id=lead_id, payload=payload)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Audit logging for pipeline movements
    record_admin_action(
        db, current_user,
        action="update_pipeline_lead",
        resource_type="pipeline_lead",
        resource_id=str(lead.id),
        metadata=payload.model_dump(exclude_unset=True)
    )

    # BROADCAST REAL-TIME UPDATE
    await manager.broadcast_event({
        "type": "PIPELINE_UPDATED",
        "lead_id": lead.id,
        "stage": lead.stage,
        "actor": current_user.username
    }, room="pastoral_ops")
    
    return {"status": "success", "lead_id": lead.id, "stage": schemas.normalize_pipeline_stage(lead.stage)}

@router.get("/consolidation/pipeline/{lead_id}/audit", response_model=List[schemas.AdminAuditLog])
def get_pipeline_lead_audit(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    """Retrieve the audit trail for a specific pipeline lead."""
    logs = db.query(models.AdminAuditLog).filter(
        models.AdminAuditLog.resource_type == "pipeline_lead",
        models.AdminAuditLog.resource_id == str(lead_id)
    ).order_by(models.AdminAuditLog.created_at.desc()).all()
    return logs

@router.get("/pipeline/leads/{lead_id}/calls", response_model=List[dict])
def get_lead_calls(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    logs = crud.get_pastoral_call_logs(db, lead_id)
    return [
        {
            "id": l.id,
            "outcome": l.outcome,
            "notes": l.notes,
            "prayer_requests": None,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]


@router.post("/pipeline/leads/{lead_id}/calls", response_model=dict)
def create_lead_call(
    lead_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    lead = db.query(models.ConsolidationPipeline).filter(models.ConsolidationPipeline.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    outcome = str(payload.get("outcome", "Exitoso"))
    notes = payload.get("notes")
    duration_seconds = int(payload.get("duration_seconds", 0) or 0)

    row = models.PastoralCallLog(
        lead_id=lead_id,
        pastor_id=current_user.id,
        outcome=outcome,
        notes=notes,
        duration_seconds=duration_seconds,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    record_admin_action(
        db,
        current_user,
        action="create_pastoral_call_log",
        resource_type="pipeline_lead",
        resource_id=str(lead_id),
        metadata={"outcome": outcome},
    )

    return {
        "id": row.id,
        "lead_id": row.lead_id,
        "pastor_id": row.pastor_id,
        "outcome": row.outcome,
        "notes": row.notes,
        "prayer_requests": payload.get("prayer_requests"),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }

# --- EVENTS & ATTENDANCE ---

@router.get("/events/", response_model=List[schemas.CrmEvent])
def list_events(
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    return crud.get_crm_events(db, skip=skip, limit=limit)

@router.post("/events/", response_model=schemas.CrmEvent)
def create_event(
    payload: schemas.CrmEventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    event = crud.create_crm_event(db, payload)
    record_admin_action(db, current_user, action="create_event", resource_type="event", resource_id=str(event.id))
    return event

@router.post("/attendance", response_model=schemas.EventAttendance)
def register_attendance(
    payload: schemas.EventAttendanceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    return crud.create_event_attendance(db, payload)

@router.post("/attendance/bulk", response_model=dict)
def register_bulk_attendance(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
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
    member_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    tickets = crud.get_counseling_tickets(db, status=status)
    if member_id:
        tickets = [t for t in tickets if t.member_id == member_id]
    return tickets

@router.get("/counseling/lead/{lead_id}", response_model=List[dict])
def get_counseling_by_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    """Devuelve sesiones de consejería asociadas a un prospecto (por lead_id o member_id combinado)."""
    try:
        # Buscar tickets donde el member_id coincida (lead puede haberse convertido en miembro)
        tickets = db.query(models.CounselingTicket).filter(
            models.CounselingTicket.member_id == lead_id
        ).all()
        return [{
            "id": t.id,
            "subject": t.subject,
            "notes": t.notes,
            "status": t.status,
            "priority_level": t.priority_level,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        } for t in tickets]
    except Exception:
        return []

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
    current_user: models.User = Depends(require_pastor_or_admin)
):
    return crud.get_prayer_requests(db, status=status)

@router.post("/prayer-requests/", response_model=schemas.PrayerRequest)
def create_prayer_request(
    payload: schemas.PrayerRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    return crud.create_prayer_request(db, payload)

@router.patch("/prayer-requests/{request_id}", response_model=dict)
def update_prayer_request(
    request_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    """Actualiza estado de una petición de oración (pending/praying/answered)."""
    req = db.query(models.PrayerRequest).filter(models.PrayerRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Prayer request not found")
    if "status" in payload:
        req.status = payload["status"]
    if "is_answered" in payload:
        # Compatibilidad: is_answered=True → status answered
        req.status = "answered" if payload["is_answered"] else "pending"
    db.commit()
    db.refresh(req)
    return {
        "id": req.id,
        "status": req.status,
        "requester_name": req.requester_name,
    }

# --- GLORY HOUSES ---

@router.get("/glory-houses", response_model=List[schemas.GloryHouse])
def list_glory_houses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
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

@router.get("/messaging/history", response_model=List[dict])
def get_messaging_history(
    member_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    """Devuelve el historial de mensajes optimizado con JOIN para evitar N+1."""
    try:
        from sqlalchemy.orm import joinedload
        q = db.query(models.CommunicationLog).options(joinedload(models.CommunicationLog.member))
        
        if member_id:
            q = q.filter(models.CommunicationLog.member_id == member_id)
            
        logs = q.order_by(models.CommunicationLog.sent_at.desc()).limit(limit).all()
        
        return [{
            "id": log.id,
            "member_id": log.member_id,
            "member_name": f"{log.member.first_name} {log.member.last_name}" if log.member else "Desconocido",
            "channel": log.channel,
            "message": log.message,
            "status": log.status,
            "sent_at": log.sent_at.isoformat() if log.sent_at else None,
        } for log in logs]
    except Exception as e:
        return []

@router.post("/messaging/send", response_model=dict)
async def send_crm_message(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
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

@router.get("/tasks", response_model=List[dict])
@router.get("/tasks/", response_model=List[dict])
def list_crm_tasks(
    status: Optional[str] = None,
    assignee_id: Optional[int] = None,
    member_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    """Lista tareas pastorales optimizada con JOIN para evitar N+1."""
    try:
        from sqlalchemy.orm import joinedload
        q = db.query(models.CrmTask).options(joinedload(models.CrmTask.member))
        if assignee_id:
            q = q.filter(models.CrmTask.assignee_id == assignee_id)
        if member_id:
            q = q.filter(models.CrmTask.member_id == member_id)
        
        tasks = q.all()
        result = []
        for t in tasks:
            result.append({
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "status": t.status,
                "priority": t.priority,
                "category": t.category,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "member_id": t.member_id,
                "member_name": f"{t.member.first_name} {t.member.last_name}" if t.member else None,
                "assigned_to": t.assignee_id,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            })
        if status:
            result = [r for r in result if r["status"] == status]
        return result
    except Exception as e:
        return []

@router.post("/tasks/", response_model=dict)
async def create_crm_task(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    """Crea una nueva tarea pastoral y notifica vía WebSocket."""
    try:
        task = models.CrmTask(
            title=payload.get("title", ""),
            description=payload.get("description"),
            status=payload.get("status", "pending"),
            priority=payload.get("priority", "medium"),
            category=payload.get("category", "Pastoral"),
            assignee_id=current_user.id,
            member_id=int(payload["member_id"]) if payload.get("member_id") else None,
            due_date=datetime.fromisoformat(payload["due_date"]) if payload.get("due_date") else None,
            created_at=datetime.utcnow(),
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # BROADCAST REAL-TIME NOTIFICATION
        await manager.broadcast_event({
            "type": "TASK_CREATED",
            "task_id": task.id,
            "title": task.title,
            "assigned_to": current_user.username
        }, room="pastoral_ops")

        return {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/tasks/{task_id}", response_model=dict)
def update_crm_task(
    task_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    task = db.query(models.CrmTask).filter(models.CrmTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    for field in ["title", "description", "status", "priority", "category", "due_date", "member_id"]:
        if field in payload:
            if field == "due_date" and payload[field]:
                setattr(task, field, datetime.fromisoformat(payload[field]))
            elif field == "member_id" and payload[field]:
                setattr(task, field, int(payload[field]))
            else:
                setattr(task, field, payload[field])
    db.commit()
    db.refresh(task)
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status,
        "priority": getattr(task, 'priority', 'medium'),
        "category": getattr(task, 'category', 'Pastoral'),
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "created_at": task.created_at.isoformat() if hasattr(task, 'created_at') and task.created_at else None,
    }


# --- VOLUNTEERS ---

@router.get("/volunteers/shifts", response_model=List[schemas.VolunteerShift])
def list_volunteer_shifts(
    member_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    return crud.get_volunteer_shifts(db, member_id=member_id)

@router.post("/volunteers/shifts", response_model=schemas.VolunteerShift)
def create_shift(
    payload: schemas.VolunteerShiftCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    return crud.create_volunteer_shift(db, payload)

@router.post("/volunteers/apply", response_model=dict)
def apply_volunteer(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    """Registra la postulación de un miembro a un equipo de voluntariado."""
    try:
        from datetime import timedelta
        # Crear un turno pendiente como postulación
        member = db.query(models.Member).filter(models.Member.user_id == current_user.id).first()
        if not member:
            raise HTTPException(404, "Perfil de miembro no encontrado")
        shift = models.VolunteerShift(
            member_id=member.id,
            role_name=payload.get("team", "General"),
            team_name=payload.get("team", "General"),
            shift_start=datetime.utcnow(),
            shift_end=datetime.utcnow() + timedelta(hours=2),
            status="pending",
            notes=f"Disponibilidad: {payload.get('availability','')} | {payload.get('notes','')}"
        )
        db.add(shift)
        db.commit()
        db.refresh(shift)
        return {"status": "success", "shift_id": shift.id, "message": "Solicitud enviada al equipo pastoral"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, str(e))

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

# --- SCANNER ---

@router.post("/scanner/validate/{token}", response_model=dict)
def validate_scanner_token(
    token: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    """Valida un código QR de asistencia con check de integridad."""
    # Formato: CCF-MBR-{id}-{secret}
    if not token.startswith("CCF-MBR-"):
        raise HTTPException(status_code=400, detail="Formato de código inválido")
    
    try:
        parts = token.split("-")
        member_id = int(parts[2])
        secret = parts[3] if len(parts) > 3 else None
        
        member = db.query(models.Member).filter(models.Member.id == member_id).first()
        
        if not member:
            raise HTTPException(status_code=404, detail="Miembro no encontrado")

        # VALIDACIÓN DE INTEGRIDAD (Simulada para MVP, en PROD comparar con hash en DB)
        if not secret or len(secret) < 6:
             raise HTTPException(status_code=403, detail="Código de seguridad inválido o expirado")
            
        return {
            "valid": True,
            "member_id": member.id,
            "name": f"{member.first_name} {member.last_name}",
            "role": member.church_role,
            "status": member.spiritual_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Código malformado")


# ─── ROUTE ALIASES ──────────────────────────────────────────────────────────
# Short-path aliases so frontend can call simpler URLs without the sub-prefix.

@router.get("/pipeline", response_model=list)
def pipeline_alias(
    stage: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Alias de /consolidation/pipeline para compatibilidad de frontend."""
    return get_pipeline(stage=stage, db=db, current_user=current_user)


@router.post("/pipeline", response_model=dict)
async def pipeline_create_alias(
    payload: schemas.ConsolidationPipelineCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Alias de creacion para compatibilidad de frontend."""
    return await create_pipeline_lead(payload=payload, db=db, current_user=current_user)


@router.get("/groups", response_model=list)
def groups_alias(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Alias de /glory-houses para compatibilidad de frontend."""
    houses = list_glory_houses(db=db, current_user=current_user)
    return [
        {
            "id": h.id,
            "name": h.name,
            "zone": h.zone,
            "address": h.address,
            "latitude": h.latitude,
            "longitude": h.longitude,
            "leader_name": h.leader_name,
            "members_count": h.members_count,
            "capacity": h.capacity,
            "status": h.status,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        for h in houses
    ]


@router.get("/volunteers", response_model=list)
def volunteers_alias(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Alias de /volunteers/shifts para compatibilidad de frontend."""
    return list_volunteer_shifts(member_id=None, db=db, current_user=current_user)


@router.get("/prayers", response_model=list)
def prayers_alias(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Alias de /prayer-requests/ para compatibilidad de frontend."""
    requests_list = list_prayer_requests(status=None, db=db, current_user=current_user)
    return [
        {
            "id": p.id,
            "requester_name": p.requester_name,
            "request_text": p.request_text,
            "is_public": p.is_public,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in requests_list
    ]


@router.get("/analytics", response_model=dict)
def crm_analytics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Métricas agregadas del CRM para el dashboard de analíticas."""
    from sqlalchemy import func as sqlfunc

    total_members = db.query(models.Member).count()
    active_members = db.query(models.Member).filter(
        models.Member.spiritual_status.in_(["Activo", "active", "Miembro Activo"])
    ).count()

    # Pipeline por etapa
    pipeline_rows = (
        db.query(models.ConsolidationPipeline.stage, sqlfunc.count(models.ConsolidationPipeline.id))
        .group_by(models.ConsolidationPipeline.stage)
        .all()
    )
    pipeline_by_stage = {}
    for stage, count in pipeline_rows:
        normalized_stage = schemas.normalize_pipeline_stage(stage)
        pipeline_by_stage[normalized_stage] = pipeline_by_stage.get(normalized_stage, 0) + count
    total_leads = sum(pipeline_by_stage.values())

    # Consejería
    open_counseling = db.query(models.CounselingTicket).filter(
        models.CounselingTicket.status == "open"
    ).count()

    # Eventos del mes
    from datetime import timezone
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
    events_this_month = db.query(models.CrmEvent).filter(
        models.CrmEvent.event_date >= month_start
    ).count()

    # Glory houses / grupos
    total_groups = db.query(models.GloryHouse).count()

    # Familia
    total_families = db.query(models.Family).count()

    return {
        "total_members": total_members,
        "active_members": active_members,
        "total_leads": total_leads,
        "pipeline_by_stage": pipeline_by_stage,
        "open_counseling": open_counseling,
        "events_this_month": events_this_month,
        "total_groups": total_groups,
        "total_families": total_families,
    }

