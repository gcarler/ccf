"""W2 indicadores: unicidad parcial viva de mediciones por (indicator_id, period).

Deduplica mediciones vivas duplicadas de `project_indicator_records` con soft
delete (conserva la medición cronológicamente más reciente por
`reported_at DESC, created_at DESC, id DESC` — coherente con W1 — y marca en
UTC `deleted_at` en las demás; sin hard delete, Axioma 2) y crea el índice
único parcial `uq_project_indicator_records_indicator_period_live` sobre las
filas vivas (`deleted_at IS NULL`), compatible con PostgreSQL y SQLite.
Reversible: `downgrade()` elimina el índice; los registros marcados no se
restauran (historia marcada, REGLAS §9 — memoria inmutable).

La deduplicación usa SQLAlchemy Core con reflexión (sin acoplar la migración
a los modelos vigentes) y valores `datetime` timezone-aware UTC, por lo que
cada dialecto serializa correctamente la columna.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20261028_0001_project_indicator_records_live_unique"
down_revision: Union[str, None] = "20261024_0001_add_coq_amount_to_project_dod_acceptances"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX_NAME = "uq_project_indicator_records_indicator_period_live"
_TABLE = "project_indicator_records"


def _soft_delete_duplicate_rows(bind: sa.engine.Connection) -> int:
    """Marca en UTC los registros vivos no más recientes de cada (indicator_id, period)."""
    metadata = sa.MetaData()
    table = sa.Table(_TABLE, metadata, autoload_with=bind)

    live_rows = bind.execute(
        sa.select(
            table.c.indicator_id,
            table.c.period,
            table.c.id,
            table.c.reported_at,
            table.c.created_at,
        ).where(table.c.deleted_at.is_(None))
    ).fetchall()

    newest_by_key: dict[tuple[object, object], tuple[object, object, object]] = {}
    rows_by_key: dict[tuple[object, object], list[object]] = defaultdict(list)
    for indicator_id, period, row_id, reported_at, created_at in live_rows:
        key = (indicator_id, period)
        rows_by_key[key].append(row_id)
        current = (reported_at, created_at, row_id)
        known = newest_by_key.get(key)
        if known is None or current > known:
            newest_by_key[key] = current

    # Para cada grupo se conserva el ganador de la cronología (W1) y se marca
    # el resto; con un único registro vivo no hay nada que marcar.
    to_soft_delete: list[object] = []
    for key, newest in newest_by_key.items():
        for row_id in rows_by_key[key]:
            if row_id != newest[2]:
                to_soft_delete.append(row_id)

    if to_soft_delete:
        now = datetime.now(timezone.utc)
        for row_id in to_soft_delete:
            bind.execute(
                table.update()
                .where(table.c.id == row_id)
                .values(deleted_at=now, updated_at=now)
            )
    return len(to_soft_delete)


def upgrade() -> None:
    bind = op.get_bind()
    # 1) Sin duplicados vivos antes de crear el índice único (soft delete).
    _soft_delete_duplicate_rows(bind)

    # 2) Índice único parcial: solo filas vivas (deleted_at IS NULL).
    op.create_index(
        _INDEX_NAME,
        _TABLE,
        ["indicator_id", "period"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(_INDEX_NAME, table_name=_TABLE)
