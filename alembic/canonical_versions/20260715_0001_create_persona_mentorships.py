"""Create persona mentorships table.

Revision ID: 20260715_0001
Revises: 20260714_0001
Create Date: 2026-07-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260715_0001"
down_revision: Union[str, None] = "20260714_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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


def upgrade() -> None:
    if _table_exists("persona_mentorships"):
        return

    uuid_t = _uuid_type()
    uuid_default = _uuid_default()

    op.create_table(
        "persona_mentorships",
        sa.Column("id", uuid_t, primary_key=True, nullable=False, server_default=uuid_default),
        sa.Column("sede_id", uuid_t, sa.ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("mentee_persona_id", uuid_t, sa.ForeignKey("personas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mentor_persona_id", uuid_t, sa.ForeignKey("personas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assigned_by_user_id", uuid_t, sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'active'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_persona_mentorships_sede_id", "persona_mentorships", ["sede_id"])
    op.create_index("ix_persona_mentorships_mentee_persona_id", "persona_mentorships", ["mentee_persona_id"])
    op.create_index("ix_persona_mentorships_mentor_persona_id", "persona_mentorships", ["mentor_persona_id"])
    op.create_index("ix_persona_mentorships_assigned_by_user_id", "persona_mentorships", ["assigned_by_user_id"])
    op.create_index("ix_persona_mentorships_status", "persona_mentorships", ["status"])
    op.create_index("ix_persona_mentorships_started_at", "persona_mentorships", ["started_at"])
    op.create_index("ix_persona_mentorships_ended_at", "persona_mentorships", ["ended_at"])
    op.create_index("ix_persona_mentorships_deleted_at", "persona_mentorships", ["deleted_at"])


def downgrade() -> None:
    if not _table_exists("persona_mentorships"):
        return

    op.drop_table("persona_mentorships")
