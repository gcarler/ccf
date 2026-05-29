"""0051_rename_member_id_to_persona_id

Revision ID: 20260528_0051
Revises: 20260528_0050
Create Date: 2026-05-28

Renombra member_id → persona_id (y leader_id → leader_persona_id) en 6 tablas
cuyos modelos ORM ya usan los nombres nuevos pero la BD conserva los antiguos.

Tablas afectadas:
  donations.member_id          → persona_id
  crm_tasks.member_id          → persona_id
  volunteer_shifts.member_id   → persona_id
  ministries.leader_id         → leader_persona_id
  member_ministries.member_id  → persona_id
  member_volunteer_skills.member_id → persona_id

Las FK constraints y relaciones ORM funcionarán sin cambios adicionales porque
PostgreSQL actualiza el constraint automáticamente al renombrar la columna.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260528_0051"
down_revision: Union[str, None] = "20260528_0050"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col_exists(table: str, col: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT count(*) FROM information_schema.columns "
        "WHERE table_name=:t AND column_name=:c AND table_schema='public'"
    ), {"t": table, "c": col})
    return r.scalar() > 0


def upgrade() -> None:
    conn = op.get_bind()
    renames = [
        ("donations",              "member_id",  "persona_id"),
        ("crm_tasks",              "member_id",  "persona_id"),
        ("volunteer_shifts",       "member_id",  "persona_id"),
        ("ministries",             "leader_id",  "leader_persona_id"),
        ("member_ministries",      "member_id",  "persona_id"),
        ("member_volunteer_skills","member_id",  "persona_id"),
    ]
    for table, old_col, new_col in renames:
        if _col_exists(table, old_col) and not _col_exists(table, new_col):
            conn.execute(sa.text(
                f"ALTER TABLE {table} RENAME COLUMN {old_col} TO {new_col}"
            ))


def downgrade() -> None:
    conn = op.get_bind()
    renames = [
        ("donations",              "persona_id",  "member_id"),
        ("crm_tasks",              "persona_id",  "member_id"),
        ("volunteer_shifts",       "persona_id",  "member_id"),
        ("ministries",             "leader_persona_id", "leader_id"),
        ("member_ministries",      "persona_id",  "member_id"),
        ("member_volunteer_skills","persona_id",  "member_id"),
    ]
    for table, old_col, new_col in renames:
        if _col_exists(table, old_col) and not _col_exists(table, new_col):
            conn.execute(sa.text(
                f"ALTER TABLE {table} RENAME COLUMN {old_col} TO {new_col}"
            ))
