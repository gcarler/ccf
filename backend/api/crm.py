from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend import crud
from backend import models
from backend import schemas
from backend.auth import require_active_user, require_admin, require_staff_or_admin
from backend.core.audit import record_admin_action
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
    created = crud.create_member(db, member)
    record_admin_action(
        db,
        current_user,
        action="create_member",
        resource_type="member",
        resource_id=str(created.id),
        metadata={"first_name": created.first_name, "last_name": created.last_name},
    )
    return created

from backend.core.audit import record_admin_action

# ...

@router.patch("/members/{member_id}", response_model=schemas.Member)
def update_member(
    member_id: int,
    payload: schemas.MemberUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    updated = crud.update_member(db, member_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Member not found")

    # Audit log
    record_admin_action(
        db,
        current_user,
        action="update_member",
        resource_type="member",
        resource_id=str(member_id),
        metadata=payload.model_dump(exclude_unset=True)
    )

    return updated

    record_admin_action(
        db,
        current_user,
        action="update_member",
        resource_type="member",
        resource_id=str(member_id),
        metadata=member.model_dump(exclude_unset=True),
    )
    return updated


@router.get("/members/{member_id}/communications", response_model=List[schemas.CommunicationLog])
def list_member_communications(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
    limit: int = 50,
):
    return crud.get_member_communication_logs(db, member_id=member_id, limit=limit)


@router.post("/members/{member_id}/communications", response_model=schemas.CommunicationLog)
def create_member_communication(
    member_id: int,
    payload: schemas.CommunicationLogCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    body = payload.model_dump()
    body["member_id"] = member_id
    return crud.create_communication_log(db, schemas.CommunicationLogCreate(**body))


@router.get("/members/by-user/{user_id}", response_model=schemas.Member)
def read_member_by_user(user_id: int, db: Session = Depends(get_db)):
    member = crud.get_member_by_user(db, user_id=user_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@router.get("/members/me", response_model=schemas.Member)
def read_my_member_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    member = crud.get_member_by_user(db, user_id=int(getattr(current_user, "id", 0)))
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@router.get("/members/{member_id}/academy-profile", response_model=schemas.MemberAcademyProfile)
def member_academy_profile(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    return crud.get_member_academy_profile(db, member_id)


class AcademyAccountRequest(BaseModel):
    password: str


@router.post("/members/{member_id}/create-academy-account")
def create_member_academy_account(
    member_id: int,
    payload: AcademyAccountRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    try:
        user = crud.create_member_academy_account(db, member_id, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"user_id": user.id, "username": user.username}


@router.get("/families", response_model=List[schemas.Family])
def read_families(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_families(db, skip=skip, limit=limit)


@router.post("/families", response_model=schemas.Family)
def create_family(
    family: schemas.FamilyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    created = crud.create_family(db, family)
    record_admin_action(
        db,
        current_user,
        action="create_family",
        resource_type="family",
        resource_id=str(created.id),
        metadata={"name": created.name},
    )
    return created


@router.get("/events", response_model=List[schemas.Event])
def read_events(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_events(db, skip=skip, limit=limit)


@router.post("/events", response_model=schemas.Event)
def create_event(
    event: schemas.EventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    created = crud.create_event(db, event)
    record_admin_action(
        db,
        current_user,
        action="create_event",
        resource_type="event",
        resource_id=str(created.id),
        metadata={"name": created.name, "event_type": created.event_type},
    )
    return created


@router.post("/attendance/", response_model=schemas.Attendance)
def record_attendance(
    payload: schemas.AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    if not payload.member_id and not payload.enrollment_id:
        raise HTTPException(status_code=400, detail="member_id o enrollment_id requerido")
    return crud.create_attendance_record(db, payload)


@router.get("/glory-houses", response_model=List[schemas.GloryHouse])
def read_glory_houses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_glory_houses(db, skip=skip, limit=limit)


@router.post("/glory-houses", response_model=schemas.GloryHouse)
def create_glory_house(
    glory_house: schemas.GloryHouseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    created = crud.create_glory_house(db, glory_house)
    record_admin_action(
        db,
        current_user,
        action="create_glory_house",
        resource_type="glory_house",
        resource_id=str(created.id),
        metadata={"name": created.name, "zone": created.zone},
    )
    return created


@router.get("/volunteers", response_model=List[schemas.Volunteer])
def read_volunteers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_volunteers(db, skip=skip, limit=limit)


@router.post("/volunteers", response_model=schemas.Volunteer)
def create_volunteer(
    volunteer: schemas.VolunteerCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    created = crud.create_volunteer(db, volunteer)
    record_admin_action(
        db,
        current_user,
        action="create_volunteer",
        resource_type="volunteer",
        resource_id=str(created.id),
        metadata={"name": created.name, "role": created.role},
    )
    return created


@router.post("/scanner/validate/{token}")
def validate_scanner_token(
    token: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    member = (
        db.query(models.Member)
        .filter(models.Member.qr_token == token)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Token no v??lido")
    return {
        "member_id": member.id,
        "member_name": f"{member.first_name} {member.last_name}",
        "role": member.church_role,
        "qr_token": member.qr_token,
    }


@router.get("/settings", response_model=schemas.CrmSettings)
def get_crm_settings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    return crud.get_crm_settings(db)


@router.post("/settings", response_model=schemas.CrmSettings)
def save_crm_settings(
    payload: schemas.CrmSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    user_id = int(getattr(current_user, "id", 0)) if current_user else None
    return crud.save_crm_settings(db, payload, updated_by=user_id)


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


@router.get("/pipeline/", response_model=List[schemas.ConsolidationPipeline])
def read_pipeline_alias(
    skip: int = 0,
    limit: int = 100,
    stage: Optional[str] = None,
    assigned_pastor_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    return read_pipeline(skip, limit, stage, assigned_pastor_id, search, db)


@router.post("/consolidation/pipeline", response_model=schemas.ConsolidationPipeline)
async def create_pipeline_lead(
    lead: schemas.ConsolidationPipelineCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    db_lead = crud.create_pipeline_lead(db, lead)
    record_admin_action(
        db,
        current_user,
        action="create_pipeline_lead",
        resource_type="pipeline_lead",
        resource_id=str(db_lead.id),
        metadata={"stage": db_lead.stage, "source": db_lead.source},
    )
    await manager.broadcast_event(
        {
            "event": "pipeline_lead_created",
            "lead": _lead_to_dict(db_lead),
        },
        room="pipeline",
    )
    return db_lead


@router.post("/pipeline/", response_model=schemas.ConsolidationPipeline)
async def create_pipeline_alias(
    lead: schemas.ConsolidationPipelineCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    return await create_pipeline_lead(lead, db, current_user)


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
    record_admin_action(
        db,
        current_user,
        action="update_pipeline_lead",
        resource_type="pipeline_lead",
        resource_id=str(lead_id),
        metadata=payload.model_dump(exclude_unset=True),
    )
    await manager.broadcast_event(
        {
            "event": "pipeline_lead_updated",
            "lead": _lead_to_dict(updated),
        },
        room="pipeline",
    )
    return updated


@router.get("/pipeline/{lead_id}", response_model=schemas.ConsolidationPipeline)
def get_pipeline_lead_details(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    lead = crud.get_pipeline_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.patch("/pipeline/{lead_id}", response_model=schemas.ConsolidationPipeline)
async def update_pipeline_alias(
    lead_id: int,
    payload: schemas.ConsolidationPipelineUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    return await update_pipeline_lead(lead_id, payload, db, current_user)


@router.get("/consolidation/leads/{lead_id}/calls", response_model=List[schemas.PastoralCallLog])
def read_lead_calls(lead_id: int, db: Session = Depends(get_db)):
    return crud.get_pastoral_call_logs(db, lead_id=lead_id)


@router.get("/pipeline/leads/{lead_id}/calls", response_model=List[schemas.PastoralCallLog])
def read_lead_calls_alias(lead_id: int, db: Session = Depends(get_db)):
    return read_lead_calls(lead_id, db)


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
    record_admin_action(
        db,
        current_user,
        action="create_pastoral_call",
        resource_type="pastoral_call",
        resource_id=str(created.id),
        metadata={"lead_id": lead_id, "outcome": created.outcome},
    )
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


@router.post("/pipeline/calls", response_model=schemas.PastoralCallLog)
async def create_call_log_alias(
    payload: schemas.PastoralCallLogCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    lead_id = int(getattr(payload, "lead_id", 0))
    return await create_call_log(lead_id, payload, db, current_user)


@router.get("/automations", response_model=List[schemas.ConsolidationAutomation])
def list_automations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    return crud.list_consolidation_automations(db)


@router.post("/automations", response_model=schemas.ConsolidationAutomation)
def create_automation(
    payload: schemas.ConsolidationAutomationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    return crud.create_consolidation_automation(db, payload)


@router.put("/automations/{automation_id}", response_model=schemas.ConsolidationAutomation)
def update_automation(
    automation_id: int,
    payload: schemas.ConsolidationAutomationUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    updated = crud.update_consolidation_automation(db, automation_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Automation not found")
    return updated


@router.delete("/automations/{automation_id}")
def delete_automation(
    automation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    if not crud.delete_consolidation_automation(db, automation_id):
        raise HTTPException(status_code=404, detail="Automation not found")
    return {"status": "deleted"}


@router.post("/pastoral/counseling", response_model=schemas.CounselingSession)
def create_counseling(
    session: schemas.CounselingSessionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    created = crud.create_counseling_session(db, session)
    record_admin_action(
        db,
        current_user,
        action="create_counseling_session",
        resource_type="counseling_session",
        resource_id=str(created.id),
        metadata={"scheduled_at": str(created.scheduled_at), "status": created.status},
    )
    return created


@router.get("/counseling/", response_model=List[schemas.CounselingSession])
def list_counseling_sessions(
    lead_id: Optional[int] = None,
    member_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    return crud.list_counseling_sessions(db, lead_id=lead_id, member_id=member_id)


@router.get("/counseling/lead/{lead_id}", response_model=List[schemas.CounselingSession])
def counseling_by_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    return crud.list_counseling_sessions(db, lead_id=lead_id)


@router.patch("/counseling/{session_id}", response_model=schemas.CounselingSession)
def update_counseling(
    session_id: int,
    payload: schemas.CounselingSessionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    updated = crud.update_counseling_session(db, session_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Counseling session not found")
    return updated


# -----------------
# Prayer Requests
# -----------------

@router.get("/prayer-requests", response_model=List[schemas.PrayerRequest])
def list_prayer_requests(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    # Only staff/admin see everything, members see their own (or public ones)
    query = db.query(models.PrayerRequest)
    if not role_in(current_user.role, {"admin", "pastor", "staff"}):
        query = query.filter(models.PrayerRequest.user_id == current_user.id)
    return query.order_by(models.PrayerRequest.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/prayer-requests", response_model=schemas.PrayerRequest)
def create_prayer_request(
    payload: schemas.PrayerRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    db_req = models.PrayerRequest(
        user_id=current_user.id,
        name=payload.name,
        request=payload.request,
        category=payload.category,
        is_anonymous=payload.is_anonymous
    )
    db.add(db_req)
    db.commit()
    db.refresh(db_req)
    return db_req


# -----------------
# Call Center / Quick Actions
# -----------------

class QuickInteractionPayload(BaseModel):
    member_id: int
    channel: str # call, sms, whatsapp, email
    outcome: str
    content: str

@router.post("/outreach/log")
async def log_pastoral_interaction(
    payload: QuickInteractionPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    # 1. Log the interaction
    log_entry = crud.create_communication_log(db, schemas.CommunicationLogCreate(
        member_id=payload.member_id,
        leader_id=current_user.id,
        channel=payload.channel,
        outcome=payload.outcome,
        content=payload.content
    ))
    
    # 2. Trigger Realtime Notification
    await manager.broadcast_event({
        "event": "interaction_logged",
        "member_id": payload.member_id,
        "channel": payload.channel,
        "outcome": payload.outcome
    }, room="crm")
    
    return log_entry
