"""
Evangelism Strategy Analytics API
==================================
Endpoints:
  GET /analytics/strategy/{strategy_id}           — KPIs generales + resumen de grupos
  GET /analytics/strategy/{strategy_id}/trend     — Tendencia de asistencia en el tiempo
  GET /analytics/strategy/{strategy_id}/funnel    — Embudo de conversión de roles
  GET /analytics/strategy/{strategy_id}/heatmap   — Asistencia por día de la semana
  GET /analytics/strategy/{strategy_id}/alerts    — Alertas tempranas (grupos y personas)
  GET /analytics/strategy/{strategy_id}/velocity  — Velocidad de cambio de roles
  GET /analytics/strategy/{strategy_id}/groups    — Grupos con mini-métricas detalladas
"""
from __future__ import annotations

import datetime as _dt
import math as _math
import uuid as _uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func as _func
from sqlalchemy.orm import Session

from backend import models
from backend.api.evangelism_shared import ATTENDED_STATES
from backend.auth import require_active_user
from backend.core.database import get_db
from backend.core.tenant import get_user_sede_id

router = APIRouter()

# ─────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────

_PERIOD_DAYS = {"7d": 7, "30d": 30, "90d": 90, "180d": 180, "365d": 365}

def _normalize_rol(name: str) -> str:
    """Normalize a role name string for fuzzy matching (lowercase, strip accents)."""
    import unicodedata
    s = unicodedata.normalize("NFD", name.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _rol_to_funnel_stage(nombre_rol: str) -> str:
    """
    Map a custom role name to a canonical funnel stage using keyword matching.
    rol_base values like 'persona'/'miembro' are CRM categories, NOT funnel stages.
    The actual ministry role comes from nombre_rol (estrategia_roles_personalizados).
    """
    n = _normalize_rol(nombre_rol)
    if any(k in n for k in ("lider", "líder", "pastor", "director")):
        if any(k in n for k in ("co", "asistente", "aux")):
            return "colider"
        return "lider"
    if any(k in n for k in ("colider", "colíder", "co-lider")):
        return "colider"
    if any(k in n for k in ("anfitrion", "anfitrión", "anfitri")):
        return "anfitrion"
    if any(k in n for k in ("asistente", "colaborador", "apoyo", "aux")):
        return "asistente"
    if any(k in n for k in ("visitante", "invitado", "nuevo")):
        return "visitante"
    # Unknown custom role — return as-is so UI can show it
    return "personalizado"

# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

def _parse_period(period: str) -> int:
    return _PERIOD_DAYS.get(period, 30)


def _date_range(days: int):
    now = _dt.datetime.now(_dt.timezone.utc)
    return now - _dt.timedelta(days=days), now


def _prev_range(days: int):
    now = _dt.datetime.now(_dt.timezone.utc)
    end = now - _dt.timedelta(days=days)
    return end - _dt.timedelta(days=days), end


def _get_strategy_or_404(db: Session, strategy_id: str):
    s = db.query(models.EstrategiaEvangelismo).filter(
        models.EstrategiaEvangelismo.id == strategy_id,
        models.EstrategiaEvangelismo.deleted_at.is_(None),
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Estrategia no encontrada")
    return s


def _group_ids_for_strategy(db: Session, strategy_id: str, sede_id) -> list[_uuid.UUID]:
    q = db.query(models.GrupoEvangelismo.id).filter(
        models.GrupoEvangelismo.estrategia_id == strategy_id,
        models.GrupoEvangelismo.deleted_at.is_(None),
    )
    if sede_id:
        q = q.filter(models.GrupoEvangelismo.sede_id == sede_id)
    return [r[0] for r in q.all()]


def _delta(current: float, previous: float) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def _attendance_stats(db: Session, group_ids: list[_uuid.UUID], start, end) -> tuple[int, int]:
    """Returns (present, total) attendance counts in the date range."""
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


def _sessions_done_count(db: Session, group_ids: list[_uuid.UUID], start, end) -> int:
    """Count sessions with estado that means 'completed', case-insensitive."""
    if not group_ids:
        return 0
    return (
        db.query(_func.count(models.SesionGrupo.id))
        .filter(
            models.SesionGrupo.grupo_id.in_(group_ids),
            _func.lower(models.SesionGrupo.estado) == "realizada",
            models.SesionGrupo.fecha_sesion >= start,
            models.SesionGrupo.fecha_sesion < end,
            models.SesionGrupo.deleted_at.is_(None),
        )
        .scalar() or 0
    )


def _sessions_total_count(db: Session, group_ids: list[_uuid.UUID], start, end) -> int:
    if not group_ids:
        return 0
    return (
        db.query(_func.count(models.SesionGrupo.id))
        .filter(
            models.SesionGrupo.grupo_id.in_(group_ids),
            models.SesionGrupo.fecha_sesion >= start,
            models.SesionGrupo.fecha_sesion < end,
            models.SesionGrupo.deleted_at.is_(None),
        )
        .scalar() or 0
    )


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
    # sede_id is optional — if user has no sede we show all groups (super-admin case)
    sede_id = get_user_sede_id(db, current_user)
    _get_strategy_or_404(db, strategy_id)
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

    # ── Sesiones (case-insensitive para manejar "Realizada" vs "REALIZADA") ──
    sessions_done = _sessions_done_count(db, group_ids, start, end)
    sessions_total = _sessions_total_count(db, group_ids, start, end)
    prev_sessions_done = _sessions_done_count(db, group_ids, prev_start, prev_end)

    # ── Nuevos ingresos ──
    new_joiners = 0
    prev_new_joiners = 0
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

    # ── Retención ──
    retention_pct = 0.0
    if prev_active_members > 0:
        retention_pct = round(min((active_members / prev_active_members) * 100, 100.0), 1)

    return {
        "period": period,
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
    sede_id = get_user_sede_id(db, current_user)
    _get_strategy_or_404(db, strategy_id)
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

    def _bucket_key(dt) -> str:
        # Normalize timezone-aware and naive datetimes
        if hasattr(dt, "tzinfo") and dt.tzinfo is None:
            dt = dt.replace(tzinfo=_dt.timezone.utc)
        if use_weeks:
            return dt.strftime("%G-W%V")
        return dt.strftime("%Y-%m")

    agg: dict[str, dict[int, dict]] = defaultdict(lambda: defaultdict(lambda: {"p": 0, "t": 0}))
    global_agg: dict[str, dict] = defaultdict(lambda: {"p": 0, "t": 0})

    for grupo_id, fecha, estado in rows:
        key = _bucket_key(fecha)
        agg[key][grupo_id]["t"] += 1
        global_agg[key]["t"] += 1
        if estado in ATTENDED_STATES:
            agg[key][grupo_id]["p"] += 1
            global_agg[key]["p"] += 1

    all_keys = sorted(set(agg.keys()))

    def _pct(p, t):
        return round((p / t) * 100, 1) if t else None

    buckets = []
    for key in all_keys:
        g_data = global_agg[key]
        entry: dict = {
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
        parts = key.split("-W")
        return f"Sem {parts[1]}" if len(parts) == 2 else key
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
    """
    Embudo ministerial basado en roles personalizados de la estrategia.

    Los valores 'persona' y 'miembro' en rol_base son categorías CRM, NO roles
    del grupo. El rol real viene de nombre_rol en estrategia_roles_personalizados
    cuando rol_base = 'personalizado'. Para personas sin rol personalizado asignado
    se muestran en 'Sin rol asignado'.
    """
    sede_id = get_user_sede_id(db, current_user)
    _get_strategy_or_404(db, strategy_id)
    group_ids = _group_ids_for_strategy(db, strategy_id, sede_id)

    if not group_ids:
        return {"total_active": 0, "stages": [], "without_role": 0, "role_breakdown": []}

    # Fetch all active participants with their custom role name (if any)
    rows = (
        db.query(
            models.ParticipanteGrupo.rol_base,
            models.RolPersonalizadoEstrategia.nombre_rol,
            _func.count(models.ParticipanteGrupo.id),
        )
        .outerjoin(
            models.RolPersonalizadoEstrategia,
            models.ParticipanteGrupo.rol_personalizado_id == models.RolPersonalizadoEstrategia.id,
        )
        .filter(
            models.ParticipanteGrupo.grupo_id.in_(group_ids),
            models.ParticipanteGrupo.activo.is_(True),
            models.ParticipanteGrupo.deleted_at.is_(None),
        )
        .group_by(
            models.ParticipanteGrupo.rol_base,
            models.RolPersonalizadoEstrategia.nombre_rol,
        )
        .all()
    )

    stage_counts: dict[str, int] = defaultdict(int)
    without_role = 0
    role_breakdown: list[dict] = []

    for rol_base, nombre_rol, count in rows:
        if nombre_rol:
            # Has a custom role — classify by role name
            stage = _rol_to_funnel_stage(nombre_rol)
            stage_counts[stage] += count
            role_breakdown.append({
                "nombre_rol": nombre_rol,
                "stage": stage,
                "count": count,
            })
        else:
            # No custom role assigned — not a funnel stage
            without_role += count

    # Average days per transition from HistorialEmbudo
    velocity_rows = (
        db.query(
            models.HistorialEmbudo.rol_nuevo,
            _func.avg(models.HistorialEmbudo.dias_en_estado_anterior),
        )
        .filter(models.HistorialEmbudo.deleted_at.is_(None))
        .group_by(models.HistorialEmbudo.rol_nuevo)
        .all()
    )
    velocity_map: dict[str, float] = {}
    for rol, avg_days in velocity_rows:
        if avg_days is not None:
            stage = _rol_to_funnel_stage(rol)
            velocity_map[stage] = round(float(avg_days), 0)

    STAGES = [
        {"key": "visitante",     "label": "Visitante / Invitado"},
        {"key": "asistente",     "label": "Asistente"},
        {"key": "anfitrion",     "label": "Anfitrión"},
        {"key": "colider",       "label": "Colíder"},
        {"key": "lider",         "label": "Líder"},
        {"key": "personalizado", "label": "Otro rol"},
    ]

    total_with_role = sum(stage_counts.values())
    total_active = total_with_role + without_role
    top = total_active or 1

    stages = []
    for stage_def in STAGES:
        count = stage_counts.get(stage_def["key"], 0)
        if count == 0 and stage_def["key"] == "personalizado":
            continue
        stages.append({
            "key": stage_def["key"],
            "label": stage_def["label"],
            "count": count,
            "pct_of_total": round((count / top) * 100, 1),
            "avg_days_before": velocity_map.get(stage_def["key"]),
        })

    return {
        "total_active": total_active,
        "with_role": total_with_role,
        "without_role": without_role,
        "stages": stages,
        "role_breakdown": sorted(role_breakdown, key=lambda x: x["count"], reverse=True),
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
    sede_id = get_user_sede_id(db, current_user)
    _get_strategy_or_404(db, strategy_id)
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

    day_agg: dict[_dt.date, dict] = defaultdict(lambda: {"p": 0, "t": 0})
    for fecha, estado in rows:
        # Handle both timezone-aware and naive datetimes
        if hasattr(fecha, "date"):
            d = fecha.date()
        else:
            d = fecha
        day_agg[d]["t"] += 1
        if estado in ATTENDED_STATES:
            day_agg[d]["p"] += 1

    weekday_agg: dict[int, dict] = defaultdict(lambda: {"p": 0, "t": 0, "sessions": 0})
    for date_key, counts in day_agg.items():
        wd = date_key.weekday()
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
    threshold_pct: int = Query(60),
    consecutive_sessions: int = Query(3),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    sede_id = get_user_sede_id(db, current_user)
    _get_strategy_or_404(db, strategy_id)
    group_ids = _group_ids_for_strategy(db, strategy_id, sede_id)
    if not group_ids:
        return {"alerts": []}

    groups = (
        db.query(models.GrupoEvangelismo)
        .filter(models.GrupoEvangelismo.id.in_(group_ids))
        .all()
    )
    group_map = {g.id: g for g in groups}
    alerts = []

    # Alert type 1: Groups with N consecutive low-attendance sessions
    for gid in group_ids:
        recent_sessions = (
            db.query(models.SesionGrupo)
            .filter(
                models.SesionGrupo.grupo_id == gid,
                _func.lower(models.SesionGrupo.estado) == "realizada",
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
            t = len(att)
            p = sum(1 for (e,) in att if e in ATTENDED_STATES)
            pct = (p / t * 100) if t else 0
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
            })

    # Alert type 2: Groups without a session in 30+ days
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
        # Normalize timezone for comparison
        if last is not None and hasattr(last, "tzinfo") and last.tzinfo is None:
            last = last.replace(tzinfo=_dt.timezone.utc)
        if last is None or last < cutoff:
            g = group_map.get(gid)
            days_ago = int((_dt.datetime.now(_dt.timezone.utc) - last).days) if last else None
            alerts.append({
                "type": "no_recent_session",
                "severity": "medium",
                "group_id": gid,
                "group_name": g.nombre if g else str(gid),
                "message": f"Sin sesión en {days_ago} días" if days_ago else "Sin sesiones registradas",
                "days_since_last": days_ago,
            })

    # Alert type 3: Groups near capacity (ready to multiply)
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
        if member_count >= int(capacity * 0.85):
            alerts.append({
                "type": "ready_to_multiply",
                "severity": "info",
                "group_id": g.id,
                "group_name": g.nombre,
                "message": f"{member_count} personas — {round(member_count / capacity * 100)}% de capacidad ({capacity})",
                "members": member_count,
                "capacity": capacity,
            })

    # Alert type 4: People with 2+ consecutive absences (top 10)
    thirty_days_ago = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=30)
    if group_ids:
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
            for pid, estado in recent_att:
                person_att[pid].append(estado)

            persona_records = {}
            if person_att:
                persons = (
                    db.query(models.Persona)
                    .filter(models.Persona.id.in_(list(person_att.keys())))
                    .all()
                )
                persona_records = {str(p.id): p for p in persons}

            absent_alerts = []
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
    # Validate strategy exists
    _get_strategy_or_404(db, strategy_id)

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
        "visitante": "Visitante", "VISITANTE": "Visitante",
        "persona": "Visitante",
        "invitado": "Invitado", "INVITADO": "Invitado",
        "asistente": "Asistente", "ASISTENTE": "Asistente",
        "miembro": "Asistente / Miembro",
        "anfitrion": "Anfitrión", "ANFITRION": "Anfitrión",
        "colider": "Colíder", "COLIDER": "Colíder",
        "lider": "Líder", "LIDER": "Líder",
    }
    _ROLE_ORDER = ["visitante", "persona", "invitado", "asistente", "miembro", "anfitrion", "colider", "lider"]

    stages = []
    for rol, avg_days, count in rows:
        if avg_days is None:
            continue
        order = _ROLE_ORDER.index(rol.lower()) if rol and rol.lower() in _ROLE_ORDER else 99
        stages.append({
            "role": rol,
            "label": _ROLE_LABELS.get(rol, rol),
            "avg_days": round(float(avg_days), 1),
            "transitions": count,
            "order": order,
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
    sede_id = get_user_sede_id(db, current_user)
    _get_strategy_or_404(db, strategy_id)
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

    leader_ids = [g.lider_persona_id for g in groups if g.lider_persona_id]
    leader_map = {}
    if leader_ids:
        leader_map = {
            str(p.id): f"{p.first_name} {p.last_name}"
            for p in db.query(models.Persona).filter(models.Persona.id.in_(leader_ids)).all()
        }

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
        return present, len(rows)

    def _sparkline(gid) -> list[float]:
        """Last 8 realized sessions attendance percentage."""
        sessions = (
            db.query(models.SesionGrupo)
            .filter(
                models.SesionGrupo.grupo_id == gid,
                _func.lower(models.SesionGrupo.estado) == "realizada",
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
            t = len(att)
            p = sum(1 for (e,) in att if e in ATTENDED_STATES)
            result.append(round((p / t) * 100, 1) if t else 0.0)
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


# ═══════════════════════════════════════════════════════════════
# ANALYTICS COMPLETO — 10 DIMENSIONES
# GET /analytics/strategy/{strategy_id}/full?weeks=12
# ═══════════════════════════════════════════════════════════════


def _semaforo_tof(pct: float) -> str:
    if pct >= 86:
        return "SATURADO"
    if pct >= 60:
        return "SALUDABLE"
    return "BAJO"


def _semaforo_ics(pct: float) -> str:
    if pct >= 90:
        return "OPTIMO"
    if pct >= 70:
        return "INCONSTANTE"
    return "ABANDONO"


def _semaforo_icd(pct: float) -> str:
    if pct >= 70:
        return "IMAN_FUERTE"
    if pct >= 35:
        return "REGULAR"
    return "COLADOR"


def _classify_group(nuevos_vol: int, icn: float) -> str:
    alto_volumen = nuevos_vol >= 5
    if alto_volumen and icn >= 70:
        return "IMAN_FUERTE"
    if alto_volumen and icn < 35:
        return "COLADOR"
    if not alto_volumen and icn >= 85:
        return "INCUBADORA"
    return "ESTANDAR"


def _shannon_entropy(counts: dict) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return round(-sum((v / total) * _math.log(v / total) for v in counts.values() if v > 0), 3)


def _age_bucket(birthday) -> str:
    if birthday is None:
        return "Desconocido"
    today = _dt.date.today()
    try:
        bday = birthday.date() if hasattr(birthday, "date") else birthday
        age = today.year - bday.year - ((today.month, today.day) < (bday.month, bday.day))
    except Exception:
        return "Desconocido"
    if age < 12:
        return "Niños"
    if age < 26:
        return "Jóvenes"
    if age < 36:
        return "Jóvenes Adultos"
    if age < 56:
        return "Adultos"
    return "Adultos Mayores"


def _attended(estado: str | None) -> bool:
    return str(estado or "").lower().strip() in {"presente", "asistio", "primera_vez", "primera vez"}


def _is_primera_vez(a) -> bool:
    return bool(a.es_primera_vez) or str(a.estado or "").lower().strip() in {"primera_vez", "primera vez"}


@router.get("/analytics/strategy/{strategy_id}/full", response_model=dict)
def get_strategy_full_analytics(
    strategy_id: str,
    weeks: int = Query(default=12, ge=1, le=104),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """10-dimension analytics engine for an evangelism strategy."""

    # ── 0. Base data load (bulk, no N+1) ──────────────────────
    fecha_hasta = _dt.date.today()
    fecha_desde = fecha_hasta - _dt.timedelta(weeks=weeks)

    grupos = (
        db.query(models.GrupoEvangelismo)
        .filter(
            models.GrupoEvangelismo.estrategia_id == strategy_id,
            models.GrupoEvangelismo.deleted_at.is_(None),
        )
        .all()
    )
    if not grupos:
        return {"error": "Estrategia sin grupos", "strategy_id": strategy_id}

    group_ids = [g.id for g in grupos]
    group_map = {g.id: g for g in grupos}

    # Sesiones en el período
    sesiones = (
        db.query(models.SesionGrupo)
        .filter(
            models.SesionGrupo.grupo_id.in_(group_ids),
            models.SesionGrupo.fecha_sesion >= fecha_desde,
            models.SesionGrupo.fecha_sesion <= fecha_hasta,
            models.SesionGrupo.deleted_at.is_(None),
        )
        .all()
    )
    session_ids = [s.id for s in sesiones]
    sessions_by_group: dict = defaultdict(list)
    for s in sesiones:
        sessions_by_group[s.grupo_id].append(s)

    # Asistencias
    asistencias = (
        db.query(models.Asistencia)
        .filter(models.Asistencia.sesion_id.in_(session_ids))
        .all()
    ) if session_ids else []
    att_by_session: dict = defaultdict(list)
    att_by_persona: dict = defaultdict(list)
    for a in asistencias:
        att_by_session[a.sesion_id].append(a)
        att_by_persona[a.persona_id].append(a)

    # Participantes activos
    participantes = (
        db.query(models.ParticipanteGrupo)
        .filter(
            models.ParticipanteGrupo.grupo_id.in_(group_ids),
            models.ParticipanteGrupo.deleted_at.is_(None),
            models.ParticipanteGrupo.activo == True,  # noqa: E712
        )
        .all()
    )
    parts_by_group: dict = defaultdict(list)
    for p in participantes:
        parts_by_group[p.grupo_id].append(p)

    # Personas únicas (participantes + asistentes)
    persona_ids = list({p.persona_id for p in participantes} | {a.persona_id for a in asistencias})
    personas_map: dict = {}
    if persona_ids:
        for persona in db.query(models.Persona).filter(models.Persona.id.in_(persona_ids)).all():
            personas_map[persona.id] = persona

    # CRM casos vinculados a estos grupos
    crm_casos = (
        db.query(models.CrmCaso)
        .filter(models.CrmCaso.origen_grupo_id.in_(group_ids))
        .all()
    ) if hasattr(models, "CrmCaso") else []
    crm_by_group: dict = defaultdict(list)
    for c in crm_casos:
        crm_by_group[c.origen_grupo_id].append(c)

    # Grupos hijos (multiplicación)
    grupos_hijos = (
        db.query(models.GrupoEvangelismo)
        .filter(
            models.GrupoEvangelismo.parent_group_id.in_(group_ids),
            models.GrupoEvangelismo.deleted_at.is_(None),
            models.GrupoEvangelismo.created_at >= _dt.datetime.combine(fecha_desde, _dt.time.min),
        )
        .all()
    ) if any(True for g in grupos if hasattr(g, "parent_group_id")) else []

    # ── DIM 1: Territorial ────────────────────────────────────
    zonas: dict = defaultdict(int)
    for g in grupos:
        if g.activo:
            zona = (g.ubicacion or "Sin zona definida").strip() or "Sin zona definida"
            zonas[zona] += 1
    total_zonas = max(len(zonas), 1)
    activos_count = sum(1 for g in grupos if g.activo)
    idc = round(activos_count / total_zonas, 2)
    dim1 = {
        "grupos_activos": activos_count,
        "zonas_identificadas": total_zonas,
        "idc": idc,
        "semaforo": "ALTO" if idc > 3 else ("MEDIO" if idc >= 1 else "CRITICO"),
        "por_zona": [{"zona": z, "grupos": c} for z, c in sorted(zonas.items(), key=lambda x: -x[1])],
        "nota": "IDC basado en campo ubicacion. Para mapa GIS agrega latitud/longitud a los grupos.",
    }

    # ── DIM 2: Capacidad y Población ─────────────────────────
    grupos_tof = []
    for g in grupos:
        activos = len(parts_by_group.get(g.id, []))
        cap = g.capacidad or 15
        tof = round(activos / cap * 100, 1)
        grupos_tof.append({
            "grupo_id": str(g.id),
            "nombre": g.nombre,
            "participantes_activos": activos,
            "capacidad": cap,
            "tof_porcentaje": tof,
            "estado": _semaforo_tof(tof),
        })
    dim2 = {
        "grupos": sorted(grupos_tof, key=lambda x: -x["tof_porcentaje"]),
        "saturados": sum(1 for x in grupos_tof if x["estado"] == "SATURADO"),
        "saludables": sum(1 for x in grupos_tof if x["estado"] == "SALUDABLE"),
        "bajos": sum(1 for x in grupos_tof if x["estado"] == "BAJO"),
    }

    # ── DIM 3: Atracción y Recurrencia ────────────────────────
    nuevos_por_grupo: dict = defaultdict(set)
    total_presentes_por_grupo: dict = defaultdict(int)
    for s in sesiones:
        for a in att_by_session.get(s.id, []):
            if _attended(a.estado):
                total_presentes_por_grupo[s.grupo_id] += 1
            if _is_primera_vez(a):
                nuevos_por_grupo[s.grupo_id].add(a.persona_id)

    # IRT: asistencias en primeras 4 sesiones para nuevos
    grupos_tan = []
    for g in grupos:
        nuevos = nuevos_por_grupo.get(g.id, set())
        total_presentes = total_presentes_por_grupo.get(g.id, 0)
        tan = round(len(nuevos) / total_presentes * 100, 1) if total_presentes > 0 else 0

        # IRT: por cada nuevo, contar cuántas asistencias en sus primeras 4 sesiones
        gsessions_sorted = sorted(sessions_by_group.get(g.id, []), key=lambda s: s.fecha_sesion)
        irt_vals = []
        for pid in nuevos:
            # Encontrar primera sesión donde asistió
            first_sess_idx = None
            for i, s in enumerate(gsessions_sorted):
                for a in att_by_session.get(s.id, []):
                    if a.persona_id == pid and _is_primera_vez(a):
                        first_sess_idx = i
                        break
                if first_sess_idx is not None:
                    break
            if first_sess_idx is None:
                continue
            next4 = gsessions_sorted[first_sess_idx:first_sess_idx + 4]
            count = sum(
                1 for s in next4
                for a in att_by_session.get(s.id, [])
                if a.persona_id == pid and _attended(a.estado)
            )
            irt_vals.append(count)

        irt_prom = round(sum(irt_vals) / len(irt_vals), 2) if irt_vals else 0
        irt_sem = "EXCELENTE" if irt_prom >= 3 else ("REGULAR" if irt_prom >= 2 else "ALERTA_DESERCION")
        grupos_tan.append({
            "grupo_id": str(g.id),
            "nombre": g.nombre,
            "nuevos_visitantes": len(nuevos),
            "tan_porcentaje": tan,
            "irt_promedio": irt_prom,
            "irt_semaforo": irt_sem,
        })

    dim3 = {
        "total_nuevos_periodo": sum(len(v) for v in nuevos_por_grupo.values()),
        "tan_global_porcentaje": round(
            sum(len(v) for v in nuevos_por_grupo.values()) /
            max(sum(total_presentes_por_grupo.values()), 1) * 100, 1
        ),
        "por_grupo": sorted(grupos_tan, key=lambda x: -x["nuevos_visitantes"]),
    }

    # ── DIM 4: Conversión CRM ────────────────────────────────
    grupos_icn = []
    for g in grupos:
        casos = crm_by_group.get(g.id, [])
        total_casos = len(casos)
        resueltos = sum(1 for c in casos if (c.estado or "").upper() in {"RESUELTO_EXITO", "CERRADO_EXITO", "GANADO"})
        perdidos = sum(1 for c in casos if (c.estado or "").upper() in {"RESUELTO_PERDIDO", "CERRADO_PERDIDO", "PERDIDO"})
        icn = round(resueltos / total_casos * 100, 1) if total_casos > 0 else 0
        nuevos = len(nuevos_por_grupo.get(g.id, set()))
        grupos_icn.append({
            "grupo_id": str(g.id),
            "nombre": g.nombre,
            "casos_crm_total": total_casos,
            "casos_resueltos_exito": resueltos,
            "casos_perdidos": perdidos,
            "casos_abiertos": total_casos - resueltos - perdidos,
            "icn_porcentaje": icn,
            "clasificacion": _classify_group(nuevos, icn),
        })

    dim4 = {
        "total_casos_crm": sum(x["casos_crm_total"] for x in grupos_icn),
        "total_resueltos": sum(x["casos_resueltos_exito"] for x in grupos_icn),
        "icn_global": round(
            sum(x["casos_resueltos_exito"] for x in grupos_icn) /
            max(sum(x["casos_crm_total"] for x in grupos_icn), 1) * 100, 1
        ),
        "por_grupo": grupos_icn,
    }

    # ── DIM 5: Consistencia y Fidelidad ──────────────────────
    alertas_enfriamiento = []
    top_asistentes = []
    personas_ica = []

    for pid, atts in att_by_persona.items():
        atts_sorted = sorted(atts, key=lambda a: a.sesion_id)
        total_atts = len(atts_sorted)
        presentes = sum(1 for a in atts_sorted if _attended(a.estado))
        ica = round(presentes / total_atts * 100, 1) if total_atts > 0 else 0

        # Alerta enfriamiento: 3+ FALTO consecutivos al final
        estados_recientes = [a.estado for a in atts_sorted[-5:]]
        consecutivos = 0
        for e in reversed(estados_recientes):
            if str(e or "").upper() == "FALTO":
                consecutivos += 1
            else:
                break

        persona = personas_map.get(pid)
        nombre = persona.nombre_completo if persona else str(pid)[:8]
        grupo_nombre = ""
        for g in grupos:
            if any(p.persona_id == pid for p in parts_by_group.get(g.id, [])):
                grupo_nombre = g.nombre
                break

        personas_ica.append({"nombre": nombre, "ica": ica, "grupo": grupo_nombre, "consecutivos_falta": consecutivos})

        if consecutivos >= 3:
            alertas_enfriamiento.append({
                "persona_id": str(pid),
                "nombre": nombre,
                "grupo": grupo_nombre,
                "ausencias_consecutivas": consecutivos,
            })
        if ica >= 80 and presentes >= 3:
            top_asistentes.append({"nombre": nombre, "ica_porcentaje": ica, "sesiones_asistidas": presentes, "grupo": grupo_nombre})

    dim5 = {
        "ica_global_porcentaje": round(
            sum(x["ica"] for x in personas_ica) / max(len(personas_ica), 1), 1
        ),
        "total_personas_analizadas": len(personas_ica),
        "alertas_enfriamiento": sorted(alertas_enfriamiento, key=lambda x: -x["ausencias_consecutivas"])[:20],
        "total_alertas_enfriamiento": len(alertas_enfriamiento),
        "top_asistentes": sorted(top_asistentes, key=lambda x: -x["ica_porcentaje"])[:10],
    }

    # ── DIM 6: Eficiencia Operativa ───────────────────────────
    grupos_ics = []
    for g in grupos:
        gsess = sessions_by_group.get(g.id, [])
        proyectadas = len(gsess)
        realizadas = sum(1 for s in gsess if (s.estado or "").lower() in {"realizada", "realizado"})
        canceladas = sum(1 for s in gsess if (s.estado or "").lower() in {"cancelada", "cancelado"})
        ics = round(realizadas / proyectadas * 100, 1) if proyectadas > 0 else 0
        # Ofrendas
        ofrenda_total = sum(float(s.offering_amount or 0) for s in gsess if s.offering_amount)
        ofrenda_prom = round(ofrenda_total / max(realizadas, 1), 0)
        grupos_ics.append({
            "grupo_id": str(g.id),
            "nombre": g.nombre,
            "sesiones_proyectadas": proyectadas,
            "sesiones_realizadas": realizadas,
            "sesiones_canceladas": canceladas,
            "sesiones_pendientes": proyectadas - realizadas - canceladas,
            "ics_porcentaje": ics,
            "estado_operativo": _semaforo_ics(ics),
            "ofrenda_total": ofrenda_total,
            "ofrenda_promedio_por_sesion": ofrenda_prom,
        })

    total_proy = sum(x["sesiones_proyectadas"] for x in grupos_ics)
    total_real = sum(x["sesiones_realizadas"] for x in grupos_ics)
    dim6 = {
        "sesiones_proyectadas_total": total_proy,
        "sesiones_realizadas_total": total_real,
        "ics_global_porcentaje": round(total_real / max(total_proy, 1) * 100, 1),
        "ofrenda_total_periodo": sum(x["ofrenda_total"] for x in grupos_ics),
        "por_grupo": sorted(grupos_ics, key=lambda x: -x["ics_porcentaje"]),
    }

    # ── DIM 7: Multiplicación ─────────────────────────────────
    tpm_vals = []
    for hijo in grupos_hijos:
        padre = group_map.get(hijo.parent_group_id)
        if padre and padre.created_at and hijo.created_at:
            dias = (hijo.created_at - padre.created_at).days
            tpm_vals.append(dias / 30)

    tmg = round(len(grupos_hijos) / max(len(grupos), 1) * 100, 1)
    tpm = round(sum(tpm_vals) / len(tpm_vals), 1) if tpm_vals else None
    dim7 = {
        "grupos_iniciales": len(grupos),
        "grupos_multiplicados_periodo": len(grupos_hijos),
        "tmg_porcentaje": tmg,
        "tpm_meses_promedio": tpm,
        "estado_reproduccion": "EXPONENCIAL" if (tpm and tpm < 9) else ("SALUDABLE" if (tpm and tpm <= 18) else "ESTANCADO"),
        "detalle_multiplicaciones": [
            {
                "grupo_hijo": h.nombre,
                "grupo_padre": group_map.get(h.parent_group_id, type("", (), {"nombre": "?"})()).nombre,
                "fecha_creacion": str(h.created_at.date()) if h.created_at else None,
            }
            for h in grupos_hijos
        ],
    }

    # ── DIM 8: Liderazgo ─────────────────────────────────────
    # Promociones: personas que cambiaron a rol lider/servidor en el período
    desde_dt = _dt.datetime.combine(fecha_desde, _dt.time.min)
    promovidos = (
        db.query(models.PersonaChurchRole)
        .filter(
            models.PersonaChurchRole.persona_id.in_(persona_ids),
            models.PersonaChurchRole.church_role.in_(["LIDER", "Líder", "SERVIDOR", "Servidor", "Lider"]),
            models.PersonaChurchRole.assigned_at >= desde_dt,
        )
        .all()
    ) if persona_ids and hasattr(models, "PersonaChurchRole") else []

    # Deserción: líderes con estado_vital inactivo
    lideres_ids = [g.lider_persona_id for g in grupos if g.lider_persona_id]
    lideres_inactivos = sum(
        1 for pid in lideres_ids
        if pid in personas_map and str(personas_map[pid].estado_vital or "").upper() in {"INACTIVO", "FRIO", "DESERTOR"}
    )

    dim8 = {
        "total_lideres_asignados": len([g for g in grupos if g.lider_persona_id]),
        "lideres_inactivos": lideres_inactivos,
        "tds_porcentaje": round(lideres_inactivos / max(len(lideres_ids), 1) * 100, 1),
        "promovidos_periodo": len(promovidos),
        "irl_porcentaje": round(len(promovidos) / max(len(persona_ids), 1) * 100, 1),
        "alertas_burnout": [
            {"nombre": personas_map[pid].nombre_completo, "grupo": group_map[gid].nombre if gid in group_map else "?", "estado_vital": personas_map[pid].estado_vital}
            for gid, g in group_map.items()
            for pid in ([g.lider_persona_id] if g.lider_persona_id and g.lider_persona_id in personas_map else [])
            if str(personas_map[pid].estado_vital or "").upper() in {"INACTIVO", "FRIO", "DESERTOR"}
        ],
    }

    # ── DIM 9: Retención de Campañas ─────────────────────────
    # Personas cuyo origen_estrategia_id = strategy_id
    personas_campana = (
        db.query(models.Persona)
        .filter(models.Persona.origen_estrategia_id == strategy_id)
        .all()
    )
    retenidos = 0
    for p in personas_campana:
        atts_p = att_by_persona.get(p.id, [])
        presentes_p = sum(1 for a in atts_p if _attended(a.estado))
        if presentes_p >= 3:
            retenidos += 1

    total_campana = len(personas_campana)
    irc = round(retenidos / total_campana * 100, 1) if total_campana > 0 else 0
    dim9 = {
        "total_captados_campana": total_campana,
        "retenidos_3_sesiones": retenidos,
        "irc_porcentaje": irc,
        "semaforo": "EXCELENTE" if irc >= 70 else ("REGULAR" if irc >= 40 else "INEFICIENTE"),
    }

    # ── DIM 10: Diversidad Generacional ──────────────────────
    rangos: dict = defaultdict(int)
    spiritual_dist: dict = defaultdict(int)
    church_role_dist: dict = defaultdict(int)
    bautizados = 0
    for pid in persona_ids:
        p = personas_map.get(pid)
        if not p:
            continue
        rangos[_age_bucket(p.birthday)] += 1
        spiritual_dist[p.spiritual_status or "Sin dato"] += 1
        church_role_dist[p.church_role or "Sin dato"] += 1
        if p.is_baptized:
            bautizados += 1

    total_px = max(len(persona_ids), 1)
    idg = _shannon_entropy(dict(rangos))
    max_entropy = round(_math.log(5), 3)  # ln(5) — 5 rangos etarios
    equilibrio = round(idg / max_entropy * 100, 1) if max_entropy > 0 else 0

    dim10 = {
        "total_personas": total_px,
        "bautizados": bautizados,
        "pct_bautizados": round(bautizados / total_px * 100, 1),
        "idg": idg,
        "idg_max_posible": max_entropy,
        "equilibrio_porcentaje": equilibrio,
        "estado_equilibrio": "EQUILIBRADO" if equilibrio >= 70 else ("MODERADO" if equilibrio >= 40 else "HOMOGENEO"),
        "distribucion_etaria": dict(rangos),
        "distribucion_spiritual_status": dict(spiritual_dist),
        "distribucion_church_role": dict(church_role_dist),
    }

    # ── WEEKLY TREND (para gráficas) ─────────────────────────
    weekly: dict = defaultdict(lambda: {"presentes": 0, "ausentes": 0, "primera_vez": 0, "sesiones": 0, "ofrenda": 0.0})
    for s in sesiones:
        wk = s.fecha_sesion.strftime("%Y-%m-%d") if hasattr(s.fecha_sesion, "strftime") else str(s.fecha_sesion)[:10]
        weekly[wk]["sesiones"] += 1
        weekly[wk]["ofrenda"] += float(s.offering_amount or 0)
        for a in att_by_session.get(s.id, []):
            if _is_primera_vez(a):
                weekly[wk]["primera_vez"] += 1
            elif _attended(a.estado):
                weekly[wk]["presentes"] += 1
            else:
                weekly[wk]["ausentes"] += 1

    weekly_list = []
    for wk in sorted(weekly.keys()):
        d = weekly[wk]
        total_w = d["presentes"] + d["ausentes"] + d["primera_vez"]
        weekly_list.append({
            "semana": wk,
            **d,
            "tasa_asistencia": round((d["presentes"] + d["primera_vez"]) / max(total_w, 1) * 100, 1),
        })

    # ── RESUMEN EJECUTIVO ─────────────────────────────────────
    total_presentes_glob = sum(w["presentes"] + w["primera_vez"] for w in weekly_list)
    total_ausentes_glob = sum(w["ausentes"] for w in weekly_list)
    total_registros = total_presentes_glob + total_ausentes_glob
    resumen = {
        "estrategia_id": strategy_id,
        "periodo_semanas": weeks,
        "fecha_desde": str(fecha_desde),
        "fecha_hasta": str(fecha_hasta),
        "total_grupos": len(grupos),
        "grupos_activos": activos_count,
        "total_sesiones_periodo": len(sesiones),
        "total_participantes": len(participantes),
        "personas_unicas_analizadas": len(persona_ids),
        "tasa_asistencia_global": round(total_presentes_glob / max(total_registros, 1) * 100, 1),
        "total_primera_vez": dim3["total_nuevos_periodo"],
        "total_alertas_enfriamiento": dim5["total_alertas_enfriamiento"],
        "ofrenda_total": dim6["ofrenda_total_periodo"],
        "ics_global": dim6["ics_global_porcentaje"],
    }

    return {
        "resumen": resumen,
        "tendencia_semanal": weekly_list,
        "dim1_territorial": dim1,
        "dim2_capacidad": dim2,
        "dim3_atraccion": dim3,
        "dim4_conversion_crm": dim4,
        "dim5_fidelidad": dim5,
        "dim6_eficiencia": dim6,
        "dim7_multiplicacion": dim7,
        "dim8_liderazgo": dim8,
        "dim9_campanas": dim9,
        "dim10_demografia": dim10,
    }
