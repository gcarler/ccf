"""Cierre de brechas de test de Academy F-01..F-10 (2026-08-02).

Este archivo cubre las brechas runtime que el backlog de Academy documenta:

- F-01  upload de tareas (submit-assignment): happy path, tipo no permitido,
        límite de tamaño y ownership (enrollment ajeno).
- F-02  ``course_students``: aislamiento cross-sede (404 para curso de otra sede).
- F-03  ``personas``: scope por sede, filtro role e is_active real (auth_users).
- F-04  mutaciones de foro cross-sede: resolve/comment/thread con course de
        otra sede → 404; thread global por estudiante → 403.
- F-05  RBAC negativo: reader no escribe, editor no archiva, student no califica.
- F-06  IDOR en progreso y submit: ownership estricto por persona.
- F-09  soft-delete de enrollments: oculto en me/enrollments, enrollments
        (admin) y me/progress.
- F-10  schemas dedicados AcademyActivityLog + FormalActaEntry.

F-07 (dashboard_metrics con date_trunc en SQLite) y F-08 (bypass manager en
rate limit) se cierran en sus archivos existentes (test_academy_comprehensive.py
y test_academy_fase_7_transversal.py respectivamente).
"""

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


def _create_enrollment(db_session, persona_id, course_id):
    enrollment = models.Enrollment(persona_id=persona_id, course_id=course_id)
    db_session.add(enrollment)
    db_session.commit()
    db_session.refresh(enrollment)
    return enrollment


def _fake_save_file(content: bytes, filename: str, subfolder: str = "general") -> str:
    """Sustituye ``storage_service.save_file_original`` (no escribe disco)."""
    return f"/api/static/{subfolder}/{filename}"


# ── F-01: upload de tareas ───────────────────────────────────────────────


