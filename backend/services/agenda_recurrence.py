"""Recurrencia RFC 5545 para la Agenda CCF.

Un ``EventoAgenda`` con ``regla_recurrencia`` (RRULE) actúa como **serie**: las
ocurrencias se expanden sobre la ventana consultada, derivando cada instancia
del ancla (``fecha_inicio`` / ``fecha_fin``). El ancla es también la primera
ocurrencia de la serie.

Límites defensivos (anti-abuso / anti-DoS):

- ``MAX_SERIES_LOOKBACK_DAYS``: una serie cuyo ancla sea anterior a la ventana
  menos este lookback no se expande (evita expandir series históricas
  ilimitadas en agregadores sin ventana).
- ``MAX_OCCURRENCES_PER_SERIES``: techo duro de ocurrencias por serie y
  ventana, aunque la RRULE declare ``COUNT`` mayores o no tenga ``UNTIL``.

Excepciones: ``excepciones_recurrencia`` guarda fechas ISO (``YYYY-MM-DD``,
día de inicio de la ocurrencia en UTC) que se omiten en la expansión.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Iterable

from dateutil.rrule import rrulestr

logger = logging.getLogger(__name__)

MAX_SERIES_LOOKBACK_DAYS = 730
MAX_OCCURRENCES_PER_SERIES = 500


def validate_rrule(value: str) -> str:
    """Normaliza y valida una RRULE RFC 5545.

    Acepta con o sin el prefijo ``RRULE:`` y lo devuelve siempre presente.
    Lanza ``ValueError`` si la regla no parsea o declara un ``COUNT`` por
    encima del techo de expansión.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError("regla_recurrencia vacía")
    rule = value.strip().upper()
    if not rule.startswith("RRULE:"):
        rule = f"RRULE:{rule}"
    if ";" not in rule and ":" in rule and "=" not in rule.split(":", 1)[1]:
        raise ValueError("RRULE sin cláusulas (ej. RRULE:FREQ=WEEKLY)")

    dtstart = datetime(2020, 1, 1, tzinfo=timezone.utc)
    try:
        parsed = rrulestr(rule, dtstart=dtstart)
    except (ValueError, TypeError, KeyError) as exc:
        raise ValueError(f"RRULE inválida: {exc}") from exc

    rules = getattr(parsed, "_rrule", [parsed])
    for r in rules:
        count = getattr(r, "_count", None)
        if count and count > MAX_OCCURRENCES_PER_SERIES:
            raise ValueError(
                f"COUNT no puede exceder {MAX_OCCURRENCES_PER_SERIES} ocurrencias"
            )
    return rule


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def expand_event(
    row,
    window_start: datetime,
    window_end: datetime,
) -> list[tuple[datetime, datetime]]:
    """Expande una serie dentro de ``[window_start, window_end]``.

    Devuelve pares ``(inicio_ocurrencia, fin_ocurrencia)`` en UTC, ordenados.
    El ancla anterior a ``window_start - MAX_SERIES_LOOKBACK_DAYS`` no se
    expande (regla anti-expansión-ilimitada). Una RRULE que no parsea se
    registra y devuelve lista vacía (la API nunca debe romper por datos
    heredados corruptos).
    """
    window_start = _as_utc(window_start)
    window_end = _as_utc(window_end)

    anchor_start = _as_utc(row.fecha_inicio)
    anchor_end = _as_utc(row.fecha_fin or row.fecha_inicio)
    duration = anchor_end - anchor_start
    if duration < timedelta(0):
        duration = timedelta(0)

    earliest = window_start - timedelta(days=MAX_SERIES_LOOKBACK_DAYS)
    if anchor_start < earliest:
        logger.info(
            "Serie %s omitida: ancla %s anterior al lookback de %s días",
            row.id,
            anchor_start.isoformat(),
            MAX_SERIES_LOOKBACK_DAYS,
        )
        return []

    rule_text = (row.regla_recurrencia or "").strip()
    if not rule_text.upper().startswith("RRULE:"):
        rule_text = f"RRULE:{rule_text}"

    try:
        rule = rrulestr(rule_text, dtstart=anchor_start)
    except (ValueError, TypeError, KeyError) as exc:
        logger.warning("RRULE inválida en evento %s: %s", row.id, exc)
        return []

    exceptions: Iterable[str] = row.excepciones_recurrencia or []
    exception_days = {str(day)[:10] for day in exceptions}

    # Una ocurrencia que empezó antes de la ventana puede cruzar hacia dentro
    # (duración > 0); por eso el corte superior es window_end + duration.
    limit = window_end + duration

    occurrences: list[tuple[datetime, datetime]] = []
    for dt in rule:
        if dt > limit:
            break
        occ_start = _as_utc(dt)
        occ_end = occ_start + duration
        if occ_end < window_start or occ_start > window_end:
            continue
        if occ_start.date().isoformat() in exception_days:
            continue
        occurrences.append((occ_start, occ_end))
        if len(occurrences) >= MAX_OCCURRENCES_PER_SERIES:
            logger.warning(
                "Serie %s truncada al techo de %s ocurrencias",
                row.id,
                MAX_OCCURRENCES_PER_SERIES,
            )
            break
    return occurrences


def occurrence_start_for(row, occurrence_date: str) -> datetime | None:
    """Devuelve el inicio de la ocurrencia cuya fecha (UTC) es ``occurrence_date``.

    Usa exactamente la misma expansión que la lectura, garantizando que sólo
    se pueda editar/eliminar una ocurrencia que la serie realmente emite y
    que no esté ya exceptuada. Devuelve ``None`` si la fecha no corresponde
    a ninguna ocurrencia vigente.
    """
    raw = str(occurrence_date or "")[:10]
    try:
        target = date.fromisoformat(raw)
    except ValueError:
        return None

    window_start = datetime(target.year, target.month, target.day, tzinfo=timezone.utc) - timedelta(days=1)
    window_end = window_start + timedelta(days=3)
    for occ_start, _occ_end in expand_event(row, window_start, window_end):
        if occ_start.date() == target:
            return occ_start
    return None


def add_exception(row, occurrence_date: str) -> list[str]:
    """Agrega ``occurrence_date`` (YYYY-MM-DD) a las excepciones de la serie.

    Normaliza y deduplica; devuelve la lista nueva sin mutar la fila.
    """
    target = str(occurrence_date or "")[:10]
    date.fromisoformat(target)  # ValueError si la fecha es inválida
    exceptions = {str(day)[:10] for day in (row.excepciones_recurrencia or [])}
    exceptions.add(target)
    return sorted(exceptions)
