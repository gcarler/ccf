"""Drop legacy CMS content tables.

Revision ID: 20260714_0001
Revises: 20260713_0001
Create Date: 2026-07-14
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260714_0001"
down_revision: Union[str, None] = "20260713_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LEGACY_TABLES = [
    "content_publications",
    "page_content_versions",
    "page_contents",
    "content_metrics",
    "media_assets",
]


def _uuid_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.String(length=36)


def _uuid_default() -> sa.sql.elements.TextClause | None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.text("gen_random_uuid()")
    return None


def _table_exists(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


def _has_personas_table() -> bool:
    return _table_exists("personas")


def upgrade() -> None:
    for table in LEGACY_TABLES:
        if _table_exists(table):
            op.drop_table(table)


def downgrade() -> None:
    uuid_t = _uuid_type()
    uuid_default = _uuid_default()

    if not _table_exists("page_contents"):
        op.create_table(
            "page_contents",
            sa.Column("id", uuid_t, primary_key=True, nullable=False, server_default=uuid_default),
            sa.Column("page_key", sa.String(length=120), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=False), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=False), nullable=True),
        )
        op.create_index("ix_page_contents_page_key", "page_contents", ["page_key"], unique=True)

    if not _table_exists("page_content_versions"):
        op.create_table(
            "page_content_versions",
            sa.Column("id", uuid_t, primary_key=True, nullable=False, server_default=uuid_default),
            sa.Column("page_key", sa.String(length=120), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=False), nullable=True),
        )
        op.create_index("ix_page_content_versions_page_key", "page_content_versions", ["page_key"])

    if not _table_exists("content_publications"):
        columns = [
            sa.Column("id", uuid_t, primary_key=True, nullable=False, server_default=uuid_default),
            sa.Column("page_key", sa.String(length=120), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=True),
            sa.Column("publish_at", sa.DateTime(timezone=False), nullable=True),
            sa.Column("expire_at", sa.DateTime(timezone=False), nullable=True),
            sa.Column("last_published_at", sa.DateTime(timezone=False), nullable=True),
            sa.Column("updated_by_persona_id", uuid_t, nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=False), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=False), nullable=True),
        ]
        constraints = []
        if _has_personas_table():
            constraints.append(
                sa.ForeignKeyConstraint(
                    ["updated_by_persona_id"],
                    ["personas.id"],
                    name="content_publications_updated_by_persona_id_fkey",
                )
            )
        op.create_table(
            "content_publications",
            *columns,
            *constraints,
        )
        op.create_index("ix_content_publications_page_key", "content_publications", ["page_key"], unique=True)
        op.create_index("ix_content_publications_status", "content_publications", ["status"])

    if not _table_exists("content_metrics"):
        op.create_table(
            "content_metrics",
            sa.Column("id", uuid_t, primary_key=True, nullable=False, server_default=uuid_default),
            sa.Column("metric_key", sa.String(length=120), nullable=False),
            sa.Column("ref_id", sa.String(length=120), nullable=True),
            sa.Column("value", sa.Integer(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=False), nullable=True),
        )
        op.create_index("ix_content_metrics_metric_key", "content_metrics", ["metric_key"])
        op.create_index("ix_content_metrics_ref_id", "content_metrics", ["ref_id"])

    if not _table_exists("media_assets"):
        op.create_table(
            "media_assets",
            sa.Column("id", uuid_t, primary_key=True, nullable=False, server_default=uuid_default),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("url", sa.String(length=500), nullable=False),
            sa.Column("mime_type", sa.String(length=120), nullable=True),
            sa.Column("size_bytes", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=False), nullable=True),
        )
