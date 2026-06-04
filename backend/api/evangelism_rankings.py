"""
Evangelism Rankings & Comparisons API

Endpoints:
  GET /api/evangelism/rankings/groups       — top 10 groups by attendance / growth / visitors
  GET /api/evangelism/rankings/monthly-comparison — this month vs last month
  GET /api/evangelism/rankings/leaders      — leader dashboard

Uses real column names from the canonical evangelism models (GrupoEvangelismo,
SesionGrupo, Asistencia, ParticipanteGrupo) and Persona from CRM.
"""
from __future__ import annotations

import datetime as _dt
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func as _func
from sqlalchemy.orm import Session

from backend import models
from backend.auth import require_active_user
from backend.core.database import get_db
from backend.core.tenant import require_user_sede_id

router = APIRouter()

# ────────────────────────────────────────────────────────────────────
# helpers
# ────────────────────────────────────────────────────────────────────

_ATTENDED_STATES = {"Presente", "ASISTIO", "present"}


def _month_range(year: int, month: int):
    """Return (start, end) datetimes for *month* (1-indexed)."""
    start = _dt.datetime(year, month, 1, 0, 0, 0)
    if month == 12:
        end = _dt.datetime(year + 1, 1, 1, 0, 0, 0)
    else:
        end = _dt.datetime(year, month + 1, 1, 0, 0, 0)
    return start, end


def _this_month_range():
    now = _dt.datetime.now(_dt.timezone.utc)
    return _month_range(now.year, now.month)


def _last_month_range():
    now = _dt.datetime.now(_dt.timezone.utc)
    if now.month == 1:
        return _month_range(now.year - 1, 12)
    return _month_range(now.year, now.month - 1)


def _active_groups_query(db: Session, strategy_id: Optional[str] = None, sede_id: Optional[int] = None):
    q = db.query(models.GrupoEvangelismo).filter(models.GrupoEvangelismo.activo)
    if strategy_id:
        q = q.filter(models.GrupoEvangelismo.estrategia_id == strategy_id)
    if sede_id is not None:
        q = q.filter(models.GrupoEvangelismo.sede_id == sede_id)
    return q


# ────────────────────────────────────────────────────────────────────
# GET /rankings/groups
# ────────────────────────────────────────────────────────────────────

