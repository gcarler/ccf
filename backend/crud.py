from __future__ import annotations

import datetime as dt
import logging
import uuid
from typing import Any, List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend import models
from backend import schemas
from backend.analytics import event_sink
from backend.core.events import DomainEvent, event_bus
from backend.core.security import get_password_hash


log = logging.getLogger(__name__)


def _publish_event(topic: str, name: str, payload: dict) -> None:
    try:
        event_bus.publish(topic, DomainEvent(name=name, payload=payload))
    except Exception as exc:  # pragma: no cover
        log.debug("Unable to publish %s: %s", name, exc)
    try:
        event_sink.persist_event(name, payload)
    except Exception as exc:  # pragma: no cover
        log.debug("Unable to persist analytics event %s: %s", name, exc)


# -----------------
# Users
# -----------------
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        role=user.role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# -----------------
# Testimonials
# -----------------
def create_testimonial(db: Session, testimonial: schemas.TestimonialCreate) -> models.Testimonial:
    db_testimonial = models.Testimonial(**testimonial.model_dump())
    db.add(db_testimonial)
    db.commit()
    db.refresh(db_testimonial)
    return db_testimonial


def get_testimonials(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    approved_only: bool = False,
) -> List[models.Testimonial]:
    query = db.query(models.Testimonial)
    if approved_only:
        query = query.filter(models.Testimonial.is_approved.is_(True))
    return query.order_by(models.Testimonial.created_at.desc()).offset(skip).limit(limit).all()


def update_testimonial(
    db: Session,
    testimonial_id: int,
    testimonial: schemas.TestimonialUpdate,
) -> Optional[models.Testimonial]:
    db_testimonial = db.query(models.Testimonial).filter(models.Testimonial.id == testimonial_id).first()
    if not db_testimonial:
        return None
    update_data = testimonial.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_testimonial, key, value)
    db.commit()
    db.refresh(db_testimonial)
    return db_testimonial


# -----------------
# Courses & Lessons
# -----------------
def get_courses(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    modality: Optional[str] = None,
    published_only: bool = True,
) -> List[models.Course]:
    query = db.query(models.Course)
    if modality:
        query = query.filter(models.Course.modality == modality)
    if published_only:
        query = query.filter(models.Course.is_published.is_(True))
    return query.order_by(models.Course.created_at.desc()).offset(skip).limit(limit).all()


def get_course(db: Session, course_id: int) -> Optional[models.Course]:
    return db.query(models.Course).filter(models.Course.id == course_id).first()


def get_course_by_code(db: Session, code: str) -> Optional[models.Course]:
    return db.query(models.Course).filter(models.Course.code == code).first()


def seed_courses_if_empty(db: Session) -> None:
    if db.query(models.Course).count() > 0:
        return
    courses = [
        models.Course(code="FOR-001", title="Fundamentos de la Fe", modality="no_formal"),
        models.Course(code="FOR-101", title="Liderazgo I", modality="formal"),
    ]
    db.add_all(courses)
    db.commit()
    for course in courses:
        db.add(models.Assessment(course_id=course.id, title="Examen Final", passing_score=70))
        db.add(models.Lesson(course_id=course.id, title="Introducción", content="Contenido base."))
    db.commit()


# -----------------
# Enrollments & Assessments
# -----------------
def get_enrollment(db: Session, enrollment_id: int) -> Optional[models.Enrollment]:
    return db.query(models.Enrollment).filter(models.Enrollment.id == enrollment_id).first()


def get_enrollments_by_user(db: Session, user_id: int) -> List[models.Enrollment]:
    return db.query(models.Enrollment).filter(models.Enrollment.user_id == user_id).all()


def create_enrollment(db: Session, enrollment: schemas.EnrollmentCreate) -> models.Enrollment:
    user = get_user(db, enrollment.user_id)
    if not user or not getattr(user, "is_active", False):
        raise ValueError("Usuario no encontrado o inactivo")

    course = get_course(db, enrollment.course_id)
    if not course or not getattr(course, "is_published", True):
        raise ValueError("El curso no está disponible")

    existing = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.user_id == enrollment.user_id,
            models.Enrollment.course_id == enrollment.course_id,
        )
        .first()
    )
    if existing:
        raise ValueError("El usuario ya está inscrito en este curso")

    db_enrollment = models.Enrollment(**enrollment.model_dump())
    db.add(db_enrollment)
    db.commit()
    db.refresh(db_enrollment)

    _publish_event(
        "academy.enrollments",
        "EnrollmentCreated",
        {
            "enrollment_id": db_enrollment.id,
            "user_id": enrollment.user_id,
            "course_id": enrollment.course_id,
            "course_title": getattr(course, "title", ""),
            "user_email": getattr(user, "email", ""),
        },
    )
    return db_enrollment


