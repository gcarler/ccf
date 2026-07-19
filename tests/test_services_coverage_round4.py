"""
Coverage for automation_engine, knowledge_base, email, conversation_memory.
"""
from unittest.mock import patch, MagicMock

import pytest

from backend.services.automation_engine import AutomationEngine
from backend.services.email import send_email, _build_message, _brand_wrap, resolve_brand_colors
from backend.services.email_templates import _safe, _cta_button
from backend.services.email_block_renderer import is_blocks_json, render_blocks_to_html


class TestAutomationEngineCoverage:
    def setup_method(self):
        AutomationEngine._instance = None
        AutomationEngine._thread = None

    def test_singleton(self):
        e1 = AutomationEngine()
        e2 = AutomationEngine()
        assert e1 is e2

    def test_start_stop(self):
        engine = AutomationEngine()
        with patch.object(engine, '_run_loop', return_value=None):
            engine.start()
            assert engine._thread is not None
            engine.stop()
            assert engine._thread is None

    def test_double_start(self):
        engine = AutomationEngine()
        with patch.object(engine, '_run_loop', return_value=None):
            engine.start()
            engine.start()
            assert engine._thread is not None
            engine.stop()

    def test_double_stop(self):
        engine = AutomationEngine()
        with patch.object(engine, '_run_loop', return_value=None):
            engine.start()
            engine.stop()
            engine.stop()
            assert engine._thread is None


class TestEmailCoverage:
    def test_build_message_with_all_params(self):
        msg = _build_message("to@test.com", "Subject", "<p>HTML</p>", "Text")
        assert "to@test.com" in msg["To"]
        assert "Subject" in msg["Subject"]

    def test_brand_wrap_no_brand(self):
        html = _brand_wrap("<p>test</p>", {})
        assert isinstance(html, str)

    def test_brand_wrap_with_full_brand(self):
        brand = {"primary": "#000", "dark": "#111", "light": "#fff", "bg": "#f0f0f0"}
        html = _brand_wrap("<p>test</p>", brand)
        assert isinstance(html, str)

    def test_resolve_brand_colors_return_dict(self):
        colors = resolve_brand_colors()
        assert isinstance(colors, dict)

    @patch("backend.services.email.smtplib.SMTP")
    def test_send_email_with_mocked_smtp(self, mock_smtp):
        from backend.core.config import get_settings
        with patch.object(get_settings(), "smtp_host", "smtp.test.com"):
            with patch.object(get_settings(), "smtp_port", 587):
                with patch.object(get_settings(), "smtp_user", "user"):
                    with patch.object(get_settings(), "smtp_password", "pass"):
                        result = send_email("to@test.com", "Subj", "<p>html</p>", "text")
                        assert result is True


class TestEmailBlockRendererExtra:
    def test_render_blocks_empty(self):
        result = render_blocks_to_html([])
        assert isinstance(result, str)
        assert "CCF" in result or result == ""

    def test_render_blocks_unknown_type(self):
        result = render_blocks_to_html([{"type": "unknown", "content": "test"}])
        assert isinstance(result, str)

    def test_is_blocks_json_edge_cases(self):
        assert is_blocks_json("[]") is False  # Empty list
        assert is_blocks_json("[{}]") is False  # No type key
        assert is_blocks_json(None) is False
        assert is_blocks_json("not json") is False


class TestEmailTemplatesExtra2:
    def test_safe_various_inputs(self):
        assert _safe(None) == ""
        assert _safe("") == ""
        assert _safe("hello") == "hello"
        assert _safe("  spaces  ") == "  spaces  "

    def test_cta_button_minimal(self):
        html = _cta_button("Click", "https://x.com", {"primary": "#000"})
        assert "Click" in html
        assert "#000" in html
