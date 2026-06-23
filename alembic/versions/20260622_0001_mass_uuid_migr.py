"""Blocked mass UUID migration placeholder.

This revision intentionally performs no schema changes. A draft mass migration
from integer PKs to UUIDs was unsafe because it crossed many domains, started a
separate Alembic branch, and dropped primary key columns without a complete
child-FK mapping and validation path.

Per the CCF safe-change protocol, PK/FK migrations must be implemented as
small, domain-specific, reversible batches after explicit approval.
"""

revision = "20260622_0001_mass_uuid_migr"
down_revision = "identity_uuid_migration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
