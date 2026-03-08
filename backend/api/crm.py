from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend import crud
from backend import models
from backend import schemas
from backend.auth import require_active_user, require_admin, require_staff_or_admin
from backend.core.database import get_db
from backend.mesh_websockets import manager


router = APIRouter()


def _lead_to_dict(lead: models.ConsolidationPipeline) -> dict:
    return {
        "id": lead.id,
        "first_name": lead.first_name,
        "last_name": lead.last_name,
        "stage": lead.stage,
        "source": lead.source,
        "assigned_pastor_id": lead.assigned_pastor_id,
        "phone": lead.phone,
        "notes": lead.notes,
        "is_automation_paused": lead.is_automation_paused,
    }


@router.get("/members/", response_model=List[schemas.Member])
def read_members(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    role: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return crud.get_members(db, skip=skip, limit=limit, search=search, role=role)


@router.post("/members", response_model=schemas.Member)
def create_member(
    member: schemas.MemberCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    return crud.create_member(db, member)


@router.patch("/members/{member_id}", response_model=schemas.Member)
def update_member(
    member_id: int,
    member: schemas.MemberUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    updated = crud.update_member(db, member_id, member)
    if not updated:
        raise HTTPException(status_code=404, detail="Member not found")
    return updated


@router.get("/members/by-user/{user_id}", response_model=schemas.Member)
def read_member_by_user(user_id: int, db: Session = Depends(get_db)):
    member = crud.get_member_by_user(db, user_id=user_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@router.get("/families", response_model=List[schemas.Family])
def read_families(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_families(db, skip=skip, limit=limit)


@router.post("/families", response_model=schemas.Family)
def create_family(
    family: schemas.FamilyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    return crud.create_family(db, family)


@router.get("/events", response_model=List[schemas.Event])
def read_events(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_events(db, skip=skip, limit=limit)


@router.post("/events", response_model=schemas.Event)
def create_event(
    event: schemas.EventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    return crud.create_event(db, event)


@router.get("/glory-houses", response_model=List[schemas.GloryHouse])
def read_glory_houses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_glory_houses(db, skip=skip, limit=limit)


@router.post("/glory-houses", response_model=schemas.GloryHouse)
def create_glory_house(
    glory_house: schemas.GloryHouseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    return crud.create_glory_house(db, glory_house)


@router.get("/volunteers", response_model=List[schemas.Volunteer])
def read_volunteers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_volunteers(db, skip=skip, limit=limit)


@router.post("/volunteers", response_model=schemas.Volunteer)
def create_volunteer(
    volunteer: schemas.VolunteerCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    return crud.create_volunteer(db, volunteer)


@router.get("/consolidation/pipeline", response_model=List[schemas.ConsolidationPipeline])
def read_pipeline(
    skip: int = 0,
    limit: int = 100,
    stage: Optional[str] = None,
    assigned_pastor_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return crud.get_pipeline_leads(
        db,
        skip=skip,
        limit=limit,
        stage=stage,
        assigned_pastor_id=assigned_pastor_id,
        search=search,
    )


@router.post("/consolidation/pipeline", response_model=schemas.ConsolidationPipeline)
async def create_pipeline_lead(
    lead: schemas.ConsolidationPipelineCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    db_lead = crud.create_pipeline_lead(db, lead)
    await manager.broadcast_event(
        {
            "event": "pipeline_lead_created",
            "lead": _lead_to_dict(db_lead),
        },
        room="pipeline",
    )
    return db_lead


@router.patch("/consolidation/pipeline/{lead_id}", response_model=schemas.ConsolidationPipeline)
async def update_pipeline_lead(
    lead_id: int,
    payload: schemas.ConsolidationPipelineUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    updated = crud.update_pipeline_lead(db, lead_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Lead not found")
    await manager.broadcast_event(
        {
            "event": "pipeline_lead_updated",
            "lead": _lead_to_dict(updated),
        },
        room="pipeline",
    )
    return updated


@router.get("/consolidation/leads/{lead_id}/calls", response_model=List[schemas.PastoralCallLog])
def read_lead_calls(lead_id: int, db: Session = Depends(get_db)):
    return crud.get_pastoral_call_logs(db, lead_id=lead_id)


@router.post("/consolidation/leads/{lead_id}/call-logs", response_model=schemas.PastoralCallLog)
async def create_call_log(
    lead_id: int,
    call_log: schemas.PastoralCallLogCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    created = crud.create_pastoral_call_log(db, lead_id=lead_id, call_log=call_log)
    if not created:
        raise HTTPException(status_code=404, detail="Lead not found")
    await manager.broadcast_event(
        {
            "event": "pastoral_call_logged",
            "lead_id": lead_id,
            "call_id": created.id,
            "outcome": created.outcome,
        },
        room="pipeline",
    )
    return created


@router.post("/pastoral/counseling", response_model=schemas.CounselingSession)
def create_counseling(
    session: schemas.CounselingSessionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    return crud.create_counseling_session(db, session)
