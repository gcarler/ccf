from __future__ import annotations

import datetime as dt
import json
import logging
import uuid
from typing import Any, List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from backend import models
from backend import schemas
from backend.content_defaults import PAGE_CONTENT_DEFAULTS
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
def get_user(db: Session, user_id: uuid.UUID) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.user_id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).join(models.Person).filter(models.Person.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = get_password_hash(user.password)
    # 1. Crear el usuario en identity
    db_user = models.User(
        username=user.username,
        password_hash=hashed_password,
    )
    db.add(db_user)
    db.flush() # Para obtener el user_id

    # 2. Crear la persona vinculada en membership
    db_person = models.Person(
        user_id=db_user.user_id,
        first_name=user.username, # Placeholder
        last_name="Usuario",      # Placeholder
        email=user.email,
    )
    db.add(db_person)
    
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_password(db: Session, user: models.User, password: str) -> models.User:
    hashed_password = get_password_hash(password)
    setattr(user, "password_hash", hashed_password)
    db.commit()
    db.refresh(user)
    return user


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()


def get_users_count(db: Session) -> int:
    return db.query(models.User).count()


def create_password_reset_token(
    db: Session,
    user_id: int,
    token: str,
    expires_at: dt.datetime,
) -> models.PasswordResetToken:
    entry = models.PasswordResetToken(user_id=user_id, token=token, expires_at=expires_at)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_password_reset_token(db: Session, token: str) -> Optional[models.PasswordResetToken]:
    return (
        db.query(models.PasswordResetToken)
        .filter(
            models.PasswordResetToken.token == token,
            models.PasswordResetToken.used.is_(False),
        )
        .first()
    )


def mark_password_reset_used(db: Session, entry: models.PasswordResetToken) -> None:
    setattr(entry, "used", True)
    db.commit()


def create_email_verification_token(
    db: Session,
    user_id: int,
    token: str,
    expires_at: dt.datetime,
) -> models.EmailVerificationToken:
    entry = models.EmailVerificationToken(user_id=user_id, token=token, expires_at=expires_at)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_email_verification_token(db: Session, token: str) -> Optional[models.EmailVerificationToken]:
    return (
        db.query(models.EmailVerificationToken)
        .filter(
            models.EmailVerificationToken.token == token,
            models.EmailVerificationToken.used.is_(False),
        )
        .first()
    )


def mark_email_verification_used(db: Session, entry: models.EmailVerificationToken) -> None:
    setattr(entry, "used", True)
    db.commit()


def mark_user_verified(db: Session, user: models.User) -> models.User:
    setattr(user, "is_email_verified", True)
    db.commit()
    db.refresh(user)
    return user


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
    approved_only: bool = True,
) -> List[models.Testimonial]:
    query = db.query(models.Testimonial).options(joinedload(models.Testimonial.author))
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
    
    # If setting to show on home, unmark all others
    if update_data.get("show_on_home") is True:
        db.query(models.Testimonial).update({models.Testimonial.show_on_home: False})
        db.flush()

    for key, value in update_data.items():
        setattr(db_testimonial, key, value)
    db.commit()
    db.refresh(db_testimonial)
    return db_testimonial


# -----------------
# Prayer & Support
# -----------------
def create_prayer_request(db: Session, request: schemas.PrayerRequestCreate) -> models.PrayerRequest:
    db_request = models.PrayerRequest(**request.model_dump())
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return db_request


def get_prayer_requests(db: Session, skip: int = 0, limit: int = 100) -> List[models.PrayerRequest]:
    return db.query(models.PrayerRequest).order_by(models.PrayerRequest.created_at.desc()).offset(skip).limit(limit).all()


def create_support_ticket(db: Session, ticket: schemas.SupportTicketCreate) -> models.SupportTicket:
    db_ticket = models.SupportTicket(**ticket.model_dump())
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket


def get_support_tickets(db: Session, user_id: Optional[int] = None, skip: int = 0, limit: int = 100):
    query = db.query(models.SupportTicket)
    if user_id:
        query = query.filter(models.SupportTicket.user_id == user_id)
    return query.order_by(models.SupportTicket.created_at.desc()).offset(skip).limit(limit).all()


def update_support_ticket(db: Session, ticket_id: int, status: str) -> Optional[models.SupportTicket]:
    db_ticket = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()
    if db_ticket:
        db_ticket.status = status
        db.commit()
        db.refresh(db_ticket)
    return db_ticket



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
    # Optimized with joinedload for lessons to avoid N+1 in catalog
    query = db.query(models.Course).options(joinedload(models.Course.lessons))
    if modality:
        query = query.filter(models.Course.modality == modality)
    if published_only:
        query = query.filter(models.Course.is_published.is_(True))
    return query.order_by(models.Course.created_at.desc()).offset(skip).limit(limit).all()


def get_course(db: Session, course_id: int) -> Optional[models.Course]:
    # Deep loading for full course view (lessons + assessments + resources)
    return (
        db.query(models.Course)
        .options(
            joinedload(models.Course.lessons).joinedload(models.Lesson.resources),
            joinedload(models.Course.assessments)
        )
        .filter(models.Course.id == course_id)
        .first()
    )


