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
from sqlalchemy.orm import Session

from backend import models
from backend.auth import require_pastor_or_admin
from backend.core.database import get_db
from backend.api.evangelism_shared import utc_now

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/notifications/send-reminders", response_model=Dict)
def send_reminders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Send notifications to group leaders for:

    1. Sessions scheduled for tomorrow (PENDIENTE).
    2. Groups that haven't reported attendance (REALIZADA session)
       in the last 7 days.
    """
    now = utc_now()
    tomorrow = (now + datetime.timedelta(days=1)).date()
    seven_days_ago = now - datetime.timedelta(days=7)

    notifications_created = 0
    details: List[Dict] = []

    # ── 1. Sessions scheduled for tomorrow ──────────────────────────
    tomorrow_start = datetime.datetime.combine(tomorrow, datetime.time.min)
    tomorrow_end = datetime.datetime.combine(tomorrow, datetime.time.max)

    sessions_tomorrow = (
        db.query(models.SesionGrupo)
        .filter(
            models.SesionGrupo.fecha_sesion >= tomorrow_start,
            models.SesionGrupo.fecha_sesion <= tomorrow_end,
            models.SesionGrupo.estado == "PENDIENTE",
        )
        .all()
    )

    group_ids_tomorrow: set[int] = {s.grupo_id for s in sessions_tomorrow}
    groups_map: Dict[int, models.GrupoEvangelismo] = {}

    if group_ids_tomorrow:
        groups = (
            db.query(models.GrupoEvangelismo)
            .filter(models.GrupoEvangelismo.id.in_(list(group_ids_tomorrow)))
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
            f"Tema: {session.tema_estudio or 'No especificado'}. "
            f"Por favor confirma tu asistencia y prepara el material necesario."
        )

        notification = models.NotificacionUsuario(
            user_id=group.lider_persona_id,
            title=title,
            content=content,
        )
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
    groups_with_recent_report = (
        db.query(models.SesionGrupo.grupo_id)
        .filter(
            models.SesionGrupo.estado == "REALIZADA",
            models.SesionGrupo.fecha_sesion >= seven_days_ago,
        )
        .distinct()
        .subquery()
    )

    inactive_groups = (
        db.query(models.GrupoEvangelismo)
        .filter(
            models.GrupoEvangelismo.activo == True,
            models.GrupoEvangelismo.lider_persona_id.isnot(None),
            ~models.GrupoEvangelismo.id.in_(
                db.query(groups_with_recent_report.c.grupo_id)
            ),
        )
        .all()
    )

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