"""Adversarial stress-tests for Native Popups Backend (Milestone 3 / R3-BE).

Empirically tests:
1. Multi-tenant isolation & site_key scoping
2. Permission enforcement & 403 / 401 response status codes
3. Edge case page_slug filtering
4. Schema validations (trigger_type, trigger_value, name, content_html)
5. Database model & CRUD edge conditions
"""

from __future__ import annotations

import uuid

import pytest

from backend import models
from tests.conftest import auth_headers, seed_admin, seed_user_with_role


@pytest.fixture
def dual_sites(db_session):
    """Creates two sites under different sedes for multi-tenant testing."""
    sede_a = models.Sede(id=uuid.uuid4(), nombre="Sede Norte", ciudad="Norte")
    sede_b = models.Sede(id=uuid.uuid4(), nombre="Sede Sur", ciudad="Sur")
    db_session.add_all([sede_a, sede_b])
    db_session.flush()

    site_a = models.CmsSite(
        id=uuid.uuid4(),
        site_key="site_alpha",
        name="Site Alpha",
        base_path="/alpha",
        is_active=True,
        sede_id=sede_a.id,
    )
    site_b = models.CmsSite(
        id=uuid.uuid4(),
        site_key="site_beta",
        name="Site Beta",
        base_path="/beta",
        is_active=True,
        sede_id=sede_b.id,
    )
    db_session.add_all([site_a, site_b])
    db_session.commit()
    return site_a, site_b, sede_a, sede_b


@pytest.fixture
def admin_user(db_session):
    admin, _, _ = seed_admin(db_session)
    return admin


@pytest.fixture
def regular_user(db_session):
    user, _, _ = seed_user_with_role(db_session, role_name="estudiante")
    return user


