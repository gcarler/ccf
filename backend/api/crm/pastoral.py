import collections
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.crm._shared import (
    _get_scoped_counseling_ticket,
    _get_scoped_grupo,
    _get_scoped_persona,
    _get_scoped_prayer_request,
    _get_scoped_task,
    _persona_full_name,
    _resolve_assignee_for_task,
    _scope_by_user_sede_via_persona,
    _serialize_case,
    _serialize_message_group,
    _serialize_task,
    utc_now,
)
from backend.core.database import get_db
from backend.core.permissions import normalize_role, require_module_access
from backend.crud.crm import (
    get_user_sede_id,
    resolve_persona_id_for_user,
)
from backend.models_crm_pipeline import CanalOrigenEnum, EstadoCasoEnum, TipoInteraccionEnum
from backend.services.evangelism_crm_bridge import crear_caso_nuevo_visitante
from backend.services.messaging import (
    MessagingGateway,
    StubMessagingGateway,  # noqa: F401 — disponible para override manual en tests
    get_messaging_gateway,
)
from backend.services.public_contact_tracking import ContactRecord, tracker

router = APIRouter(tags=["CRM"])
logger = logging.getLogger(__name__)


def _get_user_role(user: models.User) -> str:
    role = normalize_role(str(getattr(user, "role", "")))
    if not role and hasattr(user, "rol_plataforma") and user.rol_plataforma:
        role = normalize_role(user.rol_plataforma.nombre)
    return role


