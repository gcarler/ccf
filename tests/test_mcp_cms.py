from __future__ import annotations

import asyncio

import httpx
import pytest
from fastapi import HTTPException

from backend.api.mcp.auth import _request_bearer_token
from backend.api.mcp.server import mcp
from backend.app import app


class _Headers:
    def __init__(self, authorization: str = ""):
        self._authorization = authorization

    def get(self, key: str, default: str = "") -> str:
        if key.lower() == "authorization":
            return self._authorization
        return default


class _Request:
    def __init__(self, authorization: str = ""):
        self.headers = _Headers(authorization)


class _RequestContext:
    def __init__(self, authorization: str = ""):
        self.request = _Request(authorization)


class _Context:
    def __init__(self, authorization: str = ""):
        self.request_context = _RequestContext(authorization)


def test_mcp_requires_bearer_token():
    with pytest.raises(HTTPException) as error:
        _request_bearer_token(_Context())

    assert error.value.status_code == 401


def test_mcp_extracts_ccf_bearer_token():
    assert _request_bearer_token(_Context("Bearer ccf-access-token")) == "ccf-access-token"


def test_cms_tools_are_registered_with_safety_annotations():
    tools = {tool.name: tool for tool in asyncio.run(mcp.list_tools())}

    assert {
        "list_sites",
        "list_pages",
        "get_page",
        "preview_page",
        "list_themes",
        "list_menus",
        "create_page_draft",
        "update_page_draft",
        "publish_page",
    } <= tools.keys()
    assert tools["list_pages"].annotations.readOnlyHint is True
    assert tools["create_page_draft"].annotations.readOnlyHint is False
    assert tools["publish_page"].annotations.destructiveHint is True


def test_mcp_transport_requires_authentication():
    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/api/mcp/")

    response = asyncio.run(request())
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
