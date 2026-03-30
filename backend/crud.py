from __future__ import annotations

import datetime as dt
import json
import uuid
from types import SimpleNamespace
from typing import Optional, List

from sqlalchemy import or_, func, text
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.content_defaults import PAGE_CONTENT_DEFAULTS
from backend.core.security import get_password_hash, encrypt_data, decrypt_data


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=get_password_hash(user.password),
        role=user.role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, payload: schemas.UserUpdate):
    row = db.query(models.User).filter(models.User.id == user_id).first()
    if not row:
        return None
    
    update_data = payload.model_dump(exclude_unset=True)
    if "password" in update_data:
        from backend.core.security import get_password_hash
        update_data["password_hash"] = get_password_hash(update_data.pop("password"))
        
    for key, value in update_data.items():
        setattr(row, key, value)
        
    db.commit()
    db.refresh(row)
    return row


def delete_user(db: Session, user_id: int):
    row = db.query(models.User).filter(models.User.id == user_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def create_refresh_token(db: Session, user_id: int, token: str, expires_at: dt.datetime):
    row = models.RefreshToken(user_id=user_id, token=token, expires_at=expires_at, revoked=False)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_valid_refresh_token(db: Session, token: str):
    row = db.query(models.RefreshToken).filter(models.RefreshToken.token == token).first()
    if not row:
        return None
    if row.revoked:
        return None
    if row.expires_at <= _utcnow():
        return None
    return row


def revoke_refresh_token(db: Session, token: str):
    row = db.query(models.RefreshToken).filter(models.RefreshToken.token == token).first()
    if not row:
        return None
    row.revoked = True
    db.commit()
    db.refresh(row)
    return row


def grant_xp(db: Session, user_id: int, amount: int) -> Optional[models.User]:
    user = get_user(db, user_id)
    if not user:
        return None
    user.xp = (user.xp or 0) + amount
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


def update_ui_preferences(db: Session, user_id: int, settings: dict):
    prefs = db.query(models.UserUIPreference).filter(models.UserUIPreference.user_id == user_id).first()
    if not prefs:
        prefs = models.UserUIPreference(user_id=user_id, settings=settings)
        db.add(prefs)
    else:
        prefs.settings = settings
    db.commit()
    db.refresh(prefs)
    return prefs


def get_ui_preferences(db: Session, user_id: int):
    prefs = db.query(models.UserUIPreference).filter(models.UserUIPreference.user_id == user_id).first()
    if not prefs:
        prefs = models.UserUIPreference(user_id=user_id, settings={})
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


def award_badge(db: Session, user_id: int, badge_name: str):
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
    row = models.UserBadge(user_id=user_id, badge_id=badge.id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


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
    """Buscador unificado de miembros con filtros de negocio."""
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
    
    # Enriquecimiento con métricas de "Calidad" (Tres Factores: Datos/Inteligencia)
    for m in members:
        # 1. Mock de Salud Espiritual (basado en interacciones recientes)
        # En producción esto sería un score real de la IA
        m.spiritual_health = 0.5 + (abs(hash(m.first_name)) % 50) / 100.0
        
        # 2. Academy Progress Real
        if m.user_id:
            enrollments = db.query(models.Enrollment).filter(models.Enrollment.user_id == m.user_id).all()
            if enrollments:
                m.academy_progress = sum(e.progress_percent for e in enrollments) / len(enrollments)
            else:
                m.academy_progress = 0.0
        else:
            m.academy_progress = 0.0
            
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


def get_courses(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    modality: str | None = None,
    published_only: bool = True,
):
    query = db.query(models.Course)
    if modality:
        query = query.filter(models.Course.modality == modality)
    if published_only:
        query = query.filter(models.Course.is_published.is_(True))

    courses = query.offset(skip).limit(limit).all()

    # Enrich with counts
    for course in courses:
        stats = db.query(
            func.count(models.Lesson.id),
            func.sum(models.Lesson.duration_minutes)
        ).filter(models.Lesson.course_id == course.id).first()

        course.lesson_count = stats[0] or 0
        course.total_minutes = stats[1] or 0

    return courses


def get_course(db: Session, course_id: int):
    return db.query(models.Course).filter(models.Course.id == course_id).first()


def check_user_meets_prerequisites(db: Session, user_id: int, course_id: int) -> bool:
    """
    Verifica si el usuario ha completado satisfactoriamente todos los cursos previos.
    """
    prereqs = db.query(models.CoursePrerequisite).filter(models.CoursePrerequisite.course_id == course_id).all()
    if not prereqs:
        return True

    for prereq in prereqs:
        completed = (
            db.query(models.Enrollment)
            .filter(
                models.Enrollment.user_id == user_id,
                models.Enrollment.course_id == prereq.prerequisite_course_id,
                models.Enrollment.status == "completed"
            )
            .first()
        )
        if not completed:
            return False

    return True


def get_enrollment(db: Session, enrollment_id: int):
    return db.query(models.Enrollment).filter(models.Enrollment.id == enrollment_id).first()


def get_enrollments_by_user(db: Session, user_id: int):
    return db.query(models.Enrollment).filter(models.Enrollment.user_id == user_id).all()


def get_assessment(db: Session, assessment_id: int):
    return db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()


def get_assessment_with_questions(db: Session, assessment_id: int):
    return (
        db.query(models.Assessment)
        .filter(models.Assessment.id == assessment_id)
        .first()
    )


def get_lesson_progress(db: Session, user_id: int, lesson_id: int):
    return (
        db.query(models.LessonProgress)
        .filter(models.LessonProgress.user_id == user_id, models.LessonProgress.lesson_id == lesson_id)
        .first()
    )


def update_lesson_progress(
    db: Session, user_id: int, lesson_id: int, progress_percent: float, last_position: int
):
    row = (
        db.query(models.LessonProgress)
        .filter(models.LessonProgress.user_id == user_id, models.LessonProgress.lesson_id == lesson_id)
        .first()
    )
    if not row:
        row = models.LessonProgress(user_id=user_id, lesson_id=lesson_id)
        db.add(row)

    row.progress_percent = progress_percent
    row.last_position_seconds = last_position
    if progress_percent >= 100:
        row.is_completed = True

    db.commit()
    db.refresh(row)

    # RN-NF-002: Update Enrollment total progress
    lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
    if lesson:
        enrollment = db.query(models.Enrollment).filter(
            models.Enrollment.user_id == user_id,
            models.Enrollment.course_id == lesson.course_id
        ).first()
        if enrollment:
            total_lessons = db.query(models.Lesson).filter(models.Lesson.course_id == lesson.course_id).count()
            completed_count = db.query(models.LessonProgress).join(models.Lesson).filter(
                models.Lesson.course_id == lesson.course_id,
                models.LessonProgress.user_id == user_id,
                models.LessonProgress.is_completed
            ).count()

            if total_lessons > 0:
                enrollment.progress_percent = (completed_count / total_lessons) * 100
                if enrollment.progress_percent >= 100:
                    course = db.query(models.Course).filter(models.Course.id == lesson.course_id).first()
                    if course and course.modality == "no_formal":
                        enrollment.status = "completed"
                db.commit()
    return row

def create_enrollment(db: Session, enrollment: schemas.EnrollmentCreate) -> models.Enrollment:
    """
    Crea una nueva inscripción validando prerrequisitos académicos.
    """
    # 1. Check if already enrolled
    existing = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.user_id == enrollment.user_id, models.Enrollment.course_id == enrollment.course_id)
        .first()
    )
    if existing:
        raise ValueError("El estudiante ya se encuentra inscrito en este curso")

    # 2. Check prerequisites (MVP-004)
    if not check_user_meets_prerequisites(db, enrollment.user_id, enrollment.course_id):
        raise ValueError("No se cumplen los prerrequisitos académicos para acceder a este nivel")

    # 3. Create enrollment
    db_course = db.query(models.Course).filter(models.Course.id == enrollment.course_id).first()
    access_end = None
    if db_course and db_course.modality == "no_formal":
        # RN-NF-004: Window of 1 year for no_formal
        access_end = _utcnow() + dt.timedelta(days=365)

    try:
        row = models.Enrollment(
            user_id=enrollment.user_id,
            course_id=enrollment.course_id,
            access_window_end=access_end
        )
        db.add(row)

        # LOG ACTIVITY
        log = models.AcademyActivityLog(
            event_type="enrollment",
            course_id=enrollment.course_id,
            user_id=enrollment.user_id,
            modality=db_course.modality if db_course else None
        )
        db.add(log)

        db.commit()
        db.refresh(row)
        return row
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al procesar la inscripción: {str(e)}")


