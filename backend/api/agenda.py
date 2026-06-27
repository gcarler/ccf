from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from backend import models
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.core.tenant import require_user_sede_id
from backend.crud import agenda as crud
from backend.schemas.agenda import (
    AgendaEvent,
    AgendaEventCreate,
    EventParticipant,
    EventParticipantCreate,
    PhysicalResource,
    PhysicalResourceCreate,
    ResourceReservation,
    ResourceReservationCreate,
)

router = APIRouter(prefix="/agenda", tags=["Agenda"])

AgendaReader = Depends(require_module_access("spiritual_life", "read"))
AgendaEditor = Depends(require_module_access("spiritual_life", "edit"))


def _sede_id(db: Session, user) -> UUID:
    return UUID(str(require_user_sede_id(db, user)))


def _event_payload(payload: AgendaEventCreate, sede_id: UUID, persona_id: UUID) -> dict:
    return {
        "sede_id": sede_id,
        "modulo_origen": "MANUAL",
        "titulo": payload.title,
        "descripcion": payload.description,
        "fecha_inicio": payload.start_at,
        "fecha_fin": payload.end_at or payload.start_at,
        "todo_el_dia": payload.is_all_day,
        "ubicacion_texto": payload.location,
        "organizador_persona_id": persona_id,
        "visibilidad": "SEDE",
        "estado": "ACTIVO",
    }


def _serialize_event(row: models.EventoAgenda) -> dict:
    return {
        "id": row.id,
        "title": row.titulo,
        "description": row.descripcion,
        "start_at": row.fecha_inicio,
        "end_at": row.fecha_fin,
        "location": row.ubicacion_texto,
        "is_all_day": row.todo_el_dia,
        "created_by_persona_id": row.organizador_persona_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _serialize_resource(row: models.RecursoFisico) -> dict:
    return {
        "id": row.id,
        "sede_id": row.sede_id,
        "name": row.nombre,
        "resource_type": row.tipo,
        "capacity": row.capacidad_maxima,
        "is_active": row.activo,
    }


def _serialize_participant(row: models.ParticipanteEvento) -> dict:
    return {
        "id": row.id,
        "event_id": row.evento_id,
        "persona_id": row.persona_id,
        "confirmation_status": row.estado_confirmacion,
        "is_required": row.es_requerido,
        "confirmed_at": row.fecha_confirmacion,
    }


def _serialize_reservation(row: models.ReservaRecurso) -> dict:
    return {
        "id": row.id,
        "event_id": row.evento_id,
        "resource_id": row.recurso_id,
        "starts_at": row.bloqueo_inicio,
        "ends_at": row.bloqueo_fin,
    }


@router.get("/events", response_model=list[AgendaEvent])
def list_events(
    db: Session = Depends(get_db),
    current_user: models.User = AgendaReader,
):
    return [_serialize_event(row) for row in crud.list_events(db, _sede_id(db, current_user))]


@router.get("/events/by-date-range", response_model=list[AgendaEvent])
def list_events_by_date_range(
    start: datetime = Query(...),
    end: datetime = Query(...),
    db: Session = Depends(get_db),
    current_user: models.User = AgendaReader,
):
    if end <= start:
        raise HTTPException(status_code=422, detail="end must be greater than start")
    rows = crud.list_events_by_range(db, _sede_id(db, current_user), start, end)
    return [_serialize_event(row) for row in rows]


@router.post("/events", response_model=AgendaEvent, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: AgendaEventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = AgendaEditor,
):
    row = crud.create_event(
        db, _event_payload(payload, _sede_id(db, current_user), current_user.id)
    )
    return _serialize_event(row)


@router.get("/events/{event_id}", response_model=AgendaEvent)
def get_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = AgendaReader,
):
    row = crud.get_event(db, event_id, _sede_id(db, current_user))
    if not row:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return _serialize_event(row)


