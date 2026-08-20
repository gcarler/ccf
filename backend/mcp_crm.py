"""MCP privado para la operación CRM de CCF.

Las herramientas llaman a handlers/CRUD existentes cuando existe un contrato
canónico; las consultas directas mantienen las mismas fronteras de sede y no
exponen campos pastorales o médicos por defecto.
"""

from __future__ import annotations

import datetime
from typing import Any
from uuid import UUID

from mcp.server.fastmcp import FastMCP
from sqlalchemy import or_

from backend import crud, models, schemas
from backend.api.crm import pastoral as crm_pastoral
from backend.api.crm import personas as crm_personas
from backend.api.crm import pipelines as crm_pipelines
from backend.api.crm._shared import _get_scoped_persona
from backend.api.evangelism_events import events_participantes
from backend.core.audit import record_admin_action
from backend.core.cache_v2 import _to_jsonable
from backend.core.database import SessionLocal
from backend.core.tenant import require_user_sede_id
from backend.mcp_auth import (
    authenticated_mcp_app,
    get_mcp_current_user,
    require_mcp_permission,
)

crm_mcp = FastMCP(
    name="CCF CRM",
    instructions=(
        "Opera el CRM de la sede del usuario autenticado. Usa personas.id como "
        "identidad canónica, respeta los permisos CRM y no expongas notas "
        "pastorales, médicas o de consejería sensible salvo una herramienta "
        "explícita con permiso adicional."
    ),
    streamable_http_path="/",
    stateless_http=True,
)


def _call(operation, db, user, *args, **kwargs):
    return operation(*args, db=db, current_user=user, **kwargs)


def _parse_event_datetime(value: str | None) -> datetime.datetime | None:
    if value is None or not str(value).strip():
        return None
    try:
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Fecha inválida; use ISO-8601") from exc


def _safe_event(event: models.CrmEvent) -> dict[str, Any]:
    return {
        "event_id": str(event.id),
        "name": event.name,
        "description": event.description,
        "event_type": event.event_type,
        "target_audience": event.target_audience,
        "event_date": event.event_date.isoformat() if event.event_date else None,
        "location": event.location,
        "status": event.status,
        "cancellation_reason": event.cancellation_reason,
        "requires_registration": bool(event.requires_registration),
        "attendance_closed_at": event.attendance_closed_at.isoformat() if event.attendance_closed_at else None,
        "sede_id": str(event.sede_id) if event.sede_id else None,
    }


def _resolve_crm_event(db, user: models.Usuario, event_id: UUID) -> models.CrmEvent:
    sede_id = require_user_sede_id(db, user)
    event = (
        db.query(models.CrmEvent)
        .filter(
            models.CrmEvent.id == event_id,
            models.CrmEvent.sede_id == sede_id,
            models.CrmEvent.deleted_at.is_(None),
        )
        .first()
    )
    if not event:
        raise ValueError("Evento CRM no encontrado")
    return event


@crm_mcp.tool()
def list_crm_events(
    status: str | None = None,
    event_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Lista eventos CRM activos de la sede del usuario."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:read")
        sede_id = require_user_sede_id(db, user)
        query = db.query(models.CrmEvent).filter(
            models.CrmEvent.sede_id == sede_id,
            models.CrmEvent.deleted_at.is_(None),
        )
        if status:
            query = query.filter(models.CrmEvent.status == status)
        if event_type:
            query = query.filter(models.CrmEvent.event_type == event_type)
        total = query.count()
        events = (
            query.order_by(models.CrmEvent.event_date.desc().nullslast())
            .offset(max(0, int(offset)))
            .limit(max(1, min(int(limit), 200)))
            .all()
        )
        return {"items": [_safe_event(event) for event in events], "total": total}
    finally:
        db.close()


@crm_mcp.tool()
def get_crm_event(event_id: UUID) -> dict[str, Any]:
    """Obtiene un evento CRM dentro de la sede del usuario."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:read")
        return _safe_event(_resolve_crm_event(db, user, event_id))
    finally:
        db.close()


@crm_mcp.tool()
def create_crm_event(
    name: str,
    event_type: str = "ONCE",
    event_date: str | None = None,
    description: str | None = None,
    location: str | None = None,
    target_audience: str = "ALL",
) -> dict[str, Any]:
    """Crea un evento CRM en la sede y deja registro de auditoría."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:manage")
        sede_id = require_user_sede_id(db, user)
        payload = schemas.CrmEventCreate(
            name=name,
            event_type=event_type,
            target_audience=target_audience,
            event_date=_parse_event_datetime(event_date),
            description=description,
            location=location,
        )
        event = crud.create_crm_event(db, payload)
        event.sede_id = sede_id
        db.commit()
        db.refresh(event)
        record_admin_action(
            db,
            user,
            action="create_event_mcp",
            resource_type="crm_event",
            resource_id=str(event.id),
            metadata={"source": "mcp"},
        )
        return _safe_event(event)
    finally:
        db.close()


