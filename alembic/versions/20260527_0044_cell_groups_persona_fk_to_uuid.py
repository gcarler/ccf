"""0044_cell_groups_persona_fk_to_uuid

Revision ID: 20260527_0044
Revises: 8fade299a6f0
Create Date: 2026-05-27

Converts cell_groups.leader_persona_id, assistant_persona_id, host_persona_id
from INTEGER to UUID to match the Persona model (UUID PK).
Existing integer values are legacy member IDs with no valid persona UUID mapping,
so they are cleared (set to NULL) during the migration.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260527_0044"
down_revision: Union[str, None] = "8fade299a6f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Drop existing FK constraints if any
    for fk in ["fk_cell_groups_leader", "fk_cell_groups_assistant", "fk_cell_groups_host"]:
        conn.execute(sa.text(f"ALTER TABLE cell_groups DROP CONSTRAINT IF EXISTS {fk}"))

    # Drop indexes that depend on these columns
    for idx in [
        "ix_cell_groups_leader_persona_id",
        "ix_cell_groups_assistant_persona_id",
        "ix_cell_groups_host_persona_id",
    ]:
        conn.execute(sa.text(f"DROP INDEX IF EXISTS {idx}"))

    # Alter column types: INTEGER → UUID (existing integer values become NULL)
    for col in ["leader_persona_id", "assistant_persona_id", "host_persona_id"]:
        conn.execute(sa.text(
            f"ALTER TABLE cell_groups ALTER COLUMN {col} DROP DEFAULT"
        ))
        conn.execute(sa.text(
            f"UPDATE cell_groups SET {col} = NULL"
        ))
        conn.execute(sa.text(
            f"ALTER TABLE cell_groups ALTER COLUMN {col} TYPE UUID "
            f"USING NULL"
        ))
        # Re-add FK constraint
        persona_fk = col.replace("_id", "")
        conn.execute(sa.text(
            f"ALTER TABLE cell_groups ADD CONSTRAINT fk_cell_groups_{persona_fk} "
            f"FOREIGN KEY ({col}) REFERENCES personas(id) ON DELETE SET NULL"
        ))


def downgrade() -> None:
    pass
