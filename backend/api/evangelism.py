import datetime
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.evangelism_events import router as events_router
from backend.api.evangelism_faro import router as faro_router
from backend.api.evangelism_shared import (_channel_label,
                                           _member_matches_segment,
                                           _resolve_campaign_members,
                                           _serialize_crm_task,
                                           _serialize_message_group, utc_now)
from backend.auth import (normalize_role, require_active_user, require_admin,
                          require_pastor_or_admin)
from backend.core.database import get_db
from backend.mesh_websockets import manager

router = APIRouter()
router.include_router(events_router)
router.include_router(faro_router)
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
    member_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/counseling/", "/api/crm/counseling/")
    tickets = crud.get_counseling_tickets(db, status=status)
    if member_id:
        tickets = [t for t in tickets if t.member_id == member_id]
    return tickets


@router.get("/counseling/{ticket_id}", response_model=dict)
def get_counseling_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias(
        "/api/evangelism/counseling/{ticket_id}", "/api/crm/counseling/{ticket_id}"
    )
    ticket = (
        db.query(models.CounselingTicket)
        .filter(models.CounselingTicket.id == ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    member = (
        db.query(models.Member).filter(models.Member.id == ticket.member_id).first()
    )
    related_history = (
        db.query(models.CounselingTicket)
        .filter(models.CounselingTicket.member_id == ticket.member_id)
        .order_by(models.CounselingTicket.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "id": ticket.id,
        "member_id": ticket.member_id,
        "member_name": (
            f"{member.first_name} {member.last_name}" if member else "Miembro CCF"
        ),
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
        tickets = (
            db.query(models.CounselingTicket)
            .filter(models.CounselingTicket.member_id == lead_id)
            .all()
        )
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
        logger.exception(
            "Failed to list counseling tickets by lead", extra={"lead_id": lead_id}
        )
        raise HTTPException(
            status_code=500, detail="No se pudo consultar la consejeria"
        )


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
    _warn_deprecated_crm_alias(
        "/api/evangelism/counseling/{ticket_id}", "/api/crm/counseling/{ticket_id}"
    )
    ticket = (
        db.query(models.CounselingTicket)
        .filter(models.CounselingTicket.id == ticket_id)
        .first()
    )
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
    _warn_deprecated_crm_alias(
        "/api/evangelism/prayer-requests/", "/api/crm/prayer-requests"
    )
    return crud.get_prayer_requests(db, status=status)


@router.post("/prayer-requests/", response_model=schemas.PrayerRequest)
def create_prayer_request(
    payload: schemas.PrayerRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias(
        "/api/evangelism/prayer-requests/", "/api/crm/prayer-requests"
    )
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
    req = (
        db.query(models.PrayerRequest)
        .filter(models.PrayerRequest.id == request_id)
        .first()
    )
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
    req = (
        db.query(models.PrayerRequest)
        .filter(models.PrayerRequest.id == request_id)
        .first()
    )
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


# --- GLORY HOUSES ---


def _channel_label(channel: str) -> str:
    value = str(channel or "").strip().lower()
    if value == "whatsapp":
        return "WhatsApp"
    if value == "email":
        return "Email"
    return "SMS"


def _member_matches_segment(
    member: models.Member, segment: str, donation_member_ids: set[int]
) -> bool:
    value = str(segment or "").strip().lower()
    if value == "active":
        return str(member.church_role or "").strip().lower() in {
            "miembro",
            "servidor",
            "lider",
            "lÃ­der",
            "pastor",
            "coordinador",
        }
    if value == "new":
        return str(member.spiritual_status or "").strip().lower() == "nuevo"
    if value == "staff":
        return str(member.church_role or "").strip().lower() in {
            "pastor",
            "coordinador",
            "staff",
            "administrador",
            "admin",
        }
    if value == "groups":
        return member.family_id is not None
    if value == "low":
        return str(member.spiritual_status or "").strip().lower() in {
            "nuevo",
            "creyente",
        }
    if value == "vip":
        return member.id in donation_member_ids
    return False


def _resolve_campaign_members(db: Session, segments: list[str]) -> list[models.Member]:
    normalized_segments = [
        segment for segment in (s.strip().lower() for s in segments) if segment
    ]
    if not normalized_segments:
        return []

    donation_member_ids = {
        member_id
        for (member_id,) in db.query(models.Donation.member_id)
        .filter(models.Donation.member_id.isnot(None))
        .distinct()
        .all()
    }
    members = db.query(models.Member).all()
    selected = []
    seen_ids: set[int] = set()
    for member in members:
        if member.id in seen_ids:
            continue
        if any(
            _member_matches_segment(member, segment, donation_member_ids)
            for segment in normalized_segments
        ):
            selected.append(member)
            seen_ids.add(member.id)
    return selected


def _serialize_message_group(logs: list[models.CommunicationLog]) -> dict:
    ordered = sorted(logs, key=lambda log: log.created_at or datetime.min, reverse=True)
    representative = ordered[0]
    member = getattr(representative, "member", None)
    member_name = f"{member.first_name} {member.last_name}" if member else "Desconocido"
    campaign_name = next(
        (log.campaign_name for log in ordered if log.campaign_name), None
    )
    sent_at_dt = ordered[0].created_at
    delivered_count = sum(
        1 for log in ordered if str(log.outcome).lower() in {"sent", "delivered"}
    )
    failed_count = sum(1 for log in ordered if str(log.outcome).lower() == "failed")
    if failed_count and not delivered_count:
        status = "failed"
    elif failed_count:
        status = "partial"
    else:
        status = str(representative.outcome or "sent").lower()
    display_name = campaign_name or (
        f"Mensaje a {member_name}"
        if len(ordered) == 1
        else f"CampaÃ±a a {len(ordered)} contactos"
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
    member_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias(
        "/api/evangelism/messaging/history", "/api/crm/messaging/history"
    )
    """Devuelve el historial de mensajes optimizado con JOIN para evitar N+1."""
    try:
        from sqlalchemy.orm import joinedload

        q = db.query(models.CommunicationLog).options(
            joinedload(models.CommunicationLog.member)
        )

        if member_id:
            q = q.filter(models.CommunicationLog.member_id == member_id)

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
            extra={"member_id": member_id, "limit": limit},
        )
        raise HTTPException(
            status_code=500, detail="No se pudo consultar el historial de mensajes"
        )


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
        .options(joinedload(models.CommunicationLog.member))
        .filter(models.CommunicationLog.id == log_id)
        .first()
    )
    if not log:
        raise HTTPException(status_code=404, detail="Message history item not found")

    if log.external_id:
        related_logs = (
            db.query(models.CommunicationLog)
            .options(joinedload(models.CommunicationLog.member))
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
    _warn_deprecated_crm_alias(
        "/api/evangelism/messaging/send", "/api/crm/messaging/send"
    )
    from backend.services.messaging import MessagingGateway

    member_id = payload.get("member_id")
    channel = _channel_label(payload.get("channel", "WhatsApp"))
    content = payload.get("content")
    campaign_name = payload.get("campaign_name") or payload.get("name")
    target_segments = payload.get("target_segments") or []
    try:
        if target_segments:
            if not campaign_name or not content:
                raise HTTPException(
                    status_code=400, detail="campaign_name and content required"
                )
            members = _resolve_campaign_members(db, list(target_segments))
            if not members:
                raise HTTPException(
                    status_code=404,
                    detail="No se encontraron destinatarios para la campaÃ±a",
                )

            campaign_id = f"CMP-{uuid.uuid4().hex[:12]}"
            logs: list[models.CommunicationLog] = []
            delivered_count = 0
            failed_count = 0
            for member in members:
                try:
                    if channel.lower() == "whatsapp":
                        log = await MessagingGateway.send_whatsapp(
                            db,
                            member.id,
                            content,
                            current_user.id,
                            campaign_name=campaign_name,
                            external_id=campaign_id,
                        )
                    elif channel.lower() == "email":
                        log = await MessagingGateway.send_email(
                            db,
                            member.id,
                            content,
                            current_user.id,
                            campaign_name=campaign_name,
                            external_id=campaign_id,
                        )
                    else:
                        log = await MessagingGateway.send_sms(
                            db,
                            member.id,
                            content,
                            current_user.id,
                            campaign_name=campaign_name,
                            external_id=campaign_id,
                        )
                    logs.append(log)
                    delivered_count += 1
                except ValueError:
                    fallback_log = models.CommunicationLog(
                        member_id=member.id,
                        channel=channel,
                        campaign_name=campaign_name,
                        recipient_phone=member.phone,
                        content=content,
                        leader_id=current_user.id,
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
                "target_count": len(members),
                "delivered_count": delivered_count,
                "failed_count": failed_count,
                "log_ids": [log.id for log in logs],
            }

        if not member_id or not content:
            raise HTTPException(
                status_code=400, detail="member_id and content required"
            )

        if channel.lower() == "whatsapp":
            log = await MessagingGateway.send_whatsapp(
                db,
                member_id,
                content,
                current_user.id,
            )
        elif channel.lower() == "email":
            log = await MessagingGateway.send_email(
                db,
                member_id,
                content,
                current_user.id,
            )
        else:
            log = await MessagingGateway.send_sms(
                db,
                member_id,
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
                "member_id": member_id,
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
    member = getattr(task, "member", None)
    member_name = contact_name or (
        f"{member.first_name} {member.last_name}" if member else None
    )
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
        "member_id": task.member_id,
        "member_name": member_name,
        "contact_name": member_name,
        "assigned_to": assigned_to,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.get("/tasks", response_model=List[dict])
def list_crm_tasks(
    status: Optional[str] = None,
    assignee_id: Optional[int] = None,
    member_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/tasks", "/api/crm/tasks")
    """Lista tareas pastorales optimizada con JOIN para evitar N+1."""
    try:
        from sqlalchemy.orm import joinedload

        q = db.query(models.CrmTask).options(
            joinedload(models.CrmTask.member), joinedload(models.CrmTask.assignee)
        )
        if assignee_id:
            q = q.filter(models.CrmTask.assignee_id == assignee_id)
        if member_id:
            q = q.filter(models.CrmTask.member_id == member_id)

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
                "member_id": member_id,
            },
        )
        raise HTTPException(status_code=500, detail="No se pudo consultar las tareas")


@router.get("/tasks/mine", response_model=List[dict])
def list_my_crm_tasks(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    _warn_deprecated_crm_alias("/api/evangelism/tasks/mine", "/api/crm/tasks/mine")
    try:
        from sqlalchemy.orm import joinedload

        q = (
            db.query(models.CrmTask)
            .options(
                joinedload(models.CrmTask.member), joinedload(models.CrmTask.assignee)
            )
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
        raise HTTPException(
            status_code=500, detail="No se pudieron consultar mis tareas"
        )


@router.get("/tasks/{task_id}", response_model=dict)
def get_crm_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias(
        "/api/evangelism/tasks/{task_id}", "/api/crm/tasks/{task_id}"
    )
    from sqlalchemy.orm import joinedload

    task = (
        db.query(models.CrmTask)
        .options(joinedload(models.CrmTask.member), joinedload(models.CrmTask.assignee))
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
            member_id=int(payload["member_id"]) if payload.get("member_id") else None,
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
        raise HTTPException(
            status_code=400, detail="Formato de fecha o identificador invalido"
        )
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
    _warn_deprecated_crm_alias(
        "/api/evangelism/tasks/{task_id}", "/api/crm/tasks/{task_id}"
    )
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
        "member_id",
    ]:
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
        "priority": getattr(task, "priority", "medium"),
        "category": getattr(task, "category", "Pastoral"),
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "created_at": (
            task.created_at.isoformat()
            if hasattr(task, "created_at") and task.created_at
            else None
        ),
    }


# --- VOLUNTEERS ---


@router.get("/volunteers/shifts", response_model=List[schemas.VolunteerShift])
def list_volunteer_shifts(
    member_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias(
        "/api/evangelism/volunteers/shifts", "/api/crm/volunteers"
    )
    return crud.get_volunteer_shifts(db, member_id=member_id)


@router.post("/volunteers/shifts", response_model=schemas.VolunteerShift)
def create_shift(
    payload: schemas.VolunteerShiftCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias(
        "/api/evangelism/volunteers/shifts", "/api/crm/volunteers"
    )
    return crud.create_volunteer_shift(db, payload)


@router.get("/volunteers/{member_id}", response_model=dict)
def get_volunteer_detail(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias(
        "/api/evangelism/volunteers/{member_id}", "/api/crm/volunteers/{member_id}"
    )
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    shifts = (
        db.query(models.VolunteerShift)
        .filter(models.VolunteerShift.member_id == member_id)
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
            .filter(models.member_volunteer_skills.c.member_id == member_id)
            .order_by(models.VolunteerSkill.name.asc())
            .all()
        )
    ]
    primary_shift = shifts[0] if shifts else None

    return {
        "id": member.id,
        "name": f"{member.first_name} {member.last_name}".strip(),
        "role": member.church_role,
        "team": (
            primary_shift.team_name
            if primary_shift
            else (member.church_role or "General")
        ),
        "status": (
            primary_shift.status
            if primary_shift
            else ("active" if member.is_baptized else "pending")
        ),
        "joined_date": (
            member.created_at.date().isoformat() if member.created_at else None
        ),
        "total_hours": total_hours,
        "skills": skills,
    }


@router.post("/volunteers/apply", response_model=dict)
def apply_volunteer(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias(
        "/api/evangelism/volunteers/apply", "/api/crm/volunteers"
    )
    """Registra la postulaciÃ³n de un miembro a un equipo de voluntariado."""
    try:
        from datetime import timedelta

        # Crear un turno pendiente como postulaciÃ³n
        member = (
            db.query(models.Member)
            .filter(models.Member.user_id == current_user.id)
            .first()
        )
        if not member:
            raise HTTPException(404, "Perfil de miembro no encontrado")
        shift = models.VolunteerShift(
            member_id=member.id,
            role_name=payload.get("team", "General"),
            team_name=payload.get("team", "General"),
            shift_start=utc_now(),
            shift_end=utc_now() + timedelta(hours=2),
            status="pending",
            notes=f"Disponibilidad: {payload.get('availability','')} | {payload.get('notes','')}",
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
def get_crm_settings(
    db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)
):
    _warn_deprecated_crm_alias("/api/evangelism/settings", "/api/crm/settings")
    """Lee la configuración de CRM desde system_variables."""
    settings = dict(CRM_DEFAULTS)
    rows = (
        db.query(models.SystemVariable)
        .filter(models.SystemVariable.key.in_(["crm_church_name", "crm_timezone"]))
        .all()
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
            var = (
                db.query(models.SystemVariable)
                .filter(models.SystemVariable.key == db_key)
                .first()
            )
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
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Valida un cÃ³digo QR de asistencia con check de integridad."""
    if normalize_role(str(current_user.role)) not in {"admin", "pastor"}:
        raise HTTPException(
            status_code=403, detail="Permisos insuficientes. Se requiere: crm:manage"
        )
    # Formato: CCF-MBR-{id}-{secret}
    if not token.startswith("CCF-MBR-"):
        raise HTTPException(status_code=400, detail="Formato de cÃ³digo invÃ¡lido")

    try:
        parts = token.split("-")
        member_id = int(parts[2])
        secret = parts[3] if len(parts) > 3 else None

        member = db.query(models.Member).filter(models.Member.id == member_id).first()

        if not member:
            raise HTTPException(status_code=404, detail="Miembro no encontrado")

        # VALIDACIÃ“N DE INTEGRIDAD (Simulada para MVP, en PROD comparar con hash en DB)
        if not secret or len(secret) < 6:
            raise HTTPException(
                status_code=403, detail="CÃ³digo de seguridad invÃ¡lido o expirado"
            )

        return {
            "valid": True,
            "member_id": member.id,
            "name": f"{member.first_name} {member.last_name}",
            "role": member.church_role,
            "status": member.spiritual_status,
            "timestamp": utc_now().isoformat(),
        }
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="CÃ³digo malformado")


# â”€â”€â”€ FARO EN CASA: TEMPORADAS & SESIONES â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@router.get("/analytics", response_model=dict)
def crm_analytics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    _warn_deprecated_crm_alias("/api/evangelism/analytics", "/api/crm/analytics")
    """MÃ©tricas agregadas del CRM para el dashboard de analÃ­ticas."""
    from sqlalchemy import func as sqlfunc

    total_members = db.query(models.Member).count()
    active_members = (
        db.query(models.Member)
        .filter(
            models.Member.spiritual_status.in_(["Activo", "active", "Miembro Activo"])
        )
        .count()
    )

    # Pipeline por etapa
    pipeline_rows = (
        db.query(
            models.ConsolidationPipeline.stage,
            sqlfunc.count(models.ConsolidationPipeline.id),
        )
        .group_by(models.ConsolidationPipeline.stage)
        .all()
    )
    pipeline_by_stage = {}
    for stage, count in pipeline_rows:
        normalized_stage = schemas.normalize_pipeline_stage(stage)
        pipeline_by_stage[normalized_stage] = (
            pipeline_by_stage.get(normalized_stage, 0) + count
        )
    total_leads = sum(pipeline_by_stage.values())

    # Consejería
    open_counseling = (
        db.query(models.CounselingTicket)
        .filter(models.CounselingTicket.status == "open")
        .count()
    )

    # Eventos del mes
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).replace(
        tzinfo=None
    )
    events_this_month = (
        db.query(models.CrmEvent)
        .filter(models.CrmEvent.event_date >= month_start)
        .count()
    )

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


# --- EVANGELISM STRATEGIES ---

from backend.crud.crm import (create_evangelism_strategy,
                              delete_evangelism_strategy,
                              get_evangelism_strategies,
                              update_evangelism_strategy)
from backend.schemas.crm import (EvangelismStrategy, EvangelismStrategyCreate,
                                 EvangelismStrategyUpdate)


@router.get("/strategies", response_model=List[EvangelismStrategy])
def read_evangelism_strategies(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    return get_evangelism_strategies(db, skip=skip, limit=limit)


@router.get("/strategies/{strategy_id}", response_model=EvangelismStrategy)
def read_strategy(strategy_id: int, db: Session = Depends(get_db)):
    from backend.models_crm import EvangelismStrategy
    db_obj = db.query(EvangelismStrategy).filter(EvangelismStrategy.id == strategy_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Evangelism strategy not found")
    return db_obj


@router.post("/strategies", response_model=EvangelismStrategy)
def create_strategy(strategy: EvangelismStrategyCreate, db: Session = Depends(get_db)):
    return create_evangelism_strategy(db=db, strategy=strategy)


@router.put("/strategies/{strategy_id}", response_model=EvangelismStrategy)
def update_strategy(
    strategy_id: int, strategy: EvangelismStrategyUpdate, db: Session = Depends(get_db)
):
    db_obj = update_evangelism_strategy(
        db=db, strategy_id=strategy_id, strategy=strategy
    )
    if not db_obj:
        raise HTTPException(status_code=404, detail="Evangelism strategy not found")
    return db_obj


@router.delete("/strategies/{strategy_id}", response_model=EvangelismStrategy)
def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    db_obj = delete_evangelism_strategy(db=db, strategy_id=strategy_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Evangelism strategy not found")
    return db_obj
