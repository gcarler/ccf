"""Align Dimension B kernel role PKs to UUID.

``persona_church_roles.id``, ``persona_role_history.id`` and
``persona_role_history.changed_by`` remained INTEGER (serial) in databases
that were migrated before the kernel moved to UUID identity, while the ORM
models (``PersonaRoleAssignment`` / ``PersonaRoleHistory``) generate UUID
primary keys. Any write to Dimension B (``set_persona_church_role`` via
``PUT /api/kernel/church-role/{persona_id}``) fails with

    ProgrammingError: column "id" is of type integer but expression is of
    type uuid

Both tables are empty in the target database, so the type change carries no
data migration. On databases where rows already exist the migration is
skipped with a documented warning: rewriting PKs with ``gen_random_uuid()``
would silently change identifiers and must be handled as a deliberate data
migration instead.

Revision ID: 20260810_0002_kernel_roles_uuid_pk
Revises: 20260810_0001_academy_forum_threads_deleted_at
Create Date: 2026-08-10
"""

from __future__ import annotations

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

log = logging.getLogger("alembic.runtime.migration")

# revision identifiers, used by Alembic.
revision: str = "20260810_0002_kernel_roles_uuid_pk"
down_revision: Union[str, None] = "20260810_0001_academy_forum_threads_deleted_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_table(table: str) -> bool:
    return table in set(_inspector().get_table_names())


def _has_column(table: str, column: str) -> bool:
    return _has_table(table) and any(item["name"] == column for item in _inspector().get_columns(table))


def _has_rows(table: str) -> bool:
    bind = op.get_bind()
    row = bind.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first()
    return row is not None


def _drop_serial_default(table: str, column: str) -> None:
    """Detach the legacy ``nextval(...)`` default before changing the type.

    The sequence object itself is intentionally kept: ``downgrade()`` can
    re-attach it, and dropping it is unnecessary work.
    """
    op.execute(sa.text(f"ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT"))


def _promote_to_uuid(table: str, column: str, *, require_empty: bool) -> None:
    """Convert an INTEGER column to UUID in place.

    ``gen_random_uuid()`` is a PostgreSQL 13+ builtin (no extension needed);
    with zero rows the USING expression is never evaluated. When the table
    already contains rows and ``require_empty`` is set the change is skipped
    so identifiers are never silently rewritten.
    """
    if require_empty and _has_rows(table):
        log.warning(
            "Skipping %s.%s -> UUID: table has rows; a deliberate data migration is required.",
            table,
            column,
        )
        return
    op.alter_column(table, column, type_=postgresql.UUID(as_uuid=True), postgresql_using="gen_random_uuid()")


def upgrade() -> None:
    if _has_column("persona_church_roles", "id"):
        _drop_serial_default("persona_church_roles", "id")
        _promote_to_uuid("persona_church_roles", "id", require_empty=True)

    if _has_column("persona_role_history", "id"):
        _drop_serial_default("persona_role_history", "id")
        _promote_to_uuid("persona_role_history", "id", require_empty=True)

    if _has_column("persona_role_history", "changed_by"):
        # Nullable FK target column without a DB-level FK. Existing INTEGER
        # values (if any) are already dangling — personas.id is UUID — so a
        # fresh UUID per row is no worse than the legacy value; NULLs stay NULL.
        _promote_to_uuid("persona_role_history", "changed_by", require_empty=False)


def downgrade() -> None:
    """Restore the legacy INTEGER (serial) layout.

    Only executed when the tables are empty: mapping UUID identifiers back to
    INTEGER on a data-bearing table is not meaningful and is deliberately
    skipped.
    """
    # UUID -> INTEGER has no implicit cast in PostgreSQL, so a USING
    # expression is required. The tables are guaranteed empty at this point
    # (guarded by _has_rows above), therefore the literal "0" is never
    # actually evaluated.
    _USING_ZERO = "0"

    if _has_column("persona_church_roles", "id"):
        if _has_rows("persona_church_roles"):
            log.warning("Skipping downgrade of persona_church_roles.id: table has rows.")
        else:
            op.alter_column("persona_church_roles", "id", type_=sa.Integer(), postgresql_using=_USING_ZERO)
            op.execute(sa.text("ALTER TABLE persona_church_roles ALTER COLUMN id SET DEFAULT nextval('persona_church_roles_id_seq')"))

    if _has_column("persona_role_history", "id"):
        if _has_rows("persona_role_history"):
            log.warning("Skipping downgrade of persona_role_history.id: table has rows.")
        else:
            op.alter_column("persona_role_history", "id", type_=sa.Integer(), postgresql_using=_USING_ZERO)
            op.execute(sa.text("ALTER TABLE persona_role_history ALTER COLUMN id SET DEFAULT nextval('persona_role_history_id_seq')"))

    if _has_column("persona_role_history", "changed_by"):
        if _has_rows("persona_role_history"):
            log.warning("Skipping downgrade of persona_role_history.changed_by: table has rows.")
        else:
            op.alter_column("persona_role_history", "changed_by", type_=sa.Integer(), postgresql_using=_USING_ZERO)
