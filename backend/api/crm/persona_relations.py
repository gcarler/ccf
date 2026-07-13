import uuid
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.crm._shared import (
    _case_created_column,
    _get_scoped_family,
    _get_scoped_persona,
    _scope_by_user_sede_via_persona,
    _serialize_case,
    _serialize_task,
    case_query,
    prepare_case_for_output,
)
from backend.core.database import get_db
from backend.core.permissions import normalize_role, require_module_access
from backend.core.tenant import get_user_sede_id

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


def _serialize_persona_position(persona_position, position) -> dict:
    return {
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


@router.get("/personas/{persona_id}/communications", response_model=List[schemas.CommunicationLog])
def get_persona_communications(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Axioma 3: Communications sólo se exponen para personas en la sede del usuario."""
    persona = _get_scoped_persona(db, current_user, persona_id)
    query = (
        db.query(models.CommunicationLog)
        .join(models.Persona, models.CommunicationLog.persona_id == models.Persona.id)
        .filter(models.CommunicationLog.persona_id == persona.id)
    )
    query = _scope_by_user_sede_via_persona(db, current_user, query)
    return query.all()


@router.get("/personas/{persona_id}/ministries", response_model=List[dict])
def get_persona_ministries(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Devuelve todas las vinculaciones ministeriales de una persona con su rol.
    Axioma 3: persona debe estar en la sede del usuario.
    """
    persona = _get_scoped_persona(db, current_user, persona_id)
    rows = (
        db.query(models.PersonaMinistryAssignment)
        .filter(models.PersonaMinistryAssignment.persona_id == persona.id)
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


@router.get("/personas/{persona_id}/crm-perfil", response_model=dict)
def get_persona_crm_profile(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Devuelve el perfil CRM de una persona: roles, casos y seguimiento.
    Axioma 3: scope por sede via helper.
    """
    persona = _get_scoped_persona(db, current_user, persona_id)
    persona_uuid = persona.id

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
        case_query(db)
        .filter(
            models.CasoCRM.persona_id == persona_uuid,
            models.CasoCRM.deleted_at.is_(None),
        )
    )
    created_col = _case_created_column(db)
    if created_col is not None:
        cases = cases.order_by(created_col.desc()).all()
    else:
        cases = cases.order_by(models.CasoCRM.id.desc()).all()
    case_rows = [_serialize_case(prepare_case_for_output(db, case)) for case in cases]

    position_rows = [
        _serialize_persona_position(persona_position, position)
        for persona_position, position in positions
    ]

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


@router.get("/personas/{persona_id}/positions", response_model=List[dict])
def get_persona_positions(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Devuelve los cargos de una persona, siempre limitado por sede."""
    persona = _get_scoped_persona(db, current_user, persona_id)
    rows = (
        db.query(models.PersonaPosition, models.Position)
        .join(models.Position, models.Position.id == models.PersonaPosition.position_id)
        .filter(models.PersonaPosition.persona_id == persona.id)
        .order_by(
            models.PersonaPosition.is_active.desc(),
            models.PersonaPosition.start_date.desc(),
        )
        .all()
    )
    return [
        _serialize_persona_position(persona_position, position)
        for persona_position, position in rows
    ]


@router.get("/personas/{persona_id}/consolidation", response_model=dict)
def get_persona_consolidation(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Resumen de seguimiento pastoral/consolidacion de una persona por sede."""
    persona = _get_scoped_persona(db, current_user, persona_id)

    cases_q = case_query(db).filter(
        models.CasoCRM.persona_id == persona.id,
        models.CasoCRM.deleted_at.is_(None),
    )
    created_col = _case_created_column(db)
    if created_col is not None:
        cases = cases_q.order_by(created_col.desc()).all()
    else:
        cases = cases_q.order_by(models.CasoCRM.id.desc()).all()

    tasks = (
        db.query(models.TareaCRM)
        .filter(
            models.TareaCRM.persona_id == persona.id,
            models.TareaCRM.deleted_at.is_(None),
        )
        .order_by(models.TareaCRM.created_at.desc())
        .all()
    )

    communications_count = (
        db.query(models.CommunicationLog)
        .filter(models.CommunicationLog.persona_id == persona.id)
        .count()
    )

    open_tasks_count = sum(1 for task in tasks if task.status != "completed")
    case_rows = [_serialize_case(prepare_case_for_output(db, case)) for case in cases]
    task_rows = [_serialize_task(task) for task in tasks]

    return {
        "persona_id": str(persona.id),
        "persona": {
            "id": str(persona.id),
            "first_name": persona.first_name,
            "last_name": persona.last_name,
            "church_role": persona.church_role,
            "spiritual_status": persona.spiritual_status,
        },
        "summary": {
            "cases_count": len(case_rows),
            "tasks_count": len(task_rows),
            "open_tasks_count": open_tasks_count,
            "communications_count": communications_count,
        },
        "cases": case_rows,
        "tasks": task_rows,
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
    """Axioma 3: sólo se asignan posiciones a personas en la sede del usuario."""
    persona = _get_scoped_persona(db, current_user, persona_id)
    persona_uuid = persona.id
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
    """Axioma 3: sede scope via persona + check adicional sobre el assignment."""
    persona = _get_scoped_persona(db, current_user, persona_id)
    row = (
        db.query(models.PersonaPosition)
        .filter(
            models.PersonaPosition.id == persona_position_id,
            models.PersonaPosition.persona_id == persona.id,
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
    """Vincula a una persona a un ministerio con un rol especifico.
    Axioma 3: scope por sede via persona.
    """
    persona = _get_scoped_persona(db, current_user, persona_id)
    persona_uuid = persona.id
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
    """Actualiza el rol o estado de una vinculacion ministerial.
    Axioma 3: scope por sede via persona.
    """
    persona = _get_scoped_persona(db, current_user, persona_id)
    mm = (
        db.query(models.PersonaMinistryAssignment)
        .filter(
            models.PersonaMinistryAssignment.id == mm_id,
            models.PersonaMinistryAssignment.persona_id == persona.id,
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
    """Axioma 3: Family sin sede_id propio ⇒ filtramos por las Personas que la habitan."""
    user_sede = get_user_sede_id(db, current_user.id)
    families = crud.get_families(db, skip=skip, limit=limit)
    if not user_sede:
        return families
    family_ids = [f.id for f in families]
    if not family_ids:
        return []
    scoped = (
        db.query(models.Persona.family_id)
        .filter(
            models.Persona.family_id.in_(family_ids),
            models.Persona.sede_id == user_sede,
        )
        .distinct()
        .all()
    )
    allowed_ids = {row[0] for row in scoped}
    return [fam for fam in families if fam.id in allowed_ids]


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
    """Axioma 3: 404 si la familia no tiene personas en la sede del usuario."""
    _get_scoped_family(db, current_user, family_id)
    return crud.get_family_personas(db, family_id=family_id)