def test_f01_upload_assignment_happy_path(client, db_session, monkeypatch):
    from backend.core.storage import storage_service

    monkeypatch.setattr(storage_service, "save_file_original", _fake_save_file)
    student, persona, sede = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f01.happy@example.com",
        password="testpass123",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    enrollment = _create_enrollment(db_session, persona.id, course.id)
    headers = auth_headers(client, email=student.email)

    resp = client.post(
        f"/api/academy/lessons/{lesson.id}/submit-assignment",
        headers=headers,
        data={"enrollment_id": str(enrollment.id), "comment": "Mi tarea"},
        files={"file": ("tarea.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["enrollment_id"] == str(enrollment.id)
    assert body["lesson_id"] == str(lesson.id)
    assert body["file_url"].startswith("/api/static/academy/")
    assert body["comment"] == "Mi tarea"
    # Persistencia real: la entrega quedó escrita en DB, no solo serializada.
    row = (
        db_session.query(models.AssignmentSubmission)
        .filter(models.AssignmentSubmission.enrollment_id == enrollment.id)
        .first()
    )
    assert row is not None, "La submission no fue persistida en la base de datos"
    assert row.file_url.startswith("/api/static/academy/")


def test_f01_upload_rejects_disallowed_mime(client, db_session, monkeypatch):
    from backend.core.storage import storage_service

    monkeypatch.setattr(storage_service, "save_file_original", _fake_save_file)
    student, persona, sede = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f01.mime@example.com",
        password="testpass123",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    enrollment = _create_enrollment(db_session, persona.id, course.id)
    headers = auth_headers(client, email=student.email)

    resp = client.post(
        f"/api/academy/lessons/{lesson.id}/submit-assignment",
        headers=headers,
        data={"enrollment_id": str(enrollment.id)},
        files={"file": ("malware.exe", b"MZ...", "application/x-msdownload")},
    )
    assert resp.status_code == 422, resp.text
    assert "Tipo de archivo no permitido" in resp.text


def test_f01_upload_rejects_oversize(client, db_session, monkeypatch):
    from backend.core.storage import storage_service

    monkeypatch.setattr(storage_service, "save_file_original", _fake_save_file)
    student, persona, sede = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f01.size@example.com",
        password="testpass123",
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    enrollment = _create_enrollment(db_session, persona.id, course.id)
    headers = auth_headers(client, email=student.email)

    big = b"x" * (10 * 1024 * 1024 + 1)
    resp = client.post(
        f"/api/academy/lessons/{lesson.id}/submit-assignment",
        headers=headers,
        data={"enrollment_id": str(enrollment.id)},
        files={"file": ("grande.pdf", big, "application/pdf")},
    )
    assert resp.status_code == 422, resp.text
    assert "excede el límite de 10 MB" in resp.text


def test_f01_upload_rejects_foreign_enrollment(client, db_session, monkeypatch):
    from backend.core.storage import storage_service

    monkeypatch.setattr(storage_service, "save_file_original", _fake_save_file)
    owner, owner_persona, sede = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f01.owner@example.com",
        password="testpass123",
        permisos={"academy:study": "allow"},
    )
    intruder, _, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f01.intruder@example.com",
        password="testpass123",
        sede_id=sede.id,
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    owner_enrollment = _create_enrollment(db_session, owner_persona.id, course.id)
    headers = auth_headers(client, email=intruder.email)

    resp = client.post(
        f"/api/academy/lessons/{lesson.id}/submit-assignment",
        headers=headers,
        data={"enrollment_id": str(owner_enrollment.id)},
        files={"file": ("tarea.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert resp.status_code == 404, resp.text


# ── F-02: course_students cross-sede ─────────────────────────────────────


def test_f02_course_students_cross_sede_404(client, db_session):
    admin_a, _, sede_a = seed_admin(db_session, email="f02.adminA@example.com")
    _, _, sede_b = seed_admin(db_session, email="f02.adminB@example.com")
    assert sede_a.id != sede_b.id
    course_b = _create_course(db_session, sede_id=sede_b.id)
    headers_a = auth_headers(client, email=admin_a.email)

    resp = client.get(f"/api/academy/admin/courses/{course_b.id}/students", headers=headers_a)
    assert resp.status_code == 404, resp.text


def test_f02_course_students_own_sede_ok(client, db_session):
    admin_a, _, sede_a = seed_admin(db_session, email="f02.adminA@example.com")
    student, persona, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f02.student@example.com",
        password="testpass123",
        sede_id=sede_a.id,
        permisos={"academy:study": "allow"},
    )
    course_a = _create_course(db_session, sede_id=sede_a.id)
    _create_enrollment(db_session, persona.id, course_a.id)
    headers_a = auth_headers(client, email=admin_a.email)

    resp = client.get(f"/api/academy/admin/courses/{course_a.id}/students", headers=headers_a)
    assert resp.status_code == 200, resp.text
    emails = {row["email"] for row in resp.json()}
    assert student.email in emails


def test_f02_course_students_global_course_hidden_for_sede_manager(client, db_session):
    """I-03/A-03: un Manager con sede NO ve enrollments de cursos globales.

    El curso global es legible (``_get_scoped_course`` usa ``OR sede_id IS NULL``
    para captación/lectura) pero el listado admin es estricto Axioma-3: respuesta
    200 con lista VACÍA. Esto no es un bug: es la decisión documentada en
    erroresacademia.md I-02/I-03 (homologada con ``all_enrollments``).
    """
    admin_a, _, sede_a = seed_admin(db_session, email="f02.globalMgr@example.com")
    _student, persona, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f02.globalStu@example.com",
        password="testpass123",
        sede_id=sede_a.id,
        permisos={"academy:study": "allow"},
    )
    global_course = _create_course(db_session, sede_id=None)  # curso global
    _create_enrollment(db_session, persona.id, global_course.id)
    # No-vacuidad: el enrollment SÍ existe en DB — el 200+vacío viene de la
    # exclusión Axioma-3, no de un helper que falló silenciosamente.
    assert (
        db_session.query(models.Enrollment)
        .filter(models.Enrollment.course_id == global_course.id)
        .count()
        == 1
    )
    headers_a = auth_headers(client, email=admin_a.email)

    resp = client.get(f"/api/academy/admin/courses/{global_course.id}/students", headers=headers_a)
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


# ── F-03: personas (sede / role / is_active) ─────────────────────────────


def test_f03_personas_scoped_by_sede(client, db_session):
    admin_a, _, sede_a = seed_admin(db_session, email="f03.adminA@example.com")
    _, _, sede_b = seed_admin(db_session, email="f03.adminB@example.com")
    user_a, persona_a, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f03.userA@example.com",
        password="testpass123",
        sede_id=sede_a.id,
        permisos={"academy:read": "allow"},
    )
    user_b, _, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f03.userB@example.com",
        password="testpass123",
        sede_id=sede_b.id,
        permisos={"academy:read": "allow"},
    )
    headers_a = auth_headers(client, email=admin_a.email)

    resp = client.get("/api/academy/personas", headers=headers_a)
    assert resp.status_code == 200, resp.text
    emails = {row["email"] for row in resp.json()}
    assert user_a.email in emails
    assert user_b.email not in emails, "Fuga cross-sede: admin A ve persona de sede B"
    assert persona_a.email in emails


def test_f03_personas_role_filter(client, db_session):
    from backend.models_auth import RolPlataforma, UsuarioRolModulo

    admin, _, sede = seed_admin(db_session, email="f03.admin@example.com")
    student, persona, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f03.rolefilter@example.com",
        password="testpass123",
        sede_id=sede.id,
        permisos={"academy:study": "allow"},
    )
    role = db_session.query(RolPlataforma).filter(RolPlataforma.nombre == "LECTOR").first()
    assert role is not None
    db_session.add(
        UsuarioRolModulo(user_id=persona.id, modulo="academy", rol_id=role.id)
    )
    db_session.commit()
    headers = auth_headers(client, email=admin.email)

    resp = client.get("/api/academy/personas?role=LECTOR", headers=headers)
    assert resp.status_code == 200, resp.text
    emails = {row["email"] for row in resp.json()}
    assert student.email in emails
    # El admin no tiene el rol LECTOR vía UsuarioRolModulo → no debe aparecer.
    assert admin.email not in emails


