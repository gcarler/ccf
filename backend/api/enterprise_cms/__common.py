"""Shared helpers + permission deps para el paquete enterprise_cms.

Single source of truth para los 12 sub-routers del paquete
``backend/api/enterprise_cms/``. Centraliza:

- ``require_cms_read`` / ``require_cms_manage``: dependencias RBAC.
- ``_log_audit`` / ``_notify`` / ``_fire_webhooks``: helpers de efecto
  lateral compartido por los routers de audit, content permissions,
  webhooks, custom types/entries, glossary, search, media folders y
  redirects.

Antes este código estaba inline en ``backend/api/enterprise_cms.py``
(deuda estructural 🟠#4, ``docs/ESTADO_DEUDA_TECNICA_BACKEND_CMS.md``):
split del monolito 1.670 LOC en 12 routers por dominio, 2026-08-05.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.core.permissions import require_permission
from backend.models_enterprise import (
    AuditLog,
    CmsNotification,
    Webhook,
    WebhookDelivery,
)
from backend.models_identity import User

# ── Permission dependencies ───────────────────────────────────────────────────

require_cms_read = require_permission("cms:read")
require_cms_manage = require_permission("cms:manage")


# ── Side-effect helpers (audit log, notifications, webhook deliveries) ───────


def _log_audit(
    db: Session,
    user: User,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    entity_slug: str | None = None,
    site_key: str | None = None,
    changes: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
):
    """Registra una entrada en ``AuditLog`` para el actor autenticado.

    Persists via ``db.flush()`` (no commit) — el caller controla el commit
    de la transacción que abarca mutación + auditoría.
    """
    log = AuditLog(
        actor_persona_id=getattr(user, "persona_id", None),
        actor_email=getattr(user, "email", None),
        actor_role=getattr(user, "role", None),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_slug=entity_slug,
        site_key=site_key,
        changes_json=changes,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    db.flush()
    return log


def _notify(
    db: Session,
    recipient_id,
    actor_id,
    notification_type: str,
    title: str,
    body: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    entity_slug: str | None = None,
    site_key: str | None = None,
    action_url: str | None = None,
):
    """Crea una ``CmsNotification`` in-app para el destinatario."""
    notif = CmsNotification(
        recipient_persona_id=recipient_id,
        actor_persona_id=actor_id,
        notification_type=notification_type,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_slug=entity_slug,
        site_key=site_key,
        action_url=action_url,
    )
    db.add(notif)
    db.flush()
    return notif


def _fire_webhooks(db: Session, site_key: str, event: str, payload: dict):
    """Encola ``WebhookDelivery`` para cada webhook activo suscrito al
    ``event`` (o ``"*"``).  Las entregas físicas las ejecuta el worker
    async; aquí sólo se persiste el intento y se actualiza
    ``last_triggered_at`` en el hook.
    """
    hooks = (
        db.query(Webhook)
        .filter(
            Webhook.site_key == site_key,
            Webhook.is_active == True,
        )
        .all()
    )
    for hook in hooks:
        if event in (hook.events or []) or "*" in (hook.events or []):
            delivery = WebhookDelivery(
                webhook_id=hook.id,
                event=event,
                payload_json=payload,
                success=False,
            )
            db.add(delivery)
            hook.last_triggered_at = datetime.now(timezone.utc)
    db.flush()
