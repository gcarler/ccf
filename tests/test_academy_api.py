"""Tests for the canonical Academy API."""

from datetime import timedelta

from backend import models
from backend.models_shared import _utcnow
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
    headers = auth_headers(client, email=student.email, password="testpass123")

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
    headers = auth_headers(client, email=student.email, password="testpass123")

    response = client.post(
        "/api/academy/enrollments",
        headers=headers,
        json={
            "persona_id": "00000000-0000-0000-0000-000000000001",
            "course_id": str(course.id),
        },
    )

    assert response.status_code == 403


def test_forum_threads_isolate_by_sede(client, db_session):
    """Runtime: forum_threads must isolate by sede_id, preserving orphan threads.

    Verifica:
    1. Aislamiento por sede: admin A solo ve hilos de sede_a, admin B solo de sede_b.
    2. Orphan threads: hilos con course_id IS NULL visibles para todas las sedes.
    3. Course soft-deleted: hilos de cursos con deleted_at != NULL quedan ocultos.
    4. Orden determinístico: created_at explícito para evitar flakiness por commit timing.
    """
    import uuid as _uuid

    admin_a, persona_a, sede_a = seed_admin(db_session, email="adminA@example.com", password="testpass123")
    admin_b, persona_b, sede_b = seed_admin(db_session, email="adminB@example.com", password="testpass123")
    assert sede_a.id != sede_b.id, "Las sedes A y B deben ser distintas"

    base_time = _utcnow()
    course_a = models.Course(
        code=f"CA-{_uuid.uuid4().hex[:6]}",
        title="Course A",
        modality="online",
        sede_id=sede_a.id,
    )
    course_b = models.Course(
        code=f"CB-{_uuid.uuid4().hex[:6]}",
        title="Course B",
        modality="online",
        sede_id=sede_b.id,
    )
    # Course C: misma sede que A pero soft-deleted (su hilo NO debe verse).
    course_c = models.Course(
        code=f"CC-{_uuid.uuid4().hex[:6]}",
        title="Course C (deleted)",
        modality="online",
        sede_id=sede_a.id,
        deleted_at=base_time,
    )
    db_session.add_all([course_a, course_b, course_c])
    db_session.commit()

    # Created_at explícito para determinismo (orden DESC verificable).
    thread_a = models.ForumThread(
        course_id=course_a.id,
        author_persona_id=persona_a.id,
        title="Thread A",
        category="general",
        content="Contenido en sede A",
        created_at=base_time - timedelta(seconds=300),
    )
    thread_b = models.ForumThread(
        course_id=course_b.id,
        author_persona_id=persona_b.id,
        title="Thread B",
        category="general",
        content="Contenido en sede B",
        created_at=base_time - timedelta(seconds=200),
    )
    thread_c = models.ForumThread(
        course_id=course_c.id,
        author_persona_id=persona_a.id,
        title="Thread on deleted Course",
        category="general",
        content="Hilo de curso soft-deleted; debe estar OCULTO",
        created_at=base_time - timedelta(seconds=100),
    )
    thread_orphan = models.ForumThread(
        course_id=None,
        author_persona_id=persona_a.id,
        title="Global Announcement",
        category="announcement",
        content="Hilo global sin curso",
        created_at=base_time,  # el más nuevo → aparece primero en DESC
    )
    db_session.add_all([thread_a, thread_b, thread_c, thread_orphan])
    db_session.commit()

    # 1. Admin A: ve Thread A + Global Announcement; NO Thread B; NO Thread-C-deleted.
    headers_a = auth_headers(client, email="adminA@example.com")
    resp_a = client.get("/api/academy/forum/threads", headers=headers_a)
    assert resp_a.status_code == 200
    titles_a = {t["title"] for t in resp_a.json()}
    assert "Thread A" in titles_a
    assert "Global Announcement" in titles_a
    assert "Thread B" not in titles_a, "Fuga de aislamiento: admin A de sede_a ve Thread B de sede_b"
    assert "Thread on deleted Course" not in titles_a, "Hilo de curso soft-deleted debe estar OCULTO para admin A"
    response_a = [t["title"] for t in resp_a.json()]
    assert len(response_a) == 2, (
        f"Admin A debería ver exactamente 2 hilos (suyos + global), vio {len(response_a)}: {response_a}"
    )

    # 2. Admin B: ve Thread B + Global Announcement; NO Thread A; NO Thread-C-deleted.
    headers_b = auth_headers(client, email="adminB@example.com")
    resp_b = client.get("/api/academy/forum/threads", headers=headers_b)
    assert resp_b.status_code == 200
    titles_b = {t["title"] for t in resp_b.json()}
    assert "Thread B" in titles_b
    assert "Global Announcement" in titles_b
    assert "Thread A" not in titles_b, "Fuga de aislamiento: admin B de sede_b ve Thread A de sede_a"
    assert "Thread on deleted Course" not in titles_b, "Hilo de curso soft-deleted debe estar OCULTO para admin B"
    response_b = [t["title"] for t in resp_b.json()]
    assert len(response_b) == 2, (
        f"Admin B debería ver exactamente 2 hilos (suyos + global), vio {len(response_b)}: {response_b}"
    )

    # 3. Orden DESC determinístico: orphan (created_at=base_time) aparece primero.
    assert response_b[0] == "Global Announcement", (
        f"Orden DESC incorrecto; primero deberia ser Global Announcement, fue {response_b[0]}"
    )