def create_or_update_assessment_attempt(
    db: Session, enrollment: models.Enrollment, assessment: models.Assessment, submitted_score: float
):
    attempt = (
        db.query(models.AssessmentAttempt)
        .filter(
            models.AssessmentAttempt.enrollment_id == enrollment.id,
            models.AssessmentAttempt.assessment_id == assessment.id
        )
        .first()
    )
    if not attempt:
        attempt = models.AssessmentAttempt(
            enrollment_id=enrollment.id,
            assessment_id=assessment.id
        )
        db.add(attempt)

    attempt.score = submitted_score
    attempt.passed = submitted_score >= float(assessment.min_score or 70)

    # If passed, check if all course requirements met
    if attempt.passed:
        # Check if enrollment should be marked approved
        # For simplicity, we assume if one key assessment is passed, enrollment is approved
        # This could be more complex (e.g. average grade)
        enrollment.approved = True
        
        # RN-CERT-001: Auto-issue certificate upon approval
        issue_certificate_for_enrollment(db, enrollment)

    db.commit()
    db.refresh(attempt)
    return attempt


def submit_assessment_attempt(
    db: Session, assessment_id: int, enrollment_id: int, answers: list[dict]
):
    assessment = get_assessment(db, assessment_id)
    enrollment = get_enrollment(db, enrollment_id)
    if not assessment or not enrollment:
        raise ValueError("Assessment or Enrollment not found")

    total_score = 0
    max_score = sum(q.points for q in assessment.questions) if assessment.questions else 100

    # Simple grading logic
    for answer in answers:
        question_id = answer.get("question_id")
        selected_option_id = answer.get("selected_option_id")

        question = db.query(models.AssessmentQuestion).filter(models.AssessmentQuestion.id == question_id).first()
        if question:
            correct_option = (
                db.query(models.AssessmentOption)
                .filter(models.AssessmentOption.question_id == question_id, models.AssessmentOption.is_correct)
                .first()
            )
            if correct_option and correct_option.id == selected_option_id:
                total_score += question.points

    percentage = (total_score / max_score * 100) if max_score > 0 else 0
    return create_or_update_assessment_attempt(db, enrollment, assessment, percentage)


