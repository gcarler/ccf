"""Canonical helper utilities for the Evangelism / CRM module.

These functions originated in both ``evangelism.py`` and ``evangelism_shared.py``.
This module is the single source of truth going forward; the other two files
should import from here.
"""

from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy.orm import Session

from backend import models


def _channel_label(channel: str) -> str:
    """Normalize communication channel to a display name."""
    value = str(channel or "").strip().lower()
    if value == "whatsapp":
        return "WhatsApp"
    if value == "email":
        return "Email"
    return "SMS"


def _persona_matches_segment(
    persona: models.Persona,
    segment: str,
    donation_persona_ids: set[str],
) -> bool:
    """Return True if *persona* matches the named segment."""
    value = str(segment or "").strip().lower()
    if value == "active":
        return str(persona.church_role_effective or "").strip().lower() in {
            "miembro",
            "servidor",
            "lider",
            "líder",
            "pastor",
            "coordinador",
        }
    if value == "new":
        return str(persona.estado_vital or "").strip().lower() == "nuevo"
    if value == "staff":
        return str(persona.church_role_effective or "").strip().lower() in {
            "pastor",
            "coordinador",
            "staff",
            "administrador",
            "admin",
        }
    if value == "groups":
        return persona.family_id is not None
    if value == "low":
        return str(persona.estado_vital or "").strip().lower() in {
            "nuevo",
            "creyente",
        }
    if value == "vip":
        return persona.id in donation_persona_ids
    return False


def _resolve_campaign_personas(
    db: Session,
    segments: list[str],
    sede_id=None,
) -> list[models.Persona]:
    """Resolve personas matching any of the given *segments*.

    Results are deduplicated by ``persona.id``.
    """
    normalized_segments = [
        segment for segment in (s.strip().lower() for s in segments) if segment
    ]
    if not normalized_segments:
        return []

    donations_q = db.query(models.Donation.persona_id).filter(
        models.Donation.persona_id.isnot(None)
    )
    if sede_id:
        donations_q = donations_q.filter(models.Donation.sede_id == sede_id)
    donation_persona_ids = {
        str(pid) for (pid,) in donations_q.distinct().all()
    }
    personas_q = db.query(models.Persona)
    if sede_id:
        personas_q = personas_q.filter(models.Persona.sede_id == sede_id)
    personas = personas_q.all()
    selected: list[models.Persona] = []
    seen_ids: set[str] = set()
    for persona in personas:
        if persona.id in seen_ids:
            continue
        if any(
            _persona_matches_segment(persona, segment, donation_persona_ids)
            for segment in normalized_segments
        ):
            selected.append(persona)
            seen_ids.add(persona.id)
    return selected


def _serialize_message_group(logs: list[models.CommunicationLog]) -> dict:
    """Summarise a group of related CommunicationLog entries into a single dict."""
    ordered = sorted(
        logs, key=lambda log: log.created_at or datetime.datetime.min, reverse=True
    )
    representative = ordered[0]
    persona = getattr(representative, "persona", None)
    persona_name = persona.nombre_completo if persona else "Desconocido"
    campaign_name = next(
        (log.campaign_name for log in ordered if log.campaign_name), None
    )
    sent_at_dt = ordered[0].created_at
    delivered_count = sum(
        1 for log in ordered if str(log.outcome).lower() in {"sent", "delivered"}
    )
    failed_count = sum(1 for log in ordered if str(log.outcome).lower() == "failed")
    if failed_count and not delivered_count:
        status = "failed"
    elif failed_count:
        status = "partial"
    else:
        status = str(representative.outcome or "sent").lower()
    display_name = campaign_name or (
        f"Mensaje a {persona_name}"
        if len(ordered) == 1
        else f"Campaña a {len(ordered)} contactos"
    )
    return {
        "id": representative.id,
        "name": display_name,
        "campaign_name": campaign_name,
        # Both keys are part of the published response.
        "persona_name": persona_name,
        "persona_name": persona_name,
        "channel": str(representative.channel).lower(),
        "status": status,
        "sent_at": sent_at_dt.isoformat() if sent_at_dt else None,
        "target_count": len(ordered),
        "delivered_count": delivered_count,
        "failed_count": failed_count,
        "content": representative.content,
        "recipient_phone": representative.recipient_phone,
        "external_id": representative.external_id,
    }


def _serialize_crm_task(
    task: models.CrmTask,
    contact_name: Optional[str] = None,
    assignee_name: Optional[str] = None,
) -> dict:
    """Serialize a CrmTask instance to a plain dict."""
    persona = getattr(task, "persona", None)
    persona_name = contact_name or (persona.nombre_completo if persona else None)
    assignee = getattr(task, "assignee", None)
    assigned_to = assignee_name or (assignee.nombre_completo if assignee else None)
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "category": task.category,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "persona_id": task.persona_id,
        # Both keys are part of the published response.
        "persona_name": persona_name,
        "persona_name": persona_name,
        "contact_name": persona_name,
        "assigned_to": assigned_to,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }
