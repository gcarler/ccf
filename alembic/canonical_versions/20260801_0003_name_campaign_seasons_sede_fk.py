"""Normalize the campaign seasons tenant foreign-key constraint name.

Some databases received ``sede_id`` from the legacy migration before the
canonical migration existed. PostgreSQL then generated
``campaign_seasons_sede_id_fkey``. This repair makes the constraint name
stable without changing data or delete semantics.

This is a monotonic repair migration. Its downgrade is intentionally a
no-op because Alembic cannot tell whether the canonical constraint came from
this repair or from the canonical ``0001`` migration on an already-converged
database. Removing or renaming it during downgrade would silently alter the
schema owned by ``0001``.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260801_0003_name_campaign_seasons_sede_fk"
down_revision: Union[str, None] = "20260801_0002_merge_evangelism_and_projects_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CANONICAL_FK = "fk_campaign_seasons_sede_id"
# Name produced by Alembic's batch naming convention for an originally
# unnamed SQLite FK. PostgreSQL keeps its historical auto-name separately.
_LEGACY_SQLITE_FK = "fk_campaign_seasons_sede_id_sedes"
_LEGACY_POSTGRES_FK = "campaign_seasons_sede_id_fkey"


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_table(table: str) -> bool:
    return _inspector().has_table(table)


def _has_column(table: str, column: str) -> bool:
    return _has_table(table) and any(item["name"] == column for item in _inspector().get_columns(table))


def _foreign_keys() -> list[dict]:
    return [
        fk
        for fk in _inspector().get_foreign_keys("campaign_seasons")
        if fk.get("referred_table") == "sedes"
        and fk.get("constrained_columns") == ["sede_id"]
    ]


def upgrade() -> None:
    if not _has_column("campaign_seasons", "sede_id"):
        return

    foreign_keys = _foreign_keys()
    # This is a repair/rename migration, not the migration that introduces
    # tenant scoping. Preserve databases that intentionally have no FK.
    if not foreign_keys or any(fk.get("name") == _CANONICAL_FK for fk in foreign_keys):
        return

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "campaign_seasons",
            naming_convention={"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"},
        ) as batch_op:
            for fk in foreign_keys:
                constraint_name = fk.get("name") or _LEGACY_SQLITE_FK
                batch_op.drop_constraint(constraint_name, type_="foreignkey")
            batch_op.create_foreign_key(
                _CANONICAL_FK,
                "sedes",
                ["sede_id"],
                ["id"],
                ondelete="SET NULL",
            )
        return

    for fk in foreign_keys:
        if fk.get("name"):
            op.drop_constraint(fk["name"], "campaign_seasons", type_="foreignkey")
    op.create_foreign_key(
        _CANONICAL_FK,
        "campaign_seasons",
        "sedes",
        ["sede_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Monotonic repair: do not mutate the constraint on downgrade because
    # its provenance (0001 versus this repair) is not recorded in the schema.
    pass
