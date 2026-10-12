"""Notification Hub — punto único de fan-out de notificaciones (Fase 2).

Toda la plataforma debe notificar vía ``notify()`` (no mediante send_email
directo). El hub:

  1. Crea la notificación in-app (auth_notifications) vía crud existente.
  2. Consulta preferencias (notification_preferences) por canal.
  3. Dedupe: un dedupe_key idéntico no genera dos notificaciones/email
     (protección anti-spama por reintento del llamador).
  4. Si el canal email está habilitado, agenda una fila pending en
     notification_deliveries; el worker entrega con backoff.

Señal de diseño: los productores (tareas, menciones, agenda, Academy...)
NUNCA mandan email directo — solo llaman a ``notify()``.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from backend.models_auth import NotificacionUsuario
from backend.models_notifications import NotificationDelivery
from backend.services import email as email_svc
from backend.services.notification_preferences import is_channel_enabled

log = logging.getLogger(__name__)

# Reintentos máximos de la entrega email (backoff exponencial en worker).
MAX_EMAIL_ATTEMPTS = 3
# Delay base entre reintentos (segundos) — el worker usa 2**attempt * base.
BACKOFF_BASE_SECONDS = 30


def _create_in_app(
    db: Session,
    user_id: UUID,
    *,
    title: str,
    content: str,
    target_url: str | None,
    sede_id: UUID | None,
) -> NotificacionUsuario:
    notif = NotificacionUsuario(
        user_id=user_id,
        sede_id=sede_id,
        title=title[:200],
        content=content,
        target_url=target_url[:512] if target_url else None,
    )
    db.add(notif)
    db.flush()
    return notif


def notify(
    db: Session,
    user_ids: Sequence[UUID | str],
    *,
    event_type: str,
    title: str,
    content: str,
    target_url: str | None = None,
    sede_id: UUID | None = None,
    dedupe_key: str | None = None,
    channels: Iterable[str] = ("in_app", "email"),
    email_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Notifica un evento a una lista de usuarios según sus preferencias.

    Args:
        user_ids: personas destino (kernel de personas, Axioma 1).
        event_type: clave canónica (task_assigned, mention,...) que mapea a
            NotificationPreference.event_type.
        email_context: datos para renderizar el email (plantilla + kwargs);
            el worker los consume. Si es None, se genera un email simple
            título + contenido.
    Returns:
        {"created": n_notifs, "emails_queued": n, "deduped": n}
    """
    channels = tuple(channels)
    stats = {"created": 0, "emails_queued": 0, "deduped": 0}

    for raw_id in user_ids:
        try:
            user_id = raw_id if isinstance(raw_id, UUID) else UUID(str(raw_id))
        except (ValueError, TypeError):
            log.warning("notify: user_id inválido %r ignorado", raw_id)
            continue

        # Dedupe: si ya existe una notificación reciente con este dedupe_key
        # para el usuario, omitir (el llamador reintenta demasiado rápido).
        if dedupe_key:
            # Usamos target_url como campo auxiliar: dedupe_key va como sufijo.
            existing = (
                db.query(NotificacionUsuario)
                .filter(
                    NotificacionUsuario.user_id == user_id,
                    NotificacionUsuario.title == title[:200],
                    NotificacionUsuario.target_url == _dedupe_target(dedupe_key, target_url),
                )
                .first()
            )
            if existing:
                stats["deduped"] += 1
                continue

        wanted_in_app = "in_app" in channels and is_channel_enabled(
            db, user_id, "in_app", event_type
        )
        wanted_email = "email" in channels and is_channel_enabled(
            db, user_id, "email", event_type
        )

        if not wanted_in_app and not wanted_email:
            # Usuario silenció ambos canales para este evento.
            continue

        in_app_notif: NotificacionUsuario | None = None
        if wanted_in_app:
            in_app_notif = _create_in_app(
                db,
                user_id,
                title=title,
                content=content,
                target_url=_dedupe_target(dedupe_key, target_url) if dedupe_key else target_url,
                sede_id=sede_id,
            )
            stats["created"] += 1

        if wanted_email:
            if in_app_notif is None:
                # Solo email: igualmente creamos la notificación in-app como
                # registro maestro para la entrega (trazabilidad coherente).
                in_app_notif = _create_in_app(
                    db,
                    user_id,
                    title=title,
                    content=content,
                    target_url=_dedupe_target(dedupe_key, target_url) if dedupe_key else target_url,
                    sede_id=sede_id,
                )
                stats["created"] += 1
            db.add(
                NotificationDelivery(
                    notification_id=in_app_notif.id,
                    user_id=user_id,
                    channel="email",
                    recipient="",  # el worker resuelve el email del usuario
                    status="pending",
                    event_type=event_type,
                )
            )
            stats["emails_queued"] += 1

    db.commit()
    return stats


