import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.auth import (normalize_role, require_admin,
                          require_module_access, require_pastor_or_admin)
from backend.core.audit import record_admin_action
from backend.core.database import get_db

router = APIRouter(tags=["CRM"])


# --- MEMBERS ENDPOINTS ---


@router.get("/personas", response_model=List[schemas.Persona])
def list_personas(
    search: Optional[str] = None,
    role: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    sort_by: Optional[str] = Query(None, description="Campo de ordenamiento: first_name, last_name, email, church_role, spiritual_status, created_at"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Lista miembros con búsqueda, paginación y ordenamiento. Filtrado por sede del usuario."""
    sede_id = crud.get_user_sede_id(db, current_user.id)
    return crud.search_members(db, search=search, role=role, sede_id=sede_id, skip=skip, limit=limit, sort_by=sort_by, sort_dir=sort_dir)


@router.get("/personas/paginated")
def list_members_paginated(
    search: Optional[str] = None,
    role: Optional[str] = None,
    spiritual_status: Optional[str] = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort_by: Optional[str] = Query(None),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Endpoint paginado para AG Grid server-side. Retorna { items: [...], total: N }. Filtrado por sede."""
    sede_id = crud.get_user_sede_id(db, current_user.id)
    return crud.search_members_paginated(
        db,
        search=search,
        role=role,
        spiritual_status=spiritual_status,
        sede_id=sede_id,
        offset=offset,
        limit=limit,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.post("/personas/", response_model=schemas.Persona)
def create_persona(
    payload: schemas.PersonaCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Registra un nuevo miembro en el CRM."""
    return crud.create_persona(db, payload)


@router.get("/personas/me", response_model=dict)
def get_my_crm_card(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Devuelve la tarjeta de miembro del usuario actual vinculada por user_id."""
    persona = (
        db.query(models.Persona).filter(models.Persona.user_id == current_user.id).first()
    )
    if persona:
        return {
            "id": persona.id,
            "first_name": persona.first_name,
            "last_name": persona.last_name,
            "church_role": persona.church_role,
            "qr_code": f"PRS-{persona.id}-{uuid.uuid4().hex[:6]}",
        }
    return {
        "id": 0,
        "first_name": current_user.username,
        "last_name": "Usuario",
        "church_role": current_user.role,
        "qr_code": f"USR-{current_user.id}-{uuid.uuid4().hex[:6]}",
    }


@router.get("/personas/me/profile", response_model=dict)
def get_my_ministry_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Perfil ministerial completo del usuario autenticado: datos del miembro, oficios, habilidades, badges y nivel."""
    persona = (
        db.query(models.Persona).filter(models.Persona.user_id == current_user.id).first()
    )

    # ── Positions (Oficios Eclesiásticos) ──────────────────────────
    positions = []
    if persona:
        member_positions = (
            db.query(models.MemberPosition, models.Position)
            .join(models.Position, models.Position.id == models.MemberPosition.position_id)
            .filter(models.MemberPosition.persona_id == persona.id)
            .order_by(models.MemberPosition.is_active.desc(), models.MemberPosition.start_date.desc())
            .all()
        )
        for mp, pos in member_positions:
            positions.append({
                "id": mp.id,
                "position_name": pos.name,
                "category": pos.category,
                "is_active": mp.is_active,
                "start_date": mp.start_date.isoformat() if mp.start_date else None,
                "end_date": mp.end_date.isoformat() if mp.end_date else None,
            })

    # ── Skills (Habilidades) ──────────────────────────────────────
    skills = []
    if persona:
        skills = sorted(
            row.name
            for row in (
                db.query(models.VolunteerSkill)
                .join(
                    models.member_volunteer_skills,
                    models.member_volunteer_skills.c.skill_id == models.VolunteerSkill.id,
                )
                .filter(models.member_volunteer_skills.c.persona_id == persona.id)
                .all()
            )
            if row.name
        )

    # ── Badges (Logros) ────────────────────────────────────────────
    badges = []
    user_badges = (
        db.query(models.UserBadge)
        .filter(models.UserBadge.user_id == current_user.id)
        .all()
    )
    for ub in user_badges:
        badge = db.query(models.Badge).filter(models.Badge.id == ub.badge_id).first()
        if badge:
            badges.append({
                "id": badge.id,
                "name": badge.name,
                "description": badge.description,
                "icon_key": badge.icon_key,
                "xp_reward": badge.xp_reward,
                "earned_at": ub.earned_at.isoformat() if ub.earned_at else None,
            })

    # ── Level & XP ─────────────────────────────────────────────────
    level_info = {"title": None, "min_xp": 0, "next_title": None, "next_min_xp": None}
    if current_user.current_level_id:
        current_level = (
            db.query(models.Level)
            .filter(models.Level.id == current_user.current_level_id)
            .first()
        )
        if current_level:
            next_level = (
                db.query(models.Level)
                .filter(models.Level.min_xp > current_level.min_xp)
                .order_by(models.Level.min_xp.asc())
                .first()
            )
            level_info = {
                "title": current_level.title,
                "min_xp": current_level.min_xp,
                "icon_key": current_level.icon_key,
                "next_title": next_level.title if next_level else None,
                "next_min_xp": next_level.min_xp if next_level else None,
            }

    return {
        "member": {
            "id": persona.id if persona else None,
            "first_name": persona.first_name if persona else current_user.username,
            "last_name": persona.last_name if persona else "",
            "church_role": persona.church_role if persona else current_user.role,
            "spiritual_status": persona.spiritual_status if persona else None,
            "registration_date": (
                persona.registration_date.isoformat() if persona and persona.registration_date else None
            ),
        },
        "positions": positions,
        "skills": skills,
        "badges": badges,
        "xp": current_user.xp or 0,
        "level": level_info,
    }


@router.get("/personas/donations", response_model=List[dict])
def list_all_member_donations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    donations = (
        db.query(models.Donation).order_by(models.Donation.created_at.desc()).all()
    )
    result = []
    for donation in donations:
        donor_name = donation.donor_name
        if not donor_name and donation.persona:
            donor_name = f"{donation.persona.first_name} {donation.persona.last_name}"
        result.append(
            {
                "id": donation.id,
                "donor": donor_name or "Donante anonimo",
                "amount": donation.amount,
                "type": donation.donation_type,
                "date": (
                    donation.created_at.isoformat() if donation.created_at else None
                ),
                "status": donation.status,
                "reference_code": donation.reference_code,
                "persona_id": donation.persona_id,
            }
        )
    return result


@router.get("/personas/{persona_id}", response_model=schemas.Persona)
def get_persona(
    persona_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    """Obtiene el detalle de un miembro con validacion de propiedad (IDOR)."""
    persona = db.query(models.Persona).filter(models.Persona.id == persona_id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    # Check if user is looking at their own profile OR is a pastor/admin
    is_self = persona.user_id == current_user.id
    is_staff = normalize_role(str(current_user.role)) in [
        "admin",
        "pastor",
        "coordinador",
    ]

    if not is_self and not is_staff:
        raise HTTPException(
            status_code=403, detail="No autorizado para ver este perfil"
        )

    return persona


@router.patch("/personas/{persona_id}", response_model=schemas.Persona)
def update_persona(
    persona_id: int,
    payload: schemas.PersonaUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Actualiza datos de un miembro con persistencia y auditoria."""
    persona = crud.update_persona(db, persona_id=persona_id, payload=payload)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    record_admin_action(
        db,
        current_user,
        action="update_persona",
        resource_type="persona",
        resource_id=str(persona.id),
        metadata=payload.model_dump(exclude_unset=True),
    )
    return persona


@router.delete("/personas/{persona_id}", status_code=204)
def delete_persona(
    persona_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Soft-delete: marca estado_vital = INACTIVO. Nunca eliminar físicamente."""
    persona = db.query(models.Persona).filter(models.Persona.id == persona_id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    persona.estado_vital = "INACTIVO"
    from datetime import date
    persona.unregistration_date = date.today()
    db.commit()
    return None


@router.get(
    "/personas/{persona_id}/communications", response_model=List[schemas.CommunicationLog]
)
def get_persona_communications(
    persona_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    return (
        db.query(models.CommunicationLog)
        .filter(models.CommunicationLog.persona_id == persona_id)
        .all()
    )


@router.get("/personas/{persona_id}/donations", response_model=List[schemas.Donation])
def list_persona_donations(
    persona_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    return crud.get_member_donations(db, persona_id=persona_id)


@router.get("/personas/{persona_id}/timeline", response_model=List[dict])
def get_persona_growth_timeline(
    persona_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Devuelve la línea de tiempo unificada (Academia, Consejería, Comunicaciones)."""
    return crud.get_member_timeline(db, persona_id=persona_id)


@router.get("/personas/{persona_id}/ministries", response_model=List[dict])
def get_persona_ministries(
    persona_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Devuelve todas las vinculaciones ministeriales de una persona con su rol."""
    rows = (
        db.query(models.MemberMinistry)
        .filter(models.MemberMinistry.persona_id == persona_id)
        .order_by(
            models.MemberMinistry.is_active.desc(),
            models.MemberMinistry.start_date.desc(),
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
    persona_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Devuelve el perfil de consolidación de una persona: roles, casos y seguimiento."""
    persona = db.query(models.Persona).filter(models.Persona.id == persona_id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    positions = (
        db.query(models.MemberPosition, models.Position)
        .join(models.Position, models.Position.id == models.MemberPosition.position_id)
        .filter(models.MemberPosition.persona_id == persona_id)
        .order_by(
            models.MemberPosition.is_active.desc(),
            models.MemberPosition.start_date.desc(),
        )
        .all()
    )

    cases = (
        db.query(models.ConsolidationCase)
        .filter(models.ConsolidationCase.persona_id == persona_id)
        .order_by(models.ConsolidationCase.created_at.desc())
        .all()
    )

    case_rows = []
    for case in cases:
        case_rows.append(
            {
                "id": case.id,
                "persona_id": case.persona_id,
                "stage": case.stage,
                "status": case.status,
                "source": case.source,
                "last_contact_at": (
                    case.last_contact_at.isoformat() if case.last_contact_at else None
                ),
                "next_contact_at": (
                    case.next_contact_at.isoformat() if case.next_contact_at else None
                ),
                "assigned_pastor": (
                    {
                        "id": case.assigned_pastor.id,
                        "first_name": case.assigned_pastor.first_name,
                        "last_name": case.assigned_pastor.last_name,
                    }
                    if case.assigned_pastor
                    else None
                ),
                "assigned_leader": (
                    {
                        "id": case.assigned_leader.id,
                        "first_name": case.assigned_leader.first_name,
                        "last_name": case.assigned_leader.last_name,
                    }
                    if case.assigned_leader
                    else None
                ),
                "assignments_count": len(case.assignments or []),
                "interactions_count": len(case.interactions or []),
                "open_tasks_count": sum(
                    1
                    for task in (case.tasks or [])
                    if task.status != "completed"
                ),
                "notes": case.notes,
                "created_at": case.created_at.isoformat() if case.created_at else None,
                "updated_at": case.updated_at.isoformat() if case.updated_at else None,
            }
        )

    position_rows = []
    for member_position, position in positions:
        position_rows.append(
            {
                "id": member_position.id,
                "persona_id": member_position.persona_id,
                "position_id": member_position.position_id,
                "position_name": position.name if position else None,
                "category": position.category if position else None,
                "start_date": (
                    member_position.start_date.isoformat()
                    if member_position.start_date
                    else None
                ),
                "end_date": (
                    member_position.end_date.isoformat()
                    if member_position.end_date
                    else None
                ),
                "is_active": member_position.is_active,
                "notes": member_position.notes,
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
    current_user: models.User = Depends(require_pastor_or_admin),
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
    current_user: models.User = Depends(require_pastor_or_admin),
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
    position_id: int,
    payload: schemas.PositionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
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
    persona_id: int,
    payload: schemas.MemberPositionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    persona = db.query(models.Persona).filter(models.Persona.id == persona_id).first()
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
        db.query(models.MemberPosition)
        .filter(
            models.MemberPosition.persona_id == persona_id,
            models.MemberPosition.position_id == payload.position_id,
            models.MemberPosition.start_date == payload.start_date,
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

    row = models.MemberPosition(
        persona_id=persona_id,
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


@router.patch(
    "/personas/{persona_id}/positions/{member_position_id}", response_model=dict
)
def update_persona_position(
    persona_id: int,
    member_position_id: int,
    payload: schemas.MemberPositionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    row = (
        db.query(models.MemberPosition)
        .filter(
            models.MemberPosition.id == member_position_id,
            models.MemberPosition.persona_id == persona_id,
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
    persona_id: int,
    payload: schemas.MemberMinistryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Vincula a un miembro a un ministerio con un rol especifico."""
    existing = (
        db.query(models.MemberMinistry)
        .filter(
            models.MemberMinistry.persona_id == persona_id,
            models.MemberMinistry.ministry_id == payload.ministry_id,
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
    mm = models.MemberMinistry(
        persona_id=persona_id,
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
    persona_id: int,
    mm_id: int,
    payload: schemas.MemberMinistryUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Actualiza el rol o estado de una vinculacion ministerial."""
    mm = (
        db.query(models.MemberMinistry)
        .filter(
            models.MemberMinistry.id == mm_id,
            models.MemberMinistry.persona_id == persona_id,
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
    department_id: int,
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
    current_user: models.User = Depends(require_pastor_or_admin),
):
    return crud.get_families(db, skip=skip, limit=limit)


@router.post("/families/", response_model=dict)
def create_new_family(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    fam = crud.create_family(db, name)
    return {"id": fam.id, "name": fam.name}


@router.get("/family/{family_id}", response_model=List[dict])
def get_family(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    return crud.get_family_members(db, family_id=family_id)
