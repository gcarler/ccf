"""Publish transversal public UI copy from the global footer CMS page."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260901_0012"
down_revision: Union[str, None] = "20260901_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE cms_sections s
        SET props_json = (s.props_json::jsonb || '{
          "public_ui": {
            "search": {
              "categories": ["General", "Noticias", "Eventos", "Recursos"],
              "tags": ["anuncio", "tutorial", "iglesia", "comunidad"],
              "placeholder": "Buscar en el sitio... (p.ej. noticias, eventos)",
              "clear_label": "Limpiar búsqueda",
              "close_label": "Esc",
              "category_label": "Categoría:",
              "tags_label": "Etiquetas:",
              "loading_label": "Buscando resultados...",
              "empty_title": "No se encontraron resultados",
              "empty_description": "Intenta con otros términos o elimina los filtros aplicados.",
              "promoted_label": "Resultados Destacados",
              "promoted_badge": "Promocionado",
              "results_label": "Resultados",
              "shortcut_prefix": "Usa",
              "shortcut_suffix": "para abrir o cerrar",
              "product_label": "Búsqueda CMS 2.0"
            }
          }
        }'::jsonb)::json, updated_at=CURRENT_TIMESTAMP
        FROM cms_pages p JOIN cms_sites st ON st.id=p.site_id
        WHERE p.id=s.page_id AND st.site_key='ccf' AND p.slug='footer' AND s.type='footer_config'
    """)


def downgrade() -> None:
    pass