def update_course(
    db: Session, 
    course_id: int, 
    course_update: schemas.CourseBase,
    actor_id: Optional[int] = None
) -> Optional[models.Course]:
    db_course = get_course(db, course_id)
    if not db_course:
        return None
    
    update_data = course_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_course, key, value)
    
    db.commit()
    db.refresh(db_course)
    
    if actor_id:
        create_admin_audit_log(
            db, actor_user_id=actor_id, action="UPDATE", 
            resource_type="course", resource_id=str(course_id),
            metadata=update_data
        )
    
    return db_course


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
        db.add(models.Lesson(course_id=course.id, title="Introducci??n", content="Contenido base."))
    db.commit()


def _ensure_storyteller_user(db: Session) -> models.User:
    storyteller = get_user_by_email(db, "historias@ccf.la")
    if storyteller:
        return storyteller
    payload = schemas.UserCreate(
        username="historias.ccf",
        email="historias@ccf.la",
        password="Historias2026!",
        role="estudiante",
    )
    return create_user(db, payload)


def seed_public_content_if_empty(db: Session) -> None:
    if db.query(models.Announcement).count() == 0:
        announcements = [
            {
                "title": "Nueva temporada de discipulados",
                "content": "Inscr??bete en los grupos presenciales y online. Cupos limitados.",
                "image_url": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=900&q=80",
                "category": "Comunidad",
            },
            {
                "title": "Servicios presenciales reactivados",
                "content": "Abrimos tres reuniones dominicales con registro previo.",
                "image_url": "https://images.unsplash.com/photo-1497493292307-31c376b6e479?auto=format&fit=crop&w=900&q=80",
                "category": "Servicios",
            },
        ]
        db.bulk_insert_mappings(models.Announcement, announcements)
        db.commit()

    if db.query(models.Sermon).count() == 0:
        sermons = [
            {
                "title": "Sombras que sanan",
                "description": "Serie sobre hechos 5 y el poder de la iglesia primitiva.",
                "preacher": "Ps. Daniela Rodr??guez",
                "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "thumbnail_url": "https://images.unsplash.com/photo-1477414348463-c0eb7f1359b6?auto=format&fit=crop&w=900&q=80",
                "duration": "38:21",
                "series": "Hechos",
            },
            {
                "title": "Fe que se mueve",
                "description": "C??mo mantenernos expectantes en tiempos inciertos.",
                "preacher": "Ps. Andr??s Cepeda",
                "video_url": "https://www.youtube.com/watch?v=FTQbiNvZqaY",
                "thumbnail_url": "https://images.unsplash.com/photo-1481502049730-356c797990d4?auto=format&fit=crop&w=900&q=80",
                "duration": "31:10",
                "series": "Fe pr??ctica",
            },
        ]
        db.bulk_insert_mappings(models.Sermon, sermons)
        db.commit()

    if db.query(models.Book).count() == 0:
        books = [
            {
                "title": "Fundamentos del discipulado",
                "author": "CCF Studio",
                "description": "Gu??a pr??ctica para acompa??ar a nuevos creyentes.",
                "cover_image_url": "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?auto=format&fit=crop&w=800&q=80",
                "download_url": "https://files.ccf.la/discipulado.pdf",
            },
            {
                "title": "Devocional 21 d??as",
                "author": "Ps. Carolina",
                "description": "Lecturas cortas para fortalecer tu oraci??n.",
                "cover_image_url": "https://images.unsplash.com/photo-1455885666463-1ef414b56a8b?auto=format&fit=crop&w=800&q=80",
                "download_url": "https://files.ccf.la/devocional-21-dias.pdf",
            },
        ]
        db.bulk_insert_mappings(models.Book, books)
        db.commit()

    if db.query(models.Event).count() == 0:
        now = dt.datetime.utcnow()
        events = [
            {
                "title": "Noche de adoracion",
                "description": "Encuentro creativo con banda en vivo y testimonios.",
                "event_type": "Reunion",
                "event_date": now + dt.timedelta(days=5),
            },
            {
                "title": "Bootcamp de liderazgo",
                "description": "Entrenamiento intensivo para lideres de casa.",
                "event_type": "Formacion",
                "event_date": now + dt.timedelta(days=12),
            },
            {
                "title": "Salida misionera Amazonas",
                "description": "Viaje corto a comunidades rurales.",
                "event_type": "Mision",
                "event_date": now + dt.timedelta(days=25),
            },
        ]
        db.bulk_insert_mappings(models.Event, events)
        db.commit()

    if db.query(models.GloryHouse).count() == 0:
        houses = [
            {
                "name": "Casa Norte",
                "zone": "Comuna 4",
                "leader_name": "Luis y Mar??a",
                "members_count": 18,
                "schedule": "Mi??rcoles 7:00 p.m.",
            },
            {
                "name": "Casa Central",
                "zone": "Centro",
                "leader_name": "Juan y Paula",
                "members_count": 24,
                "schedule": "Viernes 6:30 p.m.",
            },
            {
                "name": "Casa Sur",
                "zone": "B?? Jardines",
                "leader_name": "Eliana y Carlos",
                "members_count": 15,
                "schedule": "Domingo 5:00 p.m.",
            },
        ]
        db.bulk_insert_mappings(models.GloryHouse, houses)
        db.commit()

    if db.query(models.Testimonial).count() == 0:
        storyteller = _ensure_storyteller_user(db)
        testimonies = [
            {
                "user_id": storyteller.user_id,
                "content": "Dios restauro nuestra familia durante el ciclo de consejeria.",
                "category": "Agradecido",
                "is_approved": True,
            },
            {
                "user_id": storyteller.user_id,
                "content": "Encontre proposito sirviendo en la Casa de Gloria.",
                "category": "Inspirado",
                "is_approved": True,
            },
        ]
        db.bulk_insert_mappings(models.Testimonial, testimonies)
        db.commit()


