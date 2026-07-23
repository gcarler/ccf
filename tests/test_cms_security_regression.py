"""Tests de regresión de seguridad para el módulo CMS v2.

Esta suite cubre tres vectores críticos identificados en la auditoría de
seguridad del CMS:

1. Tenant isolation robusta: un usuario sin sede NO es superadmin por
   defecto; el rol explícito debe conceder alcance global.
2. Sanitización XSS de ``props_json`` antes de persistir secciones CMS
   tanto en creación como en actualización.
3. Manejo de concurrencia en creación (409 vs 500 bajo unique-key races).
4. IDOR cross-sede en CMS v2 (sites, sections, menu items).
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from backend.core.sanitize_html import sanitize_html
from backend.schemas.cms_v2_sections import validate_section_props
from tests.conftest import auth_headers, seed_admin, seed_user_with_role


class _FakeRole:
    def __init__(self, nombre: str):
        self.nombre = nombre


class _FakeUser:
    def __init__(self, role_name: str | None = None):
        self.role = role_name
        self.rol_plataforma = None if role_name is None else _FakeRole(role_name)


class TestTenantIsolation:
    """Cubre el doble chequeo sede + rol en ``_assert_site_sede_scope``."""

    def test_actor_without_sede_and_non_global_role_gets_404(self):
        from backend.api.cms_v2 import _assert_site_sede_scope

        site = MagicMock()
        site.sede_id = uuid.uuid4()
        user = _FakeUser(role_name="pastor")  # rol pastoral sin sede -> no global

        with pytest.raises(HTTPException) as exc:
            _assert_site_sede_scope(site, actor_sede=None, current_user=user)
        assert exc.value.status_code == 404

    def test_actor_with_sede_cannot_access_other_sede_site(self):
        from backend.api.cms_v2 import _assert_site_sede_scope

        actor_sede = uuid.uuid4()
        site = MagicMock()
        site.sede_id = uuid.uuid4()
        user = _FakeUser(role_name="pastor")

        with pytest.raises(HTTPException) as exc:
            _assert_site_sede_scope(site, actor_sede=actor_sede, current_user=user)
        assert exc.value.status_code == 404

    def test_global_admin_bypasses_sede_scope(self):
        from backend.api.cms_v2 import _assert_site_sede_scope

        site = MagicMock()
        site.sede_id = uuid.uuid4()
        user = _FakeUser(role_name="admin")

        # No debe lanzar excepción
        _assert_site_sede_scope(site, actor_sede=None, current_user=user)

    def test_actor_with_sede_cannot_access_orphan_site(self):
        # C-01: un site huérfano (sede_id=None, por ondelete SET NULL
        # histórico) NO debe ser accesible por un actor con sede —
        # cierra el leak multi-tenant documentado en la auditoría.
        from backend.api.cms_v2 import _assert_site_sede_scope

        actor_sede = uuid.uuid4()
        site = MagicMock()
        site.sede_id = None
        user = _FakeUser(role_name="pastor")

        with pytest.raises(HTTPException) as exc:
            _assert_site_sede_scope(site, actor_sede=actor_sede, current_user=user)
        assert exc.value.status_code == 404

    def test_global_admin_can_access_orphan_site(self):
        # C-01: un admin global SÍ puede operar sites huérfanos para
        # reasignarlos o limpiarlos — esa responsabilidad no puede caer
        # en actores con sede.
        from backend.api.cms_v2 import _assert_site_sede_scope

        site = MagicMock()
        site.sede_id = None
        user = _FakeUser(role_name="admin")

        # No debe lanzar excepción
        _assert_site_sede_scope(site, actor_sede=None, current_user=user)


class TestSanitizeHtml:
    """Cubre la sanitización XSS de campos HTML en props_json."""

    def test_script_tags_are_removed(self):
        dirty = "<script>alert('xss')</script><p>hello</p>"
        clean = sanitize_html(dirty)
        assert "<script>" not in clean
        assert "alert(" not in clean
        assert "<p>hello</p>" in clean

    def test_onclick_attribute_is_removed(self):
        dirty = '<a href="/ok" onclick="alert(1)">link</a>'
        clean = sanitize_html(dirty)
        assert "onclick" not in clean
        assert 'href="/ok"' in clean

    def test_javascript_url_is_removed(self):
        dirty = '<a href="javascript:alert(1)">click</a>'
        clean = sanitize_html(dirty)
        assert "javascript:" not in clean

    def test_allowed_tags_preserved(self):
        dirty = "<p>para</p><b>bold</b><i>italic</i><ul><li>item</li></ul>"
        clean = sanitize_html(dirty)
        for tag in ["p", "b", "i", "ul", "li"]:
            assert f"<{tag}" in clean

    def test_validate_section_props_sanitizes_collapsible_html(self):
        props = {
            "title": "Info",
            "content_html": "<script>alert('xss')</script><p>safe</p>",
        }
        result = validate_section_props("collapsible", props)
        assert "<script>" not in result["content_html"]
        assert "<p>safe</p>" in result["content_html"]

    def test_validate_section_props_sanitizes_popup_body(self):
        props = {
            "title": "Aviso",
            "body": "<img src=x onerror=alert(1)><p>text</p>",
        }
        result = validate_section_props("popup_banner", props)
        assert "onerror" not in result["body"]
        assert "<p>text</p>" in result["body"]


class TestRaceConditionHandling:
    """Cubre la conversión de IntegrityError en 409 controlado."""

    def test_create_cms_site_returns_none_on_integrity_error(self, monkeypatch):
        from backend import schemas
        from backend.crud.cms import create_cms_site

        payload = schemas.CmsSiteCreate(
            site_key="faro",
            name="Faro",
            base_path="/faro",
            is_active=True,
            sede_id=None,
        )
        db = MagicMock()
        # Simulate a Postgres unique-key violation (23505)
        orig = Exception("duplicate key value violates unique constraint")
        setattr(orig, "pgcode", "23505")
        db.commit.side_effect = IntegrityError("stmt", "params", orig)
        db.rollback.return_value = None
        db.refresh.side_effect = lambda row: row

        result = create_cms_site(db, payload, commit_with_conflict_check=True)
        assert result is None
        db.rollback.assert_called_once()

    def test_create_cms_site_commits_normally_when_no_conflict(self, monkeypatch):
        from backend import schemas
        from backend.crud.cms import create_cms_site

        payload = schemas.CmsSiteCreate(
            site_key="faro",
            name="Faro",
            base_path="/faro",
            is_active=True,
            sede_id=None,
        )
        db = MagicMock()
        db.commit.return_value = None
        db.rollback.return_value = None
        db.refresh.side_effect = lambda row: row

        result = create_cms_site(db, payload, commit_with_conflict_check=True)
        assert result is not None
        assert db.rollback.called is False


class TestPatchSectionSecurity:
    """Cubre que PATCH /cms/v2/sites/{site}/pages/{slug}/sections/{id}
    sanitiza y valida ``props_json`` antes de persistir."""

    def test_patch_section_sanitizes_xss_in_props_json(self, client, db_session):
        from backend import models

        admin, _, _ = seed_admin(db_session, email="cms-patch-admin@example.com")
        site = models.CmsSite(
            id=uuid.uuid4(),
            site_key="test-site",
            name="Test Site",
            base_path="/test",
            is_active=True,
        )
        db_session.add(site)
        db_session.flush()
        page = models.CmsPage(
            id=uuid.uuid4(),
            site_id=site.id,
            slug="home",
            title="Home",
            status="draft",
        )
        db_session.add(page)
        db_session.flush()
        section = models.CmsSection(
            id=uuid.uuid4(),
            page_id=page.id,
            section_key="collapsible-1",
            type="collapsible",
            props_json={"title": "Info", "content_html": "<p>safe</p>"},
            sort_order=0,
            is_visible=True,
            status="active",
        )
        db_session.add(section)
        db_session.commit()

        headers = auth_headers(client, email="cms-patch-admin@example.com")
        resp = client.patch(
            f"/api/cms/v2/sites/test-site/pages/home/sections/{section.id}",
            headers=headers,
            json={
                "props_json": {
                    "title": "Info",
                    "content_html": "<script>alert('xss')</script><p>safe</p>",
                }
            },
        )
        assert resp.status_code == 200, f"PATCH section failed: {resp.status_code} {resp.text}"
        data = resp.json()
        assert "<script>" not in data["props_json"]["content_html"]
        assert "<p>safe</p>" in data["props_json"]["content_html"]

    def test_patch_section_rejects_invalid_props_schema(self, client, db_session):
        from backend import models

        admin, _, _ = seed_admin(db_session, email="cms-patch-admin2@example.com")
        site = models.CmsSite(
            id=uuid.uuid4(),
            site_key="test-site2",
            name="Test Site 2",
            base_path="/test2",
            is_active=True,
        )
        db_session.add(site)
        db_session.flush()
        page = models.CmsPage(
            id=uuid.uuid4(),
            site_id=site.id,
            slug="home",
            title="Home",
            status="draft",
        )
        db_session.add(page)
        db_session.flush()
        section = models.CmsSection(
            id=uuid.uuid4(),
            page_id=page.id,
            section_key="button-1",
            type="button",
            props_json={"buttons": []},
            sort_order=0,
            is_visible=True,
            status="active",
        )
        db_session.add(section)
        db_session.commit()

        headers = auth_headers(client, email="cms-patch-admin2@example.com")
        resp = client.patch(
            f"/api/cms/v2/sites/test-site2/pages/home/sections/{section.id}",
            headers=headers,
            json={
                "type": "button",
                "props_json": {
                    "buttons": [
                        {"label": "Click", "href": "/", "variant": "malicious", "size": "md"}
                    ]
                },
            },
        )
        assert resp.status_code == 422, (
            f"Expected 422 for invalid props schema, got {resp.status_code}: {resp.text}"
        )


class TestCmsV2IdorCrossSede:
    """IDOR cross-sede para CMS v2 sites, sections y menu items."""

    PASTOR_A_EMAIL = "cms-idor-pastor-a@example.com"
    PASTOR_B_EMAIL = "cms-idor-pastor-b@example.com"

    def _seed_two_pastors(self, db_session):
        from backend import models

        sede_a = models.Sede(id=uuid.uuid4(), nombre="Sede A", ciudad="Bogota", es_activa=True)
        sede_b = models.Sede(id=uuid.uuid4(), nombre="Sede B", ciudad="Medellin", es_activa=True)
        db_session.add_all([sede_a, sede_b])
        db_session.flush()

        perms = {"cms:edit": "allow", "cms:read": "allow"}
        _, _, _ = seed_user_with_role(
            db_session,
            role_name="PASTOR",
            email=self.PASTOR_A_EMAIL,
            password="testpass123",
            sede_id=sede_a.id,
            permisos=perms,
        )
        _, _, _ = seed_user_with_role(
            db_session,
            role_name="PASTOR",
            email=self.PASTOR_B_EMAIL,
            password="testpass123",
            sede_id=sede_b.id,
            permisos=perms,
        )
        return sede_a, sede_b

    def test_cross_sede_patch_section_returns_404(self, client, db_session):
        sede_a, sede_b = self._seed_two_pastors(db_session)
        site_b, page_b, section_b = self._seed_site_page_section(
            db_session, sede_b, "cross-section"
        )
        original_props = section_b.props_json

        headers_a = auth_headers(client, email=self.PASTOR_A_EMAIL)
        resp = client.patch(
            f"/api/cms/v2/sites/{site_b.site_key}/pages/{page_b.slug}/sections/{section_b.id}",
            headers=headers_a,
            json={"props_json": {"title": "hacked"}},
        )
        assert resp.status_code == 404, (
            f"IDOR PATCH section cross-sede debe 404, got {resp.status_code}: {resp.text}"
        )
        db_session.refresh(section_b)
        assert section_b.props_json == original_props, "FUGA: props mutados cross-sede pese al 404"

    def test_cross_sede_delete_section_returns_404(self, client, db_session):
        sede_a, sede_b = self._seed_two_pastors(db_session)
        site_b, page_b, section_b = self._seed_site_page_section(
            db_session, sede_b, "cross-delete-section"
        )

        headers_a = auth_headers(client, email=self.PASTOR_A_EMAIL)
        resp = client.delete(
            f"/api/cms/v2/sites/{site_b.site_key}/pages/{page_b.slug}/sections/{section_b.id}",
            headers=headers_a,
        )
        assert resp.status_code == 404, (
            f"IDor DELETE section cross-sede debe 404, got {resp.status_code}: {resp.text}"
        )
        db_session.refresh(section_b)
        assert section_b.status != "archived", "FUGA: section archivada cross-sede pese al 404"

    def test_cross_sede_patch_menu_item_returns_404(self, client, db_session):
        sede_a, sede_b = self._seed_two_pastors(db_session)
        site_b, menu_b, item_b = self._seed_site_menu_item(db_session, sede_b)
        original_label = item_b.label

        headers_a = auth_headers(client, email=self.PASTOR_A_EMAIL)
        resp = client.patch(
            f"/api/cms/v2/sites/{site_b.site_key}/menus/{menu_b.menu_key}/items/{item_b.id}",
            headers=headers_a,
            json={"label": "hacked"},
        )
        assert resp.status_code == 404, (
            f"IDOR PATCH menu item cross-sede debe 404, got {resp.status_code}: {resp.text}"
        )
        db_session.refresh(item_b)
        assert item_b.label == original_label, "FUGA: menu item mutado cross-sede pese al 404"

    def test_cross_sede_delete_menu_item_returns_404(self, client, db_session):
        sede_a, sede_b = self._seed_two_pastors(db_session)
        site_b, menu_b, item_b = self._seed_site_menu_item(db_session, sede_b)

        headers_a = auth_headers(client, email=self.PASTOR_A_EMAIL)
        resp = client.delete(
            f"/api/cms/v2/sites/{site_b.site_key}/menus/{menu_b.menu_key}/items/{item_b.id}",
            headers=headers_a,
        )
        assert resp.status_code == 404, (
            f"IDOR DELETE menu item cross-sede debe 404, got {resp.status_code}: {resp.text}"
        )
        db_session.refresh(item_b)
        assert item_b.visibility != "hidden", "FUGA: menu item ocultado cross-sede pese al 404"

    def _seed_site_page_section(self, db_session, sede, key_suffix):
        from backend import models

        site = models.CmsSite(
            id=uuid.uuid4(),
            site_key=f"site-{key_suffix}",
            name="Test",
            base_path=f"/{key_suffix}",
            is_active=True,
            sede_id=sede.id,
        )
        db_session.add(site)
        db_session.flush()
        page = models.CmsPage(
            id=uuid.uuid4(),
            site_id=site.id,
            slug="home",
            title="Home",
            status="draft",
        )
        db_session.add(page)
        db_session.flush()
        section = models.CmsSection(
            id=uuid.uuid4(),
            page_id=page.id,
            section_key="section-1",
            type="rich_text",
            props_json={"content": "original"},
            sort_order=0,
            is_visible=True,
            status="active",
        )
        db_session.add(section)
        db_session.commit()
        return site, page, section

    def _seed_site_menu_item(self, db_session, sede):
        from backend import models

        site = models.CmsSite(
            id=uuid.uuid4(),
            site_key="site-menu-cross",
            name="Test Menu",
            base_path="/menu-cross",
            is_active=True,
            sede_id=sede.id,
        )
        db_session.add(site)
        db_session.flush()
        menu = models.CmsMenu(
            id=uuid.uuid4(),
            site_id=site.id,
            menu_key="main",
            name="Main",
            is_active=True,
        )
        db_session.add(menu)
        db_session.flush()
        item = models.CmsMenuItem(
            id=uuid.uuid4(),
            menu_id=menu.id,
            label="Home",
            href="/",
            sort_order=0,
        )
        db_session.add(item)
        db_session.commit()
        return site, menu, item


class TestSectionPropsStructuralValidation:
    """C-06/H-11 regression: every section type gets structural validation."""

    @pytest.mark.parametrize(
        "section_type",
        [
            "hero", "video_hero", "rich_text", "rich_text_columns", "cards",
            "cta_banner", "gallery", "faq", "embed", "testimonials", "stats",
            "team", "countdown", "pricing", "image_text", "timeline",
            "icon_grid", "newsletter", "civic_hero_search",
            "civic_convocatoria_cards", "civic_quick_links",
            "civic_file_downloads", "civic_data_table", "civic_alert_banner",
        ],
    )
    def test_returns_validated_dict_with_expected_keys(self, section_type):
        # Each schema validates an empty dict and returns something
        # (defaults). It must not raise — empty props is the CMS default
        # for a freshly created placeholder section.
        result = validate_section_props(section_type, {})
        assert isinstance(result, dict)

    def test_drops_unexpected_keys_with_extra_ignore(self):
        # Permissive schemas drop unknown keys; an attacker cannot smuggle
        # arbitrary structure past validation into a schema'd section type.
        malicious_extra = {
            "title": "Bienvenido",
            "malicious_field": "<script>alert(1)</script>",
            "another_sneaky_key": {"nested": "data"},
        }
        result = validate_section_props("hero", malicious_extra)
        assert "malicious_field" not in result
        assert "another_sneaky_key" not in result
        assert result.get("title") == "Bienvenido"

    def test_invalid_value_type_raises(self):
        # Title is a str field in the Hero schema; an int 12345 should
        # be rejected by strict Pydantic validation (no silent coercion
        # to "12345" — that would mask malformed admin payloads).
        with pytest.raises(ValueError):
            validate_section_props("hero", {"title": 12345})

    def test_items_list_validates_nested_objects(self):
        # 'cards'│'faq' ... must route list dicts through their item schema.
        result = validate_section_props(
            "faq",
            {"title": "Preguntas", "items": [{"q": "Q", "a": "A"}]},
        )
        assert isinstance(result.get("items"), list)

    def test_html_in_body_is_sanitized_in_schema_validated_props(self):
        # Even with a schema, the body still passes sanitize_props_html
        # upstream (validate_section_props runs sanitize then validates).
        props = {"body": "<p>ok</p><script>alert(1)</script>"}
        result = validate_section_props("rich_text", props)
        body = result.get("body", "")
        assert "<script>" not in body
        assert "<p>ok</p>" in body

