"""Motor de Proyección Temporal para estrategias de evangelismo."""

from datetime import datetime, timedelta, timezone
from typing import List
import uuid

from sqlalchemy.orm import Session

from backend.models_evangelism import SesionGrupo

FRECUENCIAS = {
    # Valores del FrecuenciaEnum (MAYÚSCULAS) que vienen de la BD
    "SEMANAL": timedelta(weeks=1),
    "QUINCENAL": timedelta(weeks=2),
    "MENSUAL": timedelta(days=30),
    "BIMENSUAL": timedelta(days=60),
    "TRIMESTRAL": timedelta(days=90),
    "SEMESTRAL": timedelta(days=180),
    "ANUAL": timedelta(days=365),
    # Back-compat: valores capitalizados
    "Semanal": timedelta(weeks=1),
    "Quincenal": timedelta(weeks=2),
    "Mensual": timedelta(days=30),
    "Bimensual": timedelta(days=60),
    "Trimestral": timedelta(days=90),
    "Semestral": timedelta(days=180),
    "Anual": timedelta(days=365),
}


def proyectar_sesiones(
    db: Session,
    estrategia_id: str,
    sede_id: uuid.UUID,
    fecha_inicio: datetime,
    fecha_fin: datetime,
    frecuencia: str,
    grupos_ids: List[int],
) -> int:
    """Genera sesiones PENDIENTES para cada grupo de la estrategia."""
    delta = FRECUENCIAS.get(frecuencia)
    if delta is None:
        raise ValueError(f"Frecuencia no soportada: {frecuencia}")

    if fecha_inicio.tzinfo is None:
        fecha_inicio = fecha_inicio.replace(tzinfo=timezone.utc)
    if fecha_fin.tzinfo is None:
        fecha_fin = fecha_fin.replace(tzinfo=timezone.utc)

    fechas = []
    current = fecha_inicio
    while current <= fecha_fin:
        fechas.append(current)
        current += delta

    if not fechas or not grupos_ids:
        return 0

    created = 0
    for grupo_id in grupos_ids:
        for fecha in fechas:
            exists = (
                db.query(SesionGrupo)
                .filter(
                    SesionGrupo.grupo_id == grupo_id,
                    SesionGrupo.fecha_sesion == fecha,
                    SesionGrupo.deleted_at.is_(None),
                )
                .first()
            )
            if not exists:
                db.add(
                    SesionGrupo(
                        grupo_id=grupo_id,
                        fecha_sesion=fecha,
                        estado="PENDIENTE",
                    )
                )
                created += 1

    db.commit()
    return created
