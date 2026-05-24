import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.auth import (get_current_user, normalize_role,
                          require_active_user, require_admin,
                          require_pastor_or_admin)
from backend.core.audit import record_admin_action
from backend.core.database import get_db

router = APIRouter(tags=["CRM"])


# --- MEMBERS ENDPOINTS ---


@router.get("/members", response_model=List[schemas.Member])
def list_members(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Lista miembros con tipado estricto y busqueda optimizada."""
    return crud.search_members(db, search=search)


@router.post("/members/", response_model=schemas.Member)
def create_member(
    payload: schemas.MemberCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Registra un nuevo miembro en el CRM."""
    return crud.create_member(db, payload)


@router.get("/members/me", response_model=dict)
def get_my_crm_card(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Devuelve la tarjeta de miembro del usuario actual vinculada por user_id."""
    member = (
        db.query(models.Member).filter(models.Member.user_id == current_user.id).first()
    )
    if member:
        return {
            "id": member.id,
            "first_name": member.first_name,
            "last_name": member.last_name,
            "church_role": member.church_role,
            "qr_code": f"CCF-MBR-{member.id}-{uuid.uuid4().hex[:6]}",
        }
    return {
        "id": 0,
        "first_name": current_user.username,
        "last_name": "Usuario",
        "church_role": current_user.role,
        "qr_code": f"CCF-USR-{current_user.id}-{uuid.uuid4().hex[:6]}",
    }


@router.get("/members/donations", response_model=List[dict])
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
        if not donor_name and donation.member:
            donor_name = f"{donation.member.first_name} {donation.member.last_name}"
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
                "member_id": donation.member_id,
            }
        )
    return result


@router.get("/members/{member_id}", response_model=schemas.Member)
def get_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Obtiene el detalle de un miembro con validacion de propiedad (IDOR)."""
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # Check if user is looking at their own profile OR is a pastor/admin
    is_self = member.user_id == current_user.id
    is_staff = normalize_role(str(current_user.role)) in [
        "admin",
        "pastor",
        "coordinador",
    ]

    if not is_self and not is_staff:
        raise HTTPException(
            status_code=403, detail="No autorizado para ver este perfil"
        )

    return member


@router.patch("/members/{member_id}", response_model=schemas.Member)
def update_member(
    member_id: int,
    payload: schemas.MemberUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Actualiza datos de un miembro con persistencia y auditoria."""
    member = crud.update_member(db, member_id=member_id, payload=payload)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    record_admin_action(
        db,
        current_user,
        action="update_member",
        resource_type="member",
        resource_id=str(member.id),
        metadata=payload.model_dump(exclude_unset=True),
    )
    return member


@router.delete("/members/{member_id}", status_code=204)
def delete_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(member)
    db.commit()
    return None


@router.get(
    "/members/{member_id}/communications", response_model=List[schemas.CommunicationLog]
)
def get_member_communications(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    return (
        db.query(models.CommunicationLog)
        .filter(models.CommunicationLog.member_id == member_id)
        .all()
    )


@router.get("/members/{member_id}/donations", response_model=List[schemas.Donation])
def list_member_donations(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    return crud.get_member_donations(db, member_id=member_id)


@router.get("/members/{member_id}/timeline", response_model=List[dict])
def get_member_growth_timeline(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Devuelve la linea de tiempo unificada (Academia, Conseria, Comunicaciones)."""
    return crud.get_member_timeline(db, member_id=member_id)


@router.get("/members/{member_id}/ministries", response_model=List[dict])
def get_member_ministries(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Devuelve todas las vinculaciones ministeriales de un miembro con su rol."""
    rows = (
        db.query(models.MemberMinistry)
        .filter(models.MemberMinistry.member_id == member_id)
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
                "member_id": mm.member_id,
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


@router.get("/members/{member_id}/consolidation", response_model=dict)
def get_member_consolidation_profile(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Devuelve el perfil de consolidacion de un miembro: roles, casos y seguimiento."""
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    positions = (
        db.query(models.MemberPosition, models.Position)
        .join(models.Position, models.Position.id == models.MemberPosition.position_id)
        .filter(models.MemberPosition.member_id == member_id)
        .order_by(
            models.MemberPosition.is_active.desc(),
            models.MemberPosition.start_date.desc(),
        )
        .all()
    )

    cases = (
        db.query(models.ConsolidationCase)
        .filter(models.ConsolidationCase.member_id == member_id)
        .order_by(models.ConsolidationCase.created_at.desc())
        .all()
    )

    case_rows = []
    for case in cases:
        case_rows.append(
            {
                "id": case.id,
                "member_id": case.member_id,
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
                    for task in (case.follow_up_tasks or [])
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
                "member_id": member_position.member_id,
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
        "member": {
            "id": member.id,
            "first_name": member.first_name,
            "last_name": member.last_name,
            "church_role": member.church_role,
            "spiritual_status": member.spiritual_status,
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


@router.post("/members/{member_id}/positions", response_model=dict)
def assign_member_position(
    member_id: int,
    payload: schemas.MemberPositionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
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
            models.MemberPosition.member_id == member_id,
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
        member_id=member_id,
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
    "/members/{member_id}/positions/{member_position_id}", response_model=dict
)
def update_member_position(
    member_id: int,
    member_position_id: int,
    payload: schemas.MemberPositionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    row = (
        db.query(models.MemberPosition)
        .filter(
            models.MemberPosition.id == member_position_id,
            models.MemberPosition.member_id == member_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Member position not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "updated": True}


@router.post("/members/{member_id}/ministries", response_model=dict)
def assign_member_ministry(
    member_id: int,
    payload: schemas.MemberMinistryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Vincula a un miembro a un ministerio con un rol especifico."""
    existing = (
        db.query(models.MemberMinistry)
        .filter(
            models.MemberMinistry.member_id == member_id,
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
        member_id=member_id,
        ministry_id=payload.ministry_id,
        role=payload.role,
        notes=payload.notes,
        is_active=True,
    )
    db.add(mm)
    db.commit()
    db.refresh(mm)
    return {"id": mm.id, "created": True}


@router.patch("/members/{member_id}/ministries/{mm_id}", response_model=dict)
def update_member_ministry(
    member_id: int,
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
            models.MemberMinistry.member_id == member_id,
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
    current_user: models.User = Depends(require_active_user),
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
    current_user: models.User = Depends(require_active_user),
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
