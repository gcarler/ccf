"""Comprehensive Academy module tests — ~58 tests covering happy paths,
Pydantic extra-forbid, validation, pagination, audit logging, and security."""

from __future__ import annotations

import uuid as _uuid

from backend import models
from backend.models_shared import _utcnow
from tests.conftest import auth_headers, seed_admin, seed_user_with_role

# ── Helpers ──────────────────────────────────────────────────────────────


def _create_course(db_session, *, sede_id=None, is_published=True, code=None):
    course = models.Course(
        code=code or f"T-{_uuid.uuid4().hex[:8]}",
        title=f"Course {_uuid.uuid4().hex[:6]}",
        modality="formal",
        sede_id=sede_id,
        is_published=is_published,
    )
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)
    return course


def _create_lesson(db_session, course_id, *, is_published=True, title=None, order_index=1):
    lesson = models.Lesson(
        course_id=course_id,
        title=title or f"Lesson {_uuid.uuid4().hex[:6]}",
        content="Content",
        order_index=order_index,
        is_published=is_published,
    )
    db_session.add(lesson)
    db_session.commit()
    db_session.refresh(lesson)
    return lesson


def _create_assessment(db_session, course_id, *, lesson_id=None, title=None, is_published=True):
    assessment = models.Assessment(
        course_id=course_id,
        lesson_id=lesson_id,
        title=title or f"Assessment {_uuid.uuid4().hex[:6]}",
        passing_score=70,
        max_score=100,
        is_published=is_published,
    )
    db_session.add(assessment)
    db_session.commit()
    db_session.refresh(assessment)
    return assessment


def _create_question(db_session, assessment_id, *, text="Q1", points=1):
    q = models.AssessmentQuestion(
        assessment_id=assessment_id,
        question_text=text,
        question_type="multiple_choice",
        points=points,
        order_index=0,
    )
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)
    return q


def _create_option(db_session, question_id, *, text="Opt A", is_correct=False):
    opt = models.AssessmentOption(
        question_id=question_id,
        option_text=text,
        is_correct=is_correct,
    )
    db_session.add(opt)
    db_session.commit()
    db_session.refresh(opt)
    return opt


def _create_enrollment(db_session, persona_id, course_id):
    enrollment = models.Enrollment(persona_id=persona_id, course_id=course_id)
    db_session.add(enrollment)
    db_session.commit()
    db_session.refresh(enrollment)
    return enrollment


