"""MCP privado para Calendario/Agenda de CCF.

Agenda usa ``spiritual_life:*`` como permisos canónicos porque esa es la
matriz que ya protege ``/api/agenda``. El cliente nunca puede proporcionar la
sede: se deriva del JWT autenticado.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from mcp.server.fastmcp import FastMCP

from backend import models
from backend.core.audit import record_admin_action
from backend.core.database import SessionLocal
from backend.core.tenant import require_user_sede_id
from backend.crud import agenda as crud
from backend.mcp_auth import authenticated_mcp_app, get_mcp_current_user, require_mcp_permission
from backend.schemas.agenda import AgendaEventCreate, ResourceReservationCreate

agenda_mcp = FastMCP(
    name="CCF Calendario",
    instructions=(
        "Gestiona el calendario y la agenda de la sede del usuario autenticado. "
        "Usa los permisos spiritual_life del backend y no permitas acceder a "
        "eventos, personas, recursos o reservas de otra sede."
    ),
    streamable_http_path="/",
    stateless_http=True,
)


def _sede(db, user) -> UUID:
    return UUID(str(require_user_sede_id(db, user)))


def _safe_event(row: models.EventoAgenda) -> dict[str, Any]:
    return {
        "event_id": str(row.id),
        "title": row.titulo,
        "description": row.descripcion,
        "start_at": row.fecha_inicio.isoformat(),
        "end_at": row.fecha_fin.isoformat(),
        "location": row.ubicacion_texto,
        "is_all_day": bool(row.todo_el_dia),
        "created_by_persona_id": str(row.organizador_persona_id),
        "visibility": row.visibilidad,
        "status": row.estado,
        "color_hex": row.color_hex,
        "conference_url": row.url_conferencia,
    }


def _safe_resource(row: models.RecursoFisico) -> dict[str, Any]:
    return {
        "resource_id": str(row.id),
        "sede_id": str(row.sede_id),
        "name": row.nombre,
        "resource_type": row.tipo,
        "capacity": row.capacidad_maxima,
        "is_active": bool(row.activo),
    }


def _safe_participant(row: models.ParticipanteEvento) -> dict[str, Any]:
    return {
        "participant_id": str(row.id),
        "event_id": str(row.evento_id),
        "persona_id": str(row.persona_id),
        "confirmation_status": row.estado_confirmacion,
        "is_required": bool(row.es_requerido),
        "confirmed_at": row.fecha_confirmacion.isoformat() if row.fecha_confirmacion else None,
    }


def _safe_reservation(row: models.ReservaRecurso) -> dict[str, Any]:
    return {
        "reservation_id": str(row.id),
        "event_id": str(row.evento_id),
        "resource_id": str(row.recurso_id),
        "starts_at": row.bloqueo_inicio.isoformat(),
        "ends_at": row.bloqueo_fin.isoformat(),
    }


def _event_create(
    title: str,
    start_at: str,
    end_at: str | None,
    description: str | None,
    location: str | None,
    is_all_day: bool,
    color_hex: str | None,
    conference_url: str | None,
    visibility: str,
) -> AgendaEventCreate:
    return AgendaEventCreate(
        title=title,
        description=description,
        start_at=datetime.fromisoformat(start_at.replace("Z", "+00:00")),
        end_at=datetime.fromisoformat(end_at.replace("Z", "+00:00")) if end_at else None,
        location=location,
        is_all_day=is_all_day,
        color_hex=color_hex,
        url_conferencia=conference_url,
        visibilidad=visibility,
    )


@agenda_mcp.tool()
def list_calendar_events(limit: int = 100, offset: int = 0) -> dict[str, Any]:
    """Lista eventos activos de la sede."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "spiritual_life:read")
        rows = crud.list_events(db, _sede(db, user))
        page = rows[max(0, int(offset)) : max(0, int(offset)) + max(1, min(int(limit), 500))]
        return {"items": [_safe_event(row) for row in page], "total": len(rows)}
    finally:
        db.close()


@agenda_mcp.tool()
def list_calendar_events_by_range(start_at: str, end_at: str) -> dict[str, Any]:
    """Lista eventos que se superponen con un rango ISO-8601."""
    start = datetime.fromisoformat(start_at.replace("Z", "+00:00"))
    end = datetime.fromisoformat(end_at.replace("Z", "+00:00"))
    if end <= start:
        raise ValueError("end_at debe ser posterior a start_at")
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "spiritual_life:read")
        rows = crud.list_events_by_range(db, _sede(db, user), start, end)
        return {"items": [_safe_event(row) for row in rows], "count": len(rows)}
    finally:
        db.close()


