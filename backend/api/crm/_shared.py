import uuid as _uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import inspect
from sqlalchemy.orm import Session, load_only, selectinload

from backend import models
from backend.crud._utils import _to_uuid
from backend.schemas.crm.base import PersonaResponse
from backend.core.tenant import get_user_sede_id
from backend.services.messaging_outcomes import (
    DELIVERED_OUTCOMES,
    CommunicationOutcome,
)


def _payload_key(name: str) -> str:
    return name


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _persona_live_column_names(db: Session) -> set[str]:
    bind = db.get_bind()
    if bind is None:
        return set()
    try:
        columns = inspect(bind).get_columns("personas")
    except Exception:
        return set()
    return {str(column.get("name")) for column in columns if column.get("name")}


def _case_live_column_names(db: Session) -> set[str]:
    bind = db.get_bind()
    if bind is None:
        return set()
    try:
        columns = inspect(bind).get_columns("crm_casos")
    except Exception:
        return set()
    return {str(column.get("name")) for column in columns if column.get("name")}


def _stage_live_column_names(db: Session) -> set[str]:
    bind = db.get_bind()
    if bind is None:
        return set()
    try:
        columns = inspect(bind).get_columns("crm_etapas_pipeline")
    except Exception:
        return set()
    return {str(column.get("name")) for column in columns if column.get("name")}


def persona_query(db: Session):
    live_cols = _persona_live_column_names(db)
    live_attrs = [
        getattr(models.Persona, name)
        for name in live_cols
        if hasattr(models.Persona, name)
    ]
    query = db.query(models.Persona)
    if live_attrs:
        query = query.options(load_only(*live_attrs))
    return query


def case_query(db: Session):
    live_cols = _case_live_column_names(db)
    live_attrs = [
        getattr(models.CasoCRM, name)
        for name in live_cols
        if hasattr(models.CasoCRM, name)
    ]
    query = db.query(models.CasoCRM)
    if live_attrs:
        query = query.options(load_only(*live_attrs))

    persona_live_cols = _persona_live_column_names(db)
    persona_live_attrs = [
        getattr(models.Persona, name)
        for name in persona_live_cols
        if hasattr(models.Persona, name)
    ]
    stage_live_cols = _stage_live_column_names(db)
    stage_live_attrs = [
        getattr(models.EtapaPipeline, name)
        for name in stage_live_cols
        if hasattr(models.EtapaPipeline, name)
    ]

    if persona_live_attrs:
        query = query.options(
            selectinload(models.CasoCRM.persona).load_only(*persona_live_attrs),
            selectinload(models.CasoCRM.asignado_a).load_only(*persona_live_attrs),
        )
    if stage_live_attrs:
        query = query.options(
            selectinload(models.CasoCRM.etapa_actual).load_only(*stage_live_attrs)
        )
    return query


def prepare_persona_for_output(db: Session, persona: models.Persona):
    """Populate missing ORM-backed attributes with None to avoid lazy-loading
    fields that are absent in the live table.
    """
    live_cols = _persona_live_column_names(db)
    for field_name in PersonaResponse.model_fields:
        if field_name == "nombre_completo" or field_name in live_cols:
            continue
        if hasattr(models.Persona, field_name):
            try:
                setattr(persona, field_name, None)
            except Exception:
                persona.__dict__[field_name] = None
    return persona


def prepare_case_for_output(db: Session, case: models.CasoCRM):
    live_cols = _case_live_column_names(db)
    for field_name in models.CasoCRM.__table__.columns.keys():
        if field_name in live_cols:
            continue
        if hasattr(models.CasoCRM, field_name):
            try:
                setattr(case, field_name, None)
            except Exception:
                case.__dict__[field_name] = None
    persona = getattr(case, "persona", None)
    if persona is not None:
        prepare_persona_for_output(db, persona)
    assigned = getattr(case, "asignado_a", None)
    if assigned is not None:
        prepare_persona_for_output(db, assigned)
    return case


# ── Axioma 3 — Multi-Tenant scope helpers (Axioma 3 pattern) ──────────────
# Mirrors backend/api/academy.py::_course_scope + _get_scoped_course. Raise
# 404 (not 403) so we never leak the existence of cross-sede rows.


