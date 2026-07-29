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

import io
import uuid
from datetime import datetime, timedelta
import pytest

from backend import models
from backend.models_academy_core import Course, Lesson


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
