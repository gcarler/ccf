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


# ─── A-06/A-07/H-04: defense-in-depth del CRUD con sede_id kwarg ─────────────


def _seed_two_sedes(db_session):
    import uuid as _uuid

    sede_a = models.Sede(id=_uuid.uuid4(), nombre="Sede A", ciudad="Ciudad A")
    sede_b = models.Sede(id=_uuid.uuid4(), nombre="Sede B", ciudad="Ciudad B")
    db_session.add_all([sede_a, sede_b])
    db_session.commit()
    course_a = models.Course(
        code=f"CAA-{_uuid.uuid4().hex[:6]}",
        title="Curso A",
        modality="online",
        sede_id=sede_a.id,
        is_published=True,
    )
    course_b = models.Course(
        code=f"CBB-{_uuid.uuid4().hex[:6]}",
        title="Curso B",
        modality="online",
        sede_id=sede_b.id,
        is_published=True,
    )
    db_session.add_all([course_a, course_b])
    db_session.commit()
    return sede_a, course_a, sede_b, course_b


def test_a06_get_course_blocks_cross_sede_with_sede_id_kwarg(db_session):
    """A-06 → ``get_course(db, course_id, sede_id=sede_b)`` retorna None para
    un Course cuya ``sede_id`` es sede_a (otra sede)."""
    sede_a, course_a, sede_b, _ = _seed_two_sedes(db_session)
    # Sin sede_id: row accesible (compatibilidad callers no-API).
    assert academy_crud.get_course(db_session, course_a.id) is not None
    # Con sede_id del actor correcto: row accesible.
    assert academy_crud.get_course(db_session, course_a.id, sede_id=sede_a.id) is not None
    # Con sede_id del actor incorrecto: None (defense-in-depth).
    assert academy_crud.get_course(db_session, course_a.id, sede_id=sede_b.id) is None


def test_a07_update_course_blocks_cross_sede_with_sede_id_kwarg(db_session):
    """A-07 → ``update_course(db, course_id, data, sede_id=sede_b)`` retorna
    None (no muta) para un Course de sede_a. La row no se modifica."""
    sede_a, course_a, sede_b, _ = _seed_two_sedes(db_session)
    result = academy_crud.update_course(
        db_session, course_a.id, {"title": "Hacked"}, sede_id=sede_b.id
    )
    assert result is None, (
        "A-07 leak: update_course con sede_id incorrecto no debe retornar el row."
    )
    db_session.expire_all()
    assert db_session.query(models.Course).get(course_a.id).title == "Curso A", (
        "A-07 leak: la row del Course fue mutada por actor de otra sede."
    )


def test_a07_archive_course_blocks_cross_sede_with_sede_id_kwarg(db_session):
    """A-07 → ``archive_course(db, course_id, sede_id=sede_b)`` retorna False y
    no archiva para un Course de sede_a."""
    sede_a, course_a, sede_b, _ = _seed_two_sedes(db_session)
    archived = academy_crud.archive_course(
        db_session, course_a.id, sede_id=sede_b.id
    )
    assert archived is False, (
        "A-07 leak: archive_course con sede_id incorrecto no debe retornar True."
    )
    db_session.expire_all()
    assert (
        db_session.query(models.Course).get(course_a.id).deleted_at is None
    ), "A-07 leak: el Course fue archivado por actor de otra sede."


def test_h04_list_enrollments_filters_by_sede_id(db_session):
    """H-04 → ``list_enrollments(db, sede_id=sede_a)`` excluye enrollments de
    courses de sede_b (preserva globales)."""
    import uuid as _uuid

    sede_a, course_a, sede_b, course_b = _seed_two_sedes(db_session)
    persona = models.Persona(id=_uuid.uuid4(), first_name="X", last_name="Y", email="h04@example.com")
    db_session.add(persona)
    db_session.commit()
    e_a = models.Enrollment(persona_id=persona.id, course_id=course_a.id)
    e_b = models.Enrollment(persona_id=persona.id, course_id=course_b.id)
    db_session.add_all([e_a, e_b])
    db_session.commit()

    rows_a = academy_crud.list_enrollments(db_session, sede_id=sede_a.id)
    rows_b = academy_crud.list_enrollments(db_session, sede_id=sede_b.id)
    course_ids_a = {row.course_id for row in rows_a}
    course_ids_b = {row.course_id for row in rows_b}
    assert course_a.id in course_ids_a
    assert course_b.id not in course_ids_a, "H-04 leak: actor sede_a ve enrollment de sede_b"
    assert course_b.id in course_ids_b
    assert course_a.id not in course_ids_b, "H-04 leak: actor sede_b ve enrollment de sede_a"


# ─── H-05: list_courses con sede_id NO mezcla globales por defecto ─────────────


