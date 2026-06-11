"""
Evangelism Strategy Analytics API
==================================
Endpoints:
  GET /analytics/strategy/{strategy_id}           — KPIs generales + resumen de grupos
  GET /analytics/strategy/{strategy_id}/trend     — Tendencia de asistencia en el tiempo
  GET /analytics/strategy/{strategy_id}/funnel    — Embudo de conversión de roles
  GET /analytics/strategy/{strategy_id}/heatmap   — Asistencia por día de la semana
  GET /analytics/strategy/{strategy_id}/alerts    — Alertas tempranas (grupos y personas)
  GET /analytics/strategy/{strategy_id}/velocity  — Velocidad de cambio de roles (embudo ministerial)
  GET /analytics/strategy/{strategy_id}/groups    — Grupos con mini-métricas detalladas
"""
from __future__ import annotations

import datetime as _dt
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func as _func
from sqlalchemy.orm import Session

from backend import models
from backend.api.evangelism_shared import ATTENDED_STATES
from backend.auth import require_active_user
from backend.core.database import get_db
from backend.core.tenant import require_user_sede_id

router = APIRouter()

# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

_PERIOD_DAYS = {"7d": 7, "30d": 30, "90d": 90, "180d": 180, "365d": 365}


def _parse_period(period: str) -> int:
    return _PERIOD_DAYS.get(period, 30)


def _date_range(days: int):
    now = _dt.datetime.now(_dt.timezone.utc)
    start = now - _dt.timedelta(days=days)
    return start, now


def _prev_range(days: int):
    now = _dt.datetime.now(_dt.timezone.utc)
    end = now - _dt.timedelta(days=days)
    start = end - _dt.timedelta(days=days)
    return start, end


