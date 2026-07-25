"""20260725_0001 — add sede_id to crm_automation_flows

Axioma 3 hardening del modulo CRM (auditoria forense errorescrm.md C-04):

``crm_automation_flows`` carecía completamente de la columna ``sede_id``, lo
que convertía todos los flujos de automatización en entidades globales
cross-tenant. Cualquier pastor con ``crm:edit`` podía ver y mutar los flujos
de cualquier sede — vió REGLAS.md §4.2 y Axioma 3. Esta migración añade la
columna:

  - ``crm_automation_flows.sede_id`` — ``UUID`` ``nullable=True`` FK a
    ``sedes.id`` indexado. Se deja nullable para no romper rows legacy
    (backfill manuales pendientes o borrado de flujos legacy). El contrato
    del API exige ``sede_id is not None`` al crear flujos nuevos y filtra por
    sede del actor en toda operación de lectura/escritura.

Las tablas derivadas ``crm_automation_nodes``, ``crm_flow_branches`` y
``crm_flow_cycle_cache`` NO reciben ``sede_id`` propio: heredan el tenant al
JOIN por ``flow_id``. Esto evita denormalización multi-columna y mantiene
single-source-of-truth en el flow padre.

SQLite branch: this migration is a no-op on SQLite because tests use
``Base.metadata.create_all`` (NOT alembic migrations) — the model-level change
is sufficient for the test suite. The Postgres branch performs the real
``ALTER TABLE``.

Revision ID: 20260725_0001
Revises: 20260724_0001
Create Date: 2026-07-25 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260725_0001"
down_revision: Union[str, None] = "20260724_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # SQLite branch: no-op (tests use Base.metadata.create_all, not migrations).
    # The model already declares the column; tests get it for free.
    if dialect == "sqlite":
        return

    # Postgres branch (production): real ALTER TABLE.
    op.add_column(
        "crm_automation_flows",
        sa.Column(
            "sede_id",
            sa.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_crm_automation_flows_sede_id",
        "crm_automation_flows",
        ["sede_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_crm_automation_flows_sede_id",
        "crm_automation_flows",
        "sedes",
        ["sede_id"],
        ["id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        return

    op.drop_constraint("fk_crm_automation_flows_sede_id", "crm_automation_flows", type_="foreignkey")
    op.drop_index("ix_crm_automation_flows_sede_id", table_name="crm_automation_flows")
    op.drop_column("crm_automation_flows", "sede_id")
