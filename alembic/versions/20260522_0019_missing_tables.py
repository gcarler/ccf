"""create missing operational tables

Revision ID: 20260522_0019
Revises: 20260519_0018_cms_theme_status
Create Date: 2026-05-22

Creates 7 tables that were previously only managed by
_run_startup_migrations() / Base.metadata.create_all():
- announcements
- testimonials
- support_tickets
- spiritual_milestones
- community_board_cards
- funds
- member_roles
"""

import sqlalchemy as sa

from alembic import op

revision = "20260522_0019"
down_revision = "20260519_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # announcements — skip if table already exists (created by Base.metadata.create_all)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "announcements" not in existing_tables:
        op.create_table(
            "announcements",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("content", sa.Text, nullable=False),
            sa.Column("category", sa.String(100), server_default="General"),
            sa.Column("image_url", sa.String(500), nullable=True),
            sa.Column("is_featured", sa.Boolean, server_default=sa.false()),
            sa.Column("published_at", sa.DateTime, nullable=True),
            sa.Column("created_at", sa.DateTime, nullable=True),
            sa.Column("status", sa.String(20), server_default="draft"),
        )
        op.create_index("ix_announcements_category", "announcements", ["category"])
        op.create_index("ix_announcements_status", "announcements", ["status"])

    if "testimonials" not in existing_tables:
        op.create_table(
            "testimonials",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("content", sa.Text, nullable=False),
            sa.Column("emotion", sa.String(50), server_default="Gratitud"),
            sa.Column("media_type", sa.String(30), server_default="text"),
            sa.Column("media_url", sa.String(500), nullable=True),
            sa.Column("image_url", sa.String(500), nullable=True),
            sa.Column("video_url", sa.String(500), nullable=True),
            sa.Column("podcast_url", sa.String(500), nullable=True),
            sa.Column("is_approved", sa.Boolean, server_default=sa.false()),
            sa.Column("show_on_home", sa.Boolean, server_default=sa.false()),
            sa.Column("author_id", sa.Integer, nullable=True),
            sa.Column("created_at", sa.DateTime, nullable=True),
            sa.Column("status", sa.String(20), server_default="pending"),
            sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        )
        op.create_index("ix_testimonials_author_id", "testimonials", ["author_id"])
        op.create_index("ix_testimonials_status", "testimonials", ["status"])

    if "support_tickets" not in existing_tables:
        op.create_table(
            "support_tickets",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer, nullable=False),
            sa.Column("subject", sa.String(200), nullable=False),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("status", sa.String(20), server_default="open"),
            sa.Column("created_at", sa.DateTime, nullable=True),
            sa.Column("updated_at", sa.DateTime, nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        )
        op.create_index("ix_support_tickets_user_id", "support_tickets", ["user_id"])
        op.create_index("ix_support_tickets_status", "support_tickets", ["status"])
        op.create_index(
            "ix_support_tickets_created_at", "support_tickets", ["created_at"]
        )

    if "spiritual_milestones" not in existing_tables:
        op.create_table(
            "spiritual_milestones",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("person_id", sa.Integer, nullable=False),
            sa.Column("type", sa.String(100), nullable=False),
            sa.Column("event_date", sa.Date, nullable=False),
            sa.Column("minister_id", sa.Integer, nullable=True),
            sa.Column("notes", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime, nullable=True),
            sa.ForeignKeyConstraint(["minister_id"], ["users.id"]),
        )
        op.create_index(
            "ix_spiritual_milestones_person_id", "spiritual_milestones", ["person_id"]
        )
        op.create_index(
            "ix_spiritual_milestones_type", "spiritual_milestones", ["type"]
        )
        op.create_index(
            "ix_spiritual_milestones_minister_id",
            "spiritual_milestones",
            ["minister_id"],
        )

    if "community_board_cards" not in existing_tables:
        op.create_table(
            "community_board_cards",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("column_id", sa.String(50), nullable=True),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("body", sa.Text, nullable=True),
            sa.Column("position", sa.Integer, server_default="0"),
            sa.Column("created_at", sa.DateTime, nullable=True),
        )
        op.create_index(
            "ix_community_board_cards_column_id", "community_board_cards", ["column_id"]
        )

    if "funds" not in existing_tables:
        op.create_table(
            "funds",
            sa.Column("fund_id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("is_public", sa.Boolean, server_default=sa.false()),
            sa.Column("current_balance", sa.Float, server_default="0.0"),
            sa.Column("target_amount", sa.Float, nullable=True),
            sa.Column("created_at", sa.DateTime, nullable=True),
        )

    if "member_roles" not in existing_tables:
        op.create_table(
            "member_roles",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("member_id", sa.Integer, nullable=False),
            sa.Column("role_id", sa.Integer, nullable=False),
            sa.Column("created_at", sa.DateTime, nullable=True),
            sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["role_id"], ["role_definitions.id"], ondelete="CASCADE"
            ),
        )
        op.create_index("ix_member_roles_member_id", "member_roles", ["member_id"])
        op.create_index("ix_member_roles_role_id", "member_roles", ["role_id"])


def downgrade() -> None:
    op.drop_table("member_roles", if_exists=True)
    op.drop_table("funds", if_exists=True)
    op.drop_table("community_board_cards", if_exists=True)
    op.drop_table("spiritual_milestones", if_exists=True)
    op.drop_table("support_tickets", if_exists=True)
    op.drop_table("testimonials", if_exists=True)
    op.drop_table("announcements", if_exists=True)
