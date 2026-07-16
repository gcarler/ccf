"""Normalize project status values to canonical 5-value enum.

Legacy values like ``paused``/``stopped``/``done``/``finished``/``cancelled``/
``closed`` are mapped to their canonical equivalents. The new
``ProjectStatus`` schema in ``backend/schemas/projects.py`` enforces the
canonical values on input (with a ``BeforeValidator`` that performs the same
legacy mapping losslessly).

This migration is idempotent at the SQL level. To apply::

    alembic upgrade head

To roll back: legacy values are not preserved after upgrade — the migration is
intentionally lossy because we don't have a destination column for the
original ("cancelled" vs "archived"). Downgrade is a no-op.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260717_0001_normalize_project_status"
# Chain from the most recent canonical migration on the projects branch.
# Adjust if the local head differs in your checkout.
down_revision = "20260710_0001_add_deleted_at_to_project_tables"
branch_labels = None
depends_on = None


CANONICAL_PROJECT_STATUSES = ("planning", "active", "on_hold", "completed", "archived")
LEGACY_TO_CANONICAL = (
    ("paused", "on_hold"),
    ("stopped", "on_hold"),
    ("done", "completed"),
    ("finished", "completed"),
    ("cancelled", "archived"),
    ("closed", "archived"),
)


def upgrade() -> None:
    # Map legacy → canonical (lossless for the wire-format invariant; lossy
    # against the original string since we don't audit revertibility).
    for legacy, canonical in LEGACY_TO_CANONICAL:
        op.execute(
            f"UPDATE projects SET status = '{canonical}' WHERE status = '{legacy}'"
        )

    # Anything else not in canonical (e.g. NULL or an unknown enum value that
    # bypassed earlier validation) gets defaulted to 'planning' — the safest
    # visible reset. Operators can review the audit logs if needed.
    canonical_sql = ", ".join(f"'{s}'" for s in CANONICAL_PROJECT_STATUSES)
    op.execute(
        f"UPDATE projects SET status = 'planning' "
        f"WHERE status IS NULL OR status NOT IN ({canonical_sql})"
    )
    # Optional DB-level constraint. Comment-in to enforce at the SQL layer;
    # uncomment if downstream tooling breaks on legacy values.
    # op.create_check_constraint(
    #     "ck_projects_status_canonical",
    #     "projects",
    #     f"status IN ({canonical_sql})",
    # )


def downgrade() -> None:
    # Intentionally lossy; see module docstring.
    pass
