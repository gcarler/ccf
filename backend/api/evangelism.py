import datetime
from datetime import timezone as _tz
import hashlib
import logging
import secrets
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.evangelism_events import router as events_router
from backend.api.evangelism_grupos import router as grupos_router
from backend.api.evangelism_main import (
    estrategias_router,
    roles_router,
)
from backend.api.evangelism_multiplication import router as multiplication_router
from backend.api.evangelism_notifications import router as notifications_router
from backend.api.evangelism_rankings import router as rankings_router
from backend.api.evangelism_reports import router as reports_router
from backend.api.evangelism_analytics import router as analytics_router
from backend.api.evangelism_shared import utc_now
from backend.auth import (
    require_active_user,
    require_admin,
    require_module_access,
    require_pastor_or_admin,
)
from backend.core.database import get_db
from backend.mesh_websockets import manager
from backend.services.messaging import get_messaging_gateway, MessagingGateway

router = APIRouter()
router.include_router(events_router)
router.include_router(grupos_router)
router.include_router(estrategias_router)
router.include_router(roles_router)
router.include_router(multiplication_router)
router.include_router(notifications_router)
router.include_router(rankings_router)
router.include_router(reports_router)
router.include_router(analytics_router)
logger = logging.getLogger(__name__)
_DEPRECATED_ALIAS_HITS: set[str] = set()


def _as_uuid(value) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def _persona_id_for_user(db: Session, user_id) -> uuid.UUID | None:
    user_uuid = _as_uuid(user_id)
    if not user_uuid:
        return None
    persona = db.query(models.Persona.id).filter(models.Persona.id == user_uuid).first()
    return persona[0] if persona else None


def _persona_id_from_identity(identity) -> uuid.UUID | None:
    return _as_uuid(identity)


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


