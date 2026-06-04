"""Agenda / Calendario Unificado — CRUD functions.

RecursoFisico, EventoAgenda, ParticipanteEvento, ReservaRecurso.
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session
from backend.models_shared import _utcnow

from backend.models_agenda import (
    EventoAgenda, ParticipanteEvento, RecursoFisico, ReservaRecurso,
)
from backend.schemas.agenda_core import (
    EventoAgendaCreate, ParticipanteEventoCreate,
    RecursoFisicoCreate, ReservaRecursoCreate,
)


# ═══════════════════════════════════════════════════════════════════
# RecursoFisico
# ═══════════════════════════════════════════════════════════════════

def create_recurso(db: Session, payload: RecursoFisicoCreate) -> RecursoFisico:
    row = RecursoFisico(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_recurso(db: Session, recurso_id: int) -> Optional[RecursoFisico]:
    return db.query(RecursoFisico).filter(RecursoFisico.id == recurso_id).first()


def list_recursos(db: Session, sede_id: Optional[str] = None) -> List[RecursoFisico]:
    q = db.query(RecursoFisico)
    if sede_id is not None:
        q = q.filter(RecursoFisico.sede_id == sede_id)
    return q.order_by(RecursoFisico.nombre).all()


def update_recurso(
    db: Session, recurso_id: int, payload: RecursoFisicoCreate
) -> Optional[RecursoFisico]:
    row = db.query(RecursoFisico).filter(RecursoFisico.id == recurso_id).first()
    if not row:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_recurso(db: Session, recurso_id: int) -> bool:
    row = db.query(RecursoFisico).filter(RecursoFisico.id == recurso_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════
# EventoAgenda
# ═══════════════════════════════════════════════════════════════════

def create_evento(db: Session, payload: EventoAgendaCreate) -> EventoAgenda:
    row = EventoAgenda(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_evento(db: Session, evento_id: str) -> Optional[EventoAgenda]:
    return db.query(EventoAgenda).filter(
        EventoAgenda.id == evento_id,
        EventoAgenda.deleted_at.is_(None),
    ).first()


def list_eventos(db: Session, sede_id: Optional[str] = None) -> List[EventoAgenda]:
    q = db.query(EventoAgenda).filter(EventoAgenda.deleted_at.is_(None))
    if sede_id is not None:
        q = q.filter(EventoAgenda.sede_id == sede_id)
    return q.order_by(EventoAgenda.fecha_inicio.desc()).all()


def list_eventos_by_date_range(
    db: Session,
    sede_id: str,
    start: datetime,
    end: datetime,
) -> List[EventoAgenda]:
    """Eventos que intersectan [start, end] para una sede."""
    return (
        db.query(EventoAgenda)
        .filter(
            EventoAgenda.sede_id == sede_id,
            EventoAgenda.fecha_inicio < end,
            EventoAgenda.fecha_fin > start,
            EventoAgenda.deleted_at.is_(None),
        )
        .order_by(EventoAgenda.fecha_inicio.asc())
        .all()
    )


def update_evento(
    db: Session, evento_id: str, payload: EventoAgendaCreate
) -> Optional[EventoAgenda]:
    row = db.query(EventoAgenda).filter(EventoAgenda.id == evento_id).first()
    if not row:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_evento(db: Session, evento_id: str) -> bool:
    """Soft-delete: marca deleted_at."""
    row = db.query(EventoAgenda).filter(EventoAgenda.id == evento_id).first()
    if not row:
        return False
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════
# ParticipanteEvento
# ═══════════════════════════════════════════════════════════════════

def create_participante(
    db: Session, payload: ParticipanteEventoCreate
) -> ParticipanteEvento:
    row = ParticipanteEvento(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_participante(
    db: Session, participante_id: int
) -> Optional[ParticipanteEvento]:
    return (
        db.query(ParticipanteEvento)
        .filter(ParticipanteEvento.id == participante_id)
        .first()
    )


def list_participantes(
    db: Session, evento_id: str
) -> List[ParticipanteEvento]:
    return (
        db.query(ParticipanteEvento)
        .filter(ParticipanteEvento.evento_id == evento_id)
        .order_by(ParticipanteEvento.id)
        .all()
    )


def update_participante(
    db: Session, participante_id: int, payload: ParticipanteEventoCreate
) -> Optional[ParticipanteEvento]:
    row = (
        db.query(ParticipanteEvento)
        .filter(ParticipanteEvento.id == participante_id)
        .first()
    )
    if not row:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_participante(db: Session, participante_id: int) -> bool:
    row = (
        db.query(ParticipanteEvento)
        .filter(ParticipanteEvento.id == participante_id)
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════
# ReservaRecurso
# ═══════════════════════════════════════════════════════════════════

def create_reserva(db: Session, payload: ReservaRecursoCreate) -> ReservaRecurso:
    row = ReservaRecurso(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_reserva(db: Session, reserva_id: int) -> Optional[ReservaRecurso]:
    return db.query(ReservaRecurso).filter(ReservaRecurso.id == reserva_id).first()


def list_reservas(db: Session, evento_id: Optional[str] = None) -> List[ReservaRecurso]:
    q = db.query(ReservaRecurso)
    if evento_id is not None:
        q = q.filter(ReservaRecurso.evento_id == evento_id)
    return q.order_by(ReservaRecurso.bloqueo_inicio.asc()).all()


def update_reserva(
    db: Session, reserva_id: int, payload: ReservaRecursoCreate
) -> Optional[ReservaRecurso]:
    row = db.query(ReservaRecurso).filter(ReservaRecurso.id == reserva_id).first()
    if not row:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_reserva(db: Session, reserva_id: int) -> bool:
    row = db.query(ReservaRecurso).filter(ReservaRecurso.id == reserva_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True
