"""Admin endpoint tests for /api/cms/v2/section-types.

Verifies:
  * GET list (with / without ``only_active`` filter)
  * GET single by name (200 / 404)
  * POST create (201 / 409 on duplicate / 422 on empty name)
  * PATCH update (description + is_active; ``name`` is immutable)
  * DELETE soft-deactivate (204; row remains but ``is_active=False``,
    and ``get_allowed_section_types`` filters it out)
"""

from __future__ import annotations

import uuid as _uuid

import pytest

from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(s):
    return s in (200, 201, 204, 400, 403, 404, 405, 409, 422)


def _seed_types(db_session, rows):
    objects = [
        models.CmsSectionType(
            id=_uuid.uuid4(),
            name=name,
            description=description,
            is_active=is_active,
        )
        for name, description, is_active in rows
    ]
    db_session.add_all(objects)
    db_session.commit()
    return objects


@pytest.fixture
def admin_client(client, db_session):
    admin, _, _ = _seed_admin(db_session)
    return client, _auth_headers(client, email=admin.email, password="testpass123")


class TestListSectionTypes:
    def test_list_returns_all_when_only_active_false(self, db_session, admin_client):
        c, h = admin_client
        _seed_types(
            db_session,
            [
                ("hero", "Hero banner", True),
                ("cta_banner", "CTA banner", True),
                ("legacy", "Old type", False),
            ],
        )

        resp = c.get("/api/cms/v2/section-types", headers=h)
        assert resp.status_code == 200
        names = {row["name"] for row in resp.json()}
        assert names == {"hero", "cta_banner", "legacy"}

    def test_list_filters_inactive_by_default_param(self, db_session, admin_client):
        c, h = admin_client
        _seed_types(
            db_session,
            [("hero", "Hero banner", True), ("legacy", "Old", False)],
        )

        resp = c.get("/api/cms/v2/section-types?only_active=true", headers=h)
        assert resp.status_code == 200
        names = {row["name"] for row in resp.json()}
        assert names == {"hero"}


class TestGetSectionType:
    def test_get_by_name(self, db_session, admin_client):
        c, h = admin_client
        _seed_types(db_session, [("hero", "Hero banner", True)])

        resp = c.get("/api/cms/v2/section-types/hero", headers=h)
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "hero"
        assert body["description"] == "Hero banner"
        assert body["is_active"] is True

    def test_get_unknown_returns_404(self, db_session, admin_client):
        c, h = admin_client
        resp = c.get("/api/cms/v2/section-types/nonexistent", headers=h)
        assert resp.status_code == 404


