"""Add contenido_html column to crm_plantillas_mensaje.

Revision ID: 20260712_0001
Revises: 20260710_0003
Create Date: 2026-07-12
"""

import sqlalchemy as sa

from alembic import op

revision = "20260712_0001"
down_revision = "20260710_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "crm_plantillas_mensaje",
        sa.Column("contenido_html", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("crm_plantillas_mensaje", "contenido_html")
