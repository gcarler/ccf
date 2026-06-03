import datetime
from datetime import timezone as _tz
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.evangelism_events import router as events_router
from backend.api.evangelism_grupos import router as grupos_router
from backend.api.evangelism_multiplication import router as multiplication_router
from backend.api.evangelism_notifications import router as notifications_router
from backend.api.evangelism_rankings import router as rankings_router
from backend.api.evangelism_reports import router as reports_router
from backend.api.evangelism_shared import utc_now
from backend.auth import (
    require_active_user,
    require_admin,
    require_module_access,
    require_pastor_or_admin,
)
from backend.core.database import get_db
from backend.crud.evangelism import (  # canonical CRUD (UUID PK)
    create_estrategia as create_evangelism_strategy,
    update_estrategia as update_evangelism_strategy,
    delete_estrategia as delete_evangelism_strategy,
)
from backend.schemas.crm import (
    EvangelismStrategy,
    EvangelismStrategyCreate,
    EvangelismStrategyUpdate,
)
from backend.mesh_websockets import manager

router = APIRouter()
router.include_router(events_router)
router.include_router(grupos_router)
router.include_router(multiplication_router)
router.include_router(notifications_router)
router.include_router(rankings_router)
router.include_router(reports_router)
logger = logging.getLogger(__name__)
_DEPRECATED_ALIAS_HITS: set[str] = set()


def _warn_deprecated_crm_alias(alias_path: str, canonical_path: str) -> None:
    key = f"{alias_path}->{canonical_path}"
    if key in _DEPRECATED_ALIAS_HITS:
        return
    _DEPRECATED_ALIAS_HITS.add(key)
    logger.warning(
        "Deprecated CRM alias in /api/evangelism is in use. alias=%s canonical=%s",
        alias_path,
        canonical_path,
    )


