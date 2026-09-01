"""Move public form copy from renderer defaults into CMS content."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260901_0011"
down_revision: Union[str, None] = "20260901_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE cms_sections s
        SET props_json = (s.props_json::jsonb || ' {
          "title":"Hablemos de Tu Caminar",
          "name_label":"Nombre completo",
          "name_placeholder":"Tu nombre",
          "email_label":"Correo electrónico",
          "email_placeholder":"tu@email.com (opcional)",
          "phone_label":"WhatsApp",
          "phone_placeholder":"+57 300...",
          "message_label":"¿En qué podemos ayudarte?",
          "message_placeholder":"Cuéntanos un poco sobre ti...",
          "submit_label":"Enviar mensaje y conectar",
          "success_message":"Gracias. Te contactaremos pronto.",
          "reset_label":"Enviar otro mensaje"
        }'::jsonb)::json
        FROM cms_pages p JOIN cms_sites st ON st.id=p.site_id
        WHERE p.id=s.page_id AND st.site_key='ccf'
          AND p.slug='conocer-a-jesus' AND s.section_key='feed'
          AND s.type='contact_form'
    """)


def downgrade() -> None:
    pass
