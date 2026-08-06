"""Unit and integration tests for CMS v2 Section A/B Testing API (Milestone 3).

Verifies:
  - Admin CRUD endpoints: GET/POST/GET_ID/PATCH/DELETE under /api/cms/v2/sites/{site_key}/ab-tests
  - Event recording: POST /api/cms/v2/sites/{site_key}/ab-tests/{id}/record-event
  - Results calculation: GET /api/cms/v2/sites/{site_key}/ab-tests/{id}/results
  - Winner application: POST /api/cms/v2/sites/{site_key}/ab-tests/{id}/apply-winner
  - Error handling: 404 AbTestNotFoundError
"""

from __future__ import annotations

import uuid as _uuid

import pytest

from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture
def admin_client(client, db_session):
    admin, _, _ = _seed_admin(db_session)
    return client, _auth_headers(client, email=admin.email, password="testpass123")


@pytest.fixture
def cms_setup(db_session):
    site = models.CmsSite(
        id=_uuid.uuid4(),
        site_key="faro_ab_test",
        name="El Faro AB Test",
        base_path="/faro_ab_test",
        is_active=True,
    )
    page = models.CmsPage(
        id=_uuid.uuid4(),
        site_id=site.id,
        slug="home-ab",
        title="Home Page AB Test",
        status="published",
    )
    sec_a = models.CmsSection(
        id=_uuid.uuid4(),
        page_id=page.id,
        section_key="hero_var_a",
        type="hero",
        props_json={"title": "Hero Variant A"},
        sort_order=1,
        is_visible=True,
        status="active",
    )
    sec_b = models.CmsSection(
        id=_uuid.uuid4(),
        page_id=page.id,
        section_key="hero_var_b",
        type="hero",
        props_json={"title": "Hero Variant B"},
        sort_order=2,
        is_visible=True,
        status="active",
    )
    db_session.add_all([site, page, sec_a, sec_b])
    db_session.commit()
    return {"site": site, "page": page, "sec_a": sec_a, "sec_b": sec_b}


