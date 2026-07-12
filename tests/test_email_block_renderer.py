"""Tests para email_block_renderer.py."""
from __future__ import annotations

from backend.services.email import _FALLBACK_BRAND
from backend.services.email_block_renderer import _render_block, is_blocks_json, render_blocks_to_html


class TestIsBlocksJson:
    def test_valid(self):
        assert is_blocks_json('[{"type": "header", "props": {"title": "Test"}}]') is True
    def test_empty(self):
        assert is_blocks_json("[]") is False
    def test_not_json(self):
        assert is_blocks_json("not json") is False
    def test_not_array(self):
        assert is_blocks_json('{"type": "header"}') is False

class TestRenderBlock:
    def test_header(self):
        h = _render_block({"type": "header", "props": {"title": "Hola"}}, _FALLBACK_BRAND)
        assert "Hola" in h and "<h2" in h
    def test_text(self):
        h = _render_block({"type": "text", "props": {"content": "<p>Hola</p>"}}, _FALLBACK_BRAND)
        assert "<p>Hola</p>" in h
    def test_button(self):
        h = _render_block({"type": "button", "props": {"label": "Click", "url": "https://x.com"}}, _FALLBACK_BRAND)
        assert "Click" in h and "<a" in h
    def test_image(self):
        h = _render_block({"type": "image", "props": {"src": "https://img.com/t.jpg"}}, _FALLBACK_BRAND)
        assert "<img" in h
    def test_image_empty(self):
        assert _render_block({"type": "image", "props": {"src": ""}}, _FALLBACK_BRAND) == ""
    def test_divider(self):
        h = _render_block({"type": "divider", "props": {"color": "#FF0000"}}, _FALLBACK_BRAND)
        assert "<hr" in h and "#FF0000" in h
    def test_spacer(self):
        h = _render_block({"type": "spacer", "props": {"height": 48}}, _FALLBACK_BRAND)
        assert "48px" in h
    def test_verse(self):
        h = _render_block({"type": "verse", "props": {"text": "Juan 3:16", "reference": "Juan 3:16"}}, _FALLBACK_BRAND)
        assert "Juan 3:16" in h
    def test_columns(self):
        h = _render_block({"type": "columns", "props": {"count": 3}}, _FALLBACK_BRAND)
        assert "<table" in h
    def test_unknown(self):
        assert _render_block({"type": "unknown", "props": {}}, _FALLBACK_BRAND) == ""

class TestRenderBlocksToHtml:
    def test_produces_html(self):
        html = render_blocks_to_html([{"type": "header", "props": {"title": "T"}}, {"type": "text", "props": {"content": "X"}}])
        assert html.startswith("<!DOCTYPE html>") and "T" in html
    def test_empty(self):
        assert render_blocks_to_html([]).startswith("<!DOCTYPE html>")
    def test_custom_brand(self):
        html = render_blocks_to_html([{"type": "header", "props": {"title": "T"}}], {"primary": "#FF0000", "dark": "#333", "medium": "#666", "pale": "#EEE", "church_name": "Iglesia", "logo_url": ""})
        assert "#FF0000" in html and "Iglesia" in html
