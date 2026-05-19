"""Courses, enrollments, assessments, certificates, forum, assignments, and formal acta CRUD."""
import datetime as dt
import json
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backend import models, schemas
from backend.content_defaults import PAGE_CONTENT_DEFAULTS
from backend.crud._utils import _utcnow


# ── Courses ────────────────────────────────────────────

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

    course_ids = [c.id for c in courses]
    stats_map = {}
    if course_ids:
        stats_data = db.query(
            models.Lesson.course_id,
            func.count(models.Lesson.id),
            func.sum(models.Lesson.duration_minutes)
        ).filter(models.Lesson.course_id.in_(course_ids)).group_by(models.Lesson.course_id).all()
        stats_map = {cid: (count, minutes) for cid, count, minutes in stats_data}

    for course in courses:
        c_stats = stats_map.get(course.id, (0, 0))
        course.lesson_count = c_stats[0]
        course.total_minutes = c_stats[1] or 0

    return courses


def get_course(db: Session, course_id: int):
    return db.query(models.Course).filter(models.Course.id == course_id).first()


def check_user_meets_prerequisites(db: Session, user_id: int, course_id: int) -> bool:
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


# ── Enrollments ────────────────────────────────────────

def get_enrollment(db: Session, enrollment_id: int):
    return db.query(models.Enrollment).filter(models.Enrollment.id == enrollment_id).first()


def get_enrollments_by_user(db: Session, user_id: int):
    return db.query(models.Enrollment).options(joinedload(models.Enrollment.course)).filter(models.Enrollment.user_id == user_id).all()


def create_enrollment(db: Session, enrollment: schemas.EnrollmentCreate) -> models.Enrollment:
    existing = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.user_id == enrollment.user_id, models.Enrollment.course_id == enrollment.course_id)
        .first()
    )
    if existing:
        raise ValueError("El estudiante ya se encuentra inscrito en este curso")

    if not check_user_meets_prerequisites(db, enrollment.user_id, enrollment.course_id):
        raise ValueError("No se cumplen los prerrequisitos académicos para acceder a este nivel")

    db_course = db.query(models.Course).filter(models.Course.id == enrollment.course_id).first()
    access_end = None
    if db_course and db_course.modality == "no_formal":
        access_end = _utcnow() + dt.timedelta(days=365)

    try:
        row = models.Enrollment(
            user_id=enrollment.user_id,
            course_id=enrollment.course_id,
            access_window_end=access_end
        )
        db.add(row)

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
    except MemoryError:
        raise
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al procesar la inscripción: {str(e)}")


# ── Assessments ────────────────────────────────────────

def get_assessment(db: Session, assessment_id: int):
    return db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()


def get_assessment_with_questions(db: Session, assessment_id: int):
    return (
        db.query(models.Assessment)
        .filter(models.Assessment.id == assessment_id)
        .first()
    )


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

    if attempt.passed:
        enrollment.approved = True
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


# ── Lesson Progress ────────────────────────────────────

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


# ── Certificates ───────────────────────────────────────

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


# ── Formal Acta ────────────────────────────────────────

def close_formal_acta(
    db: Session, course_id: int, closed_by_user_id: int, min_grade: float, min_attendance: float
):
    course = db.query(models.Course).get(course_id)
    if not course:
        return None

    assessments = db.query(models.Assessment).join(models.Lesson).filter(
        models.Lesson.course_id == course_id
    ).all()

    weights = {a.id: float(a.weight) for a in assessments}
    total_weight = sum(weights.values())

    enrollments = db.query(models.Enrollment).filter(models.Enrollment.course_id == course_id).all()
    for e in enrollments:
        attempts = db.query(models.AssessmentAttempt).filter(
            models.AssessmentAttempt.enrollment_id == e.id
        ).all()

        best_scores = {}
        for att in attempts:
            if att.assessment_id not in best_scores or att.score > best_scores[att.assessment_id]:
                best_scores[att.assessment_id] = float(att.score)

        if total_weight > 0:
            weighted_sum = sum(best_scores.get(aid, 0) * w for aid, w in weights.items())
            final_grade = weighted_sum / total_weight
        else:
            final_grade = db.query(func.avg(models.AssessmentAttempt.score)).filter(
                models.AssessmentAttempt.enrollment_id == e.id
            ).scalar() or 0

        total_sessions = db.query(func.count(func.distinct(models.CourseAttendance.session_date))).join(models.Enrollment).filter(
            models.Enrollment.course_id == course_id
        ).scalar() or 1

        present_count = db.query(models.CourseAttendance).filter(
            models.CourseAttendance.enrollment_id == e.id,
            models.CourseAttendance.status.in_(["present", "justified"])
        ).count()

        attendance_rate = (present_count / total_sessions * 100)

        if final_grade >= min_grade and attendance_rate >= min_attendance:
            e.approved = True
            e.status = "completed"

            log = models.AcademyActivityLog(
                event_type="completion",
                course_id=course_id,
                user_id=e.user_id,
                modality="formal",
                value=float(final_grade)
            )
            db.add(log)

    acta = models.FormalActa(
        course_id=course_id,
        closed_by_user_id=closed_by_user_id,
        min_grade_required=min_grade,
        min_attendance_required=min_attendance
    )
    db.add(acta)
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


# ── Attendance ─────────────────────────────────────────

def record_activity_attendance(db: Session, enrollment_id: int):
    return {"status": "success", "enrollment_id": enrollment_id, "timestamp": _utcnow()}


# ── Assignments ────────────────────────────────────────

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


# ── Forum ──────────────────────────────────────────────

def get_academy_candidates(db: Session):
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