def test_f03_personas_reflects_is_active(client, db_session):
    admin, _, sede = seed_admin(db_session, email="f03.admin@example.com")
    user, _, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f03.inactive@example.com",
        password="testpass123",
        sede_id=sede.id,
        permisos={"academy:study": "allow"},
    )
    user.is_active = False
    db_session.commit()
    headers = auth_headers(client, email=admin.email)

    resp = client.get("/api/academy/personas", headers=headers)
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json() if r["email"] == "f03.inactive@example.com")
    assert row["is_active"] is False


# ── F-04: mutaciones de foro cross-sede ──────────────────────────────────


def test_f04_forum_resolve_cross_sede_404(client, db_session):
    editor_a, persona_a, sede_a = seed_admin(db_session, email="f04.editorA@example.com")
    _, persona_b, sede_b = seed_admin(db_session, email="f04.editorB@example.com")
    course_b = _create_course(db_session, sede_id=sede_b.id)
    thread_b = models.ForumThread(
        course_id=course_b.id,
        author_persona_id=persona_b.id,
        title="Thread B",
        category="general",
        content="Contenido B",
    )
    db_session.add(thread_b)
    db_session.commit()
    headers_a = auth_headers(client, email=editor_a.email)

    resp = client.patch(f"/api/academy/forum/threads/{thread_b.id}/resolve", headers=headers_a)
    assert resp.status_code == 404, resp.text


def test_f04_forum_comment_cross_sede_404(client, db_session):
    student_a, _, sede_a = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f04.studentA@example.com",
        password="testpass123",
        sede_id=None,
        permisos={"academy:study": "allow"},
    )
    _, persona_b, sede_b = seed_admin(db_session, email="f04.editorB@example.com")
    course_b = _create_course(db_session, sede_id=sede_b.id)
    thread_b = models.ForumThread(
        course_id=course_b.id,
        author_persona_id=persona_b.id,
        title="Thread B",
        category="general",
        content="Contenido B",
    )
    db_session.add(thread_b)
    db_session.commit()
    headers_a = auth_headers(client, email=student_a.email)

    resp = client.post(
        f"/api/academy/forum/threads/{thread_b.id}/comments",
        headers=headers_a,
        json={"content": "Hola desde sede A"},
    )
    assert resp.status_code == 404, resp.text


def test_f04_forum_create_thread_cross_sede_404(client, db_session):
    admin_a, _, sede_a = seed_admin(db_session, email="f04.editorA@example.com")
    _, _, sede_b = seed_admin(db_session, email="f04.editorB@example.com")
    course_b = _create_course(db_session, sede_id=sede_b.id)
    headers_a = auth_headers(client, email=admin_a.email)

    resp = client.post(
        "/api/academy/forum/threads",
        headers=headers_a,
        json={
            "title": "Hilo cross-sede",
            "category": "general",
            "content": "No debería crearse",
            "course_id": str(course_b.id),
        },
    )
    assert resp.status_code == 404, resp.text


def test_f04_student_cannot_create_global_thread(client, db_session):
    student, _, sede = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f04.student@example.com",
        password="testpass123",
        permisos={"academy:study": "allow"},
    )
    headers = auth_headers(client, email=student.email)

    resp = client.post(
        "/api/academy/forum/threads",
        headers=headers,
        json={"title": "Anuncio global", "category": "announcement", "content": "X"},
    )
    assert resp.status_code == 403, resp.text


# ── F-05: RBAC negativo ──────────────────────────────────────────────────


