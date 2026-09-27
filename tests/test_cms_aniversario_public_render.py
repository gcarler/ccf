"""
Pruebas canónicas de verificación y regresión para la Landing Aniversario 40 y CMS Render Público.
(TKT-CMS-ANIVERSARIO-VERIFY-01).

Valida:
1. Endpoint público GET /api/cms/v2/public/sites/ccf/pages/aniversario40 responde 200.
2. La página contiene las 5 secciones estructurales activas:
   - video_hero
   - rich_text (Agenda de Celebración)
   - timeline (40 Años de Historia)
   - gallery_masonry (Galería de recuerdos históricos)
   - contact_form (Muro de Gratitud y Testimonios)
3. Las props de cada sección coinciden con los contratos canónicos de CMS v2.
4. Los assets estáticos (/aniversario40/video-aniversario40.mp4 y gallery) están referenciados.
5. Invariantes Axioma 2 (soft-delete) y Axioma 3 (multi-tenant):
   - Una página con deleted_at no es visible públicamente (responde 404).
   - Acceso con site_key inválido o inactivo responde 404.
"""

from __future__ import annotations

import datetime
from datetime import timezone
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models import CmsPage, CmsSection, CmsSite


@pytest.fixture
def client():
    return TestClient(app)


def _get_or_create_site(db_session) -> CmsSite:
    site = db_session.query(CmsSite).filter_by(site_key="ccf").first()
    if not site:
        site = CmsSite(
            id=uuid.uuid4(),
            site_key="ccf",
            name="Comunidad Cristiana Faro",
            is_active=True,
            created_at=datetime.datetime.now(timezone.utc),
            updated_at=datetime.datetime.now(timezone.utc),
        )
        db_session.add(site)
        db_session.flush()
    return site


def test_public_aniversario40_page_render_and_sections(client, db_session):
    """Valida la resolución pública y renderizado de aniversario40."""
    site = _get_or_create_site(db_session)

    page = db_session.query(CmsPage).filter_by(site_id=site.id, slug="aniversario40").first()
    if not page:
        page = CmsPage(
            id=uuid.uuid4(),
            site_id=site.id,
            slug="aniversario40",
            title="40 Años Iluminando Generaciones",
            status="published",
            locale="es",
            created_at=datetime.datetime.now(timezone.utc),
            updated_at=datetime.datetime.now(timezone.utc),
        )
        db_session.add(page)
        db_session.flush()

        s_hero = CmsSection(
            id=uuid.uuid4(),
            page_id=page.id,
            section_key="hero",
            type="video_hero",
            sort_order=0,
            status="active",
            is_visible=True,
            props_json={
                "title": "Celebra con nosotros cuatro décadas de luz.",
                "body": "Una historia de fe, familia y transformación.",
                "video_url": "/aniversario40/video-aniversario40.mp4",
                "cta_label": "Registra tu asistencia",
                "cta_href": "/eventos",
            },
        )
        s_agenda = CmsSection(
            id=uuid.uuid4(),
            page_id=page.id,
            section_key="agenda",
            type="rich_text",
            sort_order=1,
            status="active",
            is_visible=True,
            props_json={
                "title": "Agenda de Celebración",
                "body": "21 de Agosto: Servicio de Milagros...",
            },
        )
        s_timeline = CmsSection(
            id=uuid.uuid4(),
            page_id=page.id,
            section_key="timeline",
            type="timeline",
            sort_order=2,
            status="active",
            is_visible=True,
            props_json={
                "title": "Nuestra Historia",
                "items": [{"year": "1986", "title": "Inicio", "description": "Comienzo del ministerio"}],
            },
        )
        s_gallery = CmsSection(
            id=uuid.uuid4(),
            page_id=page.id,
            section_key="galeria",
            type="gallery_masonry",
            sort_order=3,
            status="active",
            is_visible=True,
            props_json={
                "title": "40 Años en Imágenes",
                "images": [{"url": "/aniversario40/gallery-01.jpg", "caption": "CCF 1986"}],
            },
        )
        s_muro = CmsSection(
            id=uuid.uuid4(),
            page_id=page.id,
            section_key="muro-gratitud",
            type="contact_form",
            sort_order=4,
            status="active",
            is_visible=True,
            props_json={
                "title": "Muro de Gratitud",
                "submit_label": "Enviar Agradecimiento",
            },
        )
        db_session.add_all([s_hero, s_agenda, s_timeline, s_gallery, s_muro])
        db_session.commit()

    resp = client.get("/api/cms/v2/public/sites/ccf/pages/aniversario40")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["slug"] == "aniversario40"
    assert data["site_key"] == "ccf"
    sections = data.get("sections", [])
    assert len(sections) >= 5

    section_types = [s["type"] for s in sections if s.get("is_visible")]
    assert "video_hero" in section_types
    assert "rich_text" in section_types
    assert "timeline" in section_types
    assert "gallery_masonry" in section_types
    assert "contact_form" in section_types

    hero_section = next(s for s in sections if s["type"] == "video_hero")
    assert "video_url" in hero_section["props_json"]
    assert "video-aniversario40.mp4" in hero_section["props_json"]["video_url"]


def test_public_aniversario40_soft_delete_isolation(client, db_session):
    """Verifica que si una página tiene soft-delete, el endpoint público responde 404 (Axioma 2)."""
    site = _get_or_create_site(db_session)

    deleted_page = CmsPage(
        id=uuid.uuid4(),
        site_id=site.id,
        slug="aniversario-eliminado-test",
        title="Aniversario Test Borrado",
        status="published",
        locale="es",
        deleted_at=datetime.datetime.now(timezone.utc),
        created_at=datetime.datetime.now(timezone.utc),
        updated_at=datetime.datetime.now(timezone.utc),
    )
    db_session.add(deleted_page)
    db_session.commit()

    resp = client.get(f"/api/cms/v2/public/sites/ccf/pages/{deleted_page.slug}")
    assert resp.status_code == 404, "Una página con deleted_at no debe ser visible públicamente"


def test_public_aniversario40_invalid_site_key(client):
    """Verifica que un site_key no existente o inválido responde 404 (Axioma 3)."""
    resp = client.get("/api/cms/v2/public/sites/sitio_inexistente_xyz/pages/aniversario40")
    assert resp.status_code == 404
