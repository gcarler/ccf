"""Tests for CMS v2 Search Auto-Indexing Pipeline and Upgraded Search Endpoint."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import CmsPage, CmsPost, CmsSite, Persona, RolPlataforma, Sede, User
from backend.models_enterprise import SearchIndex, SearchPromotion
from backend.services.cms_search_indexer import (
    delete_from_search_index,
    index_cms_content,
)


@pytest.fixture
def auth_headers(db_session: Session) -> dict[str, str]:
    """Helper fixture to create an admin user and return headers."""
    role = db_session.query(RolPlataforma).filter(RolPlataforma.nombre == "ADMIN").first()
    if not role:
        role = RolPlataforma(
            id=uuid.uuid4(),
            nombre="ADMIN",
            permisos={"*": "allow"},
        )
        db_session.add(role)
        db_session.flush()

    sede = Sede(
        id=uuid.uuid4(),
        nombre="Sede Admin",
        ciudad="Bogota",
        es_activa=True,
    )
    db_session.add(sede)
    db_session.flush()

    persona = Persona(
        id=uuid.uuid4(),
        sede_id=sede.id,
        first_name="Admin",
        last_name="Tester",
        email=f"admin-{uuid.uuid4()}@example.com",
    )
    db_session.add(persona)
    db_session.flush()

    user = User(
        id=persona.id,
        sede_id=sede.id,
        username=f"admin-{uuid.uuid4().hex[:8]}",
        email=persona.email,
        password_hash="hashed_pass_test",
        rol_plataforma_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # Access token bypass fixture pattern in tests
    from backend.core.permissions import create_access_token

    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_site(db_session: Session) -> CmsSite:
    """Fixture for creating a test CMS site."""
    site_key = f"test-site-{uuid.uuid4().hex[:6]}"
    site = CmsSite(
        id=uuid.uuid4(),
        site_key=site_key,
        name="Test Search Site",
        base_path=f"/{site_key}",
    )
    db_session.add(site)
    db_session.commit()
    db_session.refresh(site)
    return site


class TestCmsSearchIndexing:
    def test_direct_indexing_service_upsert_and_delete(self, db_session: Session):
        """Test index_cms_content and delete_from_search_index direct service logic."""
        site_key = "test_service_site"
        entity_type = "page"
        entity_id = str(uuid.uuid4())

        # 1. Upsert new item
        item = index_cms_content(
            db=db_session,
            site_key=site_key,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_slug="nosotros-test",
            title="Sobre Nosotros",
            body_text="Información detallada de nuestra misión y visión.",
            category="general",
            tags=["mision", "historia"],
            is_published=True,
            boost_score=10,
        )
        assert item is not None
        assert item.title == "Sobre Nosotros"
        assert item.category == "general"
        assert item.tags == ["mision", "historia"]
        assert item.is_published is True

        # 2. Update existing item
        updated = index_cms_content(
            db=db_session,
            site_key=site_key,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_slug="nosotros-test-v2",
            title="Sobre Nosotros Actualizado",
            body_text="Nueva visión institucional.",
            category="general",
            tags=["mision", "actualizado"],
            is_published=True,
            boost_score=20,
        )
        assert updated.id == item.id
        assert updated.title == "Sobre Nosotros Actualizado"
        assert updated.boost_score == 20

        # 3. Delete item
        deleted = delete_from_search_index(
            db=db_session,
            site_key=site_key,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        assert deleted is True

        # Verify query returns empty
        found = (
            db_session.query(SearchIndex)
            .filter(
                SearchIndex.site_key == site_key,
                SearchIndex.entity_type == entity_type,
                SearchIndex.entity_id == entity_id,
            )
            .first()
        )
        assert found is None

    def test_auto_indexing_on_page_and_post_crud(
        self, client: TestClient, auth_headers: dict[str, str], test_site: CmsSite, db_session: Session
    ):
        """Test automatic search index creation, section updates, and deletion for pages & posts."""
        site_key = test_site.site_key

        # 1. Create page via API
        page_resp = client.post(
            f"/api/cms/v2/sites/{site_key}/pages",
            headers=auth_headers,
            json={
                "title": "Página Auto-Indexada",
                "slug": "pagina-auto-index",
                "status": "draft",
            },
        )
        assert page_resp.status_code == 201
        page_data = page_resp.json()
        page_id = page_data["id"]

        # Check search index created (is_published=False for draft)
        idx = (
            db_session.query(SearchIndex)
            .filter(
                SearchIndex.site_key == site_key,
                SearchIndex.entity_type == "page",
                SearchIndex.entity_id == page_id,
            )
            .first()
        )
        assert idx is not None
        assert idx.title == "Página Auto-Indexada"
        assert idx.is_published is False

        # 2. Add section to page
        sec_resp = client.post(
            f"/api/cms/v2/sites/{site_key}/pages/pagina-auto-index/sections",
            headers=auth_headers,
            json={
                "type": "rich_text",
                "props_json": {"heading": "Bienvenido", "body": "Contenido especial de prueba."},
            },
        )
        assert sec_resp.status_code == 201

        # Refresh index and verify body_text updated
        db_session.refresh(idx)
        assert "Contenido especial de prueba" in (idx.body_text or "")

        # 3. Publish page via workflow
        wf_resp = client.post(
            f"/api/cms/v2/sites/{site_key}/pages/pagina-auto-index/workflow",
            headers=auth_headers,
            json={"action": "publish", "notes": "Publicando página"},
        )
        assert wf_resp.status_code == 200

        db_session.refresh(idx)
        assert idx.is_published is True

        # 4. Create post via API
        post_resp = client.post(
            f"/api/cms/v2/sites/{site_key}/posts",
            headers=auth_headers,
            json={
                "title": "Publicación de Noticias",
                "slug": "noticias-auto-index",
                "excerpt": "Resumen de noticias",
                "content": "Contenido detallado del artículo informativo.",
                "status": "published",
            },
        )
        assert post_resp.status_code == 201
        post_data = post_resp.json()
        post_id = post_data["id"]

        post_idx = (
            db_session.query(SearchIndex)
            .filter(
                SearchIndex.site_key == site_key,
                SearchIndex.entity_type == "post",
                SearchIndex.entity_id == post_id,
            )
            .first()
        )
        assert post_idx is not None
        assert post_idx.title == "Publicación de Noticias"
        assert post_idx.is_published is True
        assert "Contenido detallado" in (post_idx.body_text or "")

        # 5. Delete post and page, verify search index entries removed
        del_post_resp = client.delete(f"/api/cms/v2/sites/{site_key}/posts/noticias-auto-index", headers=auth_headers)
        assert del_post_resp.status_code == 204

        post_idx_after = (
            db_session.query(SearchIndex)
            .filter(
                SearchIndex.site_key == site_key,
                SearchIndex.entity_type == "post",
                SearchIndex.entity_id == post_id,
            )
            .first()
        )
        assert post_idx_after is None

        del_page_resp = client.delete(f"/api/cms/v2/sites/{site_key}/pages/pagina-auto-index", headers=auth_headers)
        assert del_page_resp.status_code == 204

        page_idx_after = (
            db_session.query(SearchIndex)
            .filter(
                SearchIndex.site_key == site_key,
                SearchIndex.entity_type == "page",
                SearchIndex.entity_id == page_id,
            )
            .first()
        )
        assert page_idx_after is None

    def test_bulk_reindex_endpoint(
        self, client: TestClient, auth_headers: dict[str, str], test_site: CmsSite, db_session: Session
    ):
        """Test POST /api/cms/v2/search/reindex bulk re-indexing API."""
        site_key = test_site.site_key

        # Create page and post directly in DB
        page = CmsPage(
            id=uuid.uuid4(),
            site_id=test_site.id,
            slug="reindex-page",
            title="Página para Reindexar",
            status="published",
        )
        post = CmsPost(
            id=uuid.uuid4(),
            site_id=test_site.id,
            slug="reindex-post",
            title="Post para Reindexar",
            excerpt="Extracto de reindexación",
            content="Cuerpo de reindexación",
            status="published",
        )
        db_session.add_all([page, post])
        db_session.commit()

        # Execute bulk reindex endpoint
        resp = client.post(f"/api/cms/v2/search/reindex?site_key={site_key}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["indexed_pages"] >= 1
        assert data["indexed_posts"] >= 1
        assert data["total_indexed"] >= 2

        # Verify index entries exist
        idx_page = (
            db_session.query(SearchIndex)
            .filter(
                SearchIndex.site_key == site_key,
                SearchIndex.entity_type == "page",
                SearchIndex.entity_id == str(page.id),
            )
            .first()
        )
        assert idx_page is not None
        assert idx_page.title == "Página para Reindexar"

    def test_search_filtering_and_promotions(
        self, client: TestClient, auth_headers: dict[str, str], test_site: CmsSite, db_session: Session
    ):
        """Test search query matching with category, tags, date range, and promoted search items."""
        site_key = test_site.site_key

        # Insert test items in search index
        item1 = index_cms_content(
            db=db_session,
            site_key=site_key,
            entity_type="post",
            entity_id=str(uuid.uuid4()),
            entity_slug="conferencia-anual",
            title="Conferencia Anual de Tecnología",
            body_text="Grandes innovaciones tecnológicas y desarrollo de software.",
            category="eventos",
            tags=["tech", "conferencia"],
            is_published=True,
            boost_score=50,
        )

        index_cms_content(
            db=db_session,
            site_key=site_key,
            entity_type="post",
            entity_id=str(uuid.uuid4()),
            entity_slug="taller-diseno",
            title="Taller Práctico de Diseño UI",
            body_text="Aprende prototipado y experiencia de usuario.",
            category="educacion",
            tags=["diseño", "ui"],
            is_published=True,
            boost_score=10,
        )

        # Create a search promotion
        promo = SearchPromotion(
            id=uuid.uuid4(),
            site_key=site_key,
            query_text="tecnología",
            entity_type="post",
            entity_id=str(item1.entity_id),
            entity_slug="conferencia-anual",
            title="Destacado: Conferencia Anual",
            boost_score=100,
            is_active=True,
        )
        db_session.add(promo)
        db_session.commit()

        # 1. Search with query "tecnología" (GET & POST)
        resp_get = client.get(f"/api/cms/v2/search?site_key={site_key}&q=tecnología", headers=auth_headers)
        assert resp_get.status_code == 200
        get_data = resp_get.json()
        assert get_data["query"] == "tecnología"
        assert get_data["total"] >= 1
        assert len(get_data["promoted"]) == 1
        assert get_data["promoted"][0]["title"] == "Destacado: Conferencia Anual"

        # 2. Search POST with category filter
        resp_post_cat = client.post(
            "/api/cms/v2/search",
            headers=auth_headers,
            json={
                "site_key": site_key,
                "query": "",
                "category": "educacion",
            },
        )
        assert resp_post_cat.status_code == 200
        cat_data = resp_post_cat.json()
        assert cat_data["total"] == 1
        assert cat_data["results"][0]["entity_slug"] == "taller-diseno"

        # 3. Search POST with tags filter
        resp_post_tag = client.post(
            "/api/cms/v2/search",
            headers=auth_headers,
            json={
                "site_key": site_key,
                "query": "",
                "tags": ["tech"],
            },
        )
        assert resp_post_tag.status_code == 200
        tag_data = resp_post_tag.json()
        assert tag_data["total"] == 1
        assert tag_data["results"][0]["entity_slug"] == "conferencia-anual"
