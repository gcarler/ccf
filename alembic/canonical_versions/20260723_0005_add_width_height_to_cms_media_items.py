"""add_width_height_to_cms_media_items

F-03 (errorescms.md): ``CmsMediaItem`` no tenia campos ``width`` y
``height`` individuales — solo ``dimensions`` como string ``"WxH"``.
Las queries que querian filtrar por dimension / aspect-ratio tenian
que parsear el string, lo cual es fragil y no indexable.

Se agregan dos columnas ``Integer nullable=True`` para ancho y alto.
La columna ``dimensions`` (string) se mantiene por compatibilidad
hacia atras (frontend, seeds, logs) — no se elimina.

El endpoint ``upload_cms_media`` y ``optimize_cms_media`` ya obtienen
``width`` y ``height`` de ``ImageOptimizer.optimize()``; con este
cambio se persisten ambos campos ademas de ``dimensions``.

Revision ID: 20260723_0005
Revises: 20260723_0004
Create Date: 2026-07-23 21:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260723_0005"
down_revision: Union[str, None] = "20260723_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # F-03: columnas width/height Integer para cms_media_items.
    # Nullable=True: media existente y non-image (pdf, mp4) no tienen
    # dimensiones de pixel; la columna se popula solo en upload/optimize
    # de imagenes.
    op.add_column(
        "cms_media_items",
        sa.Column("width", sa.Integer(), nullable=True),
    )
    op.add_column(
        "cms_media_items",
        sa.Column("height", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cms_media_items", "height")
    op.drop_column("cms_media_items", "width")
