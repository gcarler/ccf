import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.core.database import get_db
from backend.core.permissions import get_current_user, require_admin
from backend.crud.crm import get_user_sede_id

router = APIRouter(prefix="/spiritual-life", tags=["Spiritual Life"])


@router.get("/milestones/{persona_id}", response_model=List[schemas.Milestone])
def get_persona_milestones(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Obtiene la linea de tiempo espiritual. Requiere estar autenticado."""
    # Axioma 3: verificar que la persona pertenece a la sede del usuario
    sede_id = get_user_sede_id(db, current_user.id)
    try:
        persona_uuid = uuid.UUID(str(persona_id))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="persona_id debe ser UUID") from None
    persona = db.query(models.Persona).filter(models.Persona.id == persona_uuid).first()
    if persona and sede_id and persona.sede_id and str(persona.sede_id) != str(sede_id):
        raise HTTPException(status_code=403, detail="Persona no pertenece a tu sede")
    return crud.get_milestones(db, persona_id=persona_uuid)


@router.post("/milestones", response_model=schemas.Milestone)
def create_spiritual_milestone(
    payload: schemas.MilestoneCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Solo administradores pueden registrar hitos oficiales."""
    return crud.create_milestone(
        db,
        persona_id=payload.persona_id,
        type=payload.type,
        event_date=payload.event_date.date(),
        minister_id=payload.minister_id,
    )
