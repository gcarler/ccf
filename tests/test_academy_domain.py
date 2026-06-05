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


def seed_persona(db_session, user):
    persona = models.Persona(
        user_id=user.id,
        first_name="Student",
        last_name="Academy",
        email=user.email,
    )
    db_session.add(persona)
    db_session.commit()
    db_session.refresh(persona)
    return persona


def test_create_enrollment_prevents_duplicates(db_session):
    user = seed_user(db_session)
    course = seed_course(db_session)
    payload = schemas.EnrollmentCreate(user_id=user.id, course_id=course.id)
    crud.create_enrollment(db_session, payload)

    with pytest.raises(ValueError):
        crud.create_enrollment(db_session, payload)


def test_create_enrollment_dual_writes_persona_id(db_session):
    user = seed_user(db_session)
    persona = seed_persona(db_session, user)
    course = seed_course(db_session)
    payload = schemas.EnrollmentCreate(user_id=user.id, course_id=course.id)

    enrollment = crud.create_enrollment(db_session, payload)

    assert enrollment.user_id == user.id
    assert enrollment.persona_id == persona.id

    log = db_session.query(models.AcademyActivityLog).filter_by(
        event_type="enrollment",
        course_id=course.id,
    ).one()
    assert log.user_id == user.id
    assert log.persona_id == persona.id


def test_lesson_progress_dual_writes_and_updates_enrollment_by_persona(db_session):
    user = seed_user(db_session)
    persona = seed_persona(db_session, user)
    course = seed_course(db_session)
    lesson = models.Lesson(
        course_id=course.id,
        title="Leccion 1",
        content="Contenido",
        order_index=1,
    )
    db_session.add(lesson)
    db_session.commit()
    db_session.refresh(lesson)
    enrollment = models.Enrollment(
        user_id=None,
        persona_id=persona.id,
        course_id=course.id,
    )
    db_session.add(enrollment)
    db_session.commit()

    progress = crud.update_lesson_progress(
        db_session,
        user_id=user.id,
        lesson_id=lesson.id,
        progress_percent=100,
        last_position=45,
    )

    assert progress.user_id == user.id
    assert progress.persona_id == persona.id
    db_session.refresh(enrollment)
    assert enrollment.progress_percent == 100


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

    readiness_dict = crud.get_pilot_readiness(db_session)
    readiness = schemas.PilotReadiness(**readiness_dict)
    assert readiness.environment_ready is True
    assert len(readiness.checklist) > 0
