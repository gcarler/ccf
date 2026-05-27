import collections
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.crm._shared import (_member_full_name, _serialize_case,
                                     _serialize_message_group, _serialize_task,
                                     utc_now)
from backend.auth import (get_current_user, normalize_role, require_active_user,
                          require_module_access, require_pastor_or_admin)
from backend.core.audit import record_admin_action
from backend.core.database import get_db
from backend.mesh_websockets import manager
from backend.services.messaging import MessagingGateway
from backend.services.public_contact_tracking import ContactRecord, tracker

router = APIRouter(tags=["CRM"])
logger = logging.getLogger(__name__)


@router.get("/consolidation/cases/{case_id}", response_model=dict)
def get_consolidation_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    case = (
        db.query(models.ConsolidationCase)
        .filter(models.ConsolidationCase.id == case_id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return _serialize_case(case)


@router.post("/consolidation/cases", response_model=dict)
def create_consolidation_case(
    payload: schemas.ConsolidationCaseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    member = (
        db.query(models.Member).filter(models.Member.id == payload.member_id).first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    row = models.ConsolidationCase(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_case(row)


@router.patch("/consolidation/cases/{case_id}", response_model=dict)
def update_consolidation_case(
    case_id: int,
    payload: schemas.ConsolidationCaseUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    case = (
        db.query(models.ConsolidationCase)
        .filter(models.ConsolidationCase.id == case_id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(case, key, value)
    db.commit()
    db.refresh(case)
    return _serialize_case(case)


@router.post("/consolidation/cases/{case_id}/assignments", response_model=dict)
def create_consolidation_assignment(
    case_id: int,
    payload: schemas.ConsolidationAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    case = (
        db.query(models.ConsolidationCase)
        .filter(models.ConsolidationCase.id == case_id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    assignment_data = payload.model_dump(exclude={"case_id"})
    row = models.ConsolidationAssignment(**assignment_data, case_id=case_id)
    db.add(row)
    case.assigned_pastor_id = payload.assigned_by_member_id
    case.assigned_leader_id = payload.assigned_to_member_id
    case.updated_at = utc_now()
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "case_id": row.case_id,
        "assigned_by_member_id": row.assigned_by_member_id,
        "assigned_to_member_id": row.assigned_to_member_id,
        "status": row.status,
        "priority": row.priority,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.post("/consolidation/cases/{case_id}/interactions", response_model=dict)
def create_consolidation_interaction(
    case_id: int,
    payload: schemas.ConsolidationInteractionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    case = (
        db.query(models.ConsolidationCase)
        .filter(models.ConsolidationCase.id == case_id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    interaction_data = payload.model_dump(exclude={"case_id"})
    row = models.ConsolidationInteraction(**interaction_data, case_id=case_id)
    db.add(row)
    case.last_contact_at = row.interaction_date
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "case_id": row.case_id,
        "performed_by_member_id": row.performed_by_member_id,
        "interaction_type": row.interaction_type,
        "interaction_date": (
            row.interaction_date.isoformat() if row.interaction_date else None
        ),
        "result": row.result,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.post("/consolidation/cases/{case_id}/tasks", response_model=dict)
def create_consolidation_task(
    case_id: int,
    payload: schemas.ConsolidationFollowUpTaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    case = (
        db.query(models.ConsolidationCase)
        .filter(models.ConsolidationCase.id == case_id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    task_data = payload.model_dump(exclude={"case_id"})
    row = models.ConsolidationFollowUpTask(**task_data, case_id=case_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "case_id": row.case_id,
        "assignment_id": row.assignment_id,
        "title": row.title,
        "status": row.status,
        "due_date": row.due_date.isoformat() if row.due_date else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


# --- LIST / DELETE Cases, nested resources ---


@router.get("/consolidation/cases", response_model=dict)
def list_consolidation_cases(
    source: Optional[str] = None,
    stage: Optional[str] = None,
    status: Optional[str] = None,
    member_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Lista casos de consolidación con paginación y filtros."""
    q = db.query(models.ConsolidationCase)

    if source:
        q = q.filter(models.ConsolidationCase.source == source)
    if stage:
        q = q.filter(models.ConsolidationCase.stage == stage)
    if status:
        q = q.filter(models.ConsolidationCase.status == status)
    if member_id:
        q = q.filter(models.ConsolidationCase.member_id == member_id)

    total = q.count()
    cases = (
        q.order_by(models.ConsolidationCase.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "cases": [_serialize_case(c) for c in cases],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
    }


@router.delete("/consolidation/cases/{case_id}", status_code=204)
def delete_consolidation_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Elimina un caso de consolidación."""
    case = (
        db.query(models.ConsolidationCase)
        .filter(models.ConsolidationCase.id == case_id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    db.delete(case)
    db.commit()
    return None


@router.get("/consolidation/cases/{case_id}/tasks", response_model=List[dict])
def list_consolidation_tasks(
    case_id: int,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Lista las tareas de seguimiento de un caso."""
    case = (
        db.query(models.ConsolidationCase)
        .filter(models.ConsolidationCase.id == case_id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    q = (
        db.query(models.ConsolidationFollowUpTask)
        .filter(models.ConsolidationFollowUpTask.case_id == case_id)
    )
    if status_filter:
        q = q.filter(models.ConsolidationFollowUpTask.status == status_filter)

    tasks = q.order_by(models.ConsolidationFollowUpTask.created_at.desc()).all()
    return [
        {
            "id": t.id,
            "case_id": t.case_id,
            "assignment_id": t.assignment_id,
            "title": t.title,
            "description": t.description,
            "status": t.status,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tasks
    ]


@router.patch("/consolidation/cases/{case_id}/tasks/{task_id}", response_model=dict)
def update_consolidation_task(
    case_id: int,
    task_id: int,
    payload: schemas.ConsolidationFollowUpTaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Actualiza una tarea de seguimiento (ej. marcar como completada)."""
    task = (
        db.query(models.ConsolidationFollowUpTask)
        .filter(
            models.ConsolidationFollowUpTask.id == task_id,
            models.ConsolidationFollowUpTask.case_id == case_id,
        )
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)

    return {
        "id": task.id,
        "case_id": task.case_id,
        "assignment_id": task.assignment_id,
        "title": task.title,
        "status": task.status,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.get("/consolidation/cases/{case_id}/interactions", response_model=List[dict])
def list_consolidation_interactions(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Lista las interacciones de un caso de consolidación."""
    case = (
        db.query(models.ConsolidationCase)
        .filter(models.ConsolidationCase.id == case_id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    interactions = (
        db.query(models.ConsolidationInteraction)
        .filter(models.ConsolidationInteraction.case_id == case_id)
        .order_by(models.ConsolidationInteraction.created_at.desc())
        .all()
    )
    return [
        {
            "id": i.id,
            "case_id": i.case_id,
            "performed_by_member_id": i.performed_by_member_id,
            "interaction_type": i.interaction_type,
            "interaction_date": i.interaction_date.isoformat() if i.interaction_date else None,
            "result": i.result,
            "notes": i.notes,
            "next_action_date": i.next_action_date.isoformat() if i.next_action_date else None,
            "created_at": i.created_at.isoformat() if i.created_at else None,
        }
        for i in interactions
    ]


@router.patch("/consolidation/assignments/{assignment_id}", response_model=dict)
def update_consolidation_assignment(
    assignment_id: int,
    payload: schemas.ConsolidationAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Actualiza una asignación de consolidación."""
    assignment = (
        db.query(models.ConsolidationAssignment)
        .filter(models.ConsolidationAssignment.id == assignment_id)
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(assignment, key, value)
    db.commit()
    db.refresh(assignment)
    return {
        "id": assignment.id,
        "case_id": assignment.case_id,
        "assigned_by_member_id": assignment.assigned_by_member_id,
        "assigned_to_member_id": assignment.assigned_to_member_id,
        "status": assignment.status,
        "priority": assignment.priority,
        "end_date": assignment.end_date.isoformat() if assignment.end_date else None,
        "created_at": assignment.created_at.isoformat() if assignment.created_at else None,
    }


# --- CONSOLIDATION & PIPELINE ---


@router.get("/consolidation/pipeline", response_model=List[dict])
def get_pipeline(
    stage: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    leads = crud.get_pipeline_leads(db, stage=stage)
    result = []
    for lead in leads:
        result.append(
            {
                "id": lead.id,
                "first_name": lead.first_name,
                "last_name": lead.last_name,
                "phone": lead.phone,
                "source": lead.source,
                "stage": schemas.normalize_pipeline_stage(lead.stage),
                "notes": lead.notes,
                "created_at": lead.created_at.isoformat(),
                "assigned_pastor_id": lead.assigned_pastor_id,
            }
        )
    return result


@router.post("/consolidation/pipeline", response_model=dict)
async def create_pipeline_lead(
    payload: schemas.ConsolidationPipelineCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
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
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Obtiene el detalle de un prospecto especifico."""
    lead = (
        db.query(models.ConsolidationPipeline)
        .filter(models.ConsolidationPipeline.id == lead_id)
        .first()
    )
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
        "assigned_pastor_id": lead.assigned_pastor_id,
    }


@router.patch("/consolidation/pipeline/{lead_id}", response_model=dict)
async def update_pipeline_lead(
    lead_id: int,
    payload: schemas.ConsolidationPipelineUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    lead = crud.update_pipeline_lead(db, lead_id=lead_id, payload=payload)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Audit logging for pipeline movements
    record_admin_action(
        db,
        current_user,
        action="update_pipeline_lead",
        resource_type="pipeline_lead",
        resource_id=str(lead.id),
        metadata=payload.model_dump(exclude_unset=True),
    )

    # BROADCAST REAL-TIME UPDATE
    await manager.broadcast_event(
        {
            "type": "PIPELINE_UPDATED",
            "lead_id": lead.id,
            "stage": lead.stage,
            "actor": current_user.username,
        },
        room="pastoral_ops",
    )

    return {
        "status": "success",
        "lead_id": lead.id,
        "stage": schemas.normalize_pipeline_stage(lead.stage),
    }


@router.delete("/consolidation/pipeline/{lead_id}", status_code=204)
def delete_pipeline_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Elimina un lead del pipeline de consolidacion."""
    lead = (
        db.query(models.ConsolidationPipeline)
        .filter(models.ConsolidationPipeline.id == lead_id)
        .first()
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.delete(lead)
    db.commit()
    return None


@router.get(
    "/consolidation/pipeline/{lead_id}/audit",
    response_model=List[schemas.AdminAuditLog],
)
def get_pipeline_lead_audit(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Retrieve the audit trail for a specific pipeline lead."""
    logs = (
        db.query(models.AdminAuditLog)
        .filter(
            models.AdminAuditLog.resource_type == "pipeline_lead",
            models.AdminAuditLog.resource_id == str(lead_id),
        )
        .order_by(models.AdminAuditLog.created_at.desc())
        .all()
    )
    return logs


@router.get("/pipeline/leads/{lead_id}/calls", response_model=List[dict])
def get_lead_calls(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
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
    current_user: models.User = Depends(require_pastor_or_admin),
):
    lead = (
        db.query(models.ConsolidationPipeline)
        .filter(models.ConsolidationPipeline.id == lead_id)
        .first()
    )
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


@router.post("/messaging/send", response_model=dict)
async def send_crm_message(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    channel = str(payload.get("channel") or "").strip().lower()
    content = str(payload.get("content") or "").strip()
    if not channel or not content:
        raise HTTPException(status_code=400, detail="channel and content are required")

    campaign_name = payload.get("campaign_name") or payload.get("name")
    member_id = payload.get("member_id")
    target_segments = payload.get("target_segments") or []

    if member_id:
        target_members = [{"id": int(member_id)}]
    else:
        member_map: dict[int, models.Member] = {}
        for segment in target_segments:
            normalized = str(segment).strip().lower()
            if normalized == "active":
                rows = (
                    db.query(models.Member)
                    .filter(models.Member.church_role == "Miembro")
                    .all()
                )
            elif normalized == "groups":
                rows = (
                    db.query(models.Member)
                    .filter(models.Member.family_id.isnot(None))
                    .all()
                )
            else:
                rows = []
            for member in rows:
                member_map[member.id] = member
        target_members = list(member_map.values())

    if not target_members:
        raise HTTPException(status_code=404, detail="No target members found")

    external_id = f"CMP-{uuid.uuid4().hex[:12]}" if len(target_members) > 1 else None
    delivered_count = 0
    failed_count = 0
    log_ids: list[int] = []

    for member in target_members:
        member_id_value = member["id"] if isinstance(member, dict) else member.id
        try:
            if channel == "whatsapp":
                log = await MessagingGateway.send_whatsapp(
                    db,
                    member_id_value,
                    content,
                    current_user.id,
                    campaign_name=campaign_name,
                    external_id=external_id,
                )
            elif channel == "sms":
                log = await MessagingGateway.send_sms(
                    db,
                    member_id_value,
                    content,
                    current_user.id,
                    campaign_name=campaign_name,
                    external_id=external_id,
                )
            elif channel == "email":
                log = await MessagingGateway.send_email(
                    db,
                    member_id_value,
                    content,
                    current_user.id,
                    campaign_name=campaign_name,
                    external_id=external_id,
                )
            else:
                raise HTTPException(status_code=400, detail="Unsupported channel")
            delivered_count += 1
            log_ids.append(log.id)
        except HTTPException:
            raise
        except MemoryError:
            raise
        except Exception:
            failed_count += 1
            if len(target_members) == 1:
                logger.exception("Messaging gateway failure")
                raise HTTPException(
                    status_code=502, detail="No se pudo enviar el mensaje"
                )

    return {
        "status": "success",
        "target_count": len(target_members),
        "delivered_count": delivered_count,
        "failed_count": failed_count,
        "log_ids": log_ids,
    }


@router.get("/messaging/history", response_model=List[dict])
def list_messaging_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    logs = (
        db.query(models.CommunicationLog)
        .order_by(models.CommunicationLog.created_at.desc())
        .all()
    )
    grouped: "collections.OrderedDict[str, list[models.CommunicationLog]]" = (
        collections.OrderedDict()
    )
    for log in logs:
        key = log.external_id or f"log-{log.id}"
        grouped.setdefault(key, []).append(log)
    return [_serialize_message_group(items) for items in grouped.values()]


@router.get("/messaging/history/{log_id}", response_model=dict)
def get_messaging_history_item(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    log = (
        db.query(models.CommunicationLog)
        .filter(models.CommunicationLog.id == log_id)
        .first()
    )
    if not log:
        raise HTTPException(status_code=404, detail="Message not found")
    if log.external_id:
        logs = (
            db.query(models.CommunicationLog)
            .filter(models.CommunicationLog.external_id == log.external_id)
            .order_by(models.CommunicationLog.created_at.desc())
            .all()
        )
    else:
        logs = [log]
    return _serialize_message_group(logs)


@router.get("/tasks", response_model=List[dict])
def list_crm_tasks(
    assignee_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Lista todas las tareas CRM con filtro opcional por asignado."""
    q = db.query(models.CrmTask)
    if assignee_id:
        q = q.filter(models.CrmTask.assignee_id == assignee_id)
    tasks = q.order_by(models.CrmTask.created_at.desc()).all()
    return [_serialize_task(t) for t in tasks]


@router.post("/tasks/", response_model=dict)
def create_crm_task(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    title = str(payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    due_date = None
    raw_due_date = payload.get("due_date")
    if raw_due_date:
        try:
            due_date = datetime.fromisoformat(str(raw_due_date).replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Formato de fecha o identificador invalido"
            )

    task = models.CrmTask(
        title=title,
        description=payload.get("description"),
        category=payload.get("category") or "Pastoral",
        member_id=payload.get("member_id"),
        assignee_id=payload.get("assignee_id") or current_user.id,
        due_date=due_date,
        status=payload.get("status") or "pending",
        priority=payload.get("priority") or "medium",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _serialize_task(task)


@router.get("/tasks/mine", response_model=List[dict])
def list_my_crm_tasks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    tasks = (
        db.query(models.CrmTask)
        .filter(models.CrmTask.assignee_id == current_user.id)
        .order_by(models.CrmTask.created_at.desc())
        .all()
    )
    return [_serialize_task(task) for task in tasks]


@router.get("/tasks/{task_id}", response_model=dict)
def get_crm_task_detail(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    task = db.query(models.CrmTask).filter(models.CrmTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    is_staff = normalize_role(str(current_user.role)) in {
        "admin",
        "pastor",
        "coordinador",
    }
    if not is_staff and task.assignee_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado para ver esta tarea")
    return _serialize_task(task)


@router.patch("/tasks/{task_id}", response_model=dict)
def update_crm_task(
    task_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    task = db.query(models.CrmTask).filter(models.CrmTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field in (
        "title",
        "description",
        "category",
        "status",
        "priority",
        "due_date",
        "assignee_id",
        "member_id",
    ):
        if field in payload:
            val = payload[field]
            if field == "due_date" and isinstance(val, str):
                try:
                    val = datetime.fromisoformat(val.replace("Z", "+00:00"))
                except ValueError:
                    raise HTTPException(
                        status_code=400, detail="Formato de fecha inválido"
                    )
            setattr(task, field, val)
    db.commit()
    db.refresh(task)
    return _serialize_task(task)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_crm_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Elimina una tarea del CRM."""
    task = (
        db.query(models.CrmTask)
        .filter(models.CrmTask.id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return None


@router.get("/counseling/{ticket_id}", response_model=dict)
def get_counseling_detail(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    ticket = (
        db.query(models.CounselingTicket)
        .filter(models.CounselingTicket.id == ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Counseling ticket not found")
    history_rows = (
        db.query(models.CounselingTicket)
        .filter(models.CounselingTicket.member_id == ticket.member_id)
        .order_by(
            models.CounselingTicket.created_at.desc(), models.CounselingTicket.id.desc()
        )
        .all()
    )
    return {
        "id": ticket.id,
        "member_id": ticket.member_id,
        "member_name": _member_full_name(ticket.member),
        "topic": ticket.subject,
        "summary": ticket.subject,
        "notes": ticket.notes,
        "confidential_notes": ticket.notes,
        "status": ticket.status,
        "priority_level": ticket.priority_level,
        "duration_minutes": 60,
        "history": [
            {
                "id": row.id,
                "text": row.subject,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in history_rows
        ],
    }


@router.get("/glory-houses/{house_id}", response_model=dict)
def get_glory_house_detail(
    house_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    house = db.query(models.GloryHouse).filter(models.GloryHouse.id == house_id).first()
    if not house:
        raise HTTPException(status_code=404, detail="Glory house not found")
    return {
        "id": house.id,
        "code": house.code,
        "name": house.name,
        "zone": house.zone,
        "address": house.address,
        "leader_id": house.leader_id,
        "assistant_id": house.assistant_id,
        "host_id": house.host_id,
        "day_of_week": house.day_of_week,
        "start_time": house.start_time,
        "end_time": house.end_time,
        "leader_name": house.leader_name,
        "members_count": house.members_count,
        "capacity": house.capacity,
        "status": str(house.status).lower(),
        "base_attendee_ids": [row.member_id for row in (house.base_attendees or [])],
        "base_attendees": [
            {
                "member_id": row.member_id,
                "role": row.role,
            }
            for row in (house.base_attendees or [])
        ],
    }


@router.get("/glory-houses", response_model=List[dict])
def list_glory_houses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    houses = db.query(models.GloryHouse).order_by(models.GloryHouse.name.asc()).all()
    return [
        {
            "id": house.id,
            "code": house.code,
            "name": house.name,
            "zone": house.zone,
            "address": house.address,
            "leader_name": house.leader_name,
            "members_count": house.members_count,
            "capacity": house.capacity,
            "status": str(house.status).lower() if house.status else "active",
        }
        for house in houses
    ]


@router.put("/glory-houses/{house_id}", response_model=dict)
def update_glory_house(
    house_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    house = db.query(models.GloryHouse).filter(models.GloryHouse.id == house_id).first()
    if not house:
        raise HTTPException(status_code=404, detail="Glory house not found")

    editable = [
        "code",
        "name",
        "zone",
        "address",
        "leader_id",
        "assistant_id",
        "host_id",
        "capacity",
        "day_of_week",
        "start_time",
        "end_time",
        "status",
    ]
    for field in editable:
        if field in payload:
            setattr(house, field, payload[field])

    if "base_attendee_ids" in payload and isinstance(
        payload["base_attendee_ids"], list
    ):
        normalized_ids = []
        for raw_id in payload["base_attendee_ids"]:
            try:
                normalized_ids.append(int(raw_id))
            except (TypeError, ValueError):
                continue
        normalized_ids = list(dict.fromkeys(normalized_ids))
        current_rows = (
            db.query(models.GloryHouseMember)
            .filter(models.GloryHouseMember.glory_house_id == house.id)
            .all()
        )
        current_by_member = {row.member_id: row for row in current_rows}
        incoming_ids = set(normalized_ids)

        for row in current_rows:
            if row.member_id not in incoming_ids:
                db.delete(row)
        for member_id in normalized_ids:
            if member_id in current_by_member:
                continue
            db.add(
                models.GloryHouseMember(
                    glory_house_id=house.id,
                    member_id=member_id,
                    role="asistente",
                )
            )

    db.commit()
    db.refresh(house)

    return {
        "id": house.id,
        "code": house.code,
        "name": house.name,
        "zone": house.zone,
        "address": house.address,
        "leader_id": house.leader_id,
        "assistant_id": house.assistant_id,
        "host_id": house.host_id,
        "capacity": house.capacity,
        "day_of_week": house.day_of_week,
        "start_time": house.start_time,
        "end_time": house.end_time,
        "status": str(house.status).lower() if house.status else "active",
        "members_count": house.members_count,
        "base_attendee_ids": [row.member_id for row in (house.base_attendees or [])],
        "base_attendees": [
            {"member_id": row.member_id, "role": row.role}
            for row in (house.base_attendees or [])
        ],
    }


@router.get("/prayer-requests/{request_id}", response_model=dict)
def get_prayer_request_detail(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    prayer = (
        db.query(models.PrayerRequest)
        .filter(models.PrayerRequest.id == request_id)
        .first()
    )
    if not prayer:
        raise HTTPException(status_code=404, detail="Prayer request not found")
    return {
        "id": prayer.id,
        "requester_name": prayer.requester_name,
        "request_text": prayer.request_text,
        "category": prayer.category,
        "status": prayer.status,
    }


# ── Counseling (CRM prefix) ──────────────────────────────


@router.get("/counseling/", response_model=List[dict])
def list_counseling_tickets(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    tickets = crud.get_counseling_tickets(db, status=status)
    return [
        {
            "id": t.id,
            "member_id": t.member_id,
            "member_name": _member_full_name(t.member) if t.member else "",
            "topic": t.subject,
            "summary": t.subject,
            "notes": t.notes,
            "status": t.status,
            "priority_level": t.priority_level or "medium",
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tickets
    ]


@router.post("/counseling/", response_model=dict, status_code=201)
def create_counseling_ticket(
    payload: schemas.CounselingTicketCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    ticket = crud.create_counseling_ticket(db, payload)
    return {
        "id": ticket.id,
        "member_id": ticket.member_id,
        "member_name": _member_full_name(ticket.member) if ticket.member else "",
        "topic": ticket.subject,
        "summary": ticket.subject,
        "notes": ticket.notes,
        "status": ticket.status,
        "priority_level": ticket.priority_level or "medium",
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
    }


@router.get("/counseling/lead/{lead_id}", response_model=List[dict])
def get_counseling_by_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    tickets = (
        db.query(models.CounselingTicket)
        .filter(models.CounselingTicket.member_id == lead_id)
        .order_by(models.CounselingTicket.created_at.desc())
        .all()
    )
    return [
        {
            "id": t.id,
            "member_id": t.member_id,
            "member_name": _member_full_name(t.member) if t.member else "",
            "topic": t.subject,
            "summary": t.subject,
            "notes": t.notes,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tickets
    ]


@router.patch("/counseling/{ticket_id}", response_model=dict)
def update_counseling_ticket(
    ticket_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    ticket = (
        db.query(models.CounselingTicket)
        .filter(models.CounselingTicket.id == ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Counseling ticket not found")
    for field in ("status", "notes", "priority_level"):
        if field in payload:
            setattr(
                ticket,
                field if field != "priority_level" else "priority_level",
                payload[field],
            )
    if "subject" in payload:
        ticket.subject = payload["subject"]
    db.commit()
    db.refresh(ticket)
    return {
        "id": ticket.id,
        "member_id": ticket.member_id,
        "member_name": _member_full_name(ticket.member) if ticket.member else "",
        "topic": ticket.subject,
        "status": ticket.status,
        "notes": ticket.notes,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
    }


# ── Settings ─────────────────────────────────────────────


@router.get("/settings", response_model=dict)
def get_crm_settings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    row = crud.get_or_create_page_content(db, "crm_settings")
    import json

    try:
        return json.loads(row.content) if row.content else {}
    except (json.JSONDecodeError, TypeError):
        return {}


@router.post("/settings", response_model=dict)
def save_crm_settings(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    import json

    crud.update_page_content(
        db,
        "crm_settings",
        schemas.PageContentUpdate(
            title="CRM Settings", content=json.dumps(payload, ensure_ascii=False)
        ),
    )
    return payload


@router.get("/roles", response_model=List[dict])
def list_crm_roles(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    rows = (
        db.query(models.RoleDefinition)
        .order_by(
            models.RoleDefinition.is_leadership.desc(), models.RoleDefinition.name.asc()
        )
        .all()
    )
    return [
        {
            "id": row.id,
            "name": row.name,
            "color": row.color,
            "is_leadership": row.is_leadership,
        }
        for row in rows
    ]


@router.post("/roles", response_model=dict, status_code=201)
def create_crm_role(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    name = str(payload.get("name") or "").strip()
    color = str(payload.get("color") or "").strip()
    if not name or not color:
        raise HTTPException(status_code=400, detail="name and color are required")
    exists = (
        db.query(models.RoleDefinition)
        .filter(models.RoleDefinition.name == name)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="El rol ya existe")
    row = models.RoleDefinition(
        name=name,
        color=color,
        is_leadership=bool(payload.get("is_leadership")),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "name": row.name,
        "color": row.color,
        "is_leadership": row.is_leadership,
    }


@router.put("/roles/{role_id}", response_model=dict)
def update_crm_role(
    role_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    row = (
        db.query(models.RoleDefinition)
        .filter(models.RoleDefinition.id == role_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    new_name = payload.get("name")
    if new_name is not None:
        new_name = str(new_name).strip()
        if not new_name:
            raise HTTPException(status_code=400, detail="name cannot be empty")
        exists = (
            db.query(models.RoleDefinition)
            .filter(
                models.RoleDefinition.name == new_name,
                models.RoleDefinition.id != role_id,
            )
            .first()
        )
        if exists:
            raise HTTPException(
                status_code=400, detail="Ya existe otro rol con ese nombre"
            )
        db.query(models.Member).filter(models.Member.church_role == row.name).update(
            {"church_role": new_name}
        )
        row.name = new_name

    if "color" in payload:
        row.color = str(payload.get("color") or "").strip()
    if "is_leadership" in payload:
        row.is_leadership = bool(payload.get("is_leadership"))

    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "name": row.name,
        "color": row.color,
        "is_leadership": row.is_leadership,
    }


@router.delete("/roles/{role_id}", response_model=dict)
def delete_crm_role(
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
    db.query(models.Member).filter(models.Member.church_role == role.name).update(
        {"church_role": fallback.name}
    )
    db.delete(role)
    db.commit()
    return {
        "success": True,
        "message": "Rol eliminado y miembros reasignados correctamente",
    }


@router.get("/analytics", response_model=dict)
def get_crm_analytics_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    total_members = db.query(models.Member).count()
    active_members = (
        db.query(models.Member)
        .filter(
            models.Member.spiritual_status.in_(["Activo", "active", "Miembro Activo"])
        )
        .count()
    )
    pipeline_rows = (
        db.query(
            models.ConsolidationPipeline.stage,
            func.count(models.ConsolidationPipeline.id),
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
    open_counseling = (
        db.query(models.CounselingTicket)
        .filter(models.CounselingTicket.status == "open")
        .count()
    )
    month_start = (
        datetime.now(timezone.utc)
        .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        .replace(tzinfo=None)
    )
    events_this_month = (
        db.query(models.CrmEvent)
        .filter(models.CrmEvent.event_date >= month_start)
        .count()
    )
    total_groups = db.query(models.GloryHouse).count()
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


# ── Prayer Requests ──────────────────────────────────────


@router.post("/prayer-requests/public", response_model=dict, status_code=201)
def create_public_prayer_request(
    payload: schemas.PrayerRequestPublicCreate,
    db: Session = Depends(get_db),
):
    """Pedido de oracion desde pagina web publica (sin auth).
    Crea PrayerRequest + Member + ConsolidationCase para que el equipo de
    consolidacion pueda contactar para orar. Source='prayer-web'."""
    # Extract name parts
    name_parts = payload.requester_name.strip().split(" ", 1)
    first_name = name_parts[0] if name_parts else payload.requester_name
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    # Create Member + ConsolidationCase via ContactTracker
    result = tracker.record_contact(db, ContactRecord(
        email=payload.email,
        phone=payload.phone,
        first_name=first_name,
        last_name=last_name,
        source="prayer-web",
        landing_page=payload.landing_page,
        campaign=payload.campaign,
        notes=payload.request_text[:200],  # Truncate for notes
    ))

    # Create PrayerRequest linked to the member
    prayer = models.PrayerRequest(
        requester_name=payload.requester_name,
        request_text=payload.request_text,
        category=payload.category,
        is_public=False,
        source="prayer-web",
        status="pending",
    )
    db.add(prayer)
    db.commit()
    db.refresh(prayer)

    return {
        "id": prayer.id,
        "requester_name": prayer.requester_name,
        "request_text": prayer.request_text,
        "category": prayer.category,
        "status": prayer.status,
        "source": prayer.source,
        "member_id": result.member.id if result.member else None,
        "case_id": result.case.id if result.case else None,
    }


@router.get("/prayer-requests", response_model=List[dict])
def list_prayer_requests(
    source: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Lista pedidos de oracion. Opcionalmente filtra por source (web, crm)."""
    q = db.query(models.PrayerRequest).order_by(models.PrayerRequest.created_at.desc())
    if source:
        q = q.filter(models.PrayerRequest.source == source)
    prayers = q.all()
    return [
        {
            "id": p.id,
            "requester_name": p.requester_name,
            "request_text": p.request_text,
            "category": p.category,
            "status": p.status,
            "source": p.source,
            "is_public": p.is_public,
            "created_at": str(p.created_at) if p.created_at else None,
        }
        for p in prayers
    ]


@router.post("/prayer-requests", response_model=dict, status_code=201)
def create_prayer_request(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Crea un pedido de oracion desde el CRM (staff/pastor)."""
    prayer = models.PrayerRequest(
        requester_name=payload.get("requester_name", current_user.username),
        request_text=payload.get("request_text", ""),
        category=payload.get("category", "General"),
        is_public=payload.get("is_public", False),
        source=payload.get("source", "crm"),
        status="active",
    )
    db.add(prayer)
    db.commit()
    db.refresh(prayer)
    return {
        "id": prayer.id,
        "requester_name": prayer.requester_name,
        "request_text": prayer.request_text,
        "category": prayer.category,
        "status": prayer.status,
        "source": prayer.source,
        "is_public": prayer.is_public,
    }


@router.patch("/prayer-requests/{request_id}", response_model=dict)
def update_prayer_request(
    request_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    prayer = (
        db.query(models.PrayerRequest)
        .filter(models.PrayerRequest.id == request_id)
        .first()
    )
    if not prayer:
        raise HTTPException(status_code=404, detail="Prayer request not found")
    for field in ("status", "category", "request_text", "requester_name", "source"):
        if field in payload:
            setattr(prayer, field, payload[field])
    db.commit()
    db.refresh(prayer)
    return {
        "id": prayer.id,
        "requester_name": prayer.requester_name,
        "request_text": prayer.request_text,
        "category": prayer.category,
        "status": prayer.status,
        "source": prayer.source,
        "is_public": prayer.is_public,
    }


@router.post("/volunteers", response_model=dict, status_code=201)
def create_volunteer(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Registra un nuevo servidor/voluntario."""
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    member_id = payload.get("member_id")
    if not member_id:
        # Create a minimal member record for standalone volunteers
        parts = name.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""
        member = models.Member(
            first_name=first_name,
            last_name=last_name,
            church_role=payload.get("role") or "volunteer",
            status="active",
        )
        db.add(member)
        db.flush()
        member_id = member.id

    shift_start = None
    shift_end = None
    if payload.get("shift_start"):
        try:
            shift_start = datetime.fromisoformat(
                str(payload["shift_start"]).replace("Z", "+00:00")
            )
        except ValueError:
            pass
    if payload.get("shift_end"):
        try:
            shift_end = datetime.fromisoformat(
                str(payload["shift_end"]).replace("Z", "+00:00")
            )
        except ValueError:
            pass

    shift = models.VolunteerShift(
        member_id=member_id,
        team_name=payload.get("team"),
        ministry=payload.get("role"),
        shift_start=shift_start,
        shift_end=shift_end,
        notes=payload.get("notes"),
        status="active",
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return {
        "id": shift.id,
        "member_id": member_id,
        "name": name,
        "team": shift.team_name,
        "status": shift.status,
    }


@router.get("/volunteers", response_model=List[dict])
def list_volunteers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Lista todos los voluntarios con sus horas y ministerios."""
    members = db.query(models.Member).all()
    result = []
    for member in members:
        shifts = (
            db.query(models.VolunteerShift)
            .filter(models.VolunteerShift.member_id == member.id)
            .all()
        )
        total_hours = 0
        for shift in shifts:
            if shift.shift_start and shift.shift_end:
                total_hours += int(
                    (shift.shift_end - shift.shift_start).total_seconds() // 3600
                )
        result.append(
            {
                "id": member.id,
                "name": f"{member.first_name} {member.last_name}",
                "total_hours": total_hours,
                "ministry_count": len(set(s.ministry for s in shifts if s.ministry)),
            }
        )
    return result


@router.get("/volunteers/{member_id}", response_model=dict)
def get_volunteer_detail(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Volunteer not found")
    shifts = (
        db.query(models.VolunteerShift)
        .filter(models.VolunteerShift.member_id == member_id)
        .order_by(models.VolunteerShift.shift_start.desc())
        .all()
    )
    latest_shift = shifts[0] if shifts else None
    total_hours = 0
    for shift in shifts:
        if shift.shift_start and shift.shift_end:
            total_hours += int(
                (shift.shift_end - shift.shift_start).total_seconds() // 3600
            )
    skills = sorted(
        row.name
        for row in (
            db.query(models.VolunteerSkill)
            .join(
                models.member_volunteer_skills,
                models.member_volunteer_skills.c.skill_id == models.VolunteerSkill.id,
            )
            .filter(models.member_volunteer_skills.c.member_id == member_id)
            .all()
        )
        if row.name
    )
    return {
        "id": member.id,
        "name": _member_full_name(member),
        "role": member.church_role,
        "team": latest_shift.team_name if latest_shift else None,
        "status": latest_shift.status if latest_shift else "inactive",
        "joined_date": (
            latest_shift.shift_start.isoformat()
            if latest_shift and latest_shift.shift_start
            else None
        ),
        "total_hours": total_hours,
        "skills": skills,
    }


@router.patch("/volunteers/{member_id}", response_model=dict)
def update_volunteer(
    member_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Volunteer not found")
    allowed = {"church_role", "first_name", "last_name", "phone", "email"}
    for k, v in payload.items():
        if k in allowed:
            setattr(member, k, v)
    db.commit()
    db.refresh(member)
    return {
        "id": member.id,
        "name": _member_full_name(member),
        "role": member.church_role,
    }


@router.delete("/volunteers/{member_id}", status_code=204)
def delete_volunteer(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Volunteer not found")
    db.query(models.VolunteerShift).filter(
        models.VolunteerShift.member_id == member_id
    ).delete()
    db.delete(member)
    db.commit()


@router.get("/groups", response_model=List[dict])
def list_crm_groups(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Lista grupos/ministerios para vistas comunitarias."""
    ministries = db.query(models.Ministry).all()
    return [
        {
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "leader": m.leader_name,
            "members_count": len(m.members) if m.members else 0,
        }
        for m in ministries
    ]


@router.get("/radar", response_model=dict)
def get_crm_radar(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Datos del radar ministerial para dashboard."""
    total_members = db.query(models.Member).count()
    total_ministries = db.query(models.Ministry).count()
    active_cases = (
        db.query(models.ConsolidationCase)
        .filter(models.ConsolidationCase.status == "active")
        .count()
    )
    pending_tasks = (
        db.query(models.CrmTask).filter(models.CrmTask.status == "pending").count()
    )
    return {
        "total_members": total_members,
        "total_ministries": total_ministries,
        "active_cases": active_cases,
        "pending_tasks": pending_tasks,
    }


# ---------------------------------------------------------------------------
# Task 3.2: Newsletter Leads Dashboard
# ---------------------------------------------------------------------------

@router.get("/leads/newsletter", response_model=dict)
def get_newsletter_leads(
    source: Optional[str] = None,
    stage: Optional[str] = None,
    landing_page: Optional[str] = None,
    campaign: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """
    CRM view para ver todos los leads originados desde suscripción al newsletter.
    Permite filtrar por source, stage, landing_page, campaign y rango de fechas.
    """
    query = (
        db.query(models.ConsolidationCase)
        .join(models.Member, models.ConsolidationCase.member_id == models.Member.id)
        .filter(
            models.ConsolidationCase.source.like("%newsletter%"),
            models.ConsolidationCase.status == "active",
        )
    )

    if source:
        query = query.filter(models.ConsolidationCase.source == source)
    if stage:
        query = query.filter(models.ConsolidationCase.stage == stage)
    if landing_page:
        query = query.filter(models.ConsolidationCase.notes.like(f"%Landing: {landing_page}%"))
    if campaign:
        query = query.filter(models.ConsolidationCase.notes.like(f"%Campaign: {campaign}%"))
    if date_from:
        query = query.filter(models.ConsolidationCase.created_at >= date_from)
    if date_to:
        query = query.filter(models.ConsolidationCase.created_at <= date_to)

    total = query.count()
    cases = (
        query.order_by(models.ConsolidationCase.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    leads = []
    for case in cases:
        member = case.member
        leads.append({
            "case_id": case.id,
            "member_id": member.id if member else None,
            "first_name": member.first_name if member else "",
            "last_name": member.last_name if member else "",
            "email": member.email if member else None,
            "phone": member.phone if member else None,
            "source": case.source,
            "stage": case.stage,
            "notes": case.notes,
            "created_at": case.created_at.isoformat() if case.created_at else None,
        })

    return {
        "leads": leads,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
    }


@router.get("/leads/export-newsletter", response_model=dict)
def export_newsletter_leads_csv(
    source: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """
    Exporta leads de newsletter como lista de dicts (para generar CSV en frontend).
    """
    query = (
        db.query(models.ConsolidationCase)
        .join(models.Member, models.ConsolidationCase.member_id == models.Member.id)
        .filter(
            models.ConsolidationCase.source.like("%newsletter%"),
            models.ConsolidationCase.status == "active",
        )
    )

    if source:
        query = query.filter(models.ConsolidationCase.source == source)
    if date_from:
        query = query.filter(models.ConsolidationCase.created_at >= date_from)
    if date_to:
        query = query.filter(models.ConsolidationCase.created_at <= date_to)

    cases = query.order_by(models.ConsolidationCase.created_at.desc()).all()

    rows = []
    for case in cases:
        member = case.member
        rows.append({
            "first_name": member.first_name if member else "",
            "last_name": member.last_name if member else "",
            "email": member.email if member else "",
            "phone": member.phone if member else "",
            "source": case.source,
            "stage": case.stage,
            "notes": case.notes or "",
            "created_at": str(case.created_at) if case.created_at else "",
        })

    return {"rows": rows, "count": len(rows)}
