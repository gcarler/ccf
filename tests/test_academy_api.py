"""Tests for the canonical Academy API."""

from backend import models
from tests.conftest import auth_headers, seed_admin, seed_user_with_role


def test_academy_courses_list(client, db_session):
    """List courses endpoint should return 200."""
    admin, persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")
    resp = client.get("/api/academy/courses", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_lector_can_enroll_and_update_own_progress(client, db_session):
    student, persona, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="academy.student@example.com",
        password="testpass123",
    )
    student.rol_plataforma.permisos = {"academy:study": "allow"}
    course = models.Course(
        code="ACA-E2E",
        title="Academy E2E",
        modality="formal",
        is_published=True,
    )
    lesson = models.Lesson(
        course=course,
        title="Leccion E2E",
        content="Contenido de prueba",
        order_index=1,
        is_published=True,
    )
    db_session.add_all([course, lesson])
    db_session.commit()
    headers = auth_headers(
        client, email=student.email, password="testpass123"
    )

    enrollment = client.post(
        "/api/academy/enrollments",
        headers=headers,
        json={"persona_id": str(persona.id), "course_id": str(course.id)},
    )
    assert enrollment.status_code == 201, enrollment.text

    progress = client.post(
        f"/api/academy/lessons/{lesson.id}/progress",
        headers=headers,
        json={"progress_percent": 100, "last_position_seconds": 45},
    )
    assert progress.status_code == 200, progress.text
    assert progress.json()["is_completed"] is True

    profile = client.get("/api/academy/me/profile", headers=headers)
    assert profile.status_code == 200, profile.text
    assert profile.json()["enrollments_count"] == 1


def test_lector_cannot_enroll_another_persona(client, db_session):
    student, _, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="academy.student@example.com",
        password="testpass123",
    )
    student.rol_plataforma.permisos = {"academy:study": "allow"}
    course = models.Course(
        code="ACA-DENY",
        title="Academy Deny",
        modality="formal",
        is_published=True,
    )
    db_session.add(course)
    db_session.commit()
    headers = auth_headers(
        client, email=student.email, password="testpass123"
    )

    response = client.post(
        "/api/academy/enrollments",
        headers=headers,
        json={
            "persona_id": "00000000-0000-0000-0000-000000000001",
            "course_id": str(course.id),
        },
    )

    assert response.status_code == 403
