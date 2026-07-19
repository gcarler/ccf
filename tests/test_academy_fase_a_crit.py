"""Fase A — ACAD-TKT-010..015 regression gates.

Estos tests son los "regression gates" permanentes para los 6 CRIT del
módulo Academy que ya estaban implementados en el código actual pero sin
cobertura de tests que detectara una regresión. El comportamiento es:

  ACAD-TKT-010 [CRIT]: submit_assessment bloqueado por scope de sede.
  ACAD-TKT-011 [CRIT]: get_lesson_progress bloqueado por lesson.deleted_at.
  ACAD-TKT-012 [CRIT]: update_lesson_progress bloqueado por sede/unpublished.
  ACAD-TKT-013 [CRIT]: submit_assessment bloqueado por course.is_published.
  ACAD-TKT-014 [CRIT]: create_assessment_admin valida lesson_id pertenece a course_id.
  ACAD-TKT-015 [CRIT]: 3 schemas Pydantic rechazan campos extra (extra="forbid").

Si alguno de estos tests falla en CI → alguien removió o debilitó la
validación del backend; el fix asociado debería reabrirse.

HISTÓRICO:
    - 2026-07-19: ACAD-TKT-010..015 cerrados funcionalmente. Drift del audit
      (PLAN_ACADEMY_CALIDAD §P0) detectado contra código real. Comportamiento
      ya implementado en backend/api/academy.py y backend/schemas/academy.py.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from backend import models
from backend.models_shared import _utcnow
from tests.conftest import auth_headers, seed_admin, seed_user_with_role

# ── Helpers ──────────────────────────────────────────────────────────


def _publish(course: models.Course) -> models.Course:
    course.is_published = True
    return course


def _publish(lesson: models.Lesson) -> models.Lesson:
    lesson.is_published = True
    return lesson


def _ensure_enrollment(
    db: Session,
    persona_id: uuid.UUID,
    course_id: uuid.UUID,
) -> models.Enrollment:
    """Crea (o reusa) una inscripción activa de un estudiante en un curso."""
    existing = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.persona_id == persona_id,
            models.Enrollment.course_id == course_id,
        )
        .first()
    )
    if existing:
        existing.deleted_at = None
        return existing
    enrollment = models.Enrollment(persona_id=persona_id, course_id=course_id)
    db.add(enrollment)
    db.commit()
    return enrollment


# ===========================================================================
# ACAD-TKT-010 — submit_assessment bloqueado por scope de sede
# ===========================================================================


def test_acad_tkt_010_submit_assessment_blocks_cross_sede(client, db_session: Session):
    """Editor/Student de sede_a NO puede submitir assessment de sede_b → 404.

    Valida Axioma 3 multi-tenant: ``_get_scoped_course`` aplica filtro de sede
    antes de cualquier lectura/escritura. Si falla, alguien debilitó el filtro.
    """
    admin_a, persona_a, sede_a = seed_admin(db_session, email="tkt010_a@example.com", password="testpass123")
    admin_b, persona_b, sede_b = seed_admin(db_session, email="tkt010_b@example.com", password="testpass123")
    assert sede_a.id != sede_b.id, "Las sedes A y B deben ser distintas para validar el scope"

    # Course + Assessment en sede_b.
    course_b = models.Course(
        code=f"T010-B-{uuid.uuid4().hex[:6]}",
        title="Course B",
        modality="online",
        sede_id=sede_b.id,
        is_published=True,
    )
    db_session.add(course_b)
    db_session.commit()

    assessment_b = models.Assessment(
        course_id=course_b.id,
        title="Assessment B",
        max_score=100,
        passing_score=70,
        is_published=True,
    )
    db_session.add(assessment_b)
    db_session.flush()

    # Pregunta vacía para que el endpoint sea ejercitable.
    question = models.AssessmentQuestion(
        assessment_id=assessment_b.id,
        question_text="Q?",
        question_type="multiple_choice",
        points=1,
        order_index=0,
    )
    db_session.add(question)
    db_session.commit()

    # Student de sede_a intenta submitir el assessment de sede_b → debe recibir 404
    # (Axioma 3: el Course no pertenece a su scope, invisible).
    headers_a = auth_headers(client, email=admin_a.email, password="testpass123")
    resp = client.post(
        f"/api/academy/assessments/{assessment_b.id}/submit",
        headers=headers_a,
        json={"answers": []},
    )
    assert resp.status_code == 404, (
        f"ACAD-TKT-010 REGRESIÓN: editor de sede_a pudo submitir assessment de sede_b "
        f"(status {resp.status_code}). Body: {resp.text}"
    )
    db_session.refresh(assessment_b)
    # No debe crearse ningún attempt.
    assert (
        db_session.query(models.AssessmentAttempt)
        .filter(models.AssessmentAttempt.assessment_id == assessment_b.id)
        .count()
    ) == 0, "ACAD-TKT-010: el attempt fue creado aunque sede_a no tiene scope"


# ===========================================================================
# ACAD-TKT-011 — get_lesson_progress bloqueado por lesson.deleted_at
# ===========================================================================


def test_acad_tkt_011_get_lesson_progress_blocks_deleted_lesson(client, db_session: Session):
    """"Lección con deleted_at setado NO debe ser visible vía progress → 404."""
    admin, _, sede = seed_admin(db_session, email="tkt011_admin@example.com", password="testpass123")
    course = models.Course(
        code=f"T011-{uuid.uuid4().hex[:6]}",
        title="Course T011",
        modality="online",
        sede_id=sede.id,
        is_published=True,
    )
    db_session.add(course)
    db_session.commit()

    lesson = models.Lesson(
        course_id=course.id,
        title="Lección archivada",
        content="x",
        order_index=1,
        is_published=True,
        deleted_at=_utcnow(),  # Soft-deleted!
    )
    db_session.add(lesson)
    db_session.commit()

    headers = auth_headers(client, email=admin.email, password="testpass123")
    resp = client.get(f"/api/academy/lessons/{lesson.id}/progress", headers=headers)
    assert resp.status_code == 404, (
        f"ACAD-TKT-011 REGRESIÓN: lección soft-deleted retornó status "
        f"{resp.status_code}. Body: {resp.text}"
    )


