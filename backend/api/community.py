from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.crud.crm import get_user_sede_id

router = APIRouter(prefix="/community", tags=["community"])


@router.get("/cards", response_model=List[schemas.CommunityBoardCard])
def list_community_cards(
    column_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return crud.get_community_cards(db, column_id=column_id)


@router.post("/cards", response_model=schemas.CommunityBoardCard, status_code=201)
def create_community_card(
    card: schemas.CommunityBoardCardCreate,
    db: Session = Depends(get_db),
):
    return crud.create_community_card(db, card)


@router.delete("/cards/{card_id}", status_code=204)
def delete_community_card(
    card_id: UUID,
    db: Session = Depends(get_db),
):
    """Elimina una tarjeta del tablero comunitario."""
    card = db.query(models.CommunityBoardCard).filter(models.CommunityBoardCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    card.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return None


@router.get("/grupos", response_model=List[dict])
def list_community_grupos(db: Session = Depends(get_db)):
    """Lista grupos para la vista comunitaria."""
    grupos = (
        db.query(models.GrupoEvangelismo)
        .filter(models.GrupoEvangelismo.deleted_at.is_(None))
        .all()
    )
    leader_ids = [g.lider_persona_id for g in grupos if g.lider_persona_id]
    leaders: dict = {}
    if leader_ids:
        rows = db.query(models.Persona).filter(models.Persona.id.in_(leader_ids)).all()
        leaders = {str(p.id): f"{p.first_name} {p.last_name}".strip() for p in rows}
    return [
        {
            "id": g.id,
            "name": g.nombre or f"Grupo {g.id}",
            "leader": leaders.get(str(g.lider_persona_id), "") if g.lider_persona_id else "",
            "total_personas": len(g.participantes) if g.participantes else 0,
        }
        for g in grupos
    ]


@router.get("/events", response_model=List[dict])
def list_community_events(db: Session = Depends(get_db)):
    """Lista eventos públicos para la vista comunitaria."""
    events = (
        db.query(models.EventoAgenda)
        .filter(
            models.EventoAgenda.deleted_at.is_(None),
            models.EventoAgenda.visibilidad.in_(["PUBLICO", "COMUNIDAD"]),
            models.EventoAgenda.estado == "ACTIVO",
        )
        .order_by(models.EventoAgenda.fecha_inicio)
        .all()
    )

    def _infer_category(title: str) -> str:
        lower = title.lower()
        if any(w in lower for w in ("joven", "juvenil", "youth")):
            return "Juveniles"
        if any(w in lower for w in ("estudio", "biblia", "celula", "grupo")):
            return "Estudios"
        if any(w in lower for w in ("mision", "misiones", "evangelismo", "calle")):
            return "Misiones"
        return "Servicios"

    return [
        {
            "id": str(e.id),
            "title": e.titulo,
            "description": e.descripcion or "",
            "date": e.fecha_inicio.isoformat() if e.fecha_inicio else "",
            "category": _infer_category(e.titulo),
            "location": e.ubicacion_texto or "",
            "attendees_count": len(
                [p for p in e.participantes if p.deleted_at is None]
            ),
        }
        for e in events
    ]


@router.post("/grupos", response_model=dict)
def create_community_grupo(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("community", "edit")),
):
    """Crea un nuevo grupo desde la vista comunitaria."""
    grupo = models.GrupoEvangelismo(
        nombre=payload.get("name", "Nuevo Grupo"),
        sede_id=get_user_sede_id(db, current_user.id) if hasattr(current_user, "id") else None,
    )
    db.add(grupo)
    db.commit()
    db.refresh(grupo)
    return {
        "id": grupo.id,
        "name": grupo.nombre,
    }
