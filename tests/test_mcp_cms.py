"""Pruebas del MCP privado de CMS."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

from backend import models
from tests.conftest import TestingSessionLocal, seed_admin


@pytest.fixture
def cms_scope(db_session):
    admin, persona, sede = seed_admin(db_session, email="mcp-cms-admin@test.com")
    site = db_session.query(models.CmsSite).filter(models.CmsSite.site_key == "ccf").first()
    if not site:
        site = models.CmsSite(
            id=uuid.uuid4(),
            site_key="ccf",
            name="Sitio CCF",
            is_active=True,
            sede_id=sede.id,
        )
        db_session.add(site)
        db_session.commit()
    return {"admin_id": admin.id, "persona": persona, "sede": sede, "site": site}


def _authenticate(subject):
    return auth_context_var.set(
        AuthenticatedUser(
            AccessToken(
                token="cms-test-token",
                client_id="test-client",
                subject=str(subject),
                scopes=["cms:read", "cms:edit", "cms:manage"],
            )
        )
    )


class TestMcpCmsContract:
    def test_registers_cms_tools(self):
        from backend.mcp_cms import cms_mcp

        tools = asyncio.run(cms_mcp.list_tools())
        names = {tool.name for tool in tools}
        assert {
            "list_cms_posts",
            "get_cms_post",
            "create_cms_post",
            "update_cms_post",
            "delete_cms_post",
            "publish_cms_post",
            "list_cms_categories",
            "list_cms_pages",
            "get_cms_page",
            "create_cms_page",
        } <= names

    def test_post_lifecycle_through_cms_mcp(self, monkeypatch, cms_scope):
        import backend.mcp_cms as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(cms_scope["admin_id"])
        try:
            slug = f"post-test-{uuid.uuid4().hex[:6]}"
            # 1. Create draft
            created = module.create_cms_post(
                title="Publicación de Prueba MCP",
                slug=slug,
                content="Contenido de prueba MCP",
                excerpt="Extracto de prueba",
                site_key="ccf",
                status="draft",
            )
            assert created["slug"] == slug
            assert created["status"] == "draft"

            # 2. Get post
            post = module.get_cms_post(slug=slug, site_key="ccf")
            assert post["title"] == "Publicación de Prueba MCP"

            # 3. Update post
            updated = module.update_cms_post(
                slug=slug,
                changes={"title": "Publicación Actualizada MCP"},
                site_key="ccf",
            )
            assert updated["title"] == "Publicación Actualizada MCP"

            # 4. Publish post
            published = module.publish_cms_post(slug=slug, site_key="ccf")
            assert published["status"] == "published"
            assert published["published_at"] is not None

            # 5. List posts
            listing = module.list_cms_posts(site_key="ccf", limit=10)
            assert listing["total"] >= 1
            assert any(item["slug"] == slug for item in listing["items"])

            # 6. Delete (archive) post
            deleted = module.delete_cms_post(slug=slug, site_key="ccf")
            assert deleted["status"] == "archived"
        finally:
            auth_context_var.reset(token)

    def test_page_lifecycle_through_cms_mcp(self, monkeypatch, cms_scope):
        import backend.mcp_cms as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(cms_scope["admin_id"])
        try:
            slug = f"page-test-{uuid.uuid4().hex[:6]}"
            # Create page
            page = module.create_cms_page(
                slug=slug,
                title="Página de Prueba MCP",
                site_key="ccf",
            )
            assert page["slug"] == slug

            # Get page
            got = module.get_cms_page(slug=slug, site_key="ccf")
            assert got["title"] == "Página de Prueba MCP"

            # List pages
            listing = module.list_cms_pages(site_key="ccf", limit=10)
            assert listing["total"] >= 1
        finally:
            auth_context_var.reset(token)
