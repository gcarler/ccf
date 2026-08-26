"""Academy event notifications.

The platform currently runs FastAPI background tasks rather than an external
Celery/RQ broker. This adapter keeps email delivery outside the request while
persisting the in-app notification in the Academy transaction.
"""

from __future__ import annotations

from html import escape
from typing import Any
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from backend import models
from backend.services.comment_notifications import create_notification
from backend.services.email import send_email


def _send_academy_email(to: str, subject: str, title: str, content: str, url: str | None) -> None:
    link = f'<p><a href="{escape(url)}">Abrir Academy</a></p>' if url else ""
    html = (
        '<div style="font-family:Arial,sans-serif;line-height:1.6">'
        f"<h2>{escape(title)}</h2><p>{escape(content)}</p>{link}</div>"
    )
    send_email(to=to, subject=subject, html=html, text=f"{title}\n\n{content}")


def queue_academy_notification(
    db: Session,
    background_tasks: BackgroundTasks,
    *,
    recipient_id: UUID | str | Any,
    title: str,
    content: str,
    subject: str,
    url: str | None = None,
    sede_id: UUID | str | Any | None = None,
) -> bool:
    """Persist an inbox event and schedule its email delivery."""
    recipient = db.query(models.Usuario).filter(models.Usuario.id == recipient_id).first()
    if recipient is None:
        return False

    body = f"{content}\n{url}" if url else content
    create_notification(db, user_id=recipient.id, sede_id=sede_id, title=title, content=body)
    if recipient.email:
        background_tasks.add_task(
            _send_academy_email,
            str(recipient.email), subject, title, content, url,
        )
    return True