@agenda_mcp.tool()
def get_calendar_event(event_id: UUID) -> dict[str, Any]:
    """Obtiene un evento dentro de la sede autenticada."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "spiritual_life:read")
        row = crud.get_event(db, event_id, _sede(db, user))
        if not row:
            raise ValueError("Evento de agenda no encontrado")
        return _safe_event(row)
    finally:
        db.close()


@agenda_mcp.tool()
def create_calendar_event(
    title: str,
    start_at: str,
    end_at: str | None = None,
    description: str | None = None,
    location: str | None = None,
    is_all_day: bool = True,
    color_hex: str | None = None,
    conference_url: str | None = None,
    visibility: str = "SEDE",
) -> dict[str, Any]:
    """Crea un evento de agenda en la sede del usuario."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "spiritual_life:edit")
        payload = _event_create(title, start_at, end_at, description, location, is_all_day, color_hex, conference_url, visibility)
        row = crud.create_event(
            db,
            {
                "sede_id": _sede(db, user),
                "modulo_origen": "MCP",
                "titulo": payload.title,
                "descripcion": payload.description,
                "fecha_inicio": payload.start_at,
                "fecha_fin": payload.end_at or payload.start_at,
                "todo_el_dia": payload.is_all_day,
                "ubicacion_texto": payload.location,
                "organizador_persona_id": user.id,
                "visibilidad": payload.visibilidad,
                "estado": "ACTIVO",
                "color_hex": payload.color_hex,
                "url_conferencia": payload.url_conferencia,
            },
        )
        record_admin_action(db, user, action="create_agenda_event_mcp", resource_type="agenda_event", resource_id=str(row.id), metadata={"source": "mcp"})
        return _safe_event(row)
    finally:
        db.close()


@agenda_mcp.tool()
def update_calendar_event(event_id: UUID, changes: dict[str, Any]) -> dict[str, Any]:
    """Actualiza campos operativos de un evento de agenda."""
    allowed = {"title", "description", "start_at", "end_at", "location", "is_all_day", "color_hex", "conference_url", "visibility"}
    clean = {key: value for key, value in changes.items() if key in allowed}
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "spiritual_life:edit")
        row = crud.get_event(db, event_id, _sede(db, user))
        if not row:
            raise ValueError("Evento de agenda no encontrado")
        if "title" in clean:
            row.titulo = clean["title"]
        if "description" in clean:
            row.descripcion = clean["description"]
        if "start_at" in clean:
            row.fecha_inicio = datetime.fromisoformat(str(clean["start_at"]).replace("Z", "+00:00"))
        if "end_at" in clean:
            row.fecha_fin = datetime.fromisoformat(str(clean["end_at"]).replace("Z", "+00:00"))
        elif "start_at" in clean:
            row.fecha_fin = row.fecha_inicio
        if row.fecha_fin < row.fecha_inicio:
            raise ValueError("end_at debe ser mayor o igual que start_at")
        mapping = {"location": "ubicacion_texto", "is_all_day": "todo_el_dia", "color_hex": "color_hex", "visibility": "visibilidad"}
        for key, attribute in mapping.items():
            if key in clean:
                setattr(row, attribute, clean[key])
        if "conference_url" in clean:
            row.url_conferencia = clean["conference_url"]
        row = crud.update_event(db, row, {
            "titulo": row.titulo,
            "descripcion": row.descripcion,
            "fecha_inicio": row.fecha_inicio,
            "fecha_fin": row.fecha_fin,
            "ubicacion_texto": row.ubicacion_texto,
            "todo_el_dia": row.todo_el_dia,
            "color_hex": row.color_hex,
            "visibilidad": row.visibilidad,
            "url_conferencia": row.url_conferencia,
        })
        record_admin_action(db, user, action="update_agenda_event_mcp", resource_type="agenda_event", resource_id=str(row.id), metadata={"fields": sorted(clean), "source": "mcp"})
        return _safe_event(row)
    finally:
        db.close()


@agenda_mcp.tool()
def archive_calendar_event(event_id: UUID) -> dict[str, Any]:
    """Archiva un evento de agenda conservando su historial."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "spiritual_life:edit")
        row = crud.get_event(db, event_id, _sede(db, user))
        if not row:
            raise ValueError("Evento de agenda no encontrado")
        crud.archive_event(db, row)
        record_admin_action(db, user, action="archive_agenda_event_mcp", resource_type="agenda_event", resource_id=str(event_id), metadata={"source": "mcp"})
        return {"status": "archived", "event_id": str(event_id)}
    finally:
        db.close()


@agenda_mcp.tool()
def list_calendar_resources() -> dict[str, Any]:
    """Lista recursos físicos activos de la sede."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "spiritual_life:read")
        return {"items": [_safe_resource(row) for row in crud.list_resources(db, _sede(db, user))]}
    finally:
        db.close()


