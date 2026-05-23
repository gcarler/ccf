from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.auth import get_current_user, require_admin
from backend.core.database import get_db

router = APIRouter(prefix="/spiritual-life", tags=["Spiritual Life"])


@router.get("/milestones/{person_id}", response_model=List[schemas.Milestone])
def get_member_milestones(
    person_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Obtiene la linea de tiempo espiritual. Requiere estar autenticado."""
    return crud.get_milestones(db, person_id=person_id)


@router.post("/milestones", response_model=schemas.Milestone)
def create_spiritual_milestone(
    payload: schemas.MilestoneCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Solo administradores pueden registrar hitos oficiales."""
    return crud.create_milestone(
        db,
        person_id=payload.person_id,
        type=payload.type,
        event_date=payload.event_date.date(),
        minister_id=payload.minister_id,
    )
