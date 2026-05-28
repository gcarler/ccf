"""0048_datetime_to_timestamptz

Revision ID: 20260528_0048
Revises: 20260528_0047
Create Date: 2026-05-28

Convierte campos DateTime críticos a TIMESTAMPTZ (Capa C — Audit Forense).
Los valores existentes se interpretan como UTC (correcto para el servidor VPS).
Impacto en frontend: los valores retornados incluirán offset +00:00,
lo que corrige el bug de desfase de 5 horas con Colombia (UTC-5).

Campos migrados:
  - agenda_eventos: fecha_inicio, fecha_fin (ya son TIMESTAMPTZ en el modelo)
  - crm_casos: fecha_creacion, sla_vencimiento_contacto, fecha_cierre
  - crm_tareas: fecha_vencimiento, created_at
  - crm_interacciones: fecha_interaccion
  - academy_enrollments: completed_at
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260528_0048"
down_revision: Union[str, None] = "20260528_0047"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col_type(table: str, col: str) -> str:
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name=:t AND column_name=:c"
    ), {"t": table, "c": col})
    row = r.fetchone()
    return row[0] if row else ""


CONVERSIONS = [
    # (table, column)
    ("crm_casos", "fecha_creacion"),
    ("crm_casos", "sla_vencimiento_contacto"),
    ("crm_casos", "fecha_cierre"),
    ("crm_tareas", "fecha_vencimiento"),
    ("crm_tareas", "created_at"),
    ("crm_interacciones", "fecha_interaccion"),
    ("academy_enrollments", "completed_at"),
    ("counseling_tickets", "created_at"),
    ("donations", "created_at"),
    ("donations", "updated_at"),
]


_MV_FINANCE_SUMMARY = """
    CREATE MATERIALIZED VIEW mv_finance_summary AS
    SELECT
        COALESCE(SUM(CASE WHEN status='completed' AND created_at >= date_trunc('month', NOW())
                     THEN amount ELSE 0 END), 0) AS monthly_income,
        COALESCE(SUM(CASE WHEN status='completed' THEN amount ELSE 0 END), 0) AS total_income,
        COUNT(DISTINCT CASE WHEN status='completed' THEN donor_email END) AS total_donors,
        COUNT(DISTINCT CASE WHEN status='completed' AND created_at >= date_trunc('month', NOW())
                       THEN donor_email END) AS monthly_donors,
        COUNT(CASE WHEN status='pending' THEN 1 END) AS pending_donations,
        NOW() AS refreshed_at
    FROM donations
    WITH DATA
"""

_DONATIONS_COLS = {"created_at", "updated_at"}


def upgrade() -> None:
    conn = op.get_bind()

    # donations.created_at/updated_at are referenced by mv_finance_summary
    donations_need_change = any(
        _col_type(t, c) not in ("timestamp with time zone", "")
        for t, c in CONVERSIONS
        if t == "donations" and c in _DONATIONS_COLS
    )
    if donations_need_change:
        conn.execute(sa.text("DROP MATERIALIZED VIEW IF EXISTS mv_finance_summary CASCADE"))

    for table, col in CONVERSIONS:
        current_type = _col_type(table, col)
        if current_type in ("timestamp with time zone", ""):
            continue
        conn.execute(sa.text(
            f"ALTER TABLE {table} ALTER COLUMN {col} TYPE TIMESTAMPTZ "
            f"USING {col} AT TIME ZONE 'UTC'"
        ))

    if donations_need_change:
        conn.execute(sa.text(_MV_FINANCE_SUMMARY))
        conn.execute(sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_finance_summary "
            "ON mv_finance_summary (refreshed_at)"
        ))


def downgrade() -> None:
    conn = op.get_bind()
    for table, col in CONVERSIONS:
        current_type = _col_type(table, col)
        if current_type != "timestamp with time zone":
            continue
        conn.execute(sa.text(
            f"ALTER TABLE {table} ALTER COLUMN {col} TYPE TIMESTAMP "
            f"USING {col} AT TIME ZONE 'UTC'"
        ))
