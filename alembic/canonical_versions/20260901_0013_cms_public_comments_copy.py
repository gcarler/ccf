"""Publish public comments UI copy in the global CMS configuration."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260901_0013"
down_revision: Union[str, None] = "20260901_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE cms_sections s
        SET props_json = (s.props_json::jsonb || '{
          "public_ui": {
            "comments": {
              "title":"Comentarios",
              "form_title":"Deja un comentario",
              "name_label":"Nombre",
              "name_placeholder":"Tu nombre",
              "email_label":"Correo Electrónico",
              "email_placeholder":"tu@email.com",
              "comment_label":"Comentario",
              "comment_placeholder":"Escribe tu comentario aquí...",
              "submit_label":"Enviar Comentario",
              "empty_label":"No hay comentarios aprobados aún. ¡Sé el primero en comentar!",
              "reply_label":"Responder",
              "reply_title_template":"Responder a {author}",
              "reply_name_placeholder":"Tu nombre",
              "reply_email_placeholder":"Tu correo",
              "reply_content_placeholder":"Escribe tu respuesta...",
              "cancel_label":"Cancelar",
              "reply_submit_label":"Enviar Respuesta",
              "required_error":"Por favor completa todos los campos.",
              "comment_success":"Comentario enviado con éxito. Pendiente de moderación.",
              "comment_error":"Error al enviar el comentario.",
              "reply_required_error":"Por favor completa todos los campos para responder.",
              "reply_success":"Respuesta enviada con éxito. Pendiente de moderación.",
              "reply_error":"Error al enviar la respuesta."
            }
          }
        }'::jsonb)::json, updated_at=CURRENT_TIMESTAMP
        FROM cms_pages p JOIN cms_sites st ON st.id=p.site_id
        WHERE p.id=s.page_id AND st.site_key='ccf' AND p.slug='footer' AND s.type='footer_config'
    """)


def downgrade() -> None:
    pass
