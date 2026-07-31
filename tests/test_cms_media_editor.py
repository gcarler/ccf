"""Tests for POST /api/cms/media/{id}/edit endpoint.

Verifies:
1. Non-destructive image edit creates a new CmsMediaItem with `_edited` suffix in filename.
2. Original media item remains unchanged in DB.
3. Axioma 3 Multi-Tenant security: cross-sede edit requests return 404.
"""

from __future__ import annotations

import io
import uuid

from backend import models
from tests.conftest import auth_headers, seed_admin


def _seed_two_sedes(db_session):
    admin_a, persona_a, sede_a = seed_admin(db_session, email="editorA@example.com", password="testpass123")
    admin_b, persona_b, sede_b = seed_admin(db_session, email="editorB@example.com", password="testpass123")
    assert sede_a.id != sede_b.id
    return (admin_a, persona_a, sede_a), (admin_b, persona_b, sede_b)


def _make_cms_media(db, persona, sede, filename="sample.png", alt_text="Sample Image"):
    m = models.CmsMediaItem(
        id=uuid.uuid4(),
        url=f"/uploads/cms/{filename}",
        filename=filename,
        alt_text=alt_text,
        section="general",
        mime_type="image/png",
        created_by_persona_id=persona.id,
        sede_id=sede.id,
        status="active",
    )
    db.add(m)
    db.flush()
    return m


# Minimal 1x1 PNG transparent pixel bytes
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?"
    b"\x03\x00\x05\xfe\x02\xfe\xa7\x35\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82"
)


class TestCmsMediaEditEndpoint:
    def test_edit_media_item_creates_new_item_with_edited_suffix(self, client, db_session):
        (admin_a, persona_a, sede_a), _ = _seed_two_sedes(db_session)
        media_orig = _make_cms_media(db_session, persona_a, sede_a, filename="hero_banner.png")

        headers = auth_headers(client, email="editorA@example.com")
        files = {"file": ("edited_canvas.png", io.BytesIO(TINY_PNG), "image/png")}
        data = {"alt_text": "Hero Banner Editado", "section": "hero"}

        resp = client.post(
            f"/api/cms/media/{media_orig.id}/edit",
            headers=headers,
            files=files,
            data=data,
        )

        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        res_data = resp.json()

        assert res_data["id"] != str(media_orig.id)
        assert "_edited" in res_data["filename"]
        assert res_data["filename"].endswith(".webp") or res_data["filename"].endswith(".png")
        assert res_data["alt_text"] == "Hero Banner Editado"

        # Verify original item was NOT modified
        orig_refreshed = db_session.query(models.CmsMediaItem).filter_by(id=media_orig.id).first()
        assert orig_refreshed is not None
        assert orig_refreshed.filename == "hero_banner.png"
        assert orig_refreshed.alt_text == "Sample Image"

    def test_edit_media_item_cross_sede_returns_404(self, client, db_session):
        (admin_a, persona_a, sede_a), (admin_b, persona_b, sede_b) = _seed_two_sedes(db_session)
        media_a = _make_cms_media(db_session, persona_a, sede_a, filename="private_a.png")

        # Admin B tries to edit Admin A's media
        headers_b = auth_headers(client, email="editorB@example.com")
        files = {"file": ("blob.png", io.BytesIO(TINY_PNG), "image/png")}

        resp = client.post(
            f"/api/cms/media/{media_a.id}/edit",
            headers=headers_b,
            files=files,
        )

        assert resp.status_code == 404
