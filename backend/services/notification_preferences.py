"""Servicio de preferencias de notificación por usuario y tipo de evento.

Fase 1 del plan de notificaciones (PLAN_NOTIFICACIONES_EMAIL_CCF.md):

  - Defaults canónicos centralizados: ``DEFAULT_NOTIFICATION_PREFERENCES``.
  - ``get_or_create_user_preferences``: siembra las preferencias por defecto
    la primera vez que un usuario consulta sus ajustes (idempotente, seguro
    ante carreras via savepoint + IntegrityError).
  - ``set_preference``: upsert de una sola preferencia (Axioma 3 —
    ``user_id`` proviene SIEMPRE del actor autenticado, nunca del payload).
  - ``is_channel_enabled``: helper de consulta para el Notification Hub (Fase 2).

Canales canónicos: ``in_app``, ``email`` (extensible en Fase 4: push, WhatsApp).
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models_auth import NotificationPreference

log = logging.getLogger(__name__)

CANONICAL_CHANNELS = ("in_app", "email")

# Defaults del plan: in-app siempre ON; email OFF salvo eventos operativos
# de alta prioridad (evita spam desde el día 1).
DEFAULT_NOTIFICATION_PREFERENCES: dict[str, dict[str, bool]] = {
    event: {"in_app": True, "email": email_default}
    for event, email_default in {
        "task_assigned": True,
        "mention": True,
        "event_reminder": True,
        "task_status_changed": False,
        "comment_reply": False,
        "academy_course_update": False,
        "evangelism_followup": False,
        "survey_response": False,
        "crm_caso_update": False,
        "broadcast": False,
    }.items()
}


def _seed_defaults(db: Session, user_id: UUID, sede_id: UUID | None) -> None:
    """Inserta las preferencias por defecto del usuario si no existen.

    Idempotente: si otra request ya sembró, ignora el conflicto.
    """
    now_rows = [
        NotificationPreference(
            user_id=user_id,
            sede_id=sede_id,
            channel=channel,
            event_type=event_type,
            enabled=enabled,
        )
        for event_type, channels in DEFAULT_NOTIFICATION_PREFERENCES.items()
        for channel, enabled in channels.items()
    ]
    try:
        db.add_all(now_rows)
        db.flush()
    except IntegrityError:
        db.rollback()
        log.debug("Preferencias ya sembradas para user %s (carrera benigna)", user_id)


def get_or_create_user_preferences(
    db: Session,
    user_id: UUID,
    sede_id: UUID | None = None,
) -> list[NotificationPreference]:
    """Devuelve todas las preferencias del usuario, sembrando defaults la 1ª vez."""
    prefs = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == user_id)
        .all()
    )
    if not prefs:
        _seed_defaults(db, user_id, sede_id)
        db.commit()
        prefs = (
            db.query(NotificationPreference)
            .filter(NotificationPreference.user_id == user_id)
            .all()
        )
    return prefs


def set_preference(
    db: Session,
    user_id: UUID,
    channel: str,
    event_type: str,
    enabled: bool,
    sede_id: UUID | None = None,
) -> NotificationPreference:
    """Upsert de una preferencia (Axioma 3: user_id del actor autenticado)."""
    if channel not in CANONICAL_CHANNELS:
        raise ValueError(f"Canal no canónico: {channel!r}. Válidos: {CANONICAL_CHANNELS}")

    pref = (
        db.query(NotificationPreference)
        .filter(
            NotificationPreference.user_id == user_id,
            NotificationPreference.channel == channel,
            NotificationPreference.event_type == event_type,
        )
        .first()
    )
    if pref:
        pref.enabled = enabled
        if sede_id is not None and pref.sede_id is None:
            pref.sede_id = sede_id
    else:
        pref = NotificationPreference(
            user_id=user_id,
            sede_id=sede_id,
            channel=channel,
            event_type=event_type,
            enabled=enabled,
        )
        db.add(pref)
    db.commit()
    db.refresh(pref)
    return pref


def is_channel_enabled(
    db: Session,
    user_id: UUID,
    channel: str,
    event_type: str,
) -> bool:
    """Consulta rápida para el Notification Hub (Fase 2).

    Devuelve el valor persistido si existe fila; si no, el default canónico.
    Nunca siembra (lectura sin efectos secundarios).
    """
    pref = (
        db.query(NotificationPreference)
        .filter(
            NotificationPreference.user_id == user_id,
            NotificationPreference.channel == channel,
            NotificationPreference.event_type == event_type,
        )
        .first()
    )
    if pref is not None:
        return bool(pref.enabled)
    default_row = DEFAULT_NOTIFICATION_PREFERENCES.get(event_type, {})
    return bool(default_row.get(channel, False))
