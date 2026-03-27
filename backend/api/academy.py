from __future__ import annotations

import pathlib
import uuid
from typing import List, Optional, cast

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend import crud
from backend import models
from backend import schemas
from backend.auth import normalize_role, require_active_user, require_staff_or_admin, role_in
from backend.core.audit import record_admin_action
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.uploads import sanitize_filename, save_upload


router = APIRouter()
settings = get_settings()


def _serialize_submission_review(row: tuple[models.AssignmentSubmission, str, str]) -> schemas.AssignmentSubmissionReview:
    submission, lesson_title, student_name = row
    return schemas.AssignmentSubmissionReview(
        id=submission.id,
        enrollment_id=submission.enrollment_id,
        lesson_id=submission.lesson_id,
        student_name=student_name,
        lesson_title=lesson_title,
        file_url=submission.file_url,
        comment=submission.comment,
        grade=submission.grade,
        teacher_feedback=submission.teacher_feedback,
        submitted_at=submission.created_at,
    )


@router.get("/courses/", response_model=List[schemas.Course])
def read_courses(
    skip: int = 0,
    limit: int = 100,
    modality: Optional[str] = None,
    published_only: bool = True,
    db: Session = Depends(get_db),
):
    return crud.get_courses(db, skip=skip, limit=limit, modality=modality, published_only=published_only)


@router.get("/courses/{course_id}", response_model=schemas.Course)
def read_course(course_id: int, db: Session = Depends(get_db)):
    db_course = crud.get_course(db, course_id)
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    return db_course


@router.get("/courses/{course_id}/lessons", response_model=List[schemas.Lesson])
def read_course_lessons(course_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.Lesson)
        .filter(models.Lesson.course_id == course_id)
        .order_by(models.Lesson.order_index)
        .all()
    )


@router.get("/assessments/{assessment_id}", response_model=schemas.Assessment)
def read_assessment(assessment_id: int, db: Session = Depends(get_db)):
    db_assessment = crud.get_assessment_with_questions(db, assessment_id)
    if not db_assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return db_assessment


class AssessmentSubmission(BaseModel):
    enrollment_id: int
    answers: List[dict] # [{"question_id": 1, "selected_option_id": 2}]


@router.post("/assessments/{assessment_id}/submit", response_model=schemas.AssessmentAttempt)
def submit_assessment(
    assessment_id: int,
    payload: AssessmentSubmission,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user)
):
    try:
        return crud.submit_assessment_attempt(
            db, 
            assessment_id=assessment_id, 
            enrollment_id=payload.enrollment_id,
            answers=payload.answers
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/lessons/{lesson_id}/progress")
def read_lesson_progress(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user)
):
    progress = crud.get_lesson_progress(db, user_id=current_user.id, lesson_id=lesson_id)
    if not progress:
        return {"progress_percent": 0.0, "last_position_seconds": 0, "is_completed": False}
    return progress


class ProgressUpdate(BaseModel):
    progress_percent: float
    last_position_seconds: int


@router.post("/lessons/{lesson_id}/progress")
def update_lesson_progress(
    lesson_id: int,
    payload: ProgressUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user)
):
    return crud.update_lesson_progress(
        db, 
        user_id=current_user.id, 
        lesson_id=lesson_id, 
        progress_percent=payload.progress_percent,
        last_position=payload.last_position_seconds
    )


