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
from typing import TYPE_CHECKING, Iterable
from uuid import UUID

from dateutil.rrule import rrulestr

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

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


def check_space_collision(
    db: Session,
    sede_id: UUID,
    room_id: UUID,
    start_at: datetime,
    end_at: datetime,
    recurrence_rule: str | None = None,
    recurrence_until: datetime | None = None,
    recurrence_exceptions: list[str] | None = None,
    exclude_event_id: UUID | None = None,
) -> dict | None:
    """Detecta colisiones de reserva para un salón / espacio físico en la misma sede.

    Evalúa tanto eventos únicos como series recurrentes (RFC 5545), respetando
    excepciones de recurrencia y asegurando que las reservas físicas no se solapen.
    Devuelve un diccionario con el detalle del evento en conflicto si hay colisión,
    o None si el espacio físico se encuentra disponible.
    """
    from backend.models_agenda import EventoAgenda, ReservaRecurso

    start_utc = _as_utc(start_at)
    end_utc = _as_utc(end_at or start_at)
    if end_utc <= start_utc:
        end_utc = start_utc + timedelta(hours=1)

    # 1. Expandir ocurrencias del evento propuesto
    mock_event = type(
        "ProposedEvent",
        (),
        {
            "id": None,
            "fecha_inicio": start_utc,
            "fecha_fin": end_utc,
            "regla_recurrencia": recurrence_rule,
            "fecha_limite_recurrencia": recurrence_until,
            "excepciones_recurrencia": recurrence_exceptions or [],
        },
    )()

    if recurrence_rule and recurrence_rule.strip():
        window_start = start_utc
        window_end = _as_utc(recurrence_until) if recurrence_until else start_utc + timedelta(days=365)
        proposed_occurrences = expand_event(mock_event, window_start, window_end)
        if not proposed_occurrences:
            exc_days = {str(d)[:10] for d in (recurrence_exceptions or [])}
            if start_utc.date().isoformat() not in exc_days:
                proposed_occurrences = [(start_utc, end_utc)]
    else:
        proposed_occurrences = [(start_utc, end_utc)]

    if not proposed_occurrences:
        return None

    global_min_start = min(occ[0] for occ in proposed_occurrences)
    global_max_end = max(occ[1] for occ in proposed_occurrences)

    # 2. Consultar eventos y reservas existentes para room_id en la misma sede
    query = (
        db.query(ReservaRecurso)
        .join(EventoAgenda, ReservaRecurso.evento_id == EventoAgenda.id)
        .filter(
            ReservaRecurso.recurso_id == room_id,
            ReservaRecurso.deleted_at.is_(None),
            EventoAgenda.sede_id == sede_id,
            EventoAgenda.deleted_at.is_(None),
            EventoAgenda.estado != "CANCELADO",
        )
    )
    if exclude_event_id is not None:
        query = query.filter(ReservaRecurso.evento_id != exclude_event_id)

    reservations = query.all()

    # 3. Evaluar colisiones contra cada reserva / evento activo
    for res in reservations:
        event = res.evento
        if not event or event.deleted_at is not None or event.estado == "CANCELADO":
            continue

        if event.regla_recurrencia and event.regla_recurrencia.strip():
            cand_occurrences = expand_event(event, global_min_start, global_max_end)
            for cand_start, cand_end in cand_occurrences:
                for prop_start, prop_end in proposed_occurrences:
                    if prop_start < cand_end and prop_end > cand_start:
                        return {
                            "conflict": True,
                            "conflict_event_id": str(event.id),
                            "conflict_event_title": event.titulo,
                            "conflict_start": cand_start.isoformat(),
                            "conflict_end": cand_end.isoformat(),
                            "room_id": str(room_id),
                            "message": (
                                f"Conflicto de reserva: el espacio ya está reservado por el evento "
                                f"'{event.titulo}' ({cand_start.strftime('%Y-%m-%d %H:%M')} - "
                                f"{cand_end.strftime('%H:%M')} UTC)"
                            ),
                        }
        else:
            cand_start = _as_utc(res.bloqueo_inicio or event.fecha_inicio)
            cand_end = _as_utc(res.bloqueo_fin or event.fecha_fin or cand_start)
            for prop_start, prop_end in proposed_occurrences:
                if prop_start < cand_end and prop_end > cand_start:
                    return {
                        "conflict": True,
                        "conflict_event_id": str(event.id),
                        "conflict_event_title": event.titulo,
                        "conflict_start": cand_start.isoformat(),
                        "conflict_end": cand_end.isoformat(),
                        "room_id": str(room_id),
                        "message": (
                            f"Conflicto de reserva: el espacio ya está reservado por el evento "
                            f"'{event.titulo}' ({cand_start.strftime('%Y-%m-%d %H:%M')} - "
                            f"{cand_end.strftime('%H:%M')} UTC)"
                        ),
                    }

    return None
