"""
CMS V2 Deep Coverage Tests — exercises edge cases, error paths, and
nested workflows across all cms_v2.py endpoints.
"""
import uuid

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="cms_deep@test.com")
    headers = _auth_headers(client, email="cms_deep@test.com", password="testpass123")
    return {"c": client, "h": headers}


# ═══════════════════════════════════════════════════════════════════════════════
# SITES — Edge cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestSitesEdgeCases:
    def test_create_site_missing_key(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/cms/v2/sites", json={"name": "X", "base_path": "/x"}, headers=h)
        assert resp.status_code == 422

    def test_create_site_missing_base_path(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/cms/v2/sites", json={"site_key": "x", "name": "X"}, headers=h)
        assert resp.status_code == 422

    def test_create_site_invalid_base_path(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/cms/v2/sites",
            json={"site_key": "x", "name": "X", "base_path": "no-slash"},
            headers=h,
        )
        assert resp.status_code == 422

    def test_create_duplicate_site(self, full):
        c, h = full["c"], full["h"]
        key = f"dup-{uuid.uuid4().hex[:6]}"
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": key, "name": "D", "base_path": "/d"},
                headers=h,
            ).status_code
        )
        resp = c.post(
            "/api/cms/v2/sites",
            json={"site_key": key, "name": "D2", "base_path": "/d2"},
            headers=h,
        )
        assert resp.status_code == 409

    def test_get_unknown_site(self, full):
        c, h = full["c"], full["h"]
        assert c.get("/api/cms/v2/sites/nonexistent", headers=h).status_code == 404

    def test_delete_unknown_site(self, full):
        c, h = full["c"], full["h"]
        assert c.delete("/api/cms/v2/sites/nonexistent", headers=h).status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# PAGES — Workflows & edge cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestPagesWorkflow:
    def test_page_must_start_draft(self, full):
        c, h = full["c"], full["h"]
        site_key = f"pw-{uuid.uuid4().hex[:6]}"
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": site_key, "name": "PW", "base_path": "/pw"},
                headers=h,
            ).status_code
        )
        resp = c.post(
            f"/api/cms/v2/sites/{site_key}/pages",
            json={"slug": "bad", "title": "Bad", "status": "published"},
            headers=h,
        )
        assert resp.status_code == 422

    def test_workflow_transitions(self, full):
        c, h = full["c"], full["h"]
        site_key = f"pw-{uuid.uuid4().hex[:6]}"
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": site_key, "name": "PW", "base_path": "/pw"},
                headers=h,
            ).status_code
        )
        assert _ok(
            c.post(
                f"/api/cms/v2/sites/{site_key}/pages",
                json={"slug": "flow", "title": "Flow", "status": "draft"},
                headers=h,
            ).status_code
        )

        # publish
        resp = c.post(
            f"/api/cms/v2/sites/{site_key}/pages/flow/workflow",
            json={"action": "publish"},
            headers=h,
        )
        assert _ok(resp.status_code), f"publish: {resp.status_code} {resp.text}"

        # archive
        resp = c.post(
            f"/api/cms/v2/sites/{site_key}/pages/flow/workflow",
            json={"action": "archive"},
            headers=h,
        )
        assert _ok(resp.status_code), f"archive: {resp.status_code} {resp.text}"

        # revert to draft
        resp = c.post(
            f"/api/cms/v2/sites/{site_key}/pages/flow/workflow",
            json={"action": "revert_draft"},
            headers=h,
        )
        assert _ok(resp.status_code), f"revert_draft: {resp.status_code} {resp.text}"

    def test_patch_page_rejects_status_change(self, full):
        c, h = full["c"], full["h"]
        site_key = f"pw-{uuid.uuid4().hex[:6]}"
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": site_key, "name": "PW", "base_path": "/pw"},
                headers=h,
            ).status_code
        )
        assert _ok(
            c.post(
                f"/api/cms/v2/sites/{site_key}/pages",
                json={"slug": "nostat", "title": "NoStat", "status": "draft"},
                headers=h,
            ).status_code
        )
        resp = c.patch(
            f"/api/cms/v2/sites/{site_key}/pages/nostat",
            json={"status": "published"},
            headers=h,
        )
        assert resp.status_code == 422

    def test_preview_includes_sections(self, full):
        c, h = full["c"], full["h"]
        site_key = f"pw-{uuid.uuid4().hex[:6]}"
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": site_key, "name": "PW", "base_path": "/pw"},
                headers=h,
            ).status_code
        )
        assert _ok(
            c.post(
                f"/api/cms/v2/sites/{site_key}/pages",
                json={"slug": "prev", "title": "Prev", "status": "draft"},
                headers=h,
            ).status_code
        )
        assert _ok(
            c.post(
                f"/api/cms/v2/sites/{site_key}/pages/prev/sections",
                json={"type": "rich_text", "props_json": {"body": "hi"}},
                headers=h,
            ).status_code
        )
        resp = c.get(f"/api/cms/v2/sites/{site_key}/pages/prev/preview", headers=h)
        assert _ok(resp.status_code)
        body = resp.json()
        assert "sections" in body
        assert len(body["sections"]) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# SECTIONS — Props validation & type guards