def record_activity_attendance(db: Session, enrollment_id: int) -> models.Attendance:
    today = dt.datetime.utcnow().date()
    start = dt.datetime.combine(today, dt.time.min)
    existing = (
        db.query(models.Attendance)
        .filter(
            models.Attendance.enrollment_id == enrollment_id,
            models.Attendance.attendance_date >= start,
        )
        .first()
    )
    if existing:
        return existing
    db_att = models.Attendance(enrollment_id=enrollment_id)
    db.add(db_att)
    db.commit()
    db.refresh(db_att)
    attendance_date = getattr(db_att, "attendance_date", None)
    attendance_iso = None
    if isinstance(attendance_date, dt.datetime):
        attendance_iso = attendance_date.isoformat()
    _publish_event(
        "academy.attendance",
        "AttendanceRecorded",
        {
            "attendance_id": db_att.id,
            "enrollment_id": enrollment_id,
            "attendance_date": attendance_iso,
        },
    )
    return db_att


def get_assessment(db: Session, assessment_id: int) -> Optional[models.Assessment]:
    return db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()


def get_course_assessments(
    db: Session, course_id: int, published_only: bool = True
) -> List[models.Assessment]:
    query = db.query(models.Assessment).filter(models.Assessment.course_id == course_id)
    if published_only:
        query = query.filter(models.Assessment.is_published.is_(True))
    return query.order_by(models.Assessment.created_at.desc()).all()


def create_or_update_assessment_attempt(
    db: Session,
    enrollment: models.Enrollment,
    assessment: models.Assessment,
    submitted_score: float,
) -> models.AssessmentAttempt:
    raw_passing: Any = getattr(assessment, "passing_score", 0)
    passing_score = float(raw_passing) if isinstance(raw_passing, (int, float)) else 0.0
    passed = submitted_score >= passing_score
    attempt = (
        db.query(models.AssessmentAttempt)
        .filter(
            models.AssessmentAttempt.enrollment_id == enrollment.id,
            models.AssessmentAttempt.assessment_id == assessment.id,
        )
        .first()
    )
    if not attempt:
        attempt = models.AssessmentAttempt(
            enrollment_id=enrollment.id,
            assessment_id=assessment.id,
            submitted_score=submitted_score,
            passed=passed,
        )
        db.add(attempt)
    else:
        setattr(attempt, "submitted_score", submitted_score)
        setattr(attempt, "passed", passed)

    setattr(enrollment, "final_grade", submitted_score)
    setattr(enrollment, "approved", passed)
    if passed:
        setattr(enrollment, "status", "completed")
        setattr(enrollment, "progress_percent", 100)

    db.commit()
    db.refresh(attempt)
    _publish_event(
        "academy.assessments",
        "AssessmentSubmitted",
        {
            "attempt_id": attempt.id,
            "assessment_id": assessment.id,
            "course_id": assessment.course_id,
            "enrollment_id": enrollment.id,
            "user_id": enrollment.user_id,
            "submitted_score": submitted_score,
            "passed": passed,
        },
    )
    return attempt


def issue_certificate_for_enrollment(db: Session, enrollment: models.Enrollment) -> models.Certificate:
    existing = db.query(models.Certificate).filter(models.Certificate.enrollment_id == enrollment.id).first()
    if existing:
        return existing
    cert = models.Certificate(
        enrollment_id=enrollment.id,
        certificate_code=f"CCF-{uuid.uuid4().hex[:8].upper()}",
        certificate_type=enrollment.course.certificate_type,
    )
    db.add(cert)
    setattr(enrollment, "certificate_issued", True)
    db.commit()
    db.refresh(cert)
    _publish_event(
        "academy.certificates",
        "CertificateIssued",
        {
            "certificate_id": cert.id,
            "certificate_code": cert.certificate_code,
            "user_id": enrollment.user_id,
            "course_id": enrollment.course_id,
        },
    )
    return cert


