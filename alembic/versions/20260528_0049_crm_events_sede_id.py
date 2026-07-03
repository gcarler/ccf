"""0049_crm_events_sede_id

Revision ID: 20260528_0049
Revises: 20260528_0048
Create Date: 2026-05-28

Añade sede_id a crm_events para cerrar brecha B-001 del audit forense.
Cierra el último endpoint sin filtro multi-tenant: GET /analytics/events/summary.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260528_0049"
down_revision: Union[str, None] = "20260528_0048"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name=:t"
    ), {"t": table})
    return r.scalar() > 0


def _col_exists(table: str, col: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT count(*) FROM information_schema.columns "
        "WHERE table_name=:t AND column_name=:c"
    ), {"t": table, "c": col})
    return r.scalar() > 0


def upgrade() -> None:
    # crm_events may not exist if never bootstrapped (compat model, no prior migration)
    if not _table_exists("crm_events"):
        conn = op.get_bind()
        conn.execute(sa.text("""
            CREATE TABLE crm_events (
                id SERIAL PRIMARY KEY,
                sede_id INTEGER REFERENCES sedes(id) ON DELETE SET NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                event_date TIMESTAMP,
                event_type VARCHAR(20) DEFAULT 'PERMANENT',
                start_time VARCHAR(50),
                end_time VARCHAR(50),
                day_of_week INTEGER,
                month_day VARCHAR(10),
                location VARCHAR(200),
                status VARCHAR(20) DEFAULT 'SCHEDULED',
                cancellation_reason TEXT,
                target_audience VARCHAR(50) DEFAULT 'ALL',
                target_role_id INTEGER,
                target_role_ids JSON,
                target_member_ids JSON,
                fixed_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(sa.text(
            "CREATE INDEX ix_crm_events_sede_id ON crm_events (sede_id)"
        ))
        return

    if not _col_exists("crm_events", "sede_id"):
        op.add_column(
            "crm_events",
            sa.Column("sede_id", sa.Integer(),
                      sa.ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_crm_events_sede_id", "crm_events", ["sede_id"])


def downgrade() -> None:
    if _col_exists("crm_events", "sede_id"):
        op.drop_index("ix_crm_events_sede_id", table_name="crm_events")
        op.drop_column("crm_events", "sede_id")
