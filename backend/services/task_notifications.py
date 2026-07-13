from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from backend import models
from backend.crud.crm import resolve_persona_id_for_user

# Import the email MODULE (not the function name) so test suites can
# `monkeypatch.setattr(backend.services.email, "send_email", _stub)`
# and have the patch reach this caller. If we did
# `from backend.services.email import send_email`, the import would bind
# the function into our module's globals and the monkeypatch on the
# source module would not affect us — that's the classic Python
# mock-pitfall. Keep the function name on this side via module
# attribute access (``email_svc.send_email``).
from backend.services import email as email_svc
from backend.services.email import render_task_assignment_email

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

    Atomicity contract (Sprint 1 — quality-triage pass):

    * Activity log + CommunicationLog are staged in a single ``try``
      block, and the in-app ``NotificacionUsuario`` is staged **after**
      the email's outcome is known.
    * When ``send_email`` returns ``False``, the
      ``NotificacionUsuario`` is **NOT** added; the
      ``CommunicationLog(outcome="email_failed")`` audit row is the sole
      artifact. This is the pivotal fix for the orphan notif pattern:
      before, the notification was added unconditionally then committed
      even when the email failed, leaving a phantom inbox entry with no
      auditable delivery state.
    * A single ``db.commit()`` at the end flushes the agreed batch.
    * Any exception (validation, SMTP failure, transient error) trips
      ``db.rollback()`` so we NEVER leave an orphan batch behind. The
      pre-fix code used a 2-stage commit that detached the notification
      from the audit, violating defense-in-depth.

    Returns ``True`` when the audit (+ optional notification + email)
    path completed; ``False`` when the transaction was rolled back or no
    email was sent and the audit row's outcome is ``no_email``.
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

        # Decide outcome FIRST; only stage NotificacionUsuario when the
        # email path succeeded (or when there is no email to send). The
        # CommunicationLog audit row is staged in every legal leaf state
        # to keep the trail truthful.
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
            # No inbox notification when there's no email channel — the
            # assignee wouldn't have a way to learn about the assignment.
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
        sent = email_svc.send_email(to=assignee.email, subject=subject, html=html, text=text)
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
        # Stage the inbox notification ONLY when the email succeeded.
        # This is the pivotal atomicity contract: send_email=False ⇒ NO
        # NotificacionUsuario (the audit row's outcome="email_failed" is
        # the source of truth). Pre-fix: an orphan notification was left
        # in the inbox even when the mail never went out.
        if sent and recipient_id:
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

        # Single atomic commit for activity log + audit row (+ optional
        # inbox notification when the email succeeded).
        db.commit()
        if not sent:
            # Outcome already recorded; surface observability without raising
            # (caller path was request-driven, not a critical path).
            logger.warning(
                "Task assignment email failed: task_id=%s assignee_id=%s",
                task.id, assignee.id,
            )
        return True
    except Exception:
        # Atomic rollback: drops the entire batch so we never persist a row
        # without its accompanying audit log. This is the pivotal Sprint 1
        # contract that fixes the orphan-NotificacionUsuario pattern.
        db.rollback()
        logger.exception(
            "notify_task_assigned failed; rolled back atomic transaction: "
            "task_id=%s assignee_id=%s",
            str(task.id), str(assignee.id),
        )
        return False