def _get_strategy_or_404(db: Session, strategy_id: str, sede_id):
    s = db.query(models.EstrategiaEvangelismo).filter(
        models.EstrategiaEvangelismo.id == strategy_id,
        models.EstrategiaEvangelismo.deleted_at.is_(None),
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Estrategia no encontrada")
    return s


def _group_ids_for_strategy(db: Session, strategy_id: str, sede_id) -> list[int]:
    q = db.query(models.GrupoEvangelismo.id).filter(
        models.GrupoEvangelismo.estrategia_id == strategy_id,
        models.GrupoEvangelismo.deleted_at.is_(None),
    )
    if sede_id is not None:
        q = q.filter(models.GrupoEvangelismo.sede_id == sede_id)
    return [r[0] for r in q.all()]


def _delta(current: float, previous: float) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def _attendance_stats(db: Session, group_ids: list[int], start, end) -> tuple[int, int]:
    """Returns (present, total) attendance counts."""
    if not group_ids:
        return 0, 0
    rows = (
        db.query(models.Asistencia.estado)
        .join(models.SesionGrupo, models.Asistencia.sesion_id == models.SesionGrupo.id)
        .filter(
            models.SesionGrupo.grupo_id.in_(group_ids),
            models.SesionGrupo.fecha_sesion >= start,
            models.SesionGrupo.fecha_sesion < end,
            models.Asistencia.deleted_at.is_(None),
            models.SesionGrupo.deleted_at.is_(None),
        )
        .all()
    )
    present = sum(1 for (e,) in rows if e in ATTENDED_STATES)
    return present, len(rows)


# ─────────────────────────────────────────────────────────
# GET /analytics/strategy/{strategy_id}  — KPIs principales
# ─────────────────────────────────────────────────────────

@router.get("/analytics/strategy/{strategy_id}")
def strategy_kpis(
    strategy_id: str,
    period: str = Query("30d"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    sede_id = require_user_sede_id(db, current_user)
    _get_strategy_or_404(db, strategy_id, sede_id)
    group_ids = _group_ids_for_strategy(db, strategy_id, sede_id)

    days = _parse_period(period)
    start, end = _date_range(days)
    prev_start, prev_end = _prev_range(days)

    # ── Asistencia ──
    present, total = _attendance_stats(db, group_ids, start, end)
    prev_present, prev_total = _attendance_stats(db, group_ids, prev_start, prev_end)
    att_pct = round((present / total) * 100, 1) if total else 0.0
    prev_att_pct = round((prev_present / prev_total) * 100, 1) if prev_total else 0.0

    # ── Participantes activos ──
    active_members = 0
    prev_active_members = 0
    if group_ids:
        active_members = (
            db.query(_func.count(models.ParticipanteGrupo.id))
            .filter(
                models.ParticipanteGrupo.grupo_id.in_(group_ids),
                models.ParticipanteGrupo.activo.is_(True),
                models.ParticipanteGrupo.deleted_at.is_(None),
                models.ParticipanteGrupo.fecha_ingreso < end,
            )
            .scalar() or 0
        )
        prev_active_members = (
            db.query(_func.count(models.ParticipanteGrupo.id))
            .filter(
                models.ParticipanteGrupo.grupo_id.in_(group_ids),
                models.ParticipanteGrupo.activo.is_(True),
                models.ParticipanteGrupo.deleted_at.is_(None),
                models.ParticipanteGrupo.fecha_ingreso < prev_end,
            )
            .scalar() or 0
        )

    # ── Sesiones ──
    sessions_done = sessions_total = prev_sessions_done = 0
    if group_ids:
        sessions_done = (
            db.query(_func.count(models.SesionGrupo.id))
            .filter(
                models.SesionGrupo.grupo_id.in_(group_ids),
                models.SesionGrupo.estado == "REALIZADA",
                models.SesionGrupo.fecha_sesion >= start,
                models.SesionGrupo.fecha_sesion < end,
                models.SesionGrupo.deleted_at.is_(None),
            )
            .scalar() or 0
        )
        sessions_total = (
            db.query(_func.count(models.SesionGrupo.id))
            .filter(
                models.SesionGrupo.grupo_id.in_(group_ids),
                models.SesionGrupo.fecha_sesion >= start,
                models.SesionGrupo.fecha_sesion < end,
                models.SesionGrupo.deleted_at.is_(None),
            )
            .scalar() or 0
        )
        prev_sessions_done = (
            db.query(_func.count(models.SesionGrupo.id))
            .filter(
                models.SesionGrupo.grupo_id.in_(group_ids),
                models.SesionGrupo.estado == "REALIZADA",
                models.SesionGrupo.fecha_sesion >= prev_start,
                models.SesionGrupo.fecha_sesion < prev_end,
                models.SesionGrupo.deleted_at.is_(None),
            )
            .scalar() or 0
        )

    # ── Nuevos ingresos en el período ──
    new_joiners = prev_new_joiners = 0
    if group_ids:
        new_joiners = (
            db.query(_func.count(models.ParticipanteGrupo.id))
            .filter(
                models.ParticipanteGrupo.grupo_id.in_(group_ids),
                models.ParticipanteGrupo.fecha_ingreso >= start,
                models.ParticipanteGrupo.fecha_ingreso < end,
                models.ParticipanteGrupo.deleted_at.is_(None),
            )
            .scalar() or 0
        )
        prev_new_joiners = (
            db.query(_func.count(models.ParticipanteGrupo.id))
            .filter(
                models.ParticipanteGrupo.grupo_id.in_(group_ids),
                models.ParticipanteGrupo.fecha_ingreso >= prev_start,
                models.ParticipanteGrupo.fecha_ingreso < prev_end,
                models.ParticipanteGrupo.deleted_at.is_(None),
            )
            .scalar() or 0
        )

    # ── Grupos activos ──
    active_groups = len(group_ids)
    groups_with_sessions = 0
    if group_ids:
        groups_with_sessions = (
            db.query(_func.count(_func.distinct(models.SesionGrupo.grupo_id)))
            .filter(
                models.SesionGrupo.grupo_id.in_(group_ids),
                models.SesionGrupo.fecha_sesion >= start,
                models.SesionGrupo.fecha_sesion < end,
                models.SesionGrupo.deleted_at.is_(None),
            )
            .scalar() or 0
        )

    # ── Retención: personas que estaban en prev y siguen en current ──
    retention_pct = 0.0
    if group_ids and prev_active_members > 0:
        still_active = active_members
        retention_pct = round(min((still_active / prev_active_members) * 100, 100.0), 1)

    return {
        "period": period,
        "group_ids": group_ids,
        "kpis": {
            "active_members": {
                "value": active_members,
                "delta": _delta(active_members, prev_active_members),
            },
            "attendance_pct": {
                "value": att_pct,
                "delta": round(att_pct - prev_att_pct, 1),
            },
            "sessions": {
                "done": sessions_done,
                "total": sessions_total,
                "prev_done": prev_sessions_done,
                "completion_pct": round((sessions_done / sessions_total) * 100, 1) if sessions_total else 0.0,
            },
            "retention_pct": {
                "value": retention_pct,
                "delta": 0.0,
            },
            "new_joiners": {
                "value": new_joiners,
                "delta": _delta(new_joiners, prev_new_joiners),
            },
            "active_groups": {
                "value": active_groups,
                "with_sessions": groups_with_sessions,
            },
        },
    }


# ─────────────────────────────────────────────────────────
# GET /analytics/strategy/{strategy_id}/trend
# ─────────────────────────────────────────────────────────

@router.get("/analytics/strategy/{strategy_id}/trend")
def strategy_trend(
    strategy_id: str,
    period: str = Query("90d"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    sede_id = require_user_sede_id(db, current_user)
    _get_strategy_or_404(db, strategy_id, sede_id)
    group_ids = _group_ids_for_strategy(db, strategy_id, sede_id)
    if not group_ids:
        return {"buckets": [], "groups": []}

    days = _parse_period(period)
    start, end = _date_range(days)
    use_weeks = days <= 90

    groups = (
        db.query(models.GrupoEvangelismo)
        .filter(models.GrupoEvangelismo.id.in_(group_ids))
        .all()
    )

    # Fetch all sessions + attendance in range
    rows = (
        db.query(
            models.SesionGrupo.grupo_id,
            models.SesionGrupo.fecha_sesion,
            models.Asistencia.estado,
        )
        .join(models.Asistencia, models.Asistencia.sesion_id == models.SesionGrupo.id)
        .filter(
            models.SesionGrupo.grupo_id.in_(group_ids),
            models.SesionGrupo.fecha_sesion >= start,
            models.SesionGrupo.fecha_sesion < end,
            models.SesionGrupo.deleted_at.is_(None),
            models.Asistencia.deleted_at.is_(None),
        )
        .all()
    )

    def _bucket_key(dt: _dt.datetime) -> str:
        if use_weeks:
            # ISO week: "2026-W23"
            return dt.strftime("%G-W%V")
        return dt.strftime("%Y-%m")

    # Aggregate per bucket per group
    # structure: {bucket_key: {group_id: {present, total}}}
    agg: dict[str, dict[int, dict]] = defaultdict(lambda: defaultdict(lambda: {"p": 0, "t": 0}))
    for grupo_id, fecha, estado in rows:
        key = _bucket_key(fecha)
        agg[key][grupo_id]["t"] += 1
        if estado in ATTENDED_STATES:
            agg[key][grupo_id]["p"] += 1

    # Also global bucket
    global_agg: dict[str, dict] = defaultdict(lambda: {"p": 0, "t": 0})
    for grupo_id, fecha, estado in rows:
        key = _bucket_key(fecha)
        global_agg[key]["t"] += 1
        if estado in ATTENDED_STATES:
            global_agg[key]["p"] += 1

    # Build sorted bucket list
    all_keys = sorted(set(agg.keys()))

    def _pct(p, t):
        return round((p / t) * 100, 1) if t else None

    buckets = []
    for key in all_keys:
        g_data = global_agg[key]
        entry = {
            "key": key,
            "label": _bucket_label(key, use_weeks),
            "avg_pct": _pct(g_data["p"], g_data["t"]),
            "present": g_data["p"],
            "total": g_data["t"],
        }
        for g in groups:
            gd = agg[key].get(g.id, {"p": 0, "t": 0})
            entry[f"g_{g.id}"] = _pct(gd["p"], gd["t"])
        buckets.append(entry)

    return {
        "buckets": buckets,
        "groups": [{"id": g.id, "name": g.nombre} for g in groups],
    }


def _bucket_label(key: str, use_weeks: bool) -> str:
    if use_weeks:
        # "2026-W23" → "Sem 23"
        parts = key.split("-W")
        return f"Sem {parts[1]}" if len(parts) == 2 else key
    # "2026-03" → "Mar 26"
    _months = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    try:
        year, month = key.split("-")
        return f"{_months[int(month)]} {year[2:]}"
    except Exception:
        return key


# ─────────────────────────────────────────────────────────
# GET /analytics/strategy/{strategy_id}/funnel
# ─────────────────────────────────────────────────────────

@router.get("/analytics/strategy/{strategy_id}/funnel")
def strategy_funnel(
    strategy_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    sede_id = require_user_sede_id(db, current_user)
    _get_strategy_or_404(db, strategy_id, sede_id)
    group_ids = _group_ids_for_strategy(db, strategy_id, sede_id)

    # Count active participants by rol_base
    role_counts: dict[str, int] = {}
    if group_ids:
        rows = (
            db.query(models.ParticipanteGrupo.rol_base, _func.count(models.ParticipanteGrupo.id))
            .filter(
                models.ParticipanteGrupo.grupo_id.in_(group_ids),
                models.ParticipanteGrupo.activo.is_(True),
                models.ParticipanteGrupo.deleted_at.is_(None),
            )
            .group_by(models.ParticipanteGrupo.rol_base)
            .all()
        )
        role_counts = {r.lower(): c for r, c in rows}

    # Canonical funnel stages (order matters — top to bottom)
    STAGES = [
        {"key": "visitante",  "label": "Visitante",    "roles": ["visitante", "invitado"]},
        {"key": "asistente",  "label": "Asistente",    "roles": ["asistente"]},
        {"key": "anfitrion",  "label": "Anfitrión",    "roles": ["anfitrion"]},
        {"key": "colider",    "label": "Colíder",      "roles": ["colider"]},
        {"key": "lider",      "label": "Líder",        "roles": ["lider"]},
    ]

    total_top = sum(role_counts.get(r, 0) for r in STAGES[0]["roles"])

    # Average days per role transition from HistorialEmbudo
    velocity_rows = (
        db.query(
            models.HistorialEmbudo.rol_nuevo,
            _func.avg(models.HistorialEmbudo.dias_en_estado_anterior),
        )
        .filter(models.HistorialEmbudo.deleted_at.is_(None))
        .group_by(models.HistorialEmbudo.rol_nuevo)
        .all()
    )
    velocity_map = {r.lower(): round(float(d), 0) for r, d in velocity_rows if d is not None}

    stages = []
    running_total = 0
    for stage in STAGES:
        count = sum(role_counts.get(r, 0) for r in stage["roles"])
        running_total += count
        pct_of_top = round((count / total_top) * 100, 1) if total_top else 0.0
        avg_days = velocity_map.get(stage["key"])
        stages.append({
            "key": stage["key"],
            "label": stage["label"],
            "count": count,
            "pct_of_top": pct_of_top,
            "avg_days_before": avg_days,
        })

    return {
        "total_active": running_total,
        "stages": stages,
    }


# ─────────────────────────────────────────────────────────
# GET /analytics/strategy/{strategy_id}/heatmap
# ─────────────────────────────────────────────────────────

@router.get("/analytics/strategy/{strategy_id}/heatmap")
def strategy_heatmap(
    strategy_id: str,
    period: str = Query("90d"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    sede_id = require_user_sede_id(db, current_user)
    _get_strategy_or_404(db, strategy_id, sede_id)
    group_ids = _group_ids_for_strategy(db, strategy_id, sede_id)
    if not group_ids:
        return {"cells": []}

    days = _parse_period(period)
    start, end = _date_range(days)

    rows = (
        db.query(
            models.SesionGrupo.fecha_sesion,
            models.Asistencia.estado,
        )
        .join(models.Asistencia, models.Asistencia.sesion_id == models.SesionGrupo.id)
        .filter(
            models.SesionGrupo.grupo_id.in_(group_ids),
            models.SesionGrupo.fecha_sesion >= start,
            models.SesionGrupo.fecha_sesion < end,
            models.SesionGrupo.deleted_at.is_(None),
            models.Asistencia.deleted_at.is_(None),
        )
        .all()
    )

    # weekday (0=Mon...6=Sun) x week_number_within_period
    # Build per-day aggregates (date → {p, t})
    day_agg: dict[_dt.date, dict] = defaultdict(lambda: {"p": 0, "t": 0})
    for fecha, estado in rows:
        d = fecha.date() if hasattr(fecha, "date") else fecha
        day_agg[d]["t"] += 1
        if estado in ATTENDED_STATES:
            day_agg[d]["p"] += 1

    # Now group by weekday
    weekday_agg: dict[int, dict] = defaultdict(lambda: {"p": 0, "t": 0, "sessions": 0})
    for date_key, counts in day_agg.items():
        wd = date_key.weekday()  # 0=Mon
        weekday_agg[wd]["p"] += counts["p"]
        weekday_agg[wd]["t"] += counts["t"]
        weekday_agg[wd]["sessions"] += 1

    _DAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    cells = []
    for wd in range(7):
        agg = weekday_agg.get(wd, {"p": 0, "t": 0, "sessions": 0})
        pct = round((agg["p"] / agg["t"]) * 100, 1) if agg["t"] else None
        cells.append({
            "weekday": wd,
            "label": _DAY_NAMES[wd],
            "sessions": agg["sessions"],
            "present": agg["p"],
            "total": agg["t"],
            "pct": pct,
        })

    return {"cells": cells}


# ─────────────────────────────────────────────────────────
# GET /analytics/strategy/{strategy_id}/alerts
# ─────────────────────────────────────────────────────────

@router.get("/analytics/strategy/{strategy_id}/alerts")
def strategy_alerts(
    strategy_id: str,
    threshold_pct: int = Query(60, description="% mínimo de asistencia aceptable"),
    consecutive_sessions: int = Query(3, description="Sesiones consecutivas bajo umbral para alerta"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    sede_id = require_user_sede_id(db, current_user)
    _get_strategy_or_404(db, strategy_id, sede_id)
    group_ids = _group_ids_for_strategy(db, strategy_id, sede_id)
    alerts = []

    if not group_ids:
        return {"alerts": []}

    groups = (
        db.query(models.GrupoEvangelismo)
        .filter(models.GrupoEvangelismo.id.in_(group_ids))
        .all()
    )
    group_map = {g.id: g for g in groups}

    # Alert type 1: Grupos con N sesiones consecutivas bajo umbral
    for gid in group_ids:
        recent_sessions = (
            db.query(models.SesionGrupo)
            .filter(
                models.SesionGrupo.grupo_id == gid,
                models.SesionGrupo.estado == "REALIZADA",
                models.SesionGrupo.deleted_at.is_(None),
            )
            .order_by(models.SesionGrupo.fecha_sesion.desc())
            .limit(consecutive_sessions + 2)
            .all()
        )
        if len(recent_sessions) < consecutive_sessions:
            continue

        low_count = 0
        for sess in recent_sessions[:consecutive_sessions]:
            att = (
                db.query(models.Asistencia.estado)
                .filter(
                    models.Asistencia.sesion_id == sess.id,
                    models.Asistencia.deleted_at.is_(None),
                )
                .all()
            )
            total = len(att)
            present = sum(1 for (e,) in att if e in ATTENDED_STATES)
            pct = (present / total * 100) if total else 0
            if pct < threshold_pct:
                low_count += 1

        if low_count >= consecutive_sessions:
            g = group_map.get(gid)
            alerts.append({
                "type": "low_attendance",
                "severity": "high",
                "group_id": gid,
                "group_name": g.nombre if g else str(gid),
                "message": f"{consecutive_sessions} sesiones consecutivas con asistencia bajo {threshold_pct}%",
                "consecutive_sessions": consecutive_sessions,
            })

    # Alert type 2: Grupos sin sesión en 30+ días
    cutoff = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=30)
    for gid in group_ids:
        last = (
            db.query(_func.max(models.SesionGrupo.fecha_sesion))
            .filter(
                models.SesionGrupo.grupo_id == gid,
                models.SesionGrupo.deleted_at.is_(None),
            )
            .scalar()
        )
        if last is None or last < cutoff:
            g = group_map.get(gid)
            days_ago = (
                (_dt.datetime.now(_dt.timezone.utc) - last).days
                if last else None
            )
            alerts.append({
                "type": "no_recent_session",
                "severity": "medium",
                "group_id": gid,
                "group_name": g.nombre if g else str(gid),
                "message": f"Sin sesión en {days_ago} días" if days_ago else "Sin sesiones registradas",
                "days_since_last": days_ago,
            })

    # Alert type 3: Grupos listos para multiplicación (>= capacidad * 0.85)
    for g in groups:
        member_count = (
            db.query(_func.count(models.ParticipanteGrupo.id))
            .filter(
                models.ParticipanteGrupo.grupo_id == g.id,
                models.ParticipanteGrupo.activo.is_(True),
                models.ParticipanteGrupo.deleted_at.is_(None),
            )
            .scalar() or 0
        )
        capacity = g.capacidad or 15
        if member_count >= capacity * 0.85:
            alerts.append({
                "type": "ready_to_multiply",
                "severity": "info",
                "group_id": g.id,
                "group_name": g.nombre,
                "message": f"{member_count} personas — alcanzó el {round(member_count/capacity*100)}% de capacidad ({capacity})",
                "members": member_count,
                "capacity": capacity,
            })

    # Alert type 4: Personas con 2+ ausencias consecutivas (top 10)
    absent_alerts = []
    thirty_days_ago = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=30)
    participant_ids = (
        db.query(_func.distinct(models.ParticipanteGrupo.persona_id))
        .filter(
            models.ParticipanteGrupo.grupo_id.in_(group_ids),
            models.ParticipanteGrupo.activo.is_(True),
            models.ParticipanteGrupo.deleted_at.is_(None),
        )
        .limit(200)
        .all()
    )
    persona_ids_list = [r[0] for r in participant_ids]

    if persona_ids_list:
        recent_att = (
            db.query(
                models.Asistencia.persona_id,
                models.Asistencia.estado,
                models.SesionGrupo.fecha_sesion,
            )
            .join(models.SesionGrupo, models.Asistencia.sesion_id == models.SesionGrupo.id)
            .filter(
                models.SesionGrupo.grupo_id.in_(group_ids),
                models.Asistencia.persona_id.in_(persona_ids_list),
                models.SesionGrupo.fecha_sesion >= thirty_days_ago,
                models.Asistencia.deleted_at.is_(None),
                models.SesionGrupo.deleted_at.is_(None),
            )
            .order_by(models.SesionGrupo.fecha_sesion.desc())
            .all()
        )

        person_att: dict = defaultdict(list)
        for pid, estado, _ in recent_att:
            person_att[pid].append(estado)

        persona_records = {}
        if person_att:
            persons = (
                db.query(models.Persona)
                .filter(models.Persona.id.in_(list(person_att.keys())))
                .all()
            )
            persona_records = {str(p.id): p for p in persons}

        for pid, estados in person_att.items():
            consecutive_absent = 0
            for e in estados:
                if e not in ATTENDED_STATES:
                    consecutive_absent += 1
                else:
                    break
            if consecutive_absent >= 2:
                p = persona_records.get(str(pid))
                name = f"{p.first_name} {p.last_name}" if p else str(pid)
                absent_alerts.append({
                    "type": "consecutive_absences",
                    "severity": "medium",
                    "persona_id": str(pid),
                    "persona_name": name,
                    "message": f"{consecutive_absent} ausencias consecutivas",
                    "consecutive_absences": consecutive_absent,
                })

    absent_alerts.sort(key=lambda x: x["consecutive_absences"], reverse=True)
    alerts.extend(absent_alerts[:10])

    return {"alerts": alerts}


# ─────────────────────────────────────────────────────────
# GET /analytics/strategy/{strategy_id}/velocity
# ─────────────────────────────────────────────────────────

@router.get("/analytics/strategy/{strategy_id}/velocity")
def strategy_velocity(
    strategy_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    sede_id = require_user_sede_id(db, current_user)
    _get_strategy_or_404(db, strategy_id, sede_id)

    # Velocity from HistorialEmbudo (global, since it's not tied to strategy directly)
    rows = (
        db.query(
            models.HistorialEmbudo.rol_nuevo,
            _func.avg(models.HistorialEmbudo.dias_en_estado_anterior),
            _func.count(models.HistorialEmbudo.id),
        )
        .filter(models.HistorialEmbudo.deleted_at.is_(None))
        .group_by(models.HistorialEmbudo.rol_nuevo)
        .all()
    )

    _ROLE_LABELS = {
        "visitante": "Visitante",
        "invitado": "Invitado",
        "asistente": "Asistente",
        "anfitrion": "Anfitrión",
        "colider": "Colíder",
        "lider": "Líder",
        "VISITANTE": "Visitante",
        "INVITADO": "Invitado",
        "ASISTENTE": "Asistente",
        "ANFITRION": "Anfitrión",
        "COLIDER": "Colíder",
        "LIDER": "Líder",
    }

    _ROLE_ORDER = ["visitante", "invitado", "asistente", "anfitrion", "colider", "lider"]

    stages = []
    for rol, avg_days, count in rows:
        stages.append({
            "role": rol,
            "label": _ROLE_LABELS.get(rol, rol),
            "avg_days": round(float(avg_days), 1) if avg_days else 0.0,
            "transitions": count,
            "order": _ROLE_ORDER.index(rol.lower()) if rol.lower() in _ROLE_ORDER else 99,
        })

    stages.sort(key=lambda x: x["order"])
    max_days = max((s["avg_days"] for s in stages), default=1) or 1

    for s in stages:
        s["pct_of_max"] = round((s["avg_days"] / max_days) * 100, 1)

    return {"stages": stages}


# ─────────────────────────────────────────────────────────
# GET /analytics/strategy/{strategy_id}/groups
# ─────────────────────────────────────────────────────────

@router.get("/analytics/strategy/{strategy_id}/groups")
def strategy_groups_detail(
    strategy_id: str,
    period: str = Query("30d"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    sede_id = require_user_sede_id(db, current_user)
    _get_strategy_or_404(db, strategy_id, sede_id)
    group_ids = _group_ids_for_strategy(db, strategy_id, sede_id)
    if not group_ids:
        return {"groups": []}

    days = _parse_period(period)
    start, end = _date_range(days)
    prev_start, prev_end = _prev_range(days)

    groups = (
        db.query(models.GrupoEvangelismo)
        .filter(models.GrupoEvangelismo.id.in_(group_ids))
        .all()
    )

    # Leader names
    leader_ids = [g.lider_persona_id for g in groups if g.lider_persona_id]
    leader_map = {}
    if leader_ids:
        leader_map = {
            str(p.id): f"{p.first_name} {p.last_name}"
            for p in db.query(models.Persona).filter(models.Persona.id.in_(leader_ids)).all()
        }

    # Member counts
    member_counts = dict(
        db.query(models.ParticipanteGrupo.grupo_id, _func.count(models.ParticipanteGrupo.id))
        .filter(
            models.ParticipanteGrupo.grupo_id.in_(group_ids),
            models.ParticipanteGrupo.activo.is_(True),
            models.ParticipanteGrupo.deleted_at.is_(None),
        )
        .group_by(models.ParticipanteGrupo.grupo_id)
        .all()
    )

    # Attendance per group, current and previous period
    def _group_att(gid, s, e):
        rows = (
            db.query(models.Asistencia.estado)
            .join(models.SesionGrupo, models.Asistencia.sesion_id == models.SesionGrupo.id)
            .filter(
                models.SesionGrupo.grupo_id == gid,
                models.SesionGrupo.fecha_sesion >= s,
                models.SesionGrupo.fecha_sesion < e,
                models.SesionGrupo.deleted_at.is_(None),
                models.Asistencia.deleted_at.is_(None),
            )
            .all()
        )
        present = sum(1 for (estado,) in rows if estado in ATTENDED_STATES)
        total = len(rows)
        return present, total

    # Sparkline: last 6 sessions attendance pct
    def _sparkline(gid):
        sessions = (
            db.query(models.SesionGrupo)
            .filter(
                models.SesionGrupo.grupo_id == gid,
                models.SesionGrupo.estado == "REALIZADA",
                models.SesionGrupo.deleted_at.is_(None),
            )
            .order_by(models.SesionGrupo.fecha_sesion.desc())
            .limit(8)
            .all()
        )
        result = []
        for sess in reversed(sessions):
            att = (
                db.query(models.Asistencia.estado)
                .filter(
                    models.Asistencia.sesion_id == sess.id,
                    models.Asistencia.deleted_at.is_(None),
                )
                .all()
            )
            total = len(att)
            present = sum(1 for (e,) in att if e in ATTENDED_STATES)
            result.append(round((present / total) * 100, 1) if total else 0.0)
        return result

    result = []
    for g in groups:
        present, total = _group_att(g.id, start, end)
        prev_present, prev_total = _group_att(g.id, prev_start, prev_end)
        pct = round((present / total) * 100, 1) if total else 0.0
        prev_pct = round((prev_present / prev_total) * 100, 1) if prev_total else 0.0

        new_joiners = (
            db.query(_func.count(models.ParticipanteGrupo.id))
            .filter(
                models.ParticipanteGrupo.grupo_id == g.id,
                models.ParticipanteGrupo.fecha_ingreso >= start,
                models.ParticipanteGrupo.fecha_ingreso < end,
                models.ParticipanteGrupo.deleted_at.is_(None),
            )
            .scalar() or 0
        )

        result.append({
            "id": g.id,
            "name": g.nombre,
            "code": g.codigo,
            "leader_name": leader_map.get(str(g.lider_persona_id), "Sin líder"),
            "members": member_counts.get(g.id, 0),
            "attendance_pct": pct,
            "prev_attendance_pct": prev_pct,
            "attendance_delta": round(pct - prev_pct, 1),
            "new_joiners": new_joiners,
            "sparkline": _sparkline(g.id),
            "capacity": g.capacidad or 15,
        })

    result.sort(key=lambda x: x["attendance_pct"], reverse=True)
    return {"groups": result}
