"""Servicio de campañas de mensajería para eventos (plan_de_preregistro, Fase 5).

Reusos intencionales:
    - ``PlantillaMensaje.contenido_texto`` + ``variables_requeridas`` del CRM.
    - Hidratación estilo ``automation_engine.py:320-333`` (mismo reemplazo
      ``{{var}}`` / ``{{VAR}}``).
    - ``services/messaging.get_messaging_gateway`` para WhatsApp/Email/SMS.

Variables dinámicas nuevas (extienden las de personas ya existentes):
    - ``{{evento_nombre}}``,  ``{{evento_fecha}}``,  ``{{evento_ubicacion}}``,
      ``{{evento_hora}}``
    - ``{{qr_url}}`` (link al QR del inscrito)
    - ``{{inscripcion_estado}}``, ``{{inscripcion_id}}``
"""

from __future__ import annotations

import datetime as _dt
import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend import models

log = logging.getLogger(__name__)


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


# ── Hidratación de variables ─────────────────────────────────────────────────


def hydrate_template(
    plantilla_text: str,
    *,
    persona: Optional[models.Persona],
    event: Optional[models.CrmEvent],
    registration: Optional[models.EventRegistration] = None,
    public_base_url: str = "",
) -> str:
    """Reemplaza variables ``{{var}}`` y ``{{VAR}}`` en el texto de la plantilla.

    Reusa el patrón de ``backend/services/automation_engine.py:320-333`` y lo
    extiende con variables de evento/inscripción.
    """
    text = plantilla_text or ""
    if persona:
        replacements = {
            "name": persona.first_name or "",
            "nombre": persona.first_name or "",
            "first_name": persona.first_name or "",
            "last_name": persona.last_name or "",
            "apellido": persona.last_name or "",
            "email": persona.email or "",
            "phone": persona.phone or "",
        }
        for var, val in replacements.items():
            text = text.replace(f"{{{{{var}}}}}", val)
            text = text.replace(f"{{{{{var.upper()}}}}}", val)

    if event:
        event_date_str = event.event_date.strftime("%d/%m/%Y") if event.event_date else ""
        event_time_str = event.start_time or ""
        ubicacion = event.location or ""
        evento_vars = {
            "evento_nombre": event.name or "",
            "evento_fecha": event_date_str,
            "evento_hora": event_time_str,
            "evento_ubicacion": ubicacion,
        }
        for var, val in evento_vars.items():
            text = text.replace(f"{{{{{var}}}}}", val)
            text = text.replace(f"{{{{{var.upper()}}}}}", val)

    if registration:
        qr_url = ""
        if registration.qr_token and public_base_url:
            qr_url = f"{public_base_url}/public/events/{registration.event_id}/qr?token={registration.qr_token}".strip()
        reg_vars = {
            "qr_url": qr_url,
            "inscripcion_estado": registration.registration_status or "",
            "inscripcion_id": str(registration.id),
        }
        for var, val in reg_vars.items():
            text = text.replace(f"{{{{{var}}}}}", val)
            text = text.replace(f"{{{{{var.upper()}}}}}", val)

    return text


# ── Envío de campaña ──────────────────────────────────────────────────────────