@crm_mcp.tool()
def update_crm_event(event_id: UUID, changes: dict[str, Any]) -> dict[str, Any]:
    """Actualiza campos operativos permitidos de un evento CRM."""
    allowed = {
        "name",
        "description",
        "event_type",
        "target_audience",
        "event_date",
        "location",
        "status",
        "cancellation_reason",
    }
    clean = {key: value for key, value in changes.items() if key in allowed}
    if "event_date" in clean:
        clean["event_date"] = _parse_event_datetime(clean["event_date"])
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:manage")
        event = _resolve_crm_event(db, user, event_id)
        for key, value in clean.items():
            setattr(event, key, value)
        db.commit()
        db.refresh(event)
        record_admin_action(
            db,
            user,
            action="update_event_mcp",
            resource_type="crm_event",
            resource_id=str(event.id),
            metadata={"fields": sorted(clean), "source": "mcp"},
        )
        return _safe_event(event)
    finally:
        db.close()


@crm_mcp.tool()
def archive_crm_event(event_id: UUID) -> dict[str, Any]:
    """Archiva un evento CRM sin eliminarlo físicamente."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:manage")
        event = _resolve_crm_event(db, user, event_id)
        event.status = "CANCELLED"
        event.cancellation_reason = "Archivado por MCP"
        event.deleted_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        record_admin_action(
            db,
            user,
            action="archive_event_mcp",
            resource_type="crm_event",
            resource_id=str(event.id),
            metadata={"source": "mcp"},
        )
        return {"status": "archived", "event_id": str(event.id)}
    finally:
        db.close()


@crm_mcp.tool()
def get_crm_event_attendance(
    event_id: UUID,
    session_date: datetime.date | None = None,
) -> dict[str, Any]:
    """Consulta la asistencia de un evento CRM, opcionalmente por fecha."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:read")
        event = _resolve_crm_event(db, user, event_id)
        query = db.query(models.EventAttendance).filter(
            models.EventAttendance.event_id == event.id,
            models.EventAttendance.deleted_at.is_(None),
        )
        if session_date is not None:
            query = query.filter(models.EventAttendance.session_date == session_date)
        rows = query.join(models.Persona).order_by(models.Persona.nombre_completo.asc()).all()
        present = []
        absent = []
        for row in rows:
            item = {
                "persona_id": str(row.persona_id),
                "name": row.persona.nombre_completo if row.persona else "Sin nombre",
                "session_date": row.session_date.isoformat(),
                "status": "present" if row.attended else "absent",
                "source": row.source,
            }
            (present if row.attended else absent).append(item)
        return {
            "event": _safe_event(event),
            "session_date": session_date.isoformat() if session_date else None,
            "counts": {"present": len(present), "absent": len(absent)},
            "present": present,
            "absent": absent,
        }
    finally:
        db.close()


@crm_mcp.tool()
def register_crm_event_attendance(
    event_id: UUID,
    session_date: datetime.date,
    persona_ids: list[UUID],
    allow_empty: bool = False,
) -> dict[str, Any]:
    """Sincroniza asistencia de un evento CRM sin cruzar sedes."""
    if not persona_ids and not allow_empty:
        raise ValueError("persona_ids está vacío; confirme allow_empty=true para marcar todos ausentes")
    if len(persona_ids) > 2000:
        raise ValueError("El máximo permitido por operación MCP es 2000 personas")
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:edit")
        event = _resolve_crm_event(db, user, event_id)
        selected_ids = list(dict.fromkeys(persona_ids))
        valid_ids = {
            row[0]
            for row in db.query(models.Persona.id)
            .filter(
                models.Persona.id.in_(selected_ids),
                models.Persona.sede_id == event.sede_id,
            )
            .all()
        }
        invalid_ids = sorted(str(persona_id) for persona_id in set(selected_ids) - valid_ids)
        if invalid_ids:
            return {
                "status": "rejected",
                "reason": "Hay personas inexistentes o fuera de la sede del evento",
                "invalid_persona_ids": invalid_ids,
                "recorded": 0,
            }
        result = events_participantes.register_bulk_attendance(
            payload={
                "event_id": str(event_id),
                "session_date": session_date.isoformat(),
                "persona_ids": [str(persona_id) for persona_id in selected_ids],
                "source": "mcp",
            },
            db=db,
            current_user=user,
        )
        return result
    finally:
        db.close()


