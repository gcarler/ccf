"""0050_consolidation_multitenant_fix

Revision ID: 20260528_0050
Revises: 20260528_0049
Create Date: 2026-05-28

Tres correcciones en el módulo de consolidación:

A) Renombra communication_logs.member_id → persona_id
   (el ORM ya usa persona_id desde hace varias versiones; la BD nunca se actualizó)

B) Añade sede_id a consolidation_cases para filtro multi-tenant

C) Añade deleted_at a consolidation_cases para soft delete
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260528_0050"
down_revision: Union[str, None] = "20260528_0049"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col_exists(table: str, col: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT count(*) FROM information_schema.columns "
        "WHERE table_name=:t AND column_name=:c"
    ), {"t": table, "c": col})
    return r.scalar() > 0


def upgrade() -> None:
    conn = op.get_bind()

    # A) Renombrar member_id → persona_id en communication_logs
    if _col_exists("communication_logs", "member_id") and not _col_exists("communication_logs", "persona_id"):
        conn.execute(sa.text(
            "ALTER TABLE communication_logs RENAME COLUMN member_id TO persona_id"
        ))

    # B) sede_id en consolidation_cases
    if not _col_exists("consolidation_cases", "sede_id"):
        op.add_column(
            "consolidation_cases",
            sa.Column("sede_id", sa.Integer(),
                      sa.ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_consolidation_cases_sede_id", "consolidation_cases", ["sede_id"])

    # C) deleted_at en consolidation_cases
    if not _col_exists("consolidation_cases", "deleted_at"):
        op.add_column(
            "consolidation_cases",
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
        )
        op.create_index(
            "ix_consolidation_cases_active",
            "consolidation_cases",
            ["deleted_at"],
            postgresql_where=sa.text("deleted_at IS NULL"),
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _col_exists("consolidation_cases", "deleted_at"):
        op.drop_index("ix_consolidation_cases_active", table_name="consolidation_cases")
        op.drop_column("consolidation_cases", "deleted_at")

    if _col_exists("consolidation_cases", "sede_id"):
        op.drop_index("ix_consolidation_cases_sede_id", table_name="consolidation_cases")
        op.drop_column("consolidation_cases", "sede_id")

    if _col_exists("communication_logs", "persona_id") and not _col_exists("communication_logs", "member_id"):
        conn.execute(sa.text(
            "ALTER TABLE communication_logs RENAME COLUMN persona_id TO member_id"
        ))