def get_certificates_by_user(db: Session, user_id: int) -> List[models.Certificate]:
    return (
        db.query(models.Certificate)
        .join(models.Enrollment)
        .filter(models.Enrollment.user_id == user_id)
        .all()
    )


# -----------------
# CMS
# -----------------
def get_announcements(db: Session) -> List[models.Announcement]:
    return db.query(models.Announcement).order_by(models.Announcement.created_at.desc()).all()


def create_announcement(db: Session, announcement: schemas.AnnouncementCreate) -> models.Announcement:
    db_announcement = models.Announcement(**announcement.model_dump())
    db.add(db_announcement)
    db.commit()
    db.refresh(db_announcement)
    return db_announcement


def delete_announcement(db: Session, announcement_id: int) -> bool:
    announcement = db.query(models.Announcement).filter(models.Announcement.id == announcement_id).first()
    if not announcement:
        return False
    db.delete(announcement)
    db.commit()
    return True


def get_sermons(db: Session) -> List[models.Sermon]:
    return db.query(models.Sermon).order_by(models.Sermon.date.desc()).all()


def create_sermon(db: Session, sermon: schemas.SermonCreate) -> models.Sermon:
    db_sermon = models.Sermon(**sermon.model_dump())
    db.add(db_sermon)
    db.commit()
    db.refresh(db_sermon)
    return db_sermon


def delete_sermon(db: Session, sermon_id: int) -> bool:
    sermon = db.query(models.Sermon).filter(models.Sermon.id == sermon_id).first()
    if not sermon:
        return False
    db.delete(sermon)
    db.commit()
    return True


def create_book(db: Session, book: schemas.BookCreate) -> models.Book:
    db_book = models.Book(**book.model_dump())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book


def get_books(db: Session, skip: int = 0, limit: int = 100) -> List[models.Book]:
    return (
        db.query(models.Book)
        .order_by(models.Book.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def delete_book(db: Session, book_id: int) -> bool:
    db_book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not db_book:
        return False
    db.delete(db_book)
    db.commit()
    return True


def get_page_content(db: Session, page_key: str) -> Optional[models.PageContent]:
    return db.query(models.PageContent).filter(models.PageContent.page_key == page_key).first()


def _snapshot_page_content(db: Session, page_content: models.PageContent) -> None:
    version = models.PageContentVersion(
        page_content_id=page_content.id,
        title=page_content.title,
        content=page_content.content,
        image_url=page_content.image_url,
    )
    db.add(version)


def update_page_content(
    db: Session, page_key: str, content: schemas.PageContentUpdate
) -> models.PageContent:
    db_content = get_page_content(db, page_key)
    if not db_content:
        db_content = models.PageContent(page_key=page_key)
        db.add(db_content)
        db.commit()
        db.refresh(db_content)
    else:
        _snapshot_page_content(db, db_content)
    update_data = content.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_content, key, value)
    db.commit()
    db.refresh(db_content)
    return db_content


def get_page_content_versions(
    db: Session, page_key: str, limit: int = 20
) -> List[models.PageContentVersion]:
    db_content = get_page_content(db, page_key)
    if not db_content:
        return []
    return (
        db.query(models.PageContentVersion)
        .filter(models.PageContentVersion.page_content_id == db_content.id)
        .order_by(models.PageContentVersion.created_at.desc())
        .limit(limit)
        .all()
    )


def create_media_asset(
    db: Session,
    filename: str,
    url: str,
    mime_type: Optional[str],
    size_bytes: Optional[int],
) -> models.MediaAsset:
    asset = models.MediaAsset(
        filename=filename,
        url=url,
        mime_type=mime_type,
        size_bytes=size_bytes,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def increment_content_metric(
    db: Session,
    content_type: str,
    content_id: int,
    metric_type: str = "view",
    amount: int = 1,
) -> models.ContentMetric:
    metric = (
        db.query(models.ContentMetric)
        .filter(
            models.ContentMetric.content_type == content_type,
            models.ContentMetric.content_id == content_id,
            models.ContentMetric.metric_type == metric_type,
        )
        .first()
    )
    if not metric:
        metric = models.ContentMetric(
            content_type=content_type,
            content_id=content_id,
            metric_type=metric_type,
        )
        db.add(metric)
    current_value = getattr(metric, "value", 0) or 0
    setattr(metric, "value", int(current_value) + amount)
    db.commit()
    db.refresh(metric)
    return metric


# -----------------
# Agent Tasks & Insights
# -----------------
def create_agent_task(db: Session, task: schemas.AgentTaskCreate, status: str = "pending") -> models.AgentTask:
    db_task = models.AgentTask(**task.model_dump(), status=status)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def update_agent_task(
    db: Session, task_id: int, payload: schemas.AgentTaskUpdate
) -> Optional[models.AgentTask]:
    db_task = db.query(models.AgentTask).filter(models.AgentTask.id == task_id).first()
    if not db_task:
        return None
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)
    db.commit()
    db.refresh(db_task)
    return db_task


def list_agent_tasks(db: Session, status: Optional[str] = None) -> List[models.AgentTask]:
    query = db.query(models.AgentTask)
    if status:
        query = query.filter(models.AgentTask.status == status)
    return query.order_by(models.AgentTask.created_at.desc()).all()


def create_agent_insight(db: Session, insight: schemas.AgentInsightCreate) -> models.AgentInsight:
    db_insight = models.AgentInsight(**insight.model_dump())
    db.add(db_insight)
    db.commit()
    db.refresh(db_insight)
    return db_insight


def acknowledge_insight(db: Session, insight_id: int) -> Optional[models.AgentInsight]:
    insight = db.query(models.AgentInsight).filter(models.AgentInsight.id == insight_id).first()
    if not insight:
        return None
    setattr(insight, "acknowledged", True)
    db.commit()
    db.refresh(insight)
    return insight


def list_agent_insights(db: Session, acknowledged: Optional[bool] = None) -> List[models.AgentInsight]:
    query = db.query(models.AgentInsight)
    if acknowledged is not None:
        query = query.filter(models.AgentInsight.acknowledged == acknowledged)
    return query.order_by(models.AgentInsight.created_at.desc()).all()


# -----------------
# Families & CRM
# -----------------
def get_members(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    role: Optional[str] = None,
) -> List[models.Member]:
    query = db.query(models.Member)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                models.Member.first_name.ilike(like),
                models.Member.last_name.ilike(like),
                models.Member.email.ilike(like),
            )
        )
    if role:
        query = query.filter(models.Member.church_role == role)
    return query.order_by(models.Member.created_at.desc()).offset(skip).limit(limit).all()