def _dedupe_target(dedupe_key: str, target_url: str | None) -> str | None:
    """Guarda dedupe_key como sufijo del target_url (dedupe por fila)."""
    base = target_url or ""
    suffix = f"#dedupe:{dedupe_key}"
    if suffix in base:
        return base
    out = f"{base}{suffix}" if not base else base + suffix
    return out[:512]


def suppress_pending_for_notification(db: Session, notification_id: UUID) -> int:
    """Fase 3: suprime entregas pending si el usuario ya leyó la notificación."""
    rows = (
        db.query(NotificationDelivery)
        .filter(
            NotificationDelivery.notification_id == notification_id,
            NotificationDelivery.status == "pending",
        )
        .all()
    )
    for row in rows:
        row.status = "suppressed"
        row.read_before_send = True
    if rows:
        db.commit()
    return len(rows)


def deliver_pending(
    db: Session,
    max_batch: int = 50,
    max_attempts: int = MAX_EMAIL_ATTEMPTS,
) -> dict[str, int]:
    """Worker: entrega emails pending con backoff exponencial.

    Estrategia: obtiene pending cuyo attempts < max_attempts, resuelve el
    email de destino del usuario, renderiza el cuerpo y envía por SMTP.
    Marca sent/failed según resultado. El scheduling real (cron/celery)
    debe invocar esta función periódicamente; aquí solo la lógica.
    """
    import datetime as _dt

    from backend.models_auth import Usuario

    pending = (
        db.query(NotificationDelivery)
        .filter(
            NotificationDelivery.status == "pending",
            NotificationDelivery.attempts < max_attempts,
        )
        .limit(max_batch)
        .all()
    )
    out = {"sent": 0, "failed": 0, "skipped_backoff": 0}

    for row in pending:
        # Backoff: si ya tiene intentos, exigir que hayan pasado 2^n * base seg.
        if row.attempts > 0 and row.created_at is not None:
            wait = _dt.timedelta(seconds=BACKOFF_BASE_SECONDS * (2 ** (row.attempts - 1)))
            age = _dt.datetime.now(_dt.timezone.utc) - row.created_at
            if age < wait:
                out["skipped_backoff"] += 1
                continue

        user = db.query(Usuario).filter(Usuario.id == row.user_id).first()
        recipient = getattr(user, "email", None) or row.recipient
        if not recipient:
            row.status = "failed"
            row.error = "no email on user"
            out["failed"] += 1
            continue

        notif = (
            db.query(NotificacionUsuario)
            .filter(NotificacionUsuario.id == row.notification_id)
            .first()
        )
        title = (notif.title if notif else "Notificación") or "Notificación"
        content = (notif.content if notif else "") or ""
        frontend_url = None
        try:
            from backend.core.config import get_settings
            frontend_url = get_settings().frontend_url
        except Exception:
            pass
        base = (frontend_url or "").rstrip("/")
        link = (notif.target_url or "") if notif else ""
        if link and base and not link.startswith("http"):
            link = f"{base}{link}"

        html = (
            f"<h2>{title}</h2><p style='line-height:1.6'>{content}</p>"
            + (f"<p><a href='{link}'>Abrir en CCF →</a></p>" if link else "")
        )
        ok = email_svc.send_email(to=recipient, subject=f"[CCF] {title}", html=html)

        row.attempts += 1
        row.recipient = recipient
        if ok:
            row.status = "sent"
            row.delivered_at = _dt.datetime.now(_dt.timezone.utc)
            out["sent"] += 1
        else:
            row.error = f"attempt {row.attempts} failed"
            if row.attempts >= max_attempts:
                row.status = "failed"
                out["failed"] += 1
            else:
                out["skipped_backoff"] += 1
    db.commit()
    return out
