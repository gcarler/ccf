"""Make evangelism_strategy_id NOT NULL on glory_houses

Faro groups must belong to a Relacional strategy. No standalone groups allowed.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260524_0030"
down_revision = "20260524_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure no NULL values exist before adding constraint
    op.execute("""
        DELETE FROM glory_houses WHERE evangelism_strategy_id IS NULL
    """)
    # Make column NOT NULL with a default for new records
    op.alter_column(
        'glory_houses',
        'evangelism_strategy_id',
        existing_type=sa.Integer(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        'glory_houses',
        'evangelism_strategy_id',
        existing_type=sa.Integer(),
        nullable=True,
    )
