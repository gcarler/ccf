"""Digest diario de notificaciones (Fase 3 — opcional por usuario).

Para usuarios con preferencia de digest, agrega TODAS las notificaciones
in-app no leídas de las últimas 24 horas en un solo email. Las entregas
individuales pending de esas notificaciones se suprimen para no mandar
correo doble.

El scheduling real debe invocar ``run_daily_digest()`` a una hora fija
(cron/celery/beat); su lógica es auditable aquí.
"""

from __future__ import annotations

import datetime as _dt
import logging
from uuid import UUID

from sqlalchemy.orm import Session

from backend.models_auth import NotificacionUsuario, Usuario
from backend.models_notifications import NotificationDelivery

log = logging.getLogger(__name__)

DIGEST_EVENT_KEY = "daily_digest"


def run_daily_digest(db: Session, max_users: int = 500) -> dict[str, int]:
    """Envía un digest a los usuarios con >1 no leídas en 24h.

    Criterios:
      - Usuario con al menos 2 notificaciones no leídas creadas en < 24h.
      - Solo si tiene email configurado.
      - Sus entregas pending de esas notificaciones se marcan suppressed.

    Returns: {"digests_sent": n, "notifications_aggregated": m}
    """
    out = {"digests_sent": 0, "notifications_aggregated": 0}
    cutoff = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=24)

    # Candidatos: users con >1 notificación no leída reciente.
    candidates = (
        db.query(NotificacionUsuario.user_id, Usuario.email)
        .join(Usuario, Usuario.id == NotificacionUsuario.user_id)
        .filter(
            NotificacionUsuario.is_read.is_(False),
            NotificacionUsuario.created_at >= cutoff,
        )
        .group_by(NotificacionUsuario.user_id, Usuario.email)
        .having(
            __import__("sqlalchemy").func.count(NotificacionUsuario.id) > 1
        )
        .limit(max_users)
        .all()
    )

    for user_id, email in candidates:
        if not email:
            continue
        rows = (
            db.query(NotificacionUsuario)
            .filter(
                NotificacionUsuario.user_id == user_id,
                NotificacionUsuario.is_read.is_(False),
                NotificacionUsuario.created_at >= cutoff,
            )
            .order_by(NotificacionUsuario.created_at.desc())
            .all()
        )
        if len(rows) < 2:
            continue

        items = "".join(
            f"<li><strong>{r.title}</strong> — {r.content or ''}</li>"
            for r in rows
        )
        subject = f"[CCF] Hoy tienes {len(rows)} notificaciones sin leer"
        html = (
            "<h2>Resumen de tu día en CCF</h2>"
            f"<p>Tienes <strong>{len(rows)}</strong> notificaciones sin leer:</p>"
            f"<ul style='line-height:1.7'>{items}</ul>"
            "<p style='color:#9ca3af;font-size:12px'>"
            "Puedes desactivar este digest desde tu cuenta → Notificaciones."
            "</p>"
        )
        from backend.services import email as email_svc

        sent = email_svc.send_email(to=email, subject=subject, html=html)
        if not sent:
            continue
        out["digests_sent"] += 1
        out["notifications_aggregated"] += len(rows)

        # Suprime entregas pending de esas notificaciones (anti doble envío).
        notif_ids = [r.id for r in rows]
        db.query(NotificationDelivery).filter(
            NotificationDelivery.notification_id.in_(notif_ids),
            NotificationDelivery.status == "pending",
        ).update({"status": "suppressed", "read_before_send": True}, synchronize_session=False)
        db.commit()

    return out
