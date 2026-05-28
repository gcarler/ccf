"""Agenda / Calendario Unificado — API REST.

Endpoints:
  Recursos:     CRUD
  Eventos:      CRUD + by-date-range + participantes
  Participantes: CRUD
  Reservas:     CRUD
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.auth import require_pastor_or_admin
from backend.core.database import get_db
from backend.crud import agenda_core as crud
from backend.schemas.agenda_core import (
    EventoAgendaCreate, EventoAgendaResponse,
    ParticipanteEventoCreate, ParticipanteEventoResponse,
    RecursoFisicoCreate, RecursoFisicoResponse,
    ReservaRecursoCreate, ReservaRecursoResponse,
)

router = APIRouter(prefix="/agenda-core", tags=["Agenda"])


# ──────────────────────────────────────────────
# RECURSOS FÍSICOS
# ──────────────────────────────────────────────

@router.get("/recursos", response_model=List[RecursoFisicoResponse])
def list_recursos(
    sede_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.list_recursos(db, sede_id=sede_id)


@router.post("/recursos", response_model=RecursoFisicoResponse)
def create_recurso(
    payload: RecursoFisicoCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.create_recurso(db, payload)


@router.get("/recursos/{recurso_id}", response_model=RecursoFisicoResponse)
def get_recurso(
    recurso_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    obj = crud.get_recurso(db, recurso_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    return obj


@router.put("/recursos/{recurso_id}", response_model=RecursoFisicoResponse)
def update_recurso(
    recurso_id: int,
    payload: RecursoFisicoCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    obj = crud.update_recurso(db, recurso_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    return obj


@router.delete("/recursos/{recurso_id}", status_code=204)
def delete_recurso(
    recurso_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    if not crud.delete_recurso(db, recurso_id):
        raise HTTPException(status_code=404, detail="Recurso no encontrado")


# ──────────────────────────────────────────────
# EVENTOS
# ──────────────────────────────────────────────

@router.get("/eventos", response_model=List[EventoAgendaResponse])
def list_eventos(
    sede_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.list_eventos(db, sede_id=sede_id)


@router.get("/eventos/by-date-range", response_model=List[EventoAgendaResponse])
def list_eventos_by_date_range(
    sede_id: int = Query(...),
    start: datetime = Query(...),
    end: datetime = Query(...),
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.list_eventos_by_date_range(db, sede_id=sede_id, start=start, end=end)


@router.post("/eventos", response_model=EventoAgendaResponse)
def create_evento(
    payload: EventoAgendaCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.create_evento(db, payload)


@router.get("/eventos/{evento_id}", response_model=EventoAgendaResponse)
def get_evento(
    evento_id: str,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    obj = crud.get_evento(db, evento_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return obj


@router.put("/eventos/{evento_id}", response_model=EventoAgendaResponse)
def update_evento(
    evento_id: str,
    payload: EventoAgendaCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    obj = crud.update_evento(db, evento_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return obj


@router.delete("/eventos/{evento_id}", status_code=204)
def delete_evento(
    evento_id: str,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    if not crud.delete_evento(db, evento_id):
        raise HTTPException(status_code=404, detail="Evento no encontrado")


# ──────────────────────────────────────────────
# PARTICIPANTES
# ──────────────────────────────────────────────

@router.get(
    "/eventos/{evento_id}/participantes",
    response_model=List[ParticipanteEventoResponse],
)
def list_participantes(
    evento_id: str,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.list_participantes(db, evento_id)


@router.post("/participantes", response_model=ParticipanteEventoResponse)
def create_participante(
    payload: ParticipanteEventoCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.create_participante(db, payload)


@router.get("/participantes/{participante_id}", response_model=ParticipanteEventoResponse)
def get_participante(
    participante_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    obj = crud.get_participante(db, participante_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Participante no encontrado")
    return obj


@router.put("/participantes/{participante_id}", response_model=ParticipanteEventoResponse)
def update_participante(
    participante_id: int,
    payload: ParticipanteEventoCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    obj = crud.update_participante(db, participante_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Participante no encontrado")
    return obj


@router.delete("/participantes/{participante_id}", status_code=204)
def delete_participante(
    participante_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    if not crud.delete_participante(db, participante_id):
        raise HTTPException(status_code=404, detail="Participante no encontrado")


# ──────────────────────────────────────────────
# RESERVAS
# ──────────────────────────────────────────────

@router.get("/reservas", response_model=List[ReservaRecursoResponse])
def list_reservas(
    evento_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.list_reservas(db, evento_id=evento_id)


@router.post("/reservas", response_model=ReservaRecursoResponse)
def create_reserva(
    payload: ReservaRecursoCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.create_reserva(db, payload)


@router.get("/reservas/{reserva_id}", response_model=ReservaRecursoResponse)
def get_reserva(
    reserva_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    obj = crud.get_reserva(db, reserva_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return obj


@router.put("/reservas/{reserva_id}", response_model=ReservaRecursoResponse)
def update_reserva(
    reserva_id: int,
    payload: ReservaRecursoCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    obj = crud.update_reserva(db, reserva_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return obj


@router.delete("/reservas/{reserva_id}", status_code=204)
def delete_reserva(
    reserva_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    if not crud.delete_reserva(db, reserva_id):
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