def _safe_person(person: models.Persona) -> dict[str, Any]:
    return {
        "persona_id": str(person.id),
        "first_name": person.first_name,
        "last_name": person.last_name,
        "name": person.nombre_completo,
        "email": person.email,
        "phone": person.phone,
        "church_role": person.church_role,
        "spiritual_status": person.spiritual_status,
        "estado_vital": person.estado_vital,
        "sede_id": str(person.sede_id) if person.sede_id else None,
    }


def _safe_case(case: models.CasoCRM) -> dict[str, Any]:
    persona = getattr(case, "persona", None)
    return {
        "case_id": str(case.id),
        "persona_id": str(case.persona_id),
        "persona_name": persona.nombre_completo if persona else None,
        "title": case.titulo_caso,
        "priority": getattr(case.prioridad, "value", case.prioridad),
        "status": getattr(case.estado, "value", case.estado),
        "source": getattr(case.origen_canal, "value", case.origen_canal),
        "pipeline_id": str(case.pipeline_id) if case.pipeline_id else None,
        "stage_id": str(case.etapa_actual_id) if case.etapa_actual_id else None,
        "assignee_id": str(case.asignado_a_id) if case.asignado_a_id else None,
        "created_at": case.fecha_creacion.isoformat() if case.fecha_creacion else None,
        "is_overdue": bool(case.is_overdue),
    }


def _safe_pipeline(row: models.PipelineCRM) -> dict[str, Any]:
    return {
        "pipeline_id": str(row.id),
        "name": row.nombre,
        "type": getattr(row.tipo, "value", row.tipo),
        "description": row.descripcion,
        "is_active": row.activo,
        "sede_id": str(row.sede_id),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _safe_stage(row: models.EtapaPipeline) -> dict[str, Any]:
    return {
        "stage_id": str(row.id),
        "pipeline_id": str(row.pipeline_id),
        "name": row.nombre,
        "order_index": row.orden,
        "requires_action": row.requiere_accion,
    }


@crm_mcp.tool()
def search_crm_people(query: str | None = None, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    """Busca personas activas de la sede por nombre, correo o teléfono."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:read")
        sede_id = require_user_sede_id(db, user)
        q = db.query(models.Persona).filter(
            models.Persona.sede_id == sede_id,
            models.Persona.estado_vital != "INACTIVO",
        )
        term = (query or "").strip()
        if term:
            pattern = f"%{term}%"
            q = q.filter(
                or_(
                    models.Persona.first_name.ilike(pattern),
                    models.Persona.last_name.ilike(pattern),
                    models.Persona.email.ilike(pattern),
                    models.Persona.phone.ilike(pattern),
                    models.Persona.nombre_completo.ilike(pattern),
                )
            )
        total = q.count()
        people = (
            q.order_by(models.Persona.nombre_completo.asc())
            .offset(max(0, int(offset)))
            .limit(max(1, min(int(limit), 200)))
            .all()
        )
        return {"items": [_safe_person(person) for person in people], "total": total}
    finally:
        db.close()


@crm_mcp.tool()
def get_crm_person(persona_id: UUID) -> dict[str, Any]:
    """Obtiene el perfil CRM no sensible de una persona de la sede."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:read")
        return _safe_person(_get_scoped_persona(db, user, persona_id))
    finally:
        db.close()


@crm_mcp.tool()
def create_crm_person(
    first_name: str,
    last_name: str,
    email: str | None = None,
    phone: str | None = None,
    church_role: str = "Miembro",
    spiritual_status: str | None = None,
) -> dict[str, Any]:
    """Crea una persona en la sede del usuario, evitando duplicados."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:edit")
        payload = schemas.PersonaCreate(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            church_role=church_role,
            spiritual_status=spiritual_status,
        )
        person = _call(crm_personas.create_persona, db, user, payload)
        return _safe_person(person)
    finally:
        db.close()


@crm_mcp.tool()
def update_crm_person(persona_id: UUID, changes: dict[str, Any]) -> dict[str, Any]:
    """Actualiza campos CRM permitidos de una persona de la sede."""
    allowed = {
        "first_name",
        "last_name",
        "email",
        "phone",
        "church_role",
        "spiritual_status",
        "estado_vital",
        "birthday",
        "city",
        "address",
    }
    clean = {key: value for key, value in changes.items() if key in allowed}
    if "birthday" in clean and isinstance(clean["birthday"], str):
        clean["birthday"] = datetime.date.fromisoformat(clean["birthday"][:10])
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:edit")
        _get_scoped_persona(db, user, persona_id)
        person = _call(
            crm_personas.update_persona,
            db,
            user,
            str(persona_id),
            payload=schemas.PersonaUpdate(**clean),
        )
        return _safe_person(person)
    finally:
        db.close()


@crm_mcp.tool()
def archive_crm_person(persona_id: UUID) -> dict[str, Any]:
    """Archiva lógicamente una persona; nunca la elimina físicamente."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:edit")
        _get_scoped_persona(db, user, persona_id)
        _call(crm_personas.delete_persona, db, user, str(persona_id))
        return {"status": "archived", "persona_id": str(persona_id)}
    finally:
        db.close()


