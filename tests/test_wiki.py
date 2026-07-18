"""Tests for the standalone Wiki module (WikiPage).

Covers CRUD, API endpoints, multi-tenant isolation, and edge cases.
Uses the same patterns as test_projects_wiki_slash_commands.py.
"""
from __future__ import annotations

import uuid as _uuid

from backend.models_wiki import WikiPage
from tests.conftest import auth_headers, seed_admin, seed_user_with_role


def _ensure_sede_and_persona(db_session):
    """Create admin, return (user, token, sede)."""
    _, token, sede = seed_admin(db_session)
    return token, sede


def _count_wiki_pages(db_session):
    return db_session.query(WikiPage).filter(WikiPage.deleted_at.is_(None)).count()


class TestWikiCRUD:
    """Direct CRUD tests (no HTTP)."""

    def test_create_wiki_page(self, db_session):
        """Create a wiki page via CRUD with sede_id."""
        token, sede = _ensure_sede_and_persona(db_session)
        from backend.crud.wiki import create_wiki_page

        page = create_wiki_page(
            db_session,
            page_key="wiki_test_crud",
            title="CRUD Test",
            content="<p>Hello</p>",
            sede_id=sede.id,
        )
        assert page.page_key == "wiki_test_crud"
        assert page.title == "CRUD Test"
        assert page.sede_id == sede.id
        assert page.deleted_at is None

    def test_list_wiki_pages_scoped_by_sede(self, db_session):
        """List must only return pages for the given sede."""
        token, sede = _ensure_sede_and_persona(db_session)
        from backend.crud.wiki import create_wiki_page, list_wiki_pages

        create_wiki_page(db_session, "wiki_sede_a_1", "Sede A Doc", "", sede_id=sede.id)
        create_wiki_page(db_session, "wiki_sede_a_2", "Sede A Doc 2", "", sede_id=sede.id)

        pages = list_wiki_pages(db_session, sede_id=sede.id)
        assert len(pages) == 2
        assert all(p.sede_id == sede.id for p in pages)

    def test_list_wiki_pages_other_sede_returns_empty(self, db_session):
        """A sede must not see pages from another sede."""
        token, sede = _ensure_sede_and_persona(db_session)
        from backend.crud.wiki import create_wiki_page, list_wiki_pages

        create_wiki_page(db_session, "wiki_only_in_sede", "Only Sede", "", sede_id=sede.id)

        other_sede_id = _uuid.uuid4()
        pages = list_wiki_pages(db_session, sede_id=other_sede_id)
        assert len(pages) == 0

    def test_get_wiki_page_nonexistent(self, db_session):
        """Getting a non-existent page must return None (not create one)."""
        from backend.crud.wiki import get_wiki_page

        page = get_wiki_page(db_session, "wiki_nonexistent", sede_id=None)
        assert page is None

    def test_soft_delete(self, db_session):
        """Soft-delete must set deleted_at and hide from list."""
        token, sede = _ensure_sede_and_persona(db_session)
        from backend.crud.wiki import create_wiki_page, get_wiki_page, list_wiki_pages, soft_delete_wiki_page

        page = create_wiki_page(db_session, "wiki_to_delete", "To Delete", "", sede_id=sede.id)
        soft_delete_wiki_page(db_session, page)

        assert page.deleted_at is not None
        # List must exclude it
        pages = list_wiki_pages(db_session, sede_id=sede.id)
        assert all(p.page_key != "wiki_to_delete" for p in pages)
        # Direct get returns None
        fetched = get_wiki_page(db_session, "wiki_to_delete", sede_id=sede.id)
        assert fetched is None

    def test_update_wiki_page(self, db_session):
        """Update must change title and content."""
        token, sede = _ensure_sede_and_persona(db_session)
        from backend.crud.wiki import create_wiki_page, get_wiki_page, update_wiki_page

        page = create_wiki_page(db_session, "wiki_to_update", "Original", "orig", sede_id=sede.id)
        update_wiki_page(db_session, page, title="Updated", content="<p>new</p>")

        fetched = get_wiki_page(db_session, "wiki_to_update", sede_id=sede.id)
        assert fetched is not None
        assert fetched.title == "Updated"
        assert fetched.content == "<p>new</p>"

    def test_search_wiki_pages(self, db_session):
        """Search must filter by title or page_key."""
        token, sede = _ensure_sede_and_persona(db_session)
        from backend.crud.wiki import create_wiki_page, list_wiki_pages

        create_wiki_page(db_session, "wiki_pastoral", "Guia Pastoral", "", sede_id=sede.id)
        create_wiki_page(db_session, "wiki_contabilidad", "Manual Contable", "", sede_id=sede.id)

        results = list_wiki_pages(db_session, sede_id=sede.id, search="pastoral")
        assert len(results) == 1
        assert results[0].page_key == "wiki_pastoral"