def _scope_by_user_sede_via_persona(db: Session, user: models.User, query):
    """Axioma 3 — Multi-Tenant: agrega el filtro `Persona.sede_id == user_sede`
    a un query que YA tiene un JOIN con `models.Persona`. Si el usuario no
    tiene sede asignada (superadmin), se retorna el query sin modificar.

    Patrón DRY para endpoints que filtran via JOIN con Persona:
      - list_messaging_history, get_messaging_history_item
      - get_newsletter_leads, export_newsletter_leads_csv
    y cualquier endpoint futuro que siga el mismo axioma.

    El caller es responsable de haber aplicado el `.join(models.Persona, ...)`
    apropiado (con la FK correcta al modelo raíz del query).
    """
    user_sede = get_user_sede_id(db, user.id)
    if user_sede:
        query = query.filter(models.Persona.sede_id == user_sede)
    return query



def _get_scoped_persona(db: Session, user: models.User, persona_id) -> models.Persona:
    # Persona NO tiene columna deleted_at (usa estado_vital para soft-delete).
    from backend.crud._utils import _to_uuid
    try:
        persona_uuid = _to_uuid(persona_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    user_sede = get_user_sede_id(db, user.id)
    query = db.query(models.Persona)
    if user_sede:
        query = query.filter(models.Persona.sede_id == user_sede)
    # estado_vital default = "ACTIVO"; soft-delete marca "INACTIVO"
    query = query.filter(models.Persona.estado_vital != "INACTIVO")
    query = query.filter(models.Persona.id == persona_uuid)
    persona = query.first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return prepare_persona_for_output(db, persona)


def _get_scoped_family(db: Session, user: models.User, family_id: UUID) -> models.Family:
    """Family no tiene sede_id propio; el scope se aplica indirectamente vía
    las Personas que pertenecen a esa familia (Axioma 3). Una familia sin
    ninguna persona en la sede del usuario se considera fuera de scope.
    """
    fam = db.query(models.Family).filter(models.Family.id == family_id).first()
    if not fam:
        raise HTTPException(status_code=404, detail="Familia no encontrada")
    user_sede = get_user_sede_id(db, user.id)
    if user_sede:
        member_in_sede = (
            db.query(models.Persona.id)
            .filter(
                models.Persona.family_id == family_id,
                models.Persona.sede_id == user_sede,
            )
            .first()
        )
        if not member_in_sede:
            raise HTTPException(status_code=404, detail="Familia no encontrada")
    return fam


def _get_scoped_grupo(db: Session, user: models.User, grupo_id) -> models.GrupoEvangelismo:
    from backend.crud._utils import _to_uuid
    try:
        grupo_uuid = _to_uuid(grupo_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    user_sede = get_user_sede_id(db, user.id)
    query = db.query(models.GrupoEvangelismo).filter(models.GrupoEvangelismo.id == grupo_uuid)
    if user_sede:
        query = query.filter(models.GrupoEvangelismo.sede_id == user_sede)
    grupo = query.first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    return grupo


def _get_scoped_counseling_ticket(db: Session, user: models.User, ticket_id) -> models.CounselingTicket:
    from backend.crud._utils import _to_uuid
    try:
        ticket_uuid = _to_uuid(ticket_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Counseling ticket not found")
    user_sede = get_user_sede_id(db, user.id)
    query = db.query(models.CounselingTicket).filter(
        models.CounselingTicket.id == ticket_uuid,
        models.CounselingTicket.deleted_at.is_(None),
    )
    if user_sede:
        query = query.join(
            models.Persona, models.CounselingTicket.persona_id == models.Persona.id
        ).filter(models.Persona.sede_id == user_sede)
    ticket = query.first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Counseling ticket not found")
    return ticket


def _get_scoped_prayer_request(db: Session, user: models.User, request_id) -> models.PrayerRequest:
    from backend.crud._utils import _to_uuid
    try:
        req_uuid = _to_uuid(request_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Prayer request not found")
    user_sede = get_user_sede_id(db, user.id)
    query = db.query(models.PrayerRequest).filter(models.PrayerRequest.id == req_uuid)
    if user_sede:
        query = query.filter(models.PrayerRequest.sede_id == user_sede)
    prayer = query.first()
    if not prayer:
        raise HTTPException(status_code=404, detail="Prayer request not found")
    return prayer


def _get_scoped_plantilla(db: Session, user: models.User, plantilla_id: str):
    """Recurso PlantillaMensaje: sede_id propio. Devuelve 404 si no está en
    el scope del usuario. Retorna el ORM object para los CRUD existentes.
    """
    from backend.crud.crm_.resources import get_plantilla
    obj = get_plantilla(db, plantilla_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    user_sede = get_user_sede_id(db, user.id)
    if user_sede and str(obj.sede_id) != str(user_sede):
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return obj


def _get_scoped_automation(db: Session, user: models.User, automation_id) -> models.CrmAutomation:
    """CrmAutomation sin sede_id propio: el scope se aplica indirectamente
    vía la plantilla referenciada en action_payload. Si la automatización
    referencia una plantilla de otra sede, se considera fuera de scope.
    """
    from backend.crud.crm_.extended import get_crm_automation
    try:
        auto_uuid = _to_uuid(automation_id) if not isinstance(automation_id, UUID) else automation_id
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Automatización no encontrada")
    auto = get_crm_automation(db, auto_uuid)
    if not auto:
        raise HTTPException(status_code=404, detail="Automatización no encontrada")
    user_sede = get_user_sede_id(db, user.id)
    if user_sede:
        from backend.crud.crm_.resources import get_plantilla as _get_plantilla
        ap = auto.action_payload or {}
        plantilla_id = ap.get("plantilla_id")
        if plantilla_id:
            plantilla = _get_plantilla(db, plantilla_id)
            if plantilla and str(plantilla.sede_id) != str(user_sede):
                raise HTTPException(status_code=404, detail="Automatización no encontrada")
    return auto


def _get_scoped_task(db: Session, user: models.User, task_id) -> models.TareaCRM:
    """Axioma 3 — Multi-Tenant: una tarea CRM está en scope si AL MENOS
    UNA de sus anclas (CasoCRM.caso_id, Persona.persona_id, Persona.asignado_a_id)
    pertenece a la sede del usuario.

    Política OR-based (misma que `_get_scoped_family`): basta que CUALQUIER FK
    esté en scope para autorizar el acceso. Esto evita over-scoping donde
    una tarea legítimamente "tropical" (caso de sede_a asignado temporalmente
    a un pastor de sede_b) quede falsamente fuera de scope.

    TareaCRM NO tiene columna sede_id propia (backend/models_crm_pipeline.py);
    el scope se aplica indirectamente por la unión de FKs. Patrón DRY para
    retrieval usado por `get_crm_task_detail` y `update_crm_task`.

    Retorna 404 (no 403) para evitar existence-leaks cross-sede.

    Edge cases:
      - Tarea sin ninguna FK (huérfana): sólo visible a superadmin sin sede.
        create_crm_task siempre pre-assigna el editor como asignado_a_id,
        por lo que la creación normal garantiza scope. Tasks huérfanas
        creadas por scripts/no-API son out-of-scope para editores.
      - Superadmin sin sede asignada: ve TODO lo no-borrado.
    """
    from backend.crud._utils import _to_uuid
    try:
        task_uuid = _to_uuid(task_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Task not found")

    task = (
        db.query(models.TareaCRM)
        .filter(
            models.TareaCRM.id == task_uuid,
            models.TareaCRM.deleted_at.is_(None),
        )
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    user_sede = get_user_sede_id(db, user.id)
    if not user_sede:
        # Superadmin sin sede: ve todo lo no borrado.
        return task

    # 1. Scope via caso_id → CasoCRM.sede_id
    if task.caso_id is not None:
        from backend.models_crm_pipeline import CasoCRM
        caso = db.query(CasoCRM).filter(CasoCRM.id == task.caso_id).first()
        if caso and str(caso.sede_id) == str(user_sede):
            return task

    # 2. Scope via persona_id (target persona)
    if task.persona_id is not None:
        persona = persona_query(db).filter(models.Persona.id == task.persona_id).first()
        if persona and persona.sede_id and str(persona.sede_id) == str(user_sede):
            return task

    # 3. Scope via asignado_a_id (assignee)
    if task.asignado_a_id is not None:
        assignee = persona_query(db).filter(models.Persona.id == task.asignado_a_id).first()
        if assignee and assignee.sede_id and str(assignee.sede_id) == str(user_sede):
            return task

    # Ningún FK ancló a la sede del caller → 404 (existence-leak-safe).
    raise HTTPException(status_code=404, detail="Task not found")


def _resolve_assignee_for_task(
    db: Session, current_user: models.User, raw_assignee_id
):
    """Valida ``assignee_id`` como UUID canónico de persona y aplica scope.

    Raises 404 (no 403, para evitar existence-leaks) si:
      - El input no es UUID.
      - La persona resuelta es cross-sede o INACTIVA.

    Retorna ``None`` cuando el payload omite ``assignee_id``.
    """
    if not raw_assignee_id:
        return None
    raw_str = str(raw_assignee_id).strip()
    if not raw_str:
        return None
    # 1. Intentar como UUID de persona
    try:
        persona_uuid = _uuid.UUID(raw_str)
    except (TypeError, ValueError):
        persona_uuid = None
    if persona_uuid:
        return _get_scoped_persona(db, current_user, persona_uuid).id
    raise HTTPException(status_code=404, detail="Assignee no encontrado")


def _serialize_persona_position(persona_position: models.PersonaPosition) -> dict:
    position = persona_position.position
    return {
        "id": persona_position.id,
        "persona_id": persona_position.persona_id,
        "position_id": persona_position.position_id,
        "position_name": position.name if position else None,
        "category": position.category if position else None,
        "start_date": (
            persona_position.start_date.isoformat()
            if persona_position.start_date
            else None
        ),
        "end_date": (
            persona_position.end_date.isoformat() if persona_position.end_date else None
        ),
        "is_active": persona_position.is_active,
        "notes": persona_position.notes,
        "created_at": (
            persona_position.created_at.isoformat()
            if persona_position.created_at
            else None
        ),
    }


def _enum_value(value):
    return getattr(value, "value", value)


def _case_stage(case: models.CasoCRM) -> str:
    stage = getattr(case, "stage", None)
    if stage:
        return str(stage)
    payload = getattr(case, "payload_web", None) if isinstance(getattr(case, "payload_web", None), dict) else {}
    stage_key = _payload_key("stage")
    if payload.get(stage_key):
        return str(payload[stage_key])

    etapa = getattr(case, "etapa_actual", None)
    etapa_name = str(getattr(etapa, "nombre", "") or "").strip().lower()
    if "llamar" in etapa_name or "contact" in etapa_name:
        return "call"
    if "visit" in etapa_name or "visita" in etapa_name:
        return "visit"
    if "discip" in etapa_name or "proceso" in etapa_name:
        return "discipleship"
    if "consolid" in etapa_name or "integr" in etapa_name:
        return "consolidated"

    estado = str(_enum_value(getattr(case, "estado", "")) or "").upper()
    if estado in {"RESUELTO_EXITO"}:
        return "consolidated"
    if estado in {"CERRADO_PERDIDO"}:
        return "lost"
    if estado in {"EN_PROGRESO"}:
        return "discipleship"
    if estado in {"ESPERANDO_RESPUESTA"}:
        return "call"
    return "new"


def _case_status(case: models.CasoCRM) -> str:
    status = getattr(case, "status", None)
    if status:
        return str(status)
    estado = str(_enum_value(getattr(case, "estado", "")) or "").upper()
    return "closed" if estado in {"RESUELTO_EXITO", "CERRADO_PERDIDO"} else "active"


def _serialize_case(case: models.CasoCRM) -> dict:
    persona = getattr(case, "persona", None)
    assigned = getattr(case, "assigned_pastor", None) or getattr(case, "asignado_a", None)
    assigned_leader = getattr(case, "assigned_leader", None)
    payload = getattr(case, "payload_web", None) if isinstance(getattr(case, "payload_web", None), dict) else {}
    created_at = getattr(case, "created_at", None) or getattr(case, "fecha_creacion", None)
    updated_at = getattr(case, "updated_at", None) or getattr(case, "fecha_creacion", None)
    last_contact_at = getattr(case, "last_contact_at", None) or payload.get(_payload_key("last_contact_at"))
    next_contact_at = (
        getattr(case, "next_contact_at", None)
        or payload.get(_payload_key("next_contact_at"))
        or getattr(case, "sla_vencimiento_contacto", None)
    )
    source = getattr(case, "source", None) or payload.get(_payload_key("source")) or _enum_value(getattr(case, "origen_canal", None))
    return {
        "id": str(case.id),
        "persona_id": str(case.persona_id) if case.persona_id else None,
        "nombre_completo": persona.nombre_completo if persona else "",
        "telefono": (
            getattr(persona, "telefono", None)
            or getattr(persona, "phone", None)
            or getattr(persona, "mobile_phone", None)
            if persona
            else None
        ),
        "stage": _case_stage(case),
        "status": _case_status(case),
        "source": source,
        "last_contact_at": (
            last_contact_at.isoformat() if hasattr(last_contact_at, "isoformat") else last_contact_at
        ),
        "next_contact_at": (
            next_contact_at.isoformat() if hasattr(next_contact_at, "isoformat") else next_contact_at
        ),
        "assigned_pastor": (
            {
                "id": assigned.id,
                "nombre_completo": assigned.nombre_completo,
            }
            if assigned
            else None
        ),
        "assigned_leader": (
            {
                "id": assigned_leader.id,
                "nombre_completo": assigned_leader.nombre_completo,
            }
            if assigned_leader
            else None
        ),
        "assignments_count": len(getattr(case, "assignments", []) or []),
        "interactions_count": len(
            getattr(case, "interactions", None)
            or getattr(case, "interacciones", [])
            or []
        ),
        "open_tasks_count": sum(
            1
            for task in (getattr(case, "tasks", None) or getattr(case, "tareas", []) or [])
            if not getattr(task, "completada", False)
        ),
        "notes": getattr(case, "notes", None) or payload.get(_payload_key("notes")) or payload,
        "sort_order": getattr(case, "sort_order", 0),
        "created_at": created_at.isoformat() if created_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }


def _persona_full_name(persona: models.Persona | None) -> str:
    if not persona:
        return "Persona"
    return persona.nombre_completo


def _serialize_task(task: models.TareaCRM) -> dict:
    assignee = getattr(task, "assignee", None)
    persona = getattr(task, "persona", None)
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "category": task.category,
        "persona_id": task.persona_id,
        "persona_name": _persona_full_name(persona) if persona else None,
        "contact_name": _persona_full_name(persona) if persona else None,
        "assigned_to": assignee.nombre_completo if assignee else None,
        "assignee_id": str(task.assignee_id) if task.assignee_id else None,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


def _serialize_message_group(logs: list[models.CommunicationLog]) -> dict:
    logs = sorted(logs, key=lambda item: item.created_at or datetime.min, reverse=True)
    first = logs[0]
    delivered_count = sum(
        1 for item in logs if (item.outcome or "").lower() in DELIVERED_OUTCOMES
    )
    failed_count = sum(1 for item in logs if (item.outcome or "").lower() == "failed")
    target_count = len(logs)
    persona_name = (
        _persona_full_name(first.persona) if getattr(first, "persona", None) else None
    )
    campaign_name = first.campaign_name
    return {
        "id": first.id,
        "name": (
            campaign_name or f"Mensaje a {persona_name}" if persona_name else "Mensaje"
        ),
        "channel": (first.channel or "").lower(),
        "status": (first.outcome or CommunicationOutcome.INTERNAL_LOG.value).lower(),
        "target_count": target_count,
        "delivered_count": delivered_count,
        "failed_count": failed_count,
        "sent_at": first.created_at.isoformat() if first.created_at else None,
        "campaign_name": campaign_name,
        "persona_name": persona_name,
        "content": first.content or "",
        "recipient_phone": first.recipient_phone,
        "external_id": first.external_id,
        "log_ids": [item.id for item in logs],
    }


def _persona_matches_segment(persona, segment: str, donation_persona_ids: set) -> bool:
    value = str(segment or "").strip().lower()
    if value == "active":
        return str(persona.church_role or "").strip().lower() in {
            "miembro", "servidor", "lider", "lider", "pastor", "coordinador",
        }
    if value == "new":
        return str(persona.spiritual_status or "").strip().lower() == "nuevo"
    if value == "staff":
        return str(persona.church_role or "").strip().lower() in {
            "pastor", "coordinador", "staff", "administrador", "admin",
        }
    if value == "groups":
        return persona.family_id is not None
    if value == "low":
        return str(persona.spiritual_status or "").strip().lower() in {
            "nuevo", "creyente",
        }
    if value == "vip":
        return persona.id in donation_persona_ids
    return False


def _resolve_campaign_personas(db, segments: list, sede_id=None) -> list:
    normalized_segments = [s for s in (seg.strip().lower() for seg in segments) if s]
    if not normalized_segments:
        return []

    donations_q = db.query(models.Donation.persona_id).filter(models.Donation.persona_id.isnot(None))
    if sede_id:
        donations_q = donations_q.filter(models.Donation.sede_id == sede_id)
    donation_persona_ids = {pid for (pid,) in donations_q.distinct().all()}
    personas_q = persona_query(db)
    if sede_id:
        personas_q = personas_q.filter(models.Persona.sede_id == sede_id)
    personas = personas_q.all()
    selected = []
    seen_ids: set = set()
    for persona in personas:
        persona = prepare_persona_for_output(db, persona)
        if persona.id in seen_ids:
            continue
        if any(_persona_matches_segment(persona, segment, donation_persona_ids) for segment in normalized_segments):
            selected.append(persona)
            seen_ids.add(persona.id)
    return selected
