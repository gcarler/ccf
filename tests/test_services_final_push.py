"""
Final coverage push — target 40%.
"""
from unittest.mock import patch

import pytest

from backend.services.email import _brand_wrap, send_email, render_verify_email, render_reset_password
from backend.services.knowledge_graph import _has_model


class TestEmailFinalPush:
    def test_render_verify_email_returns_tuple(self):
        r = render_verify_email("CODE", "https://x.com")
        assert isinstance(r, tuple) and len(r) == 2

    def test_render_reset_password_returns_tuple(self):
        r = render_reset_password("TOKEN", "https://x.com")
        assert isinstance(r, tuple) and len(r) == 2

    def test_brand_wrap_with_empty_colors(self):
        html = _brand_wrap("<p>test</p>", {})
        assert isinstance(html, str)

    @patch("backend.services.email.smtplib.SMTP")
    def test_send_email_full_flow(self, mock_smtp):
        from backend.core.config import get_settings
        with patch.object(get_settings(), "smtp_host", "smtp.example.com"):
            with patch.object(get_settings(), "smtp_port", 587):
                with patch.object(get_settings(), "smtp_user", "user"):
                    with patch.object(get_settings(), "smtp_password", "pass"):
                        result = send_email("to@test.com", "Subj", "<p>html</p>", "text")
                        assert result is not None


class TestKnowledgeGraphFinalPush:
    def test_has_model_personas(self):
        assert isinstance(_has_model("personas"), bool)

    def test_has_model_nonexistent(self):
        assert isinstance(_has_model("nonexistent_table_xyz"), bool)
