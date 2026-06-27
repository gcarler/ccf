import uuid
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.crm._shared import _serialize_case
from backend.core.permissions import normalize_role, require_module_access
from backend.core.database import get_db

router = APIRouter(tags=["CRM"])


def _parse_uuid(val: str | uuid.UUID) -> uuid.UUID:
    if isinstance(val, uuid.UUID):
        return val
    return uuid.UUID(str(val))


def _get_user_role(user: models.User) -> str:
    role = normalize_role(str(getattr(user, "role", "")))
    if not role and hasattr(user, "rol_plataforma") and user.rol_plataforma:
        role = normalize_role(user.rol_plataforma.nombre)
    return role


@router.get("/personas/{persona_id}/communications", response_model=List[schemas.CommunicationLog])
def get_persona_communications(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    persona_uuid = _parse_uuid(persona_id)
    return (
        db.query(models.CommunicationLog)
        .filter(models.CommunicationLog.persona_id == persona_uuid)
        .all()
    )


@router.get("/personas/{persona_id}/ministries", response_model=List[dict])
def get_persona_ministries(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Devuelve todas las vinculaciones ministeriales de una persona con su rol."""
    persona_uuid = _parse_uuid(persona_id)
    rows = (
        db.query(models.PersonaMinistryAssignment)
        .filter(models.PersonaMinistryAssignment.persona_id == persona_uuid)
        .order_by(
            models.PersonaMinistryAssignment.is_active.desc(),
            models.PersonaMinistryAssignment.start_date.desc(),
        )
        .all()
    )
    result = []
    for mm in rows:
        ministry = (
            db.query(models.Ministry)
            .filter(models.Ministry.id == mm.ministry_id)
            .first()
        )
        result.append(
            {
                "id": mm.id,
                "persona_id": mm.persona_id,
                "ministry_id": mm.ministry_id,
                "ministry_name": ministry.name if ministry else None,
                "ministry": (
                    {"id": ministry.id, "name": ministry.name} if ministry else None
                ),
                "role": mm.role,
                "start_date": mm.start_date.isoformat() if mm.start_date else None,
                "end_date": mm.end_date.isoformat() if mm.end_date else None,
                "is_active": mm.is_active,
                "notes": mm.notes,
            }
        )
    return result


@router.get("/personas/{persona_id}/consolidation", response_model=dict)
def get_persona_consolidation_profile(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Devuelve el perfil de consolidación de una persona: roles, casos y seguimiento."""
    persona_uuid = _parse_uuid(persona_id)
    persona = db.query(models.Persona).filter(models.Persona.id == persona_uuid).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    positions = (
        db.query(models.PersonaPosition, models.Position)
        .join(models.Position, models.Position.id == models.PersonaPosition.position_id)
        .filter(models.PersonaPosition.persona_id == persona_uuid)
        .order_by(
            models.PersonaPosition.is_active.desc(),
            models.PersonaPosition.start_date.desc(),
        )
        .all()
    )

    cases = (
        db.query(models.CasoCRM)
        .filter(
            models.CasoCRM.persona_id == persona_uuid,
            models.CasoCRM.deleted_at.is_(None),
        )
        .order_by(models.CasoCRM.fecha_creacion.desc())
        .all()
    )
    case_rows = [_serialize_case(case) for case in cases]

    position_rows = []
    for persona_position, position in positions:
        position_rows.append(
            {
                "id": persona_position.id,
                "persona_id": persona_position.persona_id,
                "position_id": persona_position.position_id,
                "position_name": position.name if position else None,
                "category": position.category if position else None,
                "start_date": (
                    persona_position.start_date.isoformat()
                    if persona_position.start_date
                    else None
                ),
                "end_date": (
                    persona_position.end_date.isoformat()
                    if persona_position.end_date
                    else None
                ),
                "is_active": persona_position.is_active,
                "notes": persona_position.notes,
            }
        )

    return {
        "persona": {
            "id": str(persona.id),
            "first_name": persona.first_name,
            "last_name": persona.last_name,
            "church_role": persona.church_role,
            "spiritual_status": persona.spiritual_status,
        },
        "positions": position_rows,
        "cases": case_rows,
    }


@router.get("/positions", response_model=List[schemas.Position])
def list_positions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    return (
        db.query(models.Position)
        .order_by(models.Position.is_active.desc(), models.Position.name.asc())
        .all()
    )


@router.post("/positions", response_model=schemas.Position)
def create_position(
    payload: schemas.PositionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    existing = (
        db.query(models.Position).filter(models.Position.name == payload.name).first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Position already exists")
    row = models.Position(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/positions/{position_id}", response_model=schemas.Position)
def update_position(
    position_id: UUID,
    payload: schemas.PositionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    row = db.query(models.Position).filter(models.Position.id == position_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Position not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@router.post("/personas/{persona_id}/positions", response_model=dict)
def assign_persona_position(
    persona_id: str,
    payload: schemas.PersonaPositionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    persona_uuid = _parse_uuid(persona_id)
    persona = db.query(models.Persona).filter(models.Persona.id == persona_uuid).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    position = (
        db.query(models.Position)
        .filter(models.Position.id == payload.position_id)
        .first()
    )
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    existing = (
        db.query(models.PersonaPosition)
        .filter(
            models.PersonaPosition.persona_id == persona_uuid,
            models.PersonaPosition.position_id == payload.position_id,
            models.PersonaPosition.start_date == payload.start_date,
        )
        .first()
    )
    if existing:
        existing.end_date = payload.end_date
        existing.is_active = payload.is_active
        existing.notes = payload.notes
        db.commit()
        db.refresh(existing)
        return {"id": existing.id, "updated": True, "position": position.name}

    row = models.PersonaPosition(
        persona_id=persona_uuid,
        position_id=payload.position_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_active=payload.is_active,
        notes=payload.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "created": True, "position": position.name}


@router.patch("/personas/{persona_id}/positions/{persona_position_id}", response_model=dict)
def update_persona_position(
    persona_id: str,
    persona_position_id: UUID,
    payload: schemas.PersonaPositionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    persona_uuid = _parse_uuid(persona_id)
    row = (
        db.query(models.PersonaPosition)
        .filter(
            models.PersonaPosition.id == persona_position_id,
            models.PersonaPosition.persona_id == persona_uuid,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Persona position not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "updated": True}


@router.post("/personas/{persona_id}/ministries", response_model=dict)
def assign_persona_ministry(
    persona_id: str,
    payload: schemas.PersonaMinistryAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Vincula a un miembro a un ministerio con un rol especifico."""
    persona_uuid = _parse_uuid(persona_id)
    existing = (
        db.query(models.PersonaMinistryAssignment)
        .filter(
            models.PersonaMinistryAssignment.persona_id == persona_uuid,
            models.PersonaMinistryAssignment.ministry_id == payload.ministry_id,
        )
        .first()
    )
    if existing:
        existing.role = payload.role
        existing.is_active = True
        existing.notes = payload.notes
        db.commit()
        db.refresh(existing)
        return {"id": existing.id, "updated": True}
    mm = models.PersonaMinistryAssignment(
        persona_id=persona_uuid,
        ministry_id=payload.ministry_id,
        role=payload.role,
        notes=payload.notes,
        is_active=True,
    )
    db.add(mm)
    db.commit()
    db.refresh(mm)
    return {"id": mm.id, "created": True}


@router.patch("/personas/{persona_id}/ministries/{mm_id}", response_model=dict)
def update_persona_ministry(
    persona_id: str,
    mm_id: UUID,
    payload: schemas.PersonaMinistryAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    """Actualiza el rol o estado de una vinculacion ministerial."""
    persona_uuid = _parse_uuid(persona_id)
    mm = (
        db.query(models.PersonaMinistryAssignment)
        .filter(
            models.PersonaMinistryAssignment.id == mm_id,
            models.PersonaMinistryAssignment.persona_id == persona_uuid,
        )
        .first()
    )
    if not mm:
        raise HTTPException(status_code=404, detail="Vinculacion no encontrada")
    if payload.role is not None:
        mm.role = payload.role
    if payload.is_active is not None:
        mm.is_active = payload.is_active
    if payload.end_date is not None:
        mm.end_date = payload.end_date
    if payload.notes is not None:
        mm.notes = payload.notes
    db.commit()
    return {"id": mm.id, "updated": True}


# --- COLOMBIAN DEPARTMENTS & CITIES ENDPOINTS ---


@router.get("/colombian-departments", response_model=List[schemas.ColombianDepartment])
def list_colombian_departments(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Devuelve la lista de los 32 departamentos de Colombia + Bogotá D.C."""
    return (
        db.query(models.ColombianDepartment)
        .order_by(models.ColombianDepartment.name)
        .all()
    )


@router.get("/colombian-departments/{department_id}/cities", response_model=List[schemas.ColombianCity])
def list_cities_by_department(
    department_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Devuelve las ciudades de un departamento específico."""
    department = (
        db.query(models.ColombianDepartment)
        .filter(models.ColombianDepartment.id == department_id)
        .first()
    )
    if not department:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    return (
        db.query(models.ColombianCity)
        .filter(models.ColombianCity.department_id == department_id)
        .order_by(models.ColombianCity.name)
        .all()
    )


# --- FAMILIES ENDPOINTS ---


@router.get("/families/", response_model=List[schemas.Family])
def list_families(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    return crud.get_families(db, skip=skip, limit=limit)


@router.post("/families/", response_model=dict)
def create_new_family(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "edit")),
):
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    fam = crud.create_family(db, name)
    return {"id": fam.id, "name": fam.name}


@router.get("/family/{family_id}", response_model=List[dict])
def get_family(
    family_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    return crud.get_family_personas(db, family_id=family_id)