def ensure_page_content_defaults(db: Session) -> None:
    created = False
    for key, payload in PAGE_CONTENT_DEFAULTS.items():
        if get_page_content(db, key):
            continue
        data = payload.copy()
        content_value = data.get("content")
        if isinstance(content_value, (dict, list)):
            data["content"] = json.dumps(content_value)
        record = models.PageContent(page_key=key, **data)
        db.add(record)
        created = True
    if created:
        db.commit()

def get_donations_total(db: Session) -> float:
    return get_total_donations_amount(db)


def get_attendance_avg(db: Session) -> int:
    return 850


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
        raise ValueError("El curso no est?? disponible")

    # --- Prerequisite Check ---
    prerequisites = db.query(models.CoursePrerequisite).filter(models.CoursePrerequisite.course_id == enrollment.course_id).all()
    for prereq in prerequisites:
        # Check if user has an enrollment for the prerequisite course that is approved/completed
        approved_prereq = (
            db.query(models.Enrollment)
            .filter(
                models.Enrollment.user_id == enrollment.user_id,
                models.Enrollment.course_id == prereq.prerequisite_course_id,
                models.Enrollment.approved.is_(True)
            )
            .first()
        )
        if not approved_prereq:
            prereq_course = get_course(db, prereq.prerequisite_course_id)
            raise ValueError(f"No has aprobado el prerrequisito obligatorio: {prereq_course.title}")
    # --------------------------

    existing = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.user_id == enrollment.user_id,
            models.Enrollment.course_id == enrollment.course_id,
        )
        .first()
    )
    if existing:
        raise ValueError("El usuario ya est?? inscrito en este curso")

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


