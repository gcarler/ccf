"""Unit tests for backend.services.cms_media_service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.services.cms_media_service import (
    _guard_path,
    delete_cms_media,
    optimize_cms_media,
    upload_cms_media,
)


class TestGuardPath:
    @pytest.mark.parametrize(
        "url",
        [
            "/api/static/cms/logo.png",
            "/static/cms/logo.png",
            "/uploads/cms/logo.png",
            "uploads/cms/logo.png",
        ],
    )
    def test_guard_path_accepts_supported_local_url_forms(self, url):
        path = _guard_path(url)
        assert path.endswith("uploads/cms/logo.png")

    def test_guard_path_rejects_traversal(self):
        with pytest.raises(ValueError, match="Invalid file path"):
            _guard_path("uploads/../../etc/passwd")

    def test_guard_path_rejects_absolute_outside_root(self):
        with pytest.raises(ValueError, match="Invalid file path"):
            _guard_path("/etc/passwd")


class TestUploadCmsMedia:
    PNG_BYTES = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        + b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4"
        + b"\x89\x00\x00\x00\rIDATx\x9cc\xfa\xff\xff?\x00\x05\xfe\x02\xfe\xa3"
        + b"\xb6\xbe\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    def test_upload_rejects_oversize(self, db_session):
        from backend.services.cms_media_service import MAX_UPLOAD_SIZE

        big = b"x" * (MAX_UPLOAD_SIZE + 1)
        with pytest.raises(ValueError, match="exceeds maximum size"):
            upload_cms_media(
                db_session,
                content=big,
                filename="huge.png",
                content_type="image/png",
                actor_user_id="00000000-0000-0000-0000-000000000001",
            )

    def test_upload_rejects_bad_extension(self, db_session):
        with pytest.raises(ValueError):
            upload_cms_media(
                db_session,
                content=b"MZ executable bytes",
                filename="malware.exe",
                content_type="application/octet-stream",
                actor_user_id="00000000-0000-0000-0000-000000000001",
            )

    def test_upload_rejects_mime_mismatch(self, db_session):
        with pytest.raises(ValueError, match="no coincide"):
            upload_cms_media(
                db_session,
                content=b"x",
                filename="photo.png",
                content_type="application/x-msdownload",
                actor_user_id="00000000-0000-0000-0000-000000000001",
            )

    @patch("backend.services.cms_media_service.storage_service")
    def test_upload_happy_path(self, mock_storage, db_session):
        from tests.conftest import seed_admin

        mock_storage.save_file.return_value = "/uploads/cms/logo.png"

        # Minimal required DB setup: persona + sede + user so CRUD resolves.
        admin, persona, sede = seed_admin(db_session, email="cmsmedia@x.com", password="testpass123")

        row = upload_cms_media(
            db_session,
            content=self.PNG_BYTES,
            filename="logo.png",
            content_type="image/png",
            section="hero",
            alt_text="Logo",
            tags=["branding"],
            optimize=False,
            actor_user_id=str(admin.id),
        )
        assert row.url == "/uploads/cms/logo.png"
        assert row.section == "hero"
        assert row.alt_text == "Logo"
        assert row.tags == ["branding"]


class TestOptimizeCmsMedia:
    @patch("backend.services.cms_media_service.storage_service")
    @patch("backend.services.cms_media_service.ImageOptimizer")
    def test_optimize_rejects_non_image(self, mock_optimizer, mock_storage, db_session):
        item = MagicMock()
        item.mime_type = "application/pdf"
        with pytest.raises(ValueError, match="Only images can be optimized"):
            optimize_cms_media(db_session, item, actor_user_id="x")


class TestDeleteCmsMedia:
    def test_delete_permanent_rejects_traversal(self, db_session):
        item = MagicMock()
        item.url = "uploads/../../etc/passwd"
        with pytest.raises(ValueError, match="Invalid file path"):
            delete_cms_media(db_session, item, permanent=True, actor_user_id="x")
