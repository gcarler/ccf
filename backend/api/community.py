from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import crud, schemas, models
from backend.auth import require_active_user
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
    card = db.query(models.CommunityBoardCard).filter(
        models.CommunityBoardCard.id == card_id
    ).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    db.delete(card)
    db.commit()
    return None


@router.get("/glory-houses", response_model=List[dict])
def list_community_glory_houses(db: Session = Depends(get_db)):
    """Lista casas de gloria para la vista comunitaria."""
    houses = db.query(models.GloryHouse).all()
    return [
        {
            "id": h.id,
            "name": h.name,
            "leader": h.leader_name,
            "address": h.address,
            "members_count": len(h.members) if h.members else 0,
        }
        for h in houses
    ]


@router.post("/glory-houses", response_model=dict)
def create_community_glory_house(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Crea una nueva casa de gloria desde la vista comunitaria."""
    house = models.GloryHouse(
        name=payload.get("name", "Nueva Casa"),
        leader_name=payload.get("leader_name") or current_user.username,
        address=payload.get("address"),
    )
    db.add(house)
    db.commit()
    db.refresh(house)
    return {"id": house.id, "name": house.name, "leader_name": house.leader_name, "address": house.address}
