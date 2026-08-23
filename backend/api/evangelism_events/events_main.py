from __future__ import annotations

import calendar
import collections
import csv
import datetime
import io
import math
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, model_validator
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.evangelism_events._shared import (
    require_event_access,
)
from backend.api.evangelism_shared import (
    get_expected_personas_for_event,
    normalize_role_scope_payload,
    utc_now,
)
from backend.core.audit import record_admin_action
from backend.core.database import get_db
from backend.core.permissions import (
    require_evangelism_manage,
    require_evangelism_read,
)
from backend.core.tenant import require_user_sede_id

router = APIRouter()
static_router = APIRouter()
dynamic_router = APIRouter()


class RoleDefinitionCreate(BaseModel):
    name: str
    color: str
    is_leadership: bool


class RoleDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    is_leadership: Optional[bool] = None


class EventAudienceUpdate(BaseModel):
    target_audience: schemas.EventAudienceType
    target_role_id: Optional[UUID] = None
    target_role_ids: Optional[List[UUID]] = None
    target_persona_ids: Optional[List[str]] = None

    @model_validator(mode="after")
    def _validate_audience(self):
        if self.target_audience == "ROLE" and not self.target_role_id and not self.target_role_ids:
            raise ValueError("target_role_id or target_role_ids required when target_audience is ROLE")
        return self


def _active_events_query(db: Session):
    return db.query(models.CrmEvent).filter(models.CrmEvent.deleted_at.is_(None))