def create_assignment_submission(
    db: Session,
    enrollment_id: int,
    lesson_id: int,
    file_url: str,
    comment: Optional[str] = None,
) -> models.AssignmentSubmission:
    submission = models.AssignmentSubmission(
        enrollment_id=enrollment_id,
        lesson_id=lesson_id,
        file_url=file_url,
        comment=comment,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


def list_assignment_submissions_with_meta(
    db: Session,
    limit: int = 100,
) -> List[Tuple[models.AssignmentSubmission, str, str]]:
    rows = (
        db.query(
            models.AssignmentSubmission,
            models.Lesson.title.label("lesson_title"),
            models.User.username.label("student_name"),
        )
        .join(models.Lesson, models.AssignmentSubmission.lesson_id == models.Lesson.id)
        .join(models.Enrollment, models.AssignmentSubmission.enrollment_id == models.Enrollment.id)
        .join(models.User, models.Enrollment.user_id == models.User.id)
        .order_by(models.AssignmentSubmission.created_at.desc())
        .limit(limit)
        .all()
    )
    return [(row[0], row[1], row[2]) for row in rows]


def get_assignment_submission_with_meta(
    db: Session, submission_id: int
) -> Optional[Tuple[models.AssignmentSubmission, str, str]]:
    row = (
        db.query(
            models.AssignmentSubmission,
            models.Lesson.title.label("lesson_title"),
            models.User.username.label("student_name"),
        )
        .join(models.Lesson, models.AssignmentSubmission.lesson_id == models.Lesson.id)
        .join(models.Enrollment, models.AssignmentSubmission.enrollment_id == models.Enrollment.id)
        .join(models.User, models.Enrollment.user_id == models.User.id)
        .filter(models.AssignmentSubmission.id == submission_id)
        .first()
    )
    if not row:
        return None
    return row[0], row[1], row[2]


def grade_assignment_submission(
    db: Session,
    submission_id: int,
    grade: Optional[float] = None,
    feedback: Optional[str] = None,
) -> Optional[models.AssignmentSubmission]:
    submission = (
        db.query(models.AssignmentSubmission)
        .filter(models.AssignmentSubmission.id == submission_id)
        .first()
    )
    if not submission:
        return None
    if grade is not None:
        setattr(submission, "grade", grade)
    if feedback is not None:
        setattr(submission, "teacher_feedback", feedback)
    db.commit()
    db.refresh(submission)
    return submission


def record_member_attendance(db: Session, member_id: int, event_id: Optional[int] = None) -> models.Attendance:
    db_att = models.Attendance(member_id=member_id, event_id=event_id)
    db.add(db_att)
    db.commit()
    db.refresh(db_att)
    
    # Trigger Workflows
    process_workflows(db, "attendance_created", {"member_id": member_id})
    
    return db_att


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
    
    # Also trigger workflow for student attendance if linked to member
    enrollment = db.query(models.Enrollment).filter(models.Enrollment.id == enrollment_id).first()
    if enrollment and enrollment.student.member:
        process_workflows(db, "attendance_created", {"member_id": enrollment.student.member[0].id})
        
    return db_att
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


def get_member_academy_profile(db: Session, member_id: int) -> schemas.MemberAcademyProfile:
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        return schemas.MemberAcademyProfile(is_linked=False, enrollments=[])
    user_id = getattr(member, "user_id", None)
    if not user_id:
        return schemas.MemberAcademyProfile(is_linked=False, enrollments=[])
    user = get_user(db, int(user_id))
    if not user:
        return schemas.MemberAcademyProfile(is_linked=False, enrollments=[])
    enrollments = get_enrollments_by_user(db, int(user_id))
    return schemas.MemberAcademyProfile(
        is_linked=True,
        username=user.username,
        enrollments=enrollments,
    )


def create_member_academy_account(db: Session, member_id: int, password: str) -> models.User:
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise ValueError("Miembro no encontrado")
    if not member.email:
        raise ValueError("El miembro no tiene un correo registrado")
    if member.user_id:
        user = get_user(db, int(member.user_id))
        if not user:
            setattr(member, "user_id", None)
            db.commit()
        else:
            update_user_password(db, user, password)
            return user
    base_username = (member.first_name or "miembro").lower()
    username = f"{base_username}.{member.id}".replace(" ", "")
    if get_user_by_email(db, member.email):
        username = f"miembro.{member.id}"
    user_schema = schemas.UserCreate(
        username=username,
        email=member.email,
        password=password,
        role="estudiante",
    )
    user = create_user(db, user_schema)
    setattr(member, "user_id", user.id)
    db.commit()
    return user


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


def create_attendance_record(db: Session, payload: schemas.AttendanceCreate) -> models.Attendance:
    entry = models.Attendance(**payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


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


def get_crm_settings(db: Session) -> models.CrmSettings:
    settings = db.query(models.CrmSettings).order_by(models.CrmSettings.id.asc()).first()
    if settings:
        return settings
    settings = models.CrmSettings()
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def save_crm_settings(
    db: Session,
    payload: schemas.CrmSettingsUpdate,
    updated_by: Optional[int] = None,
) -> models.CrmSettings:
    settings = get_crm_settings(db)
    update_data = payload.model_dump(exclude_unset=True)
    if updated_by is not None:
        update_data["updated_by_user_id"] = updated_by
    for key, value in update_data.items():
        setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return settings


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


def get_pipeline_lead(db: Session, lead_id: int) -> Optional[models.ConsolidationPipeline]:
    return db.query(models.ConsolidationPipeline).filter(models.ConsolidationPipeline.id == lead_id).first()


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


def list_consolidation_automations(db: Session) -> List[models.ConsolidationAutomation]:
    return db.query(models.ConsolidationAutomation).order_by(models.ConsolidationAutomation.stage.asc()).all()


def create_consolidation_automation(
    db: Session,
    payload: schemas.ConsolidationAutomationCreate,
) -> models.ConsolidationAutomation:
    entry = models.ConsolidationAutomation(**payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def update_consolidation_automation(
    db: Session,
    automation_id: int,
    payload: schemas.ConsolidationAutomationUpdate,
) -> Optional[models.ConsolidationAutomation]:
    entry = db.query(models.ConsolidationAutomation).filter(models.ConsolidationAutomation.id == automation_id).first()
    if not entry:
        return None
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(entry, key, value)
    db.commit()
    db.refresh(entry)
    return entry


def delete_consolidation_automation(db: Session, automation_id: int) -> bool:
    entry = db.query(models.ConsolidationAutomation).filter(models.ConsolidationAutomation.id == automation_id).first()
    if not entry:
        return False
    db.delete(entry)
    db.commit()
    return True


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


from backend.messaging_service import messaging_service

def create_communication_log(
    db: Session,
    payload: schemas.CommunicationLogCreate,
) -> models.CommunicationLog:
    entry = models.CommunicationLog(**payload.model_dump())
    db.add(entry)
    
    # Trigger real messaging service
    member = db.query(models.Member).filter(models.Member.id == payload.member_id).first()
    if member:
        if payload.channel == "sms" and member.phone:
            messaging_service.send_sms(member.phone, payload.content)
        elif payload.channel == "whatsapp" and member.phone:
            messaging_service.send_whatsapp(member.phone, payload.content)
        elif payload.channel == "email" and member.email:
            messaging_service.send_email(member.email, "Mensaje Pastoral - CCF", payload.content)

    db.commit()
    db.refresh(entry)
    return entry


def get_member_communication_logs(
    db: Session,
    member_id: int,
    limit: int = 50,
) -> List[models.CommunicationLog]:
    return (
        db.query(models.CommunicationLog)
        .filter(models.CommunicationLog.member_id == member_id)
        .order_by(models.CommunicationLog.created_at.desc())
        .limit(limit)
        .all()
    )


def get_communication_logs(db: Session, limit: int = 50) -> List[models.CommunicationLog]:
    return (
        db.query(models.CommunicationLog)
        .order_by(models.CommunicationLog.created_at.desc())
        .limit(limit)
        .all()
    )


def list_counseling_sessions(
    db: Session,
    lead_id: Optional[int] = None,
    member_id: Optional[int] = None,
) -> List[models.CounselingSession]:
    query = db.query(models.CounselingSession)
    if lead_id is not None:
        query = query.filter(models.CounselingSession.lead_id == lead_id)
    if member_id is not None:
        query = query.filter(models.CounselingSession.member_id == member_id)
    return query.order_by(models.CounselingSession.scheduled_at.desc()).all()


def get_counseling_session(db: Session, session_id: int) -> Optional[models.CounselingSession]:
    return db.query(models.CounselingSession).filter(models.CounselingSession.id == session_id).first()


def update_counseling_session(
    db: Session,
    session_id: int,
    payload: schemas.CounselingSessionUpdate,
) -> Optional[models.CounselingSession]:
    session = get_counseling_session(db, session_id)
    if not session:
        return None
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(session, key, value)
    db.commit()
    db.refresh(session)
    return session


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


def get_analytics_summary(db: Session):
    # 1. Member growth (last 6 months)
    # Simple count by month for demonstration
    member_growth = [
        {"month": "Oct", "count": 1100},
        {"month": "Nov", "count": 1150},
        {"month": "Dic", "count": 1180},
        {"month": "Ene", "count": 1210},
        {"month": "Feb", "count": 1230},
        {"month": "Mar", "count": 1240}
    ]
    
    # 2. Attendance trend (last 4 weeks)
    attendance_trend = [
        {"week": "Sem 1", "present": 850},
        {"week": "Sem 2", "present": 880},
        {"week": "Sem 3", "present": 820},
        {"week": "Sem 4", "present": 910}
    ]
    
    # 3. Donations summary
    donation_stats = [
        {"category": "Diezmos", "value": 8200},
        {"category": "Ofrendas", "value": 4250},
        {"category": "Proyectos", "value": 1500}
    ]
    
    return {
        "member_growth": member_growth,
        "attendance_trend": attendance_trend,
        "donation_stats": donation_stats
    }


def get_total_donations_amount(db: Session) -> float:
    return db.query(func.sum(models.Donation.amount)).scalar() or 0.0


# -----------------
# Treasury & Finance
# -----------------

def create_treasury_transaction(
    db: Session, transaction: schemas.TreasuryTransactionCreate
) -> models.TreasuryTransaction:
    db_transaction = models.TreasuryTransaction(**transaction.model_dump())
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction


def get_treasury_transactions(
    db: Session, skip: int = 0, limit: int = 100, type: Optional[str] = None
) -> List[models.TreasuryTransaction]:
    query = db.query(models.TreasuryTransaction)
    if type:
        query = query.filter(models.TreasuryTransaction.type == type)
    return query.order_by(models.TreasuryTransaction.date.desc()).offset(skip).limit(limit).all()


def get_treasury_summary(db: Session):
    income = db.query(func.sum(models.TreasuryTransaction.amount)).filter(models.TreasuryTransaction.type == "income").scalar() or 0.0
    expense = db.query(func.sum(models.TreasuryTransaction.amount)).filter(models.TreasuryTransaction.type == "expense").scalar() or 0.0
    return {
        "total_income": income,
        "total_expense": expense,
        "balance": income - expense
    }


# -----------------
# Workspace Config
# -----------------

def get_workspace_config(db: Session) -> Optional[models.WorkspaceConfig]:
    return db.query(models.WorkspaceConfig).filter(models.WorkspaceConfig.is_active == True).first()


def update_workspace_config(
    db: Session, config_update: schemas.WorkspaceConfigUpdate, user_id: int
) -> models.WorkspaceConfig:
    db_config = get_workspace_config(db)
    if not db_config:
        # Create initial if none exists
        db_config = models.WorkspaceConfig(
            features_enabled={},
            ui_theme_config={},
            navigation_schema=[],
            updated_by_id=user_id
        )
        db.add(db_config)
    
    update_data = config_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_config, key, value)
    
    db_config.updated_by_id = user_id
    db.commit()
    db.refresh(db_config)
    return db_config


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

    total_members = db.query(func.count(models.Member.id)).scalar() or 0
    active_members = db.query(func.count(models.Member.id)).filter(models.Member.church_role != "Inactivo").scalar() or 0

    total_glory_houses = db.query(func.count(models.GloryHouse.id)).scalar() or 0
    total_donations = db.query(func.sum(models.Donation.amount)).scalar() or 0.0

    cards = [
        schemas.MetricCard(title='Total Miembros', value=f"{total_members:,}", trend='+12', tone='blue'),
        schemas.MetricCard(title='Casas de Gloria', value=str(total_glory_houses), trend='+2', tone='indigo'),
        schemas.MetricCard(title='Estudiantes Activos', value=str(total_enrollments), trend='+5', tone='emerald'),
        schemas.MetricCard(title='Donaciones (Mes)', value=f"${total_donations:,.0f}", trend='+15%', tone='amber')
    ]

    return schemas.DashboardMetrics(
        total_courses=total_courses,
        formal_courses=formal,
        non_formal_courses=non_formal,
        total_enrollments=total_enrollments,
        completed_enrollments=completed,
        approved_formal_enrollments=approved_formal,
        approved_non_formal_enrollments=approved_non_formal,
        cards=cards
    )


# -----------------
# Notifications
# -----------------
def create_notification(db: Session, notification: schemas.NotificationCreate) -> models.Notification:
    db_notification = models.Notification(**notification.model_dump())
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification


def get_user_notifications(db: Session, user_id: int, limit: int = 20) -> List[models.Notification]:
    return (
        db.query(models.Notification)
        .filter(models.Notification.user_id == user_id)
        .order_by(models.Notification.created_at.desc())
        .limit(limit)
        .all()
    )


def mark_notification_as_read(db: Session, notification_id: int) -> Optional[models.Notification]:
    db_notif = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if db_notif:
        db_notif.is_read = True
        db.commit()
        db.refresh(db_notif)
    return db_notif


def mark_all_notifications_read(db: Session, user_id: int):
    db.query(models.Notification).filter(
        models.Notification.user_id == user_id, 
        models.Notification.is_read == False
    ).update({models.Notification.is_read: True})
    db.commit()


# -----------------
# Assessments & Questions
# -----------------
def create_assessment_question(db: Session, question: schemas.AssessmentQuestionCreate) -> models.AssessmentQuestion:
    db_question = models.AssessmentQuestion(**question.model_dump())
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question


def create_question_option(db: Session, option: schemas.QuestionOptionCreate) -> models.QuestionOption:
    db_option = models.QuestionOption(**option.model_dump())
    db.add(db_option)
    db.commit()
    db.refresh(db_option)
    return db_option


def get_assessment_with_questions(db: Session, assessment_id: int) -> Optional[models.Assessment]:
    return db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()


def submit_assessment_attempt(
    db: Session, 
    assessment_id: int, 
    enrollment_id: int, 
    answers: List[dict] # List of {"question_id": int, "selected_option_id": int}
) -> models.AssessmentAttempt:
    assessment = get_assessment_with_questions(db, assessment_id)
    if not assessment:
        raise ValueError("Assessment not found")
    
    total_points = 0.0
    earned_points = 0.0
    
    # Simple scoring logic for multiple choice
    for q in assessment.questions:
        total_points += q.points
        user_answer = next((a for a in answers if a["question_id"] == q.id), None)
        if user_answer:
            correct_option = next((o for o in q.options if o.is_correct), None)
            if correct_option and correct_option.id == user_answer["selected_option_id"]:
                earned_points += q.points
                
    score = (earned_points / total_points) * assessment.max_score if total_points > 0 else 0.0
    passed = score >= assessment.passing_score
    
    db_attempt = models.AssessmentAttempt(
        assessment_id=assessment_id,
        enrollment_id=enrollment_id,
        submitted_score=score,
        passed=passed
    )
    db.add(db_attempt)
    
    # Update enrollment progress/status if passed
    enrollment = db.query(models.Enrollment).filter(models.Enrollment.id == enrollment_id).first()
    if enrollment and passed:
        enrollment.progress_percent = 100.0 # Simplification
        enrollment.status = "completed"
        
    db.commit()
    db.refresh(db_attempt)
    return db_attempt


# -----------------
# Multimedia & Progress
# -----------------
def update_lesson_progress(
    db: Session, 
    user_id: int, 
    lesson_id: int, 
    progress_percent: float, 
    last_position: int
) -> models.UserLessonProgress:
    db_progress = db.query(models.UserLessonProgress).filter(
        models.UserLessonProgress.user_id == user_id,
        models.UserLessonProgress.lesson_id == lesson_id
    ).first()
    
    if not db_progress:
        db_progress = models.UserLessonProgress(
            user_id=user_id,
            lesson_id=lesson_id,
            progress_percent=progress_percent,
            last_position_seconds=last_position,
            is_completed=progress_percent >= 95.0
        )
        db.add(db_progress)
    else:
        db_progress.progress_percent = max(db_progress.progress_percent, progress_percent)
        db_progress.last_position_seconds = last_position
        if not db_progress.is_completed:
            db_progress.is_completed = progress_percent >= 95.0
            
    db.commit()
    db.refresh(db_progress)
    return db_progress


import uuid

# ... rest of imports

def get_lesson_progress(db: Session, user_id: int, lesson_id: int) -> Optional[models.UserLessonProgress]:
    return db.query(models.UserLessonProgress).filter(
        models.UserLessonProgress.user_id == user_id,
        models.UserLessonProgress.lesson_id == lesson_id
    ).first()


# -----------------
# Knowledge Base (AI)
# -----------------
def create_kb_entry(db: Session, title: str, content: str, category: str = "Doctrine") -> models.KnowledgeBase:
    db_kb = models.KnowledgeBase(title=title, content=content, category=category)
    db.add(db_kb)
    db.commit()
    db.refresh(db_kb)
    return db_kb


def search_knowledge_base(db: Session, query: str, limit: int = 5) -> List[models.KnowledgeBase]:
    # Simple keyword search for now
    return db.query(models.KnowledgeBase).filter(
        models.KnowledgeBase.content.ilike(f"%{query}%") | 
        models.KnowledgeBase.title.ilike(f"%{query}%")
    ).limit(limit).all()


# -----------------
# Workflows & Automations
# -----------------
def create_workflow_rule(db: Session, name: str, trigger: str, action: str, condition: dict = None, payload: dict = None) -> models.WorkflowRule:
    db_rule = models.WorkflowRule(
        name=name, 
        trigger_event=trigger, 
        condition_json=condition, 
        action_type=action, 
        action_payload=payload
    )
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule


def process_workflows(db: Session, event: str, context: dict):
    rules = db.query(models.WorkflowRule).filter(models.WorkflowRule.trigger_event == event, models.WorkflowRule.is_active == True).all()
    for rule in rules:
        try:
            # 1. Check conditions
            if event == "attendance_created":
                member_id = context.get("member_id")
                if not member_id: continue
                
                if rule.condition_json and rule.condition_json.get("count"):
                    count = db.query(func.count(models.Attendance.id)).filter(models.Attendance.member_id == member_id).scalar()
                    if count >= rule.condition_json["count"]:
                        # 2. Execute action
                        if rule.action_type == "create_agent_task":
                            create_agent_task(db, schemas.AgentTaskCreate(
                                title=rule.action_payload.get("title", "Tarea Autom??tica"),
                                description=f"El miembro #{member_id} ha cumplido la condici??n: {rule.name}",
                                priority="high",
                                source="workflow"
                            ))
                            print(f"Workflow '{rule.name}' executed: Task created.")
        except Exception as e:
            print(f"Error processing workflow {rule.name}: {e}")


def issue_certificate(db: Session, enrollment_id: int) -> models.Certificate:
    # Check if already exists
    existing = db.query(models.Certificate).filter(models.Certificate.enrollment_id == enrollment_id).first()
    if existing:
        return existing
    
    enrollment = db.query(models.Enrollment).filter(models.Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise ValueError("Enrollment not found")
        
    cert_code = f"CCF-{uuid.uuid4().hex[:8].upper()}"
    db_cert = models.Certificate(
        enrollment_id=enrollment_id,
        certificate_code=cert_code,
        certificate_type=enrollment.course.certificate_type or "Participaci??n",
        issued_at=dt.datetime.utcnow()
    )
    db.add(db_cert)
    
    enrollment.certificate_issued = True
    db.commit()
    db.refresh(db_cert)
    return db_cert


def get_certificate_by_code(db: Session, code: str) -> Optional[models.Certificate]:
    return db.query(models.Certificate).filter(models.Certificate.certificate_code == code).first()


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
        action_data=metadata,
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


def check_access(
    db: Session,
    user: models.User,
    resource_type: str,
    action: str,
    resource_id: Optional[str] = None
) -> bool:
    """Checks if a user has access to a specific resource and action."""
    # Admins have access to everything
    if user.role == "admin":
        return True

    # Check direct user policy
    direct_policy = db.query(models.AccessPolicy).filter(
        models.AccessPolicy.user_id == user.id,
        models.AccessPolicy.resource_type == resource_type,
        models.AccessPolicy.action == action
    ).filter(
        or_(models.AccessPolicy.resource_id == resource_id, models.AccessPolicy.resource_id == None)
    ).first()

    if direct_policy:
        return direct_policy.is_allowed

    # Check role-based policy (simplified for now as user has one role string)
    # In a full RBAC, we'd check all roles assigned to the user
    role_obj = db.query(models.Role).filter(models.Role.name == user.role).first()
    if role_obj:
        role_policy = db.query(models.AccessPolicy).filter(
            models.AccessPolicy.role_id == role_obj.id,
            models.AccessPolicy.resource_type == resource_type,
            models.AccessPolicy.action == action
        ).filter(
            or_(models.AccessPolicy.resource_id == resource_id, models.AccessPolicy.resource_id == None)
        ).first()
        
        if role_policy:
            return role_policy.is_allowed

    return False
def create_project(db: Session, project: schemas.ProjectCreate) -> models.Project:
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def get_projects(db: Session, skip: int = 0, limit: int = 100) -> List[models.Project]:
    return db.query(models.Project).offset(skip).limit(limit).all()


def get_project(db: Session, project_id: int) -> Optional[models.Project]:
    return db.query(models.Project).filter(models.Project.id == project_id).first()


def delete_project(db: Session, project_id: int) -> bool:
    db_project = get_project(db, project_id)
    if not db_project:
        return False
    db.delete(db_project)
    db.commit()
    return True


def create_project_task(db: Session, task: schemas.ProjectTaskCreate) -> models.ProjectTask:
    db_task = models.ProjectTask(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_project_tasks(db: Session, project_id: int, root_only: bool = False) -> List[models.ProjectTask]:
    query = db.query(models.ProjectTask).filter(models.ProjectTask.project_id == project_id)
    if root_only:
        query = query.filter(models.ProjectTask.parent_id == None)
    return query.order_by(models.ProjectTask.order_index.asc()).all()


def update_project_task(
    db: Session, task_id: int, task_update: dict
) -> Optional[models.ProjectTask]:
    db_task = db.query(models.ProjectTask).filter(models.ProjectTask.id == task_id).first()
    if not db_task:
        return None
    for key, value in task_update.items():
        if hasattr(db_task, key):
            setattr(db_task, key, value)
    db.commit()
    db.refresh(db_task)
    return db_task


def delete_project_task(db: Session, task_id: int) -> bool:
    db_task = db.query(models.ProjectTask).filter(models.ProjectTask.id == task_id).first()
    if not db_task:
        return False
    db.delete(db_task)
    db.commit()
    return True


# -----------------
# Community Hub
# -----------------
def get_community_cards(db: Session, column_id: Optional[str] = None) -> List[models.CommunityBoardCard]:
    query = db.query(models.CommunityBoardCard).order_by(models.CommunityBoardCard.created_at.asc())
    if column_id:
        query = query.filter(models.CommunityBoardCard.column_id == column_id)
    return query.all()


def create_community_card(
    db: Session, card: schemas.CommunityBoardCardCreate
) -> models.CommunityBoardCard:
    db_card = models.CommunityBoardCard(**card.model_dump())
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card


# -----------------
# Gamification Motor
# -----------------
def get_user_xp_and_level(db: Session, user_id: str):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        return None
    
    level = db.query(models.Level).filter(models.Level.id == user.current_level_id).first()
    badges = db.query(models.UserBadge).filter(models.UserBadge.user_id == user_id).all()
    
    return {
        "xp": user.xp,
        "level": level.title if level else "Aspirante",
        "badges_count": len(badges)
    }


def grant_xp(db: Session, user_id: str, amount: int) -> models.User:
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        return None
    
    user.xp += amount
    
    # Automated Level-up Check
    next_level = (
        db.query(models.Level)
        .filter(models.Level.min_xp <= user.xp)
        .order_by(models.Level.min_xp.desc())
        .first()
    )
    
    if next_level and user.current_level_id != next_level.id:
        user.current_level_id = next_level.id
        
    db.commit()
    db.refresh(user)
    return user


def award_badge(db: Session, user_id: str, badge_name: str) -> Optional[models.UserBadge]:
    badge = db.query(models.Badge).filter(models.Badge.name == badge_name).first()
    if not badge:
        return None
        
    existing = (
        db.query(models.UserBadge)
        .filter(models.UserBadge.user_id == user_id, models.UserBadge.badge_id == badge.id)
        .first()
    )
    if existing:
        return existing
        
    user_badge = models.UserBadge(user_id=user_id, badge_id=badge.id)
    db.add(user_badge)
    grant_xp(db, user_id, badge.xp_reward)
    
    db.commit()
    db.refresh(user_badge)
    return user_badge


def complete_lesson(db: Session, enrollment_id: int, lesson_id: int):
    enrollment = db.query(models.Enrollment).filter(models.Enrollment.id == enrollment_id).first()
    if not enrollment:
        return None
        
    completed = list(enrollment.lessons_completed or [])
    if lesson_id not in completed:
        completed.append(lesson_id)
        enrollment.lessons_completed = completed
        
        total_lessons = db.query(func.count(models.Lesson.id)).filter(models.Lesson.course_id == enrollment.course_id).scalar() or 1
        enrollment.progress_percent = (len(completed) / total_lessons) * 100
        
        course = db.query(models.Course).filter(models.Course.id == enrollment.course_id).first()
        xp_gain = getattr(course, "xp_per_lesson", 10)
        grant_xp(db, enrollment.user_id, xp_gain)
        
        db.commit()
        db.refresh(enrollment)
        
    return enrollment


# -----------------
# UI Preferences
# -----------------
def get_ui_preferences(db: Session, user_id: str) -> Optional[models.UserUIPreference]:
    return db.query(models.UserUIPreference).filter(models.UserUIPreference.user_id == user_id).first()


def update_ui_preferences(db: Session, user_id: str, settings: dict) -> models.UserUIPreference:
    db_prefs = get_ui_preferences(db, user_id)
    if not db_prefs:
        db_prefs = models.UserUIPreference(user_id=user_id, settings=settings)
        db.add(db_prefs)
    else:
        current_settings = dict(db_prefs.settings or {})
        current_settings.update(settings)
        db_prefs.settings = current_settings
        
    db.commit()
    db.refresh(db_prefs)
    return db_prefs
