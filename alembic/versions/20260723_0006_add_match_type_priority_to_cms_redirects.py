"""add_match_type_priority_to_cms_redirects

F-04 (errorescms.md): ``CmsRedirect.from_path`` solo soportaba match exacto.
Ahora soporta 3 ``match_type``: ``exact`` (default, back-compat), ``wildcard``
(glob con ``*``/``?``) y ``regex`` (Python ``re.search``).

Se agregan:
  - ``match_type`` String(20) NOT NULL DEFAULT 'exact' indexado
  - ``priority`` Integer NOT NULL DEFAULT 0

Ambas columnas son aditivas; todos los redirects existentes siguen siendo
``exact`` y ``priority=0`` (sin cambio de comportamiento).

Revision ID: 20260723_0006
Revises: 20260723_0005
Create Date: 2026-07-23 22:15:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260723_0006"
down_revision: Union[str, None] = "20260723_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # F-04: match_type y priority en cms_redirects.
    # NOT NULL con server_default para que los rows existentes conserven
    # el comportamiento exact-match (back-compat).
    op.add_column(
        "cms_redirects",
        sa.Column(
            "match_type",
            sa.String(length=20),
            nullable=False,
            server_default="exact",
        ),
    )
    op.add_column(
        "cms_redirects",
        sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_index(
        "ix_cms_redirects_match_type",
        "cms_redirects",
        ["match_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_cms_redirects_match_type", table_name="cms_redirects")
    op.drop_column("cms_redirects", "priority")
    op.drop_column("cms_redirects", "match_type")