@router.post("/enrollments/{enrollment_id}/issue-certificate", response_model=schemas.Certificate)
def request_certificate(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user)
):
    try:
        return crud.issue_certificate(db, enrollment_id=enrollment_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/certificates/validate/{code}", response_model=schemas.Certificate)
def validate_certificate(code: str, db: Session = Depends(get_db)):
    cert = crud.get_certificate_by_code(db, code=code)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return cert


@router.get("/dashboard/metrics", response_model=schemas.DashboardMetrics)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    return crud.get_dashboard_metrics(db)


@router.get("/dashboard/pilot-readiness", response_model=schemas.PilotReadiness)
def get_pilot_readiness(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    return crud.get_pilot_readiness(db)


@router.post("/courses/{course_id}/formal/close-acta", response_model=schemas.FormalActa)
def close_formal_acta(
    course_id: int,
    payload: schemas.FormalActaCloseRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    acta = crud.close_formal_acta(
        db,
        course_id=course_id,
        closed_by_user_id=int(getattr(current_user, "id", 0)),
        min_grade=payload.min_grade,
        min_attendance=payload.min_attendance,
    )
    record_admin_action(
        db,
        current_user,
        action="close_formal_acta",
        resource_type="formal_acta",
        resource_id=str(acta.id),
        metadata={
            "course_id": course_id,
            "min_grade": payload.min_grade,
            "min_attendance": payload.min_attendance,
        },
    )
    return acta


@router.get("/courses/{course_id}/formal/last-acta", response_model=Optional[schemas.FormalActa])
def read_last_formal_acta(course_id: int, db: Session = Depends(get_db)):
    return crud.get_latest_acta_by_course(db, course_id)


@router.post("/enrollments/", response_model=schemas.Enrollment)
def create_enrollment(
    enrollment: schemas.EnrollmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    user_id = int(getattr(current_user, "id", 0))
    if normalize_role(str(current_user.role)) != "admin" and user_id != enrollment.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only create your own enrollment")
    try:
        return crud.create_enrollment(db, enrollment)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/enrollments/{enrollment_id}/check-in", response_model=schemas.Attendance)
def check_in_attendance(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    enrollment = crud.get_enrollment(db, enrollment_id)
    if not enrollment or int(getattr(enrollment, "user_id", 0)) != int(getattr(current_user, "id", 0)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return crud.record_activity_attendance(db, enrollment_id)


@router.post(
    "/enrollments/{enrollment_id}/assessments/{assessment_id}/submit",
    response_model=schemas.AssessmentAttempt,
)
def submit_assessment(
    enrollment_id: int,
    assessment_id: int,
    payload: schemas.AssessmentAttemptSubmit,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    enrollment = crud.get_enrollment(db, enrollment_id)
    assessment = crud.get_assessment(db, assessment_id)
    if not enrollment or not assessment:
        raise HTTPException(status_code=404, detail="Not found")
    current_id = int(getattr(current_user, "id", 0))
    if int(getattr(enrollment, "user_id", 0)) != current_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    attempt = crud.create_or_update_assessment_attempt(
        db, enrollment=enrollment, assessment=assessment, submitted_score=payload.submitted_score
    )
    if getattr(enrollment, "approved", False):
        crud.issue_certificate_for_enrollment(db, enrollment)
    return attempt


@router.get("/users/{user_id}/certificates", response_model=List[schemas.Certificate])
def read_user_certificates(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    if int(getattr(current_user, "id", 0)) != user_id and normalize_role(str(current_user.role)) != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return crud.get_certificates_by_user(db, user_id)


@router.get("/users/{user_id}/enrollments", response_model=List[schemas.Enrollment])
def read_user_enrollments(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    if int(getattr(current_user, "id", 0)) != user_id and normalize_role(str(current_user.role)) != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return crud.get_enrollments_by_user(db, user_id)


@router.post("/lessons/{lesson_id}/resources", response_model=schemas.Resource)
async def upload_resource(
    lesson_id: int,
    title: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    original_name = file.filename or "resource"
    sanitized = sanitize_filename(cast(str, original_name))
    unique_name = f"res_{lesson_id}_{uuid.uuid4().hex}_{sanitized}"
    try:
        contents = await file.read()
        save_upload(contents, unique_name, settings.uploads_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    db_resource = models.Resource(
        title=title,
        file_url=f"/static/{unique_name}",
        resource_type=file.content_type or "application/octet-stream",
        lesson_id=lesson_id,
    )
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)
    record_admin_action(
        db,
        current_user,
        action="upload_lesson_resource",
        resource_type="lesson_resource",
        resource_id=str(db_resource.id),
        metadata={"lesson_id": lesson_id, "title": title},
    )
    return db_resource


@router.post("/lessons/{lesson_id}/submit-assignment", response_model=schemas.AssignmentSubmission)
async def submit_assignment_file(
    lesson_id: int,
    enrollment_id: int = Form(...),
    comment: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    enrollment = crud.get_enrollment(db, enrollment_id)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    current_id = int(getattr(current_user, "id", 0))
    if int(getattr(enrollment, "user_id", 0)) != current_id and normalize_role(str(current_user.role)) != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if int(getattr(lesson, "course_id", 0)) != int(getattr(enrollment, "course_id", 0)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lesson does not belong to enrollment")

    original_name = file.filename or "assignment"
    sanitized = sanitize_filename(cast(str, original_name))
    unique_name = f"assignment_{lesson_id}_{enrollment_id}_{uuid.uuid4().hex}_{sanitized}"
    try:
        contents = await file.read()
        save_upload(contents, unique_name, settings.uploads_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    submission = crud.create_assignment_submission(
        db,
        enrollment_id=enrollment_id,
        lesson_id=lesson_id,
        file_url=f"/static/{unique_name}",
        comment=comment,
    )
    return submission


@router.get("/admin/submissions", response_model=List[schemas.AssignmentSubmissionReview])
def admin_list_submissions(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    rows = crud.list_assignment_submissions_with_meta(db, limit=limit)
    return [_serialize_submission_review(row) for row in rows]


@router.patch("/admin/submissions/{submission_id}/grade", response_model=schemas.AssignmentSubmissionReview)
def admin_grade_submission(
    submission_id: int,
    grade: Optional[float] = Query(None),
    feedback: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    if grade is None and feedback is None:
        raise HTTPException(status_code=400, detail="grade or feedback required")
    if grade is not None and (grade < 0 or grade > 100):
        raise HTTPException(status_code=400, detail="grade must be between 0 and 100")
    updated = crud.grade_assignment_submission(db, submission_id, grade=grade, feedback=feedback)
    if not updated:
        raise HTTPException(status_code=404, detail="Submission not found")
    row = crud.get_assignment_submission_with_meta(db, submission_id)
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    return _serialize_submission_review(row)


@router.post("/certificates/sync", response_model=List[schemas.Certificate])
def sync_certificates(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    issued = crud.issue_pending_certificates(db)
    record_admin_action(
        db,
        current_user,
        action="sync_certificates",
        resource_type="certificate",
        metadata={"issued_count": len(issued)},
    )
    return issued


@router.get("/me/profile", response_model=schemas.AcademyStudentProfile)
def get_my_academy_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    user_id = str(current_user.user_id)
    enrollments = db.query(models.Enrollment).filter(models.Enrollment.user_id == user_id).all()
    certificates = db.query(models.Certificate).join(models.Enrollment).filter(models.Enrollment.user_id == user_id).all()
    
    total_progress = sum(float(e.progress_percent or 0) for e in enrollments) / len(enrollments) if enrollments else 0.0
    
    return {
        "user_id": user_id,
        "username": getattr(current_user, "username", ""),
        "total_progress": round(total_progress, 1),
        "enrollments_count": len(enrollments),
        "certificates_count": len(certificates),
        "active_courses": enrollments,
        "recent_certificates": certificates[-3:] if certificates else []
    }


@router.get("/analytics/candidates", response_model=List[schemas.User])
def get_academy_candidates(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin)
):
    return crud.get_academy_candidates(db)


# -----------------
# Forum API
# -----------------
@router.get("/forum/threads", response_model=List[schemas.ForumThread])
def get_forum_threads(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user)
):
    return crud.get_forum_threads(db)


@router.post("/forum/threads", response_model=schemas.ForumThread)
def create_thread(
    thread: schemas.ForumThreadBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user)
):
    thread_data = schemas.ForumThreadCreate(**thread.model_dump(), author_id=current_user.id)
    return crud.create_forum_thread(db, thread_data)