# Audience resolution moved to crm/_shared.py, imported below:
from backend.api.crm._shared import _resolve_campaign_members, _member_matches_segment  # noqa: E402, F401


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
    gateway: MessagingGateway = Depends(get_messaging_gateway),
):
    _warn_deprecated_crm_alias("/api/evangelism/messaging/send", "/api/crm/messaging/send")

    persona_id = payload.get("persona_id")
    channel = _channel_label(payload.get("channel", "WhatsApp"))
    content = payload.get("content")
    campaign_name = payload.get("campaign_name") or payload.get("name")
    target_segments = payload.get("target_segments") or []
    try:
        if target_segments:
            if not campaign_name or not content:
                raise HTTPException(status_code=400, detail="campaign_name and content required")
            personas = _resolve_campaign_members(
                db,
                list(target_segments),
                sede_id=crud.get_user_sede_id(db, current_user.id),
            )
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
                        log = await gateway.send_whatsapp(
                            db,
                            persona.id,
                            content,
                            current_user.id,
                            campaign_name=campaign_name,
                            external_id=campaign_id,
                        )
                    elif channel.lower() == "email":
                        log = await gateway.send_email(
                            db,
                            persona.id,
                            content,
                            current_user.id,
                            campaign_name=campaign_name,
                            external_id=campaign_id,
                        )
                    else:
                        log = await gateway.send_sms(
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
                        leader_id=_persona_id_for_user(db, current_user.id),
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
            log = await gateway.send_whatsapp(
                db,
                persona_id,
                content,
                current_user.id,
            )
        elif channel.lower() == "email":
            log = await gateway.send_email(
                db,
                persona_id,
                content,
                current_user.id,
            )
        else:
            log = await gateway.send_sms(
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
    assigned_to = assignee_name or (assignee.nombre_completo if assignee else None)
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
    assignee_persona_id: Optional[str] = None,
    persona_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/tasks", "/api/crm/tasks")
    """Lista tareas pastorales optimizada con JOIN para evitar N+1."""
    try:
        from sqlalchemy.orm import joinedload

        q = db.query(models.CrmTask).options(joinedload(models.CrmTask.persona), joinedload(models.CrmTask.assignee))
        if assignee_persona_id:
            assignee_uuid = _as_uuid(assignee_persona_id)
            if not assignee_uuid:
                raise HTTPException(status_code=400, detail="assignee_persona_id must be a UUID")
            q = q.filter(models.CrmTask.assignee_id == assignee_uuid)
        if persona_id:
            persona_uuid = _as_uuid(persona_id)
            if not persona_uuid:
                raise HTTPException(status_code=400, detail="persona_id must be a UUID")
            q = q.filter(models.CrmTask.persona_id == persona_uuid)

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
                "assignee_persona_id": assignee_persona_id,
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

        my_persona_id = _persona_id_for_user(db, current_user.id)
        if not my_persona_id:
            raise HTTPException(status_code=404, detail="Perfil de miembro no encontrado")
        q = (
            db.query(models.CrmTask)
            .options(joinedload(models.CrmTask.persona), joinedload(models.CrmTask.assignee))
            .filter(models.CrmTask.assignee_id == my_persona_id)
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
        assignee_identity = payload.get("assignee_id") or current_user.id
        assignee_persona_id = _persona_id_from_identity(assignee_identity)
        if not assignee_persona_id:
            raise HTTPException(status_code=400, detail="assignee_id must be a UUID")
        task = models.CrmTask(
            title=title,
            description=payload.get("description"),
            status=payload.get("status", "pending"),
            priority=payload.get("priority", "medium"),
            category=payload.get("category", "Pastoral"),
            assignee_id=assignee_persona_id,
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
        persona_id = _persona_id_for_user(db, current_user.id)
        if not persona_id:
            raise HTTPException(404, "Perfil de miembro no encontrado")
        shift = models.VolunteerShift(
            persona_id=persona_id,
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


def _generate_scanner_token(persona_id: str, db: Session | None = None) -> dict:
    """Genera un scanner token CCF-MBR-{persona_id}-{secret}.

    Almacena el hash SHA-256 del secret en la BD con fecha de expiración.
    Retorna el token completo para ser mostrado al usuario (única vez).
    """
    db = db or next(get_db())
    try:
        persona = db.query(models.Persona).filter(models.Persona.id == persona_id).first()
        if not persona:
            raise HTTPException(status_code=404, detail="Persona no encontrada")

        secret = secrets.token_hex(16)  # 32 caracteres hex
        token = f"CCF-MBR-{persona_id}-{secret}"

        hashed = hashlib.sha256(secret.encode()).hexdigest()
        expires_at = datetime.datetime.now(_tz.utc) + datetime.timedelta(days=365)

        persona.scanner_token_hash = hashed
        persona.scanner_token_expires_at = expires_at
        db.commit()

        return {"token": token, "expires_at": expires_at.isoformat()}
    finally:
        db.close()


@router.post("/scanner/generate/{persona_id}", response_model=dict)
def generate_scanner_token_endpoint(
    persona_id: str,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Genera un nuevo scanner token para una persona (solo pastor/admin)."""
    return _generate_scanner_token(persona_id, db=db)


@router.post("/scanner/validate/{token}", response_model=dict)
def validate_scanner_token(
    token: str,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_active_user),
):
    # Formato: CCF-MBR-{persona_id}-{secret}
    # NOTA: persona_id es un UUID con guiones (36 chars). NO se puede
    # hacer split("-") porque rompe el UUID en segmentos.
    if not token.startswith("CCF-MBR-"):
        raise HTTPException(status_code=400, detail="Formato de codigo invalido")

    try:
        payload = token.removeprefix("CCF-MBR-")
        if len(payload) < 37:  # 36 chars UUID + 1 dash + secret
            raise HTTPException(status_code=400, detail="Token malformado")
        # El UUID con guiones mide exactamente 36 caracteres
        persona_id = payload[:36]
        secret = payload[37:]  # after the dash following the UUID
        if not secret:
            raise HTTPException(status_code=400, detail="Token malformado")

        try:
            db_id = uuid.UUID(persona_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Miembro no encontrado")

        persona = db.query(models.Persona).filter(models.Persona.id == db_id).first()

        if not persona:
            raise HTTPException(status_code=404, detail="Miembro no encontrado")

        if not persona.scanner_token_hash:
            raise HTTPException(
                status_code=403,
                detail="No hay token registrado para esta persona. Genere uno nuevo.",
            )

        # Verificar expiración
        token_expires_at = persona.scanner_token_expires_at
        if token_expires_at and getattr(token_expires_at, "tzinfo", None) is None:
            token_expires_at = token_expires_at.replace(tzinfo=_tz.utc)
        if token_expires_at and token_expires_at < datetime.datetime.now(_tz.utc):
            raise HTTPException(status_code=403, detail="Token expirado. Genere uno nuevo.")

        # Comparar hash SHA-256
        computed_hash = hashlib.sha256(secret.encode()).hexdigest()
        if not secrets.compare_digest(computed_hash, persona.scanner_token_hash):
            raise HTTPException(status_code=403, detail="Token de seguridad invalido")

        return {
            "valid": True,
            "persona_id": persona.id,
            "name": f"{persona.first_name} {persona.last_name}",
            "role": persona.church_role,
            "status": persona.spiritual_status,
            "timestamp": utc_now().isoformat(),
        }
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Token malformado")


# â”€â”€â”€ FARO EN CASA: TEMPORADAS & SESIONES â”€â”€â”€


@router.get("/analytics", response_model=dict)
def crm_analytics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/analytics", "/api/crm/analytics")
    """Métricas agregadas del CRM para el dashboard de analíticas, filtradas por sede."""
    from backend.core.tenant import require_user_sede_id

    sede_id = require_user_sede_id(db, current_user)

    total_members = db.query(models.Persona).filter(models.Persona.sede_id == sede_id).count()
    active_members = (
        db.query(models.Persona)
        .filter(
            models.Persona.sede_id == sede_id,
            models.Persona.spiritual_status.in_(["Activo", "active", "Miembro Activo"]),
        )
        .count()
    )

    # Consejería
    open_counseling = (
        db.query(models.CounselingTicket)
        .filter(
            models.CounselingTicket.sede_id == sede_id,
            models.CounselingTicket.status == "open",
        )
        .count()
    )

    # Eventos del mes
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    events_this_month = (
        db.query(models.CrmEvent)
        .filter(
            models.CrmEvent.sede_id == sede_id,
            models.CrmEvent.event_date >= month_start,
        )
        .count()
    )

    # Grupos
    total_groups = db.query(models.CellGroup).filter(models.CellGroup.sede_id == sede_id).count()

    # Familia (no tiene sede_id directo, contar miembros de la sede)
    from sqlalchemy import exists

    total_families = (
        db.query(models.Family)
        .filter(
            exists()
            .where(models.Persona.family_id == models.Family.id)
            .where(models.Persona.sede_id == sede_id)
        )
        .count()
    )

    return {
        "total_members": total_members,
        "active_members": active_members,
        "open_counseling": open_counseling,
        "events_this_month": events_this_month,
        "total_groups": total_groups,
        "total_families": total_families,
    }


# ──────────────────────────────────────────────
# ESTRATEGIAS, ROLES Y EXCUSAS
# ──────────────────────────────────────────────
# Migradas a backend/api/evangelism_main/:
#   main_estrategias.py — CRUD de estrategias (estrategias_router)
#   main_roles.py       — roles personalizados + excusas (roles_router)
# Montadas via router.include_router() al inicio del archivo.
