from datetime import datetime, timezone

from backend import models


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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


def _serialize_case(case: models.CasoCRM) -> dict:
    return {
        "id": case.id,
        "persona_id": case.persona_id,
        "stage": case.stage,
        "status": case.status,
        "source": case.source,
        "last_contact_at": (
            case.last_contact_at.isoformat() if case.last_contact_at else None
        ),
        "next_contact_at": (
            case.next_contact_at.isoformat() if case.next_contact_at else None
        ),
        "assigned_pastor": (
            {
                "id": case.assigned_pastor.id,
                "nombre_completo": case.assigned_pastor.nombre_completo,
            }
            if case.assigned_pastor
            else None
        ),
        "assigned_leader": (
            {
                "id": case.assigned_leader.id,
                "nombre_completo": case.assigned_leader.nombre_completo,
            }
            if case.assigned_leader
            else None
        ),
        "assignments_count": len(case.assignments or []),
        "interactions_count": len(case.interactions or []),
        "open_tasks_count": sum(
            1 for task in (case.tasks or []) if task.status != "completed"
        ),
        "notes": case.notes,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "updated_at": case.updated_at.isoformat() if case.updated_at else None,
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
        "assigned_to": assignee.username if assignee else None,
        "assignee_id": task.assignee_id,
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
        "log_ids": [item.id for item in logs],
    }