# ===========================================================================
# ACAD-TKT-012 — update_lesson_progress bloqueado por sede y/o is_published
# ===========================================================================


@pytest.mark.parametrize(
    "scenario,lesson_published,lesson_in_user_sede,expect_blocked_at_endpoint_or_scope",
    [
        ("unpublished_in_same_sede", False, True, True),
        ("cross_sede", True, False, True),
    ],
    ids=["unpublished_in_same_sede", "cross_sede"],
)
def test_acad_tkt_012_update_lesson_progress_blocks(
    client,
    db_session: Session,
    scenario: str,
    lesson_published: bool,
    lesson_in_user_sede: bool,
    expect_blocked_at_endpoint_or_scope: bool,
):
    """ACAD-TKT-012 (unific.): 2 sub-casos en una sola función parametrizada.

    ``unpublished_in_same_sede``: lección del propio scope pero is_published=False → 404.
    ``cross_sede``: lección de OTRA sede con is_published=True → 404 por scope.
    """
    assert expect_blocked_at_endpoint_or_scope is True, "Sanity: ambos escenarios deben bloquearse"

    if scenario == "unpublished_in_same_sede":
        admin, persona, sede = seed_admin(
            db_session, email="tkt012_unpub@example.com", password="testpass123"
        )
        course = models.Course(
            code=f"T012U-{uuid.uuid4().hex[:6]}",
            title="Course T012",
            modality="online",
            sede_id=sede.id,
            is_published=True,
        )
        db_session.add(course)
        db_session.commit()
        lesson = models.Lesson(
            course_id=course.id,
            title="Lesson draft",
            content="x",
            order_index=1,
            is_published=lesson_published,  # False
        )
        db_session.add(lesson)
        db_session.commit()
        _ensure_enrollment(db_session, persona.id, course.id)
        headers = auth_headers(client, email=admin.email, password="testpass123")
        target_lesson_id = lesson.id
    else:  # cross_sede
        admin_a, _persona_a, sede_a = seed_admin(
            db_session, email="tkt012_xsede_a@example.com", password="testpass123"
        )
        _admin_b, _persona_b, sede_b = seed_admin(
            db_session, email="tkt012_xsede_b@example.com", password="testpass123"
        )
        course_b = models.Course(
            code=f"T012XS-{uuid.uuid4().hex[:6]}",
            title="Course B",
            modality="online",
            sede_id=sede_b.id,
            is_published=True,
        )
        db_session.add(course_b)
        db_session.commit()
        lesson_b = models.Lesson(
            course_id=course_b.id,
            title="Lesson B",
            content="x",
            order_index=1,
            is_published=lesson_published,  # True en cross_sede
        )
        db_session.add(lesson_b)
        db_session.commit()
        headers = auth_headers(client, email=admin_a.email, password="testpass123")
        target_lesson_id = lesson_b.id

    resp = client.post(
        f"/api/academy/lessons/{target_lesson_id}/progress",
        headers=headers,
        json={"progress_percent": 50},
    )
    assert resp.status_code == 404, (
        f"ACAD-TKT-012[{scenario}] REGRESIÓN: lección aceptó update de progreso "
        f"(status {resp.status_code}). Body: {resp.text}"
    )