# ═══════════════════════════════════════════════════════════════════════════════


class TestSectionsValidation:
    def test_rejects_unknown_section_type(self, full):
        c, h = full["c"], full["h"]
        site_key = f"sv-{uuid.uuid4().hex[:6]}"
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": site_key, "name": "SV", "base_path": "/sv"},
                headers=h,
            ).status_code
        )
        assert _ok(
            c.post(
                f"/api/cms/v2/sites/{site_key}/pages",
                json={"slug": "sec", "title": "Sec", "status": "draft"},
                headers=h,
            ).status_code
        )
        resp = c.post(
            f"/api/cms/v2/sites/{site_key}/pages/sec/sections",
            json={"type": "nonexistent_xyz", "props_json": {}},
            headers=h,
        )
        assert resp.status_code == 422

    def test_accepts_known_section_type(self, full):
        c, h = full["c"], full["h"]
        site_key = f"sv-{uuid.uuid4().hex[:6]}"
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": site_key, "name": "SV", "base_path": "/sv"},
                headers=h,
            ).status_code
        )
        assert _ok(
            c.post(
                f"/api/cms/v2/sites/{site_key}/pages",
                json={"slug": "sec", "title": "Sec", "status": "draft"},
                headers=h,
            ).status_code
        )
        resp = c.post(
            f"/api/cms/v2/sites/{site_key}/pages/sec/sections",
            json={"type": "hero", "props_json": {"title": "Hero"}},
            headers=h,
        )
        assert _ok(resp.status_code), f"hero section: {resp.status_code} {resp.text}"

    def test_accepts_civic_section_types(self, full):
        c, h = full["c"], full["h"]
        site_key = f"sv-{uuid.uuid4().hex[:6]}"
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": site_key, "name": "SV", "base_path": "/sv"},
                headers=h,
            ).status_code
        )
        assert _ok(
            c.post(
                f"/api/cms/v2/sites/{site_key}/pages",
                json={"slug": "sec", "title": "Sec", "status": "draft"},
                headers=h,
            ).status_code
        )
        civic_types = [
            "civic_hero_search",
            "civic_convocatoria_cards",
            "civic_quick_links",
            "civic_file_downloads",
            "civic_data_table",
            "civic_alert_banner",
        ]
        for stype in civic_types:
            resp = c.post(
                f"/api/cms/v2/sites/{site_key}/pages/sec/sections",
                json={"type": stype, "props_json": {"title": stype}},
                headers=h,
            )
            assert _ok(resp.status_code), f"civic type {stype}: {resp.status_code} {resp.text}"

    def test_patch_rejects_bad_status(self, full):
        c, h = full["c"], full["h"]
        site_key = f"sv-{uuid.uuid4().hex[:6]}"
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": site_key, "name": "SV", "base_path": "/sv"},
                headers=h,
            ).status_code
        )
        assert _ok(
            c.post(
                f"/api/cms/v2/sites/{site_key}/pages",
                json={"slug": "sec", "title": "Sec", "status": "draft"},
                headers=h,
            ).status_code
        )
        # Create a section so we have something to patch
        assert _ok(
            c.post(
                f"/api/cms/v2/sites/{site_key}/pages/sec/sections",
                json={"type": "hero", "props_json": {"title": "Hero"}},
                headers=h,
            ).status_code
        )
        secs = c.get(f"/api/cms/v2/sites/{site_key}/pages/sec/sections", headers=h).json()
        sid = secs["items"][0]["id"]
        resp = c.patch(
            f"/api/cms/v2/sites/{site_key}/pages/sec/sections/{sid}",
            json={"status": "invalid_status"},
            headers=h,
        )
        assert resp.status_code == 422

    def test_reorder_empty_list(self, full):
        c, h = full["c"], full["h"]
        site_key = f"sv-{uuid.uuid4().hex[:6]}"
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": site_key, "name": "SV", "base_path": "/sv"},
                headers=h,
            ).status_code
        )
        assert _ok(
            c.post(
                f"/api/cms/v2/sites/{site_key}/pages",
                json={"slug": "sec", "title": "Sec", "status": "draft"},
                headers=h,
            ).status_code
        )
        resp = c.post(
            f"/api/cms/v2/sites/{site_key}/pages/sec/sections/reorder",
            json={"items": []},
            headers=h,
        )
        assert _ok(resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# MENUS — Deep item nesting
# ═══════════════════════════════════════════════════════════════════════════════


class TestMenusDeep:
    def test_nested_items_and_reorder(self, full):
        c, h = full["c"], full["h"]
        site_key = f"md-{uuid.uuid4().hex[:6]}"
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": site_key, "name": "MD", "base_path": "/md"},
                headers=h,
            ).status_code
        )
        assert _ok(
            c.post(
                f"/api/cms/v2/sites/{site_key}/menus",
                json={"menu_key": "nav", "name": "Nav"},
                headers=h,
            ).status_code
        )

        parent = c.post(
            f"/api/cms/v2/sites/{site_key}/menus/nav/items",
            json={"label": "Parent", "href": "/parent"},
            headers=h,
        ).json()
        child = c.post(
            f"/api/cms/v2/sites/{site_key}/menus/nav/items",
            json={"label": "Child", "href": "/child", "parent_id": parent["id"]},
            headers=h,
        ).json()
        assert child["parent_id"] == parent["id"]

        items = c.get(f"/api/cms/v2/sites/{site_key}/menus/nav/items", headers=h).json()
        assert len(items) == 2

        payload = [{"id": i["id"], "sort_order": idx, "parent_id": i.get("parent_id")} for idx, i in enumerate(items)]
        resp = c.post(
            f"/api/cms/v2/sites/{site_key}/menus/nav/reorder",
            json={"items": payload},
            headers=h,
        )
        assert _ok(resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# THEMES — Activation & constraints
# ═══════════════════════════════════════════════════════════════════════════════


class TestThemesActivation:
    def test_only_one_theme_active(self, full):
        c, h = full["c"], full["h"]
        site_key = f"ta-{uuid.uuid4().hex[:6]}"
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": site_key, "name": "TA", "base_path": "/ta"},
                headers=h,
            ).status_code
        )
        t1 = c.post(
            f"/api/cms/v2/sites/{site_key}/themes",
            json={"name": "T1", "tokens_json": {}},
            headers=h,
        ).json()
        t2 = c.post(
            f"/api/cms/v2/sites/{site_key}/themes",
            json={"name": "T2", "tokens_json": {}},
            headers=h,
        ).json()

        assert _ok(c.post(f"/api/cms/v2/sites/{site_key}/themes/{t1['id']}/activate", headers=h).status_code)
        assert _ok(c.post(f"/api/cms/v2/sites/{site_key}/themes/{t2['id']}/activate", headers=h).status_code)

        themes = c.get(f"/api/cms/v2/sites/{site_key}/themes", headers=h).json()
        active = [t for t in themes if t["is_active"]]
        assert len(active) == 1
        assert active[0]["id"] == t2["id"]


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL BLOCKS — Full lifecycle
# ═══════════════════════════════════════════════════════════════════════════════


