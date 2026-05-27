from __future__ import annotations

import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import models

ABSENTEES_PREVIEW_LIMIT = 50
ABSENCE_REASON_LABELS = {
    "weather": "Clima",
    "work": "Trabajo",
    "health": "Salud",
    "family": "Familia",
    "other": "Otro",
}


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


def parse_session_date(value: object) -> datetime.date:
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise ValueError("session_date is required")
        try:
            return datetime.date.fromisoformat(raw[:10])
        except ValueError as exc:
            raise ValueError("Invalid session_date") from exc
    raise ValueError("Invalid session_date")


def normalize_role_scope_payload(payload: dict) -> dict:
    normalized = dict(payload)
    raw_role_ids = normalized.get("target_role_ids")
    raw_persona_ids = normalized.get("target_persona_ids")
    normalized_role_ids: list[int] = []
    normalized_persona_ids: list[str] = []
    if isinstance(raw_role_ids, list):
        for raw_role_id in raw_role_ids:
            try:
                normalized_role_ids.append(int(raw_role_id))
            except (TypeError, ValueError):
                continue
    normalized_role_ids = list(dict.fromkeys(normalized_role_ids))
    if isinstance(raw_persona_ids, list):
        for raw_persona_id in raw_persona_ids:
            if isinstance(raw_persona_id, str) and raw_persona_id.strip():
                normalized_persona_ids.append(raw_persona_id.strip())
    normalized_persona_ids = list(dict.fromkeys(normalized_persona_ids))

    if normalized.get("target_audience") == "ROLE":
        if normalized_role_ids:
            normalized["target_role_ids"] = normalized_role_ids
            normalized["target_role_id"] = normalized_role_ids[0]
        elif normalized.get("target_role_id") is not None:
            try:
                normalized_role_id = int(normalized["target_role_id"])
            except (TypeError, ValueError):
                normalized_role_id = None
            normalized["target_role_id"] = normalized_role_id
            normalized["target_role_ids"] = (
                [normalized_role_id] if normalized_role_id is not None else None
            )
        else:
            normalized["target_role_ids"] = None
            normalized["target_role_id"] = None
        normalized["target_persona_ids"] = None
    elif normalized.get("target_audience") == "MANUAL":
        normalized["target_role_ids"] = None
        normalized["target_role_id"] = None
        normalized["target_persona_ids"] = normalized_persona_ids or None
    else:
        normalized["target_role_ids"] = None
        normalized["target_role_id"] = None
        normalized["target_persona_ids"] = None

    return normalized


def resolve_target_role_ids(event: models.CrmEvent) -> list[int]:
    role_ids = []
    if isinstance(event.target_role_ids, list):
        for raw_role_id in event.target_role_ids:
            try:
                role_ids.append(int(raw_role_id))
            except (TypeError, ValueError):
                continue
    if not role_ids and event.target_role_id is not None:
        role_ids.append(int(event.target_role_id))
    return list(dict.fromkeys(role_ids))


def get_expected_members_for_event(
    db: Session, event: models.CrmEvent
) -> list[models.Persona]:
    if event.target_audience == "ROLE":
        role_ids = resolve_target_role_ids(event)
        if not role_ids:
            return []
        role_names = [
            row[0]
            for row in db.query(models.RoleDefinition.name)
            .filter(models.RoleDefinition.id.in_(role_ids))
            .all()
        ]
        if not role_names:
            return []
        return (
            db.query(models.Persona)
            .filter(models.Persona.church_role.in_(role_names))
            .order_by(models.Persona.nombre_completo.asc())
            .all()
        )
    if event.target_audience == "MANUAL":
        persona_ids = []
        if isinstance(event.target_persona_ids, list):
            for raw_persona_id in event.target_persona_ids:
                if isinstance(raw_persona_id, str) and raw_persona_id.strip():
                    persona_ids.append(raw_persona_id.strip())
        persona_ids = list(dict.fromkeys(persona_ids))
        if not persona_ids:
            return []
        return (
            db.query(models.Persona)
            .filter(models.Persona.id.in_(persona_ids))
            .order_by(models.Persona.nombre_completo.asc())
            .all()
        )
    return db.query(models.Persona).all()