def test_f05_reader_cannot_create_course(client, db_session):
    reader, _, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f05.reader@example.com",
        password="testpass123",
        permisos={"academy:read": "allow"},
    )
    headers = auth_headers(client, email=reader.email)

    resp = client.post(
        "/api/academy/admin/courses",
        headers=headers,
        json={"code": "READ-NO", "title": "No crear", "modality": "online"},
    )
    assert resp.status_code == 403, resp.text


def test_f05_editor_cannot_archive_course(client, db_session):
    admin, _, sede = seed_admin(db_session, email="f05.admin@example.com")
    editor, _, _ = seed_user_with_role(
        db_session,
        role_name="DOCENTE",
        email="f05.editor@example.com",
        password="testpass123",
        sede_id=sede.id,
        permisos={"academy:edit": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    headers = auth_headers(client, email=editor.email)

    resp = client.delete(f"/api/academy/admin/courses/{course.id}", headers=headers)
    assert resp.status_code == 403, resp.text


def test_f05_student_cannot_grade_submission(client, db_session):
    admin, _, sede = seed_admin(db_session, email="f05.admin@example.com")
    student, persona, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f05.student@example.com",
        password="testpass123",
        sede_id=sede.id,
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    enrollment = _create_enrollment(db_session, persona.id, course.id)
    submission = models.AssignmentSubmission(
        enrollment_id=enrollment.id, lesson_id=lesson.id, file_url="/api/static/academy/x.pdf"
    )
    db_session.add(submission)
    db_session.commit()
    headers = auth_headers(client, email=student.email)

    resp = client.patch(
        f"/api/academy/admin/submissions/{submission.id}/grade",
        headers=headers,
        json={"grade": 90, "feedback": "Bien"},
    )
    assert resp.status_code == 403, resp.text


# ── F-06: IDOR en progreso y submit ──────────────────────────────────────


def test_f06_progress_requires_enrollment(client, db_session):
    student_a, persona_a, sede = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f06.studentA@example.com",
        password="testpass123",
        permisos={"academy:study": "allow"},
    )
    student_b, _, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f06.studentB@example.com",
        password="testpass123",
        sede_id=sede.id,
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    _create_enrollment(db_session, persona_a.id, course.id)
    headers_b = auth_headers(client, email=student_b.email)

    # B no está inscrito → 403 (no IDOR: no puede escribir progreso ajeno)
    resp = client.post(
        f"/api/academy/lessons/{lesson.id}/progress",
        headers=headers_b,
        json={"progress_percent": 100, "last_position_seconds": 10},
    )
    assert resp.status_code == 403, resp.text


def test_f06_progress_read_returns_own_only(client, db_session):
    student_a, persona_a, sede = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f06.studentA@example.com",
        password="testpass123",
        permisos={"academy:study": "allow"},
    )
    student_b, _, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f06.studentB@example.com",
        password="testpass123",
        sede_id=sede.id,
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    _create_enrollment(db_session, persona_a.id, course.id)
    _create_enrollment(db_session, student_b.id, course.id)
    headers_a = auth_headers(client, email=student_a.email)
    headers_b = auth_headers(client, email=student_b.email)

    resp_a = client.post(
        f"/api/academy/lessons/{lesson.id}/progress",
        headers=headers_a,
        json={"progress_percent": 100, "last_position_seconds": 10},
    )
    assert resp_a.status_code == 200, resp_a.text

    # B lee el mismo lesson → debe ver SU progreso (0), no el 100 de A.
    resp_b = client.get(f"/api/academy/lessons/{lesson.id}/progress", headers=headers_b)
    assert resp_b.status_code == 200, resp_b.text
    body = resp_b.json()
    assert body["progress_percent"] == 0.0
    assert body["is_completed"] is False