def get_member_by_user(db: Session, user_id: int) -> Optional[models.Member]:
    return db.query(models.Member).filter(models.Member.user_id == user_id).first()


def create_member(db: Session, member: schemas.MemberCreate) -> models.Member:
    db_member = models.Member(**member.model_dump())
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member


def update_member(db: Session, member_id: int, member: schemas.MemberUpdate) -> Optional[models.Member]:
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not db_member:
        return None
    update_data = member.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_member, key, value)
    db.commit()
    db.refresh(db_member)
    return db_member


def create_family(db: Session, family: schemas.FamilyCreate) -> models.Family:
    db_family = models.Family(**family.model_dump())
    db.add(db_family)
    db.commit()
    db.refresh(db_family)
    return db_family


def get_families(db: Session, skip: int = 0, limit: int = 100) -> List[models.Family]:
    return db.query(models.Family).order_by(models.Family.created_at.desc()).offset(skip).limit(limit).all()


def get_events(db: Session, skip: int = 0, limit: int = 100) -> List[models.Event]:
    return db.query(models.Event).order_by(models.Event.created_at.desc()).offset(skip).limit(limit).all()


def create_event(db: Session, event: schemas.EventCreate) -> models.Event:
    db_event = models.Event(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def get_glory_houses(db: Session, skip: int = 0, limit: int = 100) -> List[models.GloryHouse]:
    return db.query(models.GloryHouse).order_by(models.GloryHouse.created_at.desc()).offset(skip).limit(limit).all()


def create_glory_house(db: Session, glory_house: schemas.GloryHouseCreate) -> models.GloryHouse:
    db_house = models.GloryHouse(**glory_house.model_dump())
    db.add(db_house)
    db.commit()
    db.refresh(db_house)
    return db_house


def get_volunteers(db: Session, skip: int = 0, limit: int = 100) -> List[models.Volunteer]:
    return db.query(models.Volunteer).order_by(models.Volunteer.created_at.desc()).offset(skip).limit(limit).all()


def create_volunteer(db: Session, volunteer: schemas.VolunteerCreate) -> models.Volunteer:
    db_volunteer = models.Volunteer(**volunteer.model_dump())
    db.add(db_volunteer)
    db.commit()
    db.refresh(db_volunteer)
    return db_volunteer


def get_pipeline_leads(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    stage: Optional[str] = None,
    assigned_pastor_id: Optional[int] = None,
    search: Optional[str] = None,
) -> List[models.ConsolidationPipeline]:
    query = db.query(models.ConsolidationPipeline)
    if stage:
        query = query.filter(models.ConsolidationPipeline.stage == stage)
    if assigned_pastor_id:
        query = query.filter(models.ConsolidationPipeline.assigned_pastor_id == assigned_pastor_id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                models.ConsolidationPipeline.first_name.ilike(like),
                models.ConsolidationPipeline.last_name.ilike(like),
                models.ConsolidationPipeline.phone.ilike(like),
            )
        )
    return query.order_by(models.ConsolidationPipeline.created_at.desc()).offset(skip).limit(limit).all()


