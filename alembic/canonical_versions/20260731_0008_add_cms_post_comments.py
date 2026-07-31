"""add_cms_post_comments — table for blog post comments (R4)

Revision ID: 20260731_0008_add_cms_post_comments
Revises: 20260731_0007_add_cms_ab_tests
Create Date: 2026-07-31 00:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260731_0008_add_cms_post_comments"
down_revision = "20260731_0007_add_cms_ab_tests"
branch_labels = None
depends_on = None


def _uuid_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.dialects.postgresql.UUID(as_uuid=True)
    return sa.String(length=36)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    uuid_t = _uuid_type()

    if not inspector.has_table("cms_post_comments"):
        op.create_table(
            "cms_post_comments",
            sa.Column("id", uuid_t, primary_key=True),
            sa.Column(
                "post_id",
                uuid_t,
                sa.ForeignKey("cms_posts.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "parent_id",
                uuid_t,
                sa.ForeignKey("cms_post_comments.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column("author_name", sa.String(length=120), nullable=False),
            sa.Column("author_email", sa.String(length=255), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default="pending",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
        )
        op.create_index("ix_cms_post_comments_post_id", "cms_post_comments", ["post_id"])
        op.create_index("ix_cms_post_comments_parent_id", "cms_post_comments", ["parent_id"])
        op.create_index("ix_cms_post_comments_status", "cms_post_comments", ["status"])
        op.create_index("ix_cms_post_comments_created_at", "cms_post_comments", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("cms_post_comments"):
        op.drop_index("ix_cms_post_comments_created_at", table_name="cms_post_comments")
        op.drop_index("ix_cms_post_comments_status", table_name="cms_post_comments")
        op.drop_index("ix_cms_post_comments_parent_id", table_name="cms_post_comments")
        op.drop_index("ix_cms_post_comments_post_id", table_name="cms_post_comments")
        op.drop_table("cms_post_comments")
