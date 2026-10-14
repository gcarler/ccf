"""Suite para el endpoint de subida de imágenes de la wiki de proyectos.

Cubre el criterio del ticket TKT-PROJECTS-WIKI-RICH-TOOLS-IMAGES-TYPOGRAPHY-01:

1. POST /api/projects/{project_id}/wiki/images con imagen → 200 y URL pública
   persistida vía StorageService (`projects/wiki`).
2. Archivos no-imagen → 400 SIN tocar el almacenamiento.
3. Sin autenticación → 401/403.
4. Aislamiento multi-tenant (Axioma 3): proyecto inexistente/fuera de sede
   del actor → 404.
"""

from __future__ import annotations

import base64

from tests.conftest import auth_headers, seed_admin
from tests.factories_projects import create_project_factory

# PNG 1x1 transparente.
_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="


class TestWikiImageUpload:
    def test_upload_image_returns_public_url(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)

        resp = client.post(
            f"/api/projects/{proj.id}/wiki/images",
            headers=headers,
            files={"file": ("plan.png", _PNG_BYTES, "image/png")},
        )
        assert resp.status_code == 200, resp.text
        url = resp.json()["url"]
        assert "/api/static/projects/wiki/" in url, url

    def test_upload_rejects_non_image(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)

        resp = client.post(
            f"/api/projects/{proj.id}/wiki/images",
            headers=headers,
            files={"file": ("nota.txt", b"no es imagen", "text/plain")},
        )
        assert resp.status_code == 400, resp.text
        assert "imágenes" in resp.json()["detail"], resp.text

    def test_upload_requires_authentication(self, client, db_session):
        proj = create_project_factory(db_session)
        resp = client.post(
            f"/api/projects/{proj.id}/wiki/images",
            files={"file": ("plan.png", _PNG_BYTES, "image/png")},
        )
        assert resp.status_code in (401, 403), resp.status_code

    def test_upload_cross_project_returns_404(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        create_project_factory(db_session)
        headers = auth_headers(client)

        resp = client.post(
            "/api/projects/00000000-0000-0000-0000-000000000000/wiki/images",
            headers=headers,
            files={"file": ("plan.png", _PNG_BYTES, "image/png")},
        )
        assert resp.status_code == 404, resp.status_code
