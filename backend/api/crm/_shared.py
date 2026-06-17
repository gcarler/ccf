from datetime import datetime, timezone

from backend import models


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_member_position(member_position: models.MemberPosition) -> dict:
    position = member_position.position
    return {
        "id": member_position.id,
        "persona_id": member_position.persona_id,
        "position_id": member_position.position_id,
        "position_name": position.name if position else None,
        "category": position.category if position else None,
        "start_date": (
            member_position.start_date.isoformat()
            if member_position.start_date
            else None
        ),
        "end_date": (
            member_position.end_date.isoformat() if member_position.end_date else None
        ),
        "is_active": member_position.is_active,
        "notes": member_position.notes,
        "created_at": (
            member_position.created_at.isoformat()
            if member_position.created_at
            else None
        ),
    }


def _enum_value(value):
    return getattr(value, "value", value)


def _case_legacy_stage(case: models.CasoCRM) -> str:
    stage = getattr(case, "stage", None)
    if stage:
        return str(stage)
    payload = getattr(case, "payload_web", None) if isinstance(getattr(case, "payload_web", None), dict) else {}
    if payload.get("legacy_stage"):
        return str(payload["legacy_stage"])

    etapa = getattr(case, "etapa_actual", None)
    etapa_name = str(getattr(etapa, "nombre", "") or "").strip().lower()
    if "llamar" in etapa_name or "contact" in etapa_name:
        return "call"
    if "visit" in etapa_name or "visita" in etapa_name:
        return "visit"
    if "discip" in etapa_name or "proceso" in etapa_name:
        return "discipleship"
    if "consolid" in etapa_name or "integr" in etapa_name:
        return "consolidated"

    estado = str(_enum_value(getattr(case, "estado", "")) or "").upper()
    if estado in {"RESUELTO_EXITO"}:
        return "consolidated"
    if estado in {"CERRADO_PERDIDO"}:
        return "lost"
    if estado in {"EN_PROGRESO"}:
        return "discipleship"
    if estado in {"ESPERANDO_RESPUESTA"}:
        return "call"
    return "new"


def _case_legacy_status(case: models.CasoCRM) -> str:
    status = getattr(case, "status", None)
    if status:
        return str(status)
    estado = str(_enum_value(getattr(case, "estado", "")) or "").upper()
    return "closed" if estado in {"RESUELTO_EXITO", "CERRADO_PERDIDO"} else "active"


def _serialize_case(case: models.CasoCRM) -> dict:
    persona = getattr(case, "persona", None)
    assigned = getattr(case, "assigned_pastor", None) or getattr(case, "asignado_a", None)
    assigned_leader = getattr(case, "assigned_leader", None)
    payload = getattr(case, "payload_web", None) if isinstance(getattr(case, "payload_web", None), dict) else {}
    created_at = getattr(case, "created_at", None) or getattr(case, "fecha_creacion", None)
    updated_at = getattr(case, "updated_at", None) or getattr(case, "fecha_creacion", None)
    last_contact_at = getattr(case, "last_contact_at", None)
    next_contact_at = getattr(case, "next_contact_at", None) or getattr(case, "sla_vencimiento_contacto", None)
    source = getattr(case, "source", None) or payload.get("legacy_source") or _enum_value(getattr(case, "origen_canal", None))
    return {
        "id": str(case.id),
        "persona_id": str(case.persona_id) if case.persona_id else None,
        "nombre_completo": persona.nombre_completo if persona else "",
        "telefono": (
            getattr(persona, "telefono", None)
            or getattr(persona, "phone", None)
            or getattr(persona, "mobile_phone", None)
            if persona
            else None
        ),
        "stage": _case_legacy_stage(case),
        "status": _case_legacy_status(case),
        "source": source,
        "last_contact_at": (
            last_contact_at.isoformat() if last_contact_at else None
        ),
        "next_contact_at": (
            next_contact_at.isoformat() if next_contact_at else None
        ),
        "assigned_pastor": (
            {
                "id": assigned.id,
                "nombre_completo": assigned.nombre_completo,
            }
            if assigned
            else None
        ),
        "assigned_leader": (
            {
                "id": assigned_leader.id,
                "nombre_completo": assigned_leader.nombre_completo,
            }
            if assigned_leader
            else None
        ),
        "assignments_count": len(getattr(case, "assignments", []) or []),
        "interactions_count": len(
            getattr(case, "interactions", None)
            or getattr(case, "interacciones", [])
            or []
        ),
        "open_tasks_count": sum(
            1
            for task in (getattr(case, "tasks", None) or getattr(case, "tareas", []) or [])
            if getattr(task, "status", None) != "completed"
        ),
        "notes": getattr(case, "notes", None) or payload.get("legacy_notes") or payload,
        "created_at": created_at.isoformat() if created_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }


def _persona_full_name(persona: models.Persona | None) -> str:
    if not persona:
        return "Persona"
    return persona.nombre_completo


def _serialize_task(task: models.CrmTask) -> dict:
    assignee = getattr(task, "assignee", None)
    persona = getattr(task, "persona", None)
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "category": task.category,
        "persona_id": task.persona_id,
        "persona_name": _persona_full_name(persona) if persona else None,
        "contact_name": _persona_full_name(persona) if persona else None,
        "assigned_to": assignee.nombre_completo if assignee else None,
        "assignee_id": str(task.assignee_id) if task.assignee_id else None,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


def _serialize_message_group(logs: list[models.CommunicationLog]) -> dict:
    logs = sorted(logs, key=lambda item: item.created_at or datetime.min, reverse=True)
    first = logs[0]
    delivered_count = sum(
        1 for item in logs if (item.outcome or "").lower() in {"sent", "delivered"}
    )
    failed_count = sum(1 for item in logs if (item.outcome or "").lower() == "failed")
    target_count = len(logs)
    persona_name = (
        _persona_full_name(first.persona) if getattr(first, "persona", None) else None
    )
    campaign_name = first.campaign_name
    return {
        "id": first.id,
        "name": (
            campaign_name or f"Mensaje a {persona_name}" if persona_name else "Mensaje"
        ),
        "channel": (first.channel or "").lower(),
        "status": (first.outcome or "sent").lower(),
        "target_count": target_count,
        "delivered_count": delivered_count,
        "failed_count": failed_count,
        "sent_at": first.created_at.isoformat() if first.created_at else None,
        "campaign_name": campaign_name,
        "member_name": persona_name,
        "content": first.content or "",
        "recipient_phone": first.recipient_phone,
        "external_id": first.external_id,
        "log_ids": [item.id for item in logs],
    }
