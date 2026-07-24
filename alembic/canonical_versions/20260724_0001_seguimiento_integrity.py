"""seguimiento_integrity (interno F2-F1)

Auditoria follow-up (Evangelismo Fase 2): 3 fixes de integridad agrupados
en ``registros_seguimiento`` por ser la misma entidad:

  1. ``estado_completado`` DEFAULT False (era True): un seguimiento nuevo
     nace pendiente; el flujo UI lo marca como completado cuando se procesa.
     Antes default=True creaba registros "ya completados" contradiciendo
     el panel de pendientes. Rows existentes (True) se conservan (Historico:
     "registrados/completados antes del fix").

  2. CHECK constraint ``ck_registros_seguimiento_tipo`` alinea el
     ``String(30)`` con los 4 valores validos del ``TipoSeguimientoEnum``
     (LLAMADA, MENSAJE_WHATSAPP, VISITA_PRESENCIAL, ORACION). Previene
     INSERT/UPDATE con typo fuera del enum a nivel DB.

  3. Indices en FK ``asistencia_id`` y ``responsable_id`` para acelerar
     los joins ``seguimiento -> asistencia -> sesion -> grupo -> sede``
     usados por Axioma 3 (multi-tenant filter). Sin FK index explicito
     queries eran seq scan en tablas grandes.

Migration aditiva (default change + constraint + indices); downgrade
reverteibles individualmente.

Revision ID: 20260724_0001
Revises: 20260723_0006
Create Date: 2026-07-24 23:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260724_0001"
down_revision: Union[str, None] = "20260723_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Valores validos del TipoSeguimientoEnum (backend/schemas/evangelism.py:117).
_TIPOS_VALIDOS = ("LLAMADA", "MENSAJE_WHATSAPP", "VISITA_PRESENCIAL", "ORACION")


def upgrade() -> None:
    # 1. estado_completado default True -> False (sin tocar rows existentes).
    op.alter_column(
        "registros_seguimiento",
        "estado_completado",
        server_default=sa.sql.false(),
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )

    # 2. CHECK constraint para enum tipo.
    _tipo_values_sql = ", ".join(f"'{v}'" for v in _TIPOS_VALIDOS)
    op.create_check_constraint(
        "ck_registros_seguimiento_tipo",
        "registros_seguimiento",
        f"tipo IN ({_tipo_values_sql})",
    )

    # 3. Indices en FK (asistencia_id y responsable_id).
    op.create_index(
        "ix_registros_seguimiento_asistencia_id",
        "registros_seguimiento",
        ["asistencia_id"],
        unique=False,
    )
    op.create_index(
        "ix_registros_seguimiento_responsable_id",
        "registros_seguimiento",
        ["responsable_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_registros_seguimiento_responsable_id", table_name="registros_seguimiento")
    op.drop_index("ix_registros_seguimiento_asistencia_id", table_name="registros_seguimiento")
    op.drop_constraint(
        "ck_registros_seguimiento_tipo",
        "registros_seguimiento",
        type_="check",
    )
    op.alter_column(
        "registros_seguimiento",
        "estado_completado",
        server_default=sa.sql.true(),
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )
