from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from backend import models
from backend.crud.crm import resolve_persona_id_for_user
from backend.services.email import render_task_assignment_email, send_email

logger = logging.getLogger(__name__)


def _display_name(persona: models.Persona | None) -> str:
    if not persona:
        return "Usuario"
    return getattr(persona, "nombre_completo", None) or getattr(persona, "full_name", None) or "Usuario"


def _format_due_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    return str(value)


def notify_task_assigned(
    db: Session,
    *,
    task: models.ProjectTask,
    project: models.Project | None = None,
    assigned_by_user_id: Any | None = None,
    previous_assignee_id: Any | None = None,
) -> bool:
    """Crea la trazabilidad de una asignación de tarea y dispara correo.

    Returns True when a notification/email attempt was recorded.
    """
    assignee = (
        db.query(models.Persona)
        .filter(models.Persona.id == task.assignee_id)
        .first()
        if task.assignee_id
        else None
    )
    if not assignee:
        return False

    project = project or (
        db.query(models.Project).filter(models.Project.id == task.project_id).first()
    )
    assigned_by_persona_id = resolve_persona_id_for_user(db, assigned_by_user_id)
    assigned_by = (
        db.query(models.Persona).filter(models.Persona.id == assigned_by_persona_id).first()
        if assigned_by_persona_id
        else None
    )
    recipient_id = db.query(models.User.id).filter(models.User.id == assignee.id).scalar()
    task_url = f"/plataforma/tasks/{task.id}"
    project_title = getattr(project, "title", None)
    sender_name = _display_name(assigned_by)
    assignee_name = _display_name(assignee)
    due_text = _format_due_date(getattr(task, "due_date", None))
    description = getattr(task, "description", None) or ""
    action_type = "task_reassigned" if previous_assignee_id else "task_assigned"
    action_label = "reasignada" if previous_assignee_id else "asignada"

    db.add(
        models.ProjectActivityLog(
            project_id=task.project_id,
            persona_id=assigned_by_persona_id,
            action_type=action_type,
            description=f"Tarea '{task.title}' {action_label} a {assignee_name}",
        )
    )

    notification_title = f"Nueva tarea asignada: {task.title}"
    notification_content = " ".join(
        part
        for part in [
            f"Proyecto: {project_title}" if project_title else None,
            f"Responsable: {assignee_name}" if assignee_name else None,
            f"Prioridad: {task.priority}" if getattr(task, "priority", None) else None,
            f"Fecha límite: {due_text}" if due_text else None,
            f"Abre la tarea: {task_url}",
        ]
        if part
    )

    if recipient_id:
        existing = (
            db.query(models.NotificacionUsuario)
            .filter(
                models.NotificacionUsuario.user_id == recipient_id,
                models.NotificacionUsuario.title == notification_title,
                models.NotificacionUsuario.content == notification_content,
                models.NotificacionUsuario.is_read.is_(False),
            )
            .first()
        )
        if not existing:
            db.add(
                models.NotificacionUsuario(
                    user_id=recipient_id,
                    title=notification_title,
                    content=notification_content,
                    is_read=False,
                )
            )

    db.commit()

    if not getattr(assignee, "email", None):
        db.add(
            models.CommunicationLog(
                persona_id=assignee.id,
                channel="Email",
                campaign_name="Asignación de tarea",
                content=notification_content,
                leader_id=assigned_by_persona_id,
                outcome="no_email",
            )
        )
        db.commit()
        logger.info("Task assignment notification logged without email: %s", task.id)
        return True

    subject, html, text = render_task_assignment_email(
        task_title=task.title,
        task_url=task_url,
        project_title=project_title,
        assignee_name=assignee_name,
        assigned_by_name=sender_name,
        priority=getattr(task, "priority", None),
        due_date=due_text,
        description=description,
    )
    sent = send_email(to=assignee.email, subject=subject, html=html, text=text)
    outcome = "email_sent" if sent else "email_failed"
    db.add(
        models.CommunicationLog(
            persona_id=assignee.id,
            channel="Email",
            campaign_name="Asignación de tarea",
            content=text,
            leader_id=assigned_by_persona_id,
            outcome=outcome,
        )
    )
    db.commit()
    return True
