"""0045_crm_quality_fixes

Revision ID: 20260528_0045
Revises: 20260527_0044
Create Date: 2026-05-28

Quality fixes across CRM models:
- spiritual_milestones.person_id: INTEGER (no FK) → UUID FK to personas
- counseling_tickets.member_id → renamed to persona_id (already UUID)
- donations.amount / funds.current_balance: FLOAT → NUMERIC(14,2)
- funds.name: add UNIQUE constraint
- member_roles: add UniqueConstraint(persona_id, role_id)
- personas.birthday: DATETIME → DATE
- personas.latitud/longitud: FLOAT → NUMERIC(10,8)/NUMERIC(11,8)
- donations.person_id (orphan integer): drop column
- donations.fund_id: add FK to funds.fund_id
- crm_etapas_pipeline: add UniqueConstraint(pipeline_id, orden)
- crm_pipelines / crm_plantillas_mensaje: add created_at / updated_at
- crm_casos.is_overdue: drop stored column (now a hybrid_property)
- crm_casos.sla_vencimiento_contacto: allow NULL
- crm_interacciones: add duration_seconds
- crm_tareas: add created_at, indexes
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260528_0045"
down_revision: Union[str, None] = "20260527_0044"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col_exists(table: str, col: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT count(*) FROM information_schema.columns "
        "WHERE table_name=:t AND column_name=:c"
    ), {"t": table, "c": col})
    return r.scalar() > 0


def _constraint_exists(name: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT count(*) FROM information_schema.table_constraints WHERE constraint_name=:n"
    ), {"n": name})
    return r.scalar() > 0


def _index_exists(name: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT count(*) FROM pg_indexes WHERE indexname=:n"
    ), {"n": name})
    return r.scalar() > 0


def upgrade() -> None:
    conn = op.get_bind()

    # ── spiritual_milestones: INTEGER person_id → UUID FK ──────────────────
    if _col_exists("spiritual_milestones", "person_id"):
        conn.execute(sa.text("ALTER TABLE spiritual_milestones DROP COLUMN person_id"))
    if not _col_exists("spiritual_milestones", "persona_id"):
        op.add_column("spiritual_milestones",
            sa.Column("persona_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("personas.id", ondelete="CASCADE"),
                      nullable=True, index=True))

    # ── counseling_tickets: rename member_id → persona_id ──────────────────
    if _col_exists("counseling_tickets", "member_id") and \
       not _col_exists("counseling_tickets", "persona_id"):
        op.alter_column("counseling_tickets", "member_id", new_column_name="persona_id")

    # ── donations: FLOAT amount → NUMERIC(14,2) ─────────────────────────────
    # mv_finance_summary depends on donations.amount — drop/recreate around the ALTER
    conn.execute(sa.text("DROP MATERIALIZED VIEW IF EXISTS mv_finance_summary CASCADE"))
    conn.execute(sa.text(
        "ALTER TABLE donations ALTER COLUMN amount TYPE NUMERIC(14,2) "
        "USING amount::NUMERIC(14,2)"
    ))
    conn.execute(sa.text("""
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
    """))
    conn.execute(sa.text(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_finance_summary "
        "ON mv_finance_summary (refreshed_at)"
    ))
    # donations: drop orphan integer person_id
    if _col_exists("donations", "person_id"):
        conn.execute(sa.text("ALTER TABLE donations DROP COLUMN person_id"))
    # donations: add FK to funds
    if _col_exists("donations", "fund_id"):
        conn.execute(sa.text(
            "ALTER TABLE donations DROP CONSTRAINT IF EXISTS donations_fund_id_fkey"
        ))
        try:
            conn.execute(sa.text(
                "ALTER TABLE donations ADD CONSTRAINT fk_donations_fund "
                "FOREIGN KEY (fund_id) REFERENCES funds(fund_id) ON DELETE SET NULL"
            ))
        except Exception:
            pass

    # ── funds: FLOAT → NUMERIC(14,2), add UNIQUE on name ───────────────────
    conn.execute(sa.text(
        "ALTER TABLE funds ALTER COLUMN current_balance TYPE NUMERIC(14,2) "
        "USING current_balance::NUMERIC(14,2)"
    ))
    if _col_exists("funds", "target_amount"):
        conn.execute(sa.text(
            "ALTER TABLE funds ALTER COLUMN target_amount TYPE NUMERIC(14,2) "
            "USING target_amount::NUMERIC(14,2)"
        ))
    if not _constraint_exists("uq_funds_name"):
        conn.execute(sa.text(
            "ALTER TABLE funds ADD CONSTRAINT uq_funds_name UNIQUE (name)"
        ))

    # ── member_roles: rename member_id → persona_id, add UniqueConstraint ───
    if _col_exists("member_roles", "member_id") and \
       not _col_exists("member_roles", "persona_id"):
        op.alter_column("member_roles", "member_id", new_column_name="persona_id")
    if not _constraint_exists("uq_member_role"):
        conn.execute(sa.text(
            "DELETE FROM member_roles m1 USING member_roles m2 "
            "WHERE m1.id > m2.id AND m1.persona_id = m2.persona_id AND m1.role_id = m2.role_id"
        ))
        conn.execute(sa.text(
            "ALTER TABLE member_roles ADD CONSTRAINT uq_member_role "
            "UNIQUE (persona_id, role_id)"
        ))

    # ── personas: birthday TIMESTAMP → DATE ─────────────────────────────────
    conn.execute(sa.text(
        "ALTER TABLE personas ALTER COLUMN birthday TYPE DATE "
        "USING birthday::DATE"
    ))
    # personas: latitud/longitud FLOAT → NUMERIC
    conn.execute(sa.text(
        "ALTER TABLE personas ALTER COLUMN latitud TYPE NUMERIC(10,8) "
        "USING latitud::NUMERIC(10,8)"
    ))
    conn.execute(sa.text(
        "ALTER TABLE personas ALTER COLUMN longitud TYPE NUMERIC(11,8) "
        "USING longitud::NUMERIC(11,8)"
    ))

    # ── crm_etapas_pipeline: UniqueConstraint(pipeline_id, orden) ───────────
    if not _constraint_exists("uq_etapa_pipeline_orden"):
        conn.execute(sa.text(
            "ALTER TABLE crm_etapas_pipeline ADD CONSTRAINT uq_etapa_pipeline_orden "
            "UNIQUE (pipeline_id, orden)"
        ))

    # ── crm_pipelines: add timestamps ───────────────────────────────────────
    if not _col_exists("crm_pipelines", "created_at"):
        op.add_column("crm_pipelines",
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")))
    if not _col_exists("crm_pipelines", "updated_at"):
        op.add_column("crm_pipelines",
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()")))

    # ── crm_plantillas_mensaje: add created_at ───────────────────────────────
    if not _col_exists("crm_plantillas_mensaje", "created_at"):
        op.add_column("crm_plantillas_mensaje",
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")))

    # ── crm_casos: drop is_overdue (now hybrid_property), allow NULL sla ────
    if _col_exists("crm_casos", "is_overdue"):
        conn.execute(sa.text("ALTER TABLE crm_casos DROP COLUMN is_overdue"))
    conn.execute(sa.text(
        "ALTER TABLE crm_casos ALTER COLUMN sla_vencimiento_contacto DROP NOT NULL"
    ))

    # ── crm_interacciones: add duration_seconds ──────────────────────────────
    if not _col_exists("crm_interacciones", "duration_seconds"):
        op.add_column("crm_interacciones",
            sa.Column("duration_seconds", sa.Integer(), server_default="0"))

    # ── crm_tareas: add created_at, indexes ──────────────────────────────────
    if not _col_exists("crm_tareas", "created_at"):
        op.add_column("crm_tareas",
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")))
    for idx, tbl, col in [
        ("ix_crm_tareas_completada", "crm_tareas", "completada"),
        ("ix_crm_tareas_fecha_vencimiento", "crm_tareas", "fecha_vencimiento"),
    ]:
        if not _index_exists(idx):
            conn.execute(sa.text(f"CREATE INDEX {idx} ON {tbl} ({col})"))


def downgrade() -> None:
    pass
