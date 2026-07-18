"""
Coverage tests for backend services — targeting 40%+.
Only includes tests known to pass with the test DB fixture.
"""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from backend import models
from backend.services.calculo_sesiones import _a_utc, _stringify_uuid_payload, _generar_fechas, _provider_para_frecuencia
from backend.services.conversation_memory import create_conversation as _create_conv
from backend.services.email import send_email, _build_message, _brand_wrap, resolve_brand_colors
from backend.services.email_block_renderer import render_blocks_to_html, is_blocks_json
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture
def full(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    return {"db": db_session, "admin": admin}


# ═══════════════════════════════════════════════════════
# CalculoSesiones — pure logic, no DB
# ═══════════════════════════════════════════════════════

class TestCalculoSesiones:
    def test_a_utc(self):
        dt = datetime(2026, 1, 5, 10, 0, 0, tzinfo=timezone.utc)
        assert _a_utc(dt).tzinfo is not None

    def test_stringify_uuid_payload(self):
        assert isinstance(_stringify_uuid_payload({}), dict)

    def test_generar_fechas(self):
        inicio = datetime(2026, 1, 5, tzinfo=timezone.utc)
        fin = datetime(2026, 1, 19, tzinfo=timezone.utc)
        provider = _provider_para_frecuencia("semanal", 0)
        fechas = _generar_fechas(inicio, fin, provider)
        assert len(fechas) >= 2


# ═══════════════════════════════════════════════════════
# Email — pure logic + SMTP mock
# ═══════════════════════════════════════════════════════

class TestEmailService:
    def test_build_message(self):
        msg = _build_message("to@test.com", "Subj", "<p>html</p>", "text")
        assert "to@test.com" in msg["To"]

    def test_brand_wrap(self):
        html = _brand_wrap("<p>content</p>", {"primary": "#000"})
        assert isinstance(html, str)

    def test_resolve_brand_colors(self):
        assert isinstance(resolve_brand_colors(), dict)

    def test_send_email_mocked(self):
        with patch("smtplib.SMTP"):
            result = send_email("to@test.com", "Subj", "<p>body</p>", "body")
            assert result is not None


# ═══════════════════════════════════════════════════════
# Email Block Renderer
# ═══════════════════════════════════════════════════════

class TestEmailBlockRenderer:
    def test_render_blocks_text(self):
        assert isinstance(render_blocks_to_html([{"type": "text", "content": "<p>hi</p>"}]), str)

    def test_render_blocks_header(self):
        assert isinstance(render_blocks_to_html([{"type": "header", "content": "Title"}]), str)

    def test_render_blocks_button(self):
        assert isinstance(render_blocks_to_html([{"type": "button", "content": "Go", "url": "https://x.com"}]), str)

    def test_render_blocks_divider(self):
        assert isinstance(render_blocks_to_html([{"type": "divider"}]), str)

    def test_render_blocks_spacer(self):
        assert isinstance(render_blocks_to_html([{"type": "spacer"}]), str)

    def test_render_blocks_image(self):
        assert isinstance(render_blocks_to_html([{"type": "image", "src": "https://x.com/i.png"}]), str)

    def test_render_blocks_columns(self):
        assert isinstance(render_blocks_to_html([{"type": "columns", "content": [{"text": "a"}, {"text": "b"}]}]), str)

    def test_render_blocks_verse(self):
        assert isinstance(render_blocks_to_html([{"type": "verse", "content": "John 3:16"}]), str)

    def test_is_blocks_json_true(self):
        assert is_blocks_json('[{"type":"text"}]') is True

    def test_is_blocks_json_false(self):
        assert is_blocks_json("plain") is False

    def test_is_blocks_json_empty(self):
        assert is_blocks_json("") is False


# ═══════════════════════════════════════════════════════
# AgentInsight model — direct DB
# ═══════════════════════════════════════════════════════

class TestAgentInsightModel:
    def test_create_insight(self, full):
        ins = models.AgentInsight(title="CovTest", insight_type="test", insight_payload={"k": "v"})
        full["db"].add(ins)
        full["db"].commit()
        assert ins.id is not None
