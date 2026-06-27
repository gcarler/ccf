from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from backend import models
from backend.models_shared import _utcnow


def list_events(db: Session, sede_id: UUID) -> list[models.EventoAgenda]:
    return (
        db.query(models.EventoAgenda)
        .filter(
            models.EventoAgenda.sede_id == sede_id,
            models.EventoAgenda.deleted_at.is_(None),
        )
        .order_by(models.EventoAgenda.fecha_inicio.asc())
        .all()
    )


def get_event(db: Session, event_id: UUID, sede_id: UUID) -> models.EventoAgenda | None:
    return (
        db.query(models.EventoAgenda)
        .filter(
            models.EventoAgenda.id == event_id,
            models.EventoAgenda.sede_id == sede_id,
            models.EventoAgenda.deleted_at.is_(None),
        )
        .first()
    )


def list_events_by_range(
    db: Session, sede_id: UUID, starts_at: datetime, ends_at: datetime
) -> list[models.EventoAgenda]:
    return (
        db.query(models.EventoAgenda)
        .filter(
            models.EventoAgenda.sede_id == sede_id,
            models.EventoAgenda.fecha_inicio < ends_at,
            models.EventoAgenda.fecha_fin > starts_at,
            models.EventoAgenda.deleted_at.is_(None),
        )
        .order_by(models.EventoAgenda.fecha_inicio.asc())
        .all()
    )


def create_event(db: Session, data: dict) -> models.EventoAgenda:
    row = models.EventoAgenda(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_event(db: Session, row: models.EventoAgenda, data: dict) -> models.EventoAgenda:
    for key, value in data.items():
        setattr(row, key, value)
    row.updated_at = _utcnow()
    db.commit()
    db.refresh(row)
    return row


def archive_event(db: Session, row: models.EventoAgenda) -> None:
    row.deleted_at = _utcnow()
    db.commit()


def list_resources(db: Session, sede_id: UUID) -> list[models.RecursoFisico]:
    return (
        db.query(models.RecursoFisico)
        .filter(
            models.RecursoFisico.sede_id == sede_id,
            models.RecursoFisico.deleted_at.is_(None),
        )
        .order_by(models.RecursoFisico.nombre)
        .all()
    )


def get_resource(db: Session, resource_id: UUID, sede_id: UUID) -> models.RecursoFisico | None:
    return (
        db.query(models.RecursoFisico)
        .filter(
            models.RecursoFisico.id == resource_id,
            models.RecursoFisico.sede_id == sede_id,
            models.RecursoFisico.deleted_at.is_(None),
        )
        .first()
    )


def create_resource(db: Session, data: dict) -> models.RecursoFisico:
    row = models.RecursoFisico(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_resource(db: Session, row: models.RecursoFisico, data: dict) -> models.RecursoFisico:
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def archive_resource(db: Session, row: models.RecursoFisico) -> None:
    row.deleted_at = _utcnow()
    db.commit()


def list_participants(db: Session, event_id: UUID) -> list[models.ParticipanteEvento]:
    return (
        db.query(models.ParticipanteEvento)
        .filter(
            models.ParticipanteEvento.evento_id == event_id,
            models.ParticipanteEvento.deleted_at.is_(None),
        )
        .order_by(models.ParticipanteEvento.id)
        .all()
    )


def get_participant(db: Session, participant_id: UUID) -> models.ParticipanteEvento | None:
    return (
        db.query(models.ParticipanteEvento)
        .filter(
            models.ParticipanteEvento.id == participant_id,
            models.ParticipanteEvento.deleted_at.is_(None),
        )
        .first()
    )


def create_participant(db: Session, data: dict) -> models.ParticipanteEvento:
    row = models.ParticipanteEvento(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_participant(
    db: Session, row: models.ParticipanteEvento, data: dict
) -> models.ParticipanteEvento:
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def archive_participant(db: Session, row: models.ParticipanteEvento) -> None:
    row.deleted_at = _utcnow()
    db.commit()


def list_reservations(db: Session, event_id: UUID) -> list[models.ReservaRecurso]:
    return (
        db.query(models.ReservaRecurso)
        .filter(
            models.ReservaRecurso.evento_id == event_id,
            models.ReservaRecurso.deleted_at.is_(None),
        )
        .order_by(models.ReservaRecurso.bloqueo_inicio)
        .all()
    )


def get_reservation(db: Session, reservation_id: UUID) -> models.ReservaRecurso | None:
    return (
        db.query(models.ReservaRecurso)
        .filter(
            models.ReservaRecurso.id == reservation_id,
            models.ReservaRecurso.deleted_at.is_(None),
        )
        .first()
    )


def create_reservation(db: Session, data: dict) -> models.ReservaRecurso:
    row = models.ReservaRecurso(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_reservation(
    db: Session, row: models.ReservaRecurso, data: dict
) -> models.ReservaRecurso:
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def archive_reservation(db: Session, row: models.ReservaRecurso) -> None:
    row.deleted_at = _utcnow()
    db.commit()
