import pytest

from backend import models
from backend.crud import academy as academy_crud
from backend.models_shared import _utcnow
from backend.schemas.academy import EnrollmentCreate
from tests.conftest import seed_user_with_role


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
    user, persona, _ = seed_user_with_role(
        db_session, role_name="LECTOR", email="student@example.com"
    )
    course = seed_course(db_session)
    payload = EnrollmentCreate(persona_id=persona.id, course_id=course.id)

    academy_crud.create_enrollment(db_session, payload)

    with pytest.raises(ValueError):
        academy_crud.create_enrollment(db_session, payload)


def test_create_enrollment_uses_persona_uuid(db_session):
    user, persona, _ = seed_user_with_role(
        db_session, role_name="LECTOR", email="student@example.com"
    )
    course = seed_course(db_session)

    enrollment = academy_crud.create_enrollment(
        db_session,
        EnrollmentCreate(persona_id=persona.id, course_id=course.id),
    )

    assert enrollment.persona_id == user.id == persona.id
    assert enrollment.course_id == course.id


def test_archived_enrollment_is_reactivated(db_session):
    _, persona, _ = seed_user_with_role(
        db_session, role_name="LECTOR", email="student@example.com"
    )
    course = seed_course(db_session)
    payload = EnrollmentCreate(persona_id=persona.id, course_id=course.id)
    enrollment = academy_crud.create_enrollment(db_session, payload)
    enrollment.deleted_at = _utcnow()
    db_session.commit()

    restored = academy_crud.create_enrollment(db_session, payload)

    assert restored.id == enrollment.id
    assert restored.deleted_at is None
    assert restored.status == "active"
