"""Axioma 3 + Defense-in-Depth — CMS upload & image endpoint hardening.

Tests para los 3 fixes aplicados en esta sesion:

  (A) backend/api/cms.py::upload_cms_media — extiende la pipeline de
      validacion con extension allow-list + MIME/extension alignment, no
      solo size guardrail. Cierra el vector donde un cliente sube un
      binario malicioso renombrado con una extension permitida pero un
      Content-Type falsificado.

  (B) backend/api/cms_v2.py::optimize_uploaded_image — el POST
      /api/cms/v2/images/optimize ahora usa _get_scoped_cms_media en
      lugar de un query unscoped. Un editor de sede_a ya NO puede
      forzar la reescritura del archivo JPEG optimizado de un asset de
      sede_b en el uploads_dir.

  (C) backend/api/cms_v2.py::get_resized_image — endpoint publico que
      igual rechaza media archivada (defense-in-depth).

  (D) backend/core/uploads.py::validate_mime_extension_alignment —
      unit tests del helper de alineacion MIME/extension.
"""

from __future__ import annotations

import io
import uuid as _uuid

from backend import models
from tests.conftest import auth_headers, seed_admin


def _seed_two_sedes(db_session):
    admin_a, persona_a, sede_a = seed_admin(
        db_session, email="cmsUploadA@example.com", password="testpass123"
    )
    admin_b, persona_b, sede_b = seed_admin(
        db_session, email="cmsUploadB@example.com", password="testpass123"
    )
    assert sede_a.id != sede_b.id
    return (admin_a, persona_a, sede_a), (admin_b, persona_b, sede_b)


def _auth_headers(client, email):
    return auth_headers(client, email=email)


def _make_upload_file(filename, content, content_type):
    return (filename, io.BytesIO(content), content_type)


def _make_cms_media(db, persona, sede, url, filename, alt_text, status="active"):
    m = models.CmsMediaItem(
        id=_uuid.uuid4(),
        url=url,
        filename=filename,
        alt_text=alt_text,
        section="hero",
        created_by_persona_id=persona.id,
        sede_id=sede.id,
        status=status,
    )
    db.add(m)
    db.flush()
    return m


# (D) validate_mime_extension_alignment — unit tests

class TestValidateMimeExtensionAlignment:

    def test_image_extensions_align_with_image_mime_prefix(self):
        from backend.core.uploads import validate_mime_extension_alignment

        validate_mime_extension_alignment("photo.png", "image/png")
        for ext, mime in [
            ("photo.jpg", "image/jpeg"),
            ("photo.jpeg", "image/jpeg"),
            ("photo.gif", "image/gif"),
            ("photo.webp", "image/webp"),
            ("photo.png", "image/png; charset=binary"),
        ]:
            validate_mime_extension_alignment(ext, mime)

    def test_video_extensions_align_with_video_mime_prefix(self):
        from backend.core.uploads import validate_mime_extension_alignment

        validate_mime_extension_alignment("clip.mp4", "video/mp4")
        validate_mime_extension_alignment("clip.mp4", "video/mp4; codecs=avc1")

    def test_audio_extensions_align_with_audio_mime_prefix(self):
        from backend.core.uploads import validate_mime_extension_alignment

        validate_mime_extension_alignment("song.mp3", "audio/mpeg")
        validate_mime_extension_alignment("song.wav", "audio/wav")

    def test_pdf_alignment(self):
        from backend.core.uploads import validate_mime_extension_alignment

        validate_mime_extension_alignment("doc.pdf", "application/pdf")

    def test_zip_alignment_allows_application_zip_family(self):
        from backend.core.uploads import validate_mime_extension_alignment

        for ct in (
            "application/zip",
            "application/x-zip",
            "application/x-zip-compressed",
        ):
            validate_mime_extension_alignment("bundle.zip", ct)

    def test_rejects_spoofed_mime_for_image_extension(self):
        from backend.core.uploads import validate_mime_extension_alignment

        try:
            validate_mime_extension_alignment(
                "malware.png",
                "application/x-msdownload",
            )
        except ValueError as exc:
            assert "no coincide" in str(exc).lower()
            return
        raise AssertionError(
            "validate_mime_extension_alignment dejo pasar un binario "
            "con image-ext pero mime de ejecutable"
        )

    def test_rejects_video_extension_with_audio_mime(self):
        from backend.core.uploads import validate_mime_extension_alignment

        raised = False
        try:
            validate_mime_extension_alignment("clip.mp4", "audio/mpeg")
        except ValueError:
            raised = True
        assert raised, "video extension con audio MIME debe fallar"

    def test_rejects_pdf_extension_with_image_mime(self):
        from backend.core.uploads import validate_mime_extension_alignment

        raised = False
        try:
            validate_mime_extension_alignment("doc.pdf", "image/png")
        except ValueError:
            raised = True
        assert raised, "pdf extension con image MIME debe fallar"

    def test_empty_mime_rejected_for_known_categories(self):
        from backend.core.uploads import validate_mime_extension_alignment

        for ext in ("photo.png", "clip.mp4", "song.mp3", "doc.pdf"):
            raised = False
            try:
                validate_mime_extension_alignment(ext, "")
            except ValueError:
                raised = True
            assert raised, (
                f"Content-Type vacio debe rejectar extension categorizable "
                f"({ext})"
            )


