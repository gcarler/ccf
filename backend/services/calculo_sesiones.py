"""Algoritmo de Cálculo de Sesiones — Genera sesiones PENDIENTES para todos
los grupos de una estrategia de evangelismo según su frecuencia y ventana de
fechas (inicio-fin).

Reglas de calidad aplicadas:
1. Validación de frecuencia soportada (ValueError si no coincide).
2. Normalización de timezone a UTC para evitar sesgos por huso.
3. Protección contra incremento cero (bucle infinito).
4. Validación fecha_inicio <= fecha_fin.
5. Cada sesión se compara con deleted_at IS NULL para evitar duplicados.
6. Cada iteración genera una sesión por grupo por fecha.
7. Frecuencias basadas en meses (MENSUAL, TRIMESTRAL, etc.) usan
   relativedelta para respetar los meses calendario reales.
8. Preservación del día original: si la estrategia empieza el 31 de enero,
   las sesiones serán: 31 ene → 28 feb → 31 mar → 30 abr → ..., no se
   desfasan por truncamiento.
"""

from __future__ import annotations

import calendar
from datetime import datetime, timedelta, timezone
from typing import List, Union
import uuid
import unicodedata

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from backend.models_evangelism import GrupoEvangelismo, SesionGrupo, FrecuenciaEnum

# ──────────────────────────────────────────────
# Estrategia de incremento
# ──────────────────────────────────────────────
# SEMANAL / QUINCENAL → timedelta (siempre exacto).
# MENSUAL / TRIMESTRAL / etc. → relativedelta con preservación del día
# original. Ej: si la estrategia empieza el 31 de enero, febrero se
# trunca al 28, pero marzo vuelve al 31.
# ──────────────────────────────────────────────

_IncT = Union[timedelta, relativedelta]


class _IncProvider:
    """Provee el incremento y la estrategia de generación para una frecuencia."""

    def __init__(self, incremento: _IncT, dia_original: int | None = None) -> None:
        self.incremento = incremento
        self.dia_original = dia_original  # None para timedelta, int para relativedelta

    def saltar(self, dt: datetime) -> datetime:
        """Avanza dt según el incremento, preservando el día original si aplica."""
        siguiente = dt + self.incremento
        if self.dia_original is not None and siguiente.day != self.dia_original:
            # El día se truncó (ej: 31 → 28 en febrero),
            # lo corregimos al próximo mes con ese día
            ultimo = calendar.monthrange(siguiente.year, siguiente.month)[1]
            siguiente = siguiente.replace(day=min(self.dia_original, ultimo))
        return siguiente


_FRECUENCIA_A_PROVIDER: dict[str, _IncProvider] = {
    FrecuenciaEnum.SEMANAL.value: _IncProvider(timedelta(weeks=1)),
    FrecuenciaEnum.QUINCENAL.value: _IncProvider(timedelta(weeks=2)),
    FrecuenciaEnum.MENSUAL.value: _IncProvider(relativedelta(months=1), dia_original=True),
    FrecuenciaEnum.BIMENSUAL.value: _IncProvider(relativedelta(months=2), dia_original=True),
    FrecuenciaEnum.TRIMESTRAL.value: _IncProvider(relativedelta(months=3), dia_original=True),
    FrecuenciaEnum.SEMESTRAL.value: _IncProvider(relativedelta(months=6), dia_original=True),
    FrecuenciaEnum.ANUAL.value: _IncProvider(relativedelta(years=1), dia_original=True),
    FrecuenciaEnum.EVENTO_UNICO.value: _IncProvider(timedelta.max),
    # Back-compat: datos compat
    "Semanal": _IncProvider(timedelta(weeks=1)),
    "Quincenal": _IncProvider(timedelta(weeks=2)),
    "Mensual": _IncProvider(relativedelta(months=1), dia_original=True),
    "Bimensual": _IncProvider(relativedelta(months=2), dia_original=True),
    "Trimestral": _IncProvider(relativedelta(months=3), dia_original=True),
    "Semestral": _IncProvider(relativedelta(months=6), dia_original=True),
    "Anual": _IncProvider(relativedelta(years=1), dia_original=True),
}