def test_h05_list_courses_excludes_global_by_default(db_session):
    """H-05 → ``list_courses(db, sede_id=...)`` por defecto NO incluye
    ``Course.sede_id IS NULL`` (global) — alinea con A-03. ``include_global=True``
    los re-incorpora explicit."""
    import uuid as _uuid

    sede_a = models.Sede(id=_uuid.uuid4(), nombre="Sede X", ciudad="Cdad X")
    db_session.add(sede_a)
    db_session.commit()
    course_a = models.Course(
        code=f"AX-{_uuid.uuid4().hex[:6]}",
        title="Curso A sede",
        modality="online",
        sede_id=sede_a.id,
        is_published=True,
    )
    course_global = models.Course(
        code=f"GX-{_uuid.uuid4().hex[:6]}",
        title="Curso global",
        modality="online",
        sede_id=None,
        is_published=True,
    )
    db_session.add_all([course_a, course_global])
    db_session.commit()

    # Default (include_global=False): sólo su sede.
    rows_strict = academy_crud.list_courses(db_session, sede_id=sede_a.id)
    ids_strict = {c.id for c in rows_strict}
    assert course_a.id in ids_strict
    assert course_global.id not in ids_strict, "H-05 leak: list_courses incluye curso global sin include_global=True"

    # Opt-in: incluye globales.
    rows_global = academy_crud.list_courses(db_session, sede_id=sede_a.id, include_global=True)
    ids_global = {c.id for c in rows_global}
    assert course_global.id in ids_global, "H-05: include_global=True debe devolver globales"


# ─── H-06: create_enrollment no reactiva cross-tenant ─────────────────────────


def test_h06_create_enrollment_reactivates_own_sede(db_session):
    """H-06 happy path: reactivar un enrollment archivado de un curso de la
    MISMA sede del actor funciona normalmente (preserva comportamiento
    previo cuando sede_id coincide)."""
    import uuid as _uuid

    sede_a, course_a, _, _ = _seed_two_sedes(db_session)
    persona = models.Persona(
        id=_uuid.uuid4(), first_name="A", last_name="B", email="h6a@example.com"
    )
    db_session.add(persona)
    db_session.commit()
    payload = EnrollmentCreate(persona_id=persona.id, course_id=course_a.id)
    enrollment = academy_crud.create_enrollment(
        db_session, payload, sede_id=sede_a.id
    )
    # Soft-delete y reaciclar con misma sede → reactiva.
    enrollment.deleted_at = _utcnow()
    db_session.commit()
    restored = academy_crud.create_enrollment(
        db_session, payload, sede_id=sede_a.id
    )
    assert restored.id == enrollment.id
    assert restored.deleted_at is None
    assert restored.status == "active"


def test_h06_create_enrollment_reactivates_global_course(db_session):
    """H-06: curso global (sede_id NULL) SIEMPRE es legítimo cross-tenant
    (decisión A-03 lectura/captación). Reactivar su enrollment está
    permitido independientemente de la sede del actor."""
    import uuid as _uuid

    sede_a, _, _, _ = _seed_two_sedes(db_session)
    course_global = models.Course(
        code=f"GG-{_uuid.uuid4().hex[:6]}",
        title="Curso global",
        modality="online",
        sede_id=None,
        is_published=True,
    )
    db_session.add(course_global)
    db_session.commit()
    persona = models.Persona(
        id=_uuid.uuid4(), first_name="G", last_name="B", email="h6g@example.com"
    )
    db_session.add(persona)
    db_session.commit()
    payload = EnrollmentCreate(persona_id=persona.id, course_id=course_global.id)
    enrollment = academy_crud.create_enrollment(
        db_session, payload, sede_id=sede_a.id
    )
    enrollment.deleted_at = _utcnow()
    db_session.commit()
    restored = academy_crud.create_enrollment(
        db_session, payload, sede_id=sede_a.id
    )
    assert restored.id == enrollment.id
    assert restored.deleted_at is None


def test_h06_create_enrollment_blocks_cross_sede_reactivation(db_session):
    """H-06 core: existe un enrollment archivado en un curso de sede_a. Un
    actor con sede_b que pase ``sede_id=sede_b`` NO debe reactivar ese
    enrollment — se levanta ``ValueError`` (defense-in-depth contra leak
    cross-tenant). Sin ``sede_id`` (compat callers no-API) se reactivaría
    normalmente."""
    import uuid as _uuid

    sede_a, course_a, sede_b, _ = _seed_two_sedes(db_session)
    persona = models.Persona(
        id=_uuid.uuid4(), first_name="X", last_name="Y", email="h6x@example.com"
    )
    db_session.add(persona)
    db_session.commit()
    payload = EnrollmentCreate(persona_id=persona.id, course_id=course_a.id)
    # Crear el enrollment con sede_a (sin sede_id = caller no-API legítimo).
    enrollment = academy_crud.create_enrollment(db_session, payload)
    enrollment.deleted_at = _utcnow()
    db_session.commit()
    # Actor de sede_b intenta reactivar — bloqueado.
    with pytest.raises(ValueError):
        academy_crud.create_enrollment(db_session, payload, sede_id=sede_b.id)


# ─── H-07: create_course / create_lesson validan ownership del actor ─────────


