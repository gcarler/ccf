"""Algoritmo de Cálculo de Sesiones — Genera sesiones PENDIENTES para todos
los grupos de una estrategia de evangelismo según su frecuencia y ventana de
fechas (inicio-fin).

Reglas de calidad aplicadas:
1. Validación de frecuencia soportada (ValueError si no coincide).
2. Normalización de timezone a UTC para evitar sesgos por huso.
3. Protección contra delta cero (bucle infinito).
4. Validación fecha_inicio <= fecha_fin.
5. Cada sesión se compara con deleted_at IS NULL para evitar duplicados.
6. Cada iteración genera una sesión por grupo por fecha.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List
import uuid

from sqlalchemy.orm import Session

from backend.models_evangelism import SesionGrupo, FrecuenciaEnum

# Mapa de frecuencia → delta temporal.
# Las claves son los valores del FrecuenciaEnum (mayúsculas ISO).
_FRECUENCIA_A_DELTA: dict[str, timedelta] = {
    FrecuenciaEnum.SEMANAL.value: timedelta(weeks=1),
    FrecuenciaEnum.QUINCENAL.value: timedelta(weeks=2),
    FrecuenciaEnum.MENSUAL.value: timedelta(days=30),
    FrecuenciaEnum.BIMENSUAL.value: timedelta(days=60),
    FrecuenciaEnum.TRIMESTRAL.value: timedelta(days=90),
    FrecuenciaEnum.SEMESTRAL.value: timedelta(days=180),
    FrecuenciaEnum.ANUAL.value: timedelta(days=365),
    # Back-compat: datos legacy con capitalización
    "Semanal": timedelta(weeks=1),
    "Quincenal": timedelta(weeks=2),
    "Mensual": timedelta(days=30),
    "Bimensual": timedelta(days=60),
    "Trimestral": timedelta(days=90),
    "Semestral": timedelta(days=180),
    "Anual": timedelta(days=365),
}


def _delta_para_frecuencia(frecuencia: str) -> timedelta:
    """Retorna el timedelta para una frecuencia dada.

    Raises:
        ValueError: si la frecuencia no está soportada.
    """
    delta = _FRECUENCIA_A_DELTA.get(frecuencia)
    if delta is None:
        soportadas = ", ".join([e.value for e in FrecuenciaEnum])
        raise ValueError(
            f"Frecuencia no soportada: '{frecuencia}'. "
            f"Soportadas: {soportadas}"
        )
    return delta


def _a_utc(dt: datetime) -> datetime:
    """Asegura que el datetime tenga timezone UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _generar_fechas(inicio: datetime, fin: datetime, delta: timedelta) -> List[datetime]:
    """Genera lista de fechas desde inicio hasta fin saltando por delta.

    Raises:
        ValueError: si el delta es cero (evitaría bucle infinito).
    """
    if delta.total_seconds() <= 0:
        raise ValueError("El intervalo de frecuencia debe ser mayor a cero.")
    if inicio > fin:
        raise ValueError("La fecha de inicio no puede ser posterior a la fecha de fin.")

    fechas: List[datetime] = []
    current = inicio
    while current <= fin:
        fechas.append(current)
        current += delta
    return fechas


def calcular_sesiones(
    db: Session,
    estrategia_id: str,
    sede_id: uuid.UUID,
    fecha_inicio: datetime,
    fecha_fin: datetime,
    frecuencia: str,
    grupos_ids: List[int],
) -> int:
    """Genera sesiones PENDIENTES para cada grupo de la estrategia.

    Args:
        db: Sesión de base de datos.
        estrategia_id: ID de la estrategia (solo para metadatos).
        sede_id: ID de la sede (solo para metadatos).
        fecha_inicio: Inicio de la ventana de sesiones.
        fecha_fin: Fin de la ventana de sesiones (incluye esta fecha).
        frecuencia: Clave de frecuencia (ej. "SEMANAL", "MENSUAL").
        grupos_ids: Lista de IDs de grupos a generar.

    Returns:
        Número total de sesiones creadas (nuevas, no duplicadas).
    """
    delta = _delta_para_frecuencia(frecuencia)

    inicio_utc = _a_utc(fecha_inicio)
    fin_utc = _a_utc(fecha_fin)

    fechas = _generar_fechas(inicio_utc, fin_utc, delta)

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


# ──────────────────────────────────────────────
# Alias de back-compat
# ──────────────────────────────────────────────
proyectar_sesiones = calcular_sesiones