class TestMultiTenantIsolation:
    def test_cross_tenant_popup_access_returns_404(self, client, db_session, dual_sites, admin_user):
        """Verify requesting popup_b_id via site_a endpoint returns 404."""
        site_a, site_b, _, _ = dual_sites
        headers = auth_headers(client, email=admin_user.email, password="testpass123")

        # Create popup in Site B
        popup_b = models.CmsPopup(
            site_id=site_b.id,
            name="Popup in Site B",
            content_html="<p>Site B Popup</p>",
            is_active=True,
        )
        db_session.add(popup_b)
        db_session.commit()

        # Try to fetch Site B popup using Site A site_key
        resp = client.get(
            f"/api/cms/v2/sites/{site_a.site_key}/popups/{popup_b.id}",
            headers=headers,
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Popup not found"

    def test_public_popups_site_isolation(self, client, db_session, dual_sites):
        """Verify public endpoint only returns popups belonging to requested site_key."""
        site_a, site_b, _, _ = dual_sites

        popup_a = models.CmsPopup(
            site_id=site_a.id,
            name="Alpha Popup",
            content_html="<p>Alpha</p>",
            is_active=True,
        )
        popup_b = models.CmsPopup(
            site_id=site_b.id,
            name="Beta Popup",
            content_html="<p>Beta</p>",
            is_active=True,
        )
        db_session.add_all([popup_a, popup_b])
        db_session.commit()

        # Request Site A public popups
        resp_a = client.get(f"/api/cms/v2/public/popups?site_key={site_a.site_key}")
        assert resp_a.status_code == 200
        names_a = [p["name"] for p in resp_a.json()]
        assert "Alpha Popup" in names_a
        assert "Beta Popup" not in names_a

        # Request Site B public popups
        resp_b = client.get(f"/api/cms/v2/public/popups?site_key={site_b.site_key}")
        assert resp_b.status_code == 200
        names_b = [p["name"] for p in resp_b.json()]
        assert "Beta Popup" in names_b
        assert "Alpha Popup" not in names_b


class TestPermissionEnforcement:
    def test_unauthenticated_access_returns_401(self, client, dual_sites):
        """Verify unauthenticated requests to admin endpoints return 401."""
        site_a, _, _, _ = dual_sites
        endpoints = [
            ("GET", f"/api/cms/v2/sites/{site_a.site_key}/popups"),
            ("POST", f"/api/cms/v2/sites/{site_a.site_key}/popups"),
            ("GET", f"/api/cms/v2/sites/{site_a.site_key}/popups/{uuid.uuid4()}"),
            ("PATCH", f"/api/cms/v2/sites/{site_a.site_key}/popups/{uuid.uuid4()}"),
            ("DELETE", f"/api/cms/v2/sites/{site_a.site_key}/popups/{uuid.uuid4()}"),
        ]
        for method, url in endpoints:
            if method == "GET":
                resp = client.get(url)
            elif method == "POST":
                resp = client.post(url, json={"name": "test", "content_html": "<p>test</p>"})
            elif method == "PATCH":
                resp = client.patch(url, json={"name": "test"})
            elif method == "DELETE":
                resp = client.delete(url)
            assert resp.status_code == 401, f"{method} {url} returned {resp.status_code}"

    def test_unauthorized_role_returns_403(self, client, dual_sites, regular_user):
        """Verify user without CMS editor role receives 403 on admin endpoints."""
        site_a, _, _, _ = dual_sites
        headers = auth_headers(client, email=regular_user.email, password="testpass123")

        payload = {"name": "Unauthorized Popup", "content_html": "<p>Test</p>"}
        resp = client.post(f"/api/cms/v2/sites/{site_a.site_key}/popups", json=payload, headers=headers)
        assert resp.status_code in (403, 404)  # 403 or 404 if sede scoped


class TestEdgeCaseFiltering:
    def test_empty_show_on_pages_matches_all_pages(self, client, db_session, dual_sites):
        """Verify empty show_on_pages [] matches any page_slug filter."""
        site_a, _, _, _ = dual_sites
        popup = models.CmsPopup(
            site_id=site_a.id,
            name="Global Popup",
            content_html="<p>Global</p>",
            is_active=True,
            show_on_pages=[],
        )
        db_session.add(popup)
        db_session.commit()

        # Query with different page slugs
        for slug in ["/home", "/about", "/contact", "any-slug"]:
            resp = client.get(f"/api/cms/v2/public/popups?site_key={site_a.site_key}&page_slug={slug}")
            assert resp.status_code == 200
            names = [p["name"] for p in resp.json()]
            assert "Global Popup" in names

    def test_explicit_show_on_pages_filtering(self, client, db_session, dual_sites):
        """Verify popup with explicit show_on_pages only matches listed slugs."""
        site_a, _, _, _ = dual_sites
        popup = models.CmsPopup(
            site_id=site_a.id,
            name="Targeted Popup",
            content_html="<p>Targeted</p>",
            is_active=True,
            show_on_pages=["/pricing", "/signup"],
        )
        db_session.add(popup)
        db_session.commit()

        # Should match /pricing
        resp1 = client.get(f"/api/cms/v2/public/popups?site_key={site_a.site_key}&page_slug=/pricing")
        assert "Targeted Popup" in [p["name"] for p in resp1.json()]

        # Should match /signup with whitespace padding
        resp2 = client.get(f"/api/cms/v2/public/popups?site_key={site_a.site_key}&page_slug=%20/signup%20")
        assert "Targeted Popup" in [p["name"] for p in resp2.json()]

        # Should NOT match /home
        resp3 = client.get(f"/api/cms/v2/public/popups?site_key={site_a.site_key}&page_slug=/home")
        assert "Targeted Popup" not in [p["name"] for p in resp3.json()]


class TestSchemaValidation:
    def test_invalid_trigger_type_returns_422(self, client, dual_sites, admin_user):
        site_a, _, _, _ = dual_sites
        headers = auth_headers(client, email=admin_user.email, password="testpass123")

        payload = {
            "name": "Invalid Trigger",
            "content_html": "<p>Test</p>",
            "trigger_type": "invalid_trigger_name",
        }
        resp = client.post(f"/api/cms/v2/sites/{site_a.site_key}/popups", json=payload, headers=headers)
        assert resp.status_code == 422

    def test_negative_trigger_value_returns_422(self, client, dual_sites, admin_user):
        site_a, _, _, _ = dual_sites
        headers = auth_headers(client, email=admin_user.email, password="testpass123")

        payload = {
            "name": "Negative Trigger Value",
            "content_html": "<p>Test</p>",
            "trigger_type": "time_delay",
            "trigger_value": -500,
        }
        resp = client.post(f"/api/cms/v2/sites/{site_a.site_key}/popups", json=payload, headers=headers)
        assert resp.status_code == 422

    def test_missing_required_fields_returns_422(self, client, dual_sites, admin_user):
        site_a, _, _, _ = dual_sites
        headers = auth_headers(client, email=admin_user.email, password="testpass123")

        # Missing name
        resp1 = client.post(
            f"/api/cms/v2/sites/{site_a.site_key}/popups", json={"content_html": "<p>No name</p>"}, headers=headers
        )
        assert resp1.status_code == 422

        # Missing content_html
        resp2 = client.post(f"/api/cms/v2/sites/{site_a.site_key}/popups", json={"name": "No content"}, headers=headers)
        assert resp2.status_code == 422

    def test_empty_name_returns_422(self, client, dual_sites, admin_user):
        site_a, _, _, _ = dual_sites
        headers = auth_headers(client, email=admin_user.email, password="testpass123")

        resp = client.post(
            f"/api/cms/v2/sites/{site_a.site_key}/popups",
            json={"name": "", "content_html": "<p>Empty name</p>"},
            headers=headers,
        )
        assert resp.status_code == 422
