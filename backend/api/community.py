from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend import crud, schemas
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
