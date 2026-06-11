import collections
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.crm._shared import (
    _persona_full_name,
    _serialize_case,
    _serialize_message_group,
    _serialize_task,
    utc_now,
)
from backend.auth import normalize_role, require_module_access
from backend.core.database import get_db
from backend.crud.crm import (
    get_user_sede_id,
    legacy_user_id_from_identity,
    resolve_persona_id_for_user,
    resolve_persona_id_from_identity,
)
from backend.services.messaging import MessagingGateway, get_messaging_gateway
from backend.services.messaging import StubMessagingGateway  # noqa: F401 — disponible para override manual en tests
from backend.services.public_contact_tracking import ContactRecord, tracker

router = APIRouter(tags=["CRM"])
logger = logging.getLogger(__name__)


def _get_user_role(user: models.User) -> str:
    role = normalize_role(str(getattr(user, "role", "")))
    if not role and hasattr(user, "rol_plataforma") and user.rol_plataforma:
        role = normalize_role(user.rol_plataforma.nombre)
    return role


def _get_case_or_404(db: Session, case_id: str, user_sede: Optional[int]):
    case_uuid = uuid.UUID(case_id) if isinstance(case_id, str) else case_id
    case = (
        db.query(models.ConsolidationCase)
        .filter(
            models.ConsolidationCase.id == case_uuid,
            models.ConsolidationCase.deleted_at.is_(None),
        )
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if user_sede and case.sede_id != user_sede:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def _get_persona_or_404(db: Session, persona_ref: str, user_sede: Optional[int] = None):
    """Resolve canonical UUID persona refs, with legacy user_id fallback."""
    try:
        persona_uuid = uuid.UUID(str(persona_ref))
        persona = db.query(models.Persona).filter(models.Persona.id == persona_uuid).first()
    except (TypeError, ValueError):
        from backend.crud.crm import resolve_persona_id_for_user
        persona_id = resolve_persona_id_for_user(db, persona_ref)
        persona = (
            db.query(models.Persona).filter(models.Persona.id == persona_id).first()
            if persona_id
            else None
        )

    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    if user_sede and persona.sede_id and str(persona.sede_id) != str(user_sede):
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


# ═══════════════════════════════════════════════════════════════════
# REDIRECTS: Old consolidation endpoints → new CRM Core
# ═══════════════════════════════════════════════════════════════════


@router.get("/consolidation/cases/{case_id}", response_model=dict)
def get_consolidation_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    case = _get_case_or_404(db, case_id, user_sede)
    return _serialize_case(case)


@router.post("/consolidation/cases", response_model=dict)
def create_consolidation_case(
    payload: schemas.CasoCRMCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    p_uuid = uuid.UUID(payload.persona_id) if isinstance(payload.persona_id, str) else payload.persona_id
    persona = db.query(models.Persona).filter(models.Persona.id == p_uuid).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    data = payload.model_dump()
    data["persona_id"] = p_uuid
    if data.get("assigned_pastor_id"):
        data["assigned_pastor_id"] = uuid.UUID(str(data["assigned_pastor_id"]))
    if data.get("assigned_leader_id"):
        data["assigned_leader_id"] = uuid.UUID(str(data["assigned_leader_id"]))
    row = models.ConsolidationCase(**data)
    row.sede_id = persona.sede_id
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_case(row)


@router.patch("/consolidation/cases/{case_id}", response_model=dict)
def update_consolidation_case(
    case_id: str,
    payload: schemas.CasoCRMUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    case = _get_case_or_404(db, case_id, user_sede)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key in ("assigned_pastor_id", "assigned_leader_id") and value is not None:
            value = uuid.UUID(str(value))
        setattr(case, key, value)
    db.commit()
    db.refresh(case)
    return _serialize_case(case)


@router.post("/consolidation/cases/{case_id}/assignments", response_model=dict)
def create_consolidation_assignment(
    case_id: str,
    payload: schemas.ConsolidationAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    case = _get_case_or_404(db, case_id, user_sede)
    assignment_data = payload.model_dump(exclude={"case_id"})
    if assignment_data.get("assigned_by_id"):
        assignment_data["assigned_by_id"] = uuid.UUID(str(assignment_data["assigned_by_id"]))
    if assignment_data.get("assigned_to_id"):
        assignment_data["assigned_to_id"] = uuid.UUID(str(assignment_data["assigned_to_id"]))
    case_uuid = uuid.UUID(case_id) if isinstance(case_id, str) else case_id
    row = models.ConsolidationAssignment(**assignment_data, case_id=case_uuid)
    db.add(row)
    case.assigned_pastor_id = assignment_data["assigned_by_id"]
    case.assigned_leader_id = assignment_data["assigned_to_id"]
    case.updated_at = utc_now()
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "case_id": str(row.case_id),
        "assigned_by_id": str(row.assigned_by_id),
        "assigned_to_id": str(row.assigned_to_id),
        "status": row.status,
        "priority": row.priority,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.post("/consolidation/cases/{case_id}/interactions", response_model=dict)
def create_consolidation_interaction(
    case_id: str,
    payload: schemas.ConsolidationInteractionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    case = _get_case_or_404(db, case_id, user_sede)
    interaction_data = payload.model_dump(exclude={"case_id"})
    if interaction_data.get("performed_by_id"):
        interaction_data["performed_by_id"] = uuid.UUID(str(interaction_data["performed_by_id"]))
    case_uuid = uuid.UUID(case_id) if isinstance(case_id, str) else case_id
    row = models.ConsolidationInteraction(**interaction_data, case_id=case_uuid)
    db.add(row)
    case.last_contact_at = row.interaction_date
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "case_id": str(row.case_id),
        "performed_by_id": str(row.performed_by_id),
        "interaction_type": row.interaction_type,
        "interaction_date": (row.interaction_date.isoformat() if row.interaction_date else None),
        "result": row.result,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.post("/consolidation/cases/{case_id}/tasks", response_model=dict)
def create_consolidation_task(
    case_id: str,
    payload: schemas.ConsolidationTaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    _get_case_or_404(db, case_id, user_sede)
    task_data = payload.model_dump(exclude={"case_id"})
    case_uuid = uuid.UUID(case_id) if isinstance(case_id, str) else case_id
    row = models.ConsolidationTask(**task_data, case_id=case_uuid)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "case_id": str(row.case_id),
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
    persona_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Lista casos de consolidación con paginación y filtros."""
    user_sede = get_user_sede_id(db, current_user.id)
    q = db.query(models.CasoCRM).filter(models.CasoCRM.deleted_at.is_(None))
    if user_sede:
        q = q.filter(models.CasoCRM.sede_id == user_sede)

    if source:
        q = q.filter(models.CasoCRM.origen_canal == source)
    if stage:
        q = q.filter(models.CasoCRM.estado == stage)
    if status:
        q = q.filter(models.CasoCRM.estado == status)
    if persona_id:
        q = q.filter(models.CasoCRM.persona_id == persona_id)

    total = q.count()
    cases = q.order_by(models.CasoCRM.fecha_creacion.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "cases": [_serialize_case(c) for c in cases],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
    }


@router.delete("/consolidation/cases/{case_id}", status_code=204)
def delete_consolidation_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Archiva un caso de consolidación (soft delete)."""
    user_sede = get_user_sede_id(db, current_user.id)
    case = _get_case_or_404(db, case_id, user_sede)
    case.deleted_at = utc_now()
    db.commit()
    return None


@router.get("/consolidation/cases/{case_id}/tasks", response_model=List[dict])
def list_consolidation_tasks(
    case_id: str,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Lista las tareas de seguimiento de un caso."""
    user_sede = get_user_sede_id(db, current_user.id)
    _get_case_or_404(db, case_id, user_sede)

    q = db.query(models.ConsolidationTask).filter(models.ConsolidationTask.case_id == case_id)
    if status_filter:
        q = q.filter(models.ConsolidationTask.status == status_filter)

    tasks = q.order_by(models.ConsolidationTask.created_at.desc()).all()
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
    case_id: str,
    task_id: str,
    payload: schemas.ConsolidationTaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Actualiza una tarea de seguimiento (ej. marcar como completada)."""
    user_sede = get_user_sede_id(db, current_user.id)
    _get_case_or_404(db, case_id, user_sede)
    task = (
        db.query(models.ConsolidationTask)
        .filter(
            models.ConsolidationTask.id == task_id,
            models.ConsolidationTask.case_id == case_id,
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
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Lista las interacciones de un caso de consolidación."""
    user_sede = get_user_sede_id(db, current_user.id)
    _get_case_or_404(db, case_id, user_sede)

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
            "performed_by_id": i.performed_by_id,
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
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Actualiza una asignación de consolidación."""
    assignment = (
        db.query(models.ConsolidationAssignment).filter(models.ConsolidationAssignment.id == assignment_id).first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    user_sede = get_user_sede_id(db, current_user.id)
    _get_case_or_404(db, str(assignment.case_id), user_sede)

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(assignment, key, value)
    db.commit()
    db.refresh(assignment)
    return {
        "id": assignment.id,
        "case_id": assignment.case_id,
        "assigned_by_id": assignment.assigned_by_id,
        "assigned_to_id": assignment.assigned_to_id,
        "status": assignment.status,
        "priority": assignment.priority,
        "end_date": assignment.end_date.isoformat() if assignment.end_date else None,
        "created_at": assignment.created_at.isoformat() if assignment.created_at else None,
    }


@router.post("/messaging/send", response_model=dict)
async def send_crm_message(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
    gateway: MessagingGateway = Depends(get_messaging_gateway),
):
    channel = str(payload.get("channel") or "").strip().lower()
    content = str(payload.get("content") or "").strip()
    if not channel or not content:
        raise HTTPException(status_code=400, detail="channel and content are required")

    campaign_name = payload.get("campaign_name") or payload.get("name")
    persona_id = payload.get("persona_id")
    target_segments = payload.get("target_segments") or []

    user_sede = get_user_sede_id(db, current_user.id)

    if persona_id:
        target_members = [{"id": persona_id}]
    else:
        persona_map: dict[str, models.Persona] = {}
        for segment in target_segments:
            normalized = str(segment).strip().lower()
            if normalized == "active":
                q = db.query(models.Persona).filter(models.Persona.church_role == "Miembro")
                if user_sede:
                    q = q.filter(models.Persona.sede_id == user_sede)
                if channel in {"whatsapp", "sms"}:
                    q = q.filter(models.Persona.phone.isnot(None), models.Persona.phone != "")
                elif channel == "email":
                    q = q.filter(models.Persona.email.isnot(None), models.Persona.email != "")
                rows = q.all()
            elif normalized == "groups":
                q = db.query(models.Persona).filter(models.Persona.family_id.isnot(None))
                if user_sede:
                    q = q.filter(models.Persona.sede_id == user_sede)
                if channel in {"whatsapp", "sms"}:
                    q = q.filter(models.Persona.phone.isnot(None), models.Persona.phone != "")
                elif channel == "email":
                    q = q.filter(models.Persona.email.isnot(None), models.Persona.email != "")
                rows = q.all()
            else:
                rows = []
            for persona in rows:
                persona_map[str(persona.id)] = persona
        target_members = list(persona_map.values())

    if not target_members:
        raise HTTPException(status_code=404, detail="No target members found")

    external_id = f"CMP-{uuid.uuid4().hex[:12]}" if len(target_members) > 1 else None
    delivered_count = 0
    failed_count = 0
    log_ids: list[int] = []

    for persona in target_members:
        persona_id_value = persona["id"] if isinstance(persona, dict) else persona.id
        try:
            if channel == "whatsapp":
                log = await gateway.send_whatsapp(
                    db,
                    persona_id_value,
                    content,
                    current_user.id,
                    campaign_name=campaign_name,
                    external_id=external_id,
                )
            elif channel == "sms":
                log = await gateway.send_sms(
                    db,
                    persona_id_value,
                    content,
                    current_user.id,
                    campaign_name=campaign_name,
                    external_id=external_id,
                )
            elif channel == "email":
                log = await gateway.send_email(
                    db,
                    persona_id_value,
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
                raise HTTPException(status_code=502, detail="No se pudo enviar el mensaje")

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
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    q = db.query(models.CommunicationLog).join(models.Persona, models.CommunicationLog.persona_id == models.Persona.id)
    if user_sede:
        q = q.filter(models.Persona.sede_id == user_sede)
    logs = q.order_by(models.CommunicationLog.created_at.desc()).all()
    grouped: "collections.OrderedDict[str, list[models.CommunicationLog]]" = collections.OrderedDict()
    for log in logs:
        key = log.external_id or f"log-{log.id}"
        grouped.setdefault(key, []).append(log)
    return [_serialize_message_group(items) for items in grouped.values()]


@router.get("/messaging/history/{log_id}", response_model=dict)
def get_messaging_history_item(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    log = db.query(models.CommunicationLog).filter(models.CommunicationLog.id == log_id).first()
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
    assignee_user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Lista todas las tareas CRM con filtro opcional por usuario asignado."""
    q = db.query(models.CrmTask)
    if assignee_user_id:
        assignee_persona_id = resolve_persona_id_for_user(db, assignee_user_id)
        if assignee_persona_id:
            q = q.filter(models.CrmTask.assignee_id == assignee_persona_id)
        else:
            return []
    tasks = q.order_by(models.CrmTask.created_at.desc()).all()
    return [_serialize_task(t) for t in tasks]


@router.post("/tasks/", response_model=dict)
def create_crm_task(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
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
            raise HTTPException(status_code=400, detail="Formato de fecha o identificador invalido")

    assignee_identity = payload.get("assignee_id") or current_user.id
    task = models.CrmTask(
        title=title,
        description=payload.get("description"),
        category=payload.get("category") or "Pastoral",
        persona_id=payload.get("persona_id"),
        assignee_id=resolve_persona_id_from_identity(db, assignee_identity),
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
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    my_persona_id = resolve_persona_id_for_user(db, current_user.id)
    if not my_persona_id:
        return []
    tasks = (
        db.query(models.CrmTask)
        .filter(models.CrmTask.assignee_id == my_persona_id)
        .order_by(models.CrmTask.created_at.desc())
        .all()
    )
    return [_serialize_task(task) for task in tasks]


@router.get("/tasks/{task_id}", response_model=dict)
def get_crm_task_detail(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    task = db.query(models.CrmTask).filter(models.CrmTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    is_staff = _get_user_role(current_user) in {"admin", "administrador", "pastor", "coordinador"}
    my_persona_id = resolve_persona_id_for_user(db, getattr(current_user, "id", None))
    is_persona_owner = task.assignee_id is not None and task.assignee_id == my_persona_id
    if not is_staff and not is_persona_owner:
        raise HTTPException(status_code=403, detail="No autorizado para ver esta tarea")
    return _serialize_task(task)


@router.patch("/tasks/{task_id}", response_model=dict)
def update_crm_task(
    task_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
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
        "persona_id",
    ):
        if field in payload:
            val = payload[field]
            if field == "due_date" and isinstance(val, str):
                try:
                    val = datetime.fromisoformat(val.replace("Z", "+00:00"))
                except ValueError:
                    raise HTTPException(status_code=400, detail="Formato de fecha inválido")
            if field == "assignee_id":
                task.assignee_id = resolve_persona_id_from_identity(db, val)
            else:
                setattr(task, field, val)
    db.commit()
    db.refresh(task)
    return _serialize_task(task)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_crm_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Elimina una tarea del CRM."""
    task = db.query(models.CrmTask).filter(models.CrmTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.deleted_at = utc_now()
    db.commit()
    return None


@router.get("/counseling/{ticket_id}", response_model=dict)
def get_counseling_detail(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    ticket = db.query(models.CounselingTicket).filter(models.CounselingTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Counseling ticket not found")
    history_rows = (
        db.query(models.CounselingTicket)
        .filter(models.CounselingTicket.persona_id == ticket.persona_id)
        .order_by(models.CounselingTicket.created_at.desc(), models.CounselingTicket.id.desc())
        .all()
    )
    return {
        "id": ticket.id,
        "persona_id": ticket.persona_id,
        "member_name": _persona_full_name(ticket.persona),
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


@router.get("/grupos/{grupo_id}", response_model=dict)
def get_grupo_detail(
    grupo_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    grupo = db.query(models.GrupoEvangelismo).filter(models.GrupoEvangelismo.id == grupo_id).first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    return {
        "id": grupo.id,
        "code": grupo.codigo,
        "name": grupo.nombre,
        "zone": grupo.ubicacion,
        "address": grupo.direccion,
        "lider_id": grupo.lider_persona_id,
        "asistente_id": grupo.asistente_persona_id,
        "anfitrion_id": grupo.anfitrion_persona_id,
        "day_of_week": grupo.dia_reunion,
        "start_time": grupo.hora_reunion,
        "end_time": None,
        "leader_name": None,
        "capacity": grupo.capacidad,
        "status": "active" if grupo.activo else "inactive",
        "participante_ids": [row.persona_id for row in (grupo.participantes or [])],
        "participantes": [
            {
                "persona_id": row.persona_id,
                "role": row.rol_base,
            }
            for row in (grupo.participantes or [])
        ],
    }


@router.get("/grupos", response_model=List[dict])
def list_grupos(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    q = db.query(models.GrupoEvangelismo)
    if user_sede:
        q = q.filter(models.GrupoEvangelismo.sede_id == user_sede)
    grupos = q.order_by(models.GrupoEvangelismo.nombre.asc()).all()
    return [
        {
            "id": g.id,
            "code": g.codigo,
            "name": g.nombre,
            "zone": g.ubicacion,
            "address": g.direccion,
            "leader_name": None,
            "capacity": g.capacidad,
            "status": "active" if g.activo else "inactive",
        }
        for g in grupos
    ]


@router.put("/grupos/{grupo_id}", response_model=dict)
def update_grupo(
    grupo_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    grupo = db.query(models.GrupoEvangelismo).filter(models.GrupoEvangelismo.id == grupo_id).first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")

    field_map = {
        "code": "codigo",
        "name": "nombre",
        "zone": "ubicacion",
        "address": "direccion",
        "leader_id": "lider_persona_id",
        "assistant_id": "asistente_persona_id",
        "host_id": "anfitrion_persona_id",
        "capacity": "capacidad",
        "day_of_week": "dia_reunion",
        "start_time": "hora_reunion",
    }
    for payload_key, model_attr in field_map.items():
        if payload_key in payload:
            setattr(grupo, model_attr, payload[payload_key])

    if "status" in payload:
        raw = str(payload["status"]).strip().lower()
        grupo.activo = raw in ("active", "activo", "true", "1")

    if "participante_ids" in payload and isinstance(payload["participante_ids"], list):
        normalized_ids = []
        for raw_id in payload["participante_ids"]:
            try:
                normalized_ids.append(uuid.UUID(raw_id))
            except (TypeError, ValueError):
                continue
        normalized_ids = list(dict.fromkeys(normalized_ids))
        current_rows = db.query(models.ParticipanteGrupo).filter(models.ParticipanteGrupo.grupo_id == grupo.id).all()
        current_by_persona = {row.persona_id: row for row in current_rows}
        incoming_ids = set(normalized_ids)

        for row in current_rows:
            if row.persona_id not in incoming_ids:
                row.deleted_at = utc_now()
        for persona_id in normalized_ids:
            if persona_id in current_by_persona:
                continue
            db.add(
                models.ParticipanteGrupo(
                    grupo_id=grupo.id,
                    persona_id=persona_id,
                    rol_base="asistente",
                )
            )

    db.commit()
    db.refresh(grupo)

    return {
        "id": grupo.id,
        "code": grupo.codigo,
        "name": grupo.nombre,
        "zone": grupo.ubicacion,
        "address": grupo.direccion,
        "lider_id": grupo.lider_persona_id,
        "asistente_id": grupo.asistente_persona_id,
        "anfitrion_id": grupo.anfitrion_persona_id,
        "capacity": grupo.capacidad,
        "day_of_week": grupo.dia_reunion,
        "start_time": grupo.hora_reunion,
        "end_time": None,
        "status": "active" if grupo.activo else "inactive",
        "participante_ids": [row.persona_id for row in (grupo.participantes or [])],
        "participantes": [{"persona_id": row.persona_id, "role": row.rol_base} for row in (grupo.participantes or [])],
    }


@router.get("/prayer-requests/{request_id}", response_model=dict)
def get_prayer_request_detail(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    prayer = db.query(models.PrayerRequest).filter(models.PrayerRequest.id == request_id).first()
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
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    tickets = crud.get_counseling_tickets(db, status=status, sede_id=user_sede)
    return [
        {
            "id": t.id,
            "persona_id": t.persona_id,
            "member_name": _persona_full_name(t.persona) if t.persona else "",
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
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    ticket = crud.create_counseling_ticket(db, payload)
    return {
        "id": ticket.id,
        "persona_id": ticket.persona_id,
        "member_name": _persona_full_name(ticket.persona) if ticket.persona else "",
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
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    tickets = (
        db.query(models.CounselingTicket)
        .filter(models.CounselingTicket.persona_id == lead_id)
        .order_by(models.CounselingTicket.created_at.desc())
        .all()
    )
    return [
        {
            "id": t.id,
            "persona_id": t.persona_id,
            "member_name": _persona_full_name(t.persona) if t.persona else "",
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
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    ticket = db.query(models.CounselingTicket).filter(models.CounselingTicket.id == ticket_id).first()
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
        "persona_id": ticket.persona_id,
        "member_name": _persona_full_name(ticket.persona) if ticket.persona else "",
        "topic": ticket.subject,
        "status": ticket.status,
        "notes": ticket.notes,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
    }


# ── Settings ─────────────────────────────────────────────


@router.get("/settings", response_model=dict)
def get_crm_settings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
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
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    import json

    crud.update_page_content(
        db,
        "crm_settings",
        schemas.PageContentUpdate(title="CRM Settings", content=json.dumps(payload, ensure_ascii=False)),
    )
    return payload


@router.get("/roles", response_model=List[dict])
def list_crm_roles(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    rows = (
        db.query(models.RoleDefinition)
        .order_by(models.RoleDefinition.is_leadership.desc(), models.RoleDefinition.name.asc())
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
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    name = str(payload.get("name") or "").strip()
    color = str(payload.get("color") or "").strip()
    if not name or not color:
        raise HTTPException(status_code=400, detail="name and color are required")
    exists = db.query(models.RoleDefinition).filter(models.RoleDefinition.name == name).first()
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
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    row = db.query(models.RoleDefinition).filter(models.RoleDefinition.id == role_id).first()
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
            raise HTTPException(status_code=400, detail="Ya existe otro rol con ese nombre")
        db.query(models.Persona).filter(models.Persona.church_role == row.name).update({"church_role": new_name})
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
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    if fallback_id == role_id:
        raise HTTPException(
            status_code=400,
            detail="El rol de reemplazo no puede ser el mismo rol a eliminar",
        )
    role = db.query(models.RoleDefinition).filter(models.RoleDefinition.id == role_id).first()
    fallback = db.query(models.RoleDefinition).filter(models.RoleDefinition.id == fallback_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Rol a eliminar no encontrado")
    if not fallback:
        raise HTTPException(status_code=400, detail="Rol de reemplazo no valido")
    db.query(models.Persona).filter(models.Persona.church_role == role.name).update({"church_role": fallback.name})
    role.deleted_at = utc_now()
    db.commit()
    return {
        "success": True,
        "message": "Rol eliminado y miembros reasignados correctamente",
    }


@router.get("/analytics", response_model=dict)
def get_crm_analytics_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    user_sede = get_user_sede_id(db, current_user.id)

    persona_q = db.query(models.Persona)
    if user_sede:
        persona_q = persona_q.filter(models.Persona.sede_id == user_sede)

    total_members = persona_q.count()
    active_members = persona_q.filter(
        models.Persona.spiritual_status.in_(["Activo", "active", "Miembro Activo"])
    ).count()

    counseling_q = db.query(models.CounselingTicket).filter(
        models.CounselingTicket.status == "open",
        models.CounselingTicket.deleted_at.is_(None),
    )
    if user_sede:
        counseling_q = counseling_q.join(
            models.Persona, models.CounselingTicket.persona_id == models.Persona.id
        ).filter(models.Persona.sede_id == user_sede)
    open_counseling = counseling_q.count()

    month_start = (
        datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    )
    events_q = db.query(models.CrmEvent).filter(models.CrmEvent.event_date >= month_start)
    if user_sede:
        events_q = events_q.filter(models.CrmEvent.sede_id == user_sede)
    events_this_month = events_q.count()

    groups_q = db.query(models.GrupoEvangelismo)
    if user_sede:
        groups_q = groups_q.filter(models.GrupoEvangelismo.sede_id == user_sede)
    total_groups = groups_q.count()

    total_families = db.query(models.Family).count()
    return {
        "total_members": total_members,
        "active_members": active_members,
        "open_counseling": open_counseling,
        "events_this_month": events_this_month,
        "total_groups": total_groups,
        "total_families": total_families,
        "total_leads": 0,
        "pipeline_by_stage": {},
    }


# ── Prayer Requests ──────────────────────────────────────


@router.post("/prayer-requests/public", response_model=dict, status_code=201)
def create_public_prayer_request(
    payload: schemas.PrayerRequestPublicCreate,
    db: Session = Depends(get_db),
):
    """Pedido de oracion desde pagina web publica (sin auth).
    Crea PrayerRequest + Persona + ConsolidationCase para que el equipo de
    consolidacion pueda contactar para orar. Source='prayer-web'."""
    # Extract name parts
    name_parts = payload.requester_name.strip().split(" ", 1)
    first_name = name_parts[0] if name_parts else payload.requester_name
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    # Create Persona + ConsolidationCase via ContactTracker
    result = tracker.record_contact(
        db,
        ContactRecord(
            email=payload.email,
            phone=payload.phone,
            first_name=first_name,
            last_name=last_name,
            source="prayer-web",
            landing_page=payload.landing_page,
            campaign=payload.campaign,
            notes=payload.request_text[:200],  # Truncate for notes
        ),
    )

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
        "persona_id": result.persona.id if result.persona else None,
        "case_id": result.case.id if result.case else None,
    }


@router.get("/prayer-requests", response_model=List[dict])
def list_prayer_requests(
    source: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
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
    current_user: models.User = Depends(require_module_access("crm", "edit")),
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
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    prayer = db.query(models.PrayerRequest).filter(models.PrayerRequest.id == request_id).first()
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
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Registra un nuevo servidor/voluntario."""
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    persona_id = payload.get("persona_id")
    if not persona_id:
        # Create a minimal persona record for standalone volunteers
        parts = name.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""
        persona = models.Persona(
            first_name=first_name,
            last_name=last_name,
            church_role=payload.get("role") or "volunteer",
            status="active",
        )
        db.add(persona)
        db.flush()
        persona_id = persona.id

    shift_start = None
    shift_end = None
    if payload.get("shift_start"):
        try:
            shift_start = datetime.fromisoformat(str(payload["shift_start"]).replace("Z", "+00:00"))
        except ValueError:
            pass
    if payload.get("shift_end"):
        try:
            shift_end = datetime.fromisoformat(str(payload["shift_end"]).replace("Z", "+00:00"))
        except ValueError:
            pass

    shift = models.VolunteerShift(
        persona_id=persona_id,
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
        "persona_id": persona_id,
        "name": name,
        "team": shift.team_name,
        "status": shift.status,
    }


@router.get("/volunteers", response_model=List[dict])
def list_volunteers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Lista todos los voluntarios con sus horas y ministerios."""
    from collections import defaultdict

    user_sede = get_user_sede_id(db, current_user.id)
    personas_q = db.query(models.Persona)
    if user_sede:
        personas_q = personas_q.filter(models.Persona.sede_id == user_sede)
    personas = personas_q.all()
    if not personas:
        return []

    persona_ids = [p.id for p in personas]
    all_shifts = db.query(models.VolunteerShift).filter(models.VolunteerShift.persona_id.in_(persona_ids)).all()
    shifts_by_persona: dict = defaultdict(list)
    for s in all_shifts:
        shifts_by_persona[s.persona_id].append(s)

    result = []
    for persona in personas:
        shifts = shifts_by_persona[persona.id]
        total_hours = sum(
            int((s.shift_end - s.shift_start).total_seconds() // 3600) for s in shifts if s.shift_start and s.shift_end
        )
        result.append(
            {
                "id": persona.id,
                "name": f"{persona.first_name} {persona.last_name}",
                "total_hours": total_hours,
                "ministry_count": len({s.team_name for s in shifts if s.team_name}),
            }
        )
    return result


@router.get("/volunteers/{persona_id}", response_model=dict)
def get_volunteer_detail(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    persona = _get_persona_or_404(db, persona_id, user_sede)
    shifts = (
        db.query(models.VolunteerShift)
        .filter(models.VolunteerShift.persona_id == persona.id)
        .order_by(models.VolunteerShift.shift_start.desc())
        .all()
    )
    latest_shift = shifts[0] if shifts else None
    total_hours = 0
    for shift in shifts:
        if shift.shift_start and shift.shift_end:
            total_hours += int((shift.shift_end - shift.shift_start).total_seconds() // 3600)
    skills = sorted(
        row.name
        for row in (
            db.query(models.VolunteerSkill)
            .join(
                models.member_volunteer_skills,
                models.member_volunteer_skills.c.skill_id == models.VolunteerSkill.id,
            )
            .filter(models.member_volunteer_skills.c.persona_id == persona.id)
            .all()
        )
        if row.name
    )
    return {
        "id": persona.id,
        "name": _persona_full_name(persona),
        "role": persona.church_role,
        "team": latest_shift.team_name if latest_shift else None,
        "status": latest_shift.status if latest_shift else "inactive",
        "joined_date": (latest_shift.shift_start.isoformat() if latest_shift and latest_shift.shift_start else None),
        "total_hours": total_hours,
        "skills": skills,
    }


@router.patch("/volunteers/{persona_id}", response_model=dict)
def update_volunteer(
    persona_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    persona = _get_persona_or_404(db, persona_id, user_sede)
    allowed = {"church_role", "first_name", "last_name", "phone", "email"}
    for k, v in payload.items():
        if k in allowed:
            setattr(persona, k, v)
    db.commit()
    db.refresh(persona)
    return {
        "id": persona.id,
        "name": _persona_full_name(persona),
        "role": persona.church_role,
    }


@router.delete("/volunteers/{persona_id}", status_code=204)
def delete_volunteer(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Soft-delete: desactiva turnos de voluntario y marca persona como INACTIVA."""
    user_sede = get_user_sede_id(db, current_user.id)
    persona = _get_persona_or_404(db, persona_id, user_sede)
    # Cancelar turnos futuros del voluntario (datos satélite, no Persona)
    db.query(models.VolunteerShift).filter(models.VolunteerShift.persona_id == persona.id).update(
        {models.VolunteerShift.deleted_at: utc_now()}, synchronize_session=False
    )
    # Soft-delete de la Persona
    persona.estado_vital = "INACTIVO"
    from datetime import date

    persona.unregistration_date = date.today()
    db.commit()


@router.get("/groups", response_model=List[dict])
def list_crm_groups(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Lista grupos/ministerios para vistas comunitarias."""
    ministries = db.query(models.Ministry).all()
    return [
        {
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "leader": None,
            "members_count": len(m.personas) if m.personas else 0,
        }
        for m in ministries
    ]


@router.get("/radar", response_model=dict)
def get_crm_radar(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Datos del radar ministerial para dashboard."""
    user_sede = get_user_sede_id(db, current_user.id)

    members_q = db.query(models.Persona)
    if user_sede:
        members_q = members_q.filter(models.Persona.sede_id == user_sede)
    total_members = members_q.count()

    total_ministries = db.query(models.Ministry).count()

    cases_q = db.query(models.CasoCRM).filter(
        models.CasoCRM.estado != "CERRADO",
        models.CasoCRM.deleted_at.is_(None),
    )
    if user_sede:
        cases_q = cases_q.filter(models.CasoCRM.sede_id == user_sede)
    active_cases = cases_q.count()

    tasks_q = db.query(models.CrmTask).filter(models.CrmTask.status == "pending")
    if user_sede:
        tasks_q = tasks_q.join(models.Persona, models.CrmTask.persona_id == models.Persona.id).filter(
            models.Persona.sede_id == user_sede
        )
    pending_tasks = tasks_q.count()

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
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """
    CRM view para ver todos los leads originados desde suscripción al newsletter.
    Permite filtrar por source, stage, landing_page, campaign y rango de fechas.
    """
    query = (
        db.query(models.CasoCRM)
        .join(models.Persona, models.CasoCRM.persona_id == models.Persona.id)
        .filter(
            models.CasoCRM.origen_canal.like("%newsletter%"),
            models.CasoCRM.estado != "CERRADO",
        )
    )

    if source:
        query = query.filter(models.CasoCRM.origen_canal == source)
    if stage:
        query = query.filter(models.CasoCRM.estado == stage)
    if landing_page:
        query = query.filter(models.CasoCRM.payload_web.like(f"%Landing: {landing_page}%"))
    if campaign:
        query = query.filter(models.CasoCRM.payload_web.like(f"%Campaign: {campaign}%"))
    if date_from:
        query = query.filter(models.CasoCRM.fecha_creacion >= date_from)
    if date_to:
        query = query.filter(models.CasoCRM.fecha_creacion <= date_to)

    total = query.count()
    cases = query.order_by(models.CasoCRM.fecha_creacion.desc()).offset((page - 1) * page_size).limit(page_size).all()

    leads = []
    for case in cases:
        persona = case.persona
        leads.append(
            {
                "case_id": case.id,
                "persona_id": persona.id if persona else None,
                "nombre_completo": persona.nombre_completo if persona else "",
                "email": persona.email if persona else None,
                "telefono": persona.telefono if persona else None,
                "source": str(case.origen_canal.value) if case.origen_canal else None,
                "stage": str(case.estado.value) if case.estado else None,
                "notes": case.titulo_caso,
                "created_at": case.fecha_creacion.isoformat() if case.fecha_creacion else None,
            }
        )

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
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """
    Exporta leads de newsletter como lista de dicts (para generar CSV en frontend).
    """
    query = (
        db.query(models.CasoCRM)
        .join(models.Persona, models.CasoCRM.persona_id == models.Persona.id)
        .filter(
            models.CasoCRM.origen_canal.like("%newsletter%"),
            models.CasoCRM.estado != "CERRADO",
        )
    )

    if source:
        query = query.filter(models.CasoCRM.origen_canal == source)
    if date_from:
        query = query.filter(models.CasoCRM.fecha_creacion >= date_from)
    if date_to:
        query = query.filter(models.CasoCRM.fecha_creacion <= date_to)

    cases = query.order_by(models.CasoCRM.fecha_creacion.desc()).all()

    rows = []
    for case in cases:
        persona = case.persona
        rows.append(
            {
                "first_name": persona.first_name if persona else "",
                "last_name": persona.last_name if persona else "",
                "email": persona.email if persona else "",
                "phone": persona.phone if persona else "",
                "source": str(case.origen_canal.value) if case.origen_canal else "",
                "stage": str(case.estado.value) if case.estado else "",
                "notes": case.titulo_caso or "",
                "created_at": str(case.fecha_creacion) if case.fecha_creacion else "",
            }
        )

    return {"rows": rows, "count": len(rows)}


# ──────────────────────────────────────────────
# PASTORAL CALL LOGS (Registro de llamadas de consolidación)
# ──────────────────────────────────────────────

@router.get("/consolidation/cases/{case_id}/calls", response_model=List[dict])
def list_consolidation_calls(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """List all call logs for a consolidation case."""
    user_sede = get_user_sede_id(db, current_user.id)
    _get_case_or_404(db, case_id, user_sede)
    case_uuid = uuid.UUID(case_id) if isinstance(case_id, str) else case_id
    logs = (
        db.query(models.PastoralCallLog)
        .filter(models.PastoralCallLog.case_id == case_uuid)
        .order_by(models.PastoralCallLog.created_at.desc())
        .all()
    )
    return [
        {
            "id": log.id,
            "case_id": str(log.case_id) if log.case_id else None,
            "persona_id": str(log.persona_id) if log.persona_id else None,
            "pastor_id": str(log.pastor_id) if log.pastor_id else None,
            "outcome": log.outcome,
            "notes": log.notes,
            "prayer_requests": log.prayer_requests,
            "duration_seconds": log.duration_seconds,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


@router.post("/consolidation/cases/{case_id}/calls", response_model=dict, status_code=201)
def create_consolidation_call(
    case_id: str,
    payload: schemas.PastoralCallLogCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Register a call log for a consolidation case."""
    user_sede = get_user_sede_id(db, current_user.id)
    _get_case_or_404(db, case_id, user_sede)
    case_uuid = uuid.UUID(case_id) if isinstance(case_id, str) else case_id

    # Resolve pastor_id from current user if not provided
    pastor_uuid = None
    if payload.pastor_id:
        pastor_uuid = uuid.UUID(str(payload.pastor_id))
    else:
        persona_id_str = resolve_persona_id_for_user(db, current_user.id)
        if persona_id_str:
            pastor_uuid = uuid.UUID(persona_id_str)

    # Resolve persona_id if provided
    persona_uuid = None
    if payload.persona_id:
        persona_uuid = uuid.UUID(str(payload.persona_id))

    row = models.PastoralCallLog(
        case_id=case_uuid,
        persona_id=persona_uuid,
        pastor_id=pastor_uuid or current_user.id,
        outcome=payload.outcome,
        notes=payload.notes,
        prayer_requests=payload.prayer_requests,
        duration_seconds=payload.duration_seconds,
    )
    db.add(row)

    # Update case last_contact_at
    case = _get_case_or_404(db, case_id, user_sede)
    case.last_contact_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "case_id": str(row.case_id) if row.case_id else None,
        "persona_id": str(row.persona_id) if row.persona_id else None,
        "pastor_id": str(row.pastor_id) if row.pastor_id else None,
        "outcome": row.outcome,
        "notes": row.notes,
        "prayer_requests": row.prayer_requests,
        "duration_seconds": row.duration_seconds,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
