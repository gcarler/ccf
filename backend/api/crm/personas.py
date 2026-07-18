from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.crm._shared import _get_scoped_persona
from backend.core.database import get_db
from backend.core.permissions import require_module_access, require_permission
from backend.core.tenant import get_user_sede_id
from backend.crud.crm_.shared import resolve_persona_id_for_user

router = APIRouter(tags=["CRM"])


@router.get("/personas", response_model=List[schemas.PersonaResponse])
def list_personas(
    search: Optional[str] = None,
    role: Optional[str] = None,
    estado_vital: Optional[str] = None,
    sex: Optional[str] = None,
    group_name: Optional[str] = None,
    participation_type: Optional[str] = None,
    id_type: Optional[str] = None,
    min_age: Optional[int] = Query(None, ge=0, le=120),
    max_age: Optional[int] = Query(None, ge=0, le=120),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    sort_by: Optional[str] = Query(None, description="Campo de ordenamiento"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Lista personas con búsqueda, paginación y ordenamiento. Filtrado por sede."""
    sede_id = get_user_sede_id(db, current_user.id)
    return crud.search_personas(
        db,
        search=search,
        role=role,
        estado_vital=estado_vital,
        sex=sex,
        group_name=group_name,
        participation_type=participation_type,
        id_type=id_type,
        min_age=min_age,
        max_age=max_age,
        sede_id=sede_id,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/personas/page", response_model=schemas.PersonaPageResponse)
def list_personas_page(
    search: Optional[str] = None,
    role: Optional[str] = None,
    estado_vital: Optional[str] = None,
    sex: Optional[str] = None,
    group_name: Optional[str] = None,
    participation_type: Optional[str] = None,
    id_type: Optional[str] = None,
    min_age: Optional[int] = Query(None, ge=0, le=120),
    max_age: Optional[int] = Query(None, ge=0, le=120),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by: Optional[str] = Query(None, description="Campo de ordenamiento"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Lista personas con búsqueda y paginación reales, filtrado por sede."""
    sede_id = get_user_sede_id(db, current_user.id)
    page = crud.search_personas_page(
        db,
        search=search,
        role=role,
        estado_vital=estado_vital,
        sex=sex,
        group_name=group_name,
        participation_type=participation_type,
        id_type=id_type,
        min_age=min_age,
        max_age=max_age,
        sede_id=sede_id,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return schemas.PersonaPageResponse(**page)


@router.get("/personas/me/profile")
def my_ministry_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Perfil ministerial del usuario autenticado."""
    persona_id = resolve_persona_id_for_user(db, current_user.id)
    persona = crud.get_persona(db, persona_id) if persona_id else None
    if not persona:
        raise HTTPException(status_code=404, detail="No tienes un perfil ministerial vinculado")
    return schemas.PersonaResponse.model_validate(persona)


@router.patch("/personas/me/profile", response_model=schemas.PersonaResponse)
def update_my_profile(
    payload: schemas.PersonaSelfProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("profile:manage")),
):
    """Actualiza solo el perfil personal de la persona autenticada."""
    persona_id = resolve_persona_id_for_user(db, current_user.id)
    if not persona_id:
        raise HTTPException(status_code=404, detail="No tienes un perfil personal vinculado")

    persona = crud.update_persona(db, persona_id, schemas.PersonaUpdate(**payload.model_dump(exclude_unset=True)))
    if not persona:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return persona


@router.get("/personas/{persona_id}", response_model=schemas.PersonaResponse)
def get_persona(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Obtiene una persona por UUID. Axioma 3: scope por sede_id del usuario."""
    persona = _get_scoped_persona(db, current_user, persona_id)
    from backend.crud.crm_.health import update_pastoral_health

    update_pastoral_health(db, persona.id)
    return crud.get_persona(db, persona.id)


@router.get("/personas/{persona_id}/mentor-candidates", response_model=List[schemas.PersonaMentorCandidate])
def mentor_candidates(
    persona_id: str,
    q: Optional[str] = None,
    limit: int = Query(12, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Lista candidatos de mentoría ordenados por ajuste ministerial."""
    persona = _get_scoped_persona(db, current_user, persona_id)
    sede_id = get_user_sede_id(db, current_user.id)
    candidates = crud.list_mentor_candidates(db, str(persona.id), search=q, limit=limit, sede_id=sede_id)
    return [schemas.PersonaMentorCandidate.model_validate(candidate) for candidate in candidates]


@router.post("/personas/{persona_id}/mentorship", response_model=schemas.PersonaMentorshipResponse)
def assign_mentorship(
    persona_id: str,
    payload: schemas.PersonaMentorshipCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Asigna o reemplaza la mentoría de una persona dentro de su misma sede."""
    persona = _get_scoped_persona(db, current_user, persona_id)
    assigned = crud.assign_persona_mentor(
        db,
        str(persona.id),
        str(payload.mentor_persona_id),
        assigned_by_user_id=str(current_user.id),
        notes=payload.notes,
    )
    return schemas.PersonaMentorshipResponse.model_validate(assigned)


@router.post("/personas", response_model=schemas.PersonaResponse)
def create_persona(
    payload: schemas.PersonaCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Crea una nueva persona con sede_id auto-asignado."""
    user_sede = get_user_sede_id(db, current_user.id)
    if not user_sede:
        raise HTTPException(status_code=400, detail="El usuario no tiene sede asignada")
    data = payload.model_dump()
    data["sede_id"] = user_sede
    return crud.create_persona(db, schemas.PersonaCreate(**data))


@router.put("/personas/{persona_id}", response_model=schemas.PersonaResponse)
def update_persona(
    persona_id: str,
    payload: schemas.PersonaUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Actualiza una persona existente. Axioma 3: 404 si la persona está fuera de la sede."""
    _get_scoped_persona(db, current_user, persona_id)
    persona = crud.update_persona(db, persona_id, payload)
    if not persona:
        raise HTTPException(404, detail="Persona no encontrada")
    return persona


@router.patch("/personas/{persona_id}", response_model=schemas.PersonaResponse)
def patch_persona(
    persona_id: str,
    payload: schemas.PersonaUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Actualización parcial de una persona (PATCH). Axioma 3: 404 cross-sede."""
    _get_scoped_persona(db, current_user, persona_id)
    persona = crud.update_persona(db, persona_id, payload)
    if not persona:
        raise HTTPException(404, detail="Persona no encontrada")
    return persona


@router.delete("/personas/{persona_id}")
def delete_persona(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Soft-delete: marca estado_vital = INACTIVO. Nunca eliminar físicamente.
    Axioma 3: sede scope; retorna 404 si la persona es de otra sede.
    """
    _get_scoped_persona(db, current_user, persona_id)
    if not crud.delete_persona(db, persona_id):
        raise HTTPException(404, detail="Persona no encontrada")
    return {"ok": True}


@router.get("/personas/{persona_id}/timeline")
def persona_timeline(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Obtiene la línea de tiempo de una persona. Axioma 3: scope por sede."""
    _get_scoped_persona(db, current_user, persona_id)
    timeline = crud.get_persona_timeline(db, persona_id)
    if not timeline:
        raise HTTPException(404, detail="Persona no encontrada o sin actividad")
    return timeline


@router.get("/personas/{persona_id}/donations")
def persona_donations(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Obtiene las donaciones de una persona. Axioma 3: scope por sede de la
    persona (los montos, fechas y propósito de donación NO deben cruzar sedes).
    """
    _get_scoped_persona(db, current_user, persona_id)
    return crud.get_persona_donations(db, persona_id)
