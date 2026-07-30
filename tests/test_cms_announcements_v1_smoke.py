"""Smoke tests for CMS v1 announcements endpoints (backed by CmsPost adapters).

Exercises every v1 /cms/announcements and /admin/announcements endpoint,
including CRUD, 404, and auth-gate scenarios, to verify the adapter layer
is working correctly after the legacy Announcement model removal.
"""
import uuid

import pytest
from fastapi import status

from tests.conftest import auth_headers, seed_admin

pytestmark = pytest.mark.usefixtures("db_session")


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def admin_data(db_session):
    user, persona, sede = seed_admin(db_session)
    return user, persona, sede


@pytest.fixture
def client_auth(client, db_session, admin_data):
    headers = auth_headers(client)
    return client, headers, admin_data


# ── Announcement payload helpers ────────────────────────────────────────


def _make_create_payload(overrides: dict | None = None) -> dict:
    payload = {
        "title": f"Smoke Test Announcement {uuid.uuid4().hex[:8]}",
        "content": "<p>This is a smoke test announcement content.</p>",
        "status": "published",
    }
    if overrides:
        payload.update(overrides)
    return payload


def _make_update_payload(overrides: dict | None = None) -> dict:
    payload = {
        "title": f"Updated Announcement {uuid.uuid4().hex[:8]}",
        "content": "<p>Updated content for smoke test.</p>",
    }
    if overrides:
        payload.update(overrides)
    return payload


# ═══════════════════════════════════════════════════════════════════════
# 1. PUBLIC ENDPOINTS — no auth required beyond what the router provides
# ═══════════════════════════════════════════════════════════════════════


class TestPublicAnnouncements:
    """Tests for ``GET /cms/announcements`` (public feed)."""

    def test_list_public_no_auth(self, client):
        """Public feed must work without auth headers."""
        resp = client.get("/api/cms/announcements")
        assert resp.status_code == status.HTTP_200_OK, (
            f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        )
        data = resp.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"

    def test_list_public_empty(self, client):
        """Should return empty list when no announcements exist."""
        resp = client.get("/api/cms/announcements")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == [], "Expected empty list for public feed"

    def test_get_public_not_found(self, client):
        """Getting a non-existent announcement returns 404."""
        fake_id = uuid.uuid4()
        resp = client.get(f"/api/cms/announcements/{fake_id}")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ═══════════════════════════════════════════════════════════════════════
# 2. CRUD ENDPOINTS — require auth (admin)
# ═══════════════════════════════════════════════════════════════════════