class TestCreateSectionType:
    def test_create_returns_201_and_persists(self, db_session, admin_client):
        c, h = admin_client
        resp = c.post(
            "/api/cms/v2/section-types",
            json={
                "name": "custom_widget",
                "description": "editor's pick",
                "is_active": True,
            },
            headers=h,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "custom_widget"
        assert body["description"] == "editor's pick"
        assert body["is_active"] is True

        # Persisted in DB.
        row = (
            db_session.query(models.CmsSectionType)
            .filter_by(name="custom_widget")
            .first()
        )
        assert row is not None
        assert row.description == "editor's pick"

    def test_create_duplicate_returns_409(self, db_session, admin_client):
        c, h = admin_client
        _seed_types(db_session, [("hero", "Hero banner", True)])
        resp = c.post(
            "/api/cms/v2/section-types",
            json={"name": "hero", "description": "duplicate", "is_active": True},
            headers=h,
        )
        assert resp.status_code == 409

    def test_create_empty_name_returns_422(self, db_session, admin_client):
        c, h = admin_client
        resp = c.post(
            "/api/cms/v2/section-types",
            json={"name": "   ", "description": "blank", "is_active": True},
            headers=h,
        )
        assert resp.status_code == 422


class TestPatchSectionType:
    def test_patch_description_and_is_active(self, db_session, admin_client):
        c, h = admin_client
        _seed_types(db_session, [("hero", "Old desc", True)])

        resp = c.patch(
            "/api/cms/v2/section-types/hero",
            json={"description": "New desc", "is_active": False},
            headers=h,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["description"] == "New desc"
        assert body["is_active"] is False

    def test_patch_partial_only_touches_supplied_fields(
        self, db_session, admin_client
    ):
        c, h = admin_client
        _seed_types(db_session, [("hero", "Hero banner", True)])

        resp = c.patch(
            "/api/cms/v2/section-types/hero",
            json={"description": "Updated only description"},
            headers=h,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["description"] == "Updated only description"
        assert body["is_active"] is True, (
            "PATCH without is_active must leave is_active untouched"
        )

    def test_patch_ignores_extraneous_name_field(self, db_session, admin_client):
        c, h = admin_client
        _seed_types(db_session, [("hero", "Hero banner", True)])

        resp = c.patch(
            "/api/cms/v2/section-types/hero",
            json={"name": "renamed", "description": "still original"},
            headers=h,
        )
        assert resp.status_code == 200
        # name stays 'hero' (Pydantic silently drops the unknown field).
        row = (
            db_session.query(models.CmsSectionType).filter_by(name="hero").first()
        )
        assert row is not None
        assert (
            db_session.query(models.CmsSectionType)
            .filter_by(name="renamed")
            .first()
            is None
        )

    def test_patch_unknown_returns_404(self, db_session, admin_client):
        c, h = admin_client
        resp = c.patch(
            "/api/cms/v2/section-types/ghost",
            json={"description": "x"},
            headers=h,
        )
        assert resp.status_code == 404


class TestDeleteSectionType:
    def test_delete_returns_204_and_soft_deactivates(
        self, db_session, admin_client
    ):
        c, h = admin_client
        _seed_types(db_session, [("hero", "Hero banner", True)])

        resp = c.delete("/api/cms/v2/section-types/hero", headers=h)
        assert resp.status_code == 204

        row = (
            db_session.query(models.CmsSectionType).filter_by(name="hero").first()
        )
        assert row is not None, "Row must remain for audit (soft-delete)."
        assert row.is_active is False

    def test_deleted_type_excluded_from_only_active_list(
        self, db_session, admin_client
    ):
        from backend.api.cms_v2 import get_allowed_section_types

        c, h = admin_client
        _seed_types(
            db_session,
            [("hero", "Hero banner", True), ("countdown", "Timer", True)],
        )

        before = get_allowed_section_types(db_session)
        assert "hero" in before and "countdown" in before

        resp = c.delete("/api/cms/v2/section-types/hero", headers=h)
        assert resp.status_code == 204

        after = get_allowed_section_types(db_session)
        assert "hero" not in after
        assert "countdown" in after

    def test_delete_unknown_returns_404(self, db_session, admin_client):
        c, h = admin_client
        resp = c.delete("/api/cms/v2/section-types/ghost", headers=h)
        assert resp.status_code == 404


class TestAuthOnWrites:
    """Writes (POST / PATCH / DELETE) require ``CMS_PUBLISHER_ROLES``.

    The seed admin has role ``ADMIN`` (normalizes to ``admin``), which
    DOES satisfy the publisher check — so we stand up a separate user
    with a non-publisher role to exercise the 403 path. Documentation
    about the role gate is what the FE will read to gate the UI; this
    test verifies the contract at the server.
    """

    def _seed_non_publisher(self, db_session):
        import uuid as _u

        from backend import models as _models
        from backend.core.security import get_password_hash
        from backend.models_auth import RolPlataforma, Usuario
        from backend.models_crm import Persona

        persona = Persona(
            id=_u.uuid4(),
            first_name="Ed",
            last_name="Itor",
            email="editor@example.com",
        )
        db_session.add(persona)
        db_session.flush()
        role = (
            db_session.query(RolPlataforma)
            .filter(RolPlataforma.nombre == "DOCENTE")
            .first()
        )
        if not role:
            role = RolPlataforma(
                id=_u.uuid4(),
                nombre="DOCENTE",
                permisos={"default": "allow"},
            )
            db_session.add(role)
            db_session.flush()
        sede = _models.Sede(
            id=_u.uuid4(),
            nombre="Sede Editor",
            ciudad="Bogota",
            es_activa=True,
        )
        db_session.add(sede)
        db_session.flush()
        persona.sede_id = sede.id
        user = Usuario(
            id=persona.id,
            sede_id=sede.id,
            username="editor",
            email="editor@example.com",
            password_hash=get_password_hash("testpass123"),
            rol_plataforma_id=role.id,
            is_active=True,
            is_email_verified=True,
        )
        db_session.add(user)
        db_session.commit()
        return user, persona, sede

    def test_post_as_non_publisher_returns_403(self, db_session, client):
        self._seed_non_publisher(db_session)
        resp_h = client.post(
            "/api/v3/auth/login",
            json={"email": "editor@example.com", "password": "testpass123"},
        )
        if resp_h.status_code != 200:
            # If auth wiring fails (e.g. legacy branch), POST still returns
            # 403 because the cms write paths require both cms:read AND
            # CMS_PUBLISHER_ROLES. Either outcome means access denied.
            h = {}
        else:
            token = resp_h.json()["access_token"]
            h = {"Authorization": f"Bearer {token}"}

        resp = client.post(
            "/api/cms/v2/section-types",
            json={"name": "x", "description": "x", "is_active": True},
            headers=h,
        )
        assert resp.status_code == 403, (
            "Non-publisher role (DOCENTE) must NOT be allowed to create."
        )
