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
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Union
from uuid import UUID

from dateutil.relativedelta import relativedelta
from sqlalchemy import MetaData, Table, insert
from sqlalchemy.orm import Session

from backend.models_evangelism import FrecuenciaEnum, GrupoEvangelismo, SesionGrupo
from backend.api.evangelism_shared import _sessions_grupo_live_column_names

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
    # Valores escritos por formularios historicos
    "Semanal": _IncProvider(timedelta(weeks=1)),
    "Quincenal": _IncProvider(timedelta(weeks=2)),
    "Mensual": _IncProvider(relativedelta(months=1), dia_original=True),
    "Bimensual": _IncProvider(relativedelta(months=2), dia_original=True),
    "Trimestral": _IncProvider(relativedelta(months=3), dia_original=True),
    "Semestral": _IncProvider(relativedelta(months=6), dia_original=True),
    "Anual": _IncProvider(relativedelta(years=1), dia_original=True),
}


def _normalizar_frecuencia(frecuencia: str) -> str:
    """Convierte variantes humanas a la clave canonica del enum."""
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
    estrategia_id: UUID,
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
                GrupoEvangelismo.estrategia_id == estrategia_id,
                GrupoEvangelismo.sede_id == sede_id,
                GrupoEvangelismo.deleted_at.is_(None),
            )
            .all()
        )
    }
    grupos_validos = [grupo_id for grupo_id in grupos_ids if grupo_id in valid_group_ids]
    if not grupos_validos:
        return 0

    live_columns = _sessions_grupo_live_column_names(db)
    reflected_table = None
    if db.get_bind() is not None:
        reflected_table = Table(
            "sesiones_grupo",
            MetaData(),
            autoload_with=db.get_bind(),
        )

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
    rows_to_insert: list[dict] = []
    for grupo_id in grupos_validos:
        for fecha in fechas:
            if (grupo_id, _a_utc(fecha)) not in existing_pairs:
                row = {
                    "id": uuid.uuid4(),
                    "grupo_id": grupo_id,
                    "fecha_sesion": fecha,
                    "estado": "PENDIENTE",
                }
                if "estado_habilitacion" in live_columns:
                    row["estado_habilitacion"] = "DESHABILITADO"
                if "created_at" in live_columns:
                    row["created_at"] = datetime.now(timezone.utc)
                if "deleted_at" in live_columns:
                    row["deleted_at"] = None
                if "reported_at" in live_columns:
                    row["reported_at"] = None
                if "habilitado_por" in live_columns:
                    row["habilitado_por"] = None
                if "habilitado_en" in live_columns:
                    row["habilitado_en"] = None
                if "motivo_cancelacion" in live_columns:
                    row["motivo_cancelacion"] = None
                if "tema_estudio" in live_columns:
                    row["tema_estudio"] = None
                if "notas_lider" in live_columns:
                    row["notas_lider"] = None
                if "offering_amount" in live_columns:
                    row["offering_amount"] = None
                if "season_id" in live_columns:
                    row["season_id"] = None
                if "novelty_type" in live_columns:
                    row["novelty_type"] = None
                if "novelty_detail" in live_columns:
                    row["novelty_detail"] = None
                if "reported_by_persona_id" in live_columns:
                    row["reported_by_persona_id"] = None
                if "report_deadline" in live_columns:
                    row["report_deadline"] = None
                rows_to_insert.append({k: v for k, v in row.items() if k in live_columns})
                created += 1

    try:
        if rows_to_insert:
            if reflected_table is None:
                raise RuntimeError("Cannot reflect sesiones_grupo table for insert")
            db.execute(insert(reflected_table), rows_to_insert)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return created


# ──────────────────────────────────────────────
# Nombre publico usado por el servicio de proyeccion
# ──────────────────────────────────────────────
proyectar_sesiones = calcular_sesiones