def _normalizar_frecuencia(frecuencia: str) -> str:
    """Convierte aliases humanos/compat a la clave canonica del enum."""
    if not str(frecuencia or "").strip():
        raise ValueError("La frecuencia es obligatoria.")
    normalized = unicodedata.normalize("NFKD", str(frecuencia).strip())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "SEMANAL": FrecuenciaEnum.SEMANAL.value,
        "QUINCENAL": FrecuenciaEnum.QUINCENAL.value,
        "MENSUAL": FrecuenciaEnum.MENSUAL.value,
        "BIMENSUAL": FrecuenciaEnum.BIMENSUAL.value,
        "TRIMESTRAL": FrecuenciaEnum.TRIMESTRAL.value,
        "SEMESTRAL": FrecuenciaEnum.SEMESTRAL.value,
        "ANUAL": FrecuenciaEnum.ANUAL.value,
        "EVENTO_UNICO": FrecuenciaEnum.EVENTO_UNICO.value,
        "EVENTO_UNICA": FrecuenciaEnum.EVENTO_UNICO.value,
        "UNICA": FrecuenciaEnum.EVENTO_UNICO.value,
        "UNICO": FrecuenciaEnum.EVENTO_UNICO.value,
    }
    return aliases.get(normalized, normalized)


def _provider_para_frecuencia(frecuencia: str, dia_original: int) -> _IncProvider:
    """Retorna el provider de incremento para una frecuencia.

    El ``dia_original`` se inyecta en el provider cuando usa relativedelta,
    para que preserve el día correcto (ej: 31 ene → 28 feb → 31 mar).

    Raises:
        ValueError: si la frecuencia no está soportada.
    """
    frecuencia_canonica = _normalizar_frecuencia(frecuencia)
    p = _FRECUENCIA_A_PROVIDER.get(frecuencia_canonica)
    if p is None:
        soportadas = ", ".join([e.value for e in FrecuenciaEnum])
        raise ValueError(
            f"Frecuencia no soportada: '{frecuencia}'. "
            f"Soportadas: {soportadas}"
        )
    # Clonar con el día original correcto
    return _IncProvider(p.incremento, dia_original if p.dia_original else None)


def _a_utc(dt: datetime) -> datetime:
    """Asegura que el datetime tenga timezone UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _generar_fechas(inicio: datetime, fin: datetime, provider: _IncProvider) -> List[datetime]:
    """Genera lista de fechas desde inicio hasta fin saltando por incremento.

    Soporta tanto timedelta (SEMANAL, QUINCENAL) como relativedelta con
    preservación del día original (MENSUAL, TRIMESTRAL, etc.).

    Raises:
        ValueError: si el incremento es cero o negativo (solo timedelta).
        ValueError: si inicio > fin.
    """
    if inicio > fin:
        raise ValueError("La fecha de inicio no puede ser posterior a la fecha de fin.")
    if provider.incremento == timedelta.max:
        return [inicio]
    if isinstance(provider.incremento, timedelta) and provider.incremento.total_seconds() <= 0:
        raise ValueError("El intervalo de frecuencia debe ser mayor a cero.")

    fechas: List[datetime] = []
    current = inicio
    while current <= fin:
        fechas.append(current)
        current = provider.saltar(current)
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
    inicio_utc = _a_utc(fecha_inicio)
    fin_utc = _a_utc(fecha_fin)
    provider = _provider_para_frecuencia(frecuencia, inicio_utc.day)

    fechas = _generar_fechas(inicio_utc, fin_utc, provider)

    if not fechas or not grupos_ids:
        return 0

    valid_group_ids = {
        row[0]
        for row in (
            db.query(GrupoEvangelismo.id)
            .filter(
                GrupoEvangelismo.id.in_(grupos_ids),
                GrupoEvangelismo.estrategia_id == str(estrategia_id),
                GrupoEvangelismo.sede_id == sede_id,
                GrupoEvangelismo.deleted_at.is_(None),
            )
            .all()
        )
    }
    grupos_validos = [grupo_id for grupo_id in grupos_ids if grupo_id in valid_group_ids]
    if not grupos_validos:
        return 0

    existing_pairs = {
        (grupo_id, _a_utc(fecha))
        for grupo_id, fecha in (
            db.query(SesionGrupo.grupo_id, SesionGrupo.fecha_sesion)
            .filter(
                SesionGrupo.grupo_id.in_(grupos_validos),
                SesionGrupo.deleted_at.is_(None),
            )
            .all()
        )
    }

    created = 0
    for grupo_id in grupos_validos:
        for fecha in fechas:
            if (grupo_id, _a_utc(fecha)) not in existing_pairs:
                db.add(
                    SesionGrupo(
                        grupo_id=grupo_id,
                        fecha_sesion=fecha,
                        estado="PENDIENTE",
                    )
                )
                created += 1

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return created


# ──────────────────────────────────────────────
# Alias de back-compat
# ──────────────────────────────────────────────
proyectar_sesiones = calcular_sesiones
