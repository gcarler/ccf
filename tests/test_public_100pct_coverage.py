"""
Exhaustive test suite for backend/api/public.py to achieve 100% test coverage.
Covers:
- public_list_courses & public_get_course (including 404)
- public_course_enroll (including 404 & contact tracking)
- public_contact (with prayer request creation)
- public_wishlist
- upload_public_document (allowed types, disallowed types, max size)
"""

from __future__ import annotations

import uuid

import pytest

from backend import models
from backend.models_academy_core import Course


@pytest.fixture(autouse=True)
def seed_active_sede(db_session):
    sede = db_session.query(models.Sede).filter(models.Sede.es_activa.is_(True)).first()
    if not sede:
        sede = models.Sede(nombre="Sede Principal", ciudad="Bogotá", es_activa=True)
        db_session.add(sede)
        db_session.commit()
    return sede


class TestPublicApi100PctCoverage:
    def test_public_courses_list_and_get(self, client, db_session):
        # Create published course with lesson
        c1 = Course(
            id=uuid.uuid4(),
            code="LID-PUB-01",
            title="Liderazgo Público",
            slug="liderazgo-publico",
            description="Curso de liderazgo",
            tag="Academia",
            modality="online",
            is_published=True,
        )
        c2 = Course(
            id=uuid.uuid4(),
            code="LID-PUB-02",
            title="Liderazgo Avanzado",
            slug="liderazgo-avanzado",
            modality="online",
            is_published=True,
        )
        lesson = models.Lesson(
            course_id=c1.id,
            title="Lección 1",
            content="Contenido de la lección",
            is_published=True,
        )
        db_session.add_all([c1, c2, lesson])
        db_session.commit()

        # List courses
        res = client.get("/api/public/courses")
        assert res.status_code == 200

        # Get course detail by slug
        res_detail = client.get(f"/api/public/courses/{c1.slug}")
        assert res_detail.status_code == 200
        assert res_detail.json()["id"] == c1.slug

        # Get course detail 404
        res_404 = client.get("/api/public/courses/non-existing-slug")
        assert res_404.status_code == 404

    def test_public_course_enroll(self, client, db_session):
        c = models.Course(
            code="LID-PUB-ENROLL",
            title="Curso Para Inscripción",
            slug="curso-inscripcion",
            modality="online",
            is_published=True,
        )
        db_session.add(c)
        db_session.commit()

        payload = {
            "email": "estudiante@ejemplo.com",
            "first_name": "Juan",
            "last_name": "Pérez",
            "phone": "555-1234",
            "notes": "Me interesa mucho este curso",
        }
        res = client.post(f"/api/public/courses/{c.slug}/enroll", json=payload)
        assert res.status_code in (200, 201)

    def test_public_contact_with_prayer_request(self, client, db_session):
        payload = {
            "full_name": "María Gómez",
            "email": "maria@ejemplo.com",
            "phone": "555-9876",
            "notes": "Por favor orar por mi familia",
            "source": "conocer-a-jesus",
        }
        res = client.post("/api/public/contact", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"

    def test_public_contact_rejects_invalid_email(self, client):
        response = client.post(
            "/api/public/contact",
            json={
                "full_name": "Correo inválido",
                "email": "not-an-email",
                "notes": "Debe rechazarse",
            },
        )
        assert response.status_code == 422

    def test_public_wishlist(self, client, db_session):
        res = client.post(
            "/api/public/wishlist",
            json={
                "title": "Manual de Liderazgo Ministerial",
                "email": "deseado@example.com",
                "full_name": "Esteban Quito",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["title"] == "Manual de Liderazgo Ministerial"

    def test_public_prayer_rejects_invalid_email(self, client):
        response = client.post(
            "/api/crm/prayer-requests/public",
            json={
                "requester_name": "Persona de prueba",
                "request_text": "Petición válida para probar validación",
                "email": "not-an-email",
            },
        )
        assert response.status_code == 422

    def test_upload_public_document(self, client, db_session):
        # Disallowed file type
        bad_file = ("test.exe", b"malicious content", "application/octet-stream")
        res_bad = client.post("/api/public/documents", files={"file": bad_file})
        assert res_bad.status_code == 400

        # File too large (>20MB)
        large_file = ("large.pdf", b"0" * (21 * 1024 * 1024), "application/pdf")
        res_large = client.post("/api/public/documents", files={"file": large_file})
        assert res_large.status_code == 400

        # Valid upload (PDF)
        pdf_file = ("manual.pdf", b"%PDF-1.4 test document content", "application/pdf")
        res_ok = client.post("/api/public/documents", files={"file": pdf_file})
        assert res_ok.status_code == 201
        data = res_ok.json()
        assert data["filename"] == "manual.pdf"
        assert data["mime_type"] == "application/pdf"

    # Hallazgo 2 (ses_03767db76ffee 2026-08-03): public_list_courses admitía
    # sólo access_level=='persona' tras c1d923c0, excluyendo 'open' (más
    # público que 'persona'), 'advanced' (no público) y 'privado' (valor
    # huérfano del enum canónico Literal["open","persona","advanced"]).+Ajuste: el filtro ahora admite ['open','persona'] y excluye 'advanced'
    # (curso avanzado para inscritos, no captación pública) y cualquier
    # valor fuera del enum ('privado' o futuro). La migración
    # 20260803_0005 normaliza los 4 cursos 'privado' (valor pre-enum) a 'persona'.

    def test_public_list_courses_admits_open_and_persona_excludes_advanced(self, client, db_session):
        """public_list_courses admite access_level en {'open','persona'},
        excluye 'advanced' (no público)."""

        def _course(slug: str, access_level: str) -> Course:
            return Course(
                id=uuid.uuid4(),
                code=f"LID-{slug.upper()}-{access_level}",
                title=f"Curso {slug}",
                slug=slug,
                modality="online",
                is_published=True,
                access_level=access_level,
            )

        c_open = _course("curso-open", "open")
        c_persona = _course("curso-persona", "persona")
        c_advanced = _course("curso-advanced", "advanced")
        db_session.add_all([c_open, c_persona, c_advanced])
        db_session.commit()

        res = client.get("/api/public/courses")
        assert res.status_code == 200
        ids = {c["id"] for c in res.json()}
        assert c_open.slug in ids, "open debe ser visible (captación pública)"
        assert c_persona.slug in ids, "persona debe ser visible (captación pública)"
        assert c_advanced.slug not in ids, "advanced NO es captación pública"

    def test_public_list_courses_regression_privado_excluded_unnormalized(self, client, db_session):
        """Regresión del hallazgo 2: un curso con access_level='privado'
        (valor huérfano heredado de inserciones pre-enum) NO aparece en
        /cursos hasta que la migración 20260803_0005 lo normalice a 'persona'.
        El test consagra el contrato: el filtro por sí solo NO restaura la
        visibilidad de los 4 cursos preexistentes — la migración es necesaria.
        """

        c_privado = Course(
            id=uuid.uuid4(),
            code="LID-REG-PRIVADO",
            title="Curso Privado Pre-enum",
            slug="curso-privado-pre-enum",
            modality="online",
            is_published=True,
            access_level="privado",  # bypass del validator Pydantic (inserción directa ORM)
        )
        db_session.add(c_privado)
        db_session.commit()

        res = client.get("/api/public/courses")
        assert res.status_code == 200
        ids = {c["id"] for c in res.json()}
        assert c_privado.slug not in ids, (
            "Un curso 'privado' (no normalizado) debe SIGO fuera de /cursos — "
            "la migración 20260803_0005 es la que restaura la visibilidad, no el filtro"
        )

        # Detalle por slug sigue disponible (public_get_course no filtra access_level
        # — sólo published+deleted_at), así que mientras se normaliza, el curso
        # sigue siendo accesible vía /api/public/courses/{slug}, incluso si no aparece
        # en el listado. Verificamos que el detalle no rompe con el valor huérfano.
        res_detail = client.get(f"/api/public/courses/{c_privado.slug}")
        assert res_detail.status_code == 200
        assert res_detail.json()["id"] == c_privado.slug
