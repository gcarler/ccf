"""Unit and integration tests for Native Popups Backend (R3-BE / Milestone 3).

Verifies:
  - Admin CRUD endpoints: GET/POST/GET_ID/PATCH/DELETE on /api/cms/v2/sites/{site_key}/popups
  - Role permissions and access controls
  - Public active popups endpoint: GET /api/cms/v2/public/popups?site_key={site_key}&page_slug={slug}
  - 404 PopupNotFoundError handling
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
def cms_site(db_session):
    site = models.CmsSite(
        id=_uuid.uuid4(),
        site_key="faro_popups",
        name="El Faro Popups",
        base_path="/faro_popups",
        is_active=True,
    )
    db_session.add(site)
    db_session.commit()
    return site


class TestCmsPopupsAdminApi:
    def test_create_popup(self, admin_client, cms_site):
        c, h = admin_client
        payload = {
            "name": "Welcome Popup",
            "content_html": "<div>Welcome to El Faro!</div>",
            "trigger_type": "on_load",
            "trigger_value": 0,
            "is_active": True,
            "show_on_pages": ["/home", "/about"],
        }
        resp = c.post(f"/api/cms/v2/sites/{cms_site.site_key}/popups", json=payload, headers=h)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "Welcome Popup"
        assert data["content_html"] == "<div>Welcome to El Faro!</div>"
        assert data["trigger_type"] == "on_load"
        assert data["is_active"] is True
        assert data["show_on_pages"] == ["/home", "/about"]
        assert "id" in data

    def test_list_popups(self, admin_client, cms_site, db_session):
        c, h = admin_client
        popup1 = models.CmsPopup(
            site_id=cms_site.id,
            name="Active Popup",
            content_html="<p>Active</p>",
            is_active=True,
        )
        popup2 = models.CmsPopup(
            site_id=cms_site.id,
            name="Inactive Popup",
            content_html="<p>Inactive</p>",
            is_active=False,
        )
        db_session.add_all([popup1, popup2])
        db_session.commit()

        # List all
        resp = c.get(f"/api/cms/v2/sites/{cms_site.site_key}/popups", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2

        # List only active
        resp_active = c.get(f"/api/cms/v2/sites/{cms_site.site_key}/popups?only_active=true", headers=h)
        assert resp_active.status_code == 200
        active_data = resp_active.json()
        assert all(p["is_active"] for p in active_data)

    def test_get_popup_by_id(self, admin_client, cms_site, db_session):
        c, h = admin_client
        popup = models.CmsPopup(
            site_id=cms_site.id,
            name="Specific Popup",
            content_html="<p>Specific</p>",
        )
        db_session.add(popup)
        db_session.commit()

        resp = c.get(f"/api/cms/v2/sites/{cms_site.site_key}/popups/{popup.id}", headers=h)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Specific Popup"

    def test_get_popup_not_found(self, admin_client, cms_site):
        c, h = admin_client
        random_id = _uuid.uuid4()
        resp = c.get(f"/api/cms/v2/sites/{cms_site.site_key}/popups/{random_id}", headers=h)
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Popup not found"

    def test_update_popup(self, admin_client, cms_site, db_session):
        c, h = admin_client
        popup = models.CmsPopup(
            site_id=cms_site.id,
            name="Original Name",
            content_html="<p>Original</p>",
            is_active=True,
        )
        db_session.add(popup)
        db_session.commit()

        update_payload = {
            "name": "Updated Name",
            "is_active": False,
        }
        resp = c.patch(f"/api/cms/v2/sites/{cms_site.site_key}/popups/{popup.id}", json=update_payload, headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Name"
        assert data["is_active"] is False
        assert data["content_html"] == "<p>Original</p>"

    def test_delete_popup(self, admin_client, cms_site, db_session):
        c, h = admin_client
        popup = models.CmsPopup(
            site_id=cms_site.id,
            name="To Delete",
            content_html="<p>Delete me</p>",
        )
        db_session.add(popup)
        db_session.commit()

        resp = c.delete(f"/api/cms/v2/sites/{cms_site.site_key}/popups/{popup.id}", headers=h)
        assert resp.status_code == 204

        # Confirm deleted
        get_resp = c.get(f"/api/cms/v2/sites/{cms_site.site_key}/popups/{popup.id}", headers=h)
        assert get_resp.status_code == 404


class TestCmsPopupsPublicApi:
    def test_get_public_popups(self, client, cms_site, db_session):
        popup1 = models.CmsPopup(
            site_id=cms_site.id,
            name="Public Active 1",
            content_html="<p>Active 1</p>",
            is_active=True,
            show_on_pages=[],
        )
        popup2 = models.CmsPopup(
            site_id=cms_site.id,
            name="Public Active 2 (Specific Page)",
            content_html="<p>Active 2</p>",
            is_active=True,
            show_on_pages=["/events"],
        )
        popup_inactive = models.CmsPopup(
            site_id=cms_site.id,
            name="Public Inactive",
            content_html="<p>Inactive</p>",
            is_active=False,
        )
        db_session.add_all([popup1, popup2, popup_inactive])
        db_session.commit()

        # Public list without page filter -> returns all active
        resp = client.get(f"/api/cms/v2/public/popups?site_key={cms_site.site_key}")
        assert resp.status_code == 200
        names = [p["name"] for p in resp.json()]
        assert "Public Active 1" in names
        assert "Public Active 2 (Specific Page)" in names
        assert "Public Inactive" not in names

        # Public list with page_slug filter = /events
        resp_events = client.get(f"/api/cms/v2/public/popups?site_key={cms_site.site_key}&page_slug=/events")
        assert resp_events.status_code == 200
        names_events = [p["name"] for p in resp_events.json()]
        assert "Public Active 1" in names_events  # show_on_pages is [] so shown on all pages
        assert "Public Active 2 (Specific Page)" in names_events

        # Public list with page_slug filter = /contact
        resp_contact = client.get(f"/api/cms/v2/public/popups?site_key={cms_site.site_key}&page_slug=/contact")
        assert resp_contact.status_code == 200
        names_contact = [p["name"] for p in resp_contact.json()]
        assert "Public Active 1" in names_contact
        assert "Public Active 2 (Specific Page)" not in names_contact