def test_delete_submission_archives_with_payload_json(client, db_session):
    """ACAD-MED-003 + ACAD-MED-003-FOLLOWUP: DELETE /admin/submissions/{id} debe
    soft-deleted la entrega (Regla 4, sin db.delete()) y preservar ``file_url``,
    ``lesson_id`` y ``enrollment_id`` en ``AcademyActivityLog.payload_json``.

    El job batch de purga de Seaweed consultará ``event_type='assignment_submission_archived'``
    y leerá ``payload_json`` para listar archivos huérfanos.
    """
    import uuid as _uuid

    editor, _persona_editor, sede = seed_admin(db_session, email="archiver.editor@example.com", password="testpass123")
    editor.rol_plataforma.permisos = {"academy:edit": "allow", "academy:manage": "allow"}
    db_session.commit()

    student, persona_student, _ = seed_user_with_role(
        db_session,
        role_name="academy_student",
        email="archiver.student@example.com",
        password="testpass123",
    )

    course = models.Course(
        code=f"ACA-ARCH-{_uuid.uuid4().hex[:6]}",
        title="Archivable Course",
        modality="formal",
        sede_id=sede.id,
        is_published=True,
    )
    db_session.add(course)
    db_session.commit()

    lesson = models.Lesson(
        course_id=course.id,
        title="Lesson to Archive",
        content="x",
        order_index=1,
        is_published=True,
    )
    db_session.add(lesson)
    db_session.commit()

    enrollment = models.Enrollment(persona_id=persona_student.id, course_id=course.id)
    db_session.add(enrollment)
    db_session.commit()

    original_file_url = f"https://seaweed.local/ccf/academy/{_uuid.uuid4().hex}.pdf"
    submission = models.AssignmentSubmission(
        enrollment_id=enrollment.id,
        lesson_id=lesson.id,
        file_url=original_file_url,
        comment="entrega archivable",
    )
    db_session.add(submission)
    db_session.commit()

    submission_id = submission.id
    lesson_id = lesson.id
    enrollment_id = enrollment.id

    headers = auth_headers(client, email="archiver.editor@example.com")
    resp = client.delete(
        f"/api/academy/admin/submissions/{submission_id}",
        headers=headers,
    )
    assert resp.status_code == 204, f"DELETE submission debe devolver 204 (status {resp.status_code}): {resp.text}"

    # 1. Soft delete (Regla 4): row sigue en DB pero con deleted_at poblado.
    db_session.expire_all()
    archived = (
        db_session.query(models.AssignmentSubmission).filter(models.AssignmentSubmission.id == submission_id).first()
    )
    assert archived is not None, "Regla 4 violada: row fue eliminado en lugar de archivado (deleted_at)"
    assert archived.deleted_at is not None, "Regla 4 violada: deleted_at no fue seteado tras DELETE"

    # 2. Idempotencia: un segundo DELETE sobre el mismo id devuelve 404.
    resp_again = client.delete(
        f"/api/academy/admin/submissions/{submission_id}",
        headers=headers,
    )
    assert resp_again.status_code == 404, (
        f"Segundo DELETE debe ser 404 (status {resp_again.status_code}): {resp_again.text}"
    )

    # 3. ACAD-MED-003-FOLLOWUP (cierre): AcademyActivityLog archivó el payload completo.
    log = (
        db_session.query(models.AcademyActivityLog)
        .filter(
            models.AcademyActivityLog.event_type == "assignment_submission_archived",
            models.AcademyActivityLog.persona_id == editor.id,
        )
        .order_by(models.AcademyActivityLog.created_at.desc())
        .first()
    )
    assert log is not None, (
        "ACAD-MED-003: AcademyActivityLog con event_type='assignment_submission_archived' debe existir tras DELETE"
    )
    payload = log.payload_json or {}
    assert payload.get("submission_id") == str(submission_id), (
        f"payload_json.submission_id esperado {submission_id}, obtuve {payload.get('submission_id')}"
    )
    assert payload.get("file_url") == original_file_url, (
        f"payload_json.file_url esperado {original_file_url}, "
        f"obtuve {payload.get('file_url')} — ACAD-MED-003 incompleto"
    )
    assert payload.get("lesson_id") == str(lesson_id), (
        f"payload_json.lesson_id esperado {lesson_id}, obtuve {payload.get('lesson_id')}"
    )
    assert payload.get("enrollment_id") == str(enrollment_id), (
        f"payload_json.enrollment_id esperado {enrollment_id}, obtuve {payload.get('enrollment_id')}"
    )
    assert payload.get("archived_by_persona_id") == str(editor.id), (
        f"payload_json.archived_by_persona_id esperado {editor.id}, obtuve {payload.get('archived_by_persona_id')}"
    )
    assert "archived_at" in payload, "payload_json.archived_at debe estar presente para forense temporal"


