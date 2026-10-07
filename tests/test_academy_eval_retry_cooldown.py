"""Tests for TKT-ACADEMY-EVAL-RETRY-POLICIES-01:
Assessment retry policies, cooldown enforcement, attempt status and video playback position tracking.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import uuid as _uuid

import pytest
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.models_shared import _utcnow
from tests.conftest import auth_headers, seed_admin, seed_user_with_role


def _create_course(db_session, *, sede_id=None, is_published=True):
    course = models.Course(
        code=f"ACAD-TKT-{_uuid.uuid4().hex[:8]}",
        title=f"Course {_uuid.uuid4().hex[:6]}",
        modality="online",
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
        content="Contenido de video",
        content_type="video",
        order_index=order_index,
        is_published=is_published,
    )
    db_session.add(lesson)
    db_session.commit()
    db_session.refresh(lesson)
    return lesson


def _create_assessment(
    db_session,
    course_id,
    *,
    lesson_id=None,
    title=None,
    max_attempts=3,
    cooldown_minutes=60,
    passing_score=70,
    is_published=True,
):
    assessment = models.Assessment(
        course_id=course_id,
        lesson_id=lesson_id,
        title=title or f"Assessment {_uuid.uuid4().hex[:6]}",
        passing_score=passing_score,
        max_score=100,
        max_attempts=max_attempts,
        cooldown_minutes=cooldown_minutes,
        is_published=is_published,
    )
    db_session.add(assessment)
    db_session.commit()
    db_session.refresh(assessment)
    return assessment


def _create_question(db_session, assessment_id, *, text="¿Pregunta de examen?", points=10):
    q = models.AssessmentQuestion(
        assessment_id=assessment_id,
        question_text=text,
        question_type="multiple_choice",
        points=points,
        order_index=1,
    )
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)
    return q


def _create_option(db_session, question_id, *, text="Opción", is_correct=False):
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
    enrollment = models.Enrollment(
        persona_id=persona_id,
        course_id=course_id,
        status="active",
        progress_percent=0.0,
    )
    db_session.add(enrollment)
    db_session.commit()
    db_session.refresh(enrollment)
    return enrollment


# ===========================================================================
# 1. Modelos y Schemas con max_attempts y cooldown_minutes
# ===========================================================================


def test_assessment_model_and_schema_defaults(db_session: Session):
    """Verifica que el modelo y schemas de Assessment contengan max_attempts y cooldown_minutes."""
    course = _create_course(db_session)
    assessment = models.Assessment(
        course_id=course.id,
        title="Test Defaults Assessment",
        passing_score=70,
    )
    db_session.add(assessment)
    db_session.commit()
    db_session.refresh(assessment)

    assert assessment.max_attempts == 3
    assert assessment.cooldown_minutes == 60

    # Schema Pydantic
    schema_obj = schemas.Assessment.model_validate(assessment)
    assert schema_obj.max_attempts == 3
    assert schema_obj.cooldown_minutes == 60


def test_admin_create_and_update_assessment_policies(client, db_session: Session):
    """Admin puede configurar max_attempts y cooldown_minutes al crear y actualizar evaluaciones."""
    admin, _, sede = seed_admin(db_session, email="policy_admin@example.com")
    course = _create_course(db_session, sede_id=sede.id)

    headers = auth_headers(client, email=admin.email)

    # 1. Crear evaluación con políticas custom
    payload = {
        "course_id": str(course.id),
        "title": "Examen con cooldown y límite",
        "passing_score": 80.0,
        "max_attempts": 2,
        "cooldown_minutes": 30,
        "questions": [
            {
                "text": "Pregunta 1",
                "type": "multiple_choice",
                "points": 10,
                "options": ["A", "B"],
                "correct_option": 0,
            }
        ],
    }
    resp = client.post("/api/academy/admin/assessments", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["max_attempts"] == 2
    assert data["cooldown_minutes"] == 30
    assessment_id = data["id"]

    # 2. Actualizar políticas vía PATCH
    update_payload = {
        "max_attempts": 5,
        "cooldown_minutes": 15,
    }
    patch_resp = client.patch(
        f"/api/academy/admin/assessments/{assessment_id}",
        headers=headers,
        json=update_payload,
    )
    assert patch_resp.status_code == 200, patch_resp.text
    updated_data = patch_resp.json()
    assert updated_data["max_attempts"] == 5
    assert updated_data["cooldown_minutes"] == 15


# ===========================================================================
# 2. Endpoint de registro de posición de video por lección
# ===========================================================================


def test_record_video_position_multidevice(client, db_session: Session):
    """POST /lessons/{lesson_id}/video-position persiste timestamp de reproducción y actualiza progreso."""
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="videostudent@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    _create_enrollment(db_session, persona_st.id, course.id)

    headers = auth_headers(client, email=student.email)

    # 1. Registrar posición inicial (segundo 45 de 180 = 25%)
    resp = client.post(
        f"/api/academy/lessons/{lesson.id}/video-position",
        headers=headers,
        json={"position_seconds": 45, "total_seconds": 180},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["last_position_seconds"] == 45
    assert data["progress_percent"] == 25.0
    assert data["is_completed"] is False

    # 2. Verificar persistencia en base de datos
    prog_db = (
        db_session.query(models.LessonProgress)
        .filter_by(persona_id=persona_st.id, lesson_id=lesson.id)
        .first()
    )
    assert prog_db is not None
    assert prog_db.last_position_seconds == 45

    # 3. Retomar en multidispositivo y completar video (segundo 180 de 180 = 100%)
    resp2 = client.post(
        f"/api/academy/lessons/{lesson.id}/video-position",
        headers=headers,
        json={"position_seconds": 180, "total_seconds": 180},
    )
    assert resp2.status_code == 200, resp2.text
    data2 = resp2.json()
    assert data2["last_position_seconds"] == 180
    assert data2["progress_percent"] == 100.0
    assert data2["is_completed"] is True


def test_record_video_position_requires_enrollment(client, db_session: Session):
    """Estudiante no inscrito en el curso no puede registrar posición de video (403)."""
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="unregistered_video@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)

    headers = auth_headers(client, email=student.email)
    resp = client.post(
        f"/api/academy/lessons/{lesson.id}/video-position",
        headers=headers,
        json={"position_seconds": 30},
    )
    assert resp.status_code == 403


# ===========================================================================
# 3. Bloqueo automático de reintento si no cumple ventana de enfriamiento o límite
# ===========================================================================


def test_assessment_cooldown_blocking(client, db_session: Session):
    """Reintento inmediato dentro de la ventana de enfriamiento es bloqueado con HTTP 429."""
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="cooldown_student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    assessment = _create_assessment(
        db_session,
        course.id,
        max_attempts=3,
        cooldown_minutes=60,
        passing_score=80,
    )
    q = _create_question(db_session, assessment.id, points=10)
    opt_wrong = _create_option(db_session, q.id, text="Incorrecta", is_correct=False)
    _create_enrollment(db_session, persona_st.id, course.id)

    headers = auth_headers(client, email=student.email)

    # Intento 1: se ejecuta normalmente
    resp1 = client.post(
        f"/api/academy/assessments/{assessment.id}/submit",
        headers=headers,
        json={"answers": [{"question_id": str(q.id), "selected_option_id": str(opt_wrong.id)}]},
    )
    assert resp1.status_code == 200, resp1.text
    assert resp1.json()["passed"] is False

    # Intento 2 inmediato: debe ser bloqueado por cooldown (HTTP 429)
    resp2 = client.post(
        f"/api/academy/assessments/{assessment.id}/submit",
        headers=headers,
        json={"answers": [{"question_id": str(q.id), "selected_option_id": str(opt_wrong.id)}]},
    )
    assert resp2.status_code == 429, f"Esperado 429, recibido {resp2.status_code}: {resp2.text}"
    assert "enfriamiento" in resp2.json()["detail"].lower()
    assert "retry-after" in [k.lower() for k in resp2.headers.keys()]


def test_assessment_cooldown_allows_submission_after_window_expires(client, db_session: Session):
    """Una vez vencida la ventana de enfriamiento, el siguiente reintento es permitido."""
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="cooldown_passed@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    assessment = _create_assessment(
        db_session,
        course.id,
        max_attempts=3,
        cooldown_minutes=60,
    )
    q = _create_question(db_session, assessment.id, points=10)
    opt_correct = _create_option(db_session, q.id, text="Correcta", is_correct=True)
    enrollment = _create_enrollment(db_session, persona_st.id, course.id)

    headers = auth_headers(client, email=student.email)

    # Intento 1: registrado hace 75 minutos en el pasado (> 60 min cooldown)
    past_time = datetime.now(timezone.utc) - timedelta(minutes=75)
    attempt1 = models.AssessmentAttempt(
        assessment_id=assessment.id,
        enrollment_id=enrollment.id,
        score=40.0,
        passed=False,
        submitted_at=past_time,
    )
    db_session.add(attempt1)
    db_session.commit()

    # Intento 2 actual: cooldown superado, debe procesarse exitosamente
    resp2 = client.post(
        f"/api/academy/assessments/{assessment.id}/submit",
        headers=headers,
        json={"answers": [{"question_id": str(q.id), "selected_option_id": str(opt_correct.id)}]},
    )
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["score"] == 100.0
    assert resp2.json()["passed"] is True


def test_assessment_max_attempts_blocking(client, db_session: Session):
    """Superar el límite de intentos (max_attempts) es bloqueado con HTTP 422."""
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="max_attempts@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    assessment = _create_assessment(
        db_session,
        course.id,
        max_attempts=2,
        cooldown_minutes=0,  # Sin cooldown para probar estrictamente max_attempts
    )
    q = _create_question(db_session, assessment.id, points=10)
    opt = _create_option(db_session, q.id, text="Op", is_correct=False)
    _create_enrollment(db_session, persona_st.id, course.id)

    headers = auth_headers(client, email=student.email)

    # Intento 1 de 2: OK
    r1 = client.post(
        f"/api/academy/assessments/{assessment.id}/submit",
        headers=headers,
        json={"answers": [{"question_id": str(q.id), "selected_option_id": str(opt.id)}]},
    )
    assert r1.status_code == 200

    # Intento 2 de 2: OK
    r2 = client.post(
        f"/api/academy/assessments/{assessment.id}/submit",
        headers=headers,
        json={"answers": [{"question_id": str(q.id), "selected_option_id": str(opt.id)}]},
    )
    assert r2.status_code == 200

    # Intento 3 (excede max_attempts=2): HTTP 422
    r3 = client.post(
        f"/api/academy/assessments/{assessment.id}/submit",
        headers=headers,
        json={"answers": [{"question_id": str(q.id), "selected_option_id": str(opt.id)}]},
    )
    assert r3.status_code == 422, f"Esperado 422, recibido {r3.status_code}: {r3.text}"
    assert "límite máximo" in r3.json()["detail"].lower()


# ===========================================================================
# 4. Consulta de estado de intentos (GET attempt-status)
# ===========================================================================


def test_get_assessment_attempt_status(client, db_session: Session):
    """GET /assessments/{assessment_id}/attempt-status devuelve contadores y estado de cooldown."""
    admin, _, sede = seed_admin(db_session)
    student, persona_st, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="status_student@example.com",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    assessment = _create_assessment(
        db_session,
        course.id,
        max_attempts=3,
        cooldown_minutes=60,
    )
    _create_enrollment(db_session, persona_st.id, course.id)

    headers = auth_headers(client, email=student.email)

    # Antes de cualquier intento
    resp = client.get(f"/api/academy/assessments/{assessment.id}/attempt-status", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["max_attempts"] == 3
    assert data["attempts_count"] == 0
    assert data["attempts_remaining"] == 3
    assert data["in_cooldown"] is False
    assert data["can_attempt"] is True


# ===========================================================================
# 5. Regla canónica: Zero modales centrados (uso exclusivo de Drawers)
# ===========================================================================


def test_academy_frontend_zero_centered_modals():
    """Verifica que ningún componente de academia utilice AlertDialog o modales centrados."""
    academy_components_dir = Path(__file__).resolve().parent.parent / "frontend" / "src" / "components" / "academy"
    forbidden_pattern = re.compile(r"\b(AlertDialog|ModalContent|ModalOverlay|CenteredModal)\b")

    violations = []
    for tsx_file in academy_components_dir.glob("*.tsx"):
        content = tsx_file.read_text(encoding="utf-8")
        if forbidden_pattern.search(content):
            violations.append(str(tsx_file.name))

    assert not violations, (
        f"Regla canónica violada: se detectaron modales centrados o AlertDialog en componentes de academia: {violations}. "
        f"Todos los flujos deben usar Drawers / RightPanel."
    )
