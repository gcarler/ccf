import pytest

from backend import crud, models, schemas
from backend.core.security import get_password_hash


def seed_user(db_session, email="student@example.com"):
    user = models.User(
        username="student",
        email=email,
        password_hash=get_password_hash("secret123"),
        role="estudiante",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def seed_course(db_session, code="COURSE-1"):
    course = models.Course(
        code=code,
        title="Curso Test",
        modality="formal",
        is_published=True,
    )
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)
    return course


def test_create_enrollment_prevents_duplicates(db_session):
    user = seed_user(db_session)
    course = seed_course(db_session)
    payload = schemas.EnrollmentCreate(user_id=user.id, course_id=course.id)
    crud.create_enrollment(db_session, payload)

    with pytest.raises(ValueError):
        crud.create_enrollment(db_session, payload)


def test_issue_pending_certificates(db_session):
    user = seed_user(db_session)
    course = seed_course(db_session, code="COURSE-2")
    enrollment = models.Enrollment(
        user_id=user.id,
        course_id=course.id,
        status="completed",
        approved=True,
        certificate_issued=False,
    )
    db_session.add(enrollment)
    db_session.commit()
    db_session.refresh(enrollment)

    issued = crud.issue_pending_certificates(db_session)
    assert len(issued) == 1
    assert issued[0].certificate_code.startswith("CCF-")


def test_pilot_readiness_returns_checklist(db_session):
    user = seed_user(db_session, email="other@example.com")
    course = seed_course(db_session, code="COURSE-3")
    enrollment = models.Enrollment(user_id=user.id, course_id=course.id)
    db_session.add(enrollment)
    db_session.commit()

    readiness = crud.get_pilot_readiness(db_session)
    assert readiness.environment_ready is True
    assert len(readiness.checklist) > 0