@agenda_mcp.tool()
def create_calendar_resource(name: str, resource_type: str, capacity: int | None = None, is_active: bool = True) -> dict[str, Any]:
    """Crea un recurso físico en la sede."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "spiritual_life:edit")
        row = crud.create_resource(db, {"sede_id": _sede(db, user), "nombre": name, "tipo": resource_type, "capacidad_maxima": capacity, "activo": is_active})
        return _safe_resource(row)
    finally:
        db.close()


@agenda_mcp.tool()
def archive_calendar_resource(resource_id: UUID) -> dict[str, Any]:
    """Archiva un recurso físico de la sede."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "spiritual_life:edit")
        row = crud.get_resource(db, resource_id, _sede(db, user))
        if not row:
            raise ValueError("Recurso de agenda no encontrado")
        crud.archive_resource(db, row)
        return {"status": "archived", "resource_id": str(resource_id)}
    finally:
        db.close()


@agenda_mcp.tool()
def list_calendar_participants(event_id: UUID) -> dict[str, Any]:
    """Lista participantes de un evento de la sede."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "spiritual_life:read")
        event = crud.get_event(db, event_id, _sede(db, user))
        if not event:
            raise ValueError("Evento de agenda no encontrado")
        return {"items": [_safe_participant(row) for row in crud.list_participants(db, event.id)]}
    finally:
        db.close()


@agenda_mcp.tool()
def add_calendar_participant(event_id: UUID, persona_id: UUID, confirmation_status: str = "PENDIENTE", is_required: bool = True) -> dict[str, Any]:
    """Añade una persona de la misma sede a un evento."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "spiritual_life:edit")
        sede_id = _sede(db, user)
        event = crud.get_event(db, event_id, sede_id)
        if not event:
            raise ValueError("Evento de agenda no encontrado")
        person = db.query(models.Persona).filter(models.Persona.id == persona_id, models.Persona.sede_id == sede_id).first()
        if not person:
            raise ValueError("Persona no encontrada en la sede")
        row = crud.create_participant(db, {"evento_id": event.id, "persona_id": person.id, "estado_confirmacion": confirmation_status, "es_requerido": is_required})
        return _safe_participant(row)
    finally:
        db.close()


@agenda_mcp.tool()
def archive_calendar_participant(participant_id: UUID) -> dict[str, Any]:
    """Archiva un participante verificando primero la sede del evento."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "spiritual_life:edit")
        row = crud.get_participant(db, participant_id)
        if not row or not crud.get_event(db, row.evento_id, _sede(db, user)):
            raise ValueError("Participante de agenda no encontrado")
        crud.archive_participant(db, row)
        return {"status": "archived", "participant_id": str(participant_id)}
    finally:
        db.close()


@agenda_mcp.tool()
def list_calendar_reservations(event_id: UUID) -> dict[str, Any]:
    """Lista reservas de recursos de un evento de la sede."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "spiritual_life:read")
        if not crud.get_event(db, event_id, _sede(db, user)):
            raise ValueError("Evento de agenda no encontrado")
        return {"items": [_safe_reservation(row) for row in crud.list_reservations(db, event_id)]}
    finally:
        db.close()


@agenda_mcp.tool()
def create_calendar_reservation(event_id: UUID, resource_id: UUID, starts_at: str, ends_at: str) -> dict[str, Any]:
    """Reserva un recurso físico, rechazando solapamientos."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "spiritual_life:edit")
        sede_id = _sede(db, user)
        event = crud.get_event(db, event_id, sede_id)
        resource = crud.get_resource(db, resource_id, sede_id)
        if not event or not resource:
            raise ValueError("Evento o recurso no encontrado en la sede")
        payload = ResourceReservationCreate(
            event_id=event_id,
            resource_id=resource_id,
            starts_at=datetime.fromisoformat(starts_at.replace("Z", "+00:00")),
            ends_at=datetime.fromisoformat(ends_at.replace("Z", "+00:00")),
        )
        if crud.check_reservation_conflict(db, resource_id, payload.starts_at, payload.ends_at):
            raise ValueError("El recurso ya está reservado en ese horario")
        row = crud.create_reservation(db, {"evento_id": event_id, "recurso_id": resource_id, "bloqueo_inicio": payload.starts_at, "bloqueo_fin": payload.ends_at})
        return _safe_reservation(row)
    finally:
        db.close()


@agenda_mcp.tool()
def archive_calendar_reservation(reservation_id: UUID) -> dict[str, Any]:
    """Archiva una reserva verificando el evento y su sede."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "spiritual_life:edit")
        row = crud.get_reservation(db, reservation_id)
        if not row or not crud.get_event(db, row.evento_id, _sede(db, user)):
            raise ValueError("Reserva de agenda no encontrada")
        crud.archive_reservation(db, row)
        return {"status": "archived", "reservation_id": str(reservation_id)}
    finally:
        db.close()


agenda_mcp_app = authenticated_mcp_app(agenda_mcp)