def test_grade_submission_blocks_cross_sede(client, db_session):
    """Runtime: grade_submission must reject submissions whose Course belongs to another sede.

    Verifica Axioma 3: un editor de sede_a NO puede calificar una Submission cuyo
    Lesson.course_id pertenece a sede_b, incluso conociendo el submission_id.
    Sin este control, cualquier editor con :edit podría mutar notas en cualquier sede.
    """
    import uuid as _uuid

    # Editor: ADMIN en sede_a (posee academy:edit por permisos `*`).
    admin_a, _persona_a, sede_a = seed_admin(db_session, email="editorA@example.com", password="testpass123")
    # Estudiante + sede B independientes (cada seed crea su propia Sede).
    sede_b_id = _uuid.uuid4()
    _student_b, persona_b, sede_b = seed_user_with_role(
        db_session,
        role_name="academy_student",
        email="studentB@example.com",
        password="testpass123",
        sede_id=sede_b_id,
    )
    assert sede_a.id != sede_b.id, "Las sedes A y B deben ser distintas"

    course_b = models.Course(code=f"CB-{_uuid.uuid4().hex[:6]}", title="Course B", modality="online", sede_id=sede_b.id)
    db_session.add(course_b)
    db_session.commit()

    lesson_b = models.Lesson(course_id=course_b.id, title="Lesson B", content="x", order_index=1, is_published=True)
    db_session.add(lesson_b)
    db_session.commit()

    enrollment_b = models.Enrollment(persona_id=persona_b.id, course_id=course_b.id)
    db_session.add(enrollment_b)
    db_session.commit()

    submission_b = models.AssignmentSubmission(
        enrollment_id=enrollment_b.id,
        lesson_id=lesson_b.id,
        file_url="https://example.com/file_b.pdf",
        comment="entrega de sede_b",
    )
    db_session.add(submission_b)
    db_session.commit()

    # Editor de sede_a intenta calificar Submission B → 404 (course no está en su scope).
    headers_a = auth_headers(client, email="editorA@example.com")
    resp = client.patch(
        f"/api/academy/admin/submissions/{submission_b.id}/grade",
        json={"grade": 95.0, "feedback": "A deberia poder verlos"},
        headers=headers_a,
    )
    assert resp.status_code == 404, (
        f"Sede-isolation rota: editor de sede_a calificó submission de sede_b "
        f"(status {resp.status_code}); body={resp.text}"
    )
    db_session.refresh(submission_b)
    assert submission_b.grade is None, "El grade de la submission cross-sede NO debe persistir"

    # Sanity: la Submission SÍ es calificable por un editor reasignado a sede_b.
    admin_b, _persona_b_admin, _sede_extra = seed_admin(db_session, email="editorB@example.com", password="testpass123")
    # Reasignamos manualmente al editor_b la sede_b para reproducir el path feliz.
    admin_b.sede_id = sede_b.id
    db_session.commit()
    headers_b = auth_headers(client, email="editorB@example.com")
    resp_ok = client.patch(
        f"/api/academy/admin/submissions/{submission_b.id}/grade",
        json={"grade": 88.0, "feedback": "ok"},
        headers=headers_b,
    )
    assert resp_ok.status_code == 200, (
        f"Editor de sede_b no pudo calificar su propia sede (status {resp_ok.status_code}): {resp_ok.text}"
    )
    db_session.refresh(submission_b)
    assert submission_b.grade == 88.0, f"Grade persistido incorrectamente; esperado 88.0, obtuve {submission_b.grade}"
