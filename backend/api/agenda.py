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
from backend.crud.projects import get_user_persona_id
from backend.schemas.agenda import (
    AgendaEvent,
    AgendaEventCommentCreate,
    AgendaEventCommentItem,
    AgendaEventCreate,
    EventParticipant,
    EventParticipantCreate,
    PhysicalResource,
    PhysicalResourceCreate,
    ResourceReservation,
    ResourceReservationCreate,
)
from backend.services.comment_notifications import notify_mention
from backend.services.mention_parser import resolve_mentions

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
        "visibilidad": payload.visibilidad,
        "estado": "ACTIVO",
        "color_hex": payload.color_hex,
        "url_conferencia": payload.url_conferencia,
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
        "color_hex": row.color_hex,
        "url_conferencia": row.url_conferencia,
        "visibilidad": row.visibilidad,
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


def _serialize_comment(row: models.AgendaEventComment, author: models.Persona | None = None) -> dict:
    return {
        "id": row.id,
        "event_id": row.event_id,
        "author_id": row.author_id,
        "author_name": getattr(author, "nombre_completo", None) or getattr(author, "full_name", None) or "Usuario",
        "content": row.content,
        "attachments": row.attachments or [],
        "mentions": [str(m) for m in (row.mentions or [])],
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _author_name_agenda(persona: models.Persona | None) -> str:
    if not persona:
        return "Usuario"
    return getattr(persona, "nombre_completo", None) or getattr(persona, "full_name", None) or "Usuario"


@router.get("/events", response_model=list[AgendaEvent])
def list_events(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = AgendaReader,
):
    rows = crud.list_events(db, _sede_id(db, current_user))
    return [_serialize_event(row) for row in rows[skip:skip + limit]]


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
    conflict = crud.check_reservation_conflict(
        db, payload.resource_id, payload.starts_at, payload.ends_at
    )
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
    conflict = crud.check_reservation_conflict(
        db, payload.resource_id, payload.starts_at, payload.ends_at,
        exclude_reservation_id=reservation_id,
    )
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


@router.get("/events/{event_id}/comments", response_model=list[AgendaEventCommentItem])
def list_event_comments(
    event_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = AgendaReader,
):
    if not crud.get_event(db, event_id, _sede_id(db, current_user)):
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    rows = (
        db.query(models.AgendaEventComment)
        .filter(
            models.AgendaEventComment.event_id == event_id,
            models.AgendaEventComment.deleted_at.is_(None),
        )
        .order_by(models.AgendaEventComment.created_at.desc())
        .limit(limit)
        .all()
    )
    author_ids = {r.author_id for r in rows if r.author_id}
    authors = {p.id: p for p in db.query(models.Persona).filter(models.Persona.id.in_(author_ids)).all()} if author_ids else {}
    return [_serialize_comment(r, authors.get(r.author_id)) for r in rows]


@router.post("/events/{event_id}/comments", response_model=AgendaEventCommentItem, status_code=status.HTTP_201_CREATED)
def create_event_comment(
    event_id: UUID,
    payload: AgendaEventCommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = AgendaEditor,
):
    sede_id = _sede_id(db, current_user)
    event = crud.get_event(db, event_id, sede_id)
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    author_persona_id = get_user_persona_id(db, current_user.id)
    resolved_mentions = resolve_mentions(
        db,
        content=content,
        payload_mentions=payload.mentions or [],
        author_id=author_persona_id,
        user_sede=sede_id,
    )
    comment = models.AgendaEventComment(
        event_id=event_id,
        author_id=author_persona_id,
        content=content,
        attachments=[a.model_dump() for a in (payload.attachments or [])],
        mentions=resolved_mentions,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    if comment.mentions:
        notify_mention(
            db,
            mention_ids=comment.mentions,
            author_id=comment.author_id,
            title=f"Te mencionaron en un comentario de agenda: {event.titulo}",
            content=f"{content[:120]}{'...' if len(content) > 120 else ''}",
            url=f"/plataforma/agenda/eventos/{event_id}",
            sede_id=sede_id,
        )
    return _serialize_comment(comment, comment.author)


@router.patch("/events/{event_id}/comments/{comment_id}", response_model=AgendaEventCommentItem)
def update_event_comment(
    event_id: UUID,
    comment_id: UUID,
    payload: AgendaEventCommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = AgendaEditor,
):
    sede_id = _sede_id(db, current_user)
    event = crud.get_event(db, event_id, sede_id)
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    comment = (
        db.query(models.AgendaEventComment)
        .filter(
            models.AgendaEventComment.id == comment_id,
            models.AgendaEventComment.event_id == event_id,
            models.AgendaEventComment.deleted_at.is_(None),
        )
        .first()
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Comentario no encontrado")
    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    comment.content = content
    comment.attachments = [a.model_dump() for a in (payload.attachments or [])]
    previous_mentions = {str(m) for m in (comment.mentions or [])}
    comment.mentions = resolve_mentions(
        db,
        content=content,
        payload_mentions=payload.mentions or [],
        author_id=comment.author_id,
        user_sede=sede_id,
    )
    db.commit()
    db.refresh(comment)
    # Notify only newly added mentions to avoid duplicate notifications.
    new_mentions = {str(m) for m in (comment.mentions or [])}
    added_mentions = new_mentions - previous_mentions
    if added_mentions:
        notify_mention(
            db,
            mention_ids=[UUID(m) for m in added_mentions],
            author_id=comment.author_id,
            title=f"Te mencionaron en un comentario de agenda: {event.titulo}",
            content=f"{content[:120]}{'...' if len(content) > 120 else ''}",
            url=f"/plataforma/agenda/eventos/{event_id}",
            sede_id=sede_id,
        )
    return _serialize_comment(comment, comment.author)


@router.delete("/events/{event_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event_comment(
    event_id: UUID,
    comment_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = AgendaEditor,
):
    sede_id = _sede_id(db, current_user)
    if not crud.get_event(db, event_id, sede_id):
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    comment = (
        db.query(models.AgendaEventComment)
        .filter(
            models.AgendaEventComment.id == comment_id,
            models.AgendaEventComment.event_id == event_id,
            models.AgendaEventComment.deleted_at.is_(None),
        )
        .first()
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Comentario no encontrado")
    comment.deleted_at = datetime.now()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