def get_certificates_by_user(db: Session, user_id: int):
    return (
        db.query(models.Certificate)
        .join(models.Enrollment)
        .filter(models.Enrollment.user_id == user_id)
        .all()
    )


def get_certificate_by_code(db: Session, code: str):
    return db.query(models.Certificate).filter(models.Certificate.certificate_code == code).first()


def issue_certificate_for_enrollment(db: Session, enrollment: models.Enrollment):
    if enrollment.certificate_issued:
        return db.query(models.Certificate).filter(models.Certificate.enrollment_id == enrollment.id).first()

    code = f"CCF-{uuid.uuid4().hex[:8].upper()}"
    enrollment.certificate_issued = True
    enrollment.certificate_code = code
    cert = models.Certificate(enrollment_id=enrollment.id, certificate_code=code)
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return cert


def issue_certificate(db: Session, enrollment_id: int):
    enrollment = get_enrollment(db, enrollment_id)
    if not enrollment:
        raise ValueError("Enrollment not found")
    if not enrollment.approved:
        raise ValueError("Enrollment not approved")
    return issue_certificate_for_enrollment(db, enrollment)


def record_activity_attendance(db: Session, enrollment_id: int):
    # For now, just mark the enrollment as "progressed" or similar
    # In a real system we'd have an attendance table
    return {"status": "success", "enrollment_id": enrollment_id, "timestamp": _utcnow()}

def issue_pending_certificates(db: Session):
    rows = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.status == "completed",
            models.Enrollment.approved.is_(True),
            models.Enrollment.certificate_issued.is_(False),
        )
        .all()
    )
    issued = []
    for enrollment in rows:
        code = f"CCF-{uuid.uuid4().hex[:8].upper()}"
        enrollment.certificate_issued = True
        enrollment.certificate_code = code
        cert = models.Certificate(enrollment_id=enrollment.id, certificate_code=code)
        db.add(cert)
        issued.append(cert)
    db.commit()
    for cert in issued:
        db.refresh(cert)
    return issued


def close_formal_acta(
    db: Session, course_id: int, closed_by_user_id: int, min_grade: float, min_attendance: float
):
    acta = models.FormalActa(
        course_id=course_id,
        closed_by_user_id=closed_by_user_id,
        min_grade_required=min_grade,
        min_attendance_required=min_attendance
    )
    db.add(acta)

    # RN-FOR-004: Logic to approve students based on grade AND attendance
    enrollments = db.query(models.Enrollment).filter(models.Enrollment.course_id == course_id).all()
    for e in enrollments:
        # 1. Check average grade from assessments
        avg_score = db.query(func.avg(models.AssessmentAttempt.score)).filter(
            models.AssessmentAttempt.enrollment_id == e.id
        ).scalar() or 0

        # 2. Check attendance percentage
        # Assume each course has a fixed number of sessions (e.g. 10) or we count total recorded
        total_sessions = db.query(func.count(func.distinct(models.CourseAttendance.session_date))).join(models.Enrollment).filter(
            models.Enrollment.course_id == course_id
        ).scalar() or 1

        present_count = db.query(models.CourseAttendance).filter(
            models.CourseAttendance.enrollment_id == e.id,
            models.CourseAttendance.status.in_(["present", "justified"])
        ).count()

        attendance_rate = (present_count / total_sessions * 100)

        if avg_score >= min_grade and attendance_rate >= min_attendance:
            e.approved = True
            e.status = "completed"

            # Log achievement
            log = models.AcademyActivityLog(
                event_type="completion",
                course_id=course_id,
                user_id=e.user_id,
                modality="formal",
                value=float(avg_score)
            )
            db.add(log)

    db.commit()
    db.refresh(acta)
    return acta


def get_latest_acta_by_course(db: Session, course_id: int):
    return (
        db.query(models.FormalActa)
        .filter(models.FormalActa.course_id == course_id)
        .order_by(models.FormalActa.created_at.desc())
        .first()
    )


