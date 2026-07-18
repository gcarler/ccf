"""
Evangelism Notifications API — Send reminders for upcoming sessions and
unreported attendance.
"""

from __future__ import annotations

import datetime
import logging
import uuid
from typing import Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models
from backend.api.evangelism_shared import session_read_only_options, session_read_value, utc_now
from backend.core.database import get_db
from backend.core.permissions import require_evangelism_manage
from backend.core.tenant import require_user_sede_id

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/notifications/send-reminders", response_model=Dict)
def send_reminders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    """Send notifications to group leaders for:

    1. Sessions scheduled for tomorrow (PENDIENTE).
    2. Groups that haven't reported attendance (REALIZADA session)
       in the last 7 days.
    """
    now = utc_now()
    tomorrow = (now + datetime.timedelta(days=1)).date()
    seven_days_ago = now - datetime.timedelta(days=7)
    today_start = datetime.datetime.combine(now.date(), datetime.time.min, tzinfo=datetime.timezone.utc)
    today_end = datetime.datetime.combine(now.date(), datetime.time.max, tzinfo=datetime.timezone.utc)

    notifications_created = 0
    details: List[Dict] = []

    def _notification_already_sent(user_id, title: str, content: str) -> bool:
        return (
            db.query(models.NotificacionUsuario.id)
            .filter(
                models.NotificacionUsuario.user_id == user_id,
                models.NotificacionUsuario.title == title,
                models.NotificacionUsuario.content == content,
                models.NotificacionUsuario.created_at >= today_start,
                models.NotificacionUsuario.created_at <= today_end,
            )
            .first()
            is not None
        )

    # ── 1. Sessions scheduled for tomorrow ──────────────────────────
    tomorrow_start = datetime.datetime.combine(tomorrow, datetime.time.min, tzinfo=datetime.timezone.utc)
    tomorrow_end = datetime.datetime.combine(tomorrow, datetime.time.max, tzinfo=datetime.timezone.utc)

    user_sede_id = require_user_sede_id(db, current_user)
    sessions_q = (
        db.query(models.SesionGrupo)
        .options(session_read_only_options(db))
        .join(models.GrupoEvangelismo, models.GrupoEvangelismo.id == models.SesionGrupo.grupo_id)
        .filter(
            models.SesionGrupo.deleted_at.is_(None),
            models.GrupoEvangelismo.deleted_at.is_(None),
            models.SesionGrupo.fecha_sesion >= tomorrow_start,
            models.SesionGrupo.fecha_sesion <= tomorrow_end,
            func.lower(models.SesionGrupo.estado) == "pendiente",
        )
    )
    sessions_q = sessions_q.filter(models.GrupoEvangelismo.sede_id == user_sede_id)
    sessions_tomorrow = sessions_q.all()

    group_ids_tomorrow = {s.grupo_id for s in sessions_tomorrow}
    groups_map: Dict[uuid.UUID, models.GrupoEvangelismo] = {}

    if group_ids_tomorrow:
        groups = (
            db.query(models.GrupoEvangelismo)
            .filter(
                models.GrupoEvangelismo.id.in_(list(group_ids_tomorrow)),
                models.GrupoEvangelismo.deleted_at.is_(None),
            )
            .all()
        )
        groups_map = {g.id: g for g in groups}

    # Collect leader persona ids and verify they have auth_users entries
    _leader_ids_for_sessions: set[uuid.UUID] = set()
    for session in sessions_tomorrow:
        group = groups_map.get(session.grupo_id)
        if group and group.lider_persona_id:
            _leader_ids_for_sessions.add(group.lider_persona_id)

    # Pre-fetch which leaders have auth_users accounts
    _auth_user_ids: set[uuid.UUID] = set()
    if _leader_ids_for_sessions:
        _auth_user_ids = {
            row[0]
            for row in db.query(models.Usuario.id)
            .filter(models.Usuario.id.in_(list(_leader_ids_for_sessions)))
            .all()
        }

    for session in sessions_tomorrow:
        group = groups_map.get(session.grupo_id)
        if not group or not group.lider_persona_id:
            continue
        if group.lider_persona_id not in _auth_user_ids:
            continue

        title = "Recordatorio de sesión de evangelismo"
        content = (
            f"Tienes una sesión programada para mañana "
            f"({tomorrow.strftime('%d/%m/%Y')}) en el grupo "
            f"\"{group.nombre or group.codigo}\". "
            f"Tema: {session_read_value(session, 'tema_estudio') or session_read_value(session, 'topic') or 'No especificado'}. "
            f"Por favor confirma tu asistencia y prepara el material necesario."
        )

        notification = models.NotificacionUsuario(
            user_id=group.lider_persona_id,
            title=title,
            content=content,
        )
        if _notification_already_sent(group.lider_persona_id, title, content):
            continue
        db.add(notification)
        notifications_created += 1
        details.append(
            {
                "type": "session_reminder",
                "group_id": group.id,
                "group_name": group.nombre,
                "session_id": session.id,
                "leader_persona_id": str(group.lider_persona_id),
            }
        )

    # ── 2. Groups without attendance report in 7+ days ──────────────
    recent_report_q = (
        db.query(models.SesionGrupo.grupo_id)
        .join(models.GrupoEvangelismo, models.GrupoEvangelismo.id == models.SesionGrupo.grupo_id)
        .filter(
            models.SesionGrupo.deleted_at.is_(None),
            models.GrupoEvangelismo.deleted_at.is_(None),
            func.lower(models.SesionGrupo.estado) == "realizada",
            models.SesionGrupo.fecha_sesion >= seven_days_ago,
        )
    )
    if user_sede_id:
        recent_report_q = recent_report_q.filter(models.GrupoEvangelismo.sede_id == user_sede_id)

    groups_with_recent_report = recent_report_q.distinct().subquery()

    inactive_groups_q = db.query(models.GrupoEvangelismo).filter(
        models.GrupoEvangelismo.activo,
        models.GrupoEvangelismo.deleted_at.is_(None),
        models.GrupoEvangelismo.lider_persona_id.isnot(None),
        ~models.GrupoEvangelismo.id.in_(db.query(groups_with_recent_report.c.grupo_id)),
    )
    if user_sede_id:
        inactive_groups_q = inactive_groups_q.filter(models.GrupoEvangelismo.sede_id == user_sede_id)
    inactive_groups = inactive_groups_q.all()

    # Collect leader ids for inactive groups and verify auth_users
    _inactive_leader_ids: set[uuid.UUID] = set()
    for group in inactive_groups:
        if group.lider_persona_id:
            _inactive_leader_ids.add(group.lider_persona_id)

    _inactive_auth_ids: set[uuid.UUID] = set()
    if _inactive_leader_ids:
        _inactive_auth_ids = {
            row[0]
            for row in db.query(models.Usuario.id)
            .filter(models.Usuario.id.in_(list(_inactive_leader_ids)))
            .all()
        }

    for group in inactive_groups:
        if not group.lider_persona_id:
            continue
        if group.lider_persona_id not in _inactive_auth_ids:
            continue
        # Avoid duplicate: already notified for tomorrow's session
        if group.id in group_ids_tomorrow:
            continue

        title = "Falta de reporte de asistencia"
        content = (
            f"No has reportado asistencia para el grupo "
            f"\"{group.nombre or group.codigo}\" en los últimos 7 días. "
            f"Por favor registra la asistencia de las sesiones realizadas "
            f"para mantener el seguimiento actualizado."
        )

        notification = models.NotificacionUsuario(
            user_id=group.lider_persona_id,
            title=title,
            content=content,
        )
        if _notification_already_sent(group.lider_persona_id, title, content):
            continue
        db.add(notification)
        notifications_created += 1
        details.append(
            {
                "type": "attendance_reminder",
                "group_id": group.id,
                "group_name": group.nombre,
                "leader_persona_id": str(group.lider_persona_id),
            }
        )

    db.commit()

    return {
        "success": True,
        "notifications_created": notifications_created,
        "details": details,
        "sessions_tomorrow_count": len(sessions_tomorrow),
        "inactive_groups_count": len(inactive_groups),
    }