@static_router.get("/events/", response_model=List[schemas.CrmEvent])
def list_events(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    user_sede = require_user_sede_id(db, current_user)
    events = (
        _active_events_query(db)
        .filter((models.CrmEvent.sede_id == user_sede) | models.CrmEvent.sede_id.is_(None))
        .order_by(models.CrmEvent.event_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    # Pydantic v2 validation del response_model implica que cada elemento
    # debe ser dict; convertimos cada ORM CrmEvent a dict compatible con
    # el schema (preserva contrato y evita response model orm-only errores).
    return [schemas.CrmEvent.model_validate(event).model_dump(mode="json") for event in events]


@static_router.get("/sedes", response_model=List[dict])
def list_event_sedes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    """Lista la sede del usuario + opción global. No expone catálogo completo de sedes."""
    user_sede = require_user_sede_id(db, current_user)
    user_sede_row = (
        db.query(models.Sede)
        .filter(
            models.Sede.id == user_sede,
            models.Sede.es_activa.is_(True),
            models.Sede.deleted_at.is_(None),
        )
        .first()
    )
    result = []
    if user_sede_row:
        result.append({"id": str(user_sede_row.id), "name": user_sede_row.nombre})
    # Opción global (NULL) — visible para todas las sedes
    result.append({"id": "global", "name": "Universo (todas las sedes)"})
    return result


@static_router.get("/events/personas/{event_id}", response_model=List[dict])
def list_event_personas(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    """Lista el universo de personas del evento respetando su alcance."""
    event = require_event_access(db, current_user, event_id)
    people = get_expected_personas_for_event(db, event)
    return [schemas.PersonaResponse.model_validate(person).model_dump(mode="json") for person in people]


def _strategy_event_matches(event: models.CrmEvent, strategy_id: UUID) -> bool:
    settings = event.settings_json if isinstance(event.settings_json, dict) else {}
    return str(settings.get("evangelism_strategy_id") or "") == str(strategy_id)


@static_router.post("/events/strategy/{strategy_id}/ensure", response_model=schemas.CrmEvent)
def ensure_strategy_event(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    """Resolve the event record used by an ``evento_masivo`` strategy.

    Mass strategies do not use groups/sessions.  The existing event attendance
    contract is the canonical store for their attendance, so this endpoint
    creates the event lazily when the operator first opens attendance.
    """
    user_sede = require_user_sede_id(db, current_user)
    strategy = (
        db.query(models.EstrategiaEvangelismo)
        .filter(
            models.EstrategiaEvangelismo.id == strategy_id,
            models.EstrategiaEvangelismo.sede_id == user_sede,
            models.EstrategiaEvangelismo.deleted_at.is_(None),
        )
        .first()
    )
    if not strategy:
        raise HTTPException(status_code=404, detail="Estrategia no encontrada")
    if strategy.typology != "evento_masivo":
        raise HTTPException(status_code=409, detail="La estrategia no es de tipología evento_masivo")

    event = next(
        (
            item
            for item in _active_events_query(db)
            .filter((models.CrmEvent.sede_id == user_sede) | models.CrmEvent.sede_id.is_(None))
            .order_by(models.CrmEvent.event_date.desc())
            .all()
            if _strategy_event_matches(item, strategy_id)
        ),
        None,
    )
    if not event:
        event_date = strategy.fecha_inicio or utc_now()
        event = models.CrmEvent(
            sede_id=None,
            name=strategy.nombre,
            description=strategy.descripcion,
            event_date=event_date,
            fixed_date=event_date,
            event_type="ONCE",
            status="SCHEDULED",
            target_audience="ALL",
            settings_json={
                "evangelism_strategy_id": str(strategy.id),
                "strategy_typology": "evento_masivo",
            },
        )
        db.add(event)
        db.commit()
        db.refresh(event)
    return schemas.CrmEvent.model_validate(event).model_dump(mode="json")


@static_router.post("/events/", response_model=schemas.CrmEvent)
def create_event(
    payload: schemas.CrmEventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    payload = schemas.CrmEventCreate(**normalize_role_scope_payload(payload.model_dump()))
    user_sede = require_user_sede_id(db, current_user)
    event = crud.create_crm_event(db, payload)
    # sede_id del usuario autenticado, NO del cliente. NULL = global requiere rol admin.
    # Un operador de sede A no puede crear eventos en sede B.
    if payload.sede_id is not None and str(payload.sede_id) != str(user_sede):
        raise HTTPException(
            status_code=403,
            detail="No puedes crear eventos para una sede distinta a la tuya.",
        )
    event.sede_id = payload.sede_id if payload.sede_id is not None else user_sede
    db.commit()
    db.refresh(event)
    record_admin_action(
        db,
        current_user,
        action="create_event",
        resource_type="event",
        resource_id=str(event.id),
    )
    # Pydantic v2: response_model exige dicts/None; ORM crudo genera dict_type error.
    return schemas.CrmEvent.model_validate(event).model_dump(mode="json")


@dynamic_router.put("/events/{event_id}", response_model=dict)
def update_event(
    event_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    # NOTA: event_id se mantiene como ``str`` (revertido de UUID constraint)
    # porque los alias paths ``/events/dashboard-stats``, ``/events/roles``
    # se registran DESPUÉS de ``/events/{event_id}`` en este archivo y
    # Pydantic strict con UUID devolvía 422 cuando el dynamic capturaba
    # matches no-UUID antes que las rutas estáticas.
    event = require_event_access(db, current_user, event_id)
    payload = normalize_role_scope_payload(payload)
    editable = [
        "name",
        "description",
        "location",
        "event_type",
        "target_audience",
        "target_role_id",
        "target_role_ids",
        "target_persona_ids",
        "status",
        "cancellation_reason",
        "start_time",
        "end_time",
        "day_of_week",
        "month_day",
        "fixed_date",
    ]
    for field in editable:
        if field in payload:
            val = payload[field]
            if field == "fixed_date" and isinstance(val, str) and val:
                val = datetime.datetime.fromisoformat(val.replace("Z", "+00:00"))
            setattr(event, field, val)
    db.commit()
    db.refresh(event)
    record_admin_action(
        db,
        current_user,
        action="update_event",
        resource_type="event",
        resource_id=str(event.id),
    )
    return {"id": event.id, "name": event.name, "status": "updated"}


@dynamic_router.delete("/events/{event_id}", response_model=dict)
def delete_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    """Cancela un evento (soft-delete: marca como CANCELLED + deleted_at)."""
    event = require_event_access(db, current_user, event_id)
    event.status = "CANCELLED"
    event.cancellation_reason = "Eliminado por usuario"
    event.deleted_at = utc_now()
    db.commit()
    record_admin_action(
        db,
        current_user,
        action="cancel_event",
        resource_type="event",
        resource_id=str(event_id),
    )
    return {"status": "cancelled", "id": event_id}


@dynamic_router.get("/events/{event_id}", response_model=dict)
def get_event_detail(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    event = require_event_access(db, current_user, event_id)

    attendees_count = db.query(models.EventAttendance).filter(models.EventAttendance.event_id == event_id).count()
    event_status = event.status or "SCHEDULED"
    if event_status == "SCHEDULED" and event.event_date:
        event_date = event.event_date
        now = utc_now()
        if getattr(event_date, "tzinfo", None) is None:
            event_date = event_date.replace(tzinfo=now.tzinfo)
        if event_date < now:
            event_status = "COMPLETED"

    return {
        "id": event.id,
        "name": event.name,
        "title": event.name,
        "description": event.description,
        "event_date": event.event_date.isoformat() if event.event_date else None,
        "location": event.location,
        "attendees_count": attendees_count,
        "status": event_status,
        "cancellation_reason": event.cancellation_reason,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


@dynamic_router.put("/events/{event_id}/audience")
def update_event_audience(
    event_id: str,
    payload: EventAudienceUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    event = require_event_access(db, current_user, event_id)

    normalized = normalize_role_scope_payload(payload.model_dump())
    event.target_audience = normalized["target_audience"]
    event.target_role_id = normalized.get("target_role_id")
    event.target_role_ids = normalized.get("target_role_ids")
    event.target_persona_ids = normalized.get("target_persona_ids")
    db.commit()
    return {"success": True}


@static_router.get("/events/analytics/global")
def get_global_event_analytics(
    period: str = Query("MONTH"),
    event_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    from sqlalchemy import func

    user_sede = require_user_sede_id(db, current_user)
    query = db.query(
        models.EventAttendance.session_date,
        func.count(models.EventAttendance.id).label("attended_count"),
    ).join(models.CrmEvent)

    query = query.filter(
        (models.CrmEvent.sede_id == user_sede) | models.CrmEvent.sede_id.is_(None),
        models.CrmEvent.deleted_at.is_(None),
    )
    if event_type and event_type != "ALL":
        query = query.filter(models.CrmEvent.event_type == event_type)

    daily_stats = query.group_by(models.EventAttendance.session_date).all()
    bucket_map = {}

    for row in daily_stats:
        session_day = row.session_date
        if not session_day:
            continue
        if hasattr(session_day, "date"):
            session_day = session_day.date()

        if period == "WEEK":
            isocal = session_day.isocalendar()
            key = f"{isocal[0]}-W{isocal[1]:02d}"
            label = f"Sem {isocal[1]}, {isocal[0]}"
        elif period == "MONTH":
            key = session_day.strftime("%Y-%m")
            label = f"{calendar.month_abbr[session_day.month]} {session_day.year}"
        elif period == "BIMESTER":
            bimester = math.ceil(session_day.month / 2)
            key = f"{session_day.year}-B{bimester}"
            label = f"Bimestre {bimester}, {session_day.year}"
        elif period == "TRIMESTER":
            trimester = math.ceil(session_day.month / 3)
            key = f"{session_day.year}-Q{trimester}"
            label = f"Trim {trimester}, {session_day.year}"
        elif period == "SEMESTER":
            semester = math.ceil(session_day.month / 6)
            key = f"{session_day.year}-S{semester}"
            label = f"Semestre {semester}, {session_day.year}"
        elif period == "YEAR":
            key = f"{session_day.year}"
            label = f"{session_day.year}"
        else:
            key = session_day.strftime("%Y-%m")
            label = f"{calendar.month_abbr[session_day.month]} {session_day.year}"

        if key not in bucket_map:
            bucket_map[key] = {"key": key, "label": label, "total": 0, "sessions": 0}
        bucket_map[key]["total"] += row.attended_count
        bucket_map[key]["sessions"] += 1

    series = []
    for key in sorted(bucket_map.keys()):
        bucket = bucket_map[key]
        bucket["avg"] = round(bucket["total"] / bucket["sessions"]) if bucket["sessions"] > 0 else 0
        series.append(bucket)

    total_attendance = sum(bucket["total"] for bucket in bucket_map.values())
    total_sessions = sum(bucket["sessions"] for bucket in bucket_map.values())
    avg_per_session = round(total_attendance / total_sessions) if total_sessions > 0 else 0
    peak_period = max(series, key=lambda item: item["total"]) if series else {"label": "N/A", "total": 0}

    trend = 0
    if len(series) >= 2:
        last = series[-1]["total"]
        previous = series[-2]["total"]
        if previous > 0:
            trend = round(((last - previous) / previous) * 100, 1)

    return {
        "kpis": {
            "total_attendance": total_attendance,
            "avg_per_session": avg_per_session,
            "peak_period": peak_period,
            "trend_percentage": trend,
        },
        "series": series,
    }


@static_router.get("/events/dashboard-stats")
def get_events_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    user_sede = require_user_sede_id(db, current_user)
    events = _active_events_query(db).filter(
        (models.CrmEvent.sede_id == user_sede) | models.CrmEvent.sede_id.is_(None)
    ).all()
    if not events:
        return []

    event_ids = [e.id for e in events]

    # Single query: get latest session date per event
    from sqlalchemy import func

    latest_dates = dict(
        db.query(
            models.EventAttendance.event_id,
            func.max(models.EventAttendance.session_date),
        )
        .filter(models.EventAttendance.event_id.in_(event_ids))
        .group_by(models.EventAttendance.event_id)
        .all()
    )

    # Single query: get attendance count per event per latest date
    latest_pairs = [(eid, dt) for eid, dt in latest_dates.items()]
    attendance_counts = {}
    if latest_pairs:
        from sqlalchemy import tuple_

        counts = (
            db.query(
                models.EventAttendance.event_id,
                models.EventAttendance.session_date,
                func.count(models.EventAttendance.id),
            )
            .filter(
                tuple_(
                    models.EventAttendance.event_id,
                    models.EventAttendance.session_date,
                ).in_(latest_pairs)
            )
            .group_by(
                models.EventAttendance.event_id,
                models.EventAttendance.session_date,
            )
            .all()
        )
        for event_id, session_date, cnt in counts:
            attendance_counts[(event_id, session_date)] = cnt

    stats = []
    for event in events:
        latest_date = latest_dates.get(event.id)
        if latest_date:
            attended = attendance_counts.get((event.id, latest_date), 0)
            expected = len(get_expected_personas_for_event(db, event))
            rate = round((attended / expected) * 100, 1) if expected > 0 else 0
            stats.append(
                {
                    "event_id": event.id,
                    "latest_session": latest_date.isoformat(),
                    "attended": attended,
                    "expected": expected,
                    "rate": rate,
                }
            )
        else:
            stats.append(
                {
                    "event_id": event.id,
                    "latest_session": None,
                    "attended": 0,
                    "expected": 0,
                    "rate": 0,
                }
            )

    return stats


@dynamic_router.get("/events/{event_id}/analytics")
def get_event_analytics(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    require_event_access(db, current_user, event_id)

    attendances = db.query(models.EventAttendance).filter(models.EventAttendance.event_id == event_id).all()
    sessions_by_month = collections.defaultdict(set)
    attendees_by_session = collections.defaultdict(int)

    for attendance in attendances:
        if attendance.session_date:
            month_key = attendance.session_date.strftime("%Y-%m")
            sessions_by_month[month_key].add(attendance.session_date)
            attendees_by_session[attendance.session_date] += 1

    monthly_data = []
    total_sessions = 0
    total_attendance_all = 0
    peak_month = {"month": "-", "avg": 0}

    for month in sorted(sessions_by_month.keys()):
        sessions = sessions_by_month[month]
        total_att_month = sum(attendees_by_session[session] for session in sessions)
        avg_att = round(total_att_month / len(sessions)) if sessions else 0
        monthly_data.append({"month": month, "avg_attendance": avg_att, "total_sessions": len(sessions)})
        total_sessions += len(sessions)
        total_attendance_all += total_att_month
        if avg_att > peak_month["avg"]:
            peak_month = {"month": month, "avg": avg_att}

    historical_avg = round(total_attendance_all / total_sessions) if total_sessions > 0 else 0
    trend = 0
    if len(monthly_data) >= 2:
        last = monthly_data[-1]["avg_attendance"]
        previous = monthly_data[-2]["avg_attendance"]
        if previous > 0:
            trend = round(((last - previous) / previous) * 100, 1)

    return {
        "monthly_data": monthly_data,
        "kpis": {
            "historical_avg": historical_avg,
            "peak_month": peak_month,
            "trend_percentage": trend,
        },
    }


@dynamic_router.get("/events/{event_id}/sessions/{session_date}/export")
def export_event_session_report(
    event_id: str,
    session_date: datetime.date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    event = require_event_access(db, current_user, event_id)

    attendances_db = (
        db.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event_id,
            models.EventAttendance.session_date == session_date,
        )
        .all()
    )
    attended_ids = {row.persona_id for row in attendances_db}
    expected_personas = get_expected_personas_for_event(db, event)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=",", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["Nombre Completo", "Telefono", "Email", "Rol", "Estado Asistencia"])

    for persona in expected_personas:
        status = "Presente" if persona.id in attended_ids else "Ausente"
        writer.writerow(
            [
                persona.nombre_completo,
                persona.phone or "",
                persona.email or "",
                persona.church_role or "Miembro",
                status,
            ]
        )

    expected_ids = {persona.id for persona in expected_personas}
    for attendance in attendances_db:
        if attendance.persona_id not in expected_ids and attendance.persona:
            persona = attendance.persona
            writer.writerow(
                [
                    persona.nombre_completo,
                    persona.phone or "",
                    persona.email or "",
                    persona.church_role or "Visitante Servicios",
                    "Presente (Invitado/No Esperado)",
                ]
            )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=reporte_asistencia_{event.name}_{session_date}.csv"},
    )


@dynamic_router.post("/events/{event_id}/attendance/close", response_model=dict)
def close_event_attendance_endpoint(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    """Cierra la asistencia del evento: marca ausentes y genera seguimiento CRM.

    Idempotente: si el evento ya tiene ``attendance_closed_at``, devuelve 200
    sin hacer cambios. El rollback atomico garantiza que un fallo en el CRM
    revierte TODO el lote de ausentes (no deja estado parcial).
    """
    from backend.services.event_registration_service import close_event_attendance

    event = require_event_access(db, current_user, event_id)
    result = close_event_attendance(
        db,
        event,
        closed_by=current_user.id,
    )
    return result


@dynamic_router.get("/events/{event_id}/people/lookup", response_model=dict)
def lookup_person_for_event(
    event_id: str,
    email: Optional[str] = Query(None),
    phone: Optional[str] = Query(None),
    document_number: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    """Busca una persona por email, telefono o documento dentro del scope de sede del evento.

    Devuelve datos no sensibles para identificacion administrativa.
    No expone PII mas alla de lo necesario.
    """
    from sqlalchemy import func as _func
    from sqlalchemy import or_ as _or

    event = require_event_access(db, current_user, event_id)
    sede_id = getattr(event, "sede_id", None)

    query = db.query(models.Persona)
    if sede_id:
        # Evento global (sede_id NULL): la búsqueda abarca toda la iglesia.
        query = query.filter(models.Persona.sede_id == sede_id)
    conditions = []
    if email:
        conditions.append(_func.lower(models.Persona.email) == email.strip().lower())
    if phone:
        conditions.append(models.Persona.phone == phone.strip())
    if document_number:
        conditions.append(_func.upper(models.Persona.document_number) == document_number.strip().upper())

    if not conditions:
        raise HTTPException(status_code=422, detail="Debe proporcionar email, phone o document_number")

    persona = query.filter(_or(*conditions)).first()
    if not persona:
        return {"found": False, "persona": None}

    return {
        "found": True,
        "persona": {
            "persona_id": str(persona.id),
            "nombre_completo": persona.nombre_completo,
            "email": persona.email,
            "phone": persona.phone,
            "church_role": persona.church_role,
            "origen_evento_id": str(persona.origen_evento_id) if persona.origen_evento_id else None,
        },
    }


@static_router.get("/events/roles", response_model=List[dict])
@static_router.get("/roles")
def get_roles(
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_evangelism_read),
):
    return (
        db.query(models.RoleDefinition)
        .order_by(models.RoleDefinition.is_leadership.desc(), models.RoleDefinition.name.asc())
        .all()
    )


@static_router.post("/events/roles")
@static_router.post("/roles")
def create_role(
    payload: RoleDefinitionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    exists = db.query(models.RoleDefinition).filter(models.RoleDefinition.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=400, detail="El rol ya existe")
    role = models.RoleDefinition(**payload.model_dump())
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@static_router.put("/events/roles/{role_id}")
@static_router.put("/roles/{role_id}")
def update_role(
    role_id: str,
    payload: RoleDefinitionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    role = db.query(models.RoleDefinition).filter(models.RoleDefinition.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    if payload.name is not None:
        exists = (
            db.query(models.RoleDefinition)
            .filter(
                models.RoleDefinition.name == payload.name,
                models.RoleDefinition.id != role_id,
            )
            .first()
        )
        if exists:
            raise HTTPException(status_code=400, detail="Ya existe otro rol con ese nombre")
        db.query(models.Persona).filter(models.Persona.church_role == role.name).update({"church_role": payload.name})
        role.name = payload.name

    if payload.color is not None:
        role.color = payload.color
    if payload.is_leadership is not None:
        role.is_leadership = payload.is_leadership

    db.commit()
    db.refresh(role)
    return role


@static_router.delete("/events/roles/{role_id}")
@static_router.delete("/roles/{role_id}")
def delete_role(
    role_id: str,
    fallback_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
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
    if role.is_system_locked:
        raise HTTPException(status_code=400, detail="No se puede eliminar un rol del sistema")

    # Reasignar personas al rol de reemplazo
    db.query(models.Persona).filter(models.Persona.church_role == role.name).update({"church_role": fallback.name})

    # Soft-delete: marcar como inactivo y renombrar para liberar el unique constraint
    from datetime import datetime, timezone

    suffix = datetime.now(timezone.utc).strftime("_deleted_%Y%m%d_%H%M%S")
    role.name = f"{role.name}{suffix}"
    role.is_leadership = False
    db.commit()
    return {
        "success": True,
        "message": f"Rol '{role.name}' desactivado y personas reasignadas a '{fallback.name}'",
    }


@static_router.get("/events/personas/{persona_id}/attendance-history", response_model=dict)
@static_router.get("/personas/{persona_id}/attendance-history", response_model=dict)
def get_persona_attendance_history(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    user_sede = require_user_sede_id(db, current_user)
    persona = (
        db.query(models.Persona).filter(models.Persona.id == persona_id, models.Persona.sede_id == user_sede).first()
    )
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    rows = (
        db.query(models.EventAttendance)
        .filter(models.EventAttendance.persona_id == persona_id)
        .join(models.CrmEvent)
        .filter(
            (models.CrmEvent.sede_id == user_sede) | models.CrmEvent.sede_id.is_(None),
            models.CrmEvent.deleted_at.is_(None),
        )
        .order_by(
            models.CrmEvent.event_date.desc().nullslast(),
            models.CrmEvent.created_at.desc(),
        )
        .all()
    )

    history = []
    for row in rows:
        history.append(
            {
                "event_id": row.event_id,
                "event_name": row.event.name if row.event else None,
                "event_date": (row.event.event_date.isoformat() if row.event and row.event.event_date else None),
                "session_date": (row.session_date.isoformat() if row.session_date else None),
                "status": "present" if row.attended else "absent",
                "check_in_at": row.scanned_at.isoformat() if row.scanned_at else None,
            }
        )

    return {
        "persona_id": persona.id,
        "persona_name": persona.nombre_completo,
        "total_records": len(history),
        "history": history,
    }


# Forzar prelación de rutas estáticas (dashboard-stats, /roles, /personas/...) ANTES
# de las dinámicas con /events/{event_id}. Sin este orden FastAPI matchea el
# dinámico primero y retorna 404 "Event not found" para paths no-UUID.
router.include_router(static_router)
router.include_router(dynamic_router)