def expected_group_rows(db: Session, grupo_id: int):
    rows = (
        db.query(models.ParticipanteGrupo, models.Persona)
        .join(models.Persona, models.Persona.id == models.ParticipanteGrupo.persona_id)
        .filter(models.ParticipanteGrupo.grupo_id == grupo_id)
        .order_by(models.Persona.nombre_completo.asc())
        .all()
    )
    grupo = (
        db.query(models.GrupoEvangelismo)
        .filter(models.GrupoEvangelismo.id == grupo_id)
        .first()
    )
    seen_ids = {persona.id for _, persona in rows}
    extra_personas = []
    if grupo:
        for pid in [grupo.lider_persona_id, grupo.asistente_persona_id, grupo.anfitrion_persona_id]:
            if pid and pid not in seen_ids:
                p = (
                    db.query(models.Persona)
                    .filter(models.Persona.id == pid)
                    .first()
                )
                if p:
                    extra_personas.append((None, p))
                    seen_ids.add(p.id)
    return rows + extra_personas


def _channel_label(channel: str) -> str:
    """Normalize communication channel display name."""
    value = str(channel or "").strip().lower()
    if value == "whatsapp":
        return "WhatsApp"
    if value == "email":
        return "Email"
    return "SMS"


def _member_matches_segment(
    persona: models.Persona, segment: str, donation_persona_ids: set[str]
) -> bool:
    value = str(segment or "").strip().lower()
    if value == "active":
        return str(persona.church_role or "").strip().lower() in {
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
        return str(persona.church_role or "").strip().lower() in {
            "pastor",
            "coordinador",
            "staff",
            "administrador",
            "admin",
        }
    if value == "groups":
        return persona.family_id is not None
    if value == "low":
        return str(persona.church_role or "").strip().lower() in {
            "nuevo",
            "creyente",
        }
    if value == "vip":
        return persona.id in donation_persona_ids
    return False


def _resolve_campaign_members(db: Session, segments: list[str]) -> list[models.Persona]:
    normalized_segments = [
        segment for segment in (s.strip().lower() for s in segments) if segment
    ]
    if not normalized_segments:
        return []

    donation_persona_ids = {
        str(pid)
        for (pid,) in db.query(models.Donation.persona_id)
        .filter(models.Donation.persona_id.isnot(None))
        .distinct()
        .all()
    }
    personas = db.query(models.Persona).all()
    selected = []
    seen_ids: set[str] = set()
    for persona in personas:
        if persona.id in seen_ids:
            continue
        if any(
            _member_matches_segment(persona, segment, donation_persona_ids)
            for segment in normalized_segments
        ):
            selected.append(persona)
            seen_ids.add(persona.id)
    return selected


def _serialize_message_group(logs: list[models.CommunicationLog]) -> dict:
    import datetime as _dt

    ordered = sorted(
        logs, key=lambda log: log.created_at or _dt.datetime.min, reverse=True
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
    persona = getattr(task, "persona", None)
    persona_name = contact_name or (
        persona.nombre_completo if persona else None
    )
    assignee = getattr(task, "assignee", None)
    assigned_to = assignee_name or (assignee.username if assignee else None)
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "category": task.category,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "persona_id": task.persona_id,
        "persona_name": persona_name,
        "contact_name": persona_name,
        "assigned_to": assigned_to,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


def member_payload(
    persona: models.Persona,
    attended: bool,
    scanned_at=None,
    absence_reason=None,
    absence_reason_detail=None,
    estado=None,
    es_primera_vez=False,
):
    return {
        "persona_id": persona.id,
        "name": persona.nombre_completo,
        "role": persona.church_role or "Miembro",
        "attended": attended,
        "absence_reason": absence_reason,
        "absence_reason_detail": absence_reason_detail,
        "scanned_at": scanned_at.isoformat() if scanned_at else None,
        "estado": estado,
        "es_primera_vez": es_primera_vez,
    }