# ===========================================================================
# ACAD-TKT-013 — assessment requiere course.is_published
# ===========================================================================


def test_acad_tkt_013_submit_assessment_blocks_unpublished_course(client, db_session: Session):
    """Si course.is_published=False, submit_assessment debe retornar 404.

    Aunque el editor pueda ver courses unpublished, el estudiante NO debe
    poder submitir assessments de un curso que aún no está publicado.
    """
    student, persona_student, sede = seed_user_with_role(
        db_session,
        role_name="academy_student",
        email="tkt013_student@example.com",
        password="testpass123",
    )
    student.rol_plataforma.permisos = {"academy:study": "allow"}
    db_session.commit()

    # Sedear al admin en la misma sede del student vía asignación post-hoc
    # sobre el Usuario. ``tests/conftest.py::seed_admin`` no acepta ``sede_id``
    # kwarg de forma nativa (la propagación al modelo requeriría cambiar el
    # helper compartido, riesgo de regresión en 27+ tests que lo usan). El
    # mutador post-hoc es seguro aquí: ADMIN tiene permisos ``*`` y solo nos
    # importa que ``user.sede_id`` matchee con ``sede`` para que ``_course_scope``
    # acepte el Course con scope correcto.
    seed_admin(db_session, email="tkt013_admin@example.com", password="testpass123")
    admin_record = (
        db_session.query(models.Usuario).filter(models.Usuario.email == "tkt013_admin@example.com").first()
    )
    admin_record.sede_id = sede.id
    db_session.commit()

    course = models.Course(
        code=f"T013-{uuid.uuid4().hex[:6]}",
        title="Course Draft",
        modality="online",
        sede_id=sede.id,
        is_published=False,  # No publicado!
    )
    db_session.add(course)
    db_session.commit()

    assessment = models.Assessment(
        course_id=course.id,
        title="Assessment draft",
        max_score=100,
        passing_score=70,
        is_published=True,
    )
    db_session.add(assessment)
    db_session.flush()

    question = models.AssessmentQuestion(
        assessment_id=assessment.id,
        question_text="Q?",
        question_type="multiple_choice",
        points=1,
        order_index=0,
    )
    db_session.add(question)
    db_session.commit()

    # El student está inscripto al curso (incluso si no está publicado)
    # porque algun admin podría haberlo matriculado manualmente para testing.
    _ensure_enrollment(db_session, persona_student.id, course.id)

    headers = auth_headers(client, email="tkt013_student@example.com", password="testpass123")
    resp = client.post(
        f"/api/academy/assessments/{assessment.id}/submit",
        headers=headers,
        json={"answers": []},
    )
    assert resp.status_code == 404, (
        f"ACAD-TKT-013 REGRESIÓN: assessment de curso unpublished fue aceptado "
        f"(status {resp.status_code}). Body: {resp.text}"
    )


# ===========================================================================
# ACAD-TKT-014 — create_assessment_admin rechaza lesson_id ajeno al course_id
# ===========================================================================


def test_acad_tkt_014_create_assessment_admin_blocks_lesson_from_other_course(
    client,
    db_session: Session,
):
    """``lesson_id`` que NO pertenece a ``course_id`` → 422."""
    admin, _, sede = seed_admin(db_session, email="tkt014_admin@example.com", password="testpass123")

    course_a = models.Course(
        code=f"T014A-{uuid.uuid4().hex[:6]}",
        title="Course A",
        modality="online",
        sede_id=sede.id,
        is_published=True,
    )
    course_b = models.Course(
        code=f"T014B-{uuid.uuid4().hex[:6]}",
        title="Course B",
        modality="online",
        sede_id=sede.id,
        is_published=True,
    )
    db_session.add_all([course_a, course_b])
    db_session.commit()

    # Lección pertenece a Course B, no a Course A.
    lesson_b = models.Lesson(
        course_id=course_b.id,
        title="Lesson B",
        content="x",
        order_index=1,
        is_published=True,
    )
    db_session.add(lesson_b)
    db_session.commit()

    headers = auth_headers(client, email=admin.email, password="testpass123")
    resp = client.post(
        "/api/academy/admin/assessments",
        headers=headers,
        json={
            "course_id": str(course_a.id),
            "lesson_id": str(lesson_b.id),  # Lesson B no pertenece a Course A
            "title": "Crafty assessment",
            "questions": [],
        },
    )
    assert resp.status_code == 422, (
        f"ACAD-TKT-014 REGRESIÓN: create_assessment_admin aceptó lesson_id de OTRO course "
        f"(status {resp.status_code}). Body: {resp.text}"
    )
    assert "pertenece" in resp.text or "lesson" in resp.text.lower(), (
        f"ACAD-TKT-014: el mensaje de error debería mencionar la lesson. body={resp.text}"
    )


