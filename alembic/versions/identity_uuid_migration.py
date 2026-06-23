"""Blocked identity UUID migration placeholder.

This revision intentionally performs no schema changes. The previous draft
attempted to migrate authentication and identity tables in one broad step,
which is protected compat under the CCF safe-change protocol.

Identity/auth UUID work must be split into approved reversible batches with:
- dependency inventory;
- temporary UUID columns for each FK, not only PK placeholders;
- JOIN backfill from the compat integer relation;
- zero-orphan validation;
- rollback and smoke tests for login/session flows.
"""

revision = "identity_uuid_migration"
down_revision = "ent001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
