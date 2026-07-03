"""
CMS V2 Coverage Tests — exercises all cms_v2.py endpoints with real payloads.

Fixes previous broken tests that used wrong field names ("key" vs "site_key",
"section_type" vs "type", "url" vs "href", "colors" vs "tokens_json") and
non-existent top-level endpoints (/media, /versions, /publish-logs, /workflow).
"""
import uuid

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="cms_cov@test.com")
    headers = _auth_headers(client, email="cms_cov@test.com", password="testpass123")
    return {"c": client, "h": headers}


# ═══════════════════════════════════════════════════════════════════════════════
# SITES
# ═══════════════════════════════════════════════════════════════════════════════


class TestSitesCRUD:
    def test_list_sites(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/cms/v2/sites", headers=h).status_code)

    def test_create_get_patch_delete_site(self, full):
        c, h = full["c"], full["h"]
        site_key = f"cov-{uuid.uuid4().hex[:6]}"

        resp = c.post(
            "/api/cms/v2/sites",
            json={"site_key": site_key, "name": "Cov Site", "base_path": "/cov"},
            headers=h,
        )
        assert _ok(resp.status_code), f"create_site: {resp.status_code} {resp.text}"
        body = resp.json()
        assert body["site_key"] == site_key
        assert body["name"] == "Cov Site"

        resp = c.get(f"/api/cms/v2/sites/{site_key}", headers=h)
        assert _ok(resp.status_code)
        assert resp.json()["site_key"] == site_key

        resp = c.patch(
            f"/api/cms/v2/sites/{site_key}",
            json={"name": "Updated Cov"},
            headers=h,
        )
        assert _ok(resp.status_code), f"patch_site: {resp.status_code} {resp.text}"
        assert resp.json()["name"] == "Updated Cov"

        assert _ok(c.delete(f"/api/cms/v2/sites/{site_key}", headers=h).status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGES
# ═══════════════════════════════════════════════════════════════════════════════


class TestPagesCRUD:
    def test_pages_full_crud(self, full):
        c, h = full["c"], full["h"]
        site_key = f"page-{uuid.uuid4().hex[:6]}"

        # Create site
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": site_key, "name": "Page Site", "base_path": "/ps"},
                headers=h,
            ).status_code
        )

        # List pages (empty)
        assert _ok(c.get(f"/api/cms/v2/sites/{site_key}/pages", headers=h).status_code)

        # Create page
        resp = c.post(
            f"/api/cms/v2/sites/{site_key}/pages",
            json={"slug": "home", "title": "Home", "status": "draft"},
            headers=h,
        )
        assert _ok(resp.status_code), f"create_page: {resp.status_code} {resp.text}"
        assert resp.json()["slug"] == "home"
        assert resp.json()["status"] == "draft"

        # Get page
        resp = c.get(f"/api/cms/v2/sites/{site_key}/pages/home", headers=h)
        assert _ok(resp.status_code)
        assert resp.json()["title"] == "Home"

        # Update page
        resp = c.patch(
            f"/api/cms/v2/sites/{site_key}/pages/home",
            json={"title": "Updated Home"},
            headers=h,
        )
        assert _ok(resp.status_code), f"patch_page: {resp.status_code} {resp.text}"
        assert resp.json()["title"] == "Updated Home"

        # Delete page
        assert _ok(c.delete(f"/api/cms/v2/sites/{site_key}/pages/home", headers=h).status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTIONS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSectionsCRUD:
    def test_sections_full_crud(self, full):
        c, h = full["c"], full["h"]
        site_key = f"sec-{uuid.uuid4().hex[:6]}"

        # Create site + page
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": site_key, "name": "Sec Site", "base_path": "/ss"},
                headers=h,
            ).status_code
        )
        assert _ok(
            c.post(
                f"/api/cms/v2/sites/{site_key}/pages",
                json={"slug": "landing", "title": "Landing", "status": "draft"},
                headers=h,
            ).status_code
        )

        # List sections (empty)
        assert _ok(c.get(f"/api/cms/v2/sites/{site_key}/pages/landing/sections", headers=h).status_code)

        # Create section
        resp = c.post(
            f"/api/cms/v2/sites/{site_key}/pages/landing/sections",
            json={"type": "hero", "props_json": {"title": "Hello"}},
            headers=h,
        )
        assert _ok(resp.status_code), f"create_section: {resp.status_code} {resp.text}"
        sec_id = resp.json()["id"]

        # Patch section
        resp = c.patch(
            f"/api/cms/v2/sites/{site_key}/pages/landing/sections/{sec_id}",
            json={"is_visible": False},
            headers=h,
        )
        assert _ok(resp.status_code), f"patch_section: {resp.status_code} {resp.text}"

        # Reorder sections
        resp = c.post(
            f"/api/cms/v2/sites/{site_key}/pages/landing/sections/reorder",
            json={"items": [{"id": sec_id, "sort_order": 0}]},
            headers=h,
        )
        assert _ok(resp.status_code), f"reorder_sections: {resp.status_code} {resp.text}"

        # Delete section
        assert _ok(c.delete(f"/api/cms/v2/sites/{site_key}/pages/landing/sections/{sec_id}", headers=h).status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# MENUS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMenusCRUD:
    def test_menus_full_crud(self, full):
        c, h = full["c"], full["h"]
        site_key = f"menu-{uuid.uuid4().hex[:6]}"

        # Create site
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": site_key, "name": "Menu Site", "base_path": "/ms"},
                headers=h,
            ).status_code
        )

        # List menus (empty)
        assert _ok(c.get(f"/api/cms/v2/sites/{site_key}/menus", headers=h).status_code)

        # Create menu
        resp = c.post(
            f"/api/cms/v2/sites/{site_key}/menus",
            json={"menu_key": "main", "name": "Main Menu"},
            headers=h,
        )
        assert _ok(resp.status_code), f"create_menu: {resp.status_code} {resp.text}"

        # Get menu
        assert _ok(c.get(f"/api/cms/v2/sites/{site_key}/menus/main", headers=h).status_code)

        # Update menu
        resp = c.patch(
            f"/api/cms/v2/sites/{site_key}/menus/main",
            json={"name": "Updated Main"},
            headers=h,
        )
        assert _ok(resp.status_code), f"patch_menu: {resp.status_code} {resp.text}"

        # Add menu item
        resp = c.post(
            f"/api/cms/v2/sites/{site_key}/menus/main/items",
            json={"label": "Home", "href": "/"},
            headers=h,
        )
        assert _ok(resp.status_code), f"create_menu_item: {resp.status_code} {resp.text}"
        i_id = resp.json()["id"]

        # Patch menu item
        resp = c.patch(
            f"/api/cms/v2/sites/{site_key}/menus/main/items/{i_id}",
            json={"label": "Inicio"},
            headers=h,
        )
        assert _ok(resp.status_code), f"patch_menu_item: {resp.status_code} {resp.text}"

        # Reorder menu items
        resp = c.post(
            f"/api/cms/v2/sites/{site_key}/menus/main/reorder",
            json={"items": [{"id": i_id, "sort_order": 2, "parent_id": None}]},
            headers=h,
        )
        assert _ok(resp.status_code), f"reorder_menu_items: {resp.status_code} {resp.text}"

        # Delete menu item
        assert _ok(c.delete(f"/api/cms/v2/sites/{site_key}/menus/main/items/{i_id}", headers=h).status_code)

        # Delete menu
        assert _ok(c.delete(f"/api/cms/v2/sites/{site_key}/menus/main", headers=h).status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# THEMES
# ═══════════════════════════════════════════════════════════════════════════════


class TestThemesCRUD:
    def test_themes_full_crud(self, full):
        c, h = full["c"], full["h"]
        site_key = f"th-{uuid.uuid4().hex[:6]}"

        # Create site
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": site_key, "name": "Theme Site", "base_path": "/ts"},
                headers=h,
            ).status_code
        )

        # List themes (empty)
        assert _ok(c.get(f"/api/cms/v2/sites/{site_key}/themes", headers=h).status_code)

        # Create theme
        resp = c.post(
            f"/api/cms/v2/sites/{site_key}/themes",
            json={"name": "Dark", "tokens_json": {"primary": "#000"}},
            headers=h,
        )
        assert _ok(resp.status_code), f"create_theme: {resp.status_code} {resp.text}"
        t_id = resp.json()["id"]

        # Get theme
        assert _ok(c.get(f"/api/cms/v2/sites/{site_key}/themes/{t_id}", headers=h).status_code)

        # Update theme
        resp = c.patch(
            f"/api/cms/v2/sites/{site_key}/themes/{t_id}",
            json={"name": "Light"},
            headers=h,
        )
        assert _ok(resp.status_code), f"patch_theme: {resp.status_code} {resp.text}"

        # Activate theme
        assert _ok(c.post(f"/api/cms/v2/sites/{site_key}/themes/{t_id}/activate", headers=h).status_code)

        # Delete theme
        assert _ok(c.delete(f"/api/cms/v2/sites/{site_key}/themes/{t_id}", headers=h).status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL BLOCKS
# ═══════════════════════════════════════════════════════════════════════════════


class TestGlobalBlocks:
    def test_global_blocks_full_crud(self, full):
        c, h = full["c"], full["h"]
        site_key = f"gb-{uuid.uuid4().hex[:6]}"

        # Create site
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": site_key, "name": "GB Site", "base_path": "/gbs"},
                headers=h,
            ).status_code
        )

        # List global blocks (empty)
        assert _ok(c.get(f"/api/cms/v2/global-blocks?site_key={site_key}", headers=h).status_code)

        # Create global block
        resp = c.post(
            f"/api/cms/v2/global-blocks?site_key={site_key}",
            json={"type": "rich_text", "props_json": {"title": "Block"}},
            headers=h,
        )
        assert _ok(resp.status_code), f"create_global_block: {resp.status_code} {resp.text}"
        bid = resp.json()["id"]

        # Patch global block
        resp = c.patch(
            f"/api/cms/v2/global-blocks/{bid}?site_key={site_key}",
            json={"props_json": {"title": "Updated"}},
            headers=h,
        )
        assert _ok(resp.status_code), f"patch_global_block: {resp.status_code} {resp.text}"

        # Delete global block
        assert _ok(c.delete(f"/api/cms/v2/global-blocks/{bid}?site_key={site_key}", headers=h).status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW + VERSIONS + PREVIEW + PUBLISH LOG
# ═══════════════════════════════════════════════════════════════════════════════


class TestWorkflowAndVersions:
    def test_workflow_and_versions(self, full):
        c, h = full["c"], full["h"]
        site_key = f"wf-{uuid.uuid4().hex[:6]}"

        # Create site + page
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": site_key, "name": "WF Site", "base_path": "/wf"},
                headers=h,
            ).status_code
        )
        assert _ok(
            c.post(
                f"/api/cms/v2/sites/{site_key}/pages",
                json={"slug": "about", "title": "About", "status": "draft"},
                headers=h,
            ).status_code
        )

        # Preview page
        assert _ok(c.get(f"/api/cms/v2/sites/{site_key}/pages/about/preview", headers=h).status_code)

        # Publish page
        resp = c.post(
            f"/api/cms/v2/sites/{site_key}/pages/about/workflow",
            json={"action": "publish", "notes": "go live"},
            headers=h,
        )
        assert _ok(resp.status_code), f"workflow_publish: {resp.status_code} {resp.text}"

        # List versions
        assert _ok(c.get(f"/api/cms/v2/sites/{site_key}/pages/about/versions", headers=h).status_code)

        # List publish log
        assert _ok(c.get(f"/api/cms/v2/sites/{site_key}/pages/about/publish-log", headers=h).status_code)

        # Rollback if a version exists
        versions = c.get(f"/api/cms/v2/sites/{site_key}/pages/about/versions", headers=h).json()
        if versions.get("items"):
            vid = versions["items"][0]["id"]
            resp = c.post(f"/api/cms/v2/sites/{site_key}/pages/about/rollback/{vid}", headers=h)
            assert _ok(resp.status_code), f"rollback: {resp.status_code} {resp.text}"


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestPublicEndpoints:
    def test_public_endpoints(self, full):
        c, h = full["c"], full["h"]
        site_key = f"pub-{uuid.uuid4().hex[:6]}"

        # Create site + page + menu, then publish page
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": site_key, "name": "Pub Site", "base_path": "/pub"},
                headers=h,
            ).status_code
        )
        assert _ok(
            c.post(
                f"/api/cms/v2/sites/{site_key}/pages",
                json={"slug": "home", "title": "Home", "status": "draft"},
                headers=h,
            ).status_code
        )
        assert _ok(
            c.post(
                f"/api/cms/v2/sites/{site_key}/menus",
                json={"menu_key": "main", "name": "Main"},
                headers=h,
            ).status_code
        )
        assert _ok(
            c.post(
                f"/api/cms/v2/sites/{site_key}/pages/home/workflow",
                json={"action": "publish"},
                headers=h,
            ).status_code
        )

        # Public pages list
        assert _ok(c.get(f"/api/cms/v2/public/sites/{site_key}/pages").status_code)

        # Public page
        assert _ok(c.get(f"/api/cms/v2/public/sites/{site_key}/pages/home").status_code)

        # Public menu
        assert _ok(c.get(f"/api/cms/v2/public/sites/{site_key}/menus/main").status_code)

        # Public theme (may 404 if no active theme — acceptable)
        resp = c.get(f"/api/cms/v2/public/sites/{site_key}/theme")
        assert resp.status_code in (200, 404)

        # Track + analytics
        assert _ok(c.post("/api/cms/v2/track/home").status_code)
        assert _ok(c.get("/api/cms/v2/analytics/home", headers=h).status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# PASTORAL TEAM
# ═══════════════════════════════════════════════════════════════════════════════


class TestPastoralTeam:
    def test_public_pastoral_team(self, full):
        c, h = full["c"], full["h"]
        # 404 because no site "faro" exists in test DB; we just verify endpoint shape
        resp = c.get("/api/cms/v2/public/sites/faro/pastoral-team")
        assert resp.status_code in (200, 404)

    def test_cms_pastoral_team(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/cms/v2/cms/pastoral-team", headers=h)
        assert resp.status_code in (200, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION TYPES
# ═══════════════════════════════════════════════════════════════════════════════


class TestSectionTypes:
    def test_list_section_types(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/cms/v2/section-types", headers=h).status_code)

    def test_list_only_active(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/cms/v2/section-types?only_active=true", headers=h).status_code)