def create_pipeline_lead(
    db: Session,
    lead: schemas.ConsolidationPipelineCreate,
) -> models.ConsolidationPipeline:
    db_lead = models.ConsolidationPipeline(**lead.model_dump())
    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)
    return db_lead


def update_pipeline_lead(
    db: Session,
    lead_id: int,
    payload: schemas.ConsolidationPipelineUpdate,
) -> Optional[models.ConsolidationPipeline]:
    db_lead = db.query(models.ConsolidationPipeline).filter(models.ConsolidationPipeline.id == lead_id).first()
    if not db_lead:
        return None
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_lead, key, value)
    db.commit()
    db.refresh(db_lead)
    return db_lead


def get_pastoral_call_logs(db: Session, lead_id: int) -> List[models.PastoralCallLog]:
    return (
        db.query(models.PastoralCallLog)
        .filter(models.PastoralCallLog.lead_id == lead_id)
        .order_by(models.PastoralCallLog.created_at.desc())
        .all()
    )


def create_pastoral_call_log(
    db: Session,
    lead_id: int,
    call_log: schemas.PastoralCallLogCreate,
) -> Optional[models.PastoralCallLog]:
    lead = db.query(models.ConsolidationPipeline).filter(models.ConsolidationPipeline.id == lead_id).first()
    if not lead:
        return None
    payload = call_log.model_dump()
    payload["lead_id"] = lead_id
    db_log = models.PastoralCallLog(**payload)
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


def create_counseling_session(db: Session, session: schemas.CounselingSessionCreate) -> models.CounselingSession:
    db_session = models.CounselingSession(**session.model_dump())
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


# -----------------
# Donations & Analytics
# -----------------
def create_donation(db: Session, donation: schemas.DonationCreate) -> models.Donation:
    db_donation = models.Donation(**donation.model_dump())
    db.add(db_donation)
    db.commit()
    db.refresh(db_donation)
    return db_donation


def get_donations(db: Session, skip: int = 0, limit: int = 100) -> List[models.Donation]:
    return db.query(models.Donation).order_by(models.Donation.created_at.desc()).offset(skip).limit(limit).all()


def get_total_donations_amount(db: Session) -> float:
    return db.query(func.sum(models.Donation.amount)).scalar() or 0.0


# -----------------
# Dashboard placeholders
# -----------------
def get_dashboard_metrics(db: Session) -> schemas.DashboardMetrics:
    total_courses = db.query(func.count(models.Course.id)).scalar() or 0
    formal = db.query(func.count(models.Course.id)).filter(models.Course.modality == "formal").scalar() or 0
    non_formal = total_courses - formal
    total_enrollments = db.query(func.count(models.Enrollment.id)).scalar() or 0
    completed = (
        db.query(func.count(models.Enrollment.id))
        .filter(models.Enrollment.status == "completed")
        .scalar()
        or 0
    )
    approved_formal = (
        db.query(func.count(models.Enrollment.id))
        .join(models.Course)
        .filter(models.Course.modality == "formal", models.Enrollment.approved.is_(True))
        .scalar()
        or 0
    )
    approved_non_formal = (
        db.query(func.count(models.Enrollment.id))
        .join(models.Course)
        .filter(models.Course.modality != "formal", models.Enrollment.approved.is_(True))
        .scalar()
        or 0
    )

    return schemas.DashboardMetrics(
        total_courses=total_courses,
        formal_courses=formal,
        non_formal_courses=non_formal,
        total_enrollments=total_enrollments,
        completed_enrollments=completed,
        approved_formal_enrollments=approved_formal,
        approved_non_formal_enrollments=approved_non_formal,
    )


