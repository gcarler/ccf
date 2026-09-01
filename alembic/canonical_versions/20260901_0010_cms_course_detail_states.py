"""Move course detail state copy into the CMS detail template."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260901_0010"
down_revision: Union[str, None] = "20260901_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE cms_sections s SET props_json=(s.props_json::jsonb || '{
          "load_error_title":"No pudimos cargar el curso",
          "load_error_description":"Comprueba tu conexión e inténtalo nuevamente.",
          "not_found_title":"Curso no encontrado",
          "not_found_description":"El curso que buscas ya no está disponible o el enlace es incorrecto."
        }'::jsonb)::json, updated_at=CURRENT_TIMESTAMP
        FROM cms_pages p JOIN cms_sites st ON st.id=p.site_id
        WHERE p.id=s.page_id AND st.site_key='ccf' AND p.slug='courses' AND s.section_key='detail_template'
    """)


def downgrade() -> None:
    pass
