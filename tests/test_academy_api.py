from backend import models
from backend.core.security import get_password_hash


def seed_user(db_session, email="student@example.com", password="secret123"):
    user = models.User(
        username="student",
        email=email,
        password_hash=get_password_hash(password),
        role="estudiante",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_headers(client, email="student@example.com", password="secret123"):
    response = client.post(
        "/api/auth/login",
        data={"username": email, "password": password, "grant_type": "password"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_my_academy_profile_uses_authenticated_user_id(client, db_session):
    user = seed_user(db_session)

    response = client.get("/api/academy/me/profile", headers=auth_headers(client))

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user.id
    assert data["username"] == user.username
    assert data["enrollments_count"] == 0
    assert data["certificates_count"] == 0
    assert data["active_courses"] == []
    assert data["recent_certificates"] == []


def test_academy_progress_for_current_user(client, db_session):
    user = seed_user(db_session)
    course = models.Course(
        code="DISC-101",
        title="Discipulado Básico",
        modality="no_formal",
        is_published=True,
    )
    db_session.add(course)
    db_session.flush()

    lesson_1 = models.Lesson(course_id=course.id, title="Bienvenida", content="Intro")
    lesson_2 = models.Lesson(course_id=course.id, title="Fundamentos", content="Bases")
    db_session.add_all([lesson_1, lesson_2])
    db_session.flush()

    enrollment = models.Enrollment(
        user_id=user.id,
        course_id=course.id,
        status="active",
        progress_percent=50,
        lessons_completed=[],
        approved=False,
        certificate_issued=False,
    )
    db_session.add(enrollment)
    db_session.flush()

    db_session.add(
        models.LessonProgress(
            user_id=user.id,
            lesson_id=lesson_1.id,
            progress_percent=100,
            last_position_seconds=600,
            is_completed=True,
        )
    )
    db_session.commit()

    response = client.get(f"/api/academy/users/{user.id}/progress", headers=auth_headers(client))

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    row = data[0]
    assert row["id"] == course.id
    assert row["title"] == "Discipulado Básico"
    assert row["progress_percent"] == 50.0
    assert row["status"] == "active"
    assert row["average_grade"] == 50.0
    assert row["lessons_completed"] == 1
    assert row["total_lessons"] == 2
    assert row["certificate_issued"] is False