def create_stored_procedures(db: Session) -> None:  # pragma: no cover
    # Placeholder to keep compatibility with startup bootstrap
    return None


def get_latest_acta_by_course(db: Session, course_id: int) -> Optional[models.FormalActa]:
    return (
        db.query(models.FormalActa)
        .filter(models.FormalActa.course_id == course_id)
        .order_by(models.FormalActa.created_at.desc())
        .first()
    )


def close_formal_acta(
    db: Session,
    course_id: int,
    closed_by_user_id: int,
    min_grade: float,
    min_attendance: float,
) -> models.FormalActa:
    acta = models.FormalActa(
        course_id=course_id,
        closed_by_user_id=closed_by_user_id,
        min_grade=min_grade,
        min_attendance=min_attendance,
    )
    db.add(acta)
    db.commit()
    db.refresh(acta)
    return acta


def get_pilot_readiness(db: Session) -> schemas.PilotReadiness:
    metrics = get_dashboard_metrics(db)
    checklist = [
        schemas.PilotChecklistItem(
            key="courses_published",
            label="Cursos publicados",
            completed=metrics.total_courses > 0,
        ),
        schemas.PilotChecklistItem(
            key="formal_courses",
            label="Programas formales",
            completed=metrics.formal_courses > 0,
        ),
        schemas.PilotChecklistItem(
            key="enrollments_active",
            label="Estudiantes activos",
            completed=metrics.total_enrollments > 0,
        ),
        schemas.PilotChecklistItem(
            key="certificates",
            label="Certificados emitidos",
            completed=(metrics.approved_formal_enrollments + metrics.approved_non_formal_enrollments) > 0,
        ),
    ]
    readiness_score = sum(1 for item in checklist if item.completed)
    return schemas.PilotReadiness(
        environment_ready=True,
        kpi_dashboard_ready=True,
        support_ready=True,
        security_ready=metrics.total_courses > 0,
        checklist=checklist,
        readiness_score=readiness_score / len(checklist),
    )


def issue_pending_certificates(db: Session) -> List[models.Certificate]:
    enrollments = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.approved.is_(True), models.Enrollment.certificate_issued.is_(False))
        .all()
    )
    issued: List[models.Certificate] = []
    for enrollment in enrollments:
        issued.append(issue_certificate_for_enrollment(db, enrollment))
    return issued


# -----------------
# Governance & Audit
# -----------------
def create_admin_audit_log(
    db: Session,
    actor_user_id: int,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> models.AdminAuditLog:
    entry = models.AdminAuditLog(
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata,
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_admin_audit_logs(
    db: Session,
    limit: int = 100,
    actor_user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
) -> List[models.AdminAuditLog]:
    query = db.query(models.AdminAuditLog).order_by(models.AdminAuditLog.created_at.desc())
    if actor_user_id:
        query = query.filter(models.AdminAuditLog.actor_user_id == actor_user_id)
    if resource_type:
        query = query.filter(models.AdminAuditLog.resource_type == resource_type)
    return query.limit(limit).all()
# -----------------
# Refresh Tokens
# -----------------
def create_refresh_token(db: Session, user_id: int, token: str, expires_at: dt.datetime) -> models.RefreshToken:
    db_token = models.RefreshToken(user_id=user_id, token=token, expires_at=expires_at)
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token


def revoke_refresh_token(db: Session, token: str) -> None:
    db_token = db.query(models.RefreshToken).filter(models.RefreshToken.token == token).first()
    if db_token is not None:
        setattr(db_token, "revoked", True)
        db.commit()


def verify_refresh_token(db: Session, token: str) -> Optional[models.RefreshToken]:
    refresh: Optional[models.RefreshToken] = (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.token == token, models.RefreshToken.revoked.is_(False))
        .first()
    )
    if refresh is None:
        return None
    expires_at = getattr(refresh, "expires_at", None)
    if not isinstance(expires_at, dt.datetime):
        return None
    if expires_at <= dt.datetime.utcnow():
        return None
    return refresh
