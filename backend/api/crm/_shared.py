from datetime import datetime, timezone

from backend import models


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _serialize_member_position(member_position: models.MemberPosition) -> dict:
    position = member_position.position
    return {
        "id": member_position.id,
        "member_id": member_position.member_id,
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


def _serialize_case(case: models.ConsolidationCase) -> dict:
    return {
        "id": case.id,
        "member_id": case.member_id,
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
                "first_name": case.assigned_pastor.first_name,
                "last_name": case.assigned_pastor.last_name,
            }
            if case.assigned_pastor
            else None
        ),
        "assigned_leader": (
            {
                "id": case.assigned_leader.id,
                "first_name": case.assigned_leader.first_name,
                "last_name": case.assigned_leader.last_name,
            }
            if case.assigned_leader
            else None
        ),
        "assignments_count": len(case.assignments or []),
        "interactions_count": len(case.interactions or []),
        "open_tasks_count": sum(
            1 for task in (case.follow_up_tasks or []) if task.status != "completed"
        ),
        "notes": case.notes,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "updated_at": case.updated_at.isoformat() if case.updated_at else None,
    }


def _member_full_name(member: models.Member | None) -> str:
    if not member:
        return "Miembro"
    return f"{member.first_name} {member.last_name}".strip()


def _serialize_task(task: models.CrmTask) -> dict:
    assignee = getattr(task, "assignee", None)
    member = getattr(task, "member", None)
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "category": task.category,
        "member_id": task.member_id,
        "member_name": _member_full_name(member) if member else None,
        "contact_name": _member_full_name(member) if member else None,
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
    member_name = (
        _member_full_name(first.member) if getattr(first, "member", None) else None
    )
    campaign_name = first.campaign_name
    return {
        "id": first.id,
        "name": (
            campaign_name or f"Mensaje a {member_name}" if member_name else "Mensaje"
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