def test_f06_submit_foreign_enrollment_404(client, db_session, monkeypatch):
    from backend.core.storage import storage_service

    monkeypatch.setattr(storage_service, "save_file_original", _fake_save_file)
    owner, owner_persona, sede = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f06.owner@example.com",
        password="testpass123",
        permisos={"academy:study": "allow"},
    )
    intruder, _, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f06.intruder@example.com",
        password="testpass123",
        sede_id=sede.id,
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    lesson = _create_lesson(db_session, course.id)
    owner_enrollment = _create_enrollment(db_session, owner_persona.id, course.id)
    headers = auth_headers(client, email=intruder.email)

    resp = client.post(
        f"/api/academy/lessons/{lesson.id}/submit-assignment",
        headers=headers,
        data={"enrollment_id": str(owner_enrollment.id)},
        files={"file": ("tarea.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert resp.status_code == 404, resp.text


# ── F-09: soft-delete de enrollments ─────────────────────────────────────


def test_f09_soft_deleted_enrollment_hidden_from_me_enrollments(client, db_session):
    admin, _, sede = seed_admin(db_session, email="f09.admin@example.com")
    student, persona, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f09.student@example.com",
        password="testpass123",
        sede_id=sede.id,
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    enrollment = _create_enrollment(db_session, persona.id, course.id)
    headers = auth_headers(client, email=student.email)

    # Visible antes del soft-delete
    resp = client.get("/api/academy/me/enrollments", headers=headers)
    assert resp.status_code == 200, resp.text
    assert any(e["course_id"] == str(course.id) for e in resp.json())

    enrollment.deleted_at = _utcnow()
    db_session.commit()

    resp = client.get("/api/academy/me/enrollments", headers=headers)
    assert resp.status_code == 200, resp.text
    assert not any(e["course_id"] == str(course.id) for e in resp.json())


def test_f09_soft_deleted_enrollment_hidden_from_all_enrollments(client, db_session):
    admin, _, sede = seed_admin(db_session, email="f09.admin@example.com")
    student, persona, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f09.student@example.com",
        password="testpass123",
        sede_id=sede.id,
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    enrollment = _create_enrollment(db_session, persona.id, course.id)
    headers = auth_headers(client, email=admin.email)

    resp = client.get("/api/academy/enrollments", headers=headers)
    assert resp.status_code == 200, resp.text
    assert any(e["course_id"] == str(course.id) for e in resp.json())

    enrollment.deleted_at = _utcnow()
    db_session.commit()

    resp = client.get("/api/academy/enrollments", headers=headers)
    assert resp.status_code == 200, resp.text
    assert not any(e["course_id"] == str(course.id) for e in resp.json())


def test_f09_soft_deleted_enrollment_hidden_from_my_progress(client, db_session):
    admin, _, sede = seed_admin(db_session, email="f09.admin@example.com")
    student, persona, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f09.student@example.com",
        password="testpass123",
        sede_id=sede.id,
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    enrollment = _create_enrollment(db_session, persona.id, course.id)
    headers = auth_headers(client, email=student.email)

    resp = client.get("/api/academy/me/progress", headers=headers)
    assert resp.status_code == 200, resp.text
    assert any(p["id"] == str(course.id) for p in resp.json())

    enrollment.deleted_at = _utcnow()
    db_session.commit()

    resp = client.get("/api/academy/me/progress", headers=headers)
    assert resp.status_code == 200, resp.text
    assert not any(p["id"] == str(course.id) for p in resp.json())


# ── F-10: schemas dedicados ──────────────────────────────────────────────


def test_f10_academy_activity_log_schema(client, db_session):
    from backend.schemas.academy import AcademyActivityLog

    admin, _, sede = seed_admin(db_session, email="f10.admin@example.com")
    course = _create_course(db_session, sede_id=sede.id)
    log = models.AcademyActivityLog(
        event_type="course_archived",
        course_id=course.id,
        persona_id=admin.id,
        modality=None,
        value=0,
        payload_json={"course_code": course.code},
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)

    parsed = AcademyActivityLog.model_validate(log)
    assert parsed.id == log.id
    assert parsed.event_type == "course_archived"
    assert parsed.course_id == course.id
    assert parsed.persona_id == admin.id
    assert parsed.payload_json == {"course_code": course.code}


def test_f10_formal_acta_entry_schema(client, db_session):
    from backend.schemas.academy import FormalActaEntry

    admin, _, sede = seed_admin(db_session, email="f10.admin@example.com")
    student, persona, _ = seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="f10.student@example.com",
        password="testpass123",
        sede_id=sede.id,
        permisos={"academy:study": "allow"},
    )
    course = _create_course(db_session, sede_id=sede.id)
    enrollment = _create_enrollment(db_session, persona.id, course.id)
    acta = models.FormalActa(
        course_id=course.id,
        cohort_name="General",
        closed_by_persona_id=admin.id,
        min_grade=70,
        min_attendance=75,
    )
    db_session.add(acta)
    db_session.flush()
    entry = models.FormalActaEntry(
        acta_id=acta.id,
        enrollment_id=enrollment.id,
        final_grade=88.5,
        attendance_percent=95.0,
        approved=True,
        notes="Aprobado",
    )
    db_session.add(entry)
    db_session.commit()
    db_session.refresh(entry)

    parsed = FormalActaEntry.model_validate(entry)
    assert parsed.id == entry.id
    assert parsed.acta_id == acta.id
    assert parsed.enrollment_id == enrollment.id
    assert parsed.final_grade == 88.5
    assert parsed.approved is True
    assert parsed.attendance_percent == 95.0
