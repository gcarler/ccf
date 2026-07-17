"""Add sede_id to crm_automations.

Revision ID: 0001_crm_auto_sede
Revises: 20260716_0001
Create Date: 2026-07-17 00:00:01
"""

from alembic import op
import sqlalchemy as sa

revision = "20260717_0001"
down_revision = "20260716_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "crm_automations",
        sa.Column("sede_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_crm_automations_sede_id",
        "crm_automations",
        ["sede_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_crm_automations_sede_id",
        "crm_automations",
        "sedes",
        ["sede_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_crm_automations_sede_id", "crm_automations", type_="foreignkey")
    op.drop_index("ix_crm_automations_sede_id", "crm_automations")
    op.drop_column("crm_automations", "sede_id")