@crm_mcp.tool()
def list_crm_cases(
    status: str | None = None,
    source: str | None = None,
    persona_id: UUID | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    """Lista casos CRM de la sede con filtros y paginación."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:read")
        result = _call(
            crm_pastoral.list_crm_casos,
            db,
            user,
            source=source,
            stage=None,
            status=status,
            persona_id=str(persona_id) if persona_id else None,
            page=max(1, int(page)),
            page_size=max(1, min(int(page_size), 200)),
        )
        return _to_jsonable(result)
    finally:
        db.close()


@crm_mcp.tool()
def get_crm_case(case_id: UUID) -> dict[str, Any]:
    """Obtiene un caso CRM dentro de la sede."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:read")
        case = _call(crm_pastoral.get_caso_crm, db, user, str(case_id))
        return _to_jsonable(case)
    finally:
        db.close()


@crm_mcp.tool()
def create_crm_case(
    persona_id: UUID,
    title: str | None = None,
    stage: str = "new",
    source: str = "DERIVACION_INTERNA",
    notes: str | None = None,
) -> dict[str, Any]:
    """Crea un caso de consolidación para una persona de la sede."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:edit")
        _get_scoped_persona(db, user, persona_id)
        payload = schemas.CasoCreate(
            persona_id=persona_id,
            stage=stage,
            source=source,
            notes=notes or title,
        )
        return _to_jsonable(_call(crm_pastoral.create_caso_crm, db, user, payload=payload))
    finally:
        db.close()


@crm_mcp.tool()
def update_crm_case(case_id: UUID, changes: dict[str, Any]) -> dict[str, Any]:
    """Actualiza estado, etapa, origen, asignación o notas de un caso."""
    allowed = {
        "stage",
        "status",
        "source",
        "source_campaign",
        "last_contact_at",
        "next_contact_at",
        "assigned_pastor_id",
        "assigned_leader_id",
        "notes",
    }
    clean = {key: value for key, value in changes.items() if key in allowed}
    for field in ("last_contact_at", "next_contact_at"):
        if isinstance(clean.get(field), str):
            clean[field] = datetime.datetime.fromisoformat(clean[field].replace("Z", "+00:00"))
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:edit")
        payload = schemas.CaseUpdate(**clean)
        return _to_jsonable(_call(crm_pastoral.update_caso_crm, db, user, str(case_id), payload=payload))
    finally:
        db.close()


@crm_mcp.tool()
def archive_crm_case(case_id: UUID) -> dict[str, Any]:
    """Archiva lógicamente un caso CRM."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:edit")
        _call(crm_pastoral.delete_caso_crm, db, user, str(case_id))
        return {"status": "archived", "case_id": str(case_id)}
    finally:
        db.close()


@crm_mcp.tool()
def add_crm_case_interaction(
    case_id: UUID,
    interaction_type: str,
    notes: str | None = None,
    result: str | None = None,
    interaction_date: str | None = None,
) -> dict[str, Any]:
    """Registra una interacción en la bitácora del caso CRM."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:edit")
        payload = schemas.CaseInteractionCreate(
            interaction_type=interaction_type,
            notes=notes,
            result=result,
            interaction_date=(
                datetime.datetime.fromisoformat(interaction_date.replace("Z", "+00:00"))
                if interaction_date
                else None
            ),
        )
        return _to_jsonable(
            _call(crm_pastoral.create_caso_interaction, db, user, str(case_id), payload=payload)
        )
    finally:
        db.close()


@crm_mcp.tool()
def add_crm_case_task(
    case_id: UUID,
    title: str,
    description: str | None = None,
    due_date: str | None = None,
    status: str = "pending",
) -> dict[str, Any]:
    """Crea una tarea de seguimiento asociada a un caso CRM."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:edit")
        payload = schemas.CaseTaskCreate(
            title=title,
            description=description,
            due_date=(datetime.datetime.fromisoformat(due_date.replace("Z", "+00:00")) if due_date else None),
            status=status,
        )
        return _to_jsonable(_call(crm_pastoral.create_caso_task, db, user, str(case_id), payload=payload))
    finally:
        db.close()


