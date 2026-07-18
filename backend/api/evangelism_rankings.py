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
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func as _func
from sqlalchemy.orm import Session

from backend import models
from backend.api.evangelism_shared import ATTENDED_STATES
from backend.core.database import get_db
from backend.core.permissions import require_evangelism_read
from backend.core.tenant import require_user_sede_id

router = APIRouter()

# ────────────────────────────────────────────────────────────────────
# helpers
# ────────────────────────────────────────────────────────────────────

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


def _active_groups_query(db: Session, strategy_id: Optional[UUID] = None, sede_id: Optional[UUID] = None):
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
    strategy_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
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
    group_ids = [g.id for g in groups]
    attendance_rows = []
    if group_ids:
        attendance_rows = (
            db.query(models.SesionGrupo.grupo_id, models.Asistencia.estado)
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
    present_by_group = {group_id: 0 for group_id in group_ids}
    expected_by_group = {group_id: 0 for group_id in group_ids}
    for group_id, estado in attendance_rows:
        expected_by_group[group_id] = expected_by_group.get(group_id, 0) + 1
        if estado in ATTENDED_STATES:
            present_by_group[group_id] = present_by_group.get(group_id, 0) + 1

    rows = []
    for g in groups:
        present = present_by_group.get(g.id, 0)
        expected = expected_by_group.get(g.id, 0)
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
    group_ids = [g.id for g in groups]
    this_map = dict(
        db.query(models.ParticipanteGrupo.grupo_id, _func.count(models.ParticipanteGrupo.id))
        .filter(models.ParticipanteGrupo.grupo_id.in_(group_ids) if group_ids else False)
        .filter(
            models.ParticipanteGrupo.activo,
            models.ParticipanteGrupo.fecha_ingreso < this_end,
            models.ParticipanteGrupo.deleted_at.is_(None),
        )
        .group_by(models.ParticipanteGrupo.grupo_id)
        .all()
    )
    last_map = dict(
        db.query(models.ParticipanteGrupo.grupo_id, _func.count(models.ParticipanteGrupo.id))
        .filter(models.ParticipanteGrupo.grupo_id.in_(group_ids) if group_ids else False)
        .filter(
            models.ParticipanteGrupo.activo,
            models.ParticipanteGrupo.fecha_ingreso < last_end,
            models.ParticipanteGrupo.deleted_at.is_(None),
        )
        .group_by(models.ParticipanteGrupo.grupo_id)
        .all()
    )
    rows = []
    for g in groups:
        this_count = this_map.get(g.id, 0)
        last_count = last_map.get(g.id, 0)
        growth = this_count - last_count
        rows.append(
            {
                "group_id": g.id,
                "group_name": g.nombre,
                "growth": growth,
                "current_personas": this_count or 0,
                "previous_personas": last_count or 0,
            }
        )
    rows.sort(key=lambda r: r["growth"], reverse=True)
    return rows[:10]


def _rank_by_visitors(db: Session, groups, start, end):
    group_ids = [g.id for g in groups]
    visitors_map = dict(
        db.query(models.ParticipanteGrupo.grupo_id, _func.count(models.ParticipanteGrupo.id))
        .filter(models.ParticipanteGrupo.grupo_id.in_(group_ids) if group_ids else False)
        .filter(
            models.ParticipanteGrupo.rol_base == "visitante",
            models.ParticipanteGrupo.fecha_ingreso >= start,
            models.ParticipanteGrupo.fecha_ingreso < end,
            models.ParticipanteGrupo.deleted_at.is_(None),
        )
        .group_by(models.ParticipanteGrupo.grupo_id)
        .all()
    )
    rows = []
    for g in groups:
        visitors = visitors_map.get(g.id, 0)
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
    strategy_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
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
            models.SesionGrupo.deleted_at.is_(None),
        )
        sessions = sess_q.scalar() or 0

        # total attendance (present)
        att_q = (
            db.query(_func.count(models.Asistencia.id))
            .join(models.SesionGrupo)
            .join(models.GrupoEvangelismo)
            .filter(
                base_filter,
                models.Asistencia.estado.in_(ATTENDED_STATES),
                models.SesionGrupo.fecha_sesion >= start,
                models.SesionGrupo.fecha_sesion < end,
                models.SesionGrupo.deleted_at.is_(None),
                models.Asistencia.deleted_at.is_(None),
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
                models.SesionGrupo.deleted_at.is_(None),
                models.Asistencia.deleted_at.is_(None),
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
                models.ParticipanteGrupo.deleted_at.is_(None),
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
                models.HistorialEmbudo.deleted_at.is_(None),
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
    strategy_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    """Tablero de líderes con nombre, grupo, % asistencia, personas, visitantes este mes."""
    sede_id = require_user_sede_id(db, current_user)
    this_start, this_end = _this_month_range()

    groups = _active_groups_query(db, strategy_id, sede_id).all()
    group_ids = [g.id for g in groups]
    leader_ids = [g.lider_persona_id for g in groups if g.lider_persona_id]
    leader_map = {}
    if leader_ids:
        leader_map = {
            persona.id: persona
            for persona in db.query(models.Persona).filter(models.Persona.id.in_(leader_ids)).all()
        }
    attendance_rows = []
    if group_ids:
        attendance_rows = (
            db.query(models.SesionGrupo.grupo_id, models.Asistencia.estado)
            .join(models.Asistencia, models.Asistencia.sesion_id == models.SesionGrupo.id)
            .filter(
                models.SesionGrupo.grupo_id.in_(group_ids),
                models.SesionGrupo.fecha_sesion >= this_start,
                models.SesionGrupo.fecha_sesion < this_end,
                models.SesionGrupo.deleted_at.is_(None),
                models.Asistencia.deleted_at.is_(None),
            )
            .all()
        )
    present_by_group = {group_id: 0 for group_id in group_ids}
    expected_by_group = {group_id: 0 for group_id in group_ids}
    for group_id, estado in attendance_rows:
        expected_by_group[group_id] = expected_by_group.get(group_id, 0) + 1
        if estado in ATTENDED_STATES:
            present_by_group[group_id] = present_by_group.get(group_id, 0) + 1
    personas_by_group = dict(
        db.query(models.ParticipanteGrupo.grupo_id, _func.count(models.ParticipanteGrupo.id))
        .filter(models.ParticipanteGrupo.grupo_id.in_(group_ids) if group_ids else False)
        .filter(models.ParticipanteGrupo.activo, models.ParticipanteGrupo.deleted_at.is_(None))
        .group_by(models.ParticipanteGrupo.grupo_id)
        .all()
    )
    visitors_by_group = dict(
        db.query(models.ParticipanteGrupo.grupo_id, _func.count(models.ParticipanteGrupo.id))
        .filter(models.ParticipanteGrupo.grupo_id.in_(group_ids) if group_ids else False)
        .filter(
            models.ParticipanteGrupo.rol_base == "visitante",
            models.ParticipanteGrupo.fecha_ingreso >= this_start,
            models.ParticipanteGrupo.fecha_ingreso < this_end,
            models.ParticipanteGrupo.deleted_at.is_(None),
        )
        .group_by(models.ParticipanteGrupo.grupo_id)
        .all()
    )
    rows: list[dict] = []

    for g in groups:
        # leader name
        leader_name = leader_map.get(g.lider_persona_id)
        leader_display = (
            f"{leader_name.first_name} {leader_name.last_name}"
            if leader_name
            else "Sin líder"
        )

        present = present_by_group.get(g.id, 0)
        expected = expected_by_group.get(g.id, 0)
        attendance_pct = round((present / expected) * 100, 1) if expected else 0.0

        # total personas
        personas = personas_by_group.get(g.id, 0)

        # visitors this month
        visitors = visitors_by_group.get(g.id, 0)

        rows.append(
            {
                "leader_name": leader_display,
                "leader_id": str(g.lider_persona_id) if g.lider_persona_id else None,
                "group_id": g.id,
                "group_name": g.nombre,
                "attendance_pct": attendance_pct,
                "personas": personas,
                "visitors_this_month": visitors,
            }
        )

    rows.sort(key=lambda r: r["attendance_pct"], reverse=True)
    return rows