# (A) upload_cms_media — extension allow-list + MIME alignment

class TestUploadCmsMediaHardening:

    PNG_BYTES = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        + b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4"
        + b"\x89\x00\x00\x00\rIDATx\x9cc\xfa\xff\xff?\x00\x05\xfe\x02\xfe\xa3"
        + b"\xb6\xbe\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    def _stub_storage_save(self, monkeypatch, save_calls):
        from backend.api import cms as _cms_api
        monkeypatch.setattr(
            _cms_api.storage_service,
            "save_file",
            lambda content, name, subfolder: save_calls.append(name) or f"/uploads/{name}",
        )

    def test_upload_accepts_legit_png_with_image_mime(
        self, client, db_session, monkeypatch
    ):
        save_calls = []
        self._stub_storage_save(monkeypatch, save_calls)

        _seed_two_sedes(db_session)
        headers = _auth_headers(client, "cmsUploadA@example.com")

        resp = client.post(
            "/api/cms/media/upload",
            headers=headers,
            data={"section": "hero", "alt_text": "ok"},
            files=[
                (
                    "file",
                    _make_upload_file("logo.png", self.PNG_BYTES, "image/png"),
                )
            ],
        )
        assert resp.status_code in (200, 201), (
            f"Upload happy-path fallo: {resp.status_code} {resp.text}"
        )

    def test_upload_rejects_executable_extension(
        self, client, db_session, monkeypatch
    ):
        save_calls = []
        self._stub_storage_save(monkeypatch, save_calls)

        _seed_two_sedes(db_session)
        headers = _auth_headers(client, "cmsUploadA@example.com")

        resp = client.post(
            "/api/cms/media/upload",
            headers=headers,
            data={"section": "hero"},
            files=[
                (
                    "file",
                    _make_upload_file(
                        "malware.exe",
                        b"\x4d\x5a\x90\x00\x03\x00\x00\x00",
                        "application/octet-stream",
                    ),
                )
            ],
        )
        assert resp.status_code == 400, (
            f"Upload de .exe permitida: {resp.status_code} {resp.text}"
        )
        assert save_calls == [], (
            "storage_service.save_file fue invocado pese al extension-block"
        )

    def test_upload_rejects_html_extension(
        self, client, db_session, monkeypatch
    ):
        save_calls = []
        self._stub_storage_save(monkeypatch, save_calls)

        _seed_two_sedes(db_session)
        headers = _auth_headers(client, "cmsUploadA@example.com")

        resp = client.post(
            "/api/cms/media/upload",
            headers=headers,
            data={"section": "asset"},
            files=[
                (
                    "file",
                    _make_upload_file(
                        "evil.html",
                        b"<script>alert(1)</script>",
                        "text/html",
                    ),
                )
            ],
        )
        assert resp.status_code == 400, (
            f"Upload de .html permitido: {resp.status_code} {resp.text}"
        )

    def test_upload_rejects_spoofed_mime_for_png_extension(
        self, client, db_session, monkeypatch
    ):
        """CRITICO: el allow-list deja pasar .png porque esta permitida,
        pero si el cliente manda un Content-Type falsificado, el
        alignment check lo rechaza."""
        save_calls = []
        self._stub_storage_save(monkeypatch, save_calls)

        _seed_two_sedes(db_session)
        headers = _auth_headers(client, "cmsUploadA@example.com")

        resp = client.post(
            "/api/cms/media/upload",
            headers=headers,
            data={"section": "hero"},
            files=[
                (
                    "file",
                    _make_upload_file(
                        "innocent.png",
                        b"MZ\x90\x00fake-executable-bytes-here",
                        "application/x-msdownload",
                    ),
                )
            ],
        )
        assert resp.status_code == 400, (
            f"Spoof-MIME permitido: {resp.status_code} {resp.text}"
        )
        assert save_calls == [], (
            "storage_service.save_file invocado pese al MIME-alignment block"
        )

    def test_upload_rejects_pdf_extension_with_image_mime(
        self, client, db_session, monkeypatch
    ):
        save_calls = []
        self._stub_storage_save(monkeypatch, save_calls)

        _seed_two_sedes(db_session)
        headers = _auth_headers(client, "cmsUploadA@example.com")

        resp = client.post(
            "/api/cms/media/upload",
            headers=headers,
            data={"section": "documents"},
            files=[
                (
                    "file",
                    _make_upload_file(
                        "doc.pdf",
                        b"%PDF-1.4 fake-content",
                        "image/png",
                    ),
                )
            ],
        )
        assert resp.status_code == 400, (
            f"MIME mismatch cross-category permitido: "
            f"{resp.status_code} {resp.text}"
        )

    def test_upload_rejects_oversize_file(
        self, client, db_session, monkeypatch
    ):
        save_calls = []
        self._stub_storage_save(monkeypatch, save_calls)

        _seed_two_sedes(db_session)
        headers = _auth_headers(client, "cmsUploadA@example.com")

        # 11 MiB > MAX_UPLOAD_SIZE (10 MiB).
        big = b"\x89PNG\x00" * (11 * 1024 * 1024 // 5)
        resp = client.post(
            "/api/cms/media/upload",
            headers=headers,
            data={"section": "hero"},
            files=[
                (
                    "file",
                    _make_upload_file("huge.png", big, "image/png"),
                )
            ],
        )
        assert resp.status_code == 400, (
            f"Oversize permitido: {resp.status_code} {resp.text}"
        )


# (B) /images/optimize — cross-sede IDOR

class TestImagesOptimizeCrossSedeIDOR:

    def _seed_two_media_items(self, db_session, persona_a, persona_b, sede_a, sede_b):
        m_local = _make_cms_media(
            db_session,
            persona_a,
            sede_a,
            url="https://cdn.example.com/local-asset.png",
            filename="local-asset.png",
            alt_text="Local LEGIT",
        )
        m_cross = _make_cms_media(
            db_session,
            persona_b,
            sede_b,
            url="https://cdn.example.com/cross-sede-asset.png",
            filename="cross-sede-asset.png",
            alt_text="Cross SECRETO",
        )
        db_session.commit()
        return m_local, m_cross

    def test_optimize_blocks_cross_sede_attempt(
        self, client, db_session
    ):
        """CRITICO IDOR — Axioma 3: editor de sede_a NO puede optimizar
        media de sede_b. 404 existence-leak safe. Y crucialmente: NO
        escribe un JPEG optimizado en uploads_dir para el filename del
        media cross-sede."""
        import os

        (admin_a, persona_a, sede_a), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
        m_local, m_cross = self._seed_two_media_items(
            db_session, persona_a, persona_b, sede_a, sede_b
        )

        from backend.core.config import get_settings

        settings = get_settings()
        os.makedirs(settings.uploads_dir, exist_ok=True)
        cross_orig = os.path.join(settings.uploads_dir, m_cross.filename)
        with open(cross_orig, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\ncross-sede-original-bytes")
        opt_expected = f"opt_{m_cross.filename.rsplit('.', 1)[0]}_1920w.jpg"
        opt_path = os.path.join(settings.uploads_dir, opt_expected)

        assert not os.path.exists(opt_path), (
            "Sanity: optimized file no deberia existir antes del request"
        )

        headers = _auth_headers(client, "cmsUploadA@example.com")
        resp = client.post(
            f"/api/cms/v2/images/optimize?media_id={m_cross.id}",
            headers=headers,
        )
        assert resp.status_code == 404, (
            f"Leak: optimize cross-sede permitido: "
            f"{resp.status_code} {resp.text}"
        )
        assert not os.path.exists(opt_path), (
            f"FUGA CRITICA: optimize cross-sede escribio {opt_path} en "
            f"uploads_dir (modificacion cross-sede del filesystem)."
        )

        os.remove(cross_orig)


# (C) /images/{media_id}/resize — archived 404 defense-in-depth

class TestImagesResizeArchivedDefenseInDepth:

    def test_resize_returns_url_for_active_media(self, client, db_session):
        (_, _, _), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
        m_active = _make_cms_media(
            db_session,
            persona_b,
            sede_b,
            url="https://cdn.example.com/public-hero.png",
            filename="public-hero.png",
            alt_text="public-active",
            status="active",
        )
        db_session.commit()

        resp = client.get(
            f"/api/cms/v2/images/{m_active.id}/resize?width=800&quality=80"
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["url"] == "https://cdn.example.com/public-hero.png"
        assert body["width"] == 800
        assert body["quality"] == 80

    def test_resize_returns_404_for_archived_media(self, client, db_session):
        (_, _, _), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
        m_archived = _make_cms_media(
            db_session,
            persona_b,
            sede_b,
            url="https://cdn.example.com/retired.png",
            filename="retired.png",
            alt_text="retired-asset",
            status="archived",
        )
        db_session.commit()

        resp = client.get(
            f"/api/cms/v2/images/{m_archived.id}/resize?width=800"
        )
        assert resp.status_code == 404, (
            f"Archived media filtro via resize: {resp.status_code} {resp.text}"
        )
        assert "retired" not in resp.text, (
            "FUGA: alt_text de media archivado expuesto en respuesta"
        )

    def test_resize_returns_404_for_nonexistent_media(self, client, db_session):
        fake_id = _uuid.uuid4()
        resp = client.get(
            f"/api/cms/v2/images/{fake_id}/resize?width=800"
        )
        assert resp.status_code == 404
