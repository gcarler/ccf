"""Normalize agent_knowledge_base.source_id to text.

This allows the KB indexer to store integer-backed sources and UUID-backed
sources in the same column without PostgreSQL type-cast failures.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260614_kb_source_id_text"
down_revision = "20260613_academy_public_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "agent_knowledge_base",
        "source_id",
        existing_type=sa.Integer(),
        type_=sa.String(length=120),
        postgresql_using="source_id::text",
    )


def downgrade() -> None:
    op.alter_column(
        "agent_knowledge_base",
        "source_id",
        existing_type=sa.String(length=120),
        type_=sa.Integer(),
        postgresql_using=(
            "CASE "
            "WHEN source_id ~ '^[0-9]+$' THEN source_id::integer "
            "ELSE NULL "
            "END"
        ),
    )
