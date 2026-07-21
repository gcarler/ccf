import uuid
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.crud.crm import get_user_sede_id

router = APIRouter(prefix="/spiritual-life", tags=["Spiritual Life"])


def _get_user_sede_id(db: Session, user_id: UUID) -> Optional[UUID]:
    try:
        sede_id = get_user_sede_id(db, user_id)
        return UUID(str(sede_id)) if sede_id else None
    except Exception:
        return None


def _assert_persona_in_sede(db: Session, persona_id: UUID, user_sede_id: Optional[UUID]) -> models.Persona:
    persona = db.query(models.Persona).filter(models.Persona.id == persona_id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    if user_sede_id is not None and persona.sede_id and str(persona.sede_id) != str(user_sede_id):
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


def _assert_milestone_in_sede(db: Session, milestone_id: UUID, user_sede_id: Optional[UUID]) -> models.SpiritualMilestone:
    milestone = crud.get_milestone(db, milestone_id)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    if user_sede_id is not None and milestone.sede_id and str(milestone.sede_id) != str(user_sede_id):
        raise HTTPException(status_code=404, detail="Milestone not found")
    return milestone


@router.get("/milestones", response_model=List[schemas.Milestone])
def list_milestones(
    persona_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("spiritual_life", "read")),
):
    """Listar hitos espirituales. Filtra por sede del actor."""
    user_sede_id = _get_user_sede_id(db, current_user.id)
    if persona_id:
        _assert_persona_in_sede(db, persona_id, user_sede_id)
        return crud.get_milestones(db, persona_id=persona_id)
    if user_sede_id is None:
        return crud.list_milestones(db)
    return crud.list_milestones(db, sede_id=user_sede_id)


@router.get("/milestones/{persona_id}", response_model=List[schemas.Milestone])
def get_persona_milestones(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("spiritual_life", "read")),
):
    """Obtiene la linea de tiempo espiritual de una persona."""
    try:
        persona_uuid = uuid.UUID(str(persona_id))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="persona_id debe ser UUID") from None

    user_sede_id = _get_user_sede_id(db, current_user.id)
    _assert_persona_in_sede(db, persona_uuid, user_sede_id)
    return crud.get_milestones(db, persona_id=persona_uuid)


@router.post("/milestones", response_model=schemas.Milestone)
def create_spiritual_milestone(
    payload: schemas.MilestoneCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("spiritual_life", "manage")),
):
    """Crear un hito espiritual. Requiere spiritual_life:manage."""
    user_sede_id = _get_user_sede_id(db, current_user.id)
    persona = _assert_persona_in_sede(db, payload.persona_id, user_sede_id)

    minister_uuid = None
    if payload.minister_id:
        minister = db.query(models.Persona).filter(models.Persona.id == payload.minister_id).first()
        if not minister:
            raise HTTPException(status_code=404, detail="Minister not found")
        if user_sede_id is not None and minister.sede_id and str(minister.sede_id) != str(user_sede_id):
            raise HTTPException(status_code=404, detail="Minister not found")
        minister_uuid = payload.minister_id

    return crud.create_milestone(
        db,
        persona_id=payload.persona_id,
        type=payload.type,
        event_date=payload.event_date,
        minister_id=minister_uuid,
        sede_id=persona.sede_id,
        notes=payload.notes,
    )


@router.get("/milestone/{milestone_id}", response_model=schemas.Milestone)
def get_milestone(
    milestone_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("spiritual_life", "read")),
):
    """Obtener el detalle de un hito espiritual."""
    user_sede_id = _get_user_sede_id(db, current_user.id)
    return _assert_milestone_in_sede(db, milestone_id, user_sede_id)


@router.patch("/milestone/{milestone_id}", response_model=schemas.Milestone)
def update_spiritual_milestone(
    milestone_id: UUID,
    payload: schemas.MilestoneUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("spiritual_life", "edit")),
):
    """Actualizar un hito espiritual. Requiere spiritual_life:edit."""
    user_sede_id = _get_user_sede_id(db, current_user.id)
    milestone = _assert_milestone_in_sede(db, milestone_id, user_sede_id)

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=422, detail="No fields to update")

    if payload.minister_id:
        minister = db.query(models.Persona).filter(models.Persona.id == payload.minister_id).first()
        if not minister:
            raise HTTPException(status_code=404, detail="Minister not found")
        if user_sede_id is not None and minister.sede_id and str(minister.sede_id) != str(user_sede_id):
            raise HTTPException(status_code=404, detail="Minister not found")

    updated = crud.update_milestone(db, milestone_id=milestone.id, **update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return updated



@router.delete("/milestone/{milestone_id}", status_code=204)
def delete_spiritual_milestone(
    milestone_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("spiritual_life", "edit")),
):
    """Eliminar (soft delete) un hito espiritual. Requiere spiritual_life:edit."""
    user_sede_id = _get_user_sede_id(db, current_user.id)
    _assert_milestone_in_sede(db, milestone_id, user_sede_id)
    deleted = crud.delete_milestone(db, milestone_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return None
