from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.auth import require_pastor_or_admin
from backend.core.database import get_db
from backend.crud.crm import resolve_persona_id_for_user

router = APIRouter(tags=["CRM"])


@router.get("/personas", response_model=List[schemas.PersonaResponse])
def list_personas(
    search: Optional[str] = None,
    role: Optional[str] = None,
    estado_vital: Optional[str] = None,
    sex: Optional[str] = None,
    group_name: Optional[str] = None,
    membership_type: Optional[str] = None,
    id_type: Optional[str] = None,
    min_age: Optional[int] = Query(None, ge=0, le=120),
    max_age: Optional[int] = Query(None, ge=0, le=120),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    sort_by: Optional[str] = Query(None, description="Campo de ordenamiento"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Lista personas con búsqueda, paginación y ordenamiento. Filtrado por sede."""
    sede_id = crud.get_user_sede_id(db, current_user.id)
    return crud.search_personas(
        db, search=search, role=role, estado_vital=estado_vital,
        sex=sex, group_name=group_name, membership_type=membership_type,
        id_type=id_type, min_age=min_age, max_age=max_age,
        sede_id=sede_id, skip=skip, limit=limit, sort_by=sort_by, sort_dir=sort_dir,
    )


@router.get("/personas/me/profile")
def my_ministry_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Perfil ministerial del usuario autenticado."""
    persona_id = resolve_persona_id_for_user(db, current_user.id)
    persona = db.query(models.Persona).filter(models.Persona.id == persona_id).first() if persona_id else None
    if not persona:
        raise HTTPException(status_code=404, detail="No tienes un perfil ministerial vinculado")
    return schemas.PersonaResponse.model_validate(persona)


@router.get("/personas/{persona_id}", response_model=schemas.PersonaResponse)
def get_persona(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Obtiene una persona por UUID."""
    persona = crud.get_persona(db, persona_id)
    if not persona:
        raise HTTPException(404, detail="Persona no encontrada")
    return persona


@router.post("/personas", response_model=schemas.PersonaResponse)
def create_persona(
    payload: schemas.PersonaCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Crea una nueva persona."""
    return crud.create_persona(db, payload)


@router.put("/personas/{persona_id}", response_model=schemas.PersonaResponse)
def update_persona(
    persona_id: str,
    payload: schemas.PersonaUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Actualiza una persona existente."""
    persona = crud.update_persona(db, persona_id, payload)
    if not persona:
        raise HTTPException(404, detail="Persona no encontrada")
    return persona


@router.delete("/personas/{persona_id}")
def delete_persona(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Soft-delete: marca estado_vital = INACTIVO. Nunca eliminar físicamente."""
    if not crud.delete_persona(db, persona_id):
        raise HTTPException(404, detail="Persona no encontrada")
    return {"ok": True}


@router.get("/personas/{persona_id}/timeline")
def persona_timeline(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Obtiene la línea de tiempo de una persona."""
    timeline = crud.get_persona_timeline(db, persona_id)
    if not timeline:
        raise HTTPException(404, detail="Persona no encontrada o sin actividad")
    return timeline


@router.get("/personas/{persona_id}/donations")
def persona_donations(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Obtiene las donaciones de una persona."""
    return crud.get_persona_donations(db, persona_id)
