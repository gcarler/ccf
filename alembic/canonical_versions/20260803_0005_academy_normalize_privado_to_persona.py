"""Academy: normalizar access_level='privado' a 'persona'

Corrección de datos post-cierre del hallazgo 2 (ses_03767db76ffee 2026-08-03):
el commit ``c1d923c0`` (2026-08-02) endureció ``public_list_courses`` con un
filtro ``Course.access_level == "persona"``, excluyendo cualquier curso
publicado cuyo ``access_level`` no fuera exactamente ``"persona"``. La auditoría
de BD prod (ccf_db/PostgreSQL) reveló 4 cursos publicados con
``access_level='privado'`` — un valor **huérfano del enum canónico**
``Literal["open", "persona", "advanced"]`` en ``backend/schemas/academy.py``:
no insertable por la API actual, pero heredado de inserciones anteriores.
Esos 4 cursos dejaron de aparecer en la landing pública ``/cursos`` sin
migración ni announcement.

Esta migración normaliza esos 4 (o cualquier future) ``access_level='privado'``
a ``'persona'`` para que vuelvan a ser visibles en ``/cursos``, alineando
el catálogo con el enum canónico (``"privado"`` nunca fue un valor legítimo
de la API; ``"persona"`` es el default ``server_default`` del modelo y la
única categoría pública soportada).

Idempotente: un re-run no modifica filas que ya tengan ``access_level='persona'``
(u otras) — el ``WHERE access_level = 'privado'`` acota el alcance. La
verificación ``_count_privado()`` evita el UPDATE en bruto si no hay filas
que normalizar (defensa en tests SQLite donde la tabla puede no existir).

Downgrade: no-op (la reversión a ``'privado'`` re-ocultaría los cursos de la
landing sin motivo, rompiendo visibilidad adquirida). El downgrade se declara
como benign-nop siguiendo el patrón de la migración
``20260801_0004_add_evangelism_group_end_time`` (canonical): valores
corregidos no son semánticamente reversibles.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260803_0005_academy_normalize_privado_to_persona"
down_revision: Union[str, None] = "20260801_0004_add_evangelism_group_end_time"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "academy_courses"
_LEGACY_VALUE = "privado"
_CANONICAL_VALUE = "persona"


def _has_table() -> bool:
    return sa.inspect(op.get_bind()).has_table(_TABLE)


def _count_privado() -> int:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(f"SELECT COUNT(*) FROM {_TABLE} WHERE access_level = :v"),
        {"v": _LEGACY_VALUE},
    )
    return int(result.scalar() or 0)


def upgrade() -> None:
    if not _has_table():
        return
    count = _count_privado()
    if count == 0:
        return
    bind = op.get_bind()
    bind.execute(
        sa.text(
            f"UPDATE {_TABLE} SET access_level = :canon WHERE access_level = :legacy"
        ),
        {"canon": _CANONICAL_VALUE, "legacy": _LEGACY_VALUE},
    )


def downgrade() -> None:
    # Monotonic data migration: la reversión re-ocultaría los cursos de la
    # landing pública sin motivo, rompiendo visibilidad adquirida. No-op
    # siguiendo el patrón ``20260801_0004_add_evangelism_group_end_time``.
    pass
