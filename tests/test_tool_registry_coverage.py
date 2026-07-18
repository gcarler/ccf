"""
Coverage for tool_registry module.
"""
from backend.services.tool_registry import (
    ToolRegistry, ToolDefinition, ToolParameter,
    register_all_tools,
)


class TestToolRegistry:
    def test_registry_init(self):
        r = ToolRegistry()
        assert r is not None
        assert len(r._tools) == 0

    def test_register_all_tools(self):
        registry = register_all_tools()
        assert isinstance(registry, ToolRegistry)

    def test_tool_parameter_creation(self):
        p = ToolParameter(name="test", type="string", description="Test param", required=True)
        assert p.name == "test"
        assert p.required is True

    def test_tool_definition_creation(self):
        td = ToolDefinition(
            name="test_tool",
            description="A test tool",
            module="test",
            parameters=[ToolParameter(name="p1", type="string", description="P1")],
        )
        assert td.name == "test_tool"
        assert len(td.parameters) == 1
