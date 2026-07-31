"""add_cms_ab_tests — tables for CMS section A/B testing (R3-BE)

Revision ID: 20260731_0007_add_cms_ab_tests
Revises: 20260730_0006_add_cms_newsletters_subscribers
Create Date: 2026-07-31 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260731_0007_add_cms_ab_tests"
down_revision = "20260730_0006_add_cms_newsletters_subscribers"
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

    if not inspector.has_table("cms_ab_tests"):
        op.create_table(
            "cms_ab_tests",
            sa.Column("id", uuid_t, primary_key=True),
            sa.Column(
                "site_id",
                uuid_t,
                sa.ForeignKey("cms_sites.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "page_id",
                uuid_t,
                sa.ForeignKey("cms_pages.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column(
                "section_a_id",
                uuid_t,
                sa.ForeignKey("cms_sections.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "section_b_id",
                uuid_t,
                sa.ForeignKey("cms_sections.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "traffic_split",
                sa.Float(),
                nullable=False,
                server_default="0.5",
            ),
            sa.Column(
                "status",
                sa.String(length=50),
                nullable=False,
                server_default="active",
            ),
            sa.Column(
                "winner_section_id",
                uuid_t,
                sa.ForeignKey("cms_sections.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )

        op.create_index(
            "ix_cms_ab_tests_site_id",
            "cms_ab_tests",
            ["site_id"],
            unique=False,
        )
        op.create_index(
            "ix_cms_ab_tests_page_id",
            "cms_ab_tests",
            ["page_id"],
            unique=False,
        )
        op.create_index(
            "ix_cms_ab_tests_section_a_id",
            "cms_ab_tests",
            ["section_a_id"],
            unique=False,
        )
        op.create_index(
            "ix_cms_ab_tests_section_b_id",
            "cms_ab_tests",
            ["section_b_id"],
            unique=False,
        )
        op.create_index(
            "ix_cms_ab_tests_status",
            "cms_ab_tests",
            ["status"],
            unique=False,
        )
        op.create_index(
            "ix_cms_ab_tests_deleted_at",
            "cms_ab_tests",
            ["deleted_at"],
            unique=False,
        )

    if not inspector.has_table("cms_ab_test_events"):
        op.create_table(
            "cms_ab_test_events",
            sa.Column("id", uuid_t, primary_key=True),
            sa.Column(
                "test_id",
                uuid_t,
                sa.ForeignKey("cms_ab_tests.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("variant", sa.String(length=10), nullable=False),
            sa.Column("event_type", sa.String(length=50), nullable=False),
            sa.Column("visitor_id", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

        op.create_index(
            "ix_cms_ab_test_events_test_id",
            "cms_ab_test_events",
            ["test_id"],
            unique=False,
        )
        op.create_index(
            "ix_cms_ab_test_events_variant",
            "cms_ab_test_events",
            ["variant"],
            unique=False,
        )
        op.create_index(
            "ix_cms_ab_test_events_event_type",
            "cms_ab_test_events",
            ["event_type"],
            unique=False,
        )
        op.create_index(
            "ix_cms_ab_test_events_visitor_id",
            "cms_ab_test_events",
            ["visitor_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("cms_ab_test_events"):
        op.drop_index("ix_cms_ab_test_events_visitor_id", table_name="cms_ab_test_events")
        op.drop_index("ix_cms_ab_test_events_event_type", table_name="cms_ab_test_events")
        op.drop_index("ix_cms_ab_test_events_variant", table_name="cms_ab_test_events")
        op.drop_index("ix_cms_ab_test_events_test_id", table_name="cms_ab_test_events")
        op.drop_table("cms_ab_test_events")

    if inspector.has_table("cms_ab_tests"):
        op.drop_index("ix_cms_ab_tests_deleted_at", table_name="cms_ab_tests")
        op.drop_index("ix_cms_ab_tests_status", table_name="cms_ab_tests")
        op.drop_index("ix_cms_ab_tests_section_b_id", table_name="cms_ab_tests")
        op.drop_index("ix_cms_ab_tests_section_a_id", table_name="cms_ab_tests")
        op.drop_index("ix_cms_ab_tests_page_id", table_name="cms_ab_tests")
        op.drop_index("ix_cms_ab_tests_site_id", table_name="cms_ab_tests")
        op.drop_table("cms_ab_tests")
