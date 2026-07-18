"""
Coverage tests for backend services — unit tests for pure-logic functions.
"""
import pytest

from backend.services.automation_engine import AutomationEngine
from backend.services.email_block_renderer import render_blocks_to_html, is_blocks_json


class TestEmailBlockRenderer:
    def test_render_blocks_to_html(self):
        blocks = [{"type": "text", "content": "<p>hello</p>"}]
        html = render_blocks_to_html(blocks)
        assert isinstance(html, str)

    def test_is_blocks_json_true(self):
        assert is_blocks_json('[{"type": "text"}]') is True

    def test_is_blocks_json_false_for_string(self):
        assert is_blocks_json("<p>plain</p>") is False

    def test_is_blocks_json_false_for_none(self):
        assert is_blocks_json(None) is False


class TestAutomationEngine:
    def test_init(self):
        engine = AutomationEngine()
        assert engine is not None