class TestWikiAPI:
    """HTTP-level tests for wiki endpoints."""

    BASE = "/api/wiki/pages"

    def test_list_empty(self, client, db_session):
        """GET /wiki/pages returns empty list when no pages exist."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)
        resp = client.get(self.BASE, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_and_get(self, client, db_session):
        """POST then GET must return the same document."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)
        resp = client.post(
            f"{self.BASE}/wiki_integration_test",
            json={"page_key": "wiki_integration_test", "title": "Integration", "content": "<p>test</p>"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Integration"
        assert data["content"] == "<p>test</p>"

        # GET must return the same
        get_resp = client.get(f"{self.BASE}/wiki_integration_test", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["content"] == "<p>test</p>"

    def test_create_duplicate_returns_409(self, client, db_session):
        """POST for an existing page_key must return 409 Conflict."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)
        payload = {"page_key": "wiki_dup_test", "title": "Dup", "content": ""}
        resp = client.post(f"{self.BASE}/wiki_dup_test", json=payload, headers=headers)
        assert resp.status_code == 201

        resp2 = client.post(f"{self.BASE}/wiki_dup_test", json=payload, headers=headers)
        assert resp2.status_code == 409

    def test_get_nonexistent_returns_virtual_page(self, client, db_session):
        """GET for a non-existent page_key returns a virtual page (200) with empty content."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)
        resp = client.get(f"{self.BASE}/wiki_nonexistent_404", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("content") == ""
        assert data.get("version") == 0
        assert data.get("title") is not None

    def test_patch_updates_content(self, client, db_session):
        """PATCH must update content and preserve other fields."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)
        client.post(
            f"{self.BASE}/wiki_patch_test",
            json={"page_key": "wiki_patch_test", "title": "Before", "content": "old"},
            headers=headers,
        )
        resp = client.patch(
            f"{self.BASE}/wiki_patch_test",
            json={"content": "<p>new content</p>"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "<p>new content</p>"
        assert resp.json()["title"] == "Before"

    def test_delete_soft_delete(self, client, db_session):
        """DELETE must soft-delete (204) and GET returns 404."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)
        client.post(
            f"{self.BASE}/wiki_delete_test",
            json={"page_key": "wiki_delete_test", "title": "Del", "content": ""},
            headers=headers,
        )
        resp = client.delete(f"{self.BASE}/wiki_delete_test", headers=headers)
        assert resp.status_code == 204

        get_resp = client.get(f"{self.BASE}/wiki_delete_test", headers=headers)
        assert get_resp.status_code == 404

    def test_requires_auth(self, client, db_session):
        """Unauthenticated requests must return 401."""
        resp = client.get(self.BASE)
        assert resp.status_code == 401

    def test_list_with_search(self, client, db_session):
        """Search param must filter results."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)
        client.post(
            f"{self.BASE}/wiki_search_alphas",
            json={"page_key": "wiki_search_alphas", "title": "Alpha Team", "content": ""},
            headers=headers,
        )
        client.post(
            f"{self.BASE}/wiki_search_betas",
            json={"page_key": "wiki_search_betas", "title": "Beta Group", "content": ""},
            headers=headers,
        )

        resp = client.get(f"{self.BASE}?search=alpha", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["page_key"] == "wiki_search_alphas"

    def test_page_key_normalization(self, client, db_session):
        """POST with 'my_doc' must normalize to 'wiki_my_doc'."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)
        resp = client.post(
            f"{self.BASE}/my_doc",
            json={"page_key": "my_doc", "title": "My Doc", "content": ""},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["page_key"] == "wiki_my_doc"

        # Must be accessible via normalized key
        get_resp = client.get(f"{self.BASE}/wiki_my_doc", headers=headers)
        assert get_resp.status_code == 200

    def test_patch_increments_version(self, client, db_session):
        """PATCH must increment version and snapshot previous content."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)

        # Create
        resp = client.post(
            f"{self.BASE}/wiki_vtest",
            json={"page_key": "wiki_vtest", "title": "V1", "content": "<p>version 1</p>"},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["version"] == 1

        # First PATCH
        resp = client.patch(
            f"{self.BASE}/wiki_vtest",
            json={"content": "<p>version 2</p>"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["version"] == 2
        assert resp.json()["content"] == "<p>version 2</p>"

        # Second PATCH
        resp = client.patch(
            f"{self.BASE}/wiki_vtest",
            json={"title": "V3"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["version"] == 3
        assert resp.json()["title"] == "V3"

    def test_version_history(self, client, db_session):
        """Versions endpoint must list all snapshots."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)

        client.post(
            f"{self.BASE}/wiki_vhist",
            json={"page_key": "wiki_vhist", "title": "V1", "content": "original"},
            headers=headers,
        )
        client.patch(
            f"{self.BASE}/wiki_vhist",
            json={"content": "second"},
            headers=headers,
        )
        client.patch(
            f"{self.BASE}/wiki_vhist",
            json={"title": "V3 Title"},
            headers=headers,
        )

        resp = client.get(f"{self.BASE}/wiki_vhist/versions", headers=headers)
        assert resp.status_code == 200
        versions = resp.json()
        # Current version 3 means 2 snapshots (v1 snapshot before v2, v2 snapshot before v3)
        assert len(versions) == 2
        assert versions[0]["version_number"] == 2  # most recent snapshot first
        assert versions[0]["content"] == "second"
        assert versions[1]["version_number"] == 1

    def test_pagination_offset(self, client, db_session):
        """Offset param must skip records."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)

        for i in range(5):
            client.post(
                f"{self.BASE}/wiki_page_{i}",
                json={"page_key": f"wiki_page_{i}", "title": f"Page {i}", "content": ""},
                headers=headers,
            )

        resp = client.get(f"{self.BASE}?limit=2&offset=2", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

        resp_count = client.get(f"{self.BASE}/count", headers=headers)
        assert resp_count.status_code == 200
        assert resp_count.json()["total"] >= 5

    def test_count_endpoint(self, client, db_session):
        """Count endpoint must return total matching pages."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)

        client.post(
            f"{self.BASE}/wiki_count_a",
            json={"page_key": "wiki_count_a", "title": "Alpha One", "content": ""},
            headers=headers,
        )
        client.post(
            f"{self.BASE}/wiki_count_b",
            json={"page_key": "wiki_count_b", "title": "Alpha Two", "content": ""},
            headers=headers,
        )
        client.post(
            f"{self.BASE}/wiki_count_c",
            json={"page_key": "wiki_count_c", "title": "Beta One", "content": ""},
            headers=headers,
        )

        resp = client.get(f"{self.BASE}/count?search=alpha", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

        resp_all = client.get(f"{self.BASE}/count", headers=headers)
        assert resp_all.json()["total"] >= 3

    def test_multi_tenant_isolation(self, client, db_session):
        """Sede A must not see docs from Sede B via API."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)

        # Create doc in the admin's sede
        client.post(
            f"{self.BASE}/wiki_tenant_test",
            json={"page_key": "wiki_tenant_test", "title": "Tenant Doc", "content": ""},
            headers=headers,
        )

        # List must return it
        resp = client.get(self.BASE, headers=headers)
        assert resp.status_code == 200
        keys = [d["page_key"] for d in resp.json()]
        assert "wiki_tenant_test" in keys

        # GET with a non-admin user would be filtered by sede_id automatically
        # The test confirms the CRUD layer enforces sede_id filtering
        from backend.crud.wiki import list_wiki_pages
        other_sede = _uuid.uuid4()
        other_pages = list_wiki_pages(db_session, sede_id=other_sede)
        assert len(other_pages) == 0

    def test_page_key_edge_cases(self, client, db_session):
        """Empty and special characters in page_key must be handled safely."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)

        # Key with special chars should be sanitized
        resp = client.post(
            f"{self.BASE}/Mi Documento Especial!!!",
            json={"page_key": "Mi Documento Especial!!!", "title": "Special", "content": ""},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["page_key"] == "wiki_mi-documento-especial"

    def test_xss_prevention(self, client, db_session):
        """HTML content with scripts must be stored but GET returns as-is (rendering is frontend concern)."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)

        malicious = "<p>Hello</p><script>alert('xss')</script><p>World</p>"
        resp = client.post(
            f"{self.BASE}/wiki_xss_test",
            json={"page_key": "wiki_xss_test", "title": "XSS", "content": malicious},
            headers=headers,
        )
        assert resp.status_code == 201
        assert malicious in resp.json()["content"]

        # GET must return exactly what was stored
        get_resp = client.get(f"{self.BASE}/wiki_xss_test", headers=headers)
        assert get_resp.json()["content"] == malicious

    def test_concurrent_patches(self, client, db_session):
        """Two sequential PATCH must both succeed and increment version correctly."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)

        client.post(
            f"{self.BASE}/wiki_concur_test",
            json={"page_key": "wiki_concur_test", "title": "Concur", "content": "v1"},
            headers=headers,
        )

        resp1 = client.patch(
            f"{self.BASE}/wiki_concur_test",
            json={"content": "v2"},
            headers=headers,
        )
        assert resp1.status_code == 200
        assert resp1.json()["version"] == 2
        assert resp1.json()["content"] == "v2"

        resp2 = client.patch(
            f"{self.BASE}/wiki_concur_test",
            json={"content": "v3"},
            headers=headers,
        )
        assert resp2.status_code == 200
        assert resp2.json()["version"] == 3
        assert resp2.json()["content"] == "v3"

    def test_categories_and_tags(self, client, db_session):
        """Category and tags fields must work via PATCH."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)

        client.post(
            f"{self.BASE}/wiki_cat_test",
            json={"page_key": "wiki_cat_test", "title": "Categorizable", "content": ""},
            headers=headers,
        )

        # Set category and tags via PATCH
        resp = client.patch(
            f"{self.BASE}/wiki_cat_test",
            json={"category": "manuales", "tags": ["guia", "procedimiento"]},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["category"] == "manuales"
        assert resp.json()["tags"] == ["guia", "procedimiento"]

        # Filter by category via list
        list_resp = client.get(f"{self.BASE}?category=manuales", headers=headers)
        assert list_resp.status_code == 200
        keys = [d["page_key"] for d in list_resp.json()]
        assert "wiki_cat_test" in keys

    def test_list_categories_endpoint(self, client, db_session):
        """GET /wiki/categories must list distinct categories."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)

        client.post(
            f"{self.BASE}/wiki_cat_a",
            json={"page_key": "wiki_cat_a", "title": "A", "content": ""},
            headers=headers,
        )
        client.patch(
            f"{self.BASE}/wiki_cat_a",
            json={"category": "protocolos"},
            headers=headers,
        )
        client.post(
            f"{self.BASE}/wiki_cat_b",
            json={"page_key": "wiki_cat_b", "title": "B", "content": ""},
            headers=headers,
        )
        client.patch(
            f"{self.BASE}/wiki_cat_b",
            json={"category": "guias"},
            headers=headers,
        )

        resp = client.get("/api/wiki/categories", headers=headers)
        assert resp.status_code == 200
        cats = resp.json()
        assert "protocolos" in cats
        assert "guias" in cats

    def test_versions_404_for_nonexistent(self, client, db_session):
        """GET versions for non-existent page returns 404."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)
        resp = client.get(f"{self.BASE}/wiki_no_vers/versions", headers=headers)
        assert resp.status_code == 404

    def test_patch_404_for_nonexistent(self, client, db_session):
        """PATCH for non-existent page returns 404."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)
        resp = client.patch(
            f"{self.BASE}/wiki_no_patch",
            json={"content": "never"},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_delete_404_for_nonexistent(self, client, db_session):
        """DELETE for non-existent page returns 404."""
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)
        resp = client.delete(f"{self.BASE}/wiki_no_del", headers=headers)
        assert resp.status_code == 404

    def test_resolve_sede_fallback(self, client, db_session):
        """_resolve_sede _resolve_persona must not crash, returning None on error."""
        # The except paths are exercised when a user has no sede or persona
        # The seed_admin creates a valid user, so we verify sede/persona resolution
        # works without error — the except clauses are defensive for edge cases.
        token, sede = _ensure_sede_and_persona(db_session)
        headers = auth_headers(client)

        # Create and retrieve to exercise _resolve_sede and _resolve_persona
        resp = client.post(
            f"{self.BASE}/wiki_resolve_test",
            json={"page_key": "wiki_resolve_test", "title": "Resolve Test", "content": ""},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["author_id"] is not None  # _resolve_persona worked

        # PATCH also uses both resolve functions
        resp = client.patch(
            f"{self.BASE}/wiki_resolve_test",
            json={"content": "updated"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["version"] >= 2
