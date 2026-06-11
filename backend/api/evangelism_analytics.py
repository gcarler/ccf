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


def _group_ids_for_strategy(db: Session, strategy_id: str, sede_id) -> list[int]:
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


def _attendance_stats(db: Session, group_ids: list[int], start, end) -> tuple[int, int]:
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


def _sessions_done_count(db: Session, group_ids: list[int], start, end) -> int:
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


def _sessions_total_count(db: Session, group_ids: list[int], start, end) -> int:
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
