"""Contrato del gateway MCP para todos los módulos de CCF."""

from __future__ import annotations

import asyncio

import pytest

from backend.mcp_platform import DEDICATED_MODULES, GENERIC_MODULE_SERVERS, MODULE_SPECS, platform_mcp


class TestMcpPlatformCatalog:
    def test_catalog_covers_every_module_and_dedicated_surface(self):
        result = platform_mcp._tool_manager._tools["list_platform_modules"].fn()
        assert result["count"] == len(MODULE_SPECS)
        slugs = {item["slug"] for item in result["items"]}
        assert {"projects", "finance", "finance-suite", "support", "wiki", "comments"} <= slugs
        assert {item["slug"] for item in result["items"] if item["dedicated_tools"]} == DEDICATED_MODULES

    def test_every_generic_module_has_three_standard_tools(self):
        async def collect():
            output = {}
            for slug, (server, _app) in GENERIC_MODULE_SERVERS.items():
                tools = await server.list_tools()
                output[slug] = {tool.name for tool in tools}
            return output

        tools_by_module = asyncio.run(collect())
        assert set(tools_by_module) == set(GENERIC_MODULE_SERVERS)
        for names in tools_by_module.values():
            assert {"module_info", "list_module_routes", "module_api_request"} <= names

    def test_generic_gateway_rejects_cross_module_paths_before_authentication(self):
        server, _app = GENERIC_MODULE_SERVERS["projects"]
        request_tool = server._tool_manager._tools["module_api_request"].fn

        with pytest.raises(PermissionError, match="no pertenece"):
            asyncio.run(request_tool("GET", "/api/crm/personas"))

    def test_read_only_public_module_rejects_mutation(self):
        server, _app = GENERIC_MODULE_SERVERS["public"]
        request_tool = server._tool_manager._tools["module_api_request"].fn

        with pytest.raises(PermissionError, match="solo lectura"):
            asyncio.run(request_tool("POST", "/api/public/contact", {"name": "x"}, {"message": "x"}))