@router.get("/rankings/groups")
def rankings_groups(
    by: str = Query("attendance", description="attendance | growth | visitors"),
    strategy_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Top-10 grupos ordenados por asistencia, crecimiento o visitantes."""

    sede_id = require_user_sede_id(db, current_user)
    groups = _active_groups_query(db, strategy_id, sede_id).all()

    this_start, this_end = _this_month_range()
    last_start, last_end = _last_month_range()

    if by == "growth":
        return _rank_by_growth(db, groups, this_start, this_end, last_start, last_end)

    if by == "visitors":
        return _rank_by_visitors(db, groups, this_start, this_end)

    # default: attendance
    return _rank_by_attendance(db, groups, this_start, this_end)


def _rank_by_attendance(db: Session, groups, start, end):
    rows = []
    for g in groups:
        # total present = asistencias with estado IN attended states this month
        present = (
            db.query(_func.count(models.Asistencia.id))
            .join(models.SesionGrupo)
            .filter(
                models.SesionGrupo.grupo_id == g.id,
                models.Asistencia.estado.in_(_ATTENDED_STATES),
                models.SesionGrupo.fecha_sesion >= start,
                models.SesionGrupo.fecha_sesion < end,
            )
            .scalar()
        )
        # total expected = total asistencia rows for this group's sessions this month
        expected = (
            db.query(_func.count(models.Asistencia.id))
            .join(models.SesionGrupo)
            .filter(
                models.SesionGrupo.grupo_id == g.id,
                models.SesionGrupo.fecha_sesion >= start,
                models.SesionGrupo.fecha_sesion < end,
            )
            .scalar()
        )
        rate = round((present / expected) * 100, 1) if expected else 0.0
        rows.append(
            {
                "group_id": g.id,
                "group_name": g.nombre,
                "attendance_rate": rate,
                "present": present or 0,
                "expected": expected or 0,
            }
        )
    rows.sort(key=lambda r: r["attendance_rate"], reverse=True)
    return rows[:10]


def _rank_by_growth(db: Session, groups, this_start, this_end, last_start, last_end):
    rows = []
    for g in groups:
        # members this month = active ParticipanteGrupo created before this month's end
        this_count = (
            db.query(_func.count(models.ParticipanteGrupo.id))
            .filter(
                models.ParticipanteGrupo.grupo_id == g.id,
                models.ParticipanteGrupo.activo,
                models.ParticipanteGrupo.fecha_ingreso < this_end,
            )
            .scalar()
        )
        # members last month = active ParticipanteGrupo created before last month's end
        last_count = (
            db.query(_func.count(models.ParticipanteGrupo.id))
            .filter(
                models.ParticipanteGrupo.grupo_id == g.id,
                models.ParticipanteGrupo.activo,
                models.ParticipanteGrupo.fecha_ingreso < last_end,
            )
            .scalar()
        )
        growth = (this_count or 0) - (last_count or 0)
        rows.append(
            {
                "group_id": g.id,
                "group_name": g.nombre,
                "growth": growth,
                "current_members": this_count or 0,
                "previous_members": last_count or 0,
            }
        )
    rows.sort(key=lambda r: r["growth"], reverse=True)
    return rows[:10]


def _rank_by_visitors(db: Session, groups, start, end):
    rows = []
    for g in groups:
        visitors = (
            db.query(_func.count(models.ParticipanteGrupo.id))
            .filter(
                models.ParticipanteGrupo.grupo_id == g.id,
                models.ParticipanteGrupo.rol_base == "visitante",
                models.ParticipanteGrupo.fecha_ingreso >= start,
                models.ParticipanteGrupo.fecha_ingreso < end,
            )
            .scalar()
        )
        rows.append(
            {
                "group_id": g.id,
                "group_name": g.nombre,
                "visitors": visitors or 0,
            }
        )
    rows.sort(key=lambda r: r["visitors"], reverse=True)
    return rows[:10]


# ────────────────────────────────────────────────────────────────────
# GET /rankings/monthly-comparison
# ────────────────────────────────────────────────────────────────────

@router.get("/rankings/monthly-comparison")
def monthly_comparison(
    strategy_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Comparativa mensual: este mes vs mes pasado."""
    sede_id = require_user_sede_id(db, current_user)
    this_start, this_end = _this_month_range()
    last_start, last_end = _last_month_range()

    def _stats(start, end):
        base_filter = models.GrupoEvangelismo.activo
        if sede_id is not None:
            base_filter = (models.GrupoEvangelismo.activo) & (models.GrupoEvangelismo.sede_id == sede_id)

        # sessions
        sess_q = (
            db.query(_func.count(models.SesionGrupo.id))
            .join(models.GrupoEvangelismo)
            .filter(base_filter)
        )
        if strategy_id:
            sess_q = sess_q.filter(models.GrupoEvangelismo.estrategia_id == strategy_id)
        sess_q = sess_q.filter(
            models.SesionGrupo.fecha_sesion >= start,
            models.SesionGrupo.fecha_sesion < end,
        )
        sessions = sess_q.scalar() or 0

        # total attendance (present)
        att_q = (
            db.query(_func.count(models.Asistencia.id))
            .join(models.SesionGrupo)
            .join(models.GrupoEvangelismo)
            .filter(
                base_filter,
                models.Asistencia.estado.in_(_ATTENDED_STATES),
                models.SesionGrupo.fecha_sesion >= start,
                models.SesionGrupo.fecha_sesion < end,
            )
        )
        if strategy_id:
            att_q = att_q.filter(models.GrupoEvangelismo.estrategia_id == strategy_id)
        total_attendance = att_q.scalar() or 0

        # total expected (all asistencia rows)
        exp_q = (
            db.query(_func.count(models.Asistencia.id))
            .join(models.SesionGrupo)
            .join(models.GrupoEvangelismo)
            .filter(
                base_filter,
                models.SesionGrupo.fecha_sesion >= start,
                models.SesionGrupo.fecha_sesion < end,
            )
        )
        if strategy_id:
            exp_q = exp_q.filter(models.GrupoEvangelismo.estrategia_id == strategy_id)
        total_expected = exp_q.scalar() or 0

        avg_rate = round((total_attendance / total_expected) * 100, 1) if total_expected else 0.0

        # new visitors
        vis_q = (
            db.query(_func.count(models.ParticipanteGrupo.id))
            .join(models.GrupoEvangelismo)
            .filter(
                base_filter,
                models.ParticipanteGrupo.rol_base == "visitante",
                models.ParticipanteGrupo.fecha_ingreso >= start,
                models.ParticipanteGrupo.fecha_ingreso < end,
            )
        )
        if strategy_id:
            vis_q = vis_q.filter(models.GrupoEvangelismo.estrategia_id == strategy_id)
        new_visitors = vis_q.scalar() or 0

        # new conversions — people who changed rol_anterior this month in HistorialEmbudo
        conv_q = (
            db.query(_func.count(models.HistorialEmbudo.id))
            .filter(
                models.HistorialEmbudo.fecha_cambio >= start,
                models.HistorialEmbudo.fecha_cambio < end,
            )
        )
        new_conversions = conv_q.scalar() or 0

        return {
            "total_sessions": sessions,
            "total_attendance": total_attendance,
            "total_expected": total_expected,
            "avg_rate": avg_rate,
            "new_visitors": new_visitors,
            "new_conversions": new_conversions,
        }

    current = _stats(this_start, this_end)
    previous = _stats(last_start, last_end)

    return {
        "current_month": current,
        "previous_month": previous,
    }


# ────────────────────────────────────────────────────────────────────
# GET /rankings/leaders
# ────────────────────────────────────────────────────────────────────

@router.get("/rankings/leaders")
def rankings_leaders(
    strategy_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Tablero de líderes con nombre, grupo, % asistencia, miembros, visitantes este mes."""
    sede_id = require_user_sede_id(db, current_user)
    this_start, this_end = _this_month_range()

    groups = _active_groups_query(db, strategy_id, sede_id).all()
    rows: list[dict] = []

    for g in groups:
        # leader name
        leader_name = (
            db.query(models.Persona)
            .filter(models.Persona.id == g.lider_persona_id)
            .first()
        )
        leader_display = (
            f"{leader_name.first_name} {leader_name.last_name}"
            if leader_name
            else "Sin líder"
        )

        # attendance rate for this group this month
        present = (
            db.query(_func.count(models.Asistencia.id))
            .join(models.SesionGrupo)
            .filter(
                models.SesionGrupo.grupo_id == g.id,
                models.Asistencia.estado.in_(_ATTENDED_STATES),
                models.SesionGrupo.fecha_sesion >= this_start,
                models.SesionGrupo.fecha_sesion < this_end,
            )
            .scalar()
        ) or 0
        expected = (
            db.query(_func.count(models.Asistencia.id))
            .join(models.SesionGrupo)
            .filter(
                models.SesionGrupo.grupo_id == g.id,
                models.SesionGrupo.fecha_sesion >= this_start,
                models.SesionGrupo.fecha_sesion < this_end,
            )
            .scalar()
        ) or 0
        attendance_pct = round((present / expected) * 100, 1) if expected else 0.0

        # total members
        members = (
            db.query(_func.count(models.ParticipanteGrupo.id))
            .filter(
                models.ParticipanteGrupo.grupo_id == g.id,
                models.ParticipanteGrupo.activo,
            )
            .scalar()
        ) or 0

        # visitors this month
        visitors = (
            db.query(_func.count(models.ParticipanteGrupo.id))
            .filter(
                models.ParticipanteGrupo.grupo_id == g.id,
                models.ParticipanteGrupo.rol_base == "visitante",
                models.ParticipanteGrupo.fecha_ingreso >= this_start,
                models.ParticipanteGrupo.fecha_ingreso < this_end,
            )
            .scalar()
        ) or 0

        rows.append(
            {
                "leader_name": leader_display,
                "leader_id": str(g.lider_persona_id) if g.lider_persona_id else None,
                "group_id": g.id,
                "group_name": g.nombre,
                "attendance_pct": attendance_pct,
                "members": members,
                "visitors_this_month": visitors,
            }
        )

    rows.sort(key=lambda r: r["attendance_pct"], reverse=True)
    return rows