def _get_case_or_404(db: Session, case_id: str, user_sede: Optional[uuid.UUID]):
    try:
        case_uuid = uuid.UUID(case_id) if isinstance(case_id, str) else case_id
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid case ID format")
    case = (
        db.query(models.CasoCRM)
        .filter(
            models.CasoCRM.id == case_uuid,
            models.CasoCRM.deleted_at.is_(None),
        )
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if user_sede and str(case.sede_id) != str(user_sede):
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def _payload_key(name: str) -> str:
    return name


def _stage_to_estado(stage: str) -> EstadoCasoEnum:
    normalized = str(stage or "").strip().lower()
    if normalized in {"consolidated", "integrated", "converted"}:
        return EstadoCasoEnum.RESUELTO_EXITO
    if normalized in {"lost", "closed", "discarded"}:
        return EstadoCasoEnum.CERRADO_PERDIDO
    if normalized in {"call", "contacted"}:
        return EstadoCasoEnum.ESPERANDO_RESPUESTA
    if normalized in {"visit", "visited", "discipleship", "in_process"}:
        return EstadoCasoEnum.EN_PROGRESO
    return EstadoCasoEnum.ABIERTO


def _update_case_field(case, key: str, value) -> None:
    if hasattr(case, key):
        setattr(case, key, value)
        return

    payload = dict(case.payload_web or {})
    if key == "stage":
        payload[_payload_key("stage")] = value
        case.estado = _stage_to_estado(value)
    elif key == "source":
        payload[_payload_key("source")] = value
    elif key == "notes":
        payload[_payload_key("notes")] = value
    elif key == "status":
        payload[_payload_key("status")] = value
    elif key in {"last_contact_at", "next_contact_at"}:
        payload[_payload_key(key)] = value.isoformat() if hasattr(value, "isoformat") else value
    elif key in {"assigned_pastor_id", "assigned_leader_id"}:
        case.asignado_a_id = value
    else:
        payload[_payload_key(key)] = value
    case.payload_web = payload


def _get_persona_or_404(db: Session, persona_ref: str, user_sede: Optional[uuid.UUID] = None):
    """Resolve a canonical UUID persona reference within the user's sede."""
    try:
        persona_uuid = uuid.UUID(str(persona_ref))
        persona = db.query(models.Persona).filter(models.Persona.id == persona_uuid).first()
    except (TypeError, ValueError):
        persona = None

    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    if user_sede and persona.sede_id and str(persona.sede_id) != str(user_sede):
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


def _resolve_actor_persona_uuid(db: Session, current_user: models.User):
    persona = db.query(models.Persona.id).filter(models.Persona.id == current_user.id).first()
    if not persona:
        raise HTTPException(status_code=400, detail="No se pudo resolver la persona responsable")
    return current_user.id


def _serialize_core_interaction_as_call(row: models.InteraccionCRM) -> dict:
    notes = row.resumen or ""
    outcome = row.tipo.value if hasattr(row.tipo, "value") else str(row.tipo)
    prefix = "Resultado: "
    if notes.startswith(prefix):
        first_line, _, rest = notes.partition("\n\n")
        outcome = first_line.replace(prefix, "", 1).strip() or outcome
        notes = rest or ""
    return {
        "id": row.id,
        "case_id": str(row.caso_id) if row.caso_id else None,
        "persona_id": None,
        "pastor_id": str(row.realizado_por_id) if row.realizado_por_id else None,
        "outcome": outcome,
        "notes": notes,
        "prayer_requests": None,
        "duration_seconds": row.duration_seconds or 0,
        "created_at": row.fecha_interaccion.isoformat() if row.fecha_interaccion else None,
    }


# ═══════════════════════════════════════════════════════════════════
# REDIRECTS: Old CRM endpoints → new CRM Core
# ═══════════════════════════════════════════════════════════════════


@router.get("/casos/{case_id}", response_model=dict)
def get_caso_crm(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    case = _get_case_or_404(db, case_id, user_sede)
    return _serialize_case(case)


@router.post("/casos", response_model=dict)
def create_caso_crm(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    if "persona_id" not in payload:
        user_sede = get_user_sede_id(db, current_user.id)
        if not user_sede:
            raise HTTPException(status_code=400, detail="El usuario no tiene sede asignada")

        phone = str(payload.get("phone") or "").strip() or None
        email = str(payload.get("email") or "").strip() or None
        conditions = []
        if phone:
            conditions.append(models.Persona.phone == phone)
        if email:
            conditions.append(models.Persona.email == email)
        persona = (
            db.query(models.Persona)
            .filter(or_(*conditions), models.Persona.sede_id == uuid.UUID(str(user_sede)))
            .first()
            if conditions
            else None
        )
        if not persona:
            persona = models.Persona(
                first_name=str(payload.get("first_name") or "Prospecto").strip() or "Prospecto",
                last_name=str(payload.get("last_name") or "").strip(),
                phone=phone,
                email=email,
                spiritual_status=str(payload.get("spiritual_status") or "Prospecto"),
                church_role="Visitante",
                sede_id=uuid.UUID(str(user_sede)),
            )
            db.add(persona)
            db.flush()

        case = crear_caso_nuevo_visitante(
            db,
            persona,
            uuid.UUID(str(persona.sede_id or user_sede)),
            titulo_prefix="Caso CRM",
        )
        if not case:
            raise HTTPException(status_code=500, detail="No se pudo crear el caso CRM")
        _update_case_field(case, "stage", payload.get("stage", "new"))
        _update_case_field(case, "source", payload.get("source", "Visitante"))
        _update_case_field(case, "notes", payload.get("notes"))
        db.commit()
        db.refresh(case)
        return _serialize_case(case)

    p_uuid = uuid.UUID(payload["persona_id"]) if isinstance(payload["persona_id"], str) else payload["persona_id"]
    persona = db.query(models.Persona).filter(models.Persona.id == p_uuid).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    user_sede = get_user_sede_id(db, current_user.id)
    if not persona.sede_id or (user_sede and persona.sede_id != uuid.UUID(str(user_sede))):
        raise HTTPException(status_code=404, detail="Persona not found")
    case = crear_caso_nuevo_visitante(
        db,
        persona,
        persona.sede_id,
        titulo_prefix="Consolidacion",
    )
    if not case:
        raise HTTPException(status_code=500, detail="No se pudo crear el caso de consolidacion")
    for key in ("stage", "status", "source", "notes", "assigned_pastor_id", "assigned_leader_id"):
        if key in payload:
            _update_case_field(case, key, payload[key])
    db.commit()
    db.refresh(case)
    return _serialize_case(case)


@router.patch("/casos/{case_id}", response_model=dict)
def update_caso_crm(
    case_id: str,
    payload: schemas.CaseUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    case = _get_case_or_404(db, case_id, user_sede)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key in ("assigned_pastor_id", "assigned_leader_id") and value is not None:
            value = uuid.UUID(str(value))
        _update_case_field(case, key, value)
    db.commit()
    db.refresh(case)
    return _serialize_case(case)


@router.post("/casos/{case_id}/interactions", response_model=dict)
def create_caso_interaction(
    case_id: str,
    payload: schemas.CaseInteractionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    case = _get_case_or_404(db, case_id, user_sede)
    interaction_data = payload.model_dump(exclude={"case_id"})
    case_uuid = uuid.UUID(case_id) if isinstance(case_id, str) else case_id
    actor_id = _resolve_actor_persona_uuid(db, current_user)
    row = models.InteraccionCRM(
        caso_id=case_uuid,
        realizado_por_id=actor_id,
        tipo=TipoInteraccionEnum.LLAMADA_OUTBOUND,
        fecha_interaccion=interaction_data.get("interaction_date") or datetime.now(timezone.utc),
        resumen=interaction_data.get("notes") or interaction_data.get("result") or "Interacción registrada",
    )
    db.add(row)
    _update_case_field(case, "last_contact_at", row.fecha_interaccion)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "case_id": str(row.caso_id),
        "performed_by_id": str(row.realizado_por_id),
        "interaction_type": row.tipo.value if hasattr(row.tipo, "value") else str(row.tipo),
        "interaction_date": row.fecha_interaccion.isoformat() if row.fecha_interaccion else None,
        "result": row.tipo.value if hasattr(row.tipo, "value") else str(row.tipo),
        "created_at": row.fecha_interaccion.isoformat() if row.fecha_interaccion else None,
    }


@router.post("/casos/{case_id}/tasks", response_model=dict)
def create_caso_task(
    case_id: str,
    payload: schemas.CaseTaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    _get_case_or_404(db, case_id, user_sede)
    case_uuid = uuid.UUID(case_id) if isinstance(case_id, str) else case_id
    row = models.TareaCRM(
        caso_id=case_uuid,
        asignado_a_id=_resolve_actor_persona_uuid(db, current_user),
        titulo=payload.title,
        descripcion=payload.description,
        fecha_vencimiento=payload.due_date or datetime.now(timezone.utc) + timedelta(days=1),
        completada=payload.status == "completed",
        fecha_completada=payload.completed_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "case_id": str(row.caso_id),
        "assignment_id": None,
        "title": row.titulo,
        "status": "completed" if row.completada else "pending",
        "due_date": row.fecha_vencimiento.isoformat(),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


# --- LIST / DELETE Cases, nested resources ---


@router.get("/casos", response_model=dict)
def list_crm_casos(
    source: Optional[str] = None,
    stage: Optional[str] = None,
    status: Optional[str] = None,
    persona_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Lista casos CRM con paginación y filtros."""
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


@router.delete("/casos/{case_id}", status_code=204)
def delete_caso_crm(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Archiva un caso CRM (soft delete)."""
    user_sede = get_user_sede_id(db, current_user.id)
    case = _get_case_or_404(db, case_id, user_sede)
    case.deleted_at = utc_now()
    db.commit()
    return None


@router.get("/casos/{case_id}/tasks", response_model=List[dict])
def list_caso_tasks(
    case_id: str,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Lista las tareas de seguimiento de un caso."""
    user_sede = get_user_sede_id(db, current_user.id)
    _get_case_or_404(db, case_id, user_sede)

    case_uuid = uuid.UUID(str(case_id))
    q = db.query(models.TareaCRM).filter(
        models.TareaCRM.caso_id == case_uuid,
        models.TareaCRM.deleted_at.is_(None),
    )
    if status_filter:
        q = q.filter(models.TareaCRM.estado == status_filter)

    tasks = q.order_by(models.TareaCRM.created_at.desc()).all()
    return [
        {
            "id": t.id,
            "case_id": t.caso_id,
            "assignment_id": None,
            "title": t.titulo,
            "description": t.descripcion,
            "status": "completed" if t.completada else "pending",
            "due_date": t.fecha_vencimiento.isoformat(),
            "completed_at": t.fecha_completada.isoformat() if t.fecha_completada else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tasks
    ]


@router.patch("/casos/{case_id}/tasks/{task_id}", response_model=dict)
def update_caso_task(
    case_id: str,
    task_id: str,
    payload: schemas.CaseTaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Actualiza una tarea de seguimiento (ej. marcar como completada)."""
    user_sede = get_user_sede_id(db, current_user.id)
    _get_case_or_404(db, case_id, user_sede)
    task = (
        db.query(models.TareaCRM)
        .filter(
            models.TareaCRM.id == uuid.UUID(str(task_id)),
            models.TareaCRM.caso_id == uuid.UUID(str(case_id)),
            models.TareaCRM.deleted_at.is_(None),
        )
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = payload.model_dump(exclude_unset=True)
    field_map = {
        "title": "titulo",
        "description": "descripcion",
        "due_date": "fecha_vencimiento",
        "completed_at": "fecha_completada",
    }
    for key, value in updates.items():
        if key == "status":
            task.completada = value == "completed"
            task.fecha_completada = datetime.now(timezone.utc) if task.completada else None
        elif key != "assignment_id":
            setattr(task, field_map[key], value)
    db.commit()
    db.refresh(task)

    return {
        "id": task.id,
        "case_id": task.caso_id,
        "assignment_id": None,
        "title": task.titulo,
        "status": "completed" if task.completada else "pending",
        "due_date": task.fecha_vencimiento.isoformat(),
        "completed_at": task.fecha_completada.isoformat() if task.fecha_completada else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.get("/casos/{case_id}/interactions", response_model=List[dict])
def list_caso_interactions(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Lista las interacciones de un caso de consolidación."""
    user_sede = get_user_sede_id(db, current_user.id)
    _get_case_or_404(db, case_id, user_sede)
    case_uuid = uuid.UUID(case_id) if isinstance(case_id, str) else case_id

    interactions = (
        db.query(models.InteraccionCRM)
        .filter(models.InteraccionCRM.caso_id == case_uuid)
        .order_by(models.InteraccionCRM.fecha_interaccion.desc())
        .all()
    )
    return [
        {
            "id": i.id,
            "case_id": str(i.caso_id),
            "performed_by_id": str(i.realizado_por_id),
            "interaction_type": i.tipo.value if hasattr(i.tipo, "value") else str(i.tipo),
            "interaction_date": i.fecha_interaccion.isoformat() if i.fecha_interaccion else None,
            "result": i.tipo.value if hasattr(i.tipo, "value") else str(i.tipo),
            "notes": i.resumen,
            "next_action_date": None,
            "created_at": i.fecha_interaccion.isoformat() if i.fecha_interaccion else None,
        }
        for i in interactions
    ]


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

    if persona_id:
        target_personas = [{"id": persona_id}]
    else:
        persona_map: dict[str, models.Persona] = {}
        for segment in target_segments:
            normalized = str(segment).strip().lower()
            if normalized == "active":
                q = db.query(models.Persona).filter(models.Persona.church_role == "Miembro")
                q = _scope_by_user_sede_via_persona(db, current_user, q)
                if channel in {"whatsapp", "sms"}:
                    q = q.filter(models.Persona.phone.isnot(None), models.Persona.phone != "")
                elif channel == "email":
                    q = q.filter(models.Persona.email.isnot(None), models.Persona.email != "")
                rows = q.all()
            elif normalized == "groups":
                q = db.query(models.Persona).filter(models.Persona.family_id.isnot(None))
                q = _scope_by_user_sede_via_persona(db, current_user, q)
                if channel in {"whatsapp", "sms"}:
                    q = q.filter(models.Persona.phone.isnot(None), models.Persona.phone != "")
                elif channel == "email":
                    q = q.filter(models.Persona.email.isnot(None), models.Persona.email != "")
                rows = q.all()
            else:
                rows = []
            for persona in rows:
                persona_map[str(persona.id)] = persona
        target_personas = list(persona_map.values())

    if not target_personas:
        raise HTTPException(status_code=404, detail="No target personas found")

    external_id = f"CMP-{uuid.uuid4().hex[:12]}" if len(target_personas) > 1 else None
    delivered_count = 0
    failed_count = 0
    log_ids: list[int] = []

    for persona in target_personas:
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
            if len(target_personas) == 1:
                logger.exception("Messaging gateway failure")
                raise HTTPException(status_code=502, detail="No se pudo enviar el mensaje")

    return {
        "status": "success",
        "target_count": len(target_personas),
        "delivered_count": delivered_count,
        "failed_count": failed_count,
        "log_ids": log_ids,
    }


@router.get("/messaging/history", response_model=List[dict])
def list_messaging_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    q = db.query(models.CommunicationLog).join(models.Persona, models.CommunicationLog.persona_id == models.Persona.id)
    q = _scope_by_user_sede_via_persona(db, current_user, q)
    logs = q.order_by(models.CommunicationLog.created_at.desc()).all()
    grouped: "collections.OrderedDict[str, list[models.CommunicationLog]]" = collections.OrderedDict()
    for log in logs:
        key = log.external_id or f"log-{log.id}"
        grouped.setdefault(key, []).append(log)
    return [_serialize_message_group(items) for items in grouped.values()]


@router.get("/messaging/history/{log_id}", response_model=dict)
def get_messaging_history_item(
    log_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Axioma 3: el log de mensajería sólo se expone si su Persona está en la
    sede del usuario. CommunicationLog no tiene sede_id propio; el scope se
    aplica via JOIN con Persona (mismo patrón que list_messaging_history).
    """
    query = (
        db.query(models.CommunicationLog)
        .join(models.Persona, models.CommunicationLog.persona_id == models.Persona.id)
        .filter(models.CommunicationLog.id == log_id)
    )
    query = _scope_by_user_sede_via_persona(db, current_user, query)
    log = query.first()
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
    assignee_persona_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Lista tareas CRM con scope Axioma 3 (JOIN Persona + validate assignee)."""
    q = db.query(models.TareaCRM).join(
        models.Persona, models.TareaCRM.persona_id == models.Persona.id
    )
    q = _scope_by_user_sede_via_persona(db, current_user, q)
    if assignee_persona_id:
        _get_scoped_persona(db, current_user, assignee_persona_id)
        q = q.filter(models.TareaCRM.assignee_id == assignee_persona_id)
    tasks = q.order_by(models.TareaCRM.created_at.desc()).all()
    return [_serialize_task(t) for t in tasks]


@router.post("/tasks/", response_model=dict)
def create_crm_task(
    payload: schemas.CrmTaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Crea una tarea CRM con scope validation (Axioma 3) y Pydantic
    auto-validation en la frontera (`schemas.CrmTaskCreate`).

    Hardening:
      - **Pydantic auto-validates** al nivel del request body (canonical
        FastAPI pattern): `status`/`priority` son
        `CrmTaskStatus`/`CrmTaskPriority` case-sensitive (cualquier
        valor fuera del catálogo → 422 estructurado vía FastAPI antes
        de entrar al handler). `persona_id`/`caso_id` son `UUID` (422
        si malformados). `due_date`/`completed_at` se auto-parsean ISO
        → datetime. Migración desde `payload: dict` con whitelist
        inline — ahora la validación es 100% declarativa en schema.
      - `title` queda validación manual 400 (vacío vs no-provisto:
        auto-422 por Pydantic, presente-pero-vacío: 400 detecta
        silenciosamente caller error).
      - validate `persona_id` (target persona) — debe estar en scope
        (404 cross-sede).
      - valida `assignee_id` como UUID canónico de persona y aplica scope;
        un identificador de usuario de autenticación nunca es aceptado.

    Audit log (Axioma 1) emitido por `crud.create_crm_task` (defense in
    depth): el caller API no genera audit trail directamente; el CRUD es
    garante único de la traza independientemente del caller (API,
    script, worker).
    """
    # ── Title validation ──────────────────────────────────────────────────
    # Pydantic en frontera rechaza missing (422) — aquí detectamos empty
    # string (400) por si un caller construye un POST con title:"" que
    # Pydantic por defecto acepta (no hay min_length en el schema).
    title = str(payload.title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    # ── Axioma 3 — validate persona_id (target) is in scope ────────────
    if payload.persona_id:
        scoped_persona = _get_scoped_persona(db, current_user, payload.persona_id)
        # In-place mutation: Pydantic v2 BaseModel es mutable por default.
        payload.persona_id = scoped_persona.id

    # ── Axioma 3 — validate canonical persona UUID with scope ───────────
    # Por defecto el editor se asigna la tarea (mantiene visibilidad dentro
    # de su propia sede vía _scope_by_user_sede_via_persona).
    if payload.assignee_id:
        resolved_assignee_persona_id = _resolve_assignee_for_task(
            db, current_user, payload.assignee_id
        )
        payload.assignee_id = resolved_assignee_persona_id
    else:
        resolved_assignee_persona_id = resolve_persona_id_for_user(
            db, current_user.id
        )
        payload.assignee_id = resolved_assignee_persona_id

    # ── Side-effect: status ↔ completed_at ─────────────────────────────
    # Si la tarea nace en `completed`, estampar fecha_completada AHORA
    # para que el audit log de CREATE capture el estado completo (evita
    # un segundo commit post-CRUD sin audit: fuga silenciosa de
    # trazabilidad — Axioma 1 defense in depth). override también
    # cualquier `completed_at` enviado por el cliente (server-authoritative
    # timestamp).
    from backend.schemas.crm import CrmTaskStatus

    payload.completed_at = (
        utc_now() if payload.status == CrmTaskStatus.completed else None
    )

    # Pydantic YA validó Enum membership en frontera (`payload.status` es
    # instancia `CrmTaskStatus`). `use_enum_values=True` en
    # `CrmTaskBase` garantiza `model_dump()` retorna strings planos
    # alineados con `TareaCRM.estado` `String(20)` y JSONB-safe para
    # `logs_auditoria`.

    task = crud.create_crm_task(
        db, payload, actor_user_id=str(current_user.id)
    )
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
        db.query(models.TareaCRM)
        .filter(models.TareaCRM.assignee_id == my_persona_id)
        .order_by(models.TareaCRM.created_at.desc())
        .all()
    )
    return [_serialize_task(task) for task in tasks]


@router.get("/tasks/{task_id}", response_model=dict)
def get_crm_task_detail(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Axioma 3: una tarea sólo es visible si está anclada a la sede del
    editor (cualquiera de sus FKs: caso_id, persona_id, asignado_a_id).
    Implementado con `_get_scoped_task` (OR-based, 404 cross-sede —
    mismo patrón que `update_crm_task`).

    Luego aplica el control de visibilidad existente (staff vs owner-persona);
    si la tarea es del editor pero no es staff y no es owner, retorna 403.
    """
    task = _get_scoped_task(db, current_user, task_id)
    is_staff = _get_user_role(current_user) in {"admin", "administrador", "pastor", "coordinador"}
    my_persona_id = resolve_persona_id_for_user(db, getattr(current_user, "id", None))
    is_persona_owner = task.assignee_id is not None and task.assignee_id == my_persona_id
    if not is_staff and not is_persona_owner:
        raise HTTPException(status_code=403, detail="No autorizado para ver esta tarea")
    return _serialize_task(task)


@router.patch("/tasks/{task_id}", response_model=dict)
def update_crm_task(
    task_id: uuid.UUID,
    payload: schemas.CrmTaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Actualiza una tarea CRM con scope validation (Axioma 3) y
    type validation via Pydantic en la frontera (`schemas.CrmTaskUpdate`).

    Hardening:
      - **Type + Enum validation** declarativa en `CrmTaskUpdate`:
        `persona_id`/`caso_id` son `UUID` (422 si malformados); `status`/
        `priority` son `Optional[CrmTaskStatus]`/`Optional[CrmTaskPriority]`
        (case-sensitive, 422 si fuera del catálogo); `due_date`/
        `completed_at` se auto-parsean ISO → datetime; `assignee_id`
        acepta únicamente UUID de persona. NO hay whitelist inline — la
        validación para `status`/`priority` vive en el schema
        (canonical Pydantic Enum pattern).
      - **Unknown-field guard**: campos ajenos al schema se descartan
        (`extra='ignore'` default Pydantic v2), evitando crash en
        `setattr` para atributos inexistentes en `TareaCRM`.
      - retrieve task via `_get_scoped_task` (404 cross-sede en lectura).
      - validar `persona_id` y `assignee_id` actualizados: rechazamos
        IDs cross-sede con 404 (existence-leak safe).
      - side-effect: si status cambia y entra/sale de "completed",
        `fecha_completada` (synonym `completed_at`) se estampa o se
        limpia en el payload normalizado antes de delegar al CRUD.
        Si el cliente envía AMBOS `status=completed` +
        `completed_at=<value>`, el side-effect OVERRIDE (determinístico).

    Defense in depth (Axioma 3): `crud.update_crm_task` re-ejecuta
    `_crud_scope_re_check_task` sobre el estado final combinado
    (current_row_anchors + incoming_anchors).

    Audit log (Axioma 1) emitido por `crud.update_crm_task`: sólo
    cambios reales (cambio de `fecha_completada` por side-effect cuenta
    como cambio y queda trazado).
    """
    # ── Axioma 3 — retrieve task within scope (404 cross-sede) ─────────
    task = _get_scoped_task(db, current_user, task_id)

    # ── Construir payload normalizado (side-effects coalescen aquí) ─────
    # Pydantic YA validó tipo + Enum membership en frontera. Con
    # `use_enum_values=True` en `CrmTaskUpdate`, `model_dump()` retorna
    # strings planos — alineados con la columna `TareaCRM.estado`/
    # `prioridad` `String(20)` y JSONB-safe para `logs_auditoria`.
    # Trabajamos SOLO sobre los campos efectivamente incluidos en el PATCH.
    changes_in = payload.model_dump(exclude_unset=True)

    # ── Axioma 3 — IDs referenciales validados contra sede ────────────
    if "assignee_id" in changes_in:
        new_assignee = _resolve_assignee_for_task(
            db, current_user, changes_in["assignee_id"]
        )
        # Siempre emitimos el campo (incluso si es None) para que el CRUD
        # detecte el cambio contra el valor previo (auditoría honesta).
        changes_in["assignee_id"] = new_assignee

    if "persona_id" in changes_in:
        v = changes_in["persona_id"]
        if v is None:
            changes_in["persona_id"] = None  # cliente explícitamente limpia
        else:
            scoped = _get_scoped_persona(db, current_user, v)
            # Normalizamos al UUID canónico vía SQLAlchemy (re-hidrata
            # aunque el caller haya enviado un UUID equivalente).
            changes_in["persona_id"] = scoped.id

    # caso_id: Pydantic YA validó el formato UUID (422 si malformado).
    # defense-in-depth en `crud.update_crm_task` (`_crud_scope_re_check_task`)
    # detecta anclas cross-sede sobre el estado final: si caso_id pertenece
    # a otra sede o el row tiene caso_id cross-sede entre el API fetch y
    # el commit, raise 404. NO añadimos pre-validación acá para no
    # duplicar round-trip al DB en el camino feliz; el CRUD es el garante
    # único del scope check post-migración.

    # ── Side-effect: status ↔ fecha_completada ──────────────────────────
    # `nuevo_estado` es un string (post `model_dump` por `use_enum_values=True`).
    # Comparación contra `task.estado` (también string desde SQLAlchemy) es
    # trivial. El str `"completed"` matchea `CrmTaskStatus.completed.value`
    # por igualdad de string — comparamos con literal aqui para evitar
    # re-importar CrmTaskStatus en pastoral.py.
    nuevo_estado = changes_in.get("status", task.estado)
    if "status" in changes_in and nuevo_estado != task.estado:
        if nuevo_estado == "completed" and task.fecha_completada is None:
            changes_in["completed_at"] = utc_now()
        elif nuevo_estado != "completed" and task.fecha_completada is not None:
            # Reabrir: limpiar fecha_completada para que el audit detecte el cambio.
            changes_in["completed_at"] = None

    # ── Delegar al CRUD (atomic write + audit log + scope re-check) ────
    normalized_payload = schemas.CrmTaskUpdate.model_validate(changes_in)
    updated_task = crud.update_crm_task(
        db, task_id, normalized_payload, actor_user_id=str(current_user.id)
    )
    if updated_task is None:
        # Race: la task fue borrada entre el GET scope-check y el UPDATE CRUD.
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize_task(updated_task)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_crm_task(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Axioma 3: el soft-delete de una tarea sólo aplica si la tarea está
    en scope del editor (helper `_get_scoped_task` — 404 cross-sede).

    Sin esta validación, una vez conocido un `task_id` cross-sede, un editor
    de sede_a podría emitir DELETE y afectar la visibilidad de sede_b vía
    el soft-delete (`deleted_at`). El helper garantiza que la mutación
    siempre ocurre sobre filas del scope.
    """
    task = _get_scoped_task(db, current_user, task_id)
    task.deleted_at = utc_now()
    db.commit()
    return None


@router.get("/counseling/{ticket_id}", response_model=dict)
def get_counseling_detail(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Axioma 3: el ticket de consejería sólo se expone si su persona (FK)
    está en la sede del usuario. CounselingTicket NO tiene sede_id propio.
    """
    ticket = _get_scoped_counseling_ticket(db, current_user, ticket_id)
    history_rows = (
        db.query(models.CounselingTicket)
        .filter(models.CounselingTicket.persona_id == ticket.persona_id)
        .order_by(models.CounselingTicket.created_at.desc(), models.CounselingTicket.id.desc())
        .all()
    )
    return {
        "id": ticket.id,
        "persona_id": ticket.persona_id,
        "persona_name": _persona_full_name(ticket.persona),
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
    grupo_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Axioma 3: scope por sede via GrupoEvangelismo.sede_id."""
    grupo = _get_scoped_grupo(db, current_user, grupo_id)
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
    grupo_id: uuid.UUID,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Axioma 3: mutación interdita cross-sede (404 si el grupo no pertenece
    a la sede del usuario). Aplica también si los participante_ids objetivos
    pertenecen a otra sede — follow-up recomendado.
    """
    grupo = _get_scoped_grupo(db, current_user, grupo_id)

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
    request_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Axioma 3: PrayerRequest tiene sede_id propio ⇒ scope directo."""
    prayer = _get_scoped_prayer_request(db, current_user, request_id)
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
            "persona_name": _persona_full_name(t.persona) if t.persona else "",
            "topic": t.subject,
            "summary": t.subject,
            "notes": t.notes,
            "status": t.status,
            "priority_level": t.priority_level or "medium",
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tickets
    ]


def _resolve_pastor_identity(
    db: Session, current_user: models.User, pastor_id: Optional[uuid.UUID]
):
    """Valida el UUID canónico de persona del pastor dentro del scope."""
    if pastor_id is None:
        return None
    return _get_scoped_persona(db, current_user, pastor_id).id


@router.post("/counseling/", response_model=dict, status_code=201)
def create_counseling_ticket(
    payload: schemas.CounselingTicketCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Axioma 3 — Multi-Tenant: el ticket sólo se crea si la persona objetivo
    pertenece a la sede del editor. CounselingTicket NO tiene sede_id propio;
    el scope se aplica validando la FK a Persona vía _get_scoped_persona
    (404 cross-sede, no 403, para evitar existence-leaks).

    `pastor_id` es exclusivamente el UUID canónico de una persona y se valida
    dentro del scope antes de delegar al CRUD.
    """
    _get_scoped_persona(db, current_user, payload.persona_id)
    if payload.pastor_id:
        resolved_pastor_id = _resolve_pastor_identity(db, current_user, payload.pastor_id)
        if resolved_pastor_id:
            # Reemplazar en el payload para que el CRUD no intente resolver de
            # nuevo (es idempotente pero evita trabajo redundante y deja el
            # valor canónico UUID en la fila persistida).
            payload.pastor_id = resolved_pastor_id
    ticket = crud.create_counseling_ticket(db, payload)
    return {
        "id": ticket.id,
        "persona_id": ticket.persona_id,
        "persona_name": _persona_full_name(ticket.persona) if ticket.persona else "",
        "topic": ticket.subject,
        "summary": ticket.subject,
        "notes": ticket.notes,
        "status": ticket.status,
        "priority_level": ticket.priority_level or "medium",
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
    }


@router.get("/counseling/lead/{lead_id}", response_model=List[dict])
def get_counseling_by_lead(
    lead_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Axioma 3: tickets de un lead solo se exponen si el lead esta en scope."""
    lead = _get_scoped_persona(db, current_user, lead_id)
    q = (
        db.query(models.CounselingTicket)
        .join(models.Persona, models.CounselingTicket.persona_id == models.Persona.id)
        .filter(models.CounselingTicket.persona_id == lead.id)
    )
    q = _scope_by_user_sede_via_persona(db, current_user, q)
    tickets = q.order_by(models.CounselingTicket.created_at.desc()).all()
    return [
        {
            "id": t.id,
            "persona_id": t.persona_id,
            "persona_name": _persona_full_name(t.persona) if t.persona else "",
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
    ticket_id: UUID,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Axioma 3 — Multi-Tenant: el ticket sólo se lee/modifica si su persona
    (FK) pertenece a la sede del editor. CounselingTicket NO tiene sede_id
    propio; el scope se aplica via _get_scoped_counseling_ticket (404 cross-sede,
    no 403, para evitar existence-leaks).

    `pastor_id` (opcional) es un UUID canónico de persona y valida scope.
    """
    ticket = _get_scoped_counseling_ticket(db, current_user, ticket_id)

    if "pastor_id" in payload:
        resolved_pastor_id = _resolve_pastor_identity(
            db, current_user, payload["pastor_id"]
        )
        ticket.pastor_id = resolved_pastor_id

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
        "persona_name": _persona_full_name(ticket.persona) if ticket.persona else "",
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
    role_id: UUID,
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
    role_id: UUID,
    fallback_id: UUID,
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
        "message": "Rol eliminado y personas reasignadas correctamente",
    }


@router.get("/analytics", response_model=dict)
def get_crm_analytics_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    user_sede = get_user_sede_id(db, current_user.id)

    persona_q = db.query(models.Persona)
    persona_q = _scope_by_user_sede_via_persona(db, current_user, persona_q)

    total_personas = persona_q.count()
    active_personas = persona_q.filter(
        models.Persona.spiritual_status.in_(["Activo", "active", "Miembro Activo"])
    ).count()

    counseling_q = (
        db.query(models.CounselingTicket)
        .join(models.Persona, models.CounselingTicket.persona_id == models.Persona.id)
        .filter(
            models.CounselingTicket.status == "open",
            models.CounselingTicket.deleted_at.is_(None),
        )
    )
    counseling_q = _scope_by_user_sede_via_persona(db, current_user, counseling_q)
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
        "total_personas": total_personas,
        "active_personas": active_personas,
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
    pastoral pueda contactar para orar. Source='prayer-web'."""
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

    # Create PrayerRequest linked to the persona
    prayer = models.PrayerRequest(
        sede_id=result.persona.sede_id,
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
    """Lista pedidos de oracion con scope Axioma 3 (PrayerRequest.sede_id)."""
    user_sede = get_user_sede_id(db, current_user.id)
    q = db.query(models.PrayerRequest).order_by(models.PrayerRequest.created_at.desc())
    if user_sede:
        q = q.filter(models.PrayerRequest.sede_id == user_sede)
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
    """Crea un pedido de oracion con scope Axioma 3 (sede_id auto-asignado)."""
    user_sede = get_user_sede_id(db, current_user.id)
    if not user_sede:
        raise HTTPException(status_code=400, detail="El usuario no tiene sede asignada")
    prayer = models.PrayerRequest(
        requester_name=payload.get("requester_name", current_user.username),
        request_text=payload.get("request_text", ""),
        category=payload.get("category", "General"),
        is_public=payload.get("is_public", False),
        source=payload.get("source", "crm"),
        status="active",
        sede_id=user_sede,
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
    request_id: UUID,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Axioma 3: PATCH solo aplica si el prayer esta en scope (404 cross-sede)."""
    prayer = _get_scoped_prayer_request(db, current_user, request_id)
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

    personas_q = db.query(models.Persona)
    personas_q = _scope_by_user_sede_via_persona(db, current_user, personas_q)
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
                models.persona_volunteer_skills,
                models.persona_volunteer_skills.c.skill_id == models.VolunteerSkill.id,
            )
            .filter(models.persona_volunteer_skills.c.persona_id == persona.id)
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
            "personas_count": len(m.personas) if m.personas else 0,
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

    personas_q = db.query(models.Persona)
    personas_q = _scope_by_user_sede_via_persona(db, current_user, personas_q)
    total_personas = personas_q.count()

    total_ministries = db.query(models.Ministry).count()

    # Nota: cases_q se filtra por CasoCRM.sede_id (no por Persona) — el helper
    # _scope_by_user_sede_via_persona NO aplica aquí porque el modelo raíz no
    # es Persona. Axioma 3 se preserva vía el filtro directo sobre la propia
    # columna sede_id del modelo.
    cases_q = db.query(models.CasoCRM).filter(
        models.CasoCRM.estado != "CERRADO",
        models.CasoCRM.deleted_at.is_(None),
    )
    if user_sede:
        cases_q = cases_q.filter(models.CasoCRM.sede_id == user_sede)
    active_cases = cases_q.count()

    tasks_q = (
        db.query(models.TareaCRM)
        .join(models.Persona, models.TareaCRM.persona_id == models.Persona.id)
        .filter(models.TareaCRM.status == "pending")
    )
    tasks_q = _scope_by_user_sede_via_persona(db, current_user, tasks_q)
    pending_tasks = tasks_q.count()

    return {
        "total_personas": total_personas,
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

    Axioma 3 — Multi-Tenant: el JOIN con Persona ya estaba presente, sólo faltaba
    aplicar el filtro de sede (mismo patrón que export_newsletter_leads_csv).
    Un superadmin sin sede ve TODO lo no-borrado.
    """
    query = (
        db.query(models.CasoCRM)
        .join(models.Persona, models.CasoCRM.persona_id == models.Persona.id)
        .filter(
            models.CasoCRM.origen_canal == CanalOrigenEnum.WEB_FORM,
            models.CasoCRM.origen_detalle_id.ilike("%newsletter%"),
            models.CasoCRM.estado.notin_(
                (EstadoCasoEnum.RESUELTO_EXITO, EstadoCasoEnum.CERRADO_PERDIDO)
            ),
        )
    )
    query = _scope_by_user_sede_via_persona(db, current_user, query)

    if source:
        query = query.filter(models.CasoCRM.origen_detalle_id == source)
    if stage:
        query = query.filter(models.CasoCRM.estado == stage)
    if landing_page:
        query = query.filter(cast(models.CasoCRM.payload_web, String).ilike(f"%{landing_page}%"))
    if campaign:
        query = query.filter(cast(models.CasoCRM.payload_web, String).ilike(f"%{campaign}%"))
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
                "source": case.origen_detalle_id,
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
    Axioma 3: el JOIN con Persona (ya presente) permite filtrar por sede_id;
    por defecto trae TODO lo no-borrado si el superadmin no tiene sede.
    """
    query = (
        db.query(models.CasoCRM)
        .join(models.Persona, models.CasoCRM.persona_id == models.Persona.id)
        .filter(
            models.CasoCRM.origen_canal == CanalOrigenEnum.WEB_FORM,
            models.CasoCRM.origen_detalle_id.ilike("%newsletter%"),
            models.CasoCRM.estado.notin_(
                (EstadoCasoEnum.RESUELTO_EXITO, EstadoCasoEnum.CERRADO_PERDIDO)
            ),
        )
    )
    query = _scope_by_user_sede_via_persona(db, current_user, query)

    if source:
        query = query.filter(models.CasoCRM.origen_detalle_id == source)
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
                "source": case.origen_detalle_id or "",
                "stage": str(case.estado.value) if case.estado else "",
                "notes": case.titulo_caso or "",
                "created_at": str(case.fecha_creacion) if case.fecha_creacion else "",
            }
        )

    return {"rows": rows, "count": len(rows)}


# ──────────────────────────────────────────────
# PASTORAL CALL LOGS (Registro de llamadas de consolidación)
# ──────────────────────────────────────────────

@router.get("/casos/{case_id}/calls", response_model=List[dict])
def list_caso_calls(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """List all call logs for a CRM case."""
    user_sede = get_user_sede_id(db, current_user.id)
    _get_case_or_404(db, case_id, user_sede)
    case_uuid = uuid.UUID(case_id) if isinstance(case_id, str) else case_id
    logs = (
        db.query(models.InteraccionCRM)
        .filter(models.InteraccionCRM.caso_id == case_uuid)
        .order_by(models.InteraccionCRM.fecha_interaccion.desc())
        .all()
    )
    return [_serialize_core_interaction_as_call(log) for log in logs]


@router.post("/casos/{case_id}/calls", response_model=dict, status_code=201)
def create_caso_call(
    case_id: str,
    payload: schemas.CaseCallCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Register a call log for a CRM case."""
    user_sede = get_user_sede_id(db, current_user.id)
    case = _get_case_or_404(db, case_id, user_sede)
    case_uuid = uuid.UUID(case_id) if isinstance(case_id, str) else case_id

    pastor_uuid = _resolve_actor_persona_uuid(db, current_user)

    summary_parts = [f"Resultado: {payload.outcome}"]
    if payload.notes:
        summary_parts.append(payload.notes)
    if payload.prayer_requests:
        summary_parts.append(f"Motivo de oración: {payload.prayer_requests}")
    row = models.InteraccionCRM(
        caso_id=case_uuid,
        realizado_por_id=pastor_uuid,
        tipo=TipoInteraccionEnum.LLAMADA_OUTBOUND,
        resumen="\n\n".join(summary_parts) or payload.outcome,
        duration_seconds=payload.duration_seconds,
    )
    db.add(row)
    _update_case_field(case, "last_contact_at", datetime.now(timezone.utc))
    db.commit()
    db.refresh(row)
    return _serialize_core_interaction_as_call(row)