def _create_submission(db_session, enrollment_id, lesson_id, *, file_url=None):
    sub = models.AssignmentSubmission(
        enrollment_id=enrollment_id,
        lesson_id=lesson_id,
        file_url=file_url or f"https://seaweed.local/{_uuid.uuid4().hex}.pdf",
        comment="test submission",
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


# ══════════════════════════════════════════════════════════════════════════
# A. Happy-path endpoints
# ══════════════════════════════════════════════════════════════════════════


def test_get_single_course(client, db_session):
    admin, _, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.get(f"/api/academy/courses/{course.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(course.id)
    assert data["code"] == course.code
    assert data["title"] == course.title
    assert "lesson_count" in data


def test_get_single_course_404(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    fake_id = _uuid.uuid4()
    resp = client.get(f"/api/academy/courses/{fake_id}", headers=headers)
    assert resp.status_code == 404


def test_list_lessons(client, db_session):
    admin, _, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    _create_lesson(db_session, course.id, title="First")
    _create_lesson(db_session, course.id, title="Second", order_index=2)
    headers = auth_headers(client, email=admin.email)
    resp = client.get(f"/api/academy/courses/{course.id}/lessons", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_list_assessments(client, db_session):
    admin, _, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    _create_assessment(db_session, course.id, title="Exam 1")
    _create_assessment(db_session, course.id, title="Exam 2")
    headers = auth_headers(client, email=admin.email)
    resp = client.get(f"/api/academy/courses/{course.id}/assessments", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_get_assessment(client, db_session):
    admin, persona, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    assessment = _create_assessment(db_session, course.id)
    q = _create_question(db_session, assessment.id, text="What?", points=5)
    _create_option(db_session, q.id, text="Yes", is_correct=True)
    _create_option(db_session, q.id, text="No", is_correct=False)
    headers = auth_headers(client, email=admin.email)
    resp = client.get(f"/api/academy/assessments/{assessment.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(assessment.id)
    assert len(data["questions"]) == 1


def test_get_assessment_unpublished_course_404(client, db_session):
    admin, persona, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="unpub.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id, is_published=False)
    assessment = _create_assessment(db_session, course.id)
    headers = auth_headers(client, email=student.email)
    resp = client.get(f"/api/academy/assessments/{assessment.id}", headers=headers)
    assert resp.status_code == 404


def test_submit_assessment(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="submit.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    assessment = _create_assessment(db_session, course.id)
    q = _create_question(db_session, assessment.id, text="Q1", points=10)
    opt_correct = _create_option(db_session, q.id, text="Right", is_correct=True)
    _create_option(db_session, q.id, text="Wrong", is_correct=False)
    _create_enrollment(db_session, persona_st.id, course.id)
    headers = auth_headers(client, email=student.email)
    resp = client.post(
        f"/api/academy/assessments/{assessment.id}/submit",
        headers=headers,
        json={"answers": [{"question_id": str(q.id), "selected_option_id": str(opt_correct.id)}]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 100.0
    assert data["passed"] is True


def test_submit_assessment_no_enrollment_403(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="noenroll.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    assessment = _create_assessment(db_session, course.id)
    _create_question(db_session, assessment.id)
    headers = auth_headers(client, email=student.email)
    resp = client.post(
        f"/api/academy/assessments/{assessment.id}/submit",
        headers=headers,
        json={},
    )
    assert resp.status_code == 403


def test_get_lesson_progress(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="progress.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    headers = auth_headers(client, email=student.email)
    resp = client.get(f"/api/academy/lessons/{lesson.id}/progress", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_completed"] is False
    assert data["progress_percent"] == 0.0


def test_get_lesson_progress_deleted_lesson_404(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="del.lesson.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    lesson.deleted_at = _utcnow()
    db_session.commit()
    headers = auth_headers(client, email=student.email)
    resp = client.get(f"/api/academy/lessons/{lesson.id}/progress", headers=headers)
    assert resp.status_code == 404


def test_update_lesson_progress(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="upd.progress.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    _create_enrollment(db_session, persona_st.id, course.id)
    headers = auth_headers(client, email=student.email)
    resp = client.post(
        f"/api/academy/lessons/{lesson.id}/progress",
        headers=headers,
        json={"progress_percent": 100, "last_position_seconds": 60},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_completed"] is True
    assert float(data["progress_percent"]) == 100.0


def test_my_enrollments(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="myenr.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    _create_enrollment(db_session, persona_st.id, course.id)
    headers = auth_headers(client, email=student.email)
    resp = client.get("/api/academy/me/enrollments", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_all_enrollments(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="allenr.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    _create_enrollment(db_session, persona_st.id, course.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.get("/api/academy/enrollments", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_check_in(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="checkin.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    enrollment = _create_enrollment(db_session, persona_st.id, course.id)
    headers = auth_headers(client, email=student.email)
    resp = client.post(f"/api/academy/enrollments/{enrollment.id}/check-in", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "present"


def test_check_in_idempotent(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="idem.checkin.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    enrollment = _create_enrollment(db_session, persona_st.id, course.id)
    headers = auth_headers(client, email=student.email)
    resp1 = client.post(f"/api/academy/enrollments/{enrollment.id}/check-in", headers=headers)
    resp2 = client.post(f"/api/academy/enrollments/{enrollment.id}/check-in", headers=headers)
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["id"] == resp2.json()["id"]


def test_my_progress(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="myprog.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    _create_enrollment(db_session, persona_st.id, course.id)
    headers = auth_headers(client, email=student.email)
    resp = client.get("/api/academy/me/progress", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "progress_percent" in data[0]
    assert "lessons_completed" in data[0]


def test_t12_me_progress_batch_queries_accurate(client, db_session):
    """ACAD-T12 — resumen de progreso con batch queries correctas.

    El endpoint agrega en 2 queries por lote (total y completadas, agrupadas
    por course). Verifica que ``total_lessons`` cuente solo lecciones
    publicadas no eliminadas y ``lessons_completed`` solo las completadas.
    """
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="t12.batch@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson_done = _create_lesson(db_session, course.id, order_index=1)
    _create_lesson(db_session, course.id, order_index=2)
    _create_lesson(db_session, course.id, order_index=3, is_published=False)
    deleted = _create_lesson(db_session, course.id, order_index=4)
    deleted.deleted_at = _utcnow()
    db_session.commit()
    _create_enrollment(db_session, persona_st.id, course.id)
    db_session.add(
        models.LessonProgress(
            persona_id=persona_st.id,
            lesson_id=lesson_done.id,
            progress_percent=100,
            is_completed=True,
        )
    )
    db_session.commit()

    headers = auth_headers(client, email=student.email)
    resp = client.get("/api/academy/me/progress", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    row = data[0]
    assert row["id"] == str(course.id)
    assert row["title"] == course.title
    assert row["total_lessons"] == 2  # solo publicadas no eliminadas
    assert row["lessons_completed"] == 1
    assert row["status"] == "active"
    assert row["average_grade"] == 0  # final_grade None -> 0
    assert row["certificate_issued"] is False
    assert row["last_activity"] is not None


def test_t12_me_progress_pagination_and_persona_scope(client, db_session):
    """ACAD-T12 — skip/limit funcional y aislamiento por persona."""
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="t12.pag@example.com",
        permisos={"academy:study": "allow"},
    )
    _, persona_other, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="t12.other@example.com",
        permisos={"academy:study": "allow"},
    )
    course_ids = []
    for _ in range(3):
        course = _create_course(db_session, sede_id=sede.id)
        _create_enrollment(db_session, persona_st.id, course.id)
        course_ids.append(str(course.id))
    # Inscripción de OTRO estudiante no debe filtrarse.
    other_course = _create_course(db_session, sede_id=sede.id)
    _create_enrollment(db_session, persona_other.id, other_course.id)

    headers = auth_headers(client, email=student.email)
    full = client.get("/api/academy/me/progress", headers=headers).json()
    assert len(full) == 3
    assert all(row["id"] in course_ids for row in full)
    page = client.get(
        "/api/academy/me/progress", headers=headers, params={"skip": 1, "limit": 2}
    ).json()
    assert len(page) == 2


def test_t12_me_progress_empty_and_soft_deleted_excluded(client, db_session):
    """ACAD-T12 — sin inscripciones devuelve [] y las soft-deleted se ocultan."""
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="t12.empty@example.com",
        permisos={"academy:study": "allow"},
    )
    headers = auth_headers(client, email=student.email)
    assert client.get("/api/academy/me/progress", headers=headers).json() == []

    course = _create_course(db_session, sede_id=sede.id)
    enrollment = _create_enrollment(db_session, persona_st.id, course.id)
    enrollment.deleted_at = _utcnow()
    db_session.commit()
    assert client.get("/api/academy/me/progress", headers=headers).json() == []


def test_my_certificates(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="mycert.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    enrollment = _create_enrollment(db_session, persona_st.id, course.id)
    certificate = models.Certificate(
        enrollment_id=enrollment.id,
        certificate_code=f"CCF-TEST-{_uuid.uuid4().hex[:12].upper()}",
        certificate_type="completion",
    )
    db_session.add(certificate)
    db_session.commit()
    headers = auth_headers(client, email=student.email)
    resp = client.get("/api/academy/me/certificates", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["certificate_code"] == certificate.certificate_code


def test_request_certificate(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="reqcert.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    enrollment = _create_enrollment(db_session, persona_st.id, course.id)
    enrollment.status = "completed"
    enrollment.approved = True
    db_session.commit()
    headers = auth_headers(client, email=student.email)
    resp = client.post(
        f"/api/academy/enrollments/{enrollment.id}/request-certificate",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "certificate_code" in data
    assert data["enrollment_id"] == str(enrollment.id)


def test_t14_request_certificate_creates_and_marks_enrollment(client, db_session):
    """ACAD-T14 — solicitud crea certificado y marca la inscripción."""
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="t14.create@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    course.certificate_type = "diploma"
    db_session.commit()
    enrollment = _create_enrollment(db_session, persona_st.id, course.id)
    enrollment.status = "completed"
    enrollment.approved = True
    enrollment.final_grade = 95.0
    db_session.commit()

    headers = auth_headers(client, email=student.email)
    resp = client.post(
        f"/api/academy/enrollments/{enrollment.id}/request-certificate",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["enrollment_id"] == str(enrollment.id)
    assert data["certificate_code"].startswith("CCF-ACA-")
    assert len(data["certificate_code"]) == len("CCF-ACA-") + 12
    assert data["certificate_code"].isupper()
    assert data["certificate_type"] == "diploma"

    db_session.refresh(enrollment)
    assert enrollment.certificate_issued is True
    assert enrollment.certificate_code == data["certificate_code"]


def test_t14_request_certificate_idempotent(client, db_session):
    """ACAD-T14 — segunda solicitud reusa el certificado, no duplica."""
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="t14.idem@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    enrollment = _create_enrollment(db_session, persona_st.id, course.id)
    enrollment.status = "completed"
    enrollment.approved = True
    db_session.commit()

    headers = auth_headers(client, email=student.email)
    url = f"/api/academy/enrollments/{enrollment.id}/request-certificate"
    first = client.post(url, headers=headers)
    second = client.post(url, headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    count = (
        db_session.query(models.Certificate)
        .filter(models.Certificate.enrollment_id == enrollment.id)
        .count()
    )
    assert count == 1


def test_t14_request_certificate_rejects_unapproved(client, db_session):
    """ACAD-T14 — curso no aprobado/no completado -> 400."""
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="t14.deny@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    enrollment = _create_enrollment(db_session, persona_st.id, course.id)

    headers = auth_headers(client, email=student.email)
    resp = client.post(
        f"/api/academy/enrollments/{enrollment.id}/request-certificate",
        headers=headers,
    )
    assert resp.status_code == 400


def test_t14_request_certificate_404_not_own_enrollment(client, db_session):
    """ACAD-T14 — inscripción de otro usuario o inexistente -> 404."""
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="t14.404@example.com",
        permisos={"academy:study": "allow"},
    )
    _, persona_other, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="t14.404b@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    enrollment = _create_enrollment(db_session, persona_other.id, course.id)
    enrollment.status = "completed"
    db_session.commit()

    headers = auth_headers(client, email=student.email)
    not_own = client.post(
        f"/api/academy/enrollments/{enrollment.id}/request-certificate",
        headers=headers,
    )
    assert not_own.status_code == 404
    missing = client.post(
        f"/api/academy/enrollments/{_uuid.uuid4()}/request-certificate",
        headers=headers,
    )
    assert missing.status_code == 404


def test_validate_certificate(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="valcert.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    enrollment = _create_enrollment(db_session, persona_st.id, course.id)
    code = f"CCF-VALID-{_uuid.uuid4().hex[:12].upper()}"
    certificate = models.Certificate(
        enrollment_id=enrollment.id,
        certificate_code=code,
        certificate_type="completion",
    )
    db_session.add(certificate)
    db_session.commit()
    resp = client.get(f"/api/academy/certificates/validate/{code}")
    assert resp.status_code == 200
    assert resp.json()["certificate_code"] == code


def test_validate_certificate_404(client, db_session):
    resp = client.get("/api/academy/certificates/validate/FAKE-CODE-12345")
    assert resp.status_code == 404


def test_create_forum_thread(client, db_session):
    admin, persona, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.post(
        "/api/academy/forum/threads",
        headers=headers,
        json={
            "title": "Test Thread",
            "category": "general",
            "content": "Hello world",
            "course_id": str(course.id),
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Thread"
    assert data["author_persona_id"] == str(persona.id)


def test_create_global_thread_forbidden(client, db_session):
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="global.thread.student@example.com",
        permisos={"academy:study": "allow"},
    )
    headers = auth_headers(client, email=student.email)
    resp = client.post(
        "/api/academy/forum/threads",
        headers=headers,
        json={"title": "Global", "category": "announcement", "course_id": None},
    )
    assert resp.status_code == 403


def test_resolve_forum_thread(client, db_session):
    admin, persona, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    thread = models.ForumThread(
        course_id=course.id,
        author_persona_id=persona.id,
        title="Resolvable",
        category="general",
        content="content",
    )
    db_session.add(thread)
    db_session.commit()
    db_session.refresh(thread)
    assert thread.is_resolved is False
    headers = auth_headers(client, email=admin.email)
    resp = client.patch(f"/api/academy/forum/threads/{thread.id}/resolve", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_resolved"] is True
    resp2 = client.patch(f"/api/academy/forum/threads/{thread.id}/resolve", headers=headers)
    assert resp2.json()["is_resolved"] is False


def test_schedule(client, db_session):
    admin, _, sede = seed_admin(db_session)
    _create_course(db_session, sede_id=sede.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.get("/api/academy/schedule", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "title" in data[0]


def test_dashboard_metrics(client, db_session):
    admin, _, sede = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    resp = client.get("/api/academy/dashboard/metrics", headers=headers)
    # F-07 (cierre 2026-08-02): ya NO hay skip silencioso — ``date_trunc`` se
    # hizo dialect-aware en academy_cache.py (SQLite usa strftime). El 500 de
    # SQLite era la causa raíz del skip.
    assert resp.status_code == 200
    data = resp.json()
    assert "active_students" in data
    assert "completion_rate" in data
    assert "certificates_issued" in data
    assert "total_courses" in data
    assert "cards" in data
    assert isinstance(data["enrollment_trends"], list)
    assert isinstance(data["top_courses"], list)


def test_create_course_admin(client, db_session):
    admin, _, sede = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    code = f"NEW-{_uuid.uuid4().hex[:6]}"
    resp = client.post(
        "/api/academy/admin/courses",
        headers=headers,
        json={
            "code": code,
            "title": "Brand New Course",
            "modality": "online",
            "access_level": "persona",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == code
    assert data["title"] == "Brand New Course"


def test_create_course_invalid_access_level(client, db_session):
    admin, _, sede = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    resp = client.post(
        "/api/academy/admin/courses",
        headers=headers,
        json={
            "code": f"BAD-{_uuid.uuid4().hex[:6]}",
            "title": "Bad Level",
            "modality": "online",
            "access_level": "INVALID_LEVEL",
        },
    )
    assert resp.status_code == 422


def test_update_course_admin(client, db_session):
    admin, _, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.patch(
        f"/api/academy/admin/courses/{course.id}",
        headers=headers,
        json={"title": "Updated Title"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


def test_archive_course_admin(client, db_session):
    admin, _, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.delete(f"/api/academy/admin/courses/{course.id}", headers=headers)
    assert resp.status_code == 204
    db_session.expire_all()
    archived = db_session.query(models.Course).filter(models.Course.id == course.id).first()
    assert archived.deleted_at is not None


def test_create_lesson_admin(client, db_session):
    admin, _, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.post(
        f"/api/academy/admin/courses/{course.id}/lessons",
        headers=headers,
        json={"title": "New Lesson", "content": "Body", "order_index": 1},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "New Lesson"
    assert data["course_id"] == str(course.id)


def test_update_lesson_admin(client, db_session):
    admin, _, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.patch(
        f"/api/academy/admin/lessons/{lesson.id}",
        headers=headers,
        json={"title": "Updated Lesson"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Lesson"


def test_archive_lesson_admin(client, db_session):
    admin, _, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.delete(f"/api/academy/admin/lessons/{lesson.id}", headers=headers)
    assert resp.status_code == 204
    db_session.expire_all()
    archived = db_session.query(models.Lesson).filter(models.Lesson.id == lesson.id).first()
    assert archived.deleted_at is not None


def test_list_submissions(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="listsub.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    enrollment = _create_enrollment(db_session, persona_st.id, course.id)
    _create_submission(db_session, enrollment.id, lesson.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.get("/api/academy/admin/submissions", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "student_name" in data[0]


# ══════════════════════════════════════════════════════════════════════════
# B. Pydantic extra='forbid' rejection
# ══════════════════════════════════════════════════════════════════════════


def test_progress_update_extra_field_rejected(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="extra.prog.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    _create_enrollment(db_session, persona_st.id, course.id)
    headers = auth_headers(client, email=student.email)
    resp = client.post(
        f"/api/academy/lessons/{lesson.id}/progress",
        headers=headers,
        json={"progress_percent": 50, "last_position_seconds": 0, "rogue_field": "bad"},
    )
    assert resp.status_code == 422


def test_course_payload_extra_field_rejected(client, db_session):
    admin, _, sede = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    resp = client.post(
        "/api/academy/admin/courses",
        headers=headers,
        json={
            "code": f"X-{_uuid.uuid4().hex[:6]}",
            "title": "Extra",
            "modality": "online",
            "sneaky_field": True,
        },
    )
    assert resp.status_code == 422


def test_course_update_extra_field_rejected(client, db_session):
    admin, _, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.patch(
        f"/api/academy/admin/courses/{course.id}",
        headers=headers,
        json={"title": "OK", "hacker_field": 123},
    )
    assert resp.status_code == 422


def test_lesson_payload_extra_field_rejected(client, db_session):
    admin, _, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.post(
        f"/api/academy/admin/courses/{course.id}/lessons",
        headers=headers,
        json={"title": "L", "content": "", "bad_key": False},
    )
    assert resp.status_code == 422


def test_lesson_update_extra_field_rejected(client, db_session):
    admin, _, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.patch(
        f"/api/academy/admin/lessons/{lesson.id}",
        headers=headers,
        json={"title": "OK", "evil_field": "no"},
    )
    assert resp.status_code == 422


def test_assessment_payload_extra_field_rejected(client, db_session):
    admin, _, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.post(
        "/api/academy/admin/assessments",
        headers=headers,
        json={
            "course_id": str(course.id),
            "title": "A",
            "extra_thing": "nope",
        },
    )
    assert resp.status_code == 422


def test_assessment_update_extra_field_rejected(client, db_session):
    admin, _, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    assessment = _create_assessment(db_session, course.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.patch(
        f"/api/academy/admin/assessments/{assessment.id}",
        headers=headers,
        json={"title": "OK", "totally_invalid": True},
    )
    assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════
# C. Validation tests
# ══════════════════════════════════════════════════════════════════════════


def test_grade_submission_missing_grade(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="missgrade.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    enrollment = _create_enrollment(db_session, persona_st.id, course.id)
    sub = _create_submission(db_session, enrollment.id, lesson.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.patch(
        f"/api/academy/admin/submissions/{sub.id}/grade",
        headers=headers,
        json={},
    )
    assert resp.status_code == 422


def test_grade_submission_out_of_range(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="oor.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    enrollment = _create_enrollment(db_session, persona_st.id, course.id)
    sub = _create_submission(db_session, enrollment.id, lesson.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.patch(
        f"/api/academy/admin/submissions/{sub.id}/grade",
        headers=headers,
        json={"grade": 101},
    )
    assert resp.status_code == 422


def test_grade_submission_negative(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="neggrade.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    enrollment = _create_enrollment(db_session, persona_st.id, course.id)
    sub = _create_submission(db_session, enrollment.id, lesson.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.patch(
        f"/api/academy/admin/submissions/{sub.id}/grade",
        headers=headers,
        json={"grade": -1},
    )
    assert resp.status_code == 422


def test_create_assessment_lesson_not_in_course(client, db_session):
    admin, _, sede = seed_admin(db_session)
    course_a = _create_course(db_session, sede_id=sede.id)
    course_b = _create_course(db_session, sede_id=sede.id)
    lesson_b = _create_lesson(db_session, course_b.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.post(
        "/api/academy/admin/assessments",
        headers=headers,
        json={
            "course_id": str(course_a.id),
            "lesson_id": str(lesson_b.id),
            "title": "Mismatched",
        },
    )
    assert resp.status_code == 422
    assert "lección no pertenece" in resp.json()["detail"].lower()


def test_create_assessment_with_typed_questions(client, db_session):
    admin, _, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.post(
        "/api/academy/admin/assessments",
        headers=headers,
        json={
            "course_id": str(course.id),
            "title": "Typed Questions",
            "passing_score": 50,
            "questions": [
                {
                    "text": "What is 2+2?",
                    "type": "multiple_choice",
                    "points": 10,
                    "options": ["3", "4", "5"],
                    "correct_option": 1,
                },
            ],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Typed Questions"


def test_all_enrollments_invalid_limit(client, db_session):
    admin, _, sede = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    resp = client.get("/api/academy/enrollments?limit=0", headers=headers)
    assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════
# D. Pagination tests
# ══════════════════════════════════════════════════════════════════════════


def test_all_enrollments_skip_limit(client, db_session):
    admin, _, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    for i in range(5):
        student, persona_st, _ = seed_user_with_role(
            db_session,
            role_name="LECTOR",
            email=f"page.enr{i}@example.com",
            permisos={"academy:study": "allow"},
        )
        _create_enrollment(db_session, persona_st.id, course.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.get("/api/academy/enrollments?skip=0&limit=2", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) <= 2


def test_list_courses_skip_limit(client, db_session):
    admin, _, sede = seed_admin(db_session)
    for _ in range(5):
        _create_course(db_session, sede_id=sede.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.get("/api/academy/courses?skip=0&limit=2", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) <= 2


def test_list_lessons_skip_limit(client, db_session):
    admin, _, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    for i in range(5):
        _create_lesson(db_session, course.id, order_index=i, title=f"L{i}")
    headers = auth_headers(client, email=admin.email)
    resp = client.get(
        f"/api/academy/courses/{course.id}/lessons?skip=0&limit=1",
        headers=headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) <= 1


def test_my_enrollments_skip_limit(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="mypage.student@example.com",
        permisos={"academy:study": "allow"},
    )
    for _ in range(3):
        c = _create_course(db_session, sede_id=sede.id)
        _create_enrollment(db_session, persona_st.id, c.id)
    headers = auth_headers(client, email=student.email)
    resp = client.get("/api/academy/me/enrollments?skip=0&limit=1", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) <= 1


def test_list_submissions_limit(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="sublimit.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    enrollment = _create_enrollment(db_session, persona_st.id, course.id)
    for _ in range(3):
        _create_submission(db_session, enrollment.id, lesson.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.get("/api/academy/admin/submissions?limit=1", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) <= 1


# ══════════════════════════════════════════════════════════════════════════
# E. Audit logging tests
# ══════════════════════════════════════════════════════════════════════════


def test_archive_course_creates_audit_log(client, db_session):
    admin, persona, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    headers = auth_headers(client, email=admin.email)
    client.delete(f"/api/academy/admin/courses/{course.id}", headers=headers)
    log = (
        db_session.query(models.AcademyActivityLog)
        .filter(
            models.AcademyActivityLog.event_type == "course_archived",
            models.AcademyActivityLog.persona_id == persona.id,
        )
        .first()
    )
    assert log is not None
    assert log.course_id == course.id


def test_archive_lesson_creates_audit_log(client, db_session):
    admin, persona, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    headers = auth_headers(client, email=admin.email)
    client.delete(f"/api/academy/admin/lessons/{lesson.id}", headers=headers)
    log = (
        db_session.query(models.AcademyActivityLog)
        .filter(
            models.AcademyActivityLog.event_type == "lesson_archived",
            models.AcademyActivityLog.persona_id == persona.id,
        )
        .first()
    )
    assert log is not None
    payload = log.payload_json or {}
    assert payload.get("lesson_id") == str(lesson.id)


def test_grade_submission_creates_audit_log(client, db_session):
    admin, persona, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="audit.grade.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    enrollment = _create_enrollment(db_session, persona_st.id, course.id)
    sub = _create_submission(db_session, enrollment.id, lesson.id)
    headers = auth_headers(client, email=admin.email)
    client.patch(
        f"/api/academy/admin/submissions/{sub.id}/grade",
        headers=headers,
        json={"grade": 85, "feedback": "Good"},
    )
    log = (
        db_session.query(models.AcademyActivityLog)
        .filter(
            models.AcademyActivityLog.event_type == "submission_graded",
            models.AcademyActivityLog.persona_id == persona.id,
        )
        .first()
    )
    assert log is not None
    payload = log.payload_json or {}
    assert payload.get("grade") == 85


def test_update_course_creates_audit_log(client, db_session):
    admin, persona, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    headers = auth_headers(client, email=admin.email)
    client.patch(
        f"/api/academy/admin/courses/{course.id}",
        headers=headers,
        json={"title": "Audited"},
    )
    log = (
        db_session.query(models.AcademyActivityLog)
        .filter(
            models.AcademyActivityLog.event_type == "course_updated",
            models.AcademyActivityLog.persona_id == persona.id,
        )
        .first()
    )
    assert log is not None


def test_update_lesson_creates_audit_log(client, db_session):
    admin, persona, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    headers = auth_headers(client, email=admin.email)
    client.patch(
        f"/api/academy/admin/lessons/{lesson.id}",
        headers=headers,
        json={"title": "Audited Lesson"},
    )
    log = (
        db_session.query(models.AcademyActivityLog)
        .filter(
            models.AcademyActivityLog.event_type == "lesson_updated",
            models.AcademyActivityLog.persona_id == persona.id,
        )
        .first()
    )
    assert log is not None
    payload = log.payload_json or {}
    assert payload.get("lesson_id") == str(lesson.id)


def test_resolve_forum_creates_audit_log(client, db_session):
    admin, persona, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id)
    thread = models.ForumThread(
        course_id=course.id,
        author_persona_id=persona.id,
        title="Log Thread",
        category="general",
        content="...",
    )
    db_session.add(thread)
    db_session.commit()
    db_session.refresh(thread)
    headers = auth_headers(client, email=admin.email)
    client.patch(f"/api/academy/forum/threads/{thread.id}/resolve", headers=headers)
    log = (
        db_session.query(models.AcademyActivityLog)
        .filter(
            models.AcademyActivityLog.event_type == "forum_resolved",
            models.AcademyActivityLog.persona_id == persona.id,
        )
        .first()
    )
    assert log is not None
    payload = log.payload_json or {}
    assert payload.get("thread_id") == str(thread.id)


# ══════════════════════════════════════════════════════════════════════════
# F. Negative / security tests
# ══════════════════════════════════════════════════════════════════════════


def test_unauthenticated_access_401(client, db_session):
    resp = client.get("/api/academy/courses")
    assert resp.status_code in (401, 403)


def test_student_cannot_access_admin_endpoints(client, db_session):
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="admin.deny.student@example.com",
        permisos={"academy:study": "allow"},
    )
    headers = auth_headers(client, email=student.email)
    resp = client.get("/api/academy/admin/submissions", headers=headers)
    assert resp.status_code == 403


def test_submit_assessment_cross_sede(client, db_session):
    sede_b_id = _uuid.uuid4()
    _, persona_st, sede_b = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="crosssede.student@example.com",
        permisos={"academy:study": "allow"},
        sede_id=sede_b_id,
    )
    admin_a, _, sede_a = seed_admin(db_session, email="crosssede.adminA@example.com")
    assert sede_a.id != sede_b.id
    course_b = _create_course(db_session, sede_id=sede_b.id)
    assessment = _create_assessment(db_session, course_b.id)
    _create_question(db_session, assessment.id)
    _create_enrollment(db_session, persona_st.id, course_b.id)
    headers_a = auth_headers(client, email=admin_a.email)
    resp = client.post(
        f"/api/academy/assessments/{assessment.id}/submit",
        headers=headers_a,
        json={},
    )
    assert resp.status_code == 404


def test_enrollment_persona_mismatch(client, db_session):
    admin, persona_admin, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="mismatch.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    headers = auth_headers(client, email=student.email)
    resp = client.post(
        "/api/academy/enrollments",
        headers=headers,
        json={
            "persona_id": str(persona_admin.id),
            "course_id": str(course.id),
        },
    )
    assert resp.status_code == 403


def test_enrollment_unpublished_course(client, db_session):
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="unpub.enroll.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id, is_published=False)
    headers = auth_headers(client, email=student.email)
    resp = client.post(
        "/api/academy/enrollments",
        headers=headers,
        json={
            "persona_id": str(persona_st.id),
            "course_id": str(course.id),
        },
    )
    assert resp.status_code == 404


# ── H-01: sede_id en el contrato de Course read ─────────────────────────────


def test_h01_course_response_exposes_sede_id(client, db_session):
    """H-01 → ``GET /api/academy/courses`` y ``GET /api/academy/courses/{id}``
    exponen ``sede_id`` (el contrato ya no depende de inferencia in-line)."""
    admin, _, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id, is_published=True)
    headers = auth_headers(client, email=admin.email)
    # List endpoint.
    resp_list = client.get("/api/academy/courses", headers=headers)
    assert resp_list.status_code == 200
    matched = [c for c in resp_list.json() if c["id"] == str(course.id)]
    assert matched, "H-01: curso creado no aparece en list"
    assert "sede_id" in matched[0], "H-01: sede_id ausente del list response"
    assert matched[0]["sede_id"] == str(sede.id)
    # Detail endpoint.
    resp_detail = client.get(f"/api/academy/courses/{course.id}", headers=headers)
    assert resp_detail.status_code == 200
    assert resp_detail.json()["sede_id"] == str(sede.id)


def test_h01_course_global_has_null_sede_id(client, db_session):
    """H-01 → cuando ``Course.sede_id IS NULL`` (global), el response
    expone ``sede_id: null`` explícitamente (no None implícito)."""
    admin, _, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=None, is_published=True)
    headers = auth_headers(client, email=admin.email)
    resp = client.get(f"/api/academy/courses/{course.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["sede_id"] is None


def test_h01_course_payload_forbids_sede_id(client, db_session):
    """H-01 principio: el cliente NO puede atribuir sede — ``CoursePayload``
    tiene ``extra="forbid"``, así que enviar ``sede_id`` en el write rechaza
    con 422. La sede la inyecta la API vía ``get_user_sede_id``."""
    admin, _, sede = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    resp = client.post(
        "/api/academy/admin/courses",
        headers=headers,
        json={
            "code": "FORBID-H01",
            "title": "Test forbid sede_id",
            "modality": "online",
            "sede_id": str(_uuid.uuid4()),
        },
    )
    assert resp.status_code == 422, (
        f"H-01: CoursePayload debe rechazar sede_id con 422 (extra=forbid), got {resp.status_code}"
    )


# ── F-02bis (2026-08-02): students_count real en el contract read (Axioma-3) ──


def test_f02bis_students_count_in_list_for_sede_course(client, db_session):
    """F-02bis → ``GET /api/academy/courses`` emite ``students_count`` real
    para un curso de la sede del Manager (count bulk, sin N+1)."""
    admin, _, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id, is_published=True)
    for i in range(2):
        _, persona_st, _ = seed_user_with_role(
            db_session,
            role_name="LECTOR",
            email=f"scount.list{i}@example.com",
            permisos={"academy:study": "allow"},
        )
        _create_enrollment(db_session, persona_st.id, course.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.get("/api/academy/courses", headers=headers)
    assert resp.status_code == 200
    matched = [c for c in resp.json() if c["id"] == str(course.id)]
    assert matched, "F-02bis: curso no aparece en list"
    assert matched[0]["students_count"] == 2, (
        f"F-02bis: students_count esperado 2, got {matched[0].get('students_count')}"
    )


def test_f02bis_students_count_in_detail_excludes_viewer(client, db_session):
    """F-02bis → ``GET /api/academy/courses/{id}`` expone ``students_count``
    con scope Axioma-3 estricto. El detalle es de sólo lectura y NO auto-inscribe
    al viewer (corrección 2026-08-03 del auto-enroll introducido en 922282e0):
    el admin que consulta el detalle sólo ve el 1 estudiante inscrito previamente,
    sin sumar su propia inscripción. Para auto-inscribirse, el actor debe usar
    POST /enrollments (rate-limit + scope + reactivación soft-delete alineados)."""
    admin, _, sede = seed_admin(db_session)
    course = _create_course(db_session, sede_id=sede.id, is_published=True)
    _, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="scount.detail@example.com",
        permisos={"academy:study": "allow"},
    )
    _create_enrollment(db_session, persona_st.id, course.id)
    headers = auth_headers(client, email=admin.email)
    resp = client.get(f"/api/academy/courses/{course.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["students_count"] == 1, (
        "F-02bis: detalle cuenta 1 estudiante inscrito; el admin viewer no se auto-inscribe"
    )


def test_f02bis_students_count_zero_for_global_course_sede_manager(client, db_session):
    """F-02bis → Axioma-3 estricto: un Manager con sede NO ve UGC de cursos
    globales (sede_id IS NULL) — ``students_count`` debe ser 0 aunque el curso
    global tenga estudiantes inscritos (homólogo de course_students)."""
    admin, _, sede = seed_admin(db_session)
    global_course = _create_course(db_session, sede_id=None, is_published=True)
    _, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="scount.global@example.com",
        permisos={"academy:study": "allow"},
    )
    _create_enrollment(db_session, persona_st.id, global_course.id)
    headers = auth_headers(client, email=admin.email)
    # List: el curso global es legible (OR global) pero el count es 0.
    resp_list = client.get("/api/academy/courses", headers=headers)
    matched = [c for c in resp_list.json() if c["id"] == str(global_course.id)]
    assert matched, "F-02bis: curso global debe ser visible en list (lectura captación)"
    assert matched[0]["students_count"] == 0, "F-02bis: global → count 0 para Manager con sede"
    # Detail: get_course ya NO auto-inscribe al admin (corrección 2026-08-03),
    # y el scope Axioma-3 sigue excluyendo el curso global del count.
    resp_detail = client.get(f"/api/academy/courses/{global_course.id}", headers=headers)
    assert resp_detail.status_code == 200
    assert resp_detail.json()["students_count"] == 0, "F-02bis: detalle global → count 0"


# ── H-02: LessonProgressResponse contract tipado ────────────────────────────


def test_h02_get_lesson_progress_contract(client, db_session):
    """H-02 → ``GET /api/academy/lessons/{id}/progress`` devuelve un dict
    conforme ``LessonProgressResponse`` con las 3 claves definidas
    (``progress_percent``, ``last_position_seconds``, ``is_completed``) y
    tipos correctos — sin progreso guardado el fallback es 0.0/0/False."""
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="h02.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    headers = auth_headers(client, email=student.email)
    resp = client.get(f"/api/academy/lessons/{lesson.id}/progress", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    # Contract LessonProgressResponse.
    assert set(data.keys()) == {"progress_percent", "last_position_seconds", "is_completed"}, (
        f"H-02: response keys no conforman LessonProgressResponse: {set(data.keys())}"
    )
    assert isinstance(data["progress_percent"], float)
    assert isinstance(data["last_position_seconds"], int)
    assert isinstance(data["is_completed"], bool)
    # Fallback sin progreso guardado.
    assert data["progress_percent"] == 0.0
    assert data["last_position_seconds"] == 0
    assert data["is_completed"] is False


def test_h02_get_lesson_progress_reflects_persisted_progress(client, db_session):
    """H-02 → cuando existe un ``LessonProgress`` persistido, el endpoint
    mapea sus columnas al contract LessonProgressResponse (antes devolvía
    el ORM row crudo que Pydantic rechazaba bajo response_model)."""
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="h02b.student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    # Persistimos un progreso directamente en DB.
    progress = models.LessonProgress(
        persona_id=persona_st.id,
        lesson_id=lesson.id,
        progress_percent=42.5,
        last_position_seconds=120,
        is_completed=False,
    )
    db_session.add(progress)
    db_session.commit()
    headers = auth_headers(client, email=student.email)
    resp = client.get(f"/api/academy/lessons/{lesson.id}/progress", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["progress_percent"] == 42.5
    assert data["last_position_seconds"] == 120
    assert data["is_completed"] is False
