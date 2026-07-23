"""add_index_cms_page_versions_created_at

M-05 (errorescms.md): CmsPageVersion.created_at no tenia indice. Las
queries de list_versions ordenan por version_number DESC, pero las
queries de busqueda de versiones recientes podrian beneficiarse de un
indice en created_at para tablas con muchas versiones.

Revision ID: 20260723_0004
Revises: 20260723_0003
Create Date: 2026-07-23 20:45:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260723_0004"
down_revision: Union[str, None] = "20260723_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # M-05: indice en cms_page_versions.created_at para queries de
    # versiones recientes. El modelo ya tenia index=True en page_id y
    # version_number, pero created_at no estaba indexado.
    op.create_index(
        "ix_cms_page_versions_created_at",
        "cms_page_versions",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_cms_page_versions_created_at", table_name="cms_page_versions")
