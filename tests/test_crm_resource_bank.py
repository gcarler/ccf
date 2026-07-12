"""Tests para crm_resource_bank.py — templates HTML y copy mejorado."""
from __future__ import annotations

from backend.services.crm_resource_bank import (
    SYSTEM_CATEGORIES,
    SYSTEM_TEMPLATES,
    find_system_template,
    get_system_categories,
    get_system_templates,
    system_template_id,
)
from backend.services.email_templates import _RENDERERS


class TestSystemCategories:
    def test_count(self):
        assert len(SYSTEM_CATEGORIES) == 8
    def test_serializable(self):
        cats = get_system_categories()
        assert len(cats) == 8 and all("nombre" in c for c in cats)

class TestSystemTemplates:
    def test_count(self):
        assert len(SYSTEM_TEMPLATES) >= 30
    def test_all_have_fields(self):
        for t in SYSTEM_TEMPLATES:
            assert t.categoria and t.titulo and t.canal in ("WHATSAPP", "EMAIL", "SMS") and t.contenido_texto
    def test_email_have_subject(self):
        for t in SYSTEM_TEMPLATES:
            if t.canal == "EMAIL":
                assert t.asunto
    def test_html_have_type(self):
        html = [t for t in SYSTEM_TEMPLATES if t.html_template_type]
        assert len(html) >= 5
    def test_serializable(self):
        ts = get_system_templates()
        assert len(ts) >= 30 and all("contenido_html" in t for t in ts)

class TestFindTemplate:
    def test_finds(self):
        t = SYSTEM_TEMPLATES[0]
        assert find_system_template(system_template_id(t)) is not None
    def test_unknown(self):
        assert find_system_template("nonexistent") is None

class TestCopyMejorado:
    def test_all_renderer_types_have_renderer(self):
        for t in SYSTEM_TEMPLATES:
            if t.html_template_type:
                assert t.html_template_type in _RENDERERS
