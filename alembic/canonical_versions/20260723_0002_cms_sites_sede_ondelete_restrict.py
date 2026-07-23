"""cms_sites.sede_id ondelete SET NULL -> RESTRICT (Axioma 3 hardening, C-01)

Revision ID: 20260723_0002_cms_sites_sede_ondelete_restrict
Revises: 20260723_0001
Create Date: 2026-07-23 00:00:00.000000

Endurece el FK ``cms_sites.sede_id`` para cerrar el leak multi-tenant
documentado en el hallazgo C-01 de la auditoría forense del CMS.

Contexto: ``ondelete="SET NULL"`` dejaba los sites huérfanos con
``sede_id=None`` al eliminar una sede, y ``_assert_site_sede_scope`` los
exponía a CUALQUIER actor con sede. El fix en runtime ya endureció ese
helper (un site sin sede solo lo opera un admin global); este cambio de
FK impide que se generen NUEVOS huérfanos: Postgres rechaza la
eliminación de una sede con sites dependientes.

Postgres-native: DROP + ADD del constraint detectado (``ALTER CONSTRAINT``
no soporta cambiar ``ON DELETE``). En SQLite (tests) el fix no es
necesario: los tests usan ``Base.metadata.create_all`` que ya refleja el
modelo actualizado, así que el branch SQLite es un no-op seguro. No se
recrea la tabla en tests para evitar perder datos de seed.

``downgrade`` vuelve a SET NULL (REGLAS.md §9: migraciones reversibles).
El helper de runtime sigue bloqueando huérfanos incluso tras el downgrade.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260723_0002_cms_sites_sede_ondelete_restrict"
down_revision: Union[str, None] = "20260723_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _fk_name() -> str | None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return None
    insp = _inspector()
    if "cms_sites" not in set(insp.get_table_names()):
        return None
    for fk in insp.get_foreign_keys("cms_sites"):
        cols = fk.get("constrained_columns") or []
        if "sede_id" in cols:
            return fk.get("name")
    return None


def upgrade() -> None:
    if "cms_sites" not in set(_inspector().get_table_names()):
        return

    if op.get_bind().dialect.name != "postgresql":
        # SQLite (tests) usa Base.metadata.create_all; nada que alterar.
        return

    fk = _fk_name()
    if not fk:
        return
    op.execute(f'ALTER TABLE "cms_sites" DROP CONSTRAINT "{fk}";')
    op.execute(
        f'ALTER TABLE "cms_sites" ADD CONSTRAINT "{fk}" '
        'FOREIGN KEY ("sede_id") REFERENCES "sedes" ("id") '
        "ON DELETE RESTRICT NOT DEFERRABLE INITIALLY IMMEDIATE;"
    )


def downgrade() -> None:
    if "cms_sites" not in set(_inspector().get_table_names()):
        return
    if op.get_bind().dialect.name != "postgresql":
        return

    fk = _fk_name()
    if not fk:
        return
    op.execute(f'ALTER TABLE "cms_sites" DROP CONSTRAINT "{fk}";')
    op.execute(
        f'ALTER TABLE "cms_sites" ADD CONSTRAINT "{fk}" '
        'FOREIGN KEY ("sede_id") REFERENCES "sedes" ("id") '
        "ON DELETE SET NULL NOT DEFERRABLE INITIALLY IMMEDIATE;"
    )
