"""Contract coverage for remaining CMS media CRUD/service branches."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from backend import models
from backend.crud.cms.media import (
    _apply_cleanup_orphan_cms_media,
    delete_cms_media_item,
    get_cms_media_item,
    list_cms_media_items,
    update_cms_media_item,
)
from backend.services.cms_media_service import optimize_cms_media, upload_cms_media
from tests.conftest import seed_admin


def _media(db, *, sede_id, persona_id, url, filename, status="active", alt_text="alt"):
    row = models.CmsMediaItem(
        id=uuid.uuid4(),
        url=url,
        filename=filename,
        alt_text=alt_text,
        section="hero",
        tags=["one"],
        mime_type="image/png",
        status=status,
        sede_id=sede_id,
        created_by_persona_id=persona_id,
        file_size=10,
    )
    db.add(row)
    db.flush()
    return row


def test_media_list_filters_search_section_archived_and_pagination(db_session):
    admin, persona, sede = seed_admin(db_session, email="media-list-contract@example.com")
    _media(db_session, sede_id=sede.id, persona_id=persona.id, url="/uploads/hero.png", filename="hero.png")
    _media(
        db_session,
        sede_id=sede.id,
        persona_id=persona.id,
        url="/uploads/archive.pdf",
        filename="archive.pdf",
        status="archived",
        alt_text="old document",
    )
    _media(
        db_session,
        sede_id=sede.id,
        persona_id=persona.id,
        url="/uploads/logo.png",
        filename="logo.png",
        alt_text="brand logo",
    ).section = "branding"
    db_session.commit()

    items, total = list_cms_media_items(db_session, query="logo", section="branding", skip=0, limit=1)
    assert total == 1
    assert [item.filename for item in items] == ["logo.png"]

    active, active_total = list_cms_media_items(db_session)
    assert active_total == 2
    assert all(item.status != "archived" for item in active)

    all_items, all_total = list_cms_media_items(db_session, include_archived=True, limit=10)
    assert all_total == 3
    assert any(item.status == "archived" for item in all_items)


def test_media_update_normalizes_fields_and_missing_returns_none(db_session):
    admin, persona, sede = seed_admin(db_session, email="media-update-contract@example.com")
    row = _media(
        db_session,
        sede_id=sede.id,
        persona_id=persona.id,
        url="/uploads/old.png",
        filename="old.png",
    )
    db_session.commit()

    assert get_cms_media_item(db_session, uuid.uuid4()) is None
    updated = update_cms_media_item(
        db_session,
        row.id,
        url="/uploads/new.png",
        alt_text="New alt",
        section="branding",
        tags=["new"],
        filename="new.png",
        mime_type="image/webp",
        file_size=42,
        width=20,
        height=10,
        dimensions="20x10",
        status=" ARCHIVED ",
        actor_user_id=str(admin.id),
    )
    assert updated is not None
    assert updated.url == "/uploads/new.png"
    assert updated.status == "archived"
    assert updated.tags == ["new"]
    assert updated.dimensions == "20x10"

    assert update_cms_media_item(db_session, uuid.uuid4(), actor_user_id=str(admin.id)) is None


def test_media_delete_missing_and_soft_delete(db_session):
    admin, persona, sede = seed_admin(db_session, email="media-delete-contract@example.com")
    assert delete_cms_media_item(db_session, uuid.uuid4(), actor_user_id=str(admin.id)) is False
    row = _media(
        db_session,
        sede_id=sede.id,
        persona_id=persona.id,
        url="/uploads/soft.png",
        filename="soft.png",
    )
    db_session.commit()
    assert delete_cms_media_item(db_session, row.id, actor_user_id=str(admin.id)) is True
    db_session.refresh(row)
    assert row.status == "archived"


def test_service_optimize_missing_file_and_non_image(db_session):
    non_image = MagicMock(mime_type="application/pdf")
    with pytest.raises(ValueError, match="Only images"):
        optimize_cms_media(db_session, non_image, actor_user_id="actor")

    image = MagicMock(mime_type="image/png", url="/uploads/missing.png", filename="missing.png")
    with patch("backend.services.cms_media_service.os.path.exists", return_value=False):
        with pytest.raises(ValueError, match="Original file not found"):
            optimize_cms_media(db_session, image, actor_user_id="actor")


def test_service_upload_falls_back_when_optimizer_fails(db_session, monkeypatch):
    admin, _, _ = seed_admin(db_session, email="media-fallback-contract@example.com")
    saved: list[tuple[bytes, str]] = []
    monkeypatch.setattr(
        "backend.services.cms_media_service.storage_service.save_file",
        lambda content, name, subfolder: saved.append((content, name)) or "/uploads/fallback.png",
    )
    monkeypatch.setattr(
        "backend.services.cms_media_service.ImageOptimizer.optimize",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("optimizer unavailable")),
    )
    row = upload_cms_media(
        db_session,
        content=b"png-bytes",
        filename="fallback.png",
        content_type="image/png",
        optimize=True,
        actor_user_id=str(admin.id),
    )
    assert row.filename == "fallback.png"
    assert saved == [(b"png-bytes", "fallback.png")]


def test_cleanup_hard_delete_removes_missing_physical_file(db_session, monkeypatch):
    sede = models.Sede(
        id=uuid.uuid4(), nombre="Cleanup Sede", ciudad="Bogotá", es_activa=True
    )
    persona = models.Persona(
        id=uuid.uuid4(), first_name="Cleanup", last_name="Owner", email="cleanup-owner@example.com", sede_id=sede.id, estado_vital="ACTIVO"
    )
    db_session.add_all([sede, persona])
    db_session.flush()
    monkeypatch.setattr("backend.crud.cms.media.get_settings", lambda: type("Settings", (), {"uploads_dir": "/tmp/ccf-test-uploads"})())
    row = _media(
        db_session,
        sede_id=sede.id,
        persona_id=persona.id,
        url="/uploads/already-gone.png",
        filename="already-gone.png",
    )
    db_session.commit()
    assert _apply_cleanup_orphan_cms_media(
        db_session, sede_id=sede.id, referenced_media_ids=set(), permanent=True
    ) == 1
    assert db_session.get(models.CmsMediaItem, row.id) is None
