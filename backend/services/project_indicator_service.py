"""Servicio de indicadores de proyectos — cronología de mediciones (W1).

W1 (Auditoría motores indicadores 2026-10-24, hallazgo 11/D1): los reportes
extemporáneos (backfill con `reported_at` anterior) no deben pisar el estado
actual del indicador. `current_value` y `last_spi` se resuelven del registro
VIVO más reciente de la historia por `(reported_at DESC, created_at DESC)` con
desempate determinista por `id DESC`.

Reglas respetadas:
- Soft delete (Axioma 2): solo participan registros con `deleted_at IS NULL`.
- Fechas UTC (Axioma de fechas): las columnas son `DateTime(timezone=True)`.
- Aislamiento por sede: la resolución se hace por `indicator_id`; el scope de
  sede lo garantiza el CRUD que obtiene el indicador (`get_project_indicator`).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from backend.models_projects import ProjectIndicator, ProjectIndicatorRecord

logger = logging.getLogger(__name__)

# Desempate determinista cuando dos registros comparten reported_at y created_at.
_ORDER_TIEBREAK_ATTR = "id"


def sort_records_chronologically_desc(
    records: Iterable[ProjectIndicatorRecord],
) -> list[ProjectIndicatorRecord]:
    """Ordena registros de medición por cronología descendente (W1).

    Clave principal: `reported_at` (fecha efectiva de la medición, admite
    reportes extemporáneos). Desempates: `created_at` y, por último, `id`.
    Los registros con `reported_at` ausente usan `created_at` como fallback
    (consistente con el comportamiento previo del CRUD).
    """
    return sorted(
        records or [],
        key=lambda r: (
            r.reported_at or r.created_at,
            r.created_at,
            getattr(r, _ORDER_TIEBREAK_ATTR, None),
        ),
        reverse=True,
    )


def get_latest_live_record(
    db: Session,
    indicator_id: object,
) -> Optional[ProjectIndicatorRecord]:
    """Devuelve el registro vivo más reciente por cronología (W1) o `None`.

    - Excluye registros con soft delete (`deleted_at IS NULL`, Axioma 2).
    - Orden: `reported_at DESC, created_at DESC, id DESC`.
    - Si se añadieron registros a la sesión sin flush previo, la consulta
      dispara autoflush y los incluye (compatible con flujos transaccionales).
    """
    query = (
        db.query(ProjectIndicatorRecord)
        .filter(
            ProjectIndicatorRecord.indicator_id == indicator_id,
            ProjectIndicatorRecord.deleted_at.is_(None),
        )
        .order_by(
            ProjectIndicatorRecord.reported_at.desc(),
            ProjectIndicatorRecord.created_at.desc(),
            ProjectIndicatorRecord.id.desc(),
        )
    )
    return query.first()


def apply_chronological_current_value(
    db: Session,
    indicator: ProjectIndicator,
) -> Optional[ProjectIndicatorRecord]:
    """Re-resuelve `current_value` del indicador desde su historia viva (W1).

    Persiste en el indicador el `actual_value` del registro vivo más reciente
    por cronología y actualiza `updated_at` en UTC. Si el indicador no tiene
    registros vivos, deja `current_value` intacto y devuelve `None`.
    """
    # La plataforma opera con `autoflush=False` (core/database.py); el flush
    # explícito garantiza que los registros añadidos a la sesión en curso
    # participen en la consulta antes de resolver la cronología.
    db.flush()
    latest = get_latest_live_record(db, indicator.id)
    if latest is None:
        return None

    indicator.current_value = float(latest.actual_value or 0.0)
    indicator.updated_at = datetime.now(timezone.utc)
    return latest


__all__ = [
    "apply_chronological_current_value",
    "get_latest_live_record",
    "sort_records_chronologically_desc",
]