@router.get("/counseling/", response_model=List[schemas.CounselingTicket])
def list_counseling_tickets(
    status: Optional[str] = None,
    persona_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/counseling/", "/api/crm/counseling/")
    tickets = crud.get_counseling_tickets(db, status=status)
    if persona_id:
        tickets = [t for t in tickets if t.persona_id == persona_id]
    return tickets


@router.get("/counseling/{ticket_id}", response_model=dict)
def get_counseling_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/counseling/{ticket_id}", "/api/crm/counseling/{ticket_id}")
    ticket = db.query(models.CounselingTicket).filter(models.CounselingTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    persona = db.query(models.Persona).filter(models.Persona.id == ticket.persona_id).first()
    related_history = (
        db.query(models.CounselingTicket)
        .filter(models.CounselingTicket.persona_id == ticket.persona_id)
        .order_by(models.CounselingTicket.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "id": ticket.id,
        "persona_id": ticket.persona_id,
        "member_name": (f"{persona.first_name} {persona.last_name}" if persona else "Miembro CCF"),
        "pastor_id": ticket.pastor_id,
        "topic": ticket.subject,
        "summary": ticket.subject,
        "notes": ticket.notes,
        "confidential_notes": ticket.notes,
        "status": ticket.status,
        "priority_level": ticket.priority_level,
        "scheduled_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "duration_minutes": 60,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "history": [
            {
                "id": item.id,
                "text": item.subject,
                "date": item.created_at.isoformat() if item.created_at else None,
            }
            for item in related_history
        ],
    }


@router.get("/counseling/lead/{lead_id}", response_model=List[dict])
def get_counseling_by_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias(
        "/api/evangelism/counseling/lead/{lead_id}",
        "/api/crm/counseling/lead/{lead_id}",
    )
    """Devuelve sesiones de consejerÃ­a asociadas a un prospecto (por lead_id o member_id combinado)."""
    try:
        # Buscar tickets donde el member_id coincida (lead puede haberse convertido en miembro)
        tickets = db.query(models.CounselingTicket).filter(models.CounselingTicket.persona_id == lead_id).all()
        return [
            {
                "id": t.id,
                "subject": t.subject,
                "notes": t.notes,
                "status": t.status,
                "priority_level": t.priority_level,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tickets
        ]
    except MemoryError:
        raise
    except Exception:
        logger.exception("Failed to list counseling tickets by lead", extra={"lead_id": lead_id})
        raise HTTPException(status_code=500, detail="No se pudo consultar la consejeria")


@router.post("/counseling/", response_model=schemas.CounselingTicket)
def create_counseling_ticket(
    payload: schemas.CounselingTicketCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/counseling/", "/api/crm/counseling/")
    return crud.create_counseling_ticket(db, payload)


@router.patch("/counseling/{ticket_id}", response_model=schemas.CounselingTicket)
def update_counseling_ticket(
    ticket_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/counseling/{ticket_id}", "/api/crm/counseling/{ticket_id}")
    ticket = db.query(models.CounselingTicket).filter(models.CounselingTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    if "status" in payload:
        ticket.status = payload["status"]
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/prayer-requests/", response_model=List[schemas.PrayerRequest])
def list_prayer_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/prayer-requests/", "/api/crm/prayer-requests")
    return crud.get_prayer_requests(db, status=status)


@router.post("/prayer-requests/", response_model=schemas.PrayerRequest)
def create_prayer_request(
    payload: schemas.PrayerRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/prayer-requests/", "/api/crm/prayer-requests")
    return crud.create_prayer_request(db, payload)


@router.get("/prayer-requests/{request_id}", response_model=dict)
def get_prayer_request_detail(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias(
        "/api/evangelism/prayer-requests/{request_id}",
        "/api/crm/prayer-requests/{request_id}",
    )
    req = db.query(models.PrayerRequest).filter(models.PrayerRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Prayer request not found")
    return {
        "id": req.id,
        "requester_name": req.requester_name,
        "request_text": req.request_text,
        "category": req.category,
        "is_public": req.is_public,
        "source": req.source,
        "status": req.status,
        "created_at": req.created_at.isoformat() if req.created_at else None,
    }


@router.patch("/prayer-requests/{request_id}", response_model=dict)
def update_prayer_request(
    request_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias(
        "/api/evangelism/prayer-requests/{request_id}",
        "/api/crm/prayer-requests/{request_id}",
    )
    """Actualiza estado de una peticiÃ³n de oraciÃ³n (pending/praying/answered)."""
    req = db.query(models.PrayerRequest).filter(models.PrayerRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Prayer request not found")
    if "status" in payload:
        req.status = payload["status"]
    if "source" in payload:
        req.source = payload["source"]
    if "is_answered" in payload:
        # Compatibilidad: is_answered=True → status answered
        req.status = "answered" if payload["is_answered"] else "pending"
    db.commit()
    db.refresh(req)
    return {
        "id": req.id,
        "status": req.status,
        "source": req.source,
        "is_public": req.is_public,
        "requester_name": req.requester_name,
    }


# --- GRUPOS ---


def _channel_label(channel: str) -> str:
    value = str(channel or "").strip().lower()
    if value == "whatsapp":
        return "WhatsApp"
    if value == "email":
        return "Email"
    return "SMS"


def _member_matches_segment(persona: models.Persona, segment: str, donation_persona_ids: set[str]) -> bool:
    value = str(segment or "").strip().lower()
    if value == "active":
        return str(persona.church_role or "").strip().lower() in {
            "miembro",
            "servidor",
            "lider",
            "lÃ­der",
            "pastor",
            "coordinador",
        }
    if value == "new":
        return str(persona.spiritual_status or "").strip().lower() == "nuevo"
    if value == "staff":
        return str(persona.church_role or "").strip().lower() in {
            "pastor",
            "coordinador",
            "staff",
            "administrador",
            "admin",
        }
    if value == "groups":
        return persona.family_id is not None
    if value == "low":
        return str(persona.spiritual_status or "").strip().lower() in {
            "nuevo",
            "creyente",
        }
    if value == "vip":
        return persona.id in donation_persona_ids
    return False


def _resolve_campaign_members(db: Session, segments: list[str]) -> list[models.Persona]:
    normalized_segments = [segment for segment in (s.strip().lower() for s in segments) if segment]
    if not normalized_segments:
        return []

    donation_persona_ids = {
        persona_id
        for (persona_id,) in db.query(models.Donation.persona_id)
        .filter(models.Donation.persona_id.isnot(None))
        .distinct()
        .all()
    }
    personas = db.query(models.Persona).all()
    selected = []
    seen_ids: set[str] = set()
    for persona in personas:
        if persona.id in seen_ids:
            continue
        if any(_member_matches_segment(persona, segment, donation_persona_ids) for segment in normalized_segments):
            selected.append(persona)
            seen_ids.add(persona.id)
    return selected


def _serialize_message_group(logs: list[models.CommunicationLog]) -> dict:
    ordered = sorted(logs, key=lambda log: log.created_at or datetime.min, reverse=True)
    representative = ordered[0]
    persona = getattr(representative, "persona", None)
    member_name = f"{persona.first_name} {persona.last_name}" if persona else "Desconocido"
    campaign_name = next((log.campaign_name for log in ordered if log.campaign_name), None)
    sent_at_dt = ordered[0].created_at
    delivered_count = sum(1 for log in ordered if str(log.outcome).lower() in {"sent", "delivered"})
    failed_count = sum(1 for log in ordered if str(log.outcome).lower() == "failed")
    if failed_count and not delivered_count:
        status = "failed"
    elif failed_count:
        status = "partial"
    else:
        status = str(representative.outcome or "sent").lower()
    display_name = campaign_name or (
        f"Mensaje a {member_name}" if len(ordered) == 1 else f"CampaÃ±a a {len(ordered)} contactos"
    )
    return {
        "id": representative.id,
        "name": display_name,
        "campaign_name": campaign_name,
        "member_name": member_name,
        "channel": str(representative.channel).lower(),
        "status": status,
        "sent_at": sent_at_dt.isoformat() if sent_at_dt else None,
        "target_count": len(ordered),
        "delivered_count": delivered_count,
        "failed_count": failed_count,
        "content": representative.content,
        "recipient_phone": representative.recipient_phone,
        "external_id": representative.external_id,
    }


@router.get("/messaging/history", response_model=List[dict])
def get_messaging_history(
    persona_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/messaging/history", "/api/crm/messaging/history")
    """Devuelve el historial de mensajes optimizado con JOIN para evitar N+1."""
    try:
        from sqlalchemy.orm import joinedload

        q = db.query(models.CommunicationLog).options(joinedload(models.CommunicationLog.persona))

        if persona_id:
            q = q.filter(models.CommunicationLog.persona_id == persona_id)

        logs = q.order_by(models.CommunicationLog.created_at.desc()).limit(limit).all()
        grouped: dict[str, list[models.CommunicationLog]] = {}
        for log in logs:
            key = log.external_id or f"single:{log.id}"
            grouped.setdefault(key, []).append(log)

        summaries = [_serialize_message_group(group) for group in grouped.values()]
        summaries.sort(key=lambda item: item.get("sent_at") or "", reverse=True)
        return summaries
    except MemoryError:
        raise
    except Exception:
        logger.exception(
            "Failed to list CRM messaging history",
            extra={"persona_id": persona_id, "limit": limit},
        )
        raise HTTPException(status_code=500, detail="No se pudo consultar el historial de mensajes")


@router.get("/messaging/history/{log_id}", response_model=dict)
def get_messaging_history_item(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias(
        "/api/evangelism/messaging/history/{log_id}",
        "/api/crm/messaging/history/{log_id}",
    )
    from sqlalchemy.orm import joinedload

    log = (
        db.query(models.CommunicationLog)
        .options(joinedload(models.CommunicationLog.persona))
        .filter(models.CommunicationLog.id == log_id)
        .first()
    )
    if not log:
        raise HTTPException(status_code=404, detail="Message history item not found")

    if log.external_id:
        related_logs = (
            db.query(models.CommunicationLog)
            .options(joinedload(models.CommunicationLog.persona))
            .filter(models.CommunicationLog.external_id == log.external_id)
            .order_by(models.CommunicationLog.created_at.desc())
            .all()
        )
        if len(related_logs) > 1:
            return _serialize_message_group(related_logs)

    return _serialize_message_group([log])


@router.post("/messaging/send", response_model=dict)
async def send_crm_message(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/messaging/send", "/api/crm/messaging/send")
    from backend.services.messaging import MessagingGateway

    persona_id = payload.get("persona_id")
    channel = _channel_label(payload.get("channel", "WhatsApp"))
    content = payload.get("content")
    campaign_name = payload.get("campaign_name") or payload.get("name")
    target_segments = payload.get("target_segments") or []
    try:
        if target_segments:
            if not campaign_name or not content:
                raise HTTPException(status_code=400, detail="campaign_name and content required")
            personas = _resolve_campaign_members(db, list(target_segments))
            if not personas:
                raise HTTPException(
                    status_code=404,
                    detail="No se encontraron destinatarios para la campaÃ±a",
                )

            campaign_id = f"CMP-{uuid.uuid4().hex[:12]}"
            logs: list[models.CommunicationLog] = []
            delivered_count = 0
            failed_count = 0
            for persona in personas:
                try:
                    if channel.lower() == "whatsapp":
                        log = await MessagingGateway.send_whatsapp(
                            db,
                            persona.id,
                            content,
                            current_user.id,
                            campaign_name=campaign_name,
                            external_id=campaign_id,
                        )
                    elif channel.lower() == "email":
                        log = await MessagingGateway.send_email(
                            db,
                            persona.id,
                            content,
                            current_user.id,
                            campaign_name=campaign_name,
                            external_id=campaign_id,
                        )
                    else:
                        log = await MessagingGateway.send_sms(
                            db,
                            persona.id,
                            content,
                            current_user.id,
                            campaign_name=campaign_name,
                            external_id=campaign_id,
                        )
                    logs.append(log)
                    delivered_count += 1
                except ValueError:
                    fallback_log = models.CommunicationLog(
                        persona_id=persona.id,
                        channel=channel,
                        campaign_name=campaign_name,
                        recipient_phone=persona.phone,
                        content=content,
                        leader_user_id=current_user.id,
                        outcome="failed",
                        external_id=campaign_id,
                    )
                    db.add(fallback_log)
                    db.commit()
                    db.refresh(fallback_log)
                    logs.append(fallback_log)
                    failed_count += 1

            return {
                "status": "success",
                "campaign_name": campaign_name,
                "external_id": campaign_id,
                "target_count": len(personas),
                "delivered_count": delivered_count,
                "failed_count": failed_count,
                "log_ids": [log.id for log in logs],
            }

        if not persona_id or not content:
            raise HTTPException(status_code=400, detail="persona_id and content required")

        if channel.lower() == "whatsapp":
            log = await MessagingGateway.send_whatsapp(
                db,
                persona_id,
                content,
                current_user.id,
            )
        elif channel.lower() == "email":
            log = await MessagingGateway.send_email(
                db,
                persona_id,
                content,
                current_user.id,
            )
        else:
            log = await MessagingGateway.send_sms(
                db,
                persona_id,
                content,
                current_user.id,
            )
        return {"status": "success", "log_id": log.id}
    except (HTTPException, MemoryError):
        raise
    except Exception:
        logger.exception(
            "Failed to send CRM message",
            extra={
                "persona_id": persona_id,
                "channel": channel,
                "sender_user_id": getattr(current_user, "id", None),
                "campaign_name": campaign_name,
                "target_segments": target_segments,
            },
        )
        raise HTTPException(status_code=502, detail="No se pudo enviar el mensaje")


# --- TASKS ---


def _serialize_crm_task(
    task: models.CrmTask,
    contact_name: Optional[str] = None,
    assignee_name: Optional[str] = None,
) -> dict:
    persona = getattr(task, "persona", None)
    member_name = contact_name or (f"{persona.first_name} {persona.last_name}" if persona else None)
    assignee = getattr(task, "assignee", None)
    assigned_to = assignee_name or (assignee.username if assignee else None)
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "category": task.category,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "persona_id": task.persona_id,
        "member_name": member_name,
        "contact_name": member_name,
        "assigned_to": assigned_to,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.get("/tasks", response_model=List[dict])
def list_crm_tasks(
    status: Optional[str] = None,
    assignee_id: Optional[int] = None,
    persona_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/tasks", "/api/crm/tasks")
    """Lista tareas pastorales optimizada con JOIN para evitar N+1."""
    try:
        from sqlalchemy.orm import joinedload

        q = db.query(models.CrmTask).options(joinedload(models.CrmTask.persona), joinedload(models.CrmTask.assignee))
        if assignee_id:
            q = q.filter(models.CrmTask.assignee_id == assignee_id)
        if persona_id:
            q = q.filter(models.CrmTask.persona_id == persona_id)

        tasks = q.all()
        result = [_serialize_crm_task(t) for t in tasks]
        if status:
            result = [r for r in result if r["status"] == status]
        return result
    except MemoryError:
        raise
    except Exception:
        logger.exception(
            "Failed to list CRM tasks",
            extra={
                "status": status,
                "assignee_id": assignee_id,
                "persona_id": persona_id,
            },
        )
        raise HTTPException(status_code=500, detail="No se pudo consultar las tareas")


@router.get("/tasks/mine", response_model=List[dict])
def list_my_crm_tasks(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("evangelism", "read")),
):
    _warn_deprecated_crm_alias("/api/evangelism/tasks/mine", "/api/crm/tasks/mine")
    try:
        from sqlalchemy.orm import joinedload

        q = (
            db.query(models.CrmTask)
            .options(joinedload(models.CrmTask.persona), joinedload(models.CrmTask.assignee))
            .filter(models.CrmTask.assignee_id == current_user.id)
        )
        tasks = q.order_by(models.CrmTask.created_at.desc()).all()
        result = [_serialize_crm_task(task) for task in tasks]
        if status:
            result = [row for row in result if row["status"] == status]
        return result
    except MemoryError:
        raise
    except Exception:
        logger.exception(
            "Failed to list my CRM tasks",
            extra={"user_id": getattr(current_user, "id", None)},
        )
        raise HTTPException(status_code=500, detail="No se pudieron consultar mis tareas")


@router.get("/tasks/{task_id}", response_model=dict)
def get_crm_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/tasks/{task_id}", "/api/crm/tasks/{task_id}")
    from sqlalchemy.orm import joinedload

    task = (
        db.query(models.CrmTask)
        .options(joinedload(models.CrmTask.persona), joinedload(models.CrmTask.assignee))
        .filter(models.CrmTask.id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize_crm_task(task)


@router.post("/tasks/", response_model=dict)
async def create_crm_task(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/tasks/", "/api/crm/tasks/")
    """Crea una nueva tarea pastoral y notifica vÃ­a WebSocket."""
    title = str(payload.get("title", "")).strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    try:
        due_date_value = payload.get("due_date")
        due_date = None
        if due_date_value:
            due_date = datetime.datetime.fromisoformat(str(due_date_value))
        task = models.CrmTask(
            title=title,
            description=payload.get("description"),
            status=payload.get("status", "pending"),
            priority=payload.get("priority", "medium"),
            category=payload.get("category", "Pastoral"),
            assignee_id=current_user.id,
            persona_id=payload["persona_id"] if payload.get("persona_id") else None,
            due_date=due_date,
            created_at=utc_now(),
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # BROADCAST REAL-TIME NOTIFICATION
        await manager.broadcast_event(
            {
                "type": "TASK_CREATED",
                "task_id": task.id,
                "title": task.title,
                "assigned_to": current_user.username,
            },
            room="pastoral_ops",
        )

        return {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha o identificador invalido")
    except MemoryError:
        raise
    except Exception:
        logger.exception(
            "Failed to create CRM task",
            extra={"user_id": getattr(current_user, "id", None)},
        )
        raise HTTPException(status_code=500, detail="No se pudo crear la tarea")


@router.patch("/tasks/{task_id}", response_model=dict)
def update_crm_task(
    task_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/tasks/{task_id}", "/api/crm/tasks/{task_id}")
    task = db.query(models.CrmTask).filter(models.CrmTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    for field in [
        "title",
        "description",
        "status",
        "priority",
        "category",
        "due_date",
        "persona_id",
    ]:
        if field in payload:
            if field == "due_date" and payload[field]:
                setattr(task, field, datetime.fromisoformat(payload[field]))
            elif field == "persona_id" and payload[field]:
                setattr(task, field, payload[field])
            else:
                setattr(task, field, payload[field])
    db.commit()
    db.refresh(task)
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status,
        "priority": getattr(task, "priority", "medium"),
        "category": getattr(task, "category", "Pastoral"),
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "created_at": (task.created_at.isoformat() if hasattr(task, "created_at") and task.created_at else None),
    }


# --- VOLUNTEERS ---


@router.get("/volunteers/shifts", response_model=List[schemas.VolunteerShift])
def list_volunteer_shifts(
    persona_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/volunteers/shifts", "/api/crm/volunteers")
    return crud.get_volunteer_shifts(db, persona_id=persona_id)


@router.post("/volunteers/shifts", response_model=schemas.VolunteerShift)
def create_shift(
    payload: schemas.VolunteerShiftCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/volunteers/shifts", "/api/crm/volunteers")
    return crud.create_volunteer_shift(db, payload)


@router.get("/volunteers/{persona_id}", response_model=dict)
def get_volunteer_detail(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/volunteers/{persona_id}", "/api/crm/volunteers/{persona_id}")
    try:
        db_id = uuid.UUID(persona_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Persona not found")

    persona = db.query(models.Persona).filter(models.Persona.id == db_id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    shifts = (
        db.query(models.VolunteerShift)
        .filter(models.VolunteerShift.persona_id == db_id)
        .order_by(models.VolunteerShift.created_at.desc())
        .all()
    )
    total_hours = 0
    for shift in shifts:
        if shift.shift_start and shift.shift_end:
            delta = shift.shift_end - shift.shift_start
            total_hours += max(int(delta.total_seconds() // 3600), 0)

    skills = [
        skill_name
        for (skill_name,) in (
            db.query(models.VolunteerSkill.name)
            .join(
                models.member_volunteer_skills,
                models.VolunteerSkill.id == models.member_volunteer_skills.c.skill_id,
            )
            .filter(models.member_volunteer_skills.c.persona_id == db_id)
            .order_by(models.VolunteerSkill.name.asc())
            .all()
        )
    ]
    primary_shift = shifts[0] if shifts else None

    return {
        "id": persona.id,
        "name": f"{persona.first_name} {persona.last_name}".strip(),
        "role": persona.church_role,
        "team": (primary_shift.team_name if primary_shift else (persona.church_role or "General")),
        "status": (primary_shift.status if primary_shift else ("active" if persona.is_baptized else "pending")),
        "joined_date": (persona.created_at.date().isoformat() if persona.created_at else None),
        "total_hours": total_hours,
        "skills": skills,
    }


@router.post("/volunteers/apply", response_model=dict)
def apply_volunteer(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/volunteers/apply", "/api/crm/volunteers")
    """Registra la postulaciÃ³n de un miembro a un equipo de voluntariado."""
    try:
        from datetime import timedelta

        # Crear un turno pendiente como postulaciÃ³n
        persona = db.query(models.Persona).filter(models.Persona.user_id == current_user.id).first()
        if not persona:
            raise HTTPException(404, "Perfil de miembro no encontrado")
        shift = models.VolunteerShift(
            persona_id=persona.id,
            role_name=payload.get("team", "General"),
            team_name=payload.get("team", "General"),
            shift_start=utc_now(),
            shift_end=utc_now() + timedelta(hours=2),
            status="pending",
            notes=f"Disponibilidad: {payload.get('availability', '')} | {payload.get('notes', '')}",
        )
        db.add(shift)
        db.commit()
        db.refresh(shift)
        return {
            "status": "success",
            "shift_id": shift.id,
            "message": "Solicitud enviada al equipo pastoral",
        }
    except (HTTPException, MemoryError):
        raise
    except Exception:
        logger.exception(
            "Failed to register volunteer application",
            extra={"user_id": getattr(current_user, "id", None)},
        )
        raise HTTPException(status_code=400, detail="No se pudo registrar la solicitud")


# --- SETTINGS ---

CRM_DEFAULTS = {"churchName": "CCF Faro", "timezone": "UTC"}


@router.get("/settings", response_model=dict)
def get_crm_settings(db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    _warn_deprecated_crm_alias("/api/evangelism/settings", "/api/crm/settings")
    """Lee la configuración de CRM desde system_variables."""
    settings = dict(CRM_DEFAULTS)
    rows = (
        db.query(models.SystemVariable).filter(models.SystemVariable.key.in_(["crm_church_name", "crm_timezone"])).all()
    )
    for row in rows:
        if row.key == "crm_church_name":
            settings["churchName"] = row.value
        elif row.key == "crm_timezone":
            settings["timezone"] = row.value
    return settings


@router.post("/settings", response_model=dict)
def update_crm_settings(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/settings", "/api/crm/settings")
    """Actualiza la configuración de CRM en system_variables."""
    mapping = {"churchName": "crm_church_name", "timezone": "crm_timezone"}
    for js_key, db_key in mapping.items():
        if js_key in payload:
            var = db.query(models.SystemVariable).filter(models.SystemVariable.key == db_key).first()
            if var:
                var.value = str(payload[js_key])
            else:
                db.add(models.SystemVariable(key=db_key, value=str(payload[js_key])))
    db.commit()
    return {"status": "success"}


# --- SCANNER ---


@router.post("/scanner/validate/{token}", response_model=dict)
def validate_scanner_token(
    token: str,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_active_user),
):
    # Formato: CCF-MBR-{id}-{secret}
    if not token.startswith("CCF-MBR-"):
        raise HTTPException(status_code=400, detail="Formato de cÃ³digo invÃ¡lido")

    try:
        parts = token.split("-")
        persona_id = parts[2]
        secret = parts[3] if len(parts) > 3 else None

        try:
            db_id = uuid.UUID(persona_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Miembro no encontrado")

        persona = db.query(models.Persona).filter(models.Persona.id == db_id).first()

        if not persona:
            raise HTTPException(status_code=404, detail="Miembro no encontrado")

        # VALIDACIÃ“N DE INTEGRIDAD (Simulada para MVP, en PROD comparar con hash en DB)
        if not secret or len(secret) < 6:
            raise HTTPException(status_code=403, detail="CÃ³digo de seguridad invÃ¡lido o expirado")

        return {
            "valid": True,
            "persona_id": persona.id,
            "name": f"{persona.first_name} {persona.last_name}",
            "role": persona.church_role,
            "status": persona.spiritual_status,
            "timestamp": utc_now().isoformat(),
        }
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="CÃ³digo malformado")


# â”€â”€â”€ FARO EN CASA: TEMPORADAS & SESIONES â”€â”€â”€


@router.get("/analytics", response_model=dict)
def crm_analytics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/analytics", "/api/crm/analytics")
    """Métricas agregadas del CRM para el dashboard de analíticas."""
    total_members = db.query(models.Persona).count()
    active_members = (
        db.query(models.Persona)
        .filter(models.Persona.spiritual_status.in_(["Activo", "active", "Miembro Activo"]))
        .count()
    )

    # Consejería
    open_counseling = db.query(models.CounselingTicket).filter(models.CounselingTicket.status == "open").count()

    # Eventos del mes
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
    events_this_month = db.query(models.CrmEvent).filter(models.CrmEvent.event_date >= month_start).count()

    # Grupos
    total_groups = db.query(models.CellGroup).count()

    # Familia
    total_families = db.query(models.Family).count()

    return {
        "total_members": total_members,
        "active_members": active_members,
        "open_counseling": open_counseling,
        "events_this_month": events_this_month,
        "total_groups": total_groups,
        "total_families": total_families,
    }


# --- EVANGELISM STRATEGIES ---


@router.get("/strategies", response_model=List[EvangelismStrategy])
def read_evangelism_strategies(
    skip: int = 0,
    limit: int = 100,
    activa: Optional[bool] = None,
    clase_raiz: Optional[str] = None,
    sede_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    from backend.models_evangelism import GrupoEvangelismo
    from backend.crud.evangelism import get_estrategias

    strategies = get_estrategias(
        db,
        skip=skip,
        limit=limit,
        activa=activa,
        clase_raiz=clase_raiz,
        sede_id=sede_id,
    )
    result = []
    for s in strategies:
        obj = EvangelismStrategy.model_validate(s)
        obj.group_count = db.query(GrupoEvangelismo).filter(GrupoEvangelismo.estrategia_id == str(s.id)).count()
        result.append(obj)
    return result


@router.get("/strategies/{strategy_id}", response_model=EvangelismStrategy)
def read_strategy(
    strategy_id: str,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    from backend.models_evangelism import EstrategiaEvangelismo as StrategyModel
    from backend.models_evangelism import GrupoEvangelismo

    db_obj = db.query(StrategyModel).filter(StrategyModel.id == strategy_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Evangelism strategy not found")
    result = EvangelismStrategy.model_validate(db_obj)
    result.group_count = db.query(GrupoEvangelismo).filter(GrupoEvangelismo.estrategia_id == strategy_id).count()
    return result


@router.post("/strategies", response_model=EvangelismStrategy)
def create_strategy(
    strategy: EvangelismStrategyCreate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    try:
        result = create_evangelism_strategy(db=db, data=strategy)
    except Exception:
        db.rollback()
        raise
    # ── Phase scheduling trigger ──
    if strategy.typology == "evento_masivo" and strategy.phases:
        _project_phases_as_tasks(db, result.id, result.name, strategy.phases, strategy.start_date)
    return result


@router.put("/strategies/{strategy_id}", response_model=EvangelismStrategy)
def update_strategy(
    strategy_id: str,
    strategy: EvangelismStrategyUpdate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    try:
        db_obj = update_evangelism_strategy(db=db, strategy_id=strategy_id, data=strategy)
    except Exception:
        db.rollback()
        raise
    if not db_obj:
        raise HTTPException(status_code=404, detail="Evangelism strategy not found")
    result = EvangelismStrategy.model_validate(db_obj)
    # ── Phase scheduling trigger ──
    if strategy.typology == "evento_masivo" and strategy.phases:
        _project_phases_as_tasks(db, strategy_id, result.name, strategy.phases, strategy.start_date)
    return result


@router.post("/strategies/{strategy_id}/generate-sessions", response_model=dict)
def generate_strategy_sessions(
    strategy_id: str,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Genera sesiones automáticas para todos los grupos de una estrategia según su recurrencia."""
    from backend.models_evangelism import EstrategiaEvangelismo as StratModel
    from backend.models_evangelism import GrupoEvangelismo
    from backend.services.evangelism_projection import proyectar_sesiones

    strat = db.query(StratModel).filter(StratModel.id == strategy_id).first()
    if not strat:
        raise HTTPException(status_code=404, detail="Estrategia no encontrada")
    if not strat.frecuencia or not strat.fecha_inicio or not strat.fecha_fin:
        raise HTTPException(
            status_code=400,
            detail="La estrategia necesita: frecuencia, fecha_inicio, fecha_fin",
        )

    groups = db.query(GrupoEvangelismo).filter(GrupoEvangelismo.estrategia_id == strategy_id).all()

    try:
        created = proyectar_sesiones(
            db=db,
            estrategia_id=strategy_id,
            sede_id=strat.sede_id,
            fecha_inicio=strat.fecha_inicio,
            fecha_fin=strat.fecha_fin,
            frecuencia=strat.frecuencia,
            grupos_ids=[g.id for g in groups],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    sessions_per_group = created // len(groups) if groups else 0
    return {
        "strategy": strat.nombre,
        "recurrence": strat.frecuencia,
        "start": str(strat.fecha_inicio),
        "end": str(strat.fecha_fin),
        "sessions_per_group": sessions_per_group,
        "groups": len(groups),
        "total_sessions_created": created,
    }


@router.get(
    "/strategies/{strategy_id}/roles",
    response_model=List[schemas.RolPersonalizadoEstrategiaResponse],
)
def list_strategy_roles(
    strategy_id: str,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Lista los roles personalizados de una estrategia."""
    from backend.crud.evangelism import get_roles_personalizados

    strategy = db.query(models.EstrategiaEvangelismo).filter(models.EstrategiaEvangelismo.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Estrategia no encontrada")
    return get_roles_personalizados(db, estrategia_id=strategy_id)


@router.post(
    "/strategies/{strategy_id}/roles",
    response_model=schemas.RolPersonalizadoEstrategiaResponse,
)
def create_strategy_role(
    strategy_id: str,
    payload: schemas.RolPersonalizadoEstrategiaCreate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Crea un rol personalizado para una estrategia."""
    from backend.crud.evangelism import create_rol_personalizado

    strategy = db.query(models.EstrategiaEvangelismo).filter(models.EstrategiaEvangelismo.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Estrategia no encontrada")
    payload.estrategia_id = strategy_id
    return create_rol_personalizado(db, payload)


@router.delete("/strategies/{strategy_id}/roles/{role_id}")
def delete_strategy_role(
    strategy_id: str,
    role_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Elimina un rol personalizado de una estrategia."""
    from backend.crud.evangelism import delete_rol_personalizado

    if not delete_rol_personalizado(db, role_id):
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return {"ok": True}


# ──────────────────────────────────────────────
# MOTIVOS DE EXCUSA
# ──────────────────────────────────────────────


@router.get("/excuses", response_model=List[schemas.MotivoExcusaResponse])
def list_motivos_excusa(
    solo_activos: bool = True,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Lista el catálogo de motivos de excusa."""
    from backend.crud.evangelism import get_motivos_excusa

    return get_motivos_excusa(db, solo_activos=solo_activos)


@router.post("/excuses", response_model=schemas.MotivoExcusaResponse)
def create_motivo_excusa(
    payload: schemas.MotivoExcusaCreate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Crea un nuevo motivo de excusa."""
    from backend.crud.evangelism import create_motivo_excusa

    return create_motivo_excusa(db, payload.descripcion)


@router.patch("/excuses/{excusa_id}", response_model=schemas.MotivoExcusaResponse)
def update_motivo_excusa(
    excusa_id: int,
    payload: schemas.MotivoExcusaUpdate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Actualiza un motivo de excusa (no permite modificar los del sistema)."""
    from backend.crud.evangelism import update_motivo_excusa

    result = update_motivo_excusa(db, excusa_id, descripcion=payload.descripcion, activo=payload.activo)
    if not result:
        raise HTTPException(status_code=404, detail="Excusa no encontrada o es del sistema")
    return result


@router.delete("/excuses/{excusa_id}")
def delete_motivo_excusa(
    excusa_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Elimina un motivo de excusa (no permite eliminar los del sistema)."""
    from backend.crud.evangelism import delete_motivo_excusa

    if not delete_motivo_excusa(db, excusa_id):
        raise HTTPException(status_code=404, detail="Excusa no encontrada o es del sistema")
    return {"ok": True}


@router.post("/excuses/seed")
def seed_motivos_excusa(
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Inserta las excusas base del sistema (SALUD, TRABAJO, FAMILIA, OTRA)."""
    from backend.crud.evangelism import seed_motivos_excusa

    created = seed_motivos_excusa(db)
    return {"created": len(created), "excusas": [e.descripcion for e in created]}


def _project_phases_as_tasks(db, strategy_id: str, strategy_name: str, phases: list[dict], start_date=None):
    """Create N1 tasks in Projects module for each phase of a mass event."""
    from backend.models_projects import Project, ProjectTask
    from datetime import datetime

    # Create a project linked to the strategy
    project = Project(
        title=f"[MASIVO] {strategy_name}",
        description=f"Evento masivo generado desde estrategia de evangelismo #{strategy_id}",
        status="active",
        created_at=datetime.datetime.now(_tz.utc),
    )
    # Store strategy link in description
    db.add(project)
    db.flush()

    for i, phase in enumerate(phases):
        phase_name = phase.get("name", f"Fase {i + 1}")
        phase_type = phase.get("type", "general")
        phase_start = phase.get("start_date")
        phase_end = phase.get("end_date")

        try:
            sd = datetime.fromisoformat(phase_start.replace("Z", "+00:00")) if phase_start else None
        except Exception:
            sd = None
        try:
            dd = datetime.fromisoformat(phase_end.replace("Z", "+00:00")) if phase_end else None
        except Exception:
            dd = None

        task = ProjectTask(
            project_id=project.id,
            title=f"[N1] {phase_name}",
            description=f"Fase '{phase_type}' del evento masivo '{strategy_name}'. Generada automáticamente.",
            priority="urgent",  # N1 = highest priority
            status="todo",
            start_date=sd,
            due_date=dd,
            order_index=i,
            labels=["N1", "Evangelismo", phase_type] if phase_type else ["N1", "Evangelismo"],
            created_at=datetime.datetime.now(_tz.utc),
        )
        db.add(task)

    db.commit()
    return project


@router.delete("/strategies/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_strategy(
    strategy_id: str,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    if not delete_evangelism_strategy(db=db, strategy_id=strategy_id):
        raise HTTPException(status_code=404, detail="Evangelism strategy not found")
