"""add_deleted_at_to_cms_pages

M-03 (errorescms.md): alinea el soft-delete de CmsPage con el patron de
CmsSection (H-04).  ``delete_cms_page`` ahora fija ``deleted_at`` ademas
de ``status="archived"`` para que las queries que filtren por
``deleted_at.is_(None)`` (patron ya usado por sections en
cms_v2.py:1181,1196,1205) tambien capturen las paginas archivadas.

Las queries existentes que filtran pages por ``status != "archived"``
no se ven afectadas — ``deleted_at`` es una capa semantica adicional.

Revision ID: 20260723_0003
Revises: 20260723_0002_cms_sites_sede_ondelete_restrict
Create Date: 2026-07-23 20:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260723_0003"
down_revision: Union[str, None] = "20260723_0002_cms_sites_sede_ondelete_restrict"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # CmsPage.deleted_at (M-03): nullable=True, index para queries futuras
    # que filtren por deleted_at.is_(None).
    op.add_column(
        "cms_pages",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_cms_pages_deleted_at",
        "cms_pages",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_cms_pages_deleted_at", table_name="cms_pages")
    op.drop_column("cms_pages", "deleted_at")