def create_assignment_submission(
    db: Session, enrollment_id: int, lesson_id: int, file_url: str, comment: str | None = None
):
    submission = models.AssignmentSubmission(
        enrollment_id=enrollment_id,
        lesson_id=lesson_id,
        file_url=file_url,
        comment=comment
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


def list_assignment_submissions_with_meta(db: Session, limit: int = 100):
    return (
        db.query(
            models.AssignmentSubmission,
            models.Lesson.title.label("lesson_title"),
            models.User.username.label("student_name")
        )
        .join(models.Lesson, models.AssignmentSubmission.lesson_id == models.Lesson.id)
        .join(models.Enrollment, models.AssignmentSubmission.enrollment_id == models.Enrollment.id)
        .join(models.User, models.Enrollment.user_id == models.User.id)
        .limit(limit)
        .all()
    )


def get_assignment_submission_with_meta(db: Session, submission_id: int):
    return (
        db.query(
            models.AssignmentSubmission,
            models.Lesson.title.label("lesson_title"),
            models.User.username.label("student_name")
        )
        .filter(models.AssignmentSubmission.id == submission_id)
        .join(models.Lesson, models.AssignmentSubmission.lesson_id == models.Lesson.id)
        .join(models.Enrollment, models.AssignmentSubmission.enrollment_id == models.Enrollment.id)
        .join(models.User, models.Enrollment.user_id == models.User.id)
        .first()
    )


def grade_assignment_submission(
    db: Session, submission_id: int, grade: float | None = None, feedback: str | None = None
):
    submission = db.query(models.AssignmentSubmission).filter(models.AssignmentSubmission.id == submission_id).first()
    if not submission:
        return None
    if grade is not None:
        submission.grade = grade
    if feedback is not None:
        submission.teacher_feedback = feedback
    db.commit()
    db.refresh(submission)
    return submission


def get_academy_candidates(db: Session):
    # Members who are not yet enrolled in any course
    enrolled_user_ids = db.query(models.Enrollment.user_id).distinct()
    return db.query(models.User).filter(models.User.id.notin_(enrolled_user_ids)).all()


def get_forum_threads(db: Session):
    return db.query(models.ForumThread).order_by(models.ForumThread.created_at.desc()).all()


def create_forum_thread(db: Session, thread_data: schemas.ForumThreadCreate):
    row = models.ForumThread(**thread_data.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

def get_pastor_radar(db: Session):
    return {
        "membresia_viva": db.query(models.Member).count(),
        "bautismos_este_anio": 0,
        "estudiantes_activos": db.query(models.Enrollment).filter(models.Enrollment.status == "active").count(),
        "recaudacion_mes": 0.0
    }


def get_dashboard_metrics(db: Session):
    active_students = db.query(models.Enrollment).filter(models.Enrollment.status == "active").count()
    total_enrollments = db.query(models.Enrollment).count()
    completed_enrollments = db.query(models.Enrollment).filter(models.Enrollment.status == "completed").count()

    completion_rate = (completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0
    certificates_issued = db.query(models.Enrollment).filter(models.Enrollment.certificate_issued).count()

    # 1. Stats for Formal
    formal_total = db.query(models.Enrollment).join(models.Course).filter(models.Course.modality == "formal").count()
    formal_comp = db.query(models.Enrollment).join(models.Course).filter(
        models.Course.modality == "formal", models.Enrollment.status == "completed"
    ).count()
    formal_avg = db.query(func.avg(models.AssessmentAttempt.score)).join(models.Enrollment).join(models.Course).filter(
        models.Course.modality == "formal"
    ).scalar() or 0

    # 2. Stats for No Formal
    nf_total = db.query(models.Enrollment).join(models.Course).filter(models.Course.modality == "no_formal").count()
    nf_comp = db.query(models.Enrollment).join(models.Course).filter(
        models.Course.modality == "no_formal", models.Enrollment.status == "completed"
    ).count()
    nf_avg = db.query(func.avg(models.AssessmentAttempt.score)).join(models.Enrollment).join(models.Course).filter(
        models.Course.modality == "no_formal"
    ).scalar() or 0

    # 3. Top Courses
    top_courses_rows = db.query(
        models.Course.title,
        func.count(models.Enrollment.id).label("enroll_count")
    ).join(models.Enrollment).group_by(models.Course.id).order_by(text("enroll_count DESC")).limit(5).all()

    top_courses = [{"title": r[0], "count": r[1]} for r in top_courses_rows]

    return {
        "active_students": active_students,
        "completion_rate": round(completion_rate, 2),
        "certificates_issued": certificates_issued,
        "formal_stats": {
            "total": formal_total,
            "completed": formal_comp,
            "rate": round((formal_comp / formal_total * 100) if formal_total > 0 else 0, 2),
            "avg_grade": round(float(formal_avg), 1)
        },
        "no_formal_stats": {
            "total": nf_total,
            "completed": nf_comp,
            "rate": round((nf_comp / nf_total * 100) if nf_total > 0 else 0, 2),
            "avg_grade": round(float(nf_avg), 1)
        },
        "top_courses": top_courses
    }


def get_pilot_readiness(db: Session):
    checklist = [
        {"key": "db", "status": "ok"},
        {"key": "courses", "status": "ok" if db.query(models.Course).count() >= 0 else "warning"},
        {"key": "users", "status": "ok" if db.query(models.User).count() >= 0 else "warning"},
    ]
    return schemas.PilotReadiness(environment_ready=True, checklist=checklist)


def create_agent_task(db: Session, payload: schemas.AgentTaskCreate):
    row = models.AgentTask(
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        source=payload.source,
        status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_agent_tasks(db: Session, status: str | None = None):
    query = db.query(models.AgentTask)
    if status:
        query = query.filter(models.AgentTask.status == status)
    return query.order_by(models.AgentTask.created_at.desc()).all()


def update_agent_task(db: Session, task_id: int, payload: schemas.AgentTaskUpdate):
    row = db.query(models.AgentTask).filter(models.AgentTask.id == task_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def create_agent_insight(db: Session, payload: schemas.AgentInsightCreate):
    row = models.AgentInsight(
        title=payload.title,
        insight_type=payload.insight_type,
        payload=payload.payload,
        acknowledged=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_agent_insights(db: Session, acknowledged: bool | None = None):
    query = db.query(models.AgentInsight)
    if acknowledged is not None:
        query = query.filter(models.AgentInsight.acknowledged == acknowledged)
    return query.order_by(models.AgentInsight.created_at.desc()).all()


def acknowledge_insight(db: Session, insight_id: int):
    row = db.query(models.AgentInsight).filter(models.AgentInsight.id == insight_id).first()
    if not row:
        return None
    row.acknowledged = True
    db.commit()
    db.refresh(row)
    return row


def create_admin_audit_log(
    db: Session,
    actor_user_id: int | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
):
    row = models.AdminAuditLog(
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json={**(metadata or {}), **({"ip_address": ip_address} if ip_address else {})},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_admin_audit_logs(
    db: Session,
    limit: int = 100,
    actor_user_id: int | None = None,
    resource_type: str | None = None,
):
    query = db.query(models.AdminAuditLog)
    if actor_user_id is not None:
        query = query.filter(models.AdminAuditLog.actor_user_id == actor_user_id)
    if resource_type is not None:
        query = query.filter(models.AdminAuditLog.resource_type == resource_type)
    rows = query.order_by(models.AdminAuditLog.created_at.desc()).limit(limit).all()
    for row in rows:
        row.metadata = row.metadata_json or {}
    return rows


def update_page_content(db: Session, page_key: str, payload: schemas.PageContentUpdate):
    page = db.query(models.PageContent).filter(models.PageContent.page_key == page_key).first()
    if not page:
        page = models.PageContent(page_key=page_key, title=payload.title or "", content=payload.content or "")
        db.add(page)
        db.commit()
        db.refresh(page)
        return page
    version = models.PageContentVersion(page_key=page.page_key, title=page.title, content=page.content)
    db.add(version)
    if payload.title is not None:
        page.title = payload.title
    if payload.content is not None:
        page.content = payload.content
    db.commit()
    db.refresh(page)
    return page


def get_page_content(db: Session, page_key: str):
    return db.query(models.PageContent).filter(models.PageContent.page_key == page_key).first()


def list_page_contents(db: Session, limit: int = 200):
    return (
        db.query(models.PageContent)
        .order_by(models.PageContent.updated_at.desc())
        .limit(limit)
        .all()
    )


def get_or_create_page_content(db: Session, page_key: str):
    row = get_page_content(db, page_key)
    if row:
        return row

    defaults = PAGE_CONTENT_DEFAULTS.get(page_key, {})
    title = str(defaults.get("title") or page_key.replace("_", " ").title())
    default_content = defaults.get("content", {})

    if isinstance(default_content, str):
        content_payload = default_content
    else:
        content_payload = json.dumps(default_content, ensure_ascii=False)

    row = models.PageContent(page_key=page_key, title=title, content=content_payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_page_content_versions(db: Session, page_key: str):
    return (
        db.query(models.PageContentVersion)
        .filter(models.PageContentVersion.page_key == page_key)
        .order_by(models.PageContentVersion.created_at.desc())
        .all()
    )


def restore_page_content_version(db: Session, page_key: str, version_id: int):
    version = (
        db.query(models.PageContentVersion)
        .filter(
            models.PageContentVersion.id == version_id,
            models.PageContentVersion.page_key == page_key,
        )
        .first()
    )
    if not version:
        return None

    row = get_or_create_page_content(db, page_key)
    snapshot = models.PageContentVersion(page_key=row.page_key, title=row.title, content=row.content)
    db.add(snapshot)
    row.title = version.title
    row.content = version.content
    db.commit()
    db.refresh(row)
    return row


def get_or_create_content_publication(db: Session, page_key: str):
    row = (
        db.query(models.ContentPublication)
        .filter(models.ContentPublication.page_key == page_key)
        .first()
    )
    if row:
        return row
    row = models.ContentPublication(page_key=page_key, status="draft")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_content_publication(
    db: Session,
    page_key: str,
    *,
    status: str | None = None,
    publish_at: dt.datetime | None | object = ...,
    expire_at: dt.datetime | None | object = ...,
    notes: str | None = None,
    updated_by: int | None = None,
):
    row = get_or_create_content_publication(db, page_key)
    if status is not None:
        row.status = status
    if publish_at is not ...:
        row.publish_at = publish_at
    if expire_at is not ...:
        row.expire_at = expire_at
    if notes is not None:
        row.notes = notes
    if updated_by is not None:
        row.updated_by = updated_by
    if status == "published":
        row.last_published_at = _utcnow()
    db.commit()
    db.refresh(row)
    return row


def list_content_publications(db: Session):
    return db.query(models.ContentPublication).all()


def create_cms_media_item(
    db: Session,
    *,
    url: str,
    alt_text: str | None,
    section: str,
    tags: list[str] | None,
    created_by: int | None,
):
    row = models.CmsMediaItem(
        url=url,
        alt_text=alt_text,
        section=section,
        tags=tags or [],
        created_by=created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_cms_media_items(db: Session, *, query: str | None = None, section: str | None = None, limit: int = 250):
    q = db.query(models.CmsMediaItem)
    if section:
        q = q.filter(models.CmsMediaItem.section == section)
    if query:
        like = f"%{query.strip()}%"
        q = q.filter(
            or_(
                models.CmsMediaItem.url.ilike(like),
                models.CmsMediaItem.alt_text.ilike(like),
            )
        )
    return q.order_by(models.CmsMediaItem.updated_at.desc()).limit(limit).all()


def get_cms_media_item(db: Session, item_id: int):
    return db.query(models.CmsMediaItem).filter(models.CmsMediaItem.id == item_id).first()


def update_cms_media_item(
    db: Session,
    item_id: int,
    *,
    url: str | None = None,
    alt_text: str | None = None,
    section: str | None = None,
    tags: list[str] | None = None,
):
    row = get_cms_media_item(db, item_id)
    if not row:
        return None
    if url is not None:
        row.url = url
    if alt_text is not None:
        row.alt_text = alt_text
    if section is not None:
        row.section = section
    if tags is not None:
        row.tags = tags
    db.commit()
    db.refresh(row)
    return row


def delete_cms_media_item(db: Session, item_id: int):
    row = get_cms_media_item(db, item_id)
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def increment_content_metric(db: Session, metric_key: str, ref_id: int, amount: int = 1):
    row = (
        db.query(models.ContentMetric)
        .filter(models.ContentMetric.metric_key == metric_key, models.ContentMetric.ref_id == ref_id)
        .first()
    )
    if not row:
        row = models.ContentMetric(metric_key=metric_key, ref_id=ref_id, value=0)
        db.add(row)
    row.value = int(row.value or 0) + int(amount)
    db.commit()
    db.refresh(row)
    return row


def create_media_asset(db: Session, filename: str, url: str, mime_type: str | None, size_bytes: int):
    row = models.MediaAsset(filename=filename, url=url, mime_type=mime_type, size_bytes=size_bytes)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_user_notifications(db: Session, user_id: int, limit: int = 20):
    return (
        db.query(models.Notification)
        .filter(models.Notification.user_id == user_id)
        .order_by(models.Notification.created_at.desc())
        .limit(limit)
        .all()
    )


def mark_notification_as_read(db: Session, notification_id: int):
    row = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not row:
        return None
    row.is_read = True
    db.commit()
    db.refresh(row)
    return row


def mark_all_notifications_read(db: Session, user_id: int):
    rows = db.query(models.Notification).filter(models.Notification.user_id == user_id).all()
    for row in rows:
        row.is_read = True
    db.commit()
    return len(rows)


def create_communication_log(db: Session, payload: schemas.CommunicationLogCreate):
    row = models.CommunicationLog(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_communication_logs(db: Session, limit: int = 50):
    return db.query(models.CommunicationLog).order_by(models.CommunicationLog.created_at.desc()).limit(limit).all()


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

def get_member_timeline(db: Session, member_id: int):
    """Agrega hitos de múltiples fuentes para construir la hoja de vida espiritual y académica."""
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        return []

    timeline = []

    # 1. Hito de Membresía
    timeline.append({
        "type": "membership",
        "title": "Ingreso a la Familia CCF",
        "description": f"Registro formal como {member.church_role}.",
        "date": member.created_at.isoformat(),
        "icon": "Sparkles",
        "color": "bg-purple-500"
    })

    # 2. Hitos de Academia (Usando user_id si existe)
    if member.user_id:
        enrollments = db.query(models.Enrollment).filter(models.Enrollment.user_id == member.user_id).all()
        for en in enrollments:
            # Hito de Inscripción
            timeline.append({
                "type": "academy",
                "title": "Inscripción Academia",
                "description": f"Inició el curso {en.course.name if en.course else 'de formación'}.",
                "date": en.created_at.isoformat(),
                "icon": "GraduationCap",
                "color": "bg-emerald-500"
            })
            # Hito de Certificado si existe
            if en.certificate_issued:
                timeline.append({
                    "type": "certificate",
                    "title": "Certificación Obtenida",
                    "description": f"Completó con éxito el curso: {en.course.name if en.course else 'de formación'}.",
                    "date": (en.created_at + dt.timedelta(days=30)).isoformat(), # Mock date for cert
                    "icon": "Award",
                    "color": "bg-amber-500"
                })

    # 3. Hitos de Ministerios
    for ministry in member.ministries:
        timeline.append({
            "type": "ministry",
            "title": "Vinculación Ministerial",
            "description": f"Se integró al ministerio de {ministry.name}.",
            "date": ministry.created_at.isoformat() if ministry.created_at else member.created_at.isoformat(),
            "icon": "ShieldCheck",
            "color": "bg-indigo-600"
        })

    # 4. Hitos de Consejería
    sessions = db.query(models.CounselingTicket).filter(models.CounselingTicket.member_id == member_id).all()
    for s in sessions:
        timeline.append({
            "type": "counseling",
            "title": "Sesión Pastoral",
            "description": f"Atención espiritual: {s.topic}.",
            "date": s.created_at.isoformat(),
            "icon": "Heart",
            "color": "bg-rose-500"
        })

    # 5. Hitos de Comunicación (Llamadas)
    calls = db.query(models.CommunicationLog).filter(models.CommunicationLog.member_id == member_id).all()
    for c in calls:
        timeline.append({
            "type": "communication",
            "title": "Seguimiento Pastoral",
            "description": f"Contacto vía {c.channel}: {c.content[:50]}...",
            "date": c.sent_at.isoformat(),
            "icon": "Phone",
            "color": "bg-blue-500"
        })

    # Ordenar por fecha descendente
    timeline.sort(key=lambda x: x["date"], reverse=True)
    return timeline


# --- CRM EXTENDED CRUD ---

def get_crm_events(db: Session, skip: int = 0, limit: int = 100) -> List[models.CrmEvent]:
    """Obtiene el calendario de eventos del CRM ordenados por fecha."""
    return db.query(models.CrmEvent).order_by(models.CrmEvent.event_date.desc()).offset(skip).limit(limit).all()

def create_crm_event(db: Session, payload: schemas.CrmEventCreate) -> models.CrmEvent:
    """Registra un nuevo evento en el calendario ministerial."""
    try:
        row = models.CrmEvent(**payload.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al crear evento: {str(e)}")

def get_crm_tasks(db: Session, assignee_id: Optional[int] = None, member_id: Optional[int] = None, lead_id: Optional[int] = None) -> List[models.CrmTask]:
    """Obtiene tareas pastorales con filtros opcionales."""
    query = db.query(models.CrmTask)
    if assignee_id:
        query = query.filter(models.CrmTask.assignee_id == assignee_id)
    if member_id:
        query = query.filter(models.CrmTask.member_id == member_id)
    if lead_id:
        query = query.filter(models.CrmTask.lead_id == lead_id)
    return query.order_by(models.CrmTask.due_date.asc()).all()

def create_crm_task(db: Session, payload: schemas.CrmTaskCreate) -> models.CrmTask:
    """Crea una nueva tarea de seguimiento pastoral."""
    row = models.CrmTask(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

def update_crm_task(db: Session, task_id: int, payload: schemas.CrmTaskUpdate) -> models.CrmTask:
    """Actualiza una tarea del CRM (estado, prioridad, etc)."""
    row = db.query(models.CrmTask).filter(models.CrmTask.id == task_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row

def get_volunteer_shifts(db: Session, member_id: Optional[int] = None) -> List[models.VolunteerShift]:
    """Obtiene el calendario de turnos de servicio."""
    query = db.query(models.VolunteerShift)
    if member_id:
        query = query.filter(models.VolunteerShift.member_id == member_id)
    return query.order_by(models.VolunteerShift.shift_start.asc()).all()

def create_volunteer_shift(db: Session, payload: schemas.VolunteerShiftCreate) -> models.VolunteerShift:
    """Registra un nuevo turno de voluntariado."""
    row = models.VolunteerShift(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

def get_assets(db: Session) -> List[models.AssetItem]:
    """Lista todos los activos de infraestructura."""
    return db.query(models.AssetItem).all()

def create_maintenance_log(db: Session, item_id: uuid.UUID, description: str, service_date: dt.date) -> models.MaintenanceLog:
    """Crea un registro de mantenimiento."""
    row = models.MaintenanceLog(
        item_id=item_id,
        description=description,
        service_date=dt.datetime.combine(service_date, dt.time.min)
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row




def create_event_attendance(db: Session, payload: schemas.EventAttendanceCreate) -> models.EventAttendance:
    """Registra la asistencia de un miembro a un evento."""
    try:
        row = models.EventAttendance(**payload.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al registrar asistencia: {str(e)}")

def get_counseling_tickets(
    db: Session,
    status: str | None = None,
    member_id: int | None = None,
    skip: int = 0,
    limit: int = 100
) -> List[models.CounselingTicket]:
    """Obtiene tickets de consejería con descifrado al vuelo."""
    query = db.query(models.CounselingTicket)
    if status:
        query = query.filter(models.CounselingTicket.status == status)
    if member_id:
        query = query.filter(models.CounselingTicket.member_id == member_id)
    tickets = query.order_by(models.CounselingTicket.created_at.desc()).offset(skip).limit(limit).all()

    # Descifrado para la API
    for t in tickets:
        if t.notes:
            t.notes = decrypt_data(t.notes)

    return tickets


def analyze_pastoral_priority(notes: str) -> str:
    """Motor de IA Optimus Brain v1: Heurística de Priorización Pastoral."""
    if not notes: return "NORMAL"

    notes_lower = notes.lower()

    # Indicadores Críticos (Urgente)
    critical_keywords = [
        "suicidio", "atentado", "abuso", "depresion profunda",
        "violencia", "riesgo", "emergencia", "auxilio", "ayuda ya"
    ]
    if any(k in notes_lower for k in critical_keywords):
        return "URGENTE"

    # Indicadores de Atención (Alta)
    high_keywords = [
        "conflicto familiar", "separacion", "crisis", "enfermedad grave",
        "perdida de fe", "soledad", "problemas economicos"
    ]
    if any(k in notes_lower for k in high_keywords):
        return "ALTA"

    return "NORMAL"

def analyze_pastoral_sentiment(content: str):
    """Motor de IA Optimus Brain v2: Análisis Heurístico de Sentimiento."""
    if not content: return 0.0, "NEUTRAL"

    text = content.lower()

    positive_words = ["aliento", "bendecido", "paz", "gozo", "agradecido", "crecimiento", "victoria", "fe", "esperanza"]
    negative_words = ["triste", "derrota", "angustia", "problema", "pelea", "dolor", "soledad", "duda", "miedo"]

    pos_count = sum(1 for w in positive_words if w in text)
    neg_count = sum(1 for w in negative_words if w in text)

    score = (pos_count - neg_count) / (max(pos_count + neg_count, 1))

    if score > 0.1: label = "POSITIVE"
    elif score < -0.1: label = "NEGATIVE"
    else: label = "NEUTRAL"

    return round(score, 2), label

def create_counseling_ticket(db: Session, payload: schemas.CounselingTicketCreate) -> models.CounselingTicket:
    """Abre un nuevo proceso de consejería pastoral con IA Optimus Brain v2 (Prioridad + Sentimiento)."""
    try:
        data = payload.model_dump()
        raw_notes = data.get("notes", "")

        # 1. IA Optimus Brain: Análisis de Prioridad y Sentimiento
        data["priority_level"] = analyze_pastoral_priority(raw_notes)
        score, label = analyze_pastoral_sentiment(raw_notes)
        data["sentiment_score"] = score
        data["sentiment_label"] = label

        # 2. Cifrado de notas
        if raw_notes:
            data["notes"] = encrypt_data(raw_notes)

        row = models.CounselingTicket(**data)
        db.add(row)
        db.commit()
        db.refresh(row)

        # Devolvemos descifrado
        row.notes = decrypt_data(row.notes)
        return row
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al crear ticket de consejería: {str(e)}")

def get_prayer_requests(db: Session, status: str | None = None, skip: int = 0, limit: int = 100) -> List[models.PrayerRequest]:
    """Obtiene las peticiones de oración del muro ministerial."""
    query = db.query(models.PrayerRequest)
    if status:
        query = query.filter(models.PrayerRequest.status == status)
    return query.order_by(models.PrayerRequest.created_at.desc()).offset(skip).limit(limit).all()

def create_prayer_request(db: Session, payload: schemas.PrayerRequestCreate) -> models.PrayerRequest:
    """Registra una nueva petición en el muro de oración."""
    try:
        row = models.PrayerRequest(**payload.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al registrar petición de oración: {str(e)}")

def get_glory_houses(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.GloryHouse).offset(skip).limit(limit).all()

def create_glory_house(db: Session, payload: schemas.GloryHouseCreate):
    """Registra una nueva Casa de Gloria con metadatos geográficos."""
    db_obj = models.GloryHouse(**payload.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def create_project(db: Session, project: schemas.ProjectCreate):
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def create_project_task(db: Session, task: schemas.ProjectTaskCreate):
    db_task = models.ProjectTask(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def search_knowledge_base(db: Session, query: str):
    if not query:
        return []
    # Simulación de búsqueda semántica ministerial v3.9
    mock_docs = [
        {
            "title": "Protocolo de Consolidación Ministerial",
            "content": "Lineamientos para la bienvenida de nuevos miembros y seguimiento pastoral en las primeras 48 horas tras su primera visita.",
            "category": "Operaciones",
            "relevance": 0.98
        },
        {
            "title": "Manual de Liderazgo: Casas de Gloria",
            "content": "Principios bíblicos para la gestión de grupos pequeños, resolución de conflictos y multiplicación celular en zonas urbanas.",
            "category": "Liderazgo",
            "relevance": 0.85
        },
        {
            "title": "Directiva de Seguridad Digital y Auditoría",
            "content": "Normativas para el manejo de datos sensibles de la congregación, protección de privacidad y registro exhaustivo de acciones administrativas.",
            "category": "Seguridad",
            "relevance": 0.72
        },
        {
            "title": "Reglamento Académico MESH",
            "content": "Estatutos para la formación teológica formal y no formal, criterios de evaluación y requisitos para la certificación ministerial.",
            "category": "Educación",
            "relevance": 0.65
        }
    ]
    # Filtrar por query (simulación de motor de búsqueda simple)
    results = [doc for doc in mock_docs if query.lower() in doc["title"].lower() or query.lower() in doc["content"].lower()]
    if not results:
        results = mock_docs[:3] # Devolver top 3 si no hay coincidencia directa
    
    return [SimpleNamespace(**doc) for doc in results]
