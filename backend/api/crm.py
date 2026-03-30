from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime
from backend import crud, schemas, models
from backend.core.database import get_db
from backend.auth import get_current_user, require_admin, require_pastor_or_admin
from backend.core.audit import record_admin_action

router = APIRouter(prefix="/crm", tags=["CRM"])

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

@router.get("/members/{member_id}/communications", response_model=List[schemas.CommunicationLog])
def get_member_communications(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Obtiene el historial de comunicaciones de un miembro."""
    return db.query(models.CommunicationLog).filter(models.CommunicationLog.member_id == member_id).all()

@router.get("/members/{member_id}/donations", response_model=List[schemas.Donation])
def list_member_donations(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Obtiene el historial financiero (diezmos/ofrendas) de un miembro."""
    return crud.get_member_donations(db, member_id=member_id)

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
    """Obtiene los miembros del nucleo familiar."""
    return crud.get_family_members(db, family_id=family_id)

@router.get("/talents", response_model=List[dict])
def search_talents(
    q: Optional[str] = None, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Buscador avanzado de talentos y habilidades."""
    return crud.get_talents(db, search=q)


@router.get("/consolidation/pipeline", response_model=List[dict])
def get_pipeline(
    stage: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Obtiene los prospectos del pipeline de consolidación."""
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
    """Actualiza la etapa de un prospecto en el pipeline."""
    lead = crud.update_pipeline_lead(db, lead_id=lead_id, payload=payload)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"status": "success", "lead_id": lead.id, "stage": lead.stage}

# --- EXTENDED CRM ENDPOINTS ---

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
    record_admin_action(
        db, current_user, 
        action="create_crm_event", 
        resource_type="crm_event", 
        resource_id=str(event.id),
        metadata=payload.model_dump()
    )
    return event

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
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(member, key, value)
    
    db.commit()
    db.refresh(member)
    
    record_admin_action(
        db, current_user,
        action="update_member",
        resource_type="member",
        resource_id=str(member.id),
        metadata=update_data
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

@router.post("/attendance", response_model=schemas.EventAttendance)
def register_attendance(
    payload: schemas.EventAttendanceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Registra la asistencia de un miembro a un evento."""
    attendance = crud.create_event_attendance(db, payload)
    return attendance

@router.post("/attendance/bulk", response_model=dict)
def register_bulk_attendance(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Registra asistencia masiva para un evento de forma atómica."""
    event_id = payload.get("event_id")
    member_ids = payload.get("member_ids", [])
    attendance_date_str = payload.get("attendance_date")
    
    if not event_id or not member_ids:
        raise HTTPException(status_code=400, detail="event_id and member_ids are required")
    
    from backend.crud import _utcnow
    attendance_date = _utcnow()
    if attendance_date_str:
        try:
            from datetime import datetime
            attendance_date = datetime.fromisoformat(attendance_date_str.replace('Z', ''))
        except ValueError:
            pass

    success_count = 0
    for mid in member_ids:
        try:
            # Evitar duplicados para el mismo día
            existing = db.query(models.EventAttendance).filter(
                models.EventAttendance.event_id == event_id,
                models.EventAttendance.member_id == mid,
                models.EventAttendance.attendance_date >= attendance_date.date()
            ).first()
            
            if not existing:
                row = models.EventAttendance(
                    event_id=event_id,
                    member_id=mid,
                    attendance_date=attendance_date,
                    status="present"
                )
                db.add(row)
                success_count += 1
        except Exception:
            continue
            
    db.commit()
    record_admin_action(
        db, current_user, 
        action="bulk_attendance", 
        resource_type="event", 
        resource_id=str(event_id),
        metadata={"count": success_count}
    )
    return {"status": "success", "recorded": success_count}
from backend.auth import get_current_user, require_admin, require_pastor_or_admin, require_pastor_or_admin


@router.get("/counseling/", response_model=List[schemas.CounselingTicket])
def list_counseling_tickets(
    status: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    # Auditoría de acceso a datos sensibles
    record_admin_action(
        db, current_user, 
        action="list_counseling_tickets", 
        resource_type="counseling", 
        metadata={"status_filter": status}
    )
    return crud.get_counseling_tickets(db, status=status, skip=skip, limit=limit)

@router.post("/counseling/", response_model=schemas.CounselingTicket)
def create_counseling_ticket(
    payload: schemas.CounselingTicketCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):

    ticket = crud.create_counseling_ticket(db, payload)
    record_admin_action(
        db, current_user, 
        action="create_counseling_ticket", 
        resource_type="counseling_ticket", 
        resource_id=str(ticket.id),
        metadata=payload.model_dump()
    )
    return ticket

@router.get("/prayer-requests/", response_model=List[schemas.PrayerRequest])
def list_prayer_requests(
    status: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.get_prayer_requests(db, status=status, skip=skip, limit=limit)

@router.post("/prayer-requests/", response_model=schemas.PrayerRequest)
def create_prayer_request(
    payload: schemas.PrayerRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    req = crud.create_prayer_request(db, payload)
    record_admin_action(
        db, current_user, 
        action="create_prayer_request", 
        resource_type="prayer_request", 
        resource_id=str(req.id),
        metadata=payload.model_dump()
    )
    return req

@router.get("/glory-houses", response_model=List[schemas.GloryHouse])
def list_glory_houses(
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.get_glory_houses(db, skip=skip, limit=limit)

@router.post("/glory-houses", response_model=schemas.GloryHouse)
def create_glory_house(
    payload: schemas.GloryHouseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Crea una nueva Casa de Gloria (Solo Admin)."""
    return crud.create_glory_house(db, payload)

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
    # Fallback if no member profile is directly linked
    return {
        "id": 0,
        "first_name": current_user.username,
        "last_name": "Usuario",
        "church_role": current_user.role,
        "qr_code": f"CCF-USR-{current_user.id}-{uuid.uuid4().hex[:6]}"
    }

@router.patch("/members/{member_id}", response_model=dict)
def update_member_endpoint(
    member_id: int,
    payload: schemas.MemberUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Actualiza datos de un miembro (rol, estado espiritual, etc)."""
    member = crud.update_member(db, member_id=member_id, payload=payload)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Audit log
    record_admin_action(
        db, current_user, 
        action="update_member", 
        resource_type="member", 
        resource_id=str(member_id),
        metadata=payload.model_dump(exclude_unset=True)
    )
    
    return {"status": "success", "member_id": member.id}

@router.get("/messaging/history", response_model=List[schemas.CommunicationLog])
def get_crm_messaging_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.get_communication_logs(db, limit=50)

@router.post("/messaging/send", response_model=dict)
async def send_crm_message(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Envía un mensaje real (WhatsApp/SMS) a un miembro vía el Gateway."""
    from backend.services.messaging import MessagingGateway
    
    member_id = payload.get("member_id")
    channel = payload.get("channel", "WhatsApp")
    content = payload.get("content")
    
    if not member_id or not content:
        raise HTTPException(status_code=400, detail="member_id and content are required")
        
    try:
        if channel.lower() == "whatsapp":
            log = await MessagingGateway.send_whatsapp(db, member_id, content, current_user.id)
        else:
            log = await MessagingGateway.send_sms(db, member_id, content, current_user.id)
            
        return {
            "status": "success", 
            "log_id": log.id, 
            "external_id": log.external_id,
            "outcome": log.outcome
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error en el Gateway de Mensajería")

@router.get("/pipeline/leads/{lead_id}/calls", response_model=List[dict])
def get_lead_calls(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    logs = crud.get_pastoral_call_logs(db, lead_id)
    return [{"id": l.id, "outcome": l.outcome, "notes": l.notes, "created_at": l.created_at} for l in logs]

@router.get("/members/{member_id}/timeline", response_model=List[dict])
def get_member_growth_timeline(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Devuelve la línea de tiempo unificada (Academia, Consejería, Comunicaciones)."""
    return crud.get_member_timeline(db, member_id=member_id)

@router.patch("/counseling/{ticket_id}", response_model=schemas.CounselingTicket)
def update_counseling_ticket(
    ticket_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    """Actualiza un ticket de consejería con auditoría."""
    ticket = db.query(models.CounselingTicket).filter(models.CounselingTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if "status" in payload:
        ticket.status = payload["status"]
    if "notes" in payload:
        from backend.core.security import encrypt_data
        from backend.crud import analyze_pastoral_priority, analyze_pastoral_sentiment
        
        raw_notes = payload["notes"]
        # Recalcular IA
        ticket.priority_level = analyze_pastoral_priority(raw_notes)
        score, label = analyze_pastoral_sentiment(raw_notes)
        ticket.sentiment_score = score
        ticket.sentiment_label = label
        
        ticket.notes = encrypt_data(raw_notes)
        
    db.commit()
    db.refresh(ticket)
    
    # Decrypt for response
    from backend.core.security import decrypt_data
    if ticket.notes:
        ticket.notes = decrypt_data(ticket.notes)
        
    record_admin_action(
        db, current_user, 
        action="update_counseling_ticket", 
        resource_type="counseling", 
        resource_id=str(ticket_id)
    )
    return ticket

@router.patch("/prayer-requests/{request_id}", response_model=schemas.PrayerRequest)
def update_prayer_request(
    request_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Actualiza estado de petición de oración con auditoría."""
    req = db.query(models.PrayerRequest).filter(models.PrayerRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Prayer request not found")
    if "status" in payload:
        req.status = payload["status"]
    db.commit()
    db.refresh(req)
    
    record_admin_action(
        db, current_user, 
        action="update_prayer_request", 
        resource_type="prayer_request", 
        resource_id=str(request_id)
    )
    return req

@router.post("/scanner/validate/{token}", response_model=dict)
def validate_scanner_token(
    token: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Valida un código QR de asistencia buscando al miembro real."""
    # Esperamos formato CCF-MBR-{id}-...
    if not token.startswith("CCF-MBR-"):
        raise HTTPException(status_code=400, detail="Invalid token format")
    
    try:
        parts = token.split("-")
        member_id = int(parts[2])
        member = db.query(models.Member).filter(models.Member.id == member_id).first()
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
            
        return {
            "valid": True,
            "member_id": member.id,
            "member_name": f"{member.first_name} {member.last_name}",
            "church_role": member.church_role,
            "timestamp": _utcnow().isoformat()
        }
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Malformed token")

# --- CRM TASKS ENDPOINTS ---

@router.get("/tasks/mine", response_model=List[dict])
def list_my_crm_tasks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Obtiene las tareas asignadas al usuario actual con info de contacto."""
    tasks = crud.get_crm_tasks(db, assignee_id=current_user.id)
    result = []
    for t in tasks:
        contact_name = "N/A"
        if t.member:
            contact_name = f"{t.member.first_name} {t.member.last_name}"
        elif t.lead:
            contact_name = f"{t.lead.first_name} {t.lead.last_name}"
            
        result.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "contact_name": contact_name,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "status": t.status,
            "priority": t.priority,
            "created_at": t.created_at.isoformat()
        })
    return result

@router.get("/tasks/all", response_model=List[dict])
def list_all_crm_tasks(
    member_id: Optional[int] = None,
    lead_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    """Obtiene todas las tareas del CRM con info de contacto."""
    tasks = crud.get_crm_tasks(db, member_id=member_id, lead_id=lead_id)
    result = []
    for t in tasks:
        contact_name = "N/A"
        if t.member:
            contact_name = f"{t.member.first_name} {t.member.last_name}"
        elif t.lead:
            contact_name = f"{t.lead.first_name} {t.lead.last_name}"
            
        result.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "contact_name": contact_name,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "status": t.status,
            "priority": t.priority,
            "created_at": t.created_at.isoformat()
        })
    return result


@router.post("/tasks/", response_model=schemas.CrmTask)
def create_crm_task(
    payload: schemas.CrmTaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    """Crea una nueva tarea pastoral."""
    return crud.create_crm_task(db, payload)

@router.patch("/tasks/{task_id}", response_model=schemas.CrmTask)
def update_crm_task(
    task_id: int,
    payload: schemas.CrmTaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Actualiza una tarea (estado, etc)."""
    task = crud.update_crm_task(db, task_id=task_id, payload=payload)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

# --- VOLUNTEER SHIFTS ENDPOINTS ---

@router.post("/automations/run", response_model=dict)
def run_pastoral_automations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    """
    Motor de Automatización Pastoral v1.0.
    Simula el envío de mensajes de bienvenida a nuevos leads en el pipeline.
    """
    # 1. Buscar leads en etapa 'new'
    new_leads = db.query(models.ConsolidationPipeline).filter(
        models.ConsolidationPipeline.stage == "new"
    ).all()
    
    triggered_count = 0
    for lead in new_leads:
        # Simulación de envío de mensaje vía Gateway de Mensajería
        triggered_count += 1
        # Podríamos moverlos a 'contacted' automáticamente si se desea
    
    db.commit()
    
    # Audit log
    record_admin_action(
        db, current_user, 
        action="run_pastoral_automations", 
        resource_type="automation", 
        metadata={"leads_processed": triggered_count}
    )
    
    return {
        "status": "success",
        "processed": triggered_count,
        "automation_type": "welcome_messages",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/glory-houses/clusters", response_model=dict)
def get_glory_house_clusters(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Calcula clusters de Casas de Gloria para visualización en mapa de calor.
    Mock de lógica geo-espacial para el Mapa de Calor Cinematográfico.
    """
    houses = crud.get_glory_houses(db)
    # Lógica de clustering mock basada en coordenadas base
    clusters = [
        {"center": {"lat": 13.68, "lng": -89.23}, "count": 12, "intensity": "high", "label": "Zona Norte - Alta Densidad"},
        {"center": {"lat": 13.70, "lng": -89.20}, "count": 5, "intensity": "medium", "label": "Distrito Central"},
        {"center": {"lat": 13.65, "lng": -89.25}, "count": 3, "intensity": "low", "label": "Expansión Sur"}
    ]
    return {
        "total_houses": len(houses),
        "clusters": clusters,
        "viewport_focus": {"lat": 13.69, "lng": -89.22, "zoom": 12},
        "timestamp": datetime.now().isoformat()
    }

@router.get("/volunteers/shifts", response_model=List[schemas.VolunteerShift])
def list_volunteer_shifts(
    member_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Obtiene el calendario de turnos de servicio."""
    return crud.get_volunteer_shifts(db, member_id=member_id)

@router.post("/volunteers/shifts", response_model=schemas.VolunteerShift)
def create_shift(
    payload: schemas.VolunteerShiftCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    """Asigna un turno de servicio (Solo Staff/Admin)."""
    return crud.create_volunteer_shift(db, payload)