class TestAdminAnnouncementsCRUD:
    """Full CRUD cycle for ``/admin/announcements`` endpoints."""

    def test_create_announcement(self, client_auth):
        """POST /admin/announcements → 201 + AnnouncementRead."""
        client, headers, (user, persona, sede) = client_auth
        payload = _make_create_payload()

        # Note: the POST endpoint for announcements is at /cms/announcements
        resp = client.post("/api/cms/announcements", json=payload, headers=headers)
        assert resp.status_code == status.HTTP_201_CREATED, (
            f"Expected 201, got {resp.status_code}: {resp.text[:300]}"
        )
        data = resp.json()
        assert "id" in data, f"Missing 'id' in response: {data}"
        assert data["title"] == payload["title"]
        assert data["status"] == "published"

    def test_create_unpublished_draft(self, client_auth):
        """Announcements can be created as draft."""
        client, headers, _ = client_auth
        payload = _make_create_payload({"status": "draft"})
        resp = client.post("/api/cms/announcements", json=payload, headers=headers)
        assert resp.status_code == status.HTTP_201_CREATED, resp.text[:300]
        assert resp.json()["status"] == "draft"

    def test_list_admin(self, client_auth):
        """GET /admin/announcements → list with auth."""
        client, headers, _ = client_auth
        resp = client.get("/api/admin/announcements", headers=headers)
        assert resp.status_code == status.HTTP_200_OK, resp.text[:200]
        data = resp.json()
        assert isinstance(data, list)

    def test_list_admin_no_auth(self, client):
        """Admin list without auth → 401/403."""
        resp = client.get("/api/admin/announcements")
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ), f"Expected 401/403, got {resp.status_code}"

    def test_create_no_auth(self, client):
        """POST without auth → 401/403."""
        payload = _make_create_payload()
        resp = client.post("/api/cms/announcements", json=payload)
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ), f"Expected 401/403, got {resp.status_code}"

    def test_get_admin_by_id(self, client_auth):
        """GET /admin/announcements/{id} → single announcement."""
        client, headers, _ = client_auth
        # First create one
        payload = _make_create_payload()
        created = client.post("/api/cms/announcements", json=payload, headers=headers)
        assert created.status_code == status.HTTP_201_CREATED
        ann_id = created.json()["id"]

        # Then get it
        resp = client.get(f"/api/admin/announcements/{ann_id}", headers=headers)
        assert resp.status_code == status.HTTP_200_OK, resp.text[:300]
        assert resp.json()["id"] == ann_id

    def test_get_admin_not_found(self, client_auth):
        """GET /admin/announcements/{nonexistent} → 404."""
        client, headers, _ = client_auth
        fake_id = uuid.uuid4()
        resp = client.get(f"/api/admin/announcements/{fake_id}", headers=headers)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_get_public_by_id(self, client_auth):
        """GET /cms/announcements/{id} → public view of published."""
        client, headers, _ = client_auth
        # Create published announcement
        payload = _make_create_payload()
        created = client.post("/api/cms/announcements", json=payload, headers=headers)
        assert created.status_code == status.HTTP_201_CREATED
        ann_id = created.json()["id"]

        # Public get (no auth needed)
        resp = client.get(f"/api/cms/announcements/{ann_id}")
        assert resp.status_code == status.HTTP_200_OK, resp.text[:300]
        assert resp.json()["id"] == ann_id

    def test_get_public_draft_not_found(self, client_auth):
        """Public GET should NOT expose draft announcements (404)."""
        client, headers, _ = client_auth
        payload = _make_create_payload({"status": "draft"})
        created = client.post("/api/cms/announcements", json=payload, headers=headers)
        assert created.status_code == status.HTTP_201_CREATED
        ann_id = created.json()["id"]

        resp = client.get(f"/api/cms/announcements/{ann_id}")
        assert resp.status_code == status.HTTP_404_NOT_FOUND, (
            f"Draft should be 404 for public, got {resp.status_code}"
        )

    def test_patch_announcement(self, client_auth):
        """PATCH /admin/announcements/{id} → update title/content."""
        client, headers, _ = client_auth
        # Create
        payload = _make_create_payload()
        created = client.post("/api/cms/announcements", json=payload, headers=headers)
        assert created.status_code == status.HTTP_201_CREATED
        ann_id = created.json()["id"]

        # Update
        update = _make_update_payload()
        resp = client.patch(
            f"/api/admin/announcements/{ann_id}", json=update, headers=headers
        )
        assert resp.status_code == status.HTTP_200_OK, resp.text[:300]
        data = resp.json()
        assert data["id"] == ann_id
        assert data["title"] == update["title"]

    def test_patch_announcement_status(self, client_auth):
        """PATCH can change status (published → draft)."""
        client, headers, _ = client_auth
        payload = _make_create_payload()
        created = client.post("/api/cms/announcements", json=payload, headers=headers)
        ann_id = created.json()["id"]

        resp = client.patch(
            f"/api/admin/announcements/{ann_id}",
            json={"status": "draft"},
            headers=headers,
        )
        assert resp.status_code == status.HTTP_200_OK, resp.text[:300]
        assert resp.json()["status"] == "draft"

    def test_patch_not_found(self, client_auth):
        """PATCH on nonexistent → 404."""
        client, headers, _ = client_auth
        fake_id = uuid.uuid4()
        resp = client.patch(
            f"/api/admin/announcements/{fake_id}",
            json={"title": "Nope"},
            headers=headers,
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_no_auth(self, client):
        """PATCH without auth → 401/403."""
        fake_id = uuid.uuid4()
        resp = client.patch(
            f"/api/admin/announcements/{fake_id}",
            json={"title": "Nope"},
        )
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_delete_announcement(self, client_auth):
        """DELETE /admin/announcements/{id} → 204."""
        client, headers, _ = client_auth
        payload = _make_create_payload()
        created = client.post("/api/cms/announcements", json=payload, headers=headers)
        assert created.status_code == status.HTTP_201_CREATED
        ann_id = created.json()["id"]

        resp = client.delete(f"/api/admin/announcements/{ann_id}", headers=headers)
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's gone (soft-delete = not found for admin GET)
        get_resp = client.get(f"/api/admin/announcements/{ann_id}", headers=headers)
        assert get_resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_not_found(self, client_auth):
        """DELETE on nonexistent → 404."""
        client, headers, _ = client_auth
        fake_id = uuid.uuid4()
        resp = client.delete(f"/api/admin/announcements/{fake_id}", headers=headers)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_no_auth(self, client):
        """DELETE without auth → 401/403."""
        fake_id = uuid.uuid4()
        resp = client.delete(f"/api/admin/announcements/{fake_id}")
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


# ═══════════════════════════════════════════════════════════════════════
# 3. METRICS — announcements counted via CmsPost
# ═══════════════════════════════════════════════════════════════════════


class TestAnnouncementsMetrics:
    """Verify announcements are properly counted in CMS metrics."""

    def test_metrics_include_announcements(self, client_auth):
        """GET /cms/metrics returns announcements_total and announcements_active."""
        client, headers, _ = client_auth
        resp = client.get("/api/cms/metrics", headers=headers)
        assert resp.status_code == status.HTTP_200_OK, resp.text[:200]
        data = resp.json()
        assert "announcements_total" in data
        assert "announcements_active" in data
        assert isinstance(data["announcements_total"], int)
        assert isinstance(data["announcements_active"], int)

    def test_metrics_count_increases_after_create(self, client_auth):
        """Creating a published announcement increments metrics."""
        client, headers, _ = client_auth

        # Get baseline
        baseline = client.get("/api/cms/metrics", headers=headers).json()
        base_total = baseline["announcements_total"]
        base_active = baseline["announcements_active"]

        # Create published
        payload = _make_create_payload()
        created = client.post("/api/cms/announcements", json=payload, headers=headers)
        assert created.status_code == status.HTTP_201_CREATED

        # Verify metrics increased
        after = client.get("/api/cms/metrics", headers=headers).json()
        assert after["announcements_total"] == base_total + 1, (
            f"Expected total {base_total + 1}, got {after['announcements_total']}"
        )
        assert after["announcements_active"] == base_active + 1, (
            f"Expected active {base_active + 1}, got {after['announcements_active']}"
        )

    def test_metrics_no_auth(self, client):
        """Metrics without auth → 401/403."""
        resp = client.get("/api/cms/metrics")
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


# ═══════════════════════════════════════════════════════════════════════
# 4. VALIDATION — error handling
# ═══════════════════════════════════════════════════════════════════════


class TestAnnouncementsValidation:
    """Input validation edge cases."""

    def test_create_invalid_body(self, client_auth):
        """POST with empty body → 422."""
        client, headers, _ = client_auth
        resp = client.post("/api/cms/announcements", json={}, headers=headers)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, (
            f"Expected 422, got {resp.status_code}: {resp.text[:200]}"
        )

    def test_create_missing_title(self, client_auth):
        """POST without required title → 422."""
        client, headers, _ = client_auth
        resp = client.post(
            "/api/cms/announcements",
            json={"content": "<p>No title</p>"},
            headers=headers,
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_patch_invalid_uuid(self, client_auth):
        """PATCH with non-UUID id → 422."""
        client, headers, _ = client_auth
        resp = client.patch(
            "/api/admin/announcements/not-a-uuid",
            json={"title": "test"},
            headers=headers,
        )
        # FastAPI returns 422 for path param validation errors
        assert resp.status_code in (
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_404_NOT_FOUND,
        )
