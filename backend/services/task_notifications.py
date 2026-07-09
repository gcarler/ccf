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
    """Create the audit + notification trail for a task assignment and dispatch the
    email — all in **one atomic transaction**.

    Atomicity contract (Sprint 1 — PR 1.2):

    * Activity log + NotificacionUsuario + CommunicationLog are staged in a single
      ``try`` block.
    * A single ``db.commit()`` at the end flushes the whole batch.
    * Any exception (validation, SMTP failure, transient error) trips
      ``db.rollback()`` so we NEVER leave an orphan ``NotificacionUsuario`` row
      behind. The pre-fix code used two commits: activity+notification were
      flushed first, then email was attempted. On email failure the second
      commit didn't happen but the first had already leaked the notification.

    Returns ``True`` when the audit + email path completed; ``False`` when the
    transaction was rolled back.
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
    # NOTE: with Axiom 2 (Auth v3) auth_users.id == personas.id, this matches
    # the assignee's own auth row when one exists; for non-login personas
    # (system actors) recipient_id may be None and the inbox notification
    # step is skipped.
    recipient_id = db.query(models.User.id).filter(models.User.id == assignee.id).scalar()
    task_url = f"/plataforma/tasks/{task.id}"
    project_title = getattr(project, "title", None)
    sender_name = _display_name(assigned_by)
    assignee_name = _display_name(assignee)
    due_text = _format_due_date(getattr(task, "due_date", None))
    description = getattr(task, "description", None) or ""
    action_type = "task_reassigned" if previous_assignee_id else "task_assigned"
    action_label = "reasignada" if previous_assignee_id else "asignada"

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

    # ── Atomic transaction: one commit for the whole side-effect batch ──
    try:
        db.add(
            models.ProjectActivityLog(
                project_id=task.project_id,
                persona_id=assigned_by_persona_id,
                action_type=action_type,
                description=f"Tarea '{task.title}' {action_label} a {assignee_name}",
            )
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

        # Decide outcome, attach the CommunicationLog audit row, then commit
        # exactly once. Branches here are the three legal leaf states of a
        # task assignment; the absence of any return until after the commit
        # is what makes the operation atomic.
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
            logger.info(
                "Task assignment logged without email: %s", task.id,
            )
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
        # Single atomic commit for activity log + notification + audit row
        db.commit()
        if not sent:
            # Outcome already recorded; surface observability without raising
            # (caller path was request-driven, not a critical path).
            logger.warning(
                "Task assignment email failed: task_id=%s assignee_id=%s",
                task.id, assignee.id,
            )
        return True
    except Exception as exc:
        # Atomic rollback: drops the entire batch so we never persist a row
        # without its accompanying audit log. This is the pivotal Sprint 1
        # PR 1.2 contract that fixes the orphan-NotificacionUsuario pattern.
        db.rollback()
        logger.exception(
            "notify_task_assigned failed; rolled back atomic transaction: "
            "task_id=%s assignee_id=%s",
            str(task.id), str(assignee.id),
        )
        return False
