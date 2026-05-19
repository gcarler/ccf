"""CRM: Members, pipeline, events, tasks, counseling, prayer, glory houses, etc."""
import datetime as dt
import uuid
from typing import Optional, List

from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.security import encrypt_data, decrypt_data
from backend.crud._utils import _utcnow


# ── Members ────────────────────────────────────────────

def get_member_donations(db: Session, member_id: int):
    return db.query(models.Donation).filter(models.Donation.member_id == member_id).order_by(models.Donation.created_at.desc()).all()


def create_member(db: Session, payload: schemas.MemberCreate):
    row = models.Member(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def search_members(
    db: Session,
    search: str | None = None,
    role: str | None = None,
    spiritual_status: str | None = None,
    family_id: int | None = None,
    skip: int = 0,
    limit: int = 1000
):
    query = db.query(models.Member)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                models.Member.first_name.ilike(like),
                models.Member.last_name.ilike(like),
                models.Member.email.ilike(like),
                models.Member.church_role.ilike(like),
            )
        )
    if role:
        query = query.filter(models.Member.church_role == role)
    if spiritual_status:
        query = query.filter(models.Member.spiritual_status == spiritual_status)
    if family_id:
        query = query.filter(models.Member.family_id == family_id)

    members = query.offset(skip).limit(limit).all()

    user_ids = [m.user_id for m in members if m.user_id]
    progress_map = {}
    if user_ids:
        progress_data = db.query(
            models.Enrollment.user_id,
            func.avg(models.Enrollment.progress_percent)
        ).filter(models.Enrollment.user_id.in_(user_ids)).group_by(models.Enrollment.user_id).all()
        progress_map = {uid: avg for uid, avg in progress_data}

    for m in members:
        m.spiritual_health = 0.5 + (abs(hash(m.first_name)) % 50) / 100.0
        m.academy_progress = float(progress_map.get(m.user_id, 0.0))

    return members


def get_members(db: Session, search: str | None = None, role: str | None = None):
    return search_members(db, search=search, role=role)


def update_member(db: Session, member_id: int, payload: schemas.MemberUpdate):
    row = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


# ── Pipeline ───────────────────────────────────────────