def send_campaign(
    db: Session,
    campaign: models.EventCampaign,
    *,
    public_base_url: str = "",
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> dict:
    """Envía la campaña a todas las inscripciones que matcheen ``target_status``.

    Args:
        campaign: instancia ``EventCampaign`` activa.
        public_base_url: URL base para ``{{qr_url}}``.
        dry_run: si True, NO envía, solo retorna el conteo y un mensaje de
            preview con la primera hidratación.
        limit: cap del número de envíos (None = sin cap).

    Returns:
        ``{"sent": N, "skipped": M, "errors": [...], "preview": "..."}``
    """
    if not campaign.plantilla:
        return {"sent": 0, "skipped": 0, "errors": ["Plantilla no encontrada"], "preview": ""}

    event = campaign.event
    target_statuses = campaign.target_status or ["CONFIRMED"]
    if not isinstance(target_statuses, list):
        target_statuses = [target_statuses]

    regs_q = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.event_id == campaign.event_id,
            models.EventRegistration.deleted_at.is_(None),
            models.EventRegistration.registration_status.in_(target_statuses),
        )
        .all()
    )

    if dry_run and regs_q:
        return {
            "sent": 0,
            "skipped": 0,
            "errors": [],
            "preview": hydrate_template(
                campaign.plantilla.contenido_texto,
                persona=regs_q[0].persona,
                event=event,
                registration=regs_q[0],
                public_base_url=public_base_url,
            ),
            "would_send_to": len(regs_q),
        }

    sent = 0
    errors = []
    now = _utcnow()

    from backend.services.messaging import get_messaging_gateway

    gateway = get_messaging_gateway()

    for reg in regs_q:
        if limit is not None and sent >= limit:
            break
        persona = reg.persona
        if not persona:
            continue
        try:
            text = hydrate_template(
                campaign.plantilla.contenido_texto,
                persona=persona,
                event=event,
                registration=reg,
                public_base_url=public_base_url,
            )
            campaign_name = campaign.plantilla.titulo if campaign.plantilla else campaign.name

            if campaign.canal == "WHATSAPP":
                coro = gateway.send_whatsapp(db, str(persona.id), text, leader_id=None, campaign_name=campaign_name)
            elif campaign.canal == "SMS":
                coro = gateway.send_sms(db, str(persona.id), text, leader_id=None, campaign_name=campaign_name)
            else:  # EMAIL (default)
                coro = gateway.send_email(db, str(persona.id), text, leader_id=None, campaign_name=campaign_name)

            # gateway methods are async; run synchronously in own loop to keep API simple.
            import asyncio

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                # Already inside an event loop — spawn a thread to schedule it.
                import threading

                def _runner():
                    new_loop = asyncio.new_event_loop()
                    try:
                        new_loop.run_until_complete(coro)
                    except Exception as exc:
                        log.warning("async send_campaign failed for reg %s: %s", reg.id, exc)
                    finally:
                        new_loop.close()

                t = threading.Thread(target=_runner, daemon=True)
                t.start()
            else:
                asyncio.run(coro)

            reg.reminder_sent_count += 1
            reg.last_reminder_sent_at = now
            sent += 1
        except Exception as exc:
            errors.append({"reg_id": str(reg.id), "error": str(exc)})
            log.warning("Failed to send campaign %s to reg %s: %s", campaign.id, reg.id, exc)

    # Fix #5: solo marcar la campaña como despachada (last_sent_at) si se
    # envi\u00f3 al menos un mensaje, O si no hab\u00eda audiencia (regs_q vac\u00edo)
    # para que el scheduler no reintente eternamente cuando no hay nadie a
    # quien enviar. Si sent==0 Y regs_q no estaba vac\u00edo (todos fallaron),
    # dejar last_sent_at None para que el scheduler reintente en la siguiente
    # pasada.
    campaign.sent_count += sent
    if sent > 0 or not regs_q:
        campaign.last_sent_at = now
    db.commit()

    return {"sent": sent, "skipped": len(regs_q) - sent, "errors": errors, "preview": ""}


# ── Scheduler job (llamado desde backend/scheduler.py) ───────────────────────


def run_scheduled_campaigns(db: Session, *, public_base_url: str = "") -> dict:
    """Recorre las ``EventCampaign`` activas con trigger RELATIVE_TO_EVENT y
    ejecuta las que cumplan la ventana temporal (y no hayan sido enviadas).

    Retorna ``{"triggered": [campaign_ids], "errors": [...]}``.
    """
    now = _utcnow()
    triggered = []
    errors = []

    campaigns = (
        db.query(models.EventCampaign)
        .filter(
            models.EventCampaign.is_active.is_(True),
            models.EventCampaign.deleted_at.is_(None),
            models.EventCampaign.trigger_type == "RELATIVE_TO_EVENT",
        )
        .all()
    )

    for campaign in campaigns:
        if campaign.trigger_offset_minutes is None:
            continue
        event = campaign.event
        if not event or not event.event_date:
            continue
        event_date = event.event_date
        if event_date.tzinfo is None:
            event_date = event_date.replace(tzinfo=_dt.timezone.utc)
        target_moment = event_date + _dt.timedelta(minutes=campaign.trigger_offset_minutes)
        # ya debería haberse enviado?
        if campaign.last_sent_at and campaign.last_sent_at >= target_moment:
            continue
        if target_moment > now:
            continue
        try:
            result = send_campaign(db, campaign, public_base_url=public_base_url)
            triggered.append(str(campaign.id))
            if result.get("errors"):
                errors.extend(result["errors"])
        except Exception as exc:
            errors.append({"campaign_id": str(campaign.id), "error": str(exc)})
            log.warning("Failed campaign %s: %s", campaign.id, exc)

    return {"triggered": triggered, "errors": errors}