class TestGlobalBlocksLifecycle:
    def test_create_patch_delete(self, full):
        c, h = full["c"], full["h"]
        site_key = f"gl-{uuid.uuid4().hex[:6]}"
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": site_key, "name": "GL", "base_path": "/gl"},
                headers=h,
            ).status_code
        )

        resp = c.post(
            f"/api/cms/v2/global-blocks?site_key={site_key}",
            json={"type": "hero", "props_json": {"title": "Global Hero"}},
            headers=h,
        )
        assert _ok(resp.status_code)

        blocks = c.get(f"/api/cms/v2/global-blocks?site_key={site_key}", headers=h).json()
        assert blocks["total"] >= 1

        bid = blocks["items"][0]["id"]
        resp = c.patch(
            f"/api/cms/v2/global-blocks/{bid}?site_key={site_key}",
            json={"props_json": {"title": "Updated"}},
            headers=h,
        )
        assert _ok(resp.status_code)

        assert _ok(c.delete(f"/api/cms/v2/global-blocks/{bid}?site_key={site_key}", headers=h).status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS — Rate-limit paths & missing data
# ═══════════════════════════════════════════════════════════════════════════════


class TestPublicEdgeCases:
    def test_public_unknown_site(self, full):
        c, h = full["c"], full["h"]
        assert c.get("/api/cms/v2/public/sites/ghost/pages").status_code == 404

    def test_public_unknown_page(self, full):
        c, h = full["c"], full["h"]
        key = f"pube-{uuid.uuid4().hex[:6]}"
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": key, "name": "E", "base_path": "/e"},
                headers=h,
            ).status_code
        )
        assert c.get(f"/api/cms/v2/public/sites/{key}/pages/ghost").status_code == 404

    def test_public_unknown_menu(self, full):
        c, h = full["c"], full["h"]
        key = f"pubm-{uuid.uuid4().hex[:6]}"
        assert _ok(
            c.post(
                "/api/cms/v2/sites",
                json={"site_key": key, "name": "M", "base_path": "/m"},
                headers=h,
            ).status_code
        )
        assert c.get(f"/api/cms/v2/public/sites/{key}/menus/ghost").status_code == 404

    def test_track_nonexistent_page(self, full):
        c, h = full["c"], full["h"]
        # Track endpoint silently succeeds even if page not found
        assert _ok(c.post("/api/cms/v2/track/ghost-page").status_code)

    def test_analytics_unknown_page(self, full):
        c, h = full["c"], full["h"]
        assert c.get("/api/cms/v2/analytics/ghost-page", headers=h).status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION TYPES — Catalog edge cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestSectionTypesEdgeCases:
    def test_get_unknown_section_type(self, full):
        c, h = full["c"], full["h"]
        assert c.get("/api/cms/v2/section-types/ghost_type", headers=h).status_code == 404

    def test_patch_unknown_section_type(self, full):
        c, h = full["c"], full["h"]
        resp = c.patch(
            "/api/cms/v2/section-types/ghost_type",
            json={"description": "x"},
            headers=h,
        )
        assert resp.status_code == 404

    def test_delete_unknown_section_type(self, full):
        c, h = full["c"], full["h"]
        assert c.delete("/api/cms/v2/section-types/ghost_type", headers=h).status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# IMAGE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestImageEndpoints:
    def test_resize_unknown_media(self, full):
        c, h = full["c"], full["h"]
        fake_id = str(uuid.uuid4())
        assert c.get(f"/api/cms/v2/images/{fake_id}/resize").status_code == 404

    def test_optimize_requires_auth(self, full):
        c, h = full["c"], full["h"]
        fake_id = str(uuid.uuid4())
        # Without auth should fail (401 or 403)
        resp = c.post(f"/api/cms/v2/images/optimize?media_id={fake_id}")
        assert resp.status_code in (401, 403)
