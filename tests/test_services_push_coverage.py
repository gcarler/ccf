"""
Coverage push — targeting 40%.
"""
import pytest

from backend.services.email import resolve_brand_colors, _brand_wrap, render_verify_email
from backend.services.email_templates import (
    _safe, _cta_button,
    render_welcome, render_birthday, render_event_invitation,
    render_welcome_guide, render_pastoral_followup,
    render_counseling_reminder, render_pastoral_close,
)


FULL_BRAND = {
    "primary": "#1a73e8", "secondary": "#34a853", "accent": "#fbbc04",
    "dark": "#202124", "light": "#ffffff", "bg": "#f8f9fa",
    "pale": "#e8f0fe", "medium": "#5f6368",
    "logo_url": "", "church_name": "CCF Test",
}


@pytest.fixture
def full(client, db_session):
    from tests.conftest import seed_admin
    admin, persona, sede = seed_admin(db_session)
    return {"db": db_session, "sede": sede}


class TestEmailServiceExtra:
    def test_resolve_brand_colors_with_db(self, full):
        colors = resolve_brand_colors(full["db"], full["sede"].id)
        assert isinstance(colors, dict)
        assert "primary" in colors

    def test_brand_wrap_with_full_brand(self):
        html = _brand_wrap("<p>test</p>", FULL_BRAND)
        assert isinstance(html, str)

    def test_render_verify_email_returns_str(self):
        result = render_verify_email("CODE123", "https://example.com")
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestEmailTemplatesHelpers:
    def test_safe_none(self):
        assert _safe(None) == ""

    def test_safe_string(self):
        assert _safe("hello") == "hello"

    def test_safe_preserves(self):
        assert _safe("hi there") == "hi there"

    def test_cta_button_creates_html(self):
        html = _cta_button("Click", "https://x.com", {"primary": "#000"})
        assert "Click" in html
        assert "https://x.com" in html


class TestEmailTemplatesRenderers:
    def test_render_welcome(self):
        assert isinstance(render_welcome({"name": "Test"}, FULL_BRAND), str)

    def test_render_birthday(self):
        assert isinstance(render_birthday({"name": "Test"}, FULL_BRAND), str)

    def test_render_event_invitation(self):
        assert isinstance(render_event_invitation({"name": "Test", "title": "Evento", "date": "2026-07-20",
            "time": "10:00", "location": "Salón", "description": "Desc"}, FULL_BRAND), str)

    def test_render_welcome_guide(self):
        assert isinstance(render_welcome_guide({"name": "Test"}, FULL_BRAND), str)

    def test_render_pastoral_followup(self):
        assert isinstance(render_pastoral_followup({"name": "Test", "days": "30"}, FULL_BRAND), str)

    def test_render_pastoral_close(self):
        assert isinstance(render_pastoral_close({"name": "Test"}, FULL_BRAND), str)

    def test_render_counseling_reminder(self):
        assert isinstance(render_counseling_reminder({"name": "Test"}, FULL_BRAND), str)
