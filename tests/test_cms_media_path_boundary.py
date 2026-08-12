"""CMS media path-boundary regressions for traversal-prefix escapes."""

from __future__ import annotations

import uuid

from backend import models
from backend.crud.cms.media import _apply_cleanup_orphan_cms_media
from backend.services.cms_media_service import _guard_path


def test_guard_path_rejects_sibling_directory_prefix_escape():
    """A sibling such as ``uploads_evil`` is not inside ``uploads``."""
    try:
        _guard_path("uploads/../uploads_evil/secret.bin")
    except ValueError as exc:
        assert str(exc) == "Invalid file path"
    else:
        raise AssertionError("guard_path accepted a sibling directory outside uploads")


def test_guard_path_rejects_symlink_escape(tmp_path, monkeypatch):
    uploads = tmp_path / "uploads"
    outside = tmp_path / "outside"
    uploads.mkdir()
    outside.mkdir()
    (outside / "secret.bin").write_bytes(b"secret")
    (uploads / "linked").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(
        "backend.services.cms_media_service._uploads_root",
        lambda: str(uploads),
    )

    try:
        _guard_path("uploads/linked/secret.bin")
    except ValueError as exc:
        assert str(exc) == "Invalid file path"
    else:
        raise AssertionError("guard_path accepted a symlink escape outside uploads")


def test_cleanup_archives_sibling_directory_prefix_escape(db_session):
    sede = models.Sede(
        id=uuid.uuid4(),
        nombre="Boundary Sede",
        ciudad="Bogotá",
        es_activa=True,
    )
    db_session.add(sede)
    db_session.flush()
    site = models.CmsSite(
        id=uuid.uuid4(),
        site_key="media-boundary",
        name="Media boundary",
        base_path="/media-boundary",
        is_active=True,
    )
    db_session.add(site)
    db_session.flush()
    persona = models.Persona(
        id=uuid.uuid4(),
        first_name="Boundary",
        last_name="Owner",
        email="boundary-owner@example.com",
        sede_id=sede.id,
        estado_vital="ACTIVO",
    )
    db_session.add(persona)
    db_session.flush()
    media = models.CmsMediaItem(
        id=uuid.uuid4(),
        url="uploads/../uploads_evil/secret.bin",
        filename="secret.bin",
        alt_text="secret",
        section="general",
        status="active",
        sede_id=sede.id,
        created_by_persona_id=persona.id,
    )
    db_session.add(media)
    db_session.commit()

    assert (
        _apply_cleanup_orphan_cms_media(
            db_session,
            sede_id=media.sede_id,
            referenced_media_ids=set(),
            permanent=True,
        )
        == 1
    )
    db_session.refresh(media)
    assert media.status == "archived"
