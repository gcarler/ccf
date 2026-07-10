"""cms_seo_snapshots — daily SEO score trend table

Adds ``cms_seo_snapshots`` (one row per faro site per UTC day) so the
``/plataforma/dashboard/cms`` widget can show historical trend data with
sparklines + 10-point-drop alerts. Captured by ``backend.scheduler``.

Axioma 3 compliance:
  * Multi-tenant via ``sede_id`` mirror + composite uniqueness on
    ``(site_id, captured_date)`` keeps the table lean and idempotent
    even if the cron retries within the same day.

Reversible: drops the table + indexes on downgrade.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260706_0002_cms_seo_snapshots"
down_revision = "20260706_0001_cms_schedule"
branch_labels = None
depends_on = None


def _uuid_type() -> sa.types.TypeEngine:
    """UUID portable: ``postgresql.UUID`` en Postgres, ``String(36)`` en SQLite.

    Patrón estándar del codebase (ver ``20260701_0001_cms_content_sede_id``,
    ``20260701_0003_crm_events_sede_id_uuid``, ``20260703_0001_cms_sites_sede_id``).
    Alembic ejecuta la migración contra el engine que apunte ``alembic.ini``
    — sqlite en tests, postgres en prod — y este helper elige el tipo
    correcto en función del dialect activo.
    """
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.dialects.postgresql.UUID(as_uuid=True)
    return sa.String(length=36)


def upgrade() -> None:
    uuid_t = _uuid_type()
    op.create_table(
        "cms_seo_snapshots",
        sa.Column("id", uuid_t, primary_key=True),
        sa.Column(
            "site_id",
            uuid_t,
            sa.ForeignKey("cms_sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sede_id",
            uuid_t,
            sa.ForeignKey("sedes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("captured_date", sa.Date(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("average_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_pages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_with_errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("critical_issues", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("by_severity_json", sa.JSON(), nullable=True),
        sa.UniqueConstraint("site_id", "captured_date", name="uq_cms_seo_snapshot_site_date"),
    )

    # Indexes — separate from the unique constraint so rango queries
    # (history_7d, history_30d) stay index-only.
    op.create_index(
        "ix_cms_seo_snapshots_site_id",
        "cms_seo_snapshots",
        ["site_id"],
        unique=False,
    )
    op.create_index(
        "ix_cms_seo_snapshots_sede_id",
        "cms_seo_snapshots",
        ["sede_id"],
        unique=False,
    )
    op.create_index(
        "ix_cms_seo_snapshots_captured_date",
        "cms_seo_snapshots",
        ["captured_date"],
        unique=False,
    )
    # Compound index for the most common query pattern: "give me the
    # last N days of snapshots for this faro site range-filtered by date".
    op.create_index(
        "ix_cms_seo_snapshots_site_date_desc",
        "cms_seo_snapshots",
        ["site_id", sa.text("captured_date DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_cms_seo_snapshots_site_date_desc", table_name="cms_seo_snapshots")
    op.drop_index("ix_cms_seo_snapshots_captured_date", table_name="cms_seo_snapshots")
    op.drop_index("ix_cms_seo_snapshots_sede_id", table_name="cms_seo_snapshots")
    op.drop_index("ix_cms_seo_snapshots_site_id", table_name="cms_seo_snapshots")
    op.drop_table("cms_seo_snapshots")
