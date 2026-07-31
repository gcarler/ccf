"""User notification CRUD.

Funciones para leer y mutar ``NotificacionUsuario`` ( ``auth_notifications`` ).
Todas las queries filtran por ``user_id`` (ownership). ``mark_all_notifications_read``
retorna el count de filas afectadas (A-06).

Axioma 3: cada usuario ve y modifica SÓLO sus propias notifications.
"""

import uuid
from typing import List

from sqlalchemy.orm import Session

from backend import models
from backend.crud.crm_.shared import resolve_persona_id_for_user


def get_user_notifications(
    db: Session,
    user_id: uuid.UUID | str,
    limit: int = 20,
    offset: int = 0,
) -> List[models.Notification]:
    """Lista notificaciones de un usuario, ordenadas por fecha descendente.

    Soporta paginación vía ``offset``/``limit`` (M-01).
    Resuelve ``user_id`` → ``persona_id`` vía ``resolve_persona_id_for_user``.
    """
    notification_user_id = resolve_persona_id_for_user(db, user_id)
    if notification_user_id is None:
        return []
    return (
        db.query(models.Notification)
        .filter(models.Notification.user_id == notification_user_id)
        .order_by(models.Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def mark_notification_as_read(
    db: Session,
    notification_id: uuid.UUID,
    *,
    owner_persona_id: uuid.UUID | str,
):
    """Marca una Notification como leída con ownership check (Axioma 3).

    Parámetros:
        db: sesión SQLAlchemy.
        notification_id: UUID de la Notification a marcar.
        owner_persona_id: persona_id obligatorio del caller. Si difiere de
            ``Notification.user_id`` (recipient), la Notification se considera
            fuera de scope y el CRUD retorna ``None``.

    Axioma 3 — ownership: cada usuario ve y modifica SÓLO sus propias
    notifications (BOLA-style leak prevention). Pattern consistente con
    ``_get_scoped_persona`` del CRM: 404 (no 403) para evitar existence
    leaks.

    Returns:
        La ``Notification`` actualizada (is_read=True) o ``None`` si no
        existe o no pertenece al ``owner_persona_id`` (existence-leak
        safe el caller no distingue entre ambos casos).
    """
    notification = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not notification:
        return None
    # Ownership guard: notification.user_id == owner_persona_id
    if str(notification.user_id) != str(owner_persona_id):
        # Existence-leak safe: NO se persiste mutación y se retorna None
        # para que el API layer responda 404 sin filtrar IDs existentes.
        return None
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_notifications_read(db: Session, user_id: uuid.UUID | str) -> int:
    """Marca todas las notificaciones no leídas de un usuario como leídas.

    Retorna el número de filas actualizadas (A-06: ``marked_count``).
    Si ``user_id`` no resuelve a una persona, retorna 0.
    """
    notification_user_id = resolve_persona_id_for_user(db, user_id)
    if notification_user_id is None:
        return 0
    result = (
        db.query(models.Notification)
        .filter(
            models.Notification.user_id == notification_user_id,
            models.Notification.is_read.is_(False),
        )
        .update({models.Notification.is_read: True})
    )
    db.commit()
    return result