# ===========================================================================
# ACAD-TKT-015 — extra="forbid" en AssessmentAttemptSubmit, EnrollmentCreate, ForumThreadCreate
# ===========================================================================


@pytest.mark.parametrize(
    "extra_field",
    ["hacked_field", "is_legacy_admin", "force_publish", "__proto__"],
    ids=["hacked_field", "is_legacy_admin", "force_publish", "dunder_proto"],
)
def test_acad_tkt_015_extra_forbid_assessment_submit(client, db_session: Session, extra_field):
    """AssessmentAttemptSubmit rechaza cualquier campo extra → 422.

    Parametrizado para cubrir al menos 4 vectores comunes de ataque/abuso:
    campos snake_case normales, indicaciones de admin, palabras clave,
    y atributos dunder que pasan desapercibidos en code review.
    """
    admin, _, _ = seed_admin(db_session, email=f"tkt015a_{extra_field}@example.com", password="testpass123")
    headers = auth_headers(client, email=admin.email, password="testpass123")

    # assessment_id random; Pydantic debe rechazar ANTES por el campo extra.
    assessment_id = str(uuid.uuid4())
    payload: dict = {
        "answers": [],
        extra_field: True,  # Campo parametrizado → rechazado por extra="forbid".
    }
    resp = client.post(
        f"/api/academy/assessments/{assessment_id}/submit",
        headers=headers,
        json=payload,
    )
    assert resp.status_code == 422, (
        f"ACAD-TKT-015 (AssessmentAttemptSubmit) REGRESIÓN: campo extra '{extra_field}' aceptado "
        f"(status {resp.status_code}). Body: {resp.text}"
    )


@pytest.mark.parametrize(
    "extra_field",
    ["hacked_field", "is_legacy_admin", "force_publish", "__proto__"],
    ids=["hacked_field", "is_legacy_admin", "force_publish", "dunder_proto"],
)
def test_acad_tkt_015_extra_forbid_enrollment_create(
    client, db_session: Session, extra_field
):
    """EnrollmentCreate rechaza cualquier campo extra → 422 (4 vectores)."""
    student, persona, sede = seed_user_with_role(
        db_session,
        role_name="academy_student",
        email=f"tkt015b_{extra_field}@example.com",
        password="testpass123",
    )
    student.rol_plataforma.permisos = {"academy:study": "allow"}
    db_session.commit()

    course = models.Course(
        code=f"T015B-{uuid.uuid4().hex[:6]}",
        title="Course",
        modality="online",
        sede_id=sede.id,
        is_published=True,
    )
    db_session.add(course)
    db_session.commit()

    headers = auth_headers(client, email=student.email, password="testpass123")
    resp = client.post(
        "/api/academy/enrollments",
        headers=headers,
        json={
            "persona_id": str(persona.id),
            "course_id": str(course.id),
            extra_field: True,  # Parametrizado → 422
        },
    )
    assert resp.status_code == 422, (
        f"ACAD-TKT-015 (EnrollmentCreate['{extra_field}']) REGRESIÓN: campo extra aceptado "
        f"(status {resp.status_code}). Body: {resp.text}"
    )


@pytest.mark.parametrize(
    "extra_field",
    ["hacked_field", "is_legacy_admin", "force_publish", "__proto__"],
    ids=["hacked_field", "is_legacy_admin", "force_publish", "dunder_proto"],
)
def test_acad_tkt_015_extra_forbid_forum_thread_create(
    client, db_session: Session, extra_field
):
    """ForumThreadCreate rechaza cualquier campo extra → 422 (4 vectores).

    ForumThreadCreate hereda ``extra="forbid"`` de ``ForumThreadBase``.
    El admin puede crear el hilo global, por lo que este caso no se mezcla con
    el guard de autorización de hilos globales.
    """
    admin, _, _ = seed_admin(db_session, email=f"tkt015c_{extra_field}@example.com", password="testpass123")
    headers = auth_headers(client, email=admin.email, password="testpass123")

    resp = client.post(
        "/api/academy/forum/threads",
        headers=headers,
        json={
            "title": "Hilo para validar extra=forbid",
            "category": "general",
            "course_id": None,  # Hilo global requiere academy:edit/manage (admin * pasa).
            "content": "Contenido de prueba",
            extra_field: True,  # Parametrizado → 422
        },
    )
    assert resp.status_code == 422, (
        f"ACAD-TKT-015 (ForumThreadCreate['{extra_field}']) REGRESIÓN: campo extra aceptado "
        f"(status {resp.status_code}). Body: {resp.text}"
    )
