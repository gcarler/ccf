from typing import List, Optional

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.auth import require_module_access
from backend.crud.crm import get_user_sede_id
from backend.core.database import get_db

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
    card_id: int,
    db: Session = Depends(get_db),
):
    """Elimina una tarjeta del tablero comunitario."""
    card = db.query(models.CommunityBoardCard).filter(models.CommunityBoardCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    card.deleted_at = datetime.utcnow()
    db.commit()
    return None


@router.get("/grupos", response_model=List[dict])
def list_community_cell_groups(db: Session = Depends(get_db)):
    """Lista grupos para la vista comunitaria."""
    grupos = db.query(models.GrupoEvangelismo).all()
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


@router.post("/grupos", response_model=dict)
def create_community_cell_group(
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
