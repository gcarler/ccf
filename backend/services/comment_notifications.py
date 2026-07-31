"""Helpers for comment mentions and notifications."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, List

from backend.models_shared import _utcnow

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _to_uuid(val: Any) -> uuid.UUID | None:
    if not val:
        return None
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, AttributeError):
        return None


def notify_mention(
    db: "Session",
    mention_ids: List[Any],
    author_id: Any,
    title: str,
    content: str,
    url: str,
    sede_id: Any,
) -> None:
    """Create in-app notifications for every user mentioned in a comment.

    Args:
        db: SQLAlchemy session.
        mention_ids: list of persona/auth_user UUIDs to notify.
        author_id: persona UUID of the comment author (excluded from notifications).
        title: notification title.
        content: notification body content.
        url: deep link to the commented entity.
        sede_id: optional sede scope for the notification row.
    """
    from backend import models

    author_uuid = _to_uuid(author_id)
    sede_uuid = _to_uuid(sede_id)
    seen: set[uuid.UUID] = set()

    for raw in mention_ids:
        user_uuid = _to_uuid(raw)
        if not user_uuid or user_uuid in seen:
            continue
        if user_uuid == author_uuid:
            continue
        seen.add(user_uuid)
        db.add(
            models.NotificacionUsuario(
                user_id=user_uuid,
                sede_id=sede_uuid,
                title=title,
                content=content,
                is_read=False,
                created_at=_utcnow(),
            )
        )