class TestCmsAbTestingApi:
    def test_create_ab_test(self, admin_client, cms_setup):
        c, h = admin_client
        site = cms_setup["site"]
        page = cms_setup["page"]
        sec_a = cms_setup["sec_a"]
        sec_b = cms_setup["sec_b"]

        payload = {
            "name": "Hero Section AB Test",
            "page_id": str(page.id),
            "section_a_id": str(sec_a.id),
            "section_b_id": str(sec_b.id),
            "traffic_split": 0.5,
        }
        resp = c.post(f"/api/cms/v2/sites/{site.site_key}/ab-tests", json=payload, headers=h)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "Hero Section AB Test"
        assert data["page_id"] == str(page.id)
        assert data["section_a_id"] == str(sec_a.id)
        assert data["section_b_id"] == str(sec_b.id)
        assert data["traffic_split"] == 0.5
        assert data["status"] == "active"
        assert "id" in data

    def test_list_ab_tests(self, admin_client, cms_setup, db_session):
        c, h = admin_client
        site = cms_setup["site"]
        page = cms_setup["page"]
        sec_a = cms_setup["sec_a"]
        sec_b = cms_setup["sec_b"]

        test1 = models.CmsAbTest(
            site_id=site.id,
            page_id=page.id,
            name="Test 1",
            section_a_id=sec_a.id,
            section_b_id=sec_b.id,
            status="active",
        )
        test2 = models.CmsAbTest(
            site_id=site.id,
            page_id=page.id,
            name="Test 2",
            section_a_id=sec_a.id,
            section_b_id=sec_b.id,
            status="paused",
        )
        db_session.add_all([test1, test2])
        db_session.commit()

        resp = c.get(f"/api/cms/v2/sites/{site.site_key}/ab-tests", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2

        # Test status filter
        resp_active = c.get(f"/api/cms/v2/sites/{site.site_key}/ab-tests?status=active", headers=h)
        assert resp_active.status_code == 200
        active_ids = [t["id"] for t in resp_active.json()]
        assert str(test1.id) in active_ids
        assert str(test2.id) not in active_ids

    def test_get_and_patch_ab_test(self, admin_client, cms_setup, db_session):
        c, h = admin_client
        site = cms_setup["site"]
        page = cms_setup["page"]
        sec_a = cms_setup["sec_a"]
        sec_b = cms_setup["sec_b"]

        test = models.CmsAbTest(
            site_id=site.id,
            page_id=page.id,
            name="Original Name",
            section_a_id=sec_a.id,
            section_b_id=sec_b.id,
            traffic_split=0.5,
            status="active",
        )
        db_session.add(test)
        db_session.commit()

        # GET by ID
        resp = c.get(f"/api/cms/v2/sites/{site.site_key}/ab-tests/{test.id}", headers=h)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Original Name"

        # PATCH
        patch_payload = {"name": "Updated Name", "traffic_split": 0.7, "status": "paused"}
        resp_patch = c.patch(f"/api/cms/v2/sites/{site.site_key}/ab-tests/{test.id}", json=patch_payload, headers=h)
        assert resp_patch.status_code == 200
        patched_data = resp_patch.json()
        assert patched_data["name"] == "Updated Name"
        assert patched_data["traffic_split"] == 0.7
        assert patched_data["status"] == "paused"

    def test_delete_ab_test(self, admin_client, cms_setup, db_session):
        c, h = admin_client
        site = cms_setup["site"]
        page = cms_setup["page"]
        sec_a = cms_setup["sec_a"]
        sec_b = cms_setup["sec_b"]

        test = models.CmsAbTest(
            site_id=site.id,
            page_id=page.id,
            name="To Delete",
            section_a_id=sec_a.id,
            section_b_id=sec_b.id,
            status="active",
        )
        db_session.add(test)
        db_session.commit()

        resp = c.delete(f"/api/cms/v2/sites/{site.site_key}/ab-tests/{test.id}", headers=h)
        assert resp.status_code == 200
        assert resp.json()["message"] == "A/B test deleted"

        # Verify 404 on get
        resp_get = c.get(f"/api/cms/v2/sites/{site.site_key}/ab-tests/{test.id}", headers=h)
        assert resp_get.status_code == 404

    def test_record_event_and_results(self, admin_client, cms_setup, db_session):
        c, h = admin_client
        site = cms_setup["site"]
        page = cms_setup["page"]
        sec_a = cms_setup["sec_a"]
        sec_b = cms_setup["sec_b"]

        test = models.CmsAbTest(
            site_id=site.id,
            page_id=page.id,
            name="Event Tracking Test",
            section_a_id=sec_a.id,
            section_b_id=sec_b.id,
            status="active",
        )
        db_session.add(test)
        db_session.commit()

        # Record events for Variant A (100 views, 10 clicks)
        for i in range(10):
            c.post(
                f"/api/cms/v2/sites/{site.site_key}/ab-tests/{test.id}/record-event",
                json={"variant": "a", "event_type": "view", "visitor_id": f"vis_a_{i}"},
            )
        for i in range(2):
            c.post(
                f"/api/cms/v2/sites/{site.site_key}/ab-tests/{test.id}/record-event",
                json={"variant": "a", "event_type": "click", "visitor_id": f"vis_a_{i}"},
            )

        # Record events for Variant B (100 views, 50 clicks)
        for i in range(10):
            c.post(
                f"/api/cms/v2/sites/{site.site_key}/ab-tests/{test.id}/record-event",
                json={"variant": "b", "event_type": "view", "visitor_id": f"vis_b_{i}"},
            )
        for i in range(8):
            c.post(
                f"/api/cms/v2/sites/{site.site_key}/ab-tests/{test.id}/record-event",
                json={"variant": "b", "event_type": "click", "visitor_id": f"vis_b_{i}"},
            )

        # Get Results
        resp = c.get(f"/api/cms/v2/sites/{site.site_key}/ab-tests/{test.id}/results", headers=h)
        assert resp.status_code == 200
        res = resp.json()
        assert res["views_a"] == 10
        assert res["views_b"] == 10
        assert res["clicks_a"] == 2
        assert res["clicks_b"] == 8
        assert res["conversion_rate_a"] == 0.2
        assert res["conversion_rate_b"] == 0.8
        assert res["statistical_significance"] > 0

    def test_apply_winner(self, admin_client, cms_setup, db_session):
        c, h = admin_client
        site = cms_setup["site"]
        page = cms_setup["page"]
        sec_a = cms_setup["sec_a"]
        sec_b = cms_setup["sec_b"]

        test = models.CmsAbTest(
            site_id=site.id,
            page_id=page.id,
            name="Winner Test",
            section_a_id=sec_a.id,
            section_b_id=sec_b.id,
            status="active",
        )
        db_session.add(test)
        db_session.commit()

        # Apply winner: variant B
        resp = c.post(
            f"/api/cms/v2/sites/{site.site_key}/ab-tests/{test.id}/apply-winner",
            json={"winner_variant": "b"},
            headers=h,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["winner_section_id"] == str(sec_b.id)

        # Verify in DB that section B is visible and section A is hidden
        db_session.refresh(sec_a)
        db_session.refresh(sec_b)
        assert sec_b.is_visible is True
        assert sec_a.is_visible is False

    def test_ab_test_not_found_404(self, admin_client, cms_setup):
        c, h = admin_client
        site = cms_setup["site"]
        fake_id = _uuid.uuid4()

        resp = c.get(f"/api/cms/v2/sites/{site.site_key}/ab-tests/{fake_id}", headers=h)
        assert resp.status_code == 404
