"""Tests exhaustivos y estructurales para backend/services/crm_resource_bank.py (100% Cobertura)."""

from backend.services.crm_resource_bank import (
    SYSTEM_CATEGORIES,
    SYSTEM_TEMPLATES,
    find_system_category,
    find_system_template,
    find_system_templates_by_category,
    get_system_categories,
    get_system_templates,
    system_template_id,
)


class TestCrmResourceBank100Pct:
    def test_get_system_categories(self):
        cats = get_system_categories()
        assert isinstance(cats, list)
        assert len(cats) == len(SYSTEM_CATEGORIES)
        first = cats[0]
        assert "nombre" in first
        assert "descripcion" in first
        assert "color_ui_hex" in first

    def test_get_system_templates(self):
        tpls = get_system_templates()
        assert isinstance(tpls, list)
        assert len(tpls) == len(SYSTEM_TEMPLATES)
        first = tpls[0]
        assert "id" in first
        assert "categoria" in first
        assert "titulo" in first
        assert "canal" in first

    def test_find_system_category(self):
        existing_cat_name = SYSTEM_CATEGORIES[0].nombre
        found = find_system_category(existing_cat_name)
        assert found is not None
        assert found.nombre == existing_cat_name

        notFound = find_system_category("Categoría Inexistente 999")
        assert notFound is None

    def test_system_template_id_and_find_template(self):
        first_tpl = SYSTEM_TEMPLATES[0]
        tpl_id = system_template_id(first_tpl)
        assert isinstance(tpl_id, str)
        assert len(tpl_id) > 0

        found = find_system_template(tpl_id)
        assert found is not None
        assert found.titulo == first_tpl.titulo

        notFound = find_system_template("id-plantilla-inexistente-12345")
        assert notFound is None

    def test_find_system_templates_by_category(self):
        cat_name = SYSTEM_CATEGORIES[0].nombre
        matched = find_system_templates_by_category(cat_name)
        assert isinstance(matched, list)

        none_matched = find_system_templates_by_category("Categoría Fake")
        assert len(none_matched) == 0
