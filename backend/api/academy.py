from __future__ import annotations

import pathlib
import uuid
from typing import List, Optional, cast

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

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


@router.get("/courses/{course_id}/assessments", response_model=List[schemas.Assessment])
def read_course_assessments(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    is_staff = role_in(getattr(current_user, "role", ""), {"admin", "coordinador", "docente"})
    return crud.get_course_assessments(db, course_id=course_id, published_only=not is_staff)


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
