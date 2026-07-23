"""F-03 (errorescms.md): CmsMediaItem width/height individuales.

Antes, ``CmsMediaItem`` solo tenia ``dimensions`` como string ``"WxH"``.
Las queries que querian filtrar/ordenar por dimension tenian que parsear
el string, fragil y no indexable.  El ``ImageOptimizer.optimize()`` ya
retornaba ``width`` y ``height`` pero el endpoint los descartaba.

Fix: columnas ``width`` y ``height`` Integer nullable + persistencia
desde upload/optimize.  ``dimensions`` string se mantiene por compat.

Tests:
  1) CRUD create con width/height → row persiste ambos + dimensions
  2) CRUD create sin width/height → row queda None (back-compat con
     callers legacy que no pasan dimensiones, ej. pdf/mp4)
  3) CRUD update parcial (solo width) → height preservado, no None-out
  4) CRUD update con dimensions string → row.dimensions persiste
  5) Schema CmsMediaRead expone width/height/dimensions via API
  6) Schema CmsMediaCreate valida ge=1 (cero o negativo reject 422)
"""
from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone

import pytest

from backend import models, schemas
from backend.crud import cms as crud_cms
from tests.conftest import seed_admin

# ── Fixtures locales ────────────────────────────────────────────────


def _seed(db_session):
    admin, persona, sede = seed_admin(
        db_session, email="cmsF03@example.com", password="testpass123"
    )
    return admin, persona, sede


# ── CRUD-direct (defense-in-depth sin API stack) ──────────────────


class TestF03MediaWidthHeight:
    """Cobertura CRUD-direct + schema-level de width/height/dimensions."""

    def test_crud_create_persists_width_height_dimensions(self, db_session):
        admin, persona, _ = _seed(db_session)

        row = crud_cms.create_cms_media_item(
            db_session,
            url="/img/hero.jpg",
            alt_text="hero",
            section="hero",
            tags=[],
            created_by=persona.id,
            filename="hero.jpg",
            mime_type="image/jpeg",
            file_size=20480,
            width=1920,
            height=1080,
            dimensions="1920x1080",
            actor_user_id=str(admin.id),
        )
        assert row.width == 1920
        assert row.height == 1080
        assert row.dimensions == "1920x1080"

    def test_crud_create_without_dimensions_leaves_none(self, db_session):
        admin, persona, _ = _seed(db_session)

        row = crud_cms.create_cms_media_item(
            db_session,
            url="/docs/pdfs/report.pdf",
            alt_text="reporte",
            section="docs",
            tags=[],
            created_by=persona.id,
            filename="report.pdf",
            mime_type="application/pdf",
            file_size=51200,
            actor_user_id=str(admin.id),
        )
        assert row.width is None
        assert row.height is None
        assert row.dimensions is None

    def test_crud_update_partial_width_preserves_height(self, db_session):
        admin, persona, _ = _seed(db_session)

        row = crud_cms.create_cms_media_item(
            db_session,
            url="/img/photo.jpg",
            alt_text="photo",
            section="gallery",
            tags=[],
            created_by=persona.id,
            width=800,
            height=600,
            dimensions="800x600",
            actor_user_id=str(admin.id),
        )

        updated = crud_cms.update_cms_media_item(
            db_session,
            row.id,
            width=1600,  # Cambia solo width
            actor_user_id=str(admin.id),
        )
        assert updated.width == 1600
        assert updated.height == 600  # Preservado, no None
        assert updated.dimensions == "800x600"  # No se modificó

    def test_crud_update_dimensions_string(self, db_session):
        admin, persona, _ = _seed(db_session)

        row = crud_cms.create_cms_media_item(
            db_session,
            url="/img/old.jpg",
            alt_text="old",
            section="hero",
            tags=[],
            created_by=persona.id,
            actor_user_id=str(admin.id),
        )

        updated = crud_cms.update_cms_media_item(
            db_session,
            row.id,
            width=1024,
            height=768,
            dimensions="1024x768",
            actor_user_id=str(admin.id),
        )
        assert updated.width == 1024
        assert updated.height == 768
        assert updated.dimensions == "1024x768"


# ── Schema-level (Pydantic validation sin DB) ──────────────────────


class TestF03Schemas:
    def test_create_rejects_zero_width(self):
        with pytest.raises(ValueError):  # pydantic ValidationError
            schemas.CmsMediaCreate(url="/x.jpg", width=0, height=10)

    def test_create_rejects_negative_height(self):
        with pytest.raises(ValueError):
            schemas.CmsMediaCreate(url="/x.jpg", width=100, height=-1)

    def test_create_accepts_none_dimensions(self):
        m = schemas.CmsMediaCreate(url="/x.jpg")
        assert m.width is None
        assert m.height is None
        assert m.dimensions is None

    def test_read_roundtrips_width_height_dimensions_from_orm(self):
        # Simula row ORM con width/height
        row = models.CmsMediaItem(
            id=_uuid.uuid4(),
            url="/img.jpg",
            alt_text="x",
            section="hero",
            tags=[],
            width=1920,
            height=1080,
            dimensions="1920x1080",
            status="active",
        )
        # Populate los timestamps requeridos por schema
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)
        read = schemas.CmsMediaRead.model_validate(row, from_attributes=True)
        assert read.width == 1920
        assert read.height == 1080
        assert read.dimensions == "1920x1080"

    def test_read_handles_all_none(self):
        row = models.CmsMediaItem(
            id=_uuid.uuid4(),
            url="/doc.pdf",
            alt_text=None,
            section="docs",
            tags=[],
            status="active",
        )
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)
        read = schemas.CmsMediaRead.model_validate(row, from_attributes=True)
        assert read.width is None
        assert read.height is None
        assert read.dimensions is None

    def test_update_partial_width_only(self):
        """Verifica que PATCH con solo width no rompa el schema."""
        u = schemas.CmsMediaUpdate(width=800)
        assert u.width == 800
        assert u.height is None
        assert u.dimensions is None  # No se envía en el PATCH