@crm_mcp.tool()
def list_crm_tasks(
    assignee_persona_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Lista tareas CRM visibles en la sede."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:read")
        return _to_jsonable(
            _call(
                crm_pastoral.list_crm_tasks,
                db,
                user,
                assignee_persona_id=assignee_persona_id,
                skip=max(0, int(offset)),
                limit=max(1, min(int(limit), 200)),
            )
        )
    finally:
        db.close()


@crm_mcp.tool()
def update_crm_task(task_id: UUID, changes: dict[str, Any]) -> dict[str, Any]:
    """Actualiza una tarea CRM respetando catálogo de estado/prioridad y scope."""
    clean = {key: value for key, value in changes.items() if key in {
        "title", "description", "status", "priority", "due_date", "completed_at", "persona_id", "assignee_id", "caso_id"
    }}
    for field in ("due_date", "completed_at"):
        if isinstance(clean.get(field), str):
            clean[field] = datetime.datetime.fromisoformat(clean[field].replace("Z", "+00:00"))
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:edit")
        result = _call(
            crm_pastoral.update_crm_task,
            db,
            user,
            task_id,
            payload=schemas.CrmTaskUpdate(**clean),
        )
        return _to_jsonable(result)
    finally:
        db.close()


@crm_mcp.tool()
def list_crm_pipelines() -> dict[str, Any]:
    """Lista pipelines CRM activos de la sede."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:read")
        sede_id = UUID(str(require_user_sede_id(db, user)))
        rows = crm_pipelines.crm_pipeline.list_pipelines(db, sede_id)
        return {"items": [_safe_pipeline(row) for row in rows], "count": len(rows)}
    finally:
        db.close()


@crm_mcp.tool()
def create_crm_pipeline(name: str, pipeline_type: str, description: str | None = None) -> dict[str, Any]:
    """Crea un pipeline CRM para la sede."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:manage")
        require_user_sede_id(db, user)
        payload = schemas.PipelineCreate(name=name, pipeline_type=pipeline_type, description=description)
        row = _call(crm_pipelines.create_pipeline, db, user, payload=payload)
        return _to_jsonable(row)
    finally:
        db.close()


@crm_mcp.tool()
def list_crm_pipeline_stages(pipeline_id: UUID) -> dict[str, Any]:
    """Lista etapas de un pipeline CRM de la sede."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:read")
        rows = _call(crm_pipelines.list_pipeline_stages, db, user, pipeline_id)
        return {"items": [_to_jsonable(row) for row in rows], "count": len(rows)}
    finally:
        db.close()


@crm_mcp.tool()
def create_crm_pipeline_stage(
    pipeline_id: UUID,
    name: str,
    order_index: int,
    requires_action: bool = True,
) -> dict[str, Any]:
    """Crea una etapa dentro de un pipeline CRM de la sede."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:manage")
        payload = schemas.PipelineStageCreate(
            pipeline_id=pipeline_id,
            name=name,
            order_index=max(0, int(order_index)),
            requires_action=requires_action,
        )
        return _to_jsonable(_call(crm_pipelines.create_pipeline_stage, db, user, pipeline_id, payload=payload))
    finally:
        db.close()


@crm_mcp.tool()
def create_crm_automation_flow(name: str, is_active: bool = True) -> dict[str, Any]:
    """Crea un flujo de automatización CRM atribuido a la sede del usuario."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:manage")
        return _to_jsonable(_call(crm_pipelines.automations_flows, db, user, payload={"name": name, "is_active": is_active}))
    finally:
        db.close()


@crm_mcp.tool()
def validate_crm_automation_graph(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    """Valida ciclos y consistencia básica de un grafo de automatización CRM."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "crm:edit")
        payload = {"nodes": nodes, "edges": edges}
        return _to_jsonable(_call(crm_pipelines.flows_validate, db, user, payload=payload))
    finally:
        db.close()


crm_mcp_app = authenticated_mcp_app(crm_mcp)
