"""Add tags and origen columns to members table.

Revision ID: 20260527_0036_member_tags_origen
Revises: 20260526_0034_kernel_identity
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260527_0036_member_tags_origen"
down_revision = "20260526_0034_kernel_identity"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("members", sa.Column("tags", postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column("members", sa.Column("origen_estrategia_id", sa.Integer(), nullable=True))
    op.add_column("members", sa.Column("origen_grupo_id", sa.Integer(), nullable=True))
    op.add_column("members", sa.Column("origen_fecha", sa.DateTime(), nullable=True))

    op.create_foreign_key(
        "fk_members_origen_estrategia",
        "members", "evangelism_strategies",
        ["origen_estrategia_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_members_origen_grupo",
        "members", "grupos_evangelismo",
        ["origen_grupo_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_members_origen_estrategia_id", "members", ["origen_estrategia_id"])
    op.create_index("ix_members_origen_grupo_id", "members", ["origen_grupo_id"])


def downgrade():
    op.drop_index("ix_members_origen_grupo_id", table_name="members")
    op.drop_index("ix_members_origen_estrategia_id", table_name="members")
    op.drop_constraint("fk_members_origen_grupo", "members", type_="foreignkey")
    op.drop_constraint("fk_members_origen_estrategia", "members", type_="foreignkey")
    op.drop_column("members", "origen_fecha")
    op.drop_column("members", "origen_grupo_id")
    op.drop_column("members", "origen_estrategia_id")
    op.drop_column("members", "tags")