def create_pipeline_lead(db: Session, payload: schemas.ConsolidationPipelineCreate):
    row = models.ConsolidationPipeline(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_pipeline_lead(db: Session, lead_id: int, payload: schemas.ConsolidationPipelineUpdate):
    row = db.query(models.ConsolidationPipeline).filter(models.ConsolidationPipeline.id == lead_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def get_pipeline_leads(
    db: Session,
    stage: str | None = None,
    assigned_pastor_id: int | None = None,
    search: str | None = None,
):
    query = db.query(models.ConsolidationPipeline)
    if stage:
        query = query.filter(models.ConsolidationPipeline.stage == stage)
    if assigned_pastor_id is not None:
        query = query.filter(models.ConsolidationPipeline.assigned_pastor_id == assigned_pastor_id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                models.ConsolidationPipeline.first_name.ilike(like),
                models.ConsolidationPipeline.last_name.ilike(like),
            )
        )
    return query.all()


def create_pastoral_call_log(db: Session, lead_id: int, call_log: schemas.PastoralCallLogCreate):
    row = models.PastoralCallLog(lead_id=lead_id, pastor_id=call_log.pastor_id, outcome=call_log.outcome)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_pastoral_call_logs(db: Session, lead_id: int):
    return db.query(models.PastoralCallLog).filter(models.PastoralCallLog.lead_id == lead_id).all()


# ── CRM Events ─────────────────────────────────────────

def get_crm_events(db: Session, skip: int = 0, limit: int = 100) -> List[models.CrmEvent]:
    return db.query(models.CrmEvent).order_by(models.CrmEvent.event_date.desc()).offset(skip).limit(limit).all()


def create_crm_event(db: Session, payload: schemas.CrmEventCreate) -> models.CrmEvent:
    try:
        payload_data = payload.model_dump()
        role_ids = payload_data.get("target_role_ids") or []
        payload_data["target_role_ids"] = role_ids or None
        if payload_data.get("target_audience") == "ROLE":
            payload_data["target_role_id"] = role_ids[0] if role_ids else payload_data.get("target_role_id")
        else:
            payload_data["target_role_id"] = None
            payload_data["target_role_ids"] = None
        row = models.CrmEvent(**payload_data)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except MemoryError:
        raise
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al crear evento: {str(e)}")


# ── CRM Tasks ──────────────────────────────────────────

def get_crm_tasks(db: Session, assignee_id: Optional[int] = None, member_id: Optional[int] = None, lead_id: Optional[int] = None) -> List[models.CrmTask]:
    query = db.query(models.CrmTask)
    if assignee_id:
        query = query.filter(models.CrmTask.assignee_id == assignee_id)
    if member_id:
        query = query.filter(models.CrmTask.member_id == member_id)
    if lead_id:
        query = query.filter(models.CrmTask.lead_id == lead_id)
    return query.order_by(models.CrmTask.due_date.asc()).all()


def create_crm_task(db: Session, payload: schemas.CrmTaskCreate) -> models.CrmTask:
    row = models.CrmTask(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_crm_task(db: Session, task_id: int, payload: schemas.CrmTaskUpdate) -> models.CrmTask:
    row = db.query(models.CrmTask).filter(models.CrmTask.id == task_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


# ── Volunteers ─────────────────────────────────────────

def get_volunteer_shifts(db: Session, member_id: Optional[int] = None) -> List[models.VolunteerShift]:
    query = db.query(models.VolunteerShift)
    if member_id:
        query = query.filter(models.VolunteerShift.member_id == member_id)
    return query.order_by(models.VolunteerShift.shift_start.asc()).all()


def create_volunteer_shift(db: Session, payload: schemas.VolunteerShiftCreate) -> models.VolunteerShift:
    row = models.VolunteerShift(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ── Event Attendance ───────────────────────────────────

def create_event_attendance(db: Session, payload: schemas.EventAttendanceCreate) -> models.EventAttendance:
    try:
        row = models.EventAttendance(**payload.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except MemoryError:
        raise
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al registrar asistencia: {str(e)}")


# ── Counseling ─────────────────────────────────────────

def get_counseling_tickets(
    db: Session,
    status: str | None = None,
    member_id: int | None = None,
    skip: int = 0,
    limit: int = 100
) -> List[models.CounselingTicket]:
    query = db.query(models.CounselingTicket)
    if status:
        query = query.filter(models.CounselingTicket.status == status)
    if member_id:
        query = query.filter(models.CounselingTicket.member_id == member_id)
    tickets = query.order_by(models.CounselingTicket.created_at.desc()).offset(skip).limit(limit).all()

    for t in tickets:
        if t.notes:
            t.notes = decrypt_data(t.notes)

    return tickets


def create_counseling_ticket(db: Session, payload: schemas.CounselingTicketCreate) -> models.CounselingTicket:
    from backend.crud._utils import analyze_pastoral_priority, analyze_pastoral_sentiment

    try:
        data = payload.model_dump()
        raw_notes = data.get("notes", "")

        data["priority_level"] = analyze_pastoral_priority(raw_notes)
        score, label = analyze_pastoral_sentiment(raw_notes)
        data["sentiment_score"] = score
        data["sentiment_label"] = label

        if raw_notes:
            data["notes"] = encrypt_data(raw_notes)

        row = models.CounselingTicket(**data)
        db.add(row)
        db.commit()
        db.refresh(row)

        row.notes = decrypt_data(row.notes)
        return row
    except MemoryError:
        raise
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al crear ticket de consejería: {str(e)}")


# ── Prayer ─────────────────────────────────────────────

def get_prayer_requests(db: Session, status: str | None = None, skip: int = 0, limit: int = 100) -> List[models.PrayerRequest]:
    query = db.query(models.PrayerRequest)
    if status:
        query = query.filter(models.PrayerRequest.status == status)
    return query.order_by(models.PrayerRequest.created_at.desc()).offset(skip).limit(limit).all()


def create_prayer_request(db: Session, payload: schemas.PrayerRequestCreate) -> models.PrayerRequest:
    try:
        row = models.PrayerRequest(**payload.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except MemoryError:
        raise
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al registrar petición de oración: {str(e)}")


# ── Glory Houses ───────────────────────────────────────

def get_glory_houses(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.GloryHouse).offset(skip).limit(limit).all()


def create_glory_house(db: Session, payload: schemas.GloryHouseCreate):
    data = payload.model_dump(exclude={"base_attendee_ids"})
    if not str(data.get("code") or "").strip():
        base = str(data.get("name") or data.get("address") or "FARO").strip().upper().replace(" ", "-")
        data["code"] = f"{base}-{_utcnow().strftime('%Y%m%d%H%M%S')}"
    if not str(data.get("name") or "").strip():
        fallback_name = str(data.get("address") or data["code"]).strip()
        data["name"] = f"Faro pendiente - {fallback_name}"
    db_obj = models.GloryHouse(**data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    if payload.base_attendee_ids:
        for member_id in payload.base_attendee_ids:
            attendee = models.GloryHouseMember(glory_house_id=db_obj.id, member_id=member_id, role="asistente")
            db.add(attendee)
        db.commit()
        db.refresh(db_obj)

    return db_obj


def update_glory_house(db: Session, house_id: int, payload: schemas.GloryHouseUpdate):
    house = db.query(models.GloryHouse).filter(models.GloryHouse.id == house_id).first()
    if not house:
        return None

    update_data = payload.model_dump(exclude_unset=True, exclude={"base_attendee_ids"})
    if "code" in update_data and not str(update_data["code"] or "").strip():
        update_data["code"] = house.code or f"FARO-{house.id}"
    for key, value in update_data.items():
        setattr(house, key, value)

    if payload.base_attendee_ids is not None:
        db.query(models.GloryHouseMember).filter(models.GloryHouseMember.glory_house_id == house_id).delete()
        for member_id in payload.base_attendee_ids:
            attendee = models.GloryHouseMember(glory_house_id=house_id, member_id=member_id, role="asistente")
            db.add(attendee)

    db.commit()
    db.refresh(house)
    return house


# ── Talents & Families ─────────────────────────────────

def get_talents(db: Session, search: str | None = None):
    return search_members(db, search=search)


def get_families(db: Session, skip: int = 0, limit: int = 100):
    families = db.query(models.Family).offset(skip).limit(limit).all()
    for f in families:
        f.members_count = db.query(models.Member).filter(models.Member.family_id == f.id).count()
    return families


def create_family(db: Session, name: str):
    fam = models.Family(name=name)
    db.add(fam)
    db.commit()
    db.refresh(fam)
    return fam


# ── Member Timeline ────────────────────────────────────

def get_member_timeline(db: Session, member_id: int):
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        return []

    timeline = []

    timeline.append({
        "type": "membership",
        "title": "Ingreso a la Familia CCF",
        "description": f"Registro formal como {member.church_role}.",
        "date": member.created_at.isoformat(),
        "icon": "Sparkles",
        "color": "bg-purple-500"
    })

    if member.user_id:
        enrollments = db.query(models.Enrollment).filter(models.Enrollment.user_id == member.user_id).all()
        for en in enrollments:
            timeline.append({
                "type": "academy",
                "title": "Inscripción Academia",
                "description": f"Inició el curso {en.course.name if en.course else 'de formación'}.",
                "date": en.created_at.isoformat(),
                "icon": "GraduationCap",
                "color": "bg-emerald-500"
            })
            if en.certificate_issued:
                timeline.append({
                    "type": "certificate",
                    "title": "Certificación Obtenida",
                    "description": f"Completó con éxito el curso: {en.course.name if en.course else 'de formación'}.",
                    "date": (en.created_at + dt.timedelta(days=30)).isoformat(),
                    "icon": "Award",
                    "color": "bg-amber-500"
                })

    for ministry in member.ministries:
        timeline.append({
            "type": "ministry",
            "title": "Vinculación Ministerial",
            "description": f"Se integró al ministerio de {ministry.name}.",
            "date": ministry.created_at.isoformat() if ministry.created_at else member.created_at.isoformat(),
            "icon": "ShieldCheck",
            "color": "bg-indigo-600"
        })

    sessions = db.query(models.CounselingTicket).filter(models.CounselingTicket.member_id == member_id).all()
    for s in sessions:
        timeline.append({
            "type": "counseling",
            "title": "Sesión Pastoral",
            "description": f"Atención espiritual: {s.subject}.",
            "date": s.created_at.isoformat(),
            "icon": "Heart",
            "color": "bg-rose-500"
        })

    calls = db.query(models.CommunicationLog).filter(models.CommunicationLog.member_id == member_id).all()
    for c in calls:
        timeline.append({
            "type": "communication",
            "title": "Seguimiento Pastoral",
            "description": f"Contacto vía {c.channel}: {c.content[:50]}...",
            "date": c.created_at.isoformat(),
            "icon": "Phone",
            "color": "bg-blue-500"
        })

    timeline.sort(key=lambda x: x["date"], reverse=True)
    return timeline


# ── Communication Logs ─────────────────────────────────

def create_communication_log(db: Session, payload: schemas.CommunicationLogCreate):
    row = models.CommunicationLog(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_communication_logs(db: Session, limit: int = 50):
    return db.query(models.CommunicationLog).order_by(models.CommunicationLog.created_at.desc()).limit(limit).all()


# ── Notifications ────────────────────────────────────────

def get_user_notifications(db: Session, user_id: int, limit: int = 20) -> List[models.Notification]:
    return (
        db.query(models.Notification)
        .filter(models.Notification.user_id == user_id)
        .order_by(models.Notification.created_at.desc())
        .limit(limit)
        .all()
    )


def mark_notification_as_read(db: Session, notification_id: int):
    notification = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not notification:
        return None
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_notifications_read(db: Session, user_id: int):
    db.query(models.Notification).filter(
        models.Notification.user_id == user_id,
        models.Notification.is_read == False,
    ).update({models.Notification.is_read: True})
    db.commit()


# ── Donations ────────────────────────────────────────────

def create_donation(db: Session, payload: schemas.DonationCreate) -> models.Donation:
    row = models.Donation(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_donations(db: Session, skip: int = 0, limit: int = 100) -> List[models.Donation]:
    return db.query(models.Donation).order_by(models.Donation.created_at.desc()).offset(skip).limit(limit).all()


def get_total_donations_amount(db: Session) -> float:
    return db.query(func.sum(models.Donation.amount)).scalar() or 0


# ── Spiritual Milestones ─────────────────────────────────

def get_milestones(db: Session, person_id: int) -> List[models.SpiritualMilestone]:
    return (
        db.query(models.SpiritualMilestone)
        .filter(models.SpiritualMilestone.person_id == person_id)
        .order_by(models.SpiritualMilestone.event_date.desc())
        .all()
    )


def create_milestone(db: Session, person_id: int, type: str, event_date, minister_id: Optional[int] = None) -> models.SpiritualMilestone:
    row = models.SpiritualMilestone(
        person_id=person_id,
        type=type,
        event_date=event_date,
        minister_id=minister_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ── Family Members ──────────────────────────────────────

def get_family_members(db: Session, family_id: int):
    return (
        db.query(models.Member)
        .filter(models.Member.family_id == family_id)
        .order_by(models.Member.last_name.asc(), models.Member.first_name.asc())
        .all()
    )


# ── Support Tickets ─────────────────────────────────────

def create_support_ticket(db: Session, ticket: schemas.SupportTicketCreate) -> models.SupportTicket:
    row = models.SupportTicket(**ticket.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_support_tickets(db: Session, user_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[models.SupportTicket]:
    q = db.query(models.SupportTicket).order_by(models.SupportTicket.created_at.desc())
    if user_id is not None:
        q = q.filter(models.SupportTicket.user_id == user_id)
    return q.offset(skip).limit(limit).all()


def update_support_ticket(db: Session, ticket_id: int, new_status: str):
    ticket = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()
    if not ticket:
        return None
    ticket.status = new_status
    db.commit()
    db.refresh(ticket)
    return ticket


# ── Community Board ─────────────────────────────────────

def get_community_cards(db: Session, column_id: Optional[str] = None) -> List[models.CommunityBoardCard]:
    q = db.query(models.CommunityBoardCard).order_by(models.CommunityBoardCard.position.asc())
    if column_id:
        q = q.filter(models.CommunityBoardCard.column_id == column_id)
    return q.all()


def create_community_card(db: Session, card: schemas.CommunityBoardCardCreate) -> models.CommunityBoardCard:
    max_pos = db.query(func.max(models.CommunityBoardCard.position)).scalar() or 0
    row = models.CommunityBoardCard(**card.model_dump(), position=max_pos + 1)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