@router.put("/events/{event_id}", response_model=AgendaEvent)
def update_event(
    event_id: UUID,
    payload: AgendaEventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = AgendaEditor,
):
    sede_id = _sede_id(db, current_user)
    row = crud.get_event(db, event_id, sede_id)
    if not row:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    row = crud.update_event(
        db, row, _event_payload(payload, sede_id, row.organizador_persona_id)
    )
    return _serialize_event(row)


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = AgendaEditor,
):
    row = crud.get_event(db, event_id, _sede_id(db, current_user))
    if not row:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    crud.archive_event(db, row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/resources", response_model=list[PhysicalResource])
def list_resources(
    db: Session = Depends(get_db),
    current_user: models.User = AgendaReader,
):
    rows = crud.list_resources(db, _sede_id(db, current_user))
    return [_serialize_resource(row) for row in rows]


@router.post("/resources", response_model=PhysicalResource, status_code=status.HTTP_201_CREATED)
def create_resource(
    payload: PhysicalResourceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = AgendaEditor,
):
    row = crud.create_resource(
        db,
        {
            "sede_id": _sede_id(db, current_user),
            "nombre": payload.name,
            "tipo": payload.resource_type,
            "capacidad_maxima": payload.capacity,
            "activo": payload.is_active,
        },
    )
    return _serialize_resource(row)


@router.put("/resources/{resource_id}", response_model=PhysicalResource)
def update_resource(
    resource_id: UUID,
    payload: PhysicalResourceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = AgendaEditor,
):
    row = crud.get_resource(db, resource_id, _sede_id(db, current_user))
    if not row:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    row = crud.update_resource(
        db,
        row,
        {
            "nombre": payload.name,
            "tipo": payload.resource_type,
            "capacidad_maxima": payload.capacity,
            "activo": payload.is_active,
        },
    )
    return _serialize_resource(row)


@router.delete("/resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_resource(
    resource_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = AgendaEditor,
):
    row = crud.get_resource(db, resource_id, _sede_id(db, current_user))
    if not row:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    crud.archive_resource(db, row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/events/{event_id}/participants", response_model=list[EventParticipant])
def list_participants(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = AgendaReader,
):
    if not crud.get_event(db, event_id, _sede_id(db, current_user)):
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return [_serialize_participant(row) for row in crud.list_participants(db, event_id)]


@router.post("/participants", response_model=EventParticipant, status_code=status.HTTP_201_CREATED)
def create_participant(
    payload: EventParticipantCreate,
    db: Session = Depends(get_db),
    current_user: models.User = AgendaEditor,
):
    sede_id = _sede_id(db, current_user)
    if not crud.get_event(db, payload.event_id, sede_id):
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    persona = db.query(models.Persona).filter(
        models.Persona.id == payload.persona_id,
        models.Persona.sede_id == sede_id,
    ).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    row = crud.create_participant(
        db,
        {
            "evento_id": payload.event_id,
            "persona_id": payload.persona_id,
            "estado_confirmacion": payload.confirmation_status,
            "es_requerido": payload.is_required,
            "fecha_confirmacion": payload.confirmed_at,
        },
    )
    return _serialize_participant(row)


@router.put("/participants/{participant_id}", response_model=EventParticipant)
def update_participant(
    participant_id: UUID,
    payload: EventParticipantCreate,
    db: Session = Depends(get_db),
    current_user: models.User = AgendaEditor,
):
    row = crud.get_participant(db, participant_id)
    sede_id = _sede_id(db, current_user)
    if not row or not crud.get_event(db, row.evento_id, sede_id):
        raise HTTPException(status_code=404, detail="Participante no encontrado")
    row = crud.update_participant(
        db,
        row,
        {
            "estado_confirmacion": payload.confirmation_status,
            "es_requerido": payload.is_required,
            "fecha_confirmacion": payload.confirmed_at,
        },
    )
    return _serialize_participant(row)


@router.delete("/participants/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_participant(
    participant_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = AgendaEditor,
):
    row = crud.get_participant(db, participant_id)
    if not row or not crud.get_event(db, row.evento_id, _sede_id(db, current_user)):
        raise HTTPException(status_code=404, detail="Participante no encontrado")
    crud.archive_participant(db, row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _validate_reservation_scope(
    db: Session, payload: ResourceReservationCreate, sede_id: UUID
) -> None:
    if not crud.get_event(db, payload.event_id, sede_id):
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    if not crud.get_resource(db, payload.resource_id, sede_id):
        raise HTTPException(status_code=404, detail="Recurso no encontrado")


@router.get("/events/{event_id}/reservations", response_model=list[ResourceReservation])
def list_reservations(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = AgendaReader,
):
    if not crud.get_event(db, event_id, _sede_id(db, current_user)):
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return [_serialize_reservation(row) for row in crud.list_reservations(db, event_id)]


@router.post("/reservations", response_model=ResourceReservation, status_code=status.HTTP_201_CREATED)
def create_reservation(
    payload: ResourceReservationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = AgendaEditor,
):
    _validate_reservation_scope(db, payload, _sede_id(db, current_user))
    conflict = db.query(models.ReservaRecurso).filter(
        models.ReservaRecurso.recurso_id == payload.resource_id,
        models.ReservaRecurso.bloqueo_inicio < payload.ends_at,
        models.ReservaRecurso.bloqueo_fin > payload.starts_at,
        models.ReservaRecurso.deleted_at.is_(None),
    ).first()
    if conflict:
        raise HTTPException(status_code=409, detail="El recurso ya está reservado en ese horario")
    row = crud.create_reservation(
        db,
        {
            "evento_id": payload.event_id,
            "recurso_id": payload.resource_id,
            "bloqueo_inicio": payload.starts_at,
            "bloqueo_fin": payload.ends_at,
        },
    )
    return _serialize_reservation(row)


@router.put("/reservations/{reservation_id}", response_model=ResourceReservation)
def update_reservation(
    reservation_id: UUID,
    payload: ResourceReservationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = AgendaEditor,
):
    row = crud.get_reservation(db, reservation_id)
    sede_id = _sede_id(db, current_user)
    if not row or not crud.get_event(db, row.evento_id, sede_id):
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    _validate_reservation_scope(db, payload, sede_id)
    conflict = db.query(models.ReservaRecurso).filter(
        models.ReservaRecurso.id != reservation_id,
        models.ReservaRecurso.recurso_id == payload.resource_id,
        models.ReservaRecurso.bloqueo_inicio < payload.ends_at,
        models.ReservaRecurso.bloqueo_fin > payload.starts_at,
        models.ReservaRecurso.deleted_at.is_(None),
    ).first()
    if conflict:
        raise HTTPException(status_code=409, detail="El recurso ya está reservado en ese horario")
    row = crud.update_reservation(
        db,
        row,
        {
            "evento_id": payload.event_id,
            "recurso_id": payload.resource_id,
            "bloqueo_inicio": payload.starts_at,
            "bloqueo_fin": payload.ends_at,
        },
    )
    return _serialize_reservation(row)


@router.delete("/reservations/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_reservation(
    reservation_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = AgendaEditor,
):
    row = crud.get_reservation(db, reservation_id)
    if not row or not crud.get_event(db, row.evento_id, _sede_id(db, current_user)):
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    crud.archive_reservation(db, row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