def test_h07_create_course_blocks_cross_sede_attribution(db_session):
    """H-07: ``create_course(db, {...'sede_id': otra_sede}, sede_id=mia)``
    levanta ``ValueError`` — el actor no puede crear un curso atribuyéndolo
    a otra sede. Sin ``sede_id`` (caller no-API) se respeta el payload."""
    sede_a, _, sede_b, _ = _seed_two_sedes(db_session)
    # Sin sede_id: payload respeta sede_b (compatibilidad).
    course = academy_crud.create_course(
        db_session,
        {"title": "B", "code": "B-H07-1", "modality": "online", "sede_id": sede_b.id},
    )
    assert course.sede_id == sede_b.id
    # Con sede_id=sede_a: bloquea atribuir a sede_b.
    with pytest.raises(ValueError):
        academy_crud.create_course(
            db_session,
            {"title": "B2", "code": "B-H07-2", "modality": "online", "sede_id": sede_b.id},
            sede_id=sede_a.id,
        )
    # Con sede_id=sede_a y payload sede_id=None (global legítimo): permitido.
    course_global = academy_crud.create_course(
        db_session,
        {"title": "G", "code": "G-H07", "modality": "online", "sede_id": None},
        sede_id=sede_a.id,
    )
    assert course_global.sede_id is None


def test_h07_create_lesson_blocks_cross_sede(db_session):
    """H-07: ``create_lesson(db, course_id_otra_sede, {...}, sede_id=mia)``
    levanta ``ValueError`` — el actor no puede añadir lecciones a un curso
    de otra sede. Sin ``sede_id`` (caller no-API) preserva comportamiento."""
    import uuid as _uuid

    sede_a, course_a, sede_b, course_b = _seed_two_sedes(db_session)
    # Sin sede_id: crea normalmente (compatibilidad).
    lesson = academy_crud.create_lesson(
        db_session,
        course_a.id,
        {"title": "L1", "order_index": 1, "content": "", "content_type": "text"},
    )
    assert lesson.course_id == course_a.id
    # Con sede_id=sede_a: OK (mismo curso/sede).
    lesson2 = academy_crud.create_lesson(
        db_session,
        course_a.id,
        {"title": "L2", "order_index": 2, "content": "", "content_type": "text"},
        sede_id=sede_a.id,
    )
    assert lesson2.course_id == course_a.id
    # Con sede_id=sede_a sobre course_b (otra sede): bloqueado.
    with pytest.raises(ValueError):
        academy_crud.create_lesson(
            db_session,
            course_b.id,
            {"title": "L3", "order_index": 1, "content": "", "content_type": "text"},
            sede_id=sede_a.id,
        )


# ─── H-08: _commit_or_raise_conflict distingue 409 de 500 ───────────────────


def test_h08_commit_or_raise_conflict_unique_violation_returns_409(db_session):
    """H-08: una IntegrityError por UNIQUE (23505 en Postgres / 'UNIQUE
    constraint failed' en SQLite) se traduce a HTTPException 409. Una
    IntegrityError por otra constraint (NOT NULL) se re-raise (no False-409)."""
    from fastapi import HTTPException
    from sqlalchemy.exc import IntegrityError
    from unittest.mock import MagicMock

    # Simulamos un db.commit() que lanza UNIQUE violation (SQLite).
    db = MagicMock()
    orig = MagicMock()
    orig.pgcode = None  # Fuerza la rama SQLite.
    exc = IntegrityError("stmt", params={}, orig=orig)
    # Forzamos el str(orig) a contener 'UNIQUE constraint failed'.
    orig.__str__ = lambda self: "UNIQUE constraint failed: course.code"
    db.commit.side_effect = exc
    with pytest.raises(HTTPException) as exc_info:
        academy_crud._commit_or_raise_conflict(db, detail="course code already exists")
    assert exc_info.value.status_code == 409
    assert "course code already exists" in exc_info.value.detail
    db.rollback.assert_called_once()


def test_h08_commit_or_raise_conflict_non_unique_reraises(db_session):
    """H-08: una IntegrityError que NO es unique-violation (e.g. NOT NULL,
    FK, check) se re-raise post-rollback — NO se enmascara como falso 409.
    Evita bugs silenciados (lo que M-12 corrigió en CMS)."""
    from sqlalchemy.exc import IntegrityError
    from unittest.mock import MagicMock

    db = MagicMock()
    orig = MagicMock()
    orig.pgcode = "23502"  # NOT NULL violation (no 23505).
    db.commit.side_effect = IntegrityError("stmt", params={}, orig=orig)
    with pytest.raises(IntegrityError):
        academy_crud._commit_or_raise_conflict(db, detail="whatever")
    db.rollback.assert_called_once()


def test_h08_create_course_unique_violation_surfaces_409(db_session):
    """H-08 end-to-end: ``create_course`` con un code duplicado (UNIQUE
    constraint en Postgres / SQLite) ahora levanta HTTPException(409) vía
    el wrapper, no un IntegrityError 500 sin tragar."""
    from fastapi import HTTPException

    academy_crud.create_course(
        db_session, {"title": "C1", "code": "DUP-H08", "modality": "online"}
    )
    with pytest.raises(HTTPException) as exc_info:
        academy_crud.create_course(
            db_session, {"title": "C2", "code": "DUP-H08", "modality": "online"}
        )
    assert exc_info.value.status_code == 409
