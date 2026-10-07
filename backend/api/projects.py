from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import JSONResponse
from jose import jwt as _jwt
from sqlalchemy import Integer, and_, cast, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from backend import crud, models, schemas
from backend.core.audit import record_admin_action
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.permissions import (
    ALGORITHM,
    MODULE_PERMISSION_MAP,
    SECRET_KEY,
    _has_permission,
    get_current_active_user,
    get_user_effective_permissions,
    normalize_role,
    require_module_access,
    require_staff_or_admin,
)
from backend.core.storage import storage_service
from backend.core.uploads import MAX_UPLOAD_SIZE, sanitize_filename
from backend.crud.crm import get_user_sede_id
from backend.crud.projects import (
    create_milestone as _projects_create_milestone,
)
from backend.crud.projects import (
    delete_milestone as _projects_delete_milestone,
)
from backend.crud.projects import (
    get_user_persona_id,
)
from backend.mesh_websockets import manager
from backend.services.comment_notifications import notify_mention
from backend.services.mention_parser import resolve_mentions
from backend.services.task_notifications import notify_task_assigned

settings = get_settings()


router = APIRouter()
logger = logging.getLogger(__name__)


def _resolve_persona(db: Session, user_id: Any):
    persona_id = get_user_persona_id(db, user_id)
    if not persona_id:
        return None
    return db.query(models.Persona).filter(models.Persona.id == persona_id).first()


def _author_name(persona) -> str:
    if not persona:
        return "Usuario"
    return getattr(persona, "nombre_completo", None) or getattr(persona, "full_name", None) or "Usuario"


def _project_comment_to_schema(
    comment: models.ProjectComment, author: models.Persona | None = None
) -> schemas.ProjectCommentItem:
    return schemas.ProjectCommentItem(
        id=comment.id,
        project_id=str(comment.project_id) if comment.project_id is not None else None,
        task_id=str(comment.task_id) if comment.task_id is not None else None,
        content=comment.content,
        author_id=str(comment.author_id) if comment.author_id is not None else None,
        author_name=_author_name(author),
        is_resolved=comment.is_resolved,
        is_pinned=getattr(comment, "is_pinned", False),
        pinned_at=getattr(comment, "pinned_at", None),
        pinned_by=str(comment.pinned_by) if getattr(comment, "pinned_by", None) is not None else None,
        pinner_name=_author_name(getattr(comment, "pinner", None)) if getattr(comment, "pinner", None) else None,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        attachments=comment.attachments or [],
        mentions=[str(m) for m in (comment.mentions or [])],
    )


def _notify_comment_mentions(
    db: Session,
    comment: models.ProjectComment,
    project_id: str,
    task_id: Optional[str],
    user_sede: Optional[Any],
) -> None:
    if not comment.mentions:
        return
    task_title = ""
    if task_id:
        task = db.query(models.ProjectTask).filter(models.ProjectTask.id == _to_uuid(task_id)).first()
        task_title = f" ({task.title})" if task else ""
    notify_mention(
        db,
        mention_ids=comment.mentions or [],
        author_id=comment.author_id,
        title=f"Te mencionaron en un comentario{task_title}",
        content=f"{comment.content[:120]}{'...' if len(comment.content) > 120 else ''}",
        url=f"/plataforma/projects/{project_id}?task={task_id}" if task_id else f"/plataforma/projects/{project_id}",
        sede_id=user_sede,
    )


def _assignment_changed(previous_assignee_id, current_assignee_id) -> bool:
    if previous_assignee_id is None and current_assignee_id is None:
        return False
    return str(previous_assignee_id) != str(current_assignee_id)


@router.get("/tasks", response_model=List[schemas.ProjectTask])
def list_all_my_tasks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Obtiene todas las tareas asignadas; mantiene el contrato array legacy.

    Axioma 3 — strict scope: solo se devuelven tareas de proyectos en la
    ``sede_id`` del actor. Superadmin (sin sede) ve todo.
    """
    persona_id = get_user_persona_id(db, current_user.id)
    if not persona_id:
        return []
    user_sede = get_user_sede_id(db, current_user.id)
    q = (
        db.query(models.ProjectTask)
        .join(models.Project, models.Project.id == models.ProjectTask.project_id)
        .filter(
            models.ProjectTask.assignee_id == persona_id,
            models.ProjectTask.deleted_at.is_(None),
            models.Project.deleted_at.is_(None),
        )
    )
    if user_sede is not None:
        q = q.filter(models.Project.sede_id == user_sede)
    tasks = (
        q.options(
            selectinload(models.ProjectTask.project),
            selectinload(models.ProjectTask.supplies),
            selectinload(models.ProjectTask.attachments),
            selectinload(models.ProjectTask.subtasks),
        )
        .order_by(models.ProjectTask.created_at.desc(), models.ProjectTask.id.desc())
        .all()
    )
    for t in tasks:
        _prepare_task_for_response(t)
    return tasks


@router.get("/tasks/page", response_model=schemas.PaginatedResponse[schemas.ProjectTaskPageItem])
def list_my_tasks_page(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Bounded page for the Projects task workspace; legacy array route remains."""
    persona_id = get_user_persona_id(db, current_user.id)
    if not persona_id:
        return {"items": [], "total": 0, "skip": offset, "limit": limit}
    user_sede = get_user_sede_id(db, current_user.id)
    tasks, total = crud.get_assigned_project_tasks_page(
        db,
        persona_id=persona_id,
        sede_id=user_sede,
        offset=offset,
        limit=limit,
    )
    items = []
    for task in tasks:
        _prepare_task_for_response(task)
        item = schemas.ProjectTaskPageItem.model_validate(task)
        items.append(item.model_copy(update={"project_title": task.project.title if task.project else None}))
    return {"items": items, "total": total, "skip": offset, "limit": limit}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _log_project_activity(db: Session, project_id: Any, user_id: Any, action_type: str, description: str):
    persona_id = get_user_persona_id(db, user_id)
    activity = models.ProjectActivityLog(
        project_id=_to_uuid(project_id),
        persona_id=persona_id,
        action_type=action_type,
        description=description,
    )
    db.add(activity)
    return activity


def _to_uuid(val):
    """Convert string UUID to uuid.UUID for SQLAlchemy filters."""
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, AttributeError):
        return val


def _ensure_project(db: Session, project_id: str, user_sede=None) -> models.Project:
    """Fetch a project by id and enforce multi-tenant scope (Axioma 3).

    Existence-leak safe: returns 404 (never 403) when the project is in a
    different ``sede_id`` than the actor or when the project's ``sede_id``
    is NULL while the actor is restricted to a sede. This
    matches the CRM/CMS ``_ensure_*`` convention so cross-tenant probing
    yields indistinguishable error from "not found".

    Fix vs prior implementation: previously the guard used
    ``if user_sede and project.sede_id and ...``, which let projects without
    ``sede_id`` slip past scope checks
    when an actor from any sede queried them. The new guard explicitly
    rejects projects with NULL ``sede_id`` whenever the actor is bounded
    to a sede, eliminating the leak.

    Args:
        db: SQLAlchemy session.
        project_id: Project identifier (UUID or string).
        user_sede: Actor's sede. ``None`` ⇒ superadmin path, no scope
            filter is applied.
    """
    target_uuid = _to_uuid(project_id)
    if not isinstance(target_uuid, uuid.UUID):
        raise HTTPException(status_code=404, detail="Project not found")

    project = (
        db.query(models.Project)
        .options(
            selectinload(models.Project.tasks).selectinload(models.ProjectTask.attachments),
            selectinload(models.Project.tasks).selectinload(models.ProjectTask.supplies),
            selectinload(models.Project.tasks).selectinload(models.ProjectTask.subtasks),
            selectinload(models.Project.milestones),
            selectinload(models.Project.activity_logs),
            selectinload(models.Project.kpis),
            selectinload(models.Project.dependencies),
        )
        .filter(models.Project.id == target_uuid, models.Project.deleted_at.is_(None))
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    # Axioma 3 strict scope: even projects with NULL sede_id are hidden
    # from seated actors. Only the superadmin (user_sede = None) bypasses scope.
    if user_sede is not None:
        if project.sede_id is None or str(project.sede_id) != str(user_sede):
            raise HTTPException(status_code=404, detail="Project not found")
    return project


def _ensure_task(db: Session, task_id: str) -> models.ProjectTask:
    task = (
        db.query(models.ProjectTask)
        .options(
            selectinload(models.ProjectTask.supplies),
            selectinload(models.ProjectTask.attachments),
        )
        .filter(models.ProjectTask.id == _to_uuid(task_id), models.ProjectTask.deleted_at.is_(None))
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _ensure_task_in_project(db: Session, project_id: str, task_id: str) -> models.ProjectTask:
    task = _ensure_task(db, task_id)
    if str(task.project_id) != str(project_id):
        raise HTTPException(status_code=404, detail="Task not found in project")
    return task


def _ensure_supply_in_task(db: Session, project_id: str, task_id: str, supply_id: UUID) -> models.TaskSupply:
    _ensure_task_in_project(db, project_id, task_id)
    supply = (
        db.query(models.TaskSupply)
        .filter(models.TaskSupply.id == supply_id, models.TaskSupply.task_id == _to_uuid(task_id))
        .first()
    )
    if not supply:
        raise HTTPException(status_code=404, detail="Supply not found in task")
    return supply


def _ensure_milestone_in_project(db: Session, project_id: str, milestone_id: str) -> models.ProjectMilestone:
    milestone = (
        db.query(models.ProjectMilestone)
        .filter(
            models.ProjectMilestone.id == _to_uuid(milestone_id),
            models.ProjectMilestone.project_id == _to_uuid(project_id),
        )
        .first()
    )
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found in project")
    return milestone


def _ensure_phase_in_project(db: Session, project_id: str, phase_id: str) -> models.ProjectPhase:
    phase = (
        db.query(models.ProjectPhase)
        .filter(
            models.ProjectPhase.id == _to_uuid(phase_id),
            models.ProjectPhase.project_id == _to_uuid(project_id),
            models.ProjectPhase.deleted_at.is_(None),
        )
        .first()
    )
    if not phase:
        raise HTTPException(status_code=404, detail="Phase not found in project")
    return phase


def _ensure_attachment_in_task(
    db: Session, project_id: str, task_id: str, attachment_id: str
) -> models.ProjectAttachment:
    _ensure_task_in_project(db, project_id, task_id)
    attachment = (
        db.query(models.ProjectAttachment)
        .filter(
            models.ProjectAttachment.id == _to_uuid(attachment_id),
            models.ProjectAttachment.task_id == _to_uuid(task_id),
        )
        .first()
    )
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found in task")
    return attachment


def _inbox_item_exists_for_actor(
    db: Session,
    item_id: str,
    persona_id: Any,
    user_sede: Optional[Any],
) -> bool:
    """Determinar si ``item_id`` existe en el inbox del actor.

    PEND-QUALITY-INBOX-SCOPE-001 (cierre 2026-07-16): usado por
    :func:`mark_inbox_read` para rechazar ``item_id`` arbitrarios antes
    de tocar ``project_inbox_state``.

    Formatos aceptados (deben coincidir con la salida de
    :func:`list_inbox`):

    * ``comment-<uuid>``: comentario no resuelto (de otro autor) en un
      proyecto **no soft-deleted** de la ``sede_id`` del actor.
    * ``task-<uuid>``: tarea abierta (``status != "completed"``, **no
      soft-deleted**) asignada al actor, en un proyecto **no
      soft-deleted** de la ``sede_id`` del actor.

    Existencia-leak safe: cualquier formato inválido o UUID que no
    satisface las condiciones devuelve ``False``, por lo que
    ``mark_inbox_read`` responde **404** indistinguible de "no existe".
    """
    if not item_id or not isinstance(item_id, str) or "-" not in item_id:
        return False
    prefix, _, raw_uuid = item_id.partition("-")
    if prefix not in {"comment", "task"} or not raw_uuid:
        return False
    target_uuid = _to_uuid(raw_uuid)
    if target_uuid is raw_uuid:  # _to_uuid fallback cuando el parse falla
        return False

    if prefix == "comment":
        q = (
            db.query(models.ProjectComment.id)
            .join(models.Project, models.Project.id == models.ProjectComment.project_id)
            .filter(
                models.ProjectComment.id == target_uuid,
                models.ProjectComment.deleted_at.is_(None),
                ~models.ProjectComment.is_resolved,
                # Replicar el filtro de ``list_inbox``: auto-comentarios
                # del propio actor no aparecen en su feed, por lo que
                # tampoco deben ser marcables como leídos.
                models.ProjectComment.author_id != persona_id,
                # Solo comentarios de proyectos no soft-deleted; el filtro
                # de ``author_id != persona_id`` se aplica en ``list_inbox``
                # (auto-comentarios excluidos) y se respeta aquí implícito
                # vía la uni\u00f3n con ``list_inbox``.
                models.Project.deleted_at.is_(None),
            )
        )
        if user_sede is not None:
            q = q.filter(models.Project.sede_id == user_sede)
        return db.query(q.exists()).scalar() is True

    # prefix == "task"
    q = (
        db.query(models.ProjectTask.id)
        .join(models.Project, models.Project.id == models.ProjectTask.project_id)
        .filter(
            models.ProjectTask.id == target_uuid,
            models.ProjectTask.deleted_at.is_(None),
            models.ProjectTask.status != "completed",
            models.ProjectTask.assignee_id == persona_id,
            models.Project.deleted_at.is_(None),
        )
    )
    if user_sede is not None:
        q = q.filter(models.Project.sede_id == user_sede)
    return db.query(q.exists()).scalar() is True


def _get_persona_id_for_user(db: Session, user_id: Any) -> Optional[uuid.UUID]:
    """Resolve the persona_id for a given user_id.

    Assignment-based access in Projects is tied to ``personas.id`` (owner
    and assignee), not ``auth_users.id``. Returns ``None`` when the user
    has no associated persona.
    """
    persona_id = get_user_persona_id(db, user_id)
    if persona_id:
        return _to_uuid(persona_id)
    return None


def _is_project_owner(db: Session, project_id: Any, persona_id: Any) -> bool:
    """Return True if ``persona_id`` owns the given project."""
    project = (
        db.query(models.Project)
        .filter(
            models.Project.id == _to_uuid(project_id),
            models.Project.deleted_at.is_(None),
        )
        .first()
    )
    return project is not None and str(project.owner_id) == str(persona_id)


def _is_assigned_to_project(db: Session, project_id: Any, persona_id: Any) -> bool:
    """Check if ``persona_id`` has access to ``project_id`` via assignment.

    A persona is considered assigned to a project when:
    * They are the project owner, OR
    * They are the assignee of at least one non-deleted task in the project.
    """
    if _is_project_owner(db, project_id, persona_id):
        return True
    task = (
        db.query(models.ProjectTask)
        .filter(
            models.ProjectTask.project_id == _to_uuid(project_id),
            models.ProjectTask.assignee_id == _to_uuid(persona_id),
            models.ProjectTask.deleted_at.is_(None),
        )
        .first()
    )
    return task is not None


def _is_assigned_to_task(db: Session, task_id: Any, persona_id: Any) -> bool:
    """Check if ``persona_id`` has access to ``task_id`` via assignment.

    A persona is considered assigned to a task when:
    * They are the assignee of the task, OR
    * They are the owner of the parent project.
    """
    task = (
        db.query(models.ProjectTask)
        .filter(
            models.ProjectTask.id == _to_uuid(task_id),
            models.ProjectTask.deleted_at.is_(None),
        )
        .first()
    )
    if not task:
        return False
    if str(task.assignee_id) == str(persona_id):
        return True
    return _is_project_owner(db, task.project_id, persona_id)


def _has_role_based_project_access(db: Session, current_user: models.User, min_level: str) -> bool:
    """Check if the user has role-based permission for the Projects module.

    Reuses ``backend.core.permissions.get_user_effective_permissions`` and
    ``_has_permission`` so the assignment-based dependency stays consistent
    with the rest of the platform without circular imports.
    """
    perm_key = MODULE_PERMISSION_MAP["projects"].get(min_level)
    if not perm_key:
        return False
    perms = get_user_effective_permissions(db, current_user)
    if perms.get(perm_key) == "allow":
        return True
    role = normalize_role(str(getattr(current_user, "role", "")))
    if not role and hasattr(current_user, "rol_plataforma") and current_user.rol_plataforma:
        role = normalize_role(current_user.rol_plataforma.nombre)
    return _has_permission(role, set(perms.keys()), perm_key)


def require_project_access(min_level: str = "read"):
    """FastAPI dependency factory: role-based OR assignment-based access.

    Rules:
    * Admin/Gestor/Editor pass via role-based permissions (existing model).
    * For ``read`` and ``edit`` levels, any authenticated user with a
      persona assigned to the project/task also passes.
    * ``manage`` level remains strictly role-based.
    * Endpoints without a ``project_id`` or ``task_id`` path parameter
      fall back to role-based checks (assignment cannot be determined).
    * Axioma 3: before returning 403, the dependency checks whether the
      referenced project/task exists in the actor's sede. If it does not
      exist or belongs to another sede, 404 is returned instead, even for
      the ``manage`` level.

    This implements the product decision that in the Projects module
    access is driven by task/project assignment, not only by platform role.
    """

    async def _check(
        request: Request,
        current_user: models.User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ):
        project_id = request.path_params.get("project_id")
        task_id = request.path_params.get("task_id")

        # Axioma 3 — existence-leak safe: before rejecting with 403, verify the
        # resource exists in the actor's scope. If the project/task belongs to
        # another sede (or does not exist), return 404 so cross-sede probing is
        # indistinguishable from a missing resource. This applies to all levels,
        # including manage, so a user without projects:manage still gets 404
        # (not 403) when the resource is cross-sede or non-existent.
        user_sede = get_user_sede_id(db, current_user.id)
        if user_sede is not None and (project_id or task_id):
            target_project_id = None
            if task_id:
                task_uuid = _to_uuid(task_id)
                if not isinstance(task_uuid, uuid.UUID):
                    raise HTTPException(status_code=404, detail="Task not found")
                task_row = (
                    db.query(models.ProjectTask.project_id)
                    .filter(
                        models.ProjectTask.id == task_uuid,
                        models.ProjectTask.deleted_at.is_(None),
                    )
                    .first()
                )
                if not task_row:
                    raise HTTPException(status_code=404, detail="Task not found")
                target_project_id = task_row.project_id
                # If the path also carries a project_id, it must match the
                # task's parent project. Otherwise the resource is not
                # where the URL says it is.
                if project_id:
                    path_project_uuid = _to_uuid(project_id)
                    if not isinstance(path_project_uuid, uuid.UUID) or str(target_project_id) != str(path_project_uuid):
                        raise HTTPException(status_code=404, detail="Task not found in project")
            elif project_id:
                project_uuid = _to_uuid(project_id)
                if not isinstance(project_uuid, uuid.UUID):
                    raise HTTPException(status_code=404, detail="Project not found")
                target_project_id = project_uuid

            if target_project_id is not None:
                project_sede = (
                    db.query(models.Project.sede_id)
                    .filter(
                        models.Project.id == target_project_id,
                        models.Project.deleted_at.is_(None),
                    )
                    .scalar()
                )
                if project_sede is None or str(project_sede) != str(user_sede):
                    raise HTTPException(status_code=404, detail="Project not found")

        # Role-based access is granted only after the resource scope check
        # above. This prevents an admin/editor role from probing or mutating
        # a project belonging to another sede.
        if _has_role_based_project_access(db, current_user, min_level):
            return current_user

        # manage level is strictly role-based
        if min_level == "manage":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permisos insuficientes. Se requiere: projects:{min_level}",
            )

        persona_id = _get_persona_id_for_user(db, current_user.id)
        if not persona_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permisos insuficientes. Se requiere: projects:{min_level}",
            )

        # Task-level endpoints take precedence when task_id is present
        if task_id and _is_assigned_to_task(db, task_id, persona_id):
            return current_user

        # Project-level assignment
        if project_id and _is_assigned_to_project(db, project_id, persona_id):
            return current_user

        # No project_id/task_id in path → cannot determine assignment
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permisos insuficientes. Se requiere: projects:{min_level}",
        )

    return _check


def _assert_assignee_in_sede(
    db: Session,
    assignee_id: Optional[uuid.UUID | str],
    user_sede: Optional[uuid.UUID | str],
) -> None:
    """Validate that an assignee persona belongs to the actor's ``sede_id``.

    Closed Axioma 3 enforcement on PATCH/POST payloads that carry an
    ``assignee_id``. Without this check, an actor from ``sede_a`` could
    inject a UUID of a persona from ``sede_b`` and have the backend
    transparently persist that cross-sede assignment.

    Behavior:
      * ``assignee_id`` falsy (None or empty) → silent skip (no assignee).
      * ``user_sede`` is ``None`` (superadmin) → no scope filter.
      * Otherwise the persona must exist AND live in the actor's sede.
        Personas with NULL ``sede_id`` are treated as untagged and
        blocked to avoid cross-sede leakage. Existence-leak safe: 404
        on mismatch (never 403).

    Note: ``_to_uuid`` is *not* raise-style — it returns the original bad
    value on parse failure. The downstream ``Persona.id ==`` filter then
    returns ``None`` and we map it to 404. We intentionally do NOT raise
    a separate 400 on malformed UUIDs; that's a single source of truth
    with the rest of the project.
    """
    if not assignee_id:
        return
    if user_sede is None:
        return
    persona_uuid = _to_uuid(assignee_id)
    persona = db.query(models.Persona).filter(models.Persona.id == persona_uuid).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Assignee not found")
    if persona.sede_id is None or str(persona.sede_id) != str(user_sede):
        # Existence-leak safe: indistinguishable from "not found".
        raise HTTPException(status_code=404, detail="Assignee not found")


def _assert_status_in_project_phases(db: Session, project_id: Any, status_value: Any) -> None:
    """Reject a task ``status`` that does not match any active ``ProjectPhase.slug``.

    Contract (test_projects_kanban_move.py RED suite, Sprint 1/2):

    * **400** (not 422): business-rule violation tied to DB state, not a
      Pydantic schema issue — distinct from FastAPI's 422 reserved for
      schema validation. FastAPI returns 422 only when static schema
      constraints are violated; kanban membership is a runtime concept.
    * Soft-deleted phases (``deleted_at IS NOT NULL``) are filtered out
      by :func:`crud.get_project_phases`, so they cannot be assigned —
      this satisfies ``test_patch_status_to_soft_deleted_phase_rejected``.
    * Empty / None ``status`` is treated as "not in payload" — callers
      that don't touch ``status`` should not be forced to send a value.
    * **Canonical fallback**: when the project has no active phases
      (e.g. test fixtures that create a project directly without calling
      ``create_default_phases_factory``) the canonical 4-phase set is
      accepted. Production always bootstraps default phases via the
      ``create_project`` endpoint so this path is guard-only — it keeps
      ``test_create_task`` from breaking under strict validation while
      still rejecting garbage slugs like ``"not_a_real_phase"``. Note:
      it is not a free-string fallback; only the 4 canonical phases are
      allowed.
    * Race window: there is an inherent race between this snapshot read
      and the subsequent ``setattr(task, "status", ...)`` if another
      request calls ``set_project_phases`` between them. Mitigations
      (SELECT … FOR SHARE, optimistic locking) are deferred until the
      drag-and-drop kanban endpoints need higher-throughput safety.

    The detail string intentionally contains both words "status" and
    "phase" so the test envelope assertion passes and consumers can
    pinpoint the offending axis.
    """
    if status_value is None:
        return
    # Normalize whitespace defensively without forbidding slugs that
    # legitimately contain spaces (none currently exist, but be safe).
    candidate = str(status_value).strip()
    if not candidate:
        return
    project_uuid = _to_uuid(project_id)
    phase_rows = crud.get_project_phases(db, project_uuid)
    if phase_rows:
        valid_slugs = {p.slug for p in phase_rows}
        source = "project phases"
    else:
        valid_slugs = _CANONICAL_PHASE_SLUGS
        source = "canonical defaults (project has no phases configured)"
    if candidate in valid_slugs:
        return
    pretty = ", ".join(sorted(valid_slugs))
    raise HTTPException(
        status_code=400,
        detail=(f"status '{candidate}' is not a valid phase. Active phases for this {source}: [{pretty}]"),
    )


_MAX_WHITEBOARD_JSON_BYTES = 20 * 1024 * 1024


def _validate_whiteboard_json(elements_json: str) -> None:
    """Valida que elements_json sea JSON válido y con forma esperada.

    Rechaza el literal "undefined" (bug de cliente JS), JSON malformado,
    payloads vacíos o demasiado grandes, y árboles JSON cuya top-level no sea
    un objeto (canvas.toJSON de fabric) o un array de elementos (tests / API
    directa). Cada elemento debe ser un objeto, no un primitivo.
    """
    if not isinstance(elements_json, str):
        raise HTTPException(status_code=400, detail="elements_json must be a string")
    if len(elements_json.encode("utf-8")) > _MAX_WHITEBOARD_JSON_BYTES:
        raise HTTPException(status_code=400, detail="elements_json exceeds the maximum allowed size")
    stripped = elements_json.strip()
    if not stripped:
        raise HTTPException(status_code=400, detail="elements_json must not be empty")
    if stripped.lower() == "undefined":
        raise HTTPException(status_code=400, detail="elements_json must be valid JSON, got 'undefined'")
    try:
        parsed = json.loads(elements_json)
    except (json.JSONDecodeError, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="elements_json must be valid JSON")

    if not isinstance(parsed, (dict, list)):
        raise HTTPException(status_code=400, detail="elements_json must be a JSON object or array")

    def _items_are_objects(items: list) -> None:
        for item in items:
            if not isinstance(item, dict):
                raise HTTPException(status_code=400, detail="elements_json list items must be JSON objects")

    if isinstance(parsed, list):
        _items_are_objects(parsed)
    elif "objects" in parsed:
        # fabric.Canvas.toJSON() shape: {"version": "...", "objects": [...]}
        if not isinstance(parsed["objects"], list):
            raise HTTPException(status_code=400, detail="elements_json 'objects' must be a list")
        _items_are_objects(parsed["objects"])


def _whiteboard_utc(value: datetime) -> datetime:
    """Normaliza timestamps de versión (SQLite puede devolverlos sin tzinfo)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


# Canonical 4-phase set used when a project has no active Phase rows
# configured (most often in tests that bypass ``create_default_phases``).
# This is intentionally a tight allow-list, not a free-string fallback.
_CANONICAL_PHASE_SLUGS: frozenset[str] = frozenset({"todo", "in_progress", "review", "completed"})

# Compat enum values that may still exist in client payloads or old DB rows.
# These are normalized to canonical values on read/write to avoid 422 errors
# and to keep the UI consistent.
_COMPAT_PRIORITY_MAP: dict[str, str] = {"normal": "medium"}
_COMPAT_STATUS_MAP: dict[str, str] = {"done": "completed", "blocked": "todo", "pending": "todo"}


def _normalize_task_payload(payload: dict) -> dict:
    """Map compat task status/priority values to canonical enums in payloads."""
    if "priority" in payload and isinstance(payload["priority"], str):
        payload["priority"] = _COMPAT_PRIORITY_MAP.get(payload["priority"], payload["priority"])
    if "status" in payload and isinstance(payload["status"], str):
        payload["status"] = _COMPAT_STATUS_MAP.get(payload["status"], payload["status"])
    return payload


def _normalize_task_enums(task: models.ProjectTask) -> None:
    """Map compat task status/priority values stored on a task row to canonical enums."""
    if task.priority in _COMPAT_PRIORITY_MAP:
        task.priority = _COMPAT_PRIORITY_MAP[task.priority]
    if task.status in _COMPAT_STATUS_MAP:
        task.status = _COMPAT_STATUS_MAP[task.status]


def _prepare_task_for_response(task: models.ProjectTask) -> models.ProjectTask:
    _normalize_task_enums(task)
    _normalize_dates(task)
    if hasattr(task, "supplies") and task.supplies:
        task.supplies = [s for s in task.supplies if s.deleted_at is None]
    if hasattr(task, "subtasks") and task.subtasks:
        task.subtasks = [_prepare_task_for_response(sub) for sub in task.subtasks if sub.deleted_at is None]
    return task


def _prepare_project_for_response(project: models.Project) -> models.Project:
    _normalize_dates(project)
    for milestone in getattr(project, "milestones", []) or []:
        _normalize_dates(milestone)
    for task in getattr(project, "tasks", []) or []:
        _prepare_task_for_response(task)
    for kpi in getattr(project, "kpis", []) or []:
        _normalize_dates(kpi)
    for dep in getattr(project, "dependencies", []) or []:
        _normalize_dates(dep)
    for exp in getattr(project, "expenses", []) or []:
        _normalize_dates(exp)
    for risk in getattr(project, "risks", []) or []:
        _normalize_dates(risk)
    return project


def _normalize_dates(obj):
    if not obj:
        return obj
    # Soporte mejorado para multiples formatos de fecha de SQLite
    for attr in [
        "created_at",
        "target_date",
        "due_date",
        "start_date",
        "end_date",
        "updated_at",
        "last_edited_at",
    ]:
        val = getattr(obj, attr, None)
        if val and isinstance(val, str):
            try:
                # Limpiar milisegundos si es necesario
                clean_val = val.split(".")[0] if "." in val and "T" not in val else val
                setattr(
                    obj,
                    attr,
                    datetime.fromisoformat(clean_val.replace(" ", "T").replace("Z", "+00:00")),
                )
            except MemoryError:
                raise
            except (ValueError, TypeError, OverflowError) as exc:
                logger.warning(
                    "Failed to normalize project date: %s",
                    exc,
                    extra={"attribute": attr, "value": val},
                )
                if attr == "created_at":
                    setattr(obj, attr, datetime.now())
    return obj


@router.get("/assignee-candidates", response_model=List[schemas.ProjectAssigneeCandidate])
def list_project_assignee_candidates(
    search: Optional[str] = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Return minimal candidate data scoped to the authenticated Projects tenant."""
    user_sede = get_user_sede_id(db, current_user.id)
    if not user_sede:
        raise HTTPException(status_code=409, detail="El usuario no tiene una sede asignada")

    sede_uuid = UUID(str(user_sede))
    query = db.query(models.Persona).filter(models.Persona.sede_id == sede_uuid)
    search_term = (search or "").strip()
    if search_term:
        pattern = f"%{search_term}%"
        query = query.filter(
            or_(
                models.Persona.first_name.ilike(pattern),
                models.Persona.last_name.ilike(pattern),
                models.Persona.nombre_completo.ilike(pattern),
            )
        )

    candidates = query.order_by(
        models.Persona.first_name.asc(), models.Persona.last_name.asc(), models.Persona.id.asc()
    ).limit(limit).all()
    return [
        schemas.ProjectAssigneeCandidate(id=person.id, nombre_completo=person.nombre_completo)
        for person in candidates
    ]


@router.get("/assignee-candidates/{persona_id}", response_model=schemas.ProjectAssigneeCandidate)
def get_project_assignee_candidate(
    persona_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Resolve a selected assignment name without requiring CRM access."""
    user_sede = get_user_sede_id(db, current_user.id)
    if not user_sede:
        raise HTTPException(status_code=409, detail="El usuario no tiene una sede asignada")

    person = (
        db.query(models.Persona)
        .filter(models.Persona.id == persona_id, models.Persona.sede_id == UUID(str(user_sede)))
        .first()
    )
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return schemas.ProjectAssigneeCandidate(id=person.id, nombre_completo=person.nombre_completo)


@router.get("", response_model=List[schemas.Project])
def list_projects(
    status_filter: Optional[str] = Query(None, alias="status"),
    owner_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    query = (
        db.query(models.Project)
        .options(
            selectinload(models.Project.tasks).selectinload(models.ProjectTask.attachments),
            selectinload(models.Project.milestones),
        )
        .filter(models.Project.deleted_at.is_(None))
    )
    if user_sede:
        query = query.filter(models.Project.sede_id == user_sede)
    if status_filter:
        query = query.filter(models.Project.status == status_filter)
    if owner_id:
        query = query.filter(models.Project.owner_id == owner_id)

    projects = query.order_by(models.Project.created_at.desc(), models.Project.id.desc()).all()
    for p in projects:
        _prepare_project_for_response(p)
    return projects


@router.get("/page", response_model=schemas.PaginatedResponse[schemas.Project])
def list_projects_page(
    status_filter: Optional[str] = Query(None, alias="status"),
    owner_id: Optional[UUID] = None,
    search: Optional[str] = Query(None, max_length=200),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Paginated listing for interactive screens; legacy ``/projects`` stays compatible."""
    user_sede = get_user_sede_id(db, current_user.id)
    projects, total = crud.get_projects_page(
        db,
        offset=offset,
        limit=limit,
        sede_id=user_sede,
        status_filter=status_filter,
        owner_id=owner_id,
        search=search,
    )
    for project in projects:
        _prepare_project_for_response(project)
    return {"items": projects, "total": total, "skip": offset, "limit": limit}


@router.get("/summary-page", response_model=schemas.PaginatedResponse[schemas.ProjectSummary])
def list_project_summaries_page(
    status_filter: Optional[str] = Query(None, alias="status"),
    owner_id: Optional[UUID] = None,
    search: Optional[str] = Query(None, max_length=200),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Bounded collection for overview screens; returns aggregates, not child graphs."""
    user_sede = get_user_sede_id(db, current_user.id)
    rows, total = crud.get_project_summaries_page(
        db,
        offset=offset,
        limit=limit,
        sede_id=user_sede,
        status_filter=status_filter,
        owner_id=owner_id,
        search=search,
    )
    items = []
    for row in rows:
        project = row["project"]
        item = schemas.ProjectSummary.model_validate({
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "status": project.status,
            "owner_id": project.owner_id,
            "color": project.color,
            "icon": project.icon,
            "start_date": project.start_date,
            "target_date": project.target_date,
            "progress_mode": project.progress_mode,
            "manual_progress": project.manual_progress,
            "budget_allocated": project.budget_allocated,
            "budget_spent": project.budget_spent,
            "health_override": project.health_override,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "task_count": row["task_count"],
            "completed_task_count": row["completed_task_count"],
            "in_progress_task_count": row["in_progress_task_count"],
        })
        if item.status == "completed":
            item.health_status = "completed"
        elif item.health_override:
            item.health_status = item.health_override
        elif row["overdue_task_count"] >= 2:
            item.health_status = "off_track"
        elif row["overdue_task_count"] == 1:
            item.health_status = "at_risk"
        else:
            item.health_status = "on_track"

        if item.progress_mode == "manual":
            item.progress_percent = max(0, min(100, round(item.manual_progress or 0)))
        elif item.progress_mode == "milestones" and row["milestone_count"]:
            item.progress_percent = round(
                row["completed_milestone_count"] / row["milestone_count"] * 100
            )
        elif item.task_count:
            item.progress_percent = round(item.completed_task_count / item.task_count * 100)
        items.append(item)
    return {"items": items, "total": total, "skip": offset, "limit": limit}


@router.post("", response_model=schemas.Project, status_code=status.HTTP_201_CREATED)
def create_project(
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    owner_persona_id = get_user_persona_id(db, current_user.id)
    user_sede = get_user_sede_id(db, current_user.id)
    if not user_sede:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario autenticado no tiene una sede asignada para crear proyectos",
        )
    requested_owner_id = project.owner_id or owner_persona_id
    if requested_owner_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Asigna un responsable o vincula el usuario autenticado a una persona antes de crear el proyecto",
        )
    _assert_assignee_in_sede(db, requested_owner_id, user_sede)
    try:
        db_project = crud.create_project(
            db,
            project,
            owner_persona_id=requested_owner_id,
            sede_id=user_sede,
            commit=False,
        )
        crud.create_default_phases(db, db_project.id, commit=False)
        db.commit()
        db.refresh(db_project)
    except Exception:
        db.rollback()
        raise

    if owner_persona_id:
        crud.create_activity_log(
            db, db_project.id, owner_persona_id, "project_created", f"Proyecto '{db_project.title}' creado"
        )

    record_admin_action(
        db, current_user, action="create_project", resource_type="project", resource_id=str(db_project.id)
    )
    _normalize_dates(db_project)
    return db_project


# ── Phases / Kanban Columns ─────────────────────────────


@router.get("/{project_id}/phases", response_model=List[schemas.ProjectPhaseSchema])
def list_project_phases(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("read")),
):
    """Lista las fases (columnas del kanban) de un proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    return crud.get_project_phases(db, project_id)


@router.put("/{project_id}/phases", response_model=List[schemas.ProjectPhaseSchema])
def set_project_phases(
    project_id: str,
    phases: List[schemas.ProjectPhaseInput],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("manage")),
):
    """Reemplaza todas las fases del proyecto (reordenar / renombrar / agregar / eliminar).
    El orden en el array define el order_index de cada fase.
    Solo administradores y gestores pueden modificar fases.
    El acceso se valida con ``require_project_access("manage")``; por tanto,
    un usuario sin permisos de manage recibe 404 (no 403) cuando el proyecto
    no existe o pertenece a otra sede (Axioma 3).
    """
    user_sede = get_user_sede_id(db, current_user.id)
    _project = _ensure_project(db, project_id, user_sede=user_sede)
    # Race-condition fix: lock the parent project row while we validate
    # task counts and apply the phase rewrite, so concurrent inserts
    # under a status about to be removed cannot create orphan tasks.
    db.query(models.Project).filter(models.Project.id == _to_uuid(project_id)).with_for_update().first()

    # Check no phase with tasks is being deleted
    existing = {p.slug for p in crud.get_project_phases(db, project_id)}
    incoming = {p.slug for p in phases}
    removed = existing - incoming
    if removed:
        has_tasks = (
            db.query(models.ProjectTask)
            .filter(
                models.ProjectTask.project_id == project_id,
                models.ProjectTask.status.in_(removed),
            )
            .count()
        )
        if has_tasks:
            raise HTTPException(
                status_code=409,
                detail=f"No se puede eliminar la fase '{next(iter(removed))}': tiene {has_tasks} tarea(s) asignada(s). Mueve las tareas primero.",
            )

    phase_dicts = [
        {
            "name": p.name,
            "slug": p.slug,
            "color": p.color,
            "order_index": i,
            "start_date": getattr(p, "start_date", None),
            "end_date": getattr(p, "end_date", None),
        }
        for i, p in enumerate(phases)
    ]
    created = crud.set_project_phases(db, _to_uuid(project_id), phase_dicts)
    for ph in created:
        _normalize_dates(ph)
    return created


# --- COMMENTS ---


@router.get("/comments", response_model=List[schemas.ProjectCommentItem])
def list_all_comments(
    unresolved_only: bool = False,
    limit: int = Query(120, le=500),
    offset: int = Query(0, ge=0),
    project_id: Optional[str] = None,
    task_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista todos los comentarios de proyectos con filtros opcionales.

    Axioma 3 — strict scope: el feed global de comentarios queda acotado
    a los proyectos del actor. La ruta acepta un ``project_id`` opcional
    para filtrado explícito (validado vía ``_ensure_project``); cuando
    NO se pasa project_id, la respuesta agrega comentarios de proyectos
    visibles para la ``sede_id`` del actor. Superadmin (sin sede) sigue
    viendo todo, consistente con ``list_projects``.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    q = db.query(models.ProjectComment).filter(models.ProjectComment.deleted_at.is_(None))
    if project_id:
        # Validate scope at the project level before exposing its comments.
        _ensure_project(db, project_id, user_sede=user_sede)
        q = q.filter(models.ProjectComment.project_id == _to_uuid(project_id))
    elif user_sede:
        # No project filter → join with Project and keep only those in
        # the actor's sede. Also exclude comments on soft-deleted projects.
        q = q.join(models.Project, models.Project.id == models.ProjectComment.project_id).filter(
            models.Project.sede_id == user_sede,
            models.Project.deleted_at.is_(None),
        )
    if unresolved_only:
        q = q.filter(models.ProjectComment.is_resolved.is_(False))
    if task_id:
        q = q.filter(models.ProjectComment.task_id == _to_uuid(task_id))
    rows = (
        q.order_by(models.ProjectComment.is_pinned.desc(), models.ProjectComment.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    # Batch-fetch authors and pinners to avoid N+1 queries
    author_ids = {row.author_id for row in rows if row.author_id}
    pinner_ids = {row.pinned_by for row in rows if getattr(row, "pinned_by", None)}
    all_person_ids = author_ids | pinner_ids
    persons_map = {}
    if all_person_ids:
        persons = db.query(models.Persona).filter(models.Persona.id.in_(all_person_ids)).all()
        persons_map = {p.id: _author_name(p) for p in persons}
    result = []
    for row in rows:
        result.append(
            schemas.ProjectCommentItem(
                id=row.id,
                project_id=str(row.project_id) if row.project_id is not None else None,
                task_id=str(row.task_id) if row.task_id is not None else None,
                content=row.content,
                author_id=str(row.author_id) if row.author_id is not None else None,
                author_name=persons_map.get(row.author_id, "Usuario"),
                is_resolved=row.is_resolved,
                is_pinned=getattr(row, "is_pinned", False),
                pinned_at=getattr(row, "pinned_at", None),
                pinned_by=str(row.pinned_by) if getattr(row, "pinned_by", None) is not None else None,
                pinner_name=persons_map.get(row.pinned_by) if getattr(row, "pinned_by", None) else None,
                created_at=row.created_at,
                updated_at=row.updated_at,
                attachments=row.attachments or [],
                mentions=[str(m) for m in (row.mentions or [])],
            )
        )
    return result


@router.post(
    "/{project_id}/tasks",
    response_model=schemas.ProjectTask,
    status_code=status.HTTP_201_CREATED,
)
def create_project_task(
    project_id: str,
    task: schemas.ProjectTaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    if task.parent_id:
        _ensure_task_in_project(db, project_id, str(task.parent_id))
    # Race-condition fix: acquire a row lock on the parent project so the
    # subsequent MAX(order_index) + INSERT is serialized across concurrent
    # task creations. On PostgreSQL this is a real SELECT ... FOR UPDATE;
    # on SQLite it is a no-op (the test suite runs serialized transactions).
    project = db.query(models.Project).filter(models.Project.id == _to_uuid(project_id)).with_for_update().first()
    payload = task.model_dump()
    _normalize_task_payload(payload)
    _assert_status_in_project_phases(db, project_id, payload.get("status"))
    _assert_assignee_in_sede(db, payload.get("assignee_id"), user_sede)
    try:
        crud.validate_task_dates_within_phase(
            db,
            project_id,
            status_slug=payload.get("status"),
            node=payload.get("node"),
            start_date=payload.get("start_date"),
            due_date=payload.get("due_date"),
        )
    except (crud.TaskDateOutOfBoundsError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    max_order = (
        db.query(func.max(models.ProjectTask.order_index))
        .filter(models.ProjectTask.project_id == _to_uuid(project_id))
        .scalar()
        or 0
    )
    payload["project_id"] = _to_uuid(project_id)
    payload["order_index"] = max_order + 1
    db_task = models.ProjectTask(**payload)
    db.add(db_task)

    # Bitacora Ministerial
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "task_created",
        f"Tarea '{db_task.title}' lanzada por {getattr(current_user, 'username', getattr(current_user, 'email', 'usuario'))}",
    )
    db.commit()
    db.refresh(db_task)
    if getattr(db_task, "assignee_id", None):
        notify_task_assigned(
            db,
            task=db_task,
            project=project,
            assigned_by_user_id=current_user.id,
        )
    return db_task


# ── PORTFOLIO SUMMARY ──────────────────────────────────────────────────────────


@router.get("/summary", response_model=List[schemas.ProjectPortfolioSummaryRow])
def portfolio_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Resumen de portafolio agrupado por estatus de proyecto.

    Axioma 3 — strict scope: solo se agregan proyectos en la ``sede_id``
    del actor. Superadmin (sin sede) ve todo.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    done_case = func.coalesce(func.sum(cast(models.ProjectTask.status == "completed", Integer)), 0).label(
        "completed_tasks"
    )

    q = (
        db.query(
            models.Project.status,
            func.count(func.distinct(models.Project.id)).label("total_projects"),
            func.count(models.ProjectTask.id).label("total_tasks"),
            done_case,
        )
        .outerjoin(
            models.ProjectTask,
            and_(
                models.ProjectTask.project_id == models.Project.id,
                models.ProjectTask.deleted_at.is_(None),
            ),
        )
        .filter(models.Project.deleted_at.is_(None))
    )
    if user_sede:
        q = q.filter(models.Project.sede_id == user_sede)
    rows = q.group_by(models.Project.status).all()

    return [
        schemas.ProjectPortfolioSummaryRow(
            project_status=row[0] or "unknown",
            total_projects=row[1],
            total_tasks=row[2] or 0,
            completed_tasks=row[3] or 0,
            completion_ratio=round((row[3] or 0) / max(row[2] or 1, 1), 2),
        )
        for row in rows
    ]


@router.get("/workload", response_model=List[schemas.ProjectWorkloadSummaryRow])
def workload_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Resumen de carga de trabajo por persona.

    Axioma 3 — strict scope consistente con el resto del módulo: solo se
    agregan tareas de proyectos en la ``sede_id`` del actor. Superadmin
    (``user_sede`` = ``None``) ve todo.

    N+1 fix (oportunista, Sprint 1.1) — antes este endpoint emitía una
    query de ``COUNT(overdue)`` por cada assignee devolvido por la query
    principal (1 + N queries). Ahora las tres métricas (open / in_review /
    overdue) se agregan en un único ``GROUP BY`` con ``CASE`` expressions
    portable sobre SQLite + Postgres. Una sola query para N assignees.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    open_statuses = ("todo", "in_progress", "review")
    now_expr = func.now()

    open_count = func.count(models.ProjectTask.id).label("open_tasks")
    in_review_count = func.coalesce(
        func.sum(cast(models.ProjectTask.status == "review", Integer)),
        0,
    ).label("in_review")
    overdue_count = func.coalesce(
        func.sum(
            cast(
                models.ProjectTask.status.in_(open_statuses) & (models.ProjectTask.due_date < now_expr),
                Integer,
            )
        ),
        0,
    ).label("overdue_tasks")

    q = db.query(
        models.ProjectTask.assignee_id,
        open_count,
        in_review_count,
        overdue_count,
    ).filter(
        models.ProjectTask.status.in_(open_statuses),
        models.ProjectTask.assignee_id.isnot(None),
        models.ProjectTask.deleted_at.is_(None),
    )
    if user_sede:
        # Single JOIN when scope is set; supplies ``Project.sede_id`` to the
        # WHERE. Without this the workload feed would leak cross-sede rows.
        q = q.join(models.Project, models.Project.id == models.ProjectTask.project_id).filter(
            models.Project.sede_id == user_sede
        )

    rows = q.group_by(models.ProjectTask.assignee_id).order_by(open_count.desc()).all()
    return [
        schemas.ProjectWorkloadSummaryRow(
            assignee_id=str(row.assignee_id) if row.assignee_id else None,
            open_tasks=row.open_tasks or 0,
            in_review=row.in_review or 0,
            overdue_tasks=row.overdue_tasks or 0,
        )
        for row in rows
    ]


# ── TEAM (MEMBRESÍA DEL PROYECTO) ────────────────────────────────────────────


def _serialize_member(member: models.ProjectMember) -> schemas.ProjectMember:
    name = None
    if member.persona:
        name = (
            getattr(member.persona, "nombre_completo", None)
            or getattr(member.persona, "full_name", None)
            or f"{getattr(member.persona, 'first_name', '')} {getattr(member.persona, 'last_name', '')}".strip()
            or None
        )
    return schemas.ProjectMember(
        id=str(member.id),
        project_id=str(member.project_id),
        persona_id=str(member.persona_id),
        role=member.role or "member",
        invited_at=member.invited_at,
        persona_name=name,
    )


@router.get("/{project_id}/team", response_model=List[schemas.ProjectMember])
def list_project_team(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("read")),
):
    """Lista los miembros del equipo del proyecto.

    Axioma 3 — strict scope: ``_ensure_project`` valida que el proyecto
    pertenezca a la sede del actor antes de listar miembros.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    members = (
        db.query(models.ProjectMember)
        .options(selectinload(models.ProjectMember.persona))
        .filter(
            models.ProjectMember.project_id == _to_uuid(project_id),
            models.ProjectMember.deleted_at.is_(None),
        )
        .order_by(models.ProjectMember.invited_at.asc())
        .all()
    )
    return [_serialize_member(m) for m in members]


@router.post(
    "/{project_id}/team",
    response_model=schemas.ProjectMember,
    status_code=status.HTTP_201_CREATED,
)
def invite_project_member(
    project_id: str,
    payload: schemas.ProjectMemberCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Invita a una persona de la sede a colaborar en el proyecto (F4).

    Valida que la persona exista y pertenezca a la sede del actor, y evita
    duplicados (unique constraint ``uq_project_member_persona`` → 409).
    """
    user_sede = get_user_sede_id(db, current_user.id)
    project = _ensure_project(db, project_id, user_sede=user_sede)
    persona = db.query(models.Persona).filter(models.Persona.id == _to_uuid(payload.persona_id)).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    if user_sede is not None:
        persona_sede = getattr(persona, "sede_id", None)
        if persona_sede is None or str(persona_sede) != str(user_sede):
            raise HTTPException(status_code=404, detail="Persona no encontrada en esta sede")

    existing = (
        db.query(models.ProjectMember)
        .filter(
            models.ProjectMember.project_id == _to_uuid(project_id),
            models.ProjectMember.persona_id == _to_uuid(payload.persona_id),
        )
        .first()
    )
    if existing and existing.deleted_at is None:
        raise HTTPException(status_code=409, detail="La persona ya es miembro del proyecto")

    if existing and existing.deleted_at is not None:
        # Re-invitación: reactivar la membresía previamente retirada (soft delete).
        existing.deleted_at = None
        existing.invited_at = _utcnow()
        db.add(existing)
        _log_project_activity(
            db,
            project_id,
            current_user.id,
            "member_invited",
            f"{_author_name(persona)} invitado al equipo de '{project.title}'",
        )
        db.commit()
        db.refresh(existing)
        existing.persona = persona
        return _serialize_member(existing)

    member = models.ProjectMember(
        project_id=_to_uuid(project_id),
        persona_id=_to_uuid(payload.persona_id),
        role="member",
    )
    db.add(member)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "member_invited",
        f"{_author_name(persona)} invitado al equipo de '{project.title}'",
    )
    db.commit()
    db.refresh(member)
    member.persona = persona
    return _serialize_member(member)


@router.delete("/{project_id}/team/{persona_id}", response_model=dict)
def remove_project_member(
    project_id: str,
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Retira a una persona del equipo del proyecto (F4, soft delete).

    Cumple Regla 4 (no hard deletes en tablas transaccionales): marca
    ``deleted_at`` en lugar de ``db.delete``. Una persona retirada puede
    volver a ser invitada (reactivación en POST /team).
    """
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    member = (
        db.query(models.ProjectMember)
        .filter(
            models.ProjectMember.project_id == _to_uuid(project_id),
            models.ProjectMember.persona_id == _to_uuid(persona_id),
            models.ProjectMember.deleted_at.is_(None),
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="La persona no es miembro del proyecto")
    member.deleted_at = _utcnow()
    db.commit()
    return {"ok": True, "removed": str(persona_id)}


@router.get("/activities", response_model=List[schemas.ProjectActivityItem])
def list_activities(
    limit: int = Query(20, le=200),
    offset: int = Query(0, ge=0),
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Feed de actividad global de proyectos.

    Axioma 3 — strict scope: cuando NO se pasa ``project_id`` el feed
    se acota a bitacoras de proyectos visibles para la ``sede_id`` del
    actor (join con Project). Cuando SÍ se pasa ``project_id``, se
    valida la sede del proyecto con ``_ensure_project``. Esto elimina
    el leak cross-sede del feed ministerial.

    N+1 fix (oportunista, Sprint 1.1) — antes cada log disparaba su
    propio ``db.query(Project).filter(id=log.project_id).first()`` para
    resolver ``project_title``. Con ``limit=200`` eso eran hasta 200
    queries por request. Ahora se hace un único ``IN (...)`` batch y se
    indexa por ``project_id`` en un dict para O(1) lookup por log.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    q = db.query(models.ProjectActivityLog)
    if project_id:
        _ensure_project(db, project_id, user_sede=user_sede)
        q = q.filter(models.ProjectActivityLog.project_id == _to_uuid(project_id))
    elif user_sede:
        # Join con Project para que ``Project.sede_id`` sea usable en el filtro.
        # Exclude activity logs from soft-deleted projects.
        q = q.join(models.Project, models.Project.id == models.ProjectActivityLog.project_id).filter(
            models.Project.sede_id == user_sede,
            models.Project.deleted_at.is_(None),
        )
    logs = q.order_by(models.ProjectActivityLog.created_at.desc()).offset(offset).limit(limit).all()

    # ── Batch fetch: 1 query for the unique project_ids of this page ──
    project_ids = {log.project_id for log in logs if log.project_id}
    projects_map: dict = {}
    if project_ids:
        rows = db.query(models.Project.id, models.Project.title).filter(models.Project.id.in_(project_ids)).all()
        projects_map = {pid: title for pid, title in rows}

    result = []
    for log in logs:
        _normalize_dates(log)
        result.append(
            schemas.ProjectActivityItem(
                id=str(log.id),
                kind=log.action_type,
                project_id=str(log.project_id) if log.project_id is not None else None,
                project_title=projects_map.get(log.project_id, "Proyecto"),
                description=log.description or "",
                created_at=log.created_at or _utcnow(),
            )
        )
    return result


@router.get("/tasks/{task_id}", response_model=schemas.ProjectTask)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("read")),
):
    """Obtiene una tarea por ID.

    Axioma 3 — cross-sede defense-in-depth: validate the task's parent
    project against the actor's ``sede_id`` via ``_ensure_project``. Without
    this, a user from sede_a could fetch a task in sede_b just by guessing
    the task_id.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    task = _ensure_task(db, task_id)
    _ensure_project(db, str(task.project_id), user_sede=user_sede)
    _normalize_task_enums(task)
    _normalize_dates(task)
    return task


@router.patch("/tasks/{task_id}", response_model=schemas.ProjectTask)
def update_task(
    task_id: str,
    payload: schemas.ProjectTaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Actualiza una tarea usando ruta plana (sin project_id).

    Axioma 3 — the flat PATCH path takes only ``task_id``. We must
    validate the task's parent project via ``_ensure_project`` so a
    sede_a user cannot mutate tasks in sede_b projects just by knowing
    the task_id (existence-leak safe: returns 404, not 403).
    """
    user_sede = get_user_sede_id(db, current_user.id)
    task = _ensure_task(db, task_id)
    _ensure_project(db, str(task.project_id), user_sede=user_sede)
    update_data = payload.model_dump(exclude_unset=True)
    _normalize_task_payload(update_data)
    if "status" in update_data:
        _assert_status_in_project_phases(db, task.project_id, update_data["status"])
    if "assignee_id" in update_data:
        _assert_assignee_in_sede(db, update_data["assignee_id"], user_sede)

    effective_status = update_data.get("status", task.status)
    effective_node = update_data.get("node", getattr(task, "node", None))
    effective_start = update_data.get("start_date", task.start_date)
    effective_due = update_data.get("due_date", task.due_date)
    try:
        crud.validate_task_dates_within_phase(
            db,
            task.project_id,
            status_slug=effective_status,
            node=effective_node,
            start_date=effective_start,
            due_date=effective_due,
            task_id=task.id,
        )
    except (crud.TaskDateOutOfBoundsError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    previous_assignee_id = getattr(task, "assignee_id", None)
    previous_values = {key: getattr(task, key, None) for key in update_data}
    for key, value in update_data.items():
        setattr(task, key, value)
    _normalize_task_enums(task)
    changed_fields = [key for key in update_data if previous_values[key] != getattr(task, key, None)]
    if changed_fields:
        _log_project_activity(
            db,
            str(task.project_id),
            current_user.id,
            "task_updated",
            f"Tarea '{task.title}' actualizada: {', '.join(changed_fields)}",
        )
    task.updated_at = _utcnow()
    db.commit()
    db.refresh(task)
    if (
        "assignee_id" in update_data
        and _assignment_changed(previous_assignee_id, getattr(task, "assignee_id", None))
        and task.assignee_id
    ):
        notify_task_assigned(
            db,
            task=task,
            assigned_by_user_id=current_user.id,
            previous_assignee_id=previous_assignee_id,
        )
    _normalize_dates(task)
    return task


# ── INBOX (must be before /{project_id} routes) ────────────────────────────────


@router.get("/inbox", response_model=List[schemas.ProjectInboxItem])
def list_inbox(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Bandeja de entrada unificada por persona: 2 superficies en un solo feed.

    **Endpoint**: ``GET /api/projects/inbox?limit=N`` (default 50, máx 200).

    **Response shape**: ``List[ProjectInboxItem]`` (ver Pydantic en
    ``backend/schemas/projects.py``). Cada item expone ``id`` composite
    (``"comment-<id>"`` / ``"task-<id>"``), ``type`` (``"comment"`` /
    ``"task_assigned"``), ``user``, ``content``, ``project``,
    ``project_id``, ``task_id`` (opcional), ``task_title`` (opcional),
    ``is_read`` y ``created_at``.

    **Superficies combinadas** (ordenadas independientemente, truncadas al
    ``limit`` final):

    1. **Comentarios no resueltos** (``type="comment"``): ``ProjectComment``
       con ``~is_resolved``, ``author_id != persona_id`` (excluye
       auto-comentarios). Orden: ``created_at desc``.
    2. **Tareas abiertas asignadas al actor** (``type="task_assigned"``):
       ``ProjectTask`` con ``assignee_id == persona_id``,
       ``status != "completed"``, ``deleted_at IS NULL``. Orden:
       ``updated_at desc``.

    **Marca de leído** (sincronizada vía ``POST /api/projects/inbox/{item_id}/read``):
    ``ProjectInboxState`` con UNIQUE ``(persona_id, item_id)``. Una query
    batch por superficie resuelve el flag ``is_read`` en O(1) por item.

    **RBAC**:

    * ``GET /inbox`` requiere ``projects:read`` (decorador). Admin / Gestor
      / Editor pasan; **Miembro = 403** (baseline documentado en
      ``tests/test_projects_rbac.py`` + ``PEND-RBAC-001``).
    * ``POST /inbox/{item_id}/read`` requiere ``projects:edit``.

    **Axioma 3 (multi-tenant)**:

    * Sedes sentadas: sólo items de proyectos cuya ``Project.sede_id ==
      user_sede``. Cross-sede unread comments + out-of-sede assigned
      tasks filtrados server-side. Proyectos soft-deleted excluidos.
    * Superadmin (``user_sede = None``): ve todo (consistente con
      ``list_projects`` / ``list_whiteboards`` / ``list_activities``).

    **Performance**: N+1 fix (Sprint 1.1). Un ``IN (...)`` batch por
    superficie para resolver ``author_name`` / ``project_title`` más un
    batch para resolver ``is_read`` desde ``project_inbox_state``.
    ``selectinload(Project.owner)`` evita N+1 al resolver ``user`` en
    items ``task_assigned``.

    **Diferencia con ``GET /api/projects/activities``**: ``activities`` es
    bitácora cruda universal por proyecto; ``inbox`` es feed normalizado
    por persona con merge de 2 superficies y estado ``is_read``.

    Contrato documentado en handover canónico:
    ``ccf/docs/ESTADO_PROYECTOS.md`` §4.1 (cierre de ``PEND-INBOX-CONTRACT-001``).
    """
    inbox_items: list[schemas.ProjectInboxItem] = []

    # Obtener persona_id (UUID) desde current_user.id (Integer)
    persona = _resolve_persona(db, current_user.id)
    persona_id = persona.id if persona else None
    user_sede = get_user_sede_id(db, current_user.id)

    # Comentarios no leídos en proyectos del usuario
    unread_comments = ()
    if persona_id:
        q_unread = (
            db.query(models.ProjectComment, models.Project)
            .join(models.Project, models.Project.id == models.ProjectComment.project_id)
            .filter(
                ~models.ProjectComment.is_resolved,
                models.ProjectComment.deleted_at.is_(None),
                models.ProjectComment.author_id != persona_id,
                # PEND-QUALITY-INBOX-SCOPE-001 (2026-07-16): excluir
                # comentarios cuyo proyecto esté soft-deleted para que el
                # feed del inbox no muestre fantasmas tras un borrado.
                models.Project.deleted_at.is_(None),
            )
        )
        if user_sede:
            q_unread = q_unread.filter(models.Project.sede_id == user_sede)
        unread_comments = q_unread.order_by(models.ProjectComment.created_at.desc()).limit(limit).all()

    # ── Batch-fetch authors + inbox states (N+1 fix) ──
    comment_author_ids = {c.author_id for c, _ in unread_comments if c.author_id}
    comment_item_ids = {f"comment-{c.id}" for c, _ in unread_comments}
    authors_map: dict = {}
    if comment_author_ids:
        authors_map = {
            p.id: _author_name(p)
            for p in db.query(models.Persona).filter(models.Persona.id.in_(comment_author_ids)).all()
        }
    inbox_states_map: dict = {}
    if comment_item_ids and persona_id:
        inbox_states_map = {
            s.item_id: s.is_read
            for s in db.query(models.ProjectInboxState)
            .filter(
                models.ProjectInboxState.persona_id == persona_id,
                models.ProjectInboxState.item_id.in_(comment_item_ids),
            )
            .all()
        }

    for comment, project in unread_comments:
        item_id = f"comment-{comment.id}"
        is_read = inbox_states_map.get(item_id, False)
        inbox_items.append(
            schemas.ProjectInboxItem(
                id=item_id,
                type="comment",
                user=authors_map.get(comment.author_id, "Usuario"),
                content=comment.content[:120],
                project=project.title,
                project_id=str(project.id) if project.id is not None else None,
                task_id=str(comment.task_id) if comment.task_id is not None else None,
                is_read=is_read,
                created_at=comment.created_at,
            )
        )

    # ── Task-assignments inbox surface (NEW, Sprint 1.1) ─────────
    # Tareas ABIERTAs asignadas al actor en proyectos visibles. Cierra el
    # feature gap donde instancias donde el email había fallado / no había
    # sido enviado aún así quedaban sin notificar al inbox. La query
    # excluye tareas completadas (estado terminal) y soft-deleted.
    assigned_tasks = ()
    if persona_id:
        q_tasks = (
            db.query(models.ProjectTask, models.Project)
            .join(models.Project, models.Project.id == models.ProjectTask.project_id)
            .options(selectinload(models.Project.owner))
            .filter(
                models.ProjectTask.assignee_id == persona_id,
                models.ProjectTask.deleted_at.is_(None),
                models.ProjectTask.status != "completed",
                # PEND-QUALITY-INBOX-SCOPE-001 (2026-07-16): excluir
                # tareas cuyo proyecto esté soft-deleted para no exponer
                # tareas fantasma en el inbox tras un borrado. La rama de
                # ``task.deleted_at`` ya excluye soft-delete a nivel tarea.
                models.Project.deleted_at.is_(None),
            )
        )
        if user_sede:
            q_tasks = q_tasks.filter(models.Project.sede_id == user_sede)
        assigned_tasks = q_tasks.order_by(models.ProjectTask.updated_at.desc()).limit(limit).all()

    # ── Batch-fetch inbox states for task items (N+1 fix) ──
    task_item_ids = {f"task-{t.id}" for t, _ in assigned_tasks}
    task_inbox_states_map: dict = {}
    if task_item_ids and persona_id:
        task_inbox_states_map = {
            s.item_id: s.is_read
            for s in db.query(models.ProjectInboxState)
            .filter(
                models.ProjectInboxState.persona_id == persona_id,
                models.ProjectInboxState.item_id.in_(task_item_ids),
            )
            .all()
        }

    for task, project in assigned_tasks:
        item_id = f"task-{task.id}"
        is_read = task_inbox_states_map.get(item_id, False)
        project_owner_name = _author_name(project.owner) if project and getattr(project, "owner", None) else "Equipo"
        inbox_items.append(
            schemas.ProjectInboxItem(
                id=item_id,
                type="task_assigned",
                user=project_owner_name,
                content=f"Tarea asignada: {task.title}",
                project=project.title if project else "Proyecto",
                project_id=str(project.id) if project and project.id is not None else None,
                task_id=str(task.id),
                task_title=task.title,
                is_read=is_read,
                created_at=task.updated_at or _utcnow(),
            )
        )

    return inbox_items[:limit]


@router.post("/inbox/{item_id}/read", response_model=dict)
def mark_inbox_read(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Marca un item del inbox como leído.

    PEND-QUALITY-INBOX-SCOPE-001 (2026-07-16): exigir que ``item_id``
    corresponda a una entrada real del inbox del actor antes de
    upsertar ``ProjectInboxState``. Antes este endpoint hacía un upsert
    ciego en ``project_inbox_state`` y cualquier ``item_id`` arbitrario
    quedaba persistido como leído. Ahora se valida:

    * El formato ``comment-<uuid>`` o ``task-<uuid>``.
    * Que la entidad subyacente (comentario no resuelto de otro autor en
      proyecto visible, o tarea abierta asignada al actor en proyecto
      visible) efectivamente exista para ``persona_id`` + ``user_sede``.

    Si no se cumple, responde **404** (existence-leak safe). El upsert
    atómico se mantiene para cubrir el race entre POSTs concurrentes.
    """
    persona = _resolve_persona(db, current_user.id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    user_sede = get_user_sede_id(db, current_user.id)

    # ── Validación de existencia real del item en el inbox del actor ──
    if not _inbox_item_exists_for_actor(db, item_id, persona.id, user_sede):
        raise HTTPException(status_code=404, detail="Inbox item not found")

    # Race-condition fix: replace check-then-act with an atomic upsert.
    # Two concurrent clicks or a duplicate POST would otherwise both see
    # ``state = None`` and either duplicate the row (if no unique
    # constraint) or raise IntegrityError 500 (if there is one). The
    # try/except handles both PostgreSQL and SQLite dialects uniformly.
    try:
        state = models.ProjectInboxState(
            persona_id=persona.id,
            item_id=item_id,
            is_read=True,
        )
        db.add(state)
        db.commit()
    except IntegrityError:
        db.rollback()
        state = (
            db.query(models.ProjectInboxState)
            .filter(
                models.ProjectInboxState.persona_id == persona.id,
                models.ProjectInboxState.item_id == item_id,
            )
            .first()
        )
        if state and not state.is_read:
            state.is_read = True
            db.commit()
    return {"ok": True, "item_id": item_id}


# ── WIKI & WHITEBOARD CON CALIDAD AUDITADA ─────────────────────────
# NOTA: /whiteboards (sin project_id) debe ir ANTES de /{project_id}
# para evitar que FastAPI interprete "whiteboards" como un project_id.


@router.get("/whiteboards", response_model=List[schemas.ProjectWhiteboard])
def list_whiteboards(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Lista todas las pizarras activas del alcance del actor actual.

    Axioma 3 — solo se devuelven pizarras cuyos proyectos pertenezcan a la
    ``sede_id`` del actor. Esto previene el leak cross-sede del feed de
    whiteboards en el módulo de plataforma. El superadmin (``user_sede``
    = ``None``) sigue viendo todas, consistente con list_projects.

    El listado está paginado (``limit``/``offset``, default 200, cap 500)
    para no materializar el feed completo en memoria en sedes grandes.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    q = (
        db.query(models.ProjectWhiteboard)
        .join(models.Project, models.Project.id == models.ProjectWhiteboard.project_id)
        .filter(models.ProjectWhiteboard.deleted_at.is_(None))
    )
    if user_sede:
        q = q.filter(models.Project.sede_id == user_sede)
    boards = q.order_by(models.ProjectWhiteboard.updated_at.desc()).offset(offset).limit(limit).all()
    return [_normalize_dates(b) for b in boards]


# ---------------------------------------------------------------------------
# PROJECT TEMPLATES & CATALOG (Super-PRO Fase 6)
# NOTA: /templates y /from-template deben ir ANTES de /{project_id}
# ---------------------------------------------------------------------------

@router.get(
    "/templates",
    response_model=List[schemas.ProjectTemplate],
    tags=["Projects Templates Super-PRO"],
)
def list_project_templates(
    category: Optional[str] = None,
    search: Optional[str] = None,
    is_public: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista las plantillas disponibles de proyectos aplicando alcance multi-tenant (Axioma 3)."""
    user_sede = get_user_sede_id(db, current_user.id)
    templates = crud.get_project_templates(
        db,
        sede_id=user_sede,
        category=category,
        search=search,
        is_public=is_public,
    )
    for t in templates:
        _normalize_dates(t)
    return templates


@router.post(
    "/templates",
    response_model=schemas.ProjectTemplate,
    status_code=status.HTTP_201_CREATED,
    tags=["Projects Templates Super-PRO"],
)
def create_project_template_endpoint(
    payload: schemas.ProjectTemplateCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Crea una nueva plantilla reutilizable de proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    creator_persona_id = get_user_persona_id(db, current_user.id)
    try:
        template = crud.create_project_template(
            db,
            template_in=payload,
            creator_persona_id=creator_persona_id,
            sede_id=user_sede,
            can_manage_global=_has_role_based_project_access(db, current_user, "manage"),
        )
        _normalize_dates(template)
        return template
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creando plantilla: {str(e)}")


@router.get(
    "/templates/{template_id}",
    response_model=schemas.ProjectTemplate,
    tags=["Projects Templates Super-PRO"],
)
def get_project_template_endpoint(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Obtiene el detalle y estructura de una plantilla de proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    template = crud.get_project_template(db, _to_uuid(template_id), sede_id=user_sede)
    if not template:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    _normalize_dates(template)
    return template


@router.patch(
    "/templates/{template_id}",
    response_model=schemas.ProjectTemplate,
    tags=["Projects Templates Super-PRO"],
)
def update_project_template_endpoint(
    template_id: str,
    payload: schemas.ProjectTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Actualiza los metadatos o estructura de una plantilla."""
    user_sede = get_user_sede_id(db, current_user.id)
    template = crud.update_project_template(
        db,
        template_id=_to_uuid(template_id),
        template_in=payload,
        sede_id=user_sede,
        can_manage_global=_has_role_based_project_access(db, current_user, "manage"),
    )
    if not template:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    _normalize_dates(template)
    return template


@router.delete(
    "/templates/{template_id}",
    tags=["Projects Templates Super-PRO"],
)
def delete_project_template_endpoint(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Elimina (soft-delete) una plantilla de proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    deleted = crud.delete_project_template(
        db,
        _to_uuid(template_id),
        sede_id=user_sede,
        can_manage_global=_has_role_based_project_access(db, current_user, "manage"),
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return {"ok": True, "message": "Plantilla eliminada correctamente"}


@router.post(
    "/from-template/{template_id}",
    response_model=schemas.Project,
    status_code=status.HTTP_201_CREATED,
    tags=["Projects Templates Super-PRO"],
)
@router.post(
    "/templates/{template_id}/instantiate",
    response_model=schemas.Project,
    status_code=status.HTTP_201_CREATED,
    tags=["Projects Templates Super-PRO"],
)
def instantiate_project_from_template_endpoint(
    template_id: str,
    payload: schemas.InstantiateProjectFromTemplate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Instancia atómicamente un nuevo proyecto a partir de una plantilla."""
    user_sede = get_user_sede_id(db, current_user.id)
    if not user_sede:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario autenticado no tiene una sede asignada para instanciar proyectos",
        )

    creator_persona_id = get_user_persona_id(db, current_user.id)
    if not creator_persona_id:
        raise HTTPException(status_code=401, detail="No se pudo determinar la persona autenticada")
    requested_owner_id = payload.owner_id or creator_persona_id
    _assert_assignee_in_sede(db, requested_owner_id, user_sede)

    try:
        project = crud.create_project_from_template(
            db,
            template_id=_to_uuid(template_id),
            payload=payload,
            creator_persona_id=creator_persona_id,
            sede_id=user_sede,
        )
        _normalize_dates(project)
        return project
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al instanciar proyecto: {str(e)}")


@router.post(
    "/{project_id}/save-as-template",
    response_model=schemas.ProjectTemplate,
    status_code=status.HTTP_201_CREATED,
    tags=["Projects Templates Super-PRO"],
)
def save_project_as_template_endpoint(
    project_id: str,
    payload: schemas.SaveProjectAsTemplate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Captura las fases y tareas del proyecto activo para guardarlo como plantilla reutilizable."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    creator_persona_id = get_user_persona_id(db, current_user.id)
    if not creator_persona_id:
        raise HTTPException(status_code=401, detail="No se pudo determinar la persona autenticada")
    try:
        template = crud.save_project_as_template(
            db,
            project_id=_to_uuid(project_id),
            payload=payload,
            creator_persona_id=creator_persona_id,
            sede_id=user_sede,
        )
        _log_project_activity(
            db,
            project_id,
            current_user.id,
            "saved_as_template",
            f"Proyecto guardado como plantilla '{template.name}'",
        )
        _normalize_dates(template)
        return template
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al guardar plantilla: {str(e)}")


@router.get("/{project_id}", response_model=schemas.Project)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("read")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    p = _ensure_project(db, project_id, user_sede=user_sede)
    _prepare_project_for_response(p)
    for log in p.activity_logs:
        _normalize_dates(log)
        log.user_name = log.persona.nombre_completo if log.persona else "Sistema"
    p.budget_summary = crud.get_project_budget_summary(db, p.id)
    p.risks_summary = crud.get_project_risks_summary(db, p.id)
    p.workload_summary = crud.get_project_workload(db, p.id)
    return p


@router.get("/{project_id}/analytics", response_model=schemas.ProjectAnalytics)
def get_project_analytics(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("read")),
):
    """Analítica real del proyecto para la vista maestra.

    Reemplaza las métricas hardcodeadas que antes se renderizaban en
    ``ProjectMasterView`` (Velocidad / Retraso / Riesgo / Salud). Todo se
    deriva del set de tareas persistido del proyecto, dentro de la sede
    del actor (Axioma 3, vía ``_ensure_project``).
    """
    user_sede = get_user_sede_id(db, current_user.id)
    project = _ensure_project(db, project_id, user_sede=user_sede)

    now = datetime.now(timezone.utc)
    tasks = (
        db.query(models.ProjectTask)
        .filter(
            models.ProjectTask.project_id == _to_uuid(project_id),
            models.ProjectTask.deleted_at.is_(None),
        )
        .all()
    )
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == "completed")
    open_statuses = ("todo", "in_progress", "review")
    open_tasks = sum(1 for t in tasks if t.status in open_statuses)
    unassigned_tasks = sum(1 for t in tasks if t.status in open_statuses and not t.assignee_id)

    def _as_aware(dt) -> datetime:
        if dt is None:
            return None
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

    overdue_tasks = 0
    max_overdue_days = 0
    for t in tasks:
        due = _as_aware(t.due_date)
        if t.status in open_statuses and due is not None and due < now:
            overdue_tasks += 1
            max_overdue_days = max(max_overdue_days, max((now - due).days, 0))

    # Velocidad: tareas completadas por día desde la creación del proyecto.
    created = _as_aware(project.created_at) or now
    days_since_creation = max((now - created).days, 1)
    velocity = round(completed_tasks / days_since_creation, 2)

    # Riesgo: bloqueos reales (vencidas > atascadas > saludable).
    if overdue_tasks > 0:
        risk_level = "alto"
        risk_reason = f"{overdue_tasks} tarea(s) vencida(s)"
    elif unassigned_tasks > 0:
        risk_level = "medio"
        risk_reason = f"{unassigned_tasks} tarea(s) sin responsable"
    else:
        risk_level = "bajo"
        risk_reason = "Sin bloqueos"

    # Salud: % de avance penalizado por vencidas y sin responsable.
    completion_pct = round((completed_tasks / max(total_tasks, 1)) * 100) if total_tasks else 0
    health_score = max(completion_pct - min(overdue_tasks * 15, 45) - min(unassigned_tasks * 5, 15), 0)
    if health_score >= 80:
        health_label = "óptima"
    elif health_score >= 60:
        health_label = "buena"
    elif health_score >= 40:
        health_label = "en riesgo"
    else:
        health_label = "crítica"

    return schemas.ProjectAnalytics(
        project_id=str(project.id),
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        open_tasks=open_tasks,
        overdue_tasks=overdue_tasks,
        unassigned_tasks=unassigned_tasks,
        velocity=velocity,
        overdue_days=max_overdue_days,
        risk_level=risk_level,
        risk_reason=risk_reason,
        health_score=health_score,
        health_label=health_label,
    )


@router.get("/{project_id}/wiki", response_model=Optional[schemas.ProjectDocument])
def get_project_wiki(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("read")),
):
    """Obtiene el wiki (ProjectDocument) asociado a un proyecto.

    Axioma 3 — the route previously skipped ``_ensure_project`` and
    leaked cross-sede wikis by guessing project_id. The fix mirrors the
    rest of the module: validate the parent project before returning
    the document.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    doc = db.query(models.ProjectDocument).filter(models.ProjectDocument.project_id == _to_uuid(project_id)).first()
    return _normalize_dates(doc)


@router.post("/{project_id}/wiki", response_model=schemas.ProjectDocument)
def update_project_wiki(
    project_id: str,
    payload: schemas.ProjectDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)  # Validates project exists + scope
    doc = crud.get_project_wiki(db, _to_uuid(project_id))
    title = payload.title or "Wiki Ministerial"
    content = payload.content or ""
    author_persona_id = get_user_persona_id(db, current_user.id)

    if not doc:
        doc = models.ProjectDocument(
            project_id=_to_uuid(project_id),
            title=title,
            content=content,
            author_id=author_persona_id,
        )
        db.add(doc)
    else:
        doc.title = title
        doc.content = content
        doc.author_id = author_persona_id
        doc.last_edited_at = datetime.now(timezone.utc)

    # Registrar cambio en la bitacora
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "wiki_updated",
        "Documentacion Wiki actualizada.",
    )
    db.commit()
    db.refresh(doc)
    return _normalize_dates(doc)


@router.get("/{project_id}/whiteboard", response_model=Optional[schemas.ProjectWhiteboard])
def get_project_whiteboard(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("read")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    board = crud.get_project_whiteboard(db, _to_uuid(project_id))
    return _normalize_dates(board)


@router.post("/{project_id}/whiteboard", response_model=schemas.ProjectWhiteboard)
def update_project_whiteboard(
    project_id: str,
    payload: schemas.ProjectWhiteboardUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    # Busca cualquier fila (incluso soft-deleted): project_id es UNIQUE, así
    # que una pizarra borrada debe restaurarse (deleted_at = NULL) en lugar de
    # dejar un hueco invisible que sigue aceptando 200 sin aparecer en GET.
    board = (
        db.query(models.ProjectWhiteboard)
        .filter(models.ProjectWhiteboard.project_id == _to_uuid(project_id))
        .with_for_update()
        .first()
    )

    if payload.base_updated_at is not None:
        current_updated_at = _whiteboard_utc(board.updated_at) if board and board.updated_at else None
        requested_updated_at = _whiteboard_utc(payload.base_updated_at)
        if (
            board is None
            or board.deleted_at is not None
            or current_updated_at is None
            or requested_updated_at != current_updated_at
        ):
            current_version = current_updated_at.isoformat() if current_updated_at else None
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "detail": {
                        "code": "whiteboard_conflict",
                        "message": "La pizarra cambió desde que la cargaste. Recárgala antes de volver a guardar.",
                        "current_updated_at": current_version,
                    }
                },
            )
    title = payload.title or "Pizarra Estrategica"
    elements = payload.elements_json or "[]"

    # Validate elements_json is valid JSON (reject "undefined", malformed, etc.)
    _validate_whiteboard_json(elements)

    if not board:
        board = models.ProjectWhiteboard(project_id=_to_uuid(project_id), title=title, elements_json=elements)
        db.add(board)
    else:
        board.elements_json = elements
        board.deleted_at = None
        board.updated_at = datetime.now(timezone.utc)

    board.title = title
    if payload.thumbnail_url is not None:
        board.thumbnail_url = payload.thumbnail_url

    db.commit()
    db.refresh(board)
    return _normalize_dates(board)


@router.delete("/{project_id}/whiteboard", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_whiteboard(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Realiza soft delete de la pizarra asociada a un proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    board = (
        db.query(models.ProjectWhiteboard).filter(models.ProjectWhiteboard.project_id == _to_uuid(project_id)).first()
    )
    if board:
        board.deleted_at = datetime.now(timezone.utc)
        board.updated_at = datetime.now(timezone.utc)
        db.commit()
    return None


@router.post("/{project_id}/whiteboard/thumbnail", response_model=dict)
async def upload_project_whiteboard_thumbnail(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Sube el thumbnail de la pizarra.

    El archivo se optimiza automáticamente (WebP re-encoded y resize) por el
    storage service y el URL resultante se persiste en ``thumbnail_url`` para
    que el feed pueda mostrar una vista previa sin transportar el canvas.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)

    content_type = (file.content_type or "").lower()
    if content_type not in ("image/png", "image/jpeg", "image/webp"):
        raise HTTPException(status_code=400, detail="Thumbnail must be a PNG, JPEG or WebP image")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds maximum size")

    board = (
        db.query(models.ProjectWhiteboard)
        .filter(
            models.ProjectWhiteboard.project_id == _to_uuid(project_id),
            models.ProjectWhiteboard.deleted_at.is_(None),
        )
        .first()
    )
    if not board:
        raise HTTPException(status_code=404, detail="Whiteboard not found")

    filename = sanitize_filename(file.filename or "thumbnail.png")
    url = storage_service.save_file(contents, filename, subfolder="projects/whiteboards")
    board.thumbnail_url = url
    db.commit()
    return {"thumbnail_url": url}


@router.websocket("/{project_id}/whiteboard/ws")
async def whiteboard_collab_ws(websocket: WebSocket, project_id: str):
    """WebSocket de colaboración en tiempo real de la pizarra del proyecto.

    Cierra PZ-05/PZ-13 (planpizarra.md): el frontend conectaba a
    ``/api/v1/projects/{id}/whiteboard/ws`` que no existía en el backend
    (404). Este endpoint es el canal real de cursores + sincronización de
    objetos entre pestañas/usuarios.

    Autenticación: ``token`` JWT en query params (mismo contrato que
    ``/messaging/ws/{client_id}``). Valida:
      1. Token presente y decodificable (4001 si falla).
      2. ``sub`` (user ID) no vacío (4001 si falla).
      3. Usuario existe y está activo (4003 si falla).
      4. Proyecto existe, no soft-deleted y en la sede del actor
         (4004 si falla — Axioma 3, existence-leak safe).
      5. Acceso de lectura al proyecto (rol O asignación, 4003 si falla),
         consistente con ``require_project_access("read")``.

    Room por proyecto: ``wb_{project_uuid}`` (UUID canónico normalizado,
    aislada de chat/presencia).
    Protocolo de mensajes (JSON):
      client → server: ``{"type":"join","name":...,"clientId":...}``,
        ``{"type":"cursor","x","y","name"}``,
        ``{"type":"object_modified"|"object_added","objData"}``,
        ``{"type":"object_removed","objId"}``.
      server → room: reenvía el mensaje con ``sender_id`` = clientId del
        emisor para que cada pestaña filtre su propio eco (el frontend
        ignora ``sender_id === clientId`` y los ids en ``ignoreNextUpdateIds``).
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return
    try:
        payload_data = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject = str(payload_data.get("sub") or "")
        if not subject:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    from sqlalchemy.orm import Session as _Session

    from backend.core.database import SessionLocal

    _db: _Session = SessionLocal()
    try:
        _user = _db.query(models.User).filter(models.User.id == subject).first()
        if not _user or not _user.is_active:
            await websocket.close(code=4003, reason="User not found or inactive")
            return

        # Normaliza project_id a UUID ANTES de consultar la BD: _to_uuid
        # devuelve el string crudo si no es un UUID, y comparar un string
        # contra una columna uuid lanzaría un DataError no manejado de
        # PostgreSQL. Un id malformado responde 4004 (indistinguible de
        # "proyecto no existe").
        project_uuid = _to_uuid(project_id)
        if not isinstance(project_uuid, uuid.UUID):
            await websocket.close(code=4004, reason="Project not found")
            return

        user_sede = get_user_sede_id(_db, _user.id)
        project = (
            _db.query(models.Project)
            .filter(
                models.Project.id == project_uuid,
                models.Project.deleted_at.is_(None),
            )
            .first()
        )
        if not project:
            await websocket.close(code=4004, reason="Project not found")
            return
        # Axioma 3 — scope multi-tenant: proyectos sin sede o de otra sede
        # son indistinguibles de "no existe" (404/4004, nunca 403).
        if user_sede is not None:
            if project.sede_id is None or str(project.sede_id) != str(user_sede):
                await websocket.close(code=4004, reason="Project not found")
                return

        # Alinea lectura/escritura con require_project_access: el rol concede
        # el nivel correspondiente y owner/assignee conserva el acceso asignado.
        persona_id = _get_persona_id_for_user(_db, _user.id)
        is_assigned = bool(persona_id and _is_assigned_to_project(_db, project_id, persona_id))
        can_read = _has_role_based_project_access(_db, _user, "read") or is_assigned
        can_write = _has_role_based_project_access(_db, _user, "edit") or is_assigned
        if not can_read:
            await websocket.close(code=4003, reason="Insufficient permissions")
            return
    finally:
        _db.close()

    # Identidad del cliente (por pestaña) para filtrado de eco propio.
    client_id = websocket.query_params.get("clientId") or str(uuid.uuid4())
    # Room canónico por UUID normalizado: evita que la misma pizarra se
    # divida en dos rooms por variantes de casing del path param.
    room = f"wb_{project_uuid}"
    await manager.connect(client_id, websocket, rooms=[room])

    sender_id = client_id
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(message, dict):
                continue
            msg_type = message.get("type")
            if msg_type == "join":
                # La identidad del emisor se fija SOLO con el clientId del
                # query param (el registrado en manager.connect). El cuerpo
                # del join NO puede redefinirlo: el frontend filtra su eco
                # propio con ``sender_id === clientId``, así que permitir un
                # override aquí permitiría suplantar la identidad de otra
                # pestaña y hacer que ignore nuestros updates.
                continue
            if msg_type in ("object_modified", "object_added", "object_removed") and not can_write:
                await websocket.close(code=4003, reason="Insufficient permissions")
                return
            if msg_type in ("cursor", "object_modified", "object_added", "object_removed"):
                out = dict(message)
                out["sender_id"] = sender_id
                await manager.broadcast_event(out, room=room)
    except WebSocketDisconnect:
        await manager.disconnect(client_id)
    except Exception:
        await manager.disconnect(client_id)


# --- ATTACHMENTS & SUPPLIES ---


@router.post("/{project_id}/tasks/{task_id}/attachments", response_model=schemas.ProjectTask)
async def upload_task_attachment(
    project_id: str,
    task_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    task = _ensure_task_in_project(db, project_id, task_id)
    filename = sanitize_filename(file.filename or "file")
    contents = await file.read()

    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds maximum size")

    url = storage_service.save_file(contents, filename, subfolder="projects")

    uploader_persona_id = get_user_persona_id(db, current_user.id)
    attachment = models.ProjectAttachment(
        task_id=_to_uuid(task_id),
        filename=filename,
        file_url=url,
        file_type=file.content_type,
        file_size=len(contents),
        uploader_id=uploader_persona_id,
    )
    db.add(attachment)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "attachment_added",
        f"Archivo '{filename}' adjuntado a '{task.title}'",
    )
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{project_id}/tasks/{task_id}/attachments/{attachment_id}", response_model=dict)
def delete_task_attachment(
    project_id: str,
    task_id: str,
    attachment_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Elimina un archivo adjunto de una tarea (soft delete)."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    attachment = _ensure_attachment_in_task(db, project_id, task_id, attachment_id)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "attachment_deleted",
        f"Archivo '{attachment.filename}' eliminado",
    )
    crud.delete_attachment(db, _to_uuid(attachment_id))
    return {"ok": True, "deleted": attachment_id}


@router.patch("/{project_id}/tasks/{task_id}", response_model=schemas.ProjectTask)
def update_project_task(
    project_id: str,
    task_id: str,
    payload: schemas.ProjectTaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Actualiza una tarea con auditoría ministerial automática."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    task = _ensure_task_in_project(db, project_id, task_id)
    update_data = payload.model_dump(exclude_unset=True)
    _normalize_task_payload(update_data)
    if "status" in update_data:
        _assert_status_in_project_phases(db, project_id, update_data["status"])
    # Validate that the new assignee (if any) belongs to the actor's sede.
    # Without this, an actor in sede A could inject a persona UUID from sede B
    # via PATCH body {} and assign tasks across tenant boundaries.
    if "assignee_id" in update_data:
        _assert_assignee_in_sede(db, update_data.get("assignee_id"), user_sede)

    effective_status = update_data.get("status", task.status)
    effective_node = update_data.get("node", getattr(task, "node", None))
    effective_start = update_data.get("start_date", task.start_date)
    effective_due = update_data.get("due_date", task.due_date)
    try:
        crud.validate_task_dates_within_phase(
            db,
            project_id,
            status_slug=effective_status,
            node=effective_node,
            start_date=effective_start,
            due_date=effective_due,
            task_id=task.id,
        )
    except (crud.TaskDateOutOfBoundsError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    previous_assignee_id = getattr(task, "assignee_id", None)
    changed_fields = []

    for key, value in update_data.items():
        old_value = getattr(task, key, None)
        setattr(task, key, value)
        if old_value != value:
            changed_fields.append(key)

    _normalize_task_enums(task)
    if changed_fields:
        _log_project_activity(
            db,
            project_id,
            current_user.id,
            "task_updated",
            f"Tarea '{task.title}' actualizada: {', '.join(changed_fields)}",
        )
    db.commit()
    db.refresh(task)
    if (
        "assignee_id" in update_data
        and _assignment_changed(previous_assignee_id, getattr(task, "assignee_id", None))
        and task.assignee_id
    ):
        notify_task_assigned(
            db,
            task=task,
            assigned_by_user_id=current_user.id,
            previous_assignee_id=previous_assignee_id,
        )
    return task


@router.get("/{project_id}/tasks/{task_id}/supplies", response_model=List[schemas.TaskSupply])
def list_task_supplies(
    project_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("read")),
):
    """Lista los insumos de una tarea."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    _ensure_task_in_project(db, project_id, task_id)
    return crud.get_task_supplies(db, _to_uuid(task_id))


@router.post(
    "/{project_id}/tasks/{task_id}/supplies",
    response_model=schemas.TaskSupply,
    status_code=status.HTTP_201_CREATED,
)
def create_task_supply(
    project_id: str,
    task_id: str,
    payload: schemas.TaskSupplyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Crea un insumo requerido para una tarea."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    task = _ensure_task_in_project(db, project_id, task_id)
    supply = models.TaskSupply(task_id=_to_uuid(task_id), **payload.model_dump())
    db.add(supply)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "supply_added",
        f"Insumo '{supply.item_name}' agregado a '{task.title}'",
    )
    db.commit()
    db.refresh(supply)
    return supply


@router.patch(
    "/{project_id}/tasks/{task_id}/supplies/{supply_id}",
    response_model=schemas.TaskSupply,
)
def update_task_supply(
    project_id: str,
    task_id: str,
    supply_id: str,
    payload: schemas.TaskSupplyUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Actualiza nombre, cantidad o estado de un insumo."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    task = _ensure_task_in_project(db, project_id, task_id)
    supply = _ensure_supply_in_task(db, project_id, task_id, supply_id)
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(supply, key, value)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "supply_updated",
        f"Insumo '{supply.item_name}' actualizado en '{task.title}'",
    )
    db.commit()
    db.refresh(supply)
    return supply


@router.delete("/{project_id}/tasks/{task_id}/supplies/{supply_id}", response_model=dict)
def delete_task_supply(
    project_id: str,
    task_id: str,
    supply_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Elimina un insumo de una tarea."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    task = _ensure_task_in_project(db, project_id, task_id)
    supply = _ensure_supply_in_task(db, project_id, task_id, supply_id)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "supply_deleted",
        f"Insumo '{supply.item_name}' eliminado de '{task.title}'",
    )
    crud.delete_supply(db, supply_id)
    return {"ok": True, "deleted": supply_id}


# ── SUBTASKS ───────────────────────────────────────────────────────────────────


@router.post(
    "/{project_id}/tasks/{task_id}/subtasks",
    response_model=schemas.ProjectTask,
    status_code=status.HTTP_201_CREATED,
)
def create_subtask(
    project_id: str,
    task_id: str,
    subtask: schemas.ProjectTaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Crea una subtarea (nivel 2 o 3) bajo una tarea existente."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    parent_task = _ensure_task_in_project(db, project_id, task_id)
    # Race-condition fix: lock the parent project row before reading the
    # MAX(order_index) so concurrent subtask creations do not share the
    # same order_index slot.
    db.query(models.Project).filter(models.Project.id == _to_uuid(project_id)).with_for_update().first()
    payload = subtask.model_dump()
    _normalize_task_payload(payload)
    _assert_status_in_project_phases(db, project_id, payload.get("status"))
    _assert_assignee_in_sede(db, payload.get("assignee_id"), user_sede)
    max_order = (
        db.query(func.max(models.ProjectTask.order_index)).filter(models.ProjectTask.parent_id == task_id).scalar() or 0
    )
    # FIX: Previously these were assigned as raw strings (``project_id`` is
    # declared as ``str`` from the route path). ``ProjectTask.project_id``
    # is a ``UUID(as_uuid=True)`` column — assigning a string breaks SQLite
    # (see ``tests/test_projects_api.py::TestTasks::test_create_task_with_uuid_assignee``
    # and the parametrized regression suite). Coerce via ``_to_uuid``.
    payload["project_id"] = _to_uuid(project_id)
    payload["parent_id"] = _to_uuid(task_id)
    payload["order_index"] = max_order + 1
    db_subtask = models.ProjectTask(**payload)
    db.add(db_subtask)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "subtask_created",
        f"Sub-actividad '{db_subtask.title}' creada bajo '{parent_task.title}'",
    )
    db.commit()
    db.refresh(db_subtask)
    if getattr(db_subtask, "assignee_id", None):
        notify_task_assigned(
            db,
            task=db_subtask,
            assigned_by_user_id=current_user.id,
            previous_assignee_id=None,
        )
    return db_subtask


@router.patch(
    "/{project_id}/tasks/{task_id}/subtasks/{subtask_id}",
    response_model=schemas.ProjectTask,
)
def update_subtask(
    project_id: str,
    task_id: str,
    subtask_id: str,
    payload: schemas.ProjectTaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Actualiza una subtarea."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    _ensure_task_in_project(db, project_id, task_id)
    subtask = _ensure_task_in_project(db, project_id, subtask_id)
    if str(subtask.parent_id) != str(task_id):
        raise HTTPException(status_code=404, detail="Subtask not found under task")
    update_data = payload.model_dump(exclude_unset=True)
    _normalize_task_payload(update_data)
    if "status" in update_data:
        _assert_status_in_project_phases(db, project_id, update_data["status"])
    if "assignee_id" in update_data:
        _assert_assignee_in_sede(db, update_data["assignee_id"], user_sede)
    previous_assignee_id = getattr(subtask, "assignee_id", None)
    for key, value in update_data.items():
        setattr(subtask, key, value)
    _normalize_task_enums(subtask)
    db.commit()
    db.refresh(subtask)
    if (
        "assignee_id" in update_data
        and _assignment_changed(previous_assignee_id, getattr(subtask, "assignee_id", None))
        and subtask.assignee_id
    ):
        notify_task_assigned(
            db,
            task=subtask,
            assigned_by_user_id=current_user.id,
            previous_assignee_id=previous_assignee_id,
        )
    return subtask


@router.delete("/{project_id}/tasks/{task_id}/subtasks/{subtask_id}")
def delete_subtask(
    project_id: str,
    task_id: str,
    subtask_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Elimina una subtarea."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    _ensure_task_in_project(db, project_id, task_id)
    subtask = _ensure_task_in_project(db, project_id, subtask_id)
    if str(subtask.parent_id) != str(task_id):
        raise HTTPException(status_code=404, detail="Subtask not found under task")
    subtask.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "deleted": subtask_id}


# ── COMMENTS ──────────────────────────────────────────────────────────────────


@router.post("/comments", response_model=schemas.ProjectCommentItem)
def create_comment(
    payload: schemas.ProjectCommentCreateWithProject,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Crea un comentario usando project_id en el body."""
    project_id = payload.project_id
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    task_id = payload.task_id
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    if task_id:
        _ensure_task_in_project(db, project_id, task_id)
    author_persona_id = get_user_persona_id(db, current_user.id)
    resolved_mentions = resolve_mentions(
        db,
        content=content,
        payload_mentions=payload.mentions or [],
        author_id=author_persona_id,
        user_sede=user_sede,
    )
    comment = models.ProjectComment(
        project_id=_to_uuid(project_id),
        task_id=_to_uuid(task_id) if task_id else None,
        author_id=author_persona_id,
        content=content,
        attachments=[a.model_dump() for a in (payload.attachments or [])],
        mentions=[str(mention_id) for mention_id in resolved_mentions],
    )
    db.add(comment)
    _notify_comment_mentions(db, comment, project_id, task_id, user_sede)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "comment_added",
        content,
    )
    db.commit()
    db.refresh(comment)
    persona = (
        db.query(models.Persona).filter(models.Persona.id == comment.author_id).first() if comment.author_id else None
    )
    return _project_comment_to_schema(comment, persona)


@router.post("/{project_id}/comments", response_model=schemas.ProjectCommentItem)
def create_project_comment(
    project_id: str,
    payload: schemas.ProjectCommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Crea un comentario en un proyecto.

    Usa ``require_project_access("edit")`` (no ``require_module_access``) para
    que un miembro asignado al proyecto (owner o assignee de una tarea) pueda
    comentar sin necesidad de un rol de plataforma con ``projects:edit``.
    Consistente con ``create_project_task`` que también usa assignment-based.
    El scope Axioma 3 se valida dentro de ``_ensure_project``.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    if payload.task_id:
        _ensure_task_in_project(db, project_id, payload.task_id)
    author_persona_id = get_user_persona_id(db, current_user.id)
    resolved_mentions = resolve_mentions(
        db,
        content=payload.content,
        payload_mentions=payload.mentions or [],
        author_id=author_persona_id,
        user_sede=user_sede,
    )
    comment = models.ProjectComment(
        project_id=_to_uuid(project_id),
        task_id=_to_uuid(payload.task_id) if payload.task_id else None,
        author_id=author_persona_id,
        content=payload.content,
        attachments=[a.model_dump() for a in (payload.attachments or [])],
        mentions=[str(mention_id) for mention_id in resolved_mentions],
    )
    db.add(comment)
    _notify_comment_mentions(db, comment, project_id, payload.task_id, user_sede)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "comment_added",
        payload.content,
    )
    db.commit()
    db.refresh(comment)
    persona = (
        db.query(models.Persona).filter(models.Persona.id == comment.author_id).first() if comment.author_id else None
    )
    return _project_comment_to_schema(comment, persona)


@router.patch("/comments/{comment_id}", response_model=schemas.ProjectCommentItem)
def update_project_comment(
    comment_id: str,
    payload: schemas.ProjectCommentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Actualiza un comentario (contenido o estado de resolución)."""
    comment = db.query(models.ProjectComment).filter(models.ProjectComment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    # IDOR fix + Axioma 3: validate that the actor's sede matches the comment's
    # parent project. Without this a sede_a user could mutate a comment in a
    # sede_b project by guessing the comment_id and calling PATCH/DELETE.
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, str(comment.project_id), user_sede=user_sede)
    if payload.content is not None:
        comment.content = payload.content
    if payload.is_resolved is not None:
        comment.is_resolved = payload.is_resolved
    if payload.attachments is not None:
        comment.attachments = [a.model_dump() for a in payload.attachments]
    # Re-extract mentions from the updated content and merge with any
    # explicit payload mentions so hand-written @mentions stay in sync.
    previous_mentions = {str(m) for m in (comment.mentions or [])}
    if payload.mentions is not None or payload.content is not None:
        comment.mentions = resolve_mentions(
            db,
            content=comment.content,
            payload_mentions=payload.mentions or [],
            author_id=comment.author_id,
            user_sede=user_sede,
        )
    db.commit()
    db.refresh(comment)
    # Notify only newly added mentions after an edit to avoid spamming
    # users who were already mentioned in the original comment.
    new_mentions = {str(m) for m in (comment.mentions or [])}
    added_mentions = new_mentions - previous_mentions
    if added_mentions:
        added_uuids = [_to_uuid(m) for m in added_mentions]
        comment.mentions = added_uuids
        _notify_comment_mentions(
            db, comment, str(comment.project_id), str(comment.task_id) if comment.task_id else None, user_sede
        )
        comment.mentions = [_to_uuid(m) for m in new_mentions]
        db.commit()
    author = db.query(models.Persona).filter(models.Persona.id == comment.author_id).first()
    return _project_comment_to_schema(comment, author)


# ── TASK LIST PER PROJECT ──────────────────────────────────────────────────────


@router.get("/{project_id}/tasks", response_model=List[schemas.ProjectTask])
def list_project_tasks(
    project_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista todas las tareas de un proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    q = (
        db.query(models.ProjectTask)
        .options(
            selectinload(models.ProjectTask.attachments),
            selectinload(models.ProjectTask.supplies),
            selectinload(models.ProjectTask.subtasks),
        )
        .filter(models.ProjectTask.project_id == _to_uuid(project_id), models.ProjectTask.deleted_at.is_(None))
    )

    if status_filter:
        q = q.filter(models.ProjectTask.status == status_filter)

    tasks = q.order_by(models.ProjectTask.order_index.asc()).all()

    for t in tasks:
        _prepare_task_for_response(t)

    return tasks


# ── PROJECT UPDATE & DELETE ────────────────────────────────────────────────────


@router.patch("/{project_id}", response_model=schemas.Project)
def update_project(
    project_id: str,
    payload: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Actualiza los metadatos de un proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    project = _ensure_project(db, project_id, user_sede=user_sede)
    update_data = payload.model_dump(exclude_unset=True)
    if "owner_id" in update_data:
        _assert_assignee_in_sede(db, update_data["owner_id"], user_sede)
    changed_fields = []
    for key, value in update_data.items():
        old_value = getattr(project, key, None)
        setattr(project, key, value)
        if old_value != value:
            changed_fields.append(key)
    project.updated_at = _utcnow()
    if changed_fields:
        _log_project_activity(
            db,
            project_id,
            current_user.id,
            "project_updated",
            f"Proyecto '{project.title}' actualizado: {', '.join(changed_fields)}",
        )
    db.commit()
    db.refresh(project)
    _normalize_dates(project)
    return project


@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    """Marca el proyecto como eliminado sin purgar físicamente sus relaciones.

    Solo se actualiza ``Project.deleted_at``; tareas, hitos y demás registros
    relacionados se conservan en la base de datos y dejan de estar disponibles
    en las consultas activas que primero validan el proyecto.

    **Política confirmada** (``PEND-QUALITY-RBAC-ASYM-001`` — cierre
    2026-07-16): ``DELETE /projects/{id}`` requiere ``academy:manage``
    v\u00eda ``require_staff_or_admin``, NO ``projects:edit`` como su primo
    ``PATCH /projects/{id}``. La asimetr\u00eda se mantiene como pol\u00edtica
    deliberada porque la retirada de un proyecto afecta la disponibilidad
    operacional de tareas, hitos, wiki, pizarra, comentarios y bit\u00e1cora
    ministerial — es una operaci\u00f3n de alcance de m\u00f3dulo, no de proyecto.

    * Editor (con ``projects:edit``) pasa ``PATCH`` pero recibe **403** en
      ``DELETE``.  Esto queda congelado por
      ``tests/test_projects_rbac.py::test_delete_project_requires_academy_manage_per_policy``.
    * Gestor / Admin pasan ambas rutas.

    Si en el futuro se decide alinear ``DELETE`` con la matriz
    ``projects:*``, este docstring y ``PROJECTS_RBAC_MATRIX.md \u00a76``
    deben actualizarse, y el test arriba debe ajustarse.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    project = _ensure_project(db, project_id, user_sede=user_sede)
    project.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "deleted": project_id}


@router.delete("/{project_id}/tasks/{task_id}")
def delete_project_task(
    project_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Elimina una tarea de un proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    task = _ensure_task_in_project(db, project_id, task_id)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "task_deleted",
        f"Tarea '{task.title}' eliminada",
    )
    task.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "deleted": task_id}


@router.delete("/comments/{comment_id}")
def delete_project_comment(
    comment_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Elimina un comentario."""
    comment = db.query(models.ProjectComment).filter(models.ProjectComment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    # IDOR fix + Axioma 3 (mirror of update_project_comment): the actor
    # must own the sede that owns the comment's parent project.
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, str(comment.project_id), user_sede=user_sede)
    comment.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "deleted": comment_id}


# ── PROJECT CHAT ─────────────────────────────────────────────────────


@router.get("/{project_id}/messages", response_model=List[schemas.ProjectMessageItem])
def list_project_messages(
    project_id: str,
    limit: int = Query(50, le=200),
    before: Optional[int] = Query(None, alias="before"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """List project chat messages, newest first, with cursor pagination.

    Axioma 3 — the actor's ``sede_id`` is validated through
    ``_ensure_project`` (with ``user_sede`` filter); if the project does
    not belong to the actor's sede the response is exactly 404 — no
    existence leak.

    Soft-delete filter — contract: ``deleted_at IS NOT NULL`` messages
    are *excluded* from the listing (audit only), keeping the DB row
    intact for the parallel
    ``TestChatDeletePermissions::test_soft_deleted_message_kept_in_db_for_audit``
    contract. Hard-delete is reserved to admin forensics tooling, never
    via this endpoint.

    Cursor pagination — ``before`` is the **integer representation** of
    the cursor UUID (the client's ``uuid.UUID(...).int`` form). The DB
    column stores UUIDs as 32-char hex strings (SQLite) or native UUID
    (Postgres). We must NOT pass the raw ``int`` to SQLAlchemy because
    SQLite raises ``OverflowError: Python int too large to convert to
    SQLite INTEGER`` (UUID.int ≈ 10^38 > INT64 max ≈ 9.2e18). So we
    rebuild the UUID from the int and compare against its hex form (or
    canonical string in Postgres). Falls back to UUID string parsing if
    ``before`` is passed as a canonical UUID string (forward compat).
    Malformed cursors no-op rather than 422 — pagination is best-effort.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    room = f"project_{project_id}"
    q = db.query(models.ChatMessage).filter(
        models.ChatMessage.room_id == room,
        models.ChatMessage.deleted_at.is_(None),
    )
    if before is not None:
        cursor_hex: Optional[str] = None
        try:
            # Primary path: client sends ``cursor.int`` — the integer of
            # a UUID. SQLite-bound int comparison would overflow, so we
            # reconstruct the UUID and compare by hex string instead.
            cursor_uuid = uuid.UUID(int=int(before))
            cursor_hex = cursor_uuid.hex
        except (TypeError, ValueError, OverflowError):
            try:
                # Forward-compat: someone passed a canonical UUID string.
                cursor_uuid = uuid.UUID(str(before))
                cursor_hex = cursor_uuid.hex
            except (TypeError, ValueError, AttributeError):
                # Malformed cursor — best-effort: skip the filter rather
                # than fail the request. Pagination clients retry on stale
                # cursor with the latest ID anyway.
                cursor_hex = None
        if cursor_hex:
            q = q.filter(models.ChatMessage.id < uuid.UUID(cursor_hex))
    rows = q.order_by(models.ChatMessage.created_at.desc()).limit(limit).all()
    sender_ids = {r.sender_id for r in rows}
    users_map = {}
    if sender_ids:
        personas = db.query(models.Persona).filter(models.Persona.id.in_(sender_ids)).all()
        users_map = {p.id: _author_name(p) for p in personas}
    return [
        schemas.ProjectMessageItem(
            id=r.id,
            sender_id=str(r.sender_id),
            sender_name=users_map.get(r.sender_id, "Usuario"),
            content=r.content,
            created_at=r.created_at,
            is_read=r.is_read,
        )
        for r in rows
    ]


@router.post(
    "/{project_id}/messages",
    response_model=schemas.ProjectMessageItem,
    status_code=status.HTTP_201_CREATED,
)
def send_project_message(
    project_id: str,
    payload: schemas.ProjectMessageCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Send a message to the project chat room."""
    user_sede = get_user_sede_id(db, current_user.id)
    project = _ensure_project(db, project_id, user_sede=user_sede)
    persona = _resolve_persona(db, current_user.id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    msg = models.ChatMessage(
        sender_id=persona.id,
        room_id=f"project_{project_id}",
        content=payload.content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    # Starlette executes async background tasks on the ASGI event loop after
    # sending the response. Calling get_event_loop() here is unsafe because
    # synchronous endpoints run in worker threads and JSON encoding also
    # rejects raw UUID objects.
    background_tasks.add_task(
        manager.broadcast_event,
        {
            "event": "project_message",
            "project_id": str(project.id),
            "message": {
                "id": str(msg.id),
                "sender_id": str(msg.sender_id),
                "sender_name": _author_name(persona),
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "is_read": False,
            },
        },
        room=f"project_{project.id}",
    )

    return schemas.ProjectMessageItem(
        id=msg.id,
        sender_id=str(msg.sender_id),
        sender_name=_author_name(persona),
        content=msg.content,
        created_at=msg.created_at,
    )


@router.delete("/{project_id}/messages/{message_id}")
def delete_project_message(
    project_id: str,
    message_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Delete a chat message (own message or admin).

    IDOR fix + Axioma 3: validate that ``msg.room_id == project_{project_id}``
    before any role check so a sede_a user cannot delete messages stored
    under ``project_b`` by guessing message_ids. Without this the helper
    would happily return 200 on cross-project ids.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    msg = db.query(models.ChatMessage).filter(models.ChatMessage.id == message_id).first()
    if not msg:
        raise HTTPException(404, detail="Message not found")
    if str(msg.room_id) != f"project_{project_id}":
        # Existence-leak safe rejection: the message is real but it doesn't
        # belong to the project in the URL path. 404, not 403.
        raise HTTPException(404, detail="Message not found in this project")
    if msg.sender_id != current_user.id:
        role = normalize_role(getattr(current_user, "role", ""))
        if not role and hasattr(current_user, "rol_plataforma") and current_user.rol_plataforma:
            role = normalize_role(current_user.rol_plataforma.nombre)
        if role not in ("admin", "pastor", "coordinador"):
            raise HTTPException(403, detail="Cannot delete another user's message")
    msg.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


# ── MILESTONES ─────────────────────────────────────────────────────────────────


@router.get("/{project_id}/milestones", response_model=List[schemas.ProjectMilestone])
def list_project_milestones(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista los hitos de un proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    milestones = crud.get_project_milestones(db, _to_uuid(project_id))
    for m in milestones:
        _normalize_dates(m)
    return milestones


@router.post(
    "/{project_id}/milestones",
    response_model=schemas.ProjectMilestone,
    status_code=status.HTTP_201_CREATED,
)
def create_project_milestone(
    project_id: str,
    payload: schemas.ProjectMilestoneBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Crea un hito en un proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    milestone = _projects_create_milestone(
        db,
        _to_uuid(project_id),
        title=payload.title,
        description=payload.description,
        target_date=payload.target_date,
        is_completed=payload.is_completed or False,
    )
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "milestone_created",
        f"Hito '{milestone.title}' creado",
    )
    db.commit()
    _normalize_dates(milestone)
    return milestone


@router.delete("/{project_id}/milestones/{milestone_id}", response_model=dict)
def delete_project_milestone(
    project_id: str,
    milestone_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Elimina un hito de un proyecto (soft delete)."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    milestone = _ensure_milestone_in_project(db, project_id, milestone_id)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "milestone_deleted",
        f"Hito '{milestone.title}' eliminado",
    )
    _projects_delete_milestone(db, _to_uuid(milestone_id))
    return {"ok": True, "deleted": milestone_id}


@router.patch("/{project_id}/milestones/{milestone_id}", response_model=schemas.ProjectMilestone)
def update_project_milestone(
    project_id: str,
    milestone_id: str,
    payload: schemas.ProjectMilestoneUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Actualiza un hito y registra cambios relevantes en la bitacora."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    milestone = _ensure_milestone_in_project(db, project_id, milestone_id)
    previous_completed = milestone.is_completed
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(milestone, key, value)

    if "is_completed" in update_data and milestone.is_completed != previous_completed:
        action_type = "milestone_completed" if milestone.is_completed else "milestone_reopened"
        description = (
            f"Hito '{milestone.title}' completado" if milestone.is_completed else f"Hito '{milestone.title}' reabierto"
        )
    else:
        action_type = "milestone_updated"
        description = f"Hito '{milestone.title}' actualizado"

    _log_project_activity(
        db,
        project_id,
        current_user.id,
        action_type,
        description,
    )
    db.commit()
    db.refresh(milestone)
    _normalize_dates(milestone)
    return milestone


# ── KPIS (PROYECTOS PRO) ───────────────────────────────────────────────────────


@router.get(
    "/{project_id}/kpis",
    response_model=List[schemas.ProjectKPI],
    tags=["Projects PRO"],
)
def list_project_kpis(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista los indicadores clave de desempeño (KPIs) del proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    kpis = crud.get_project_kpis(db, _to_uuid(project_id))
    for k in kpis:
        _normalize_dates(k)
    return kpis


@router.post(
    "/{project_id}/kpis",
    response_model=schemas.ProjectKPI,
    status_code=status.HTTP_201_CREATED,
    tags=["Projects PRO"],
)
def create_project_kpi(
    project_id: str,
    payload: schemas.ProjectKPICreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Crea un nuevo indicador o meta personalizada para el proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    kpi = crud.create_project_kpi(db, _to_uuid(project_id), payload)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "kpi_created",
        f"Indicador '{kpi.title}' creado (Meta: {kpi.target_value} {kpi.unit})",
    )
    db.commit()
    _normalize_dates(kpi)
    return kpi


@router.patch(
    "/{project_id}/kpis/{kpi_id}",
    response_model=schemas.ProjectKPI,
    tags=["Projects PRO"],
)
def update_project_kpi(
    project_id: str,
    kpi_id: str,
    payload: schemas.ProjectKPIUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Actualiza el avance o metadatos de un indicador."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    kpi = crud.get_project_kpi(db, _to_uuid(project_id), _to_uuid(kpi_id))
    if not kpi:
        raise HTTPException(status_code=404, detail="Indicador no encontrado")
    prev_val = kpi.current_value
    updated_kpi = crud.update_project_kpi(db, _to_uuid(project_id), _to_uuid(kpi_id), payload)
    if payload.current_value is not None and payload.current_value != prev_val:
        _log_project_activity(
            db,
            project_id,
            current_user.id,
            "kpi_progress",
            f"Indicador '{kpi.title}' actualizado a {payload.current_value} / {kpi.target_value} {kpi.unit}",
        )
        db.commit()
    _normalize_dates(updated_kpi)
    return updated_kpi


@router.delete(
    "/{project_id}/kpis/{kpi_id}",
    response_model=dict,
    tags=["Projects PRO"],
)
def delete_project_kpi(
    project_id: str,
    kpi_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Elimina un indicador mediante soft delete."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    kpi = crud.get_project_kpi(db, _to_uuid(project_id), _to_uuid(kpi_id))
    if not kpi:
        raise HTTPException(status_code=404, detail="Indicador no encontrado")
    crud.delete_project_kpi(db, _to_uuid(project_id), _to_uuid(kpi_id))
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "kpi_deleted",
        f"Indicador '{kpi.title}' eliminado",
    )
    db.commit()
    return {"ok": True, "deleted": kpi_id}


# ── DEPENDENCIES (GANTT PRO) ───────────────────────────────────────────────────


@router.get(
    "/{project_id}/dependencies",
    response_model=List[schemas.ProjectTaskDependency],
    tags=["Projects PRO"],
)
def list_task_dependencies(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista las dependencias entre tareas para la vista Gantt PRO."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    deps = crud.get_task_dependencies(db, _to_uuid(project_id))
    for d in deps:
        _normalize_dates(d)
    return deps


@router.post(
    "/{project_id}/dependencies",
    response_model=schemas.ProjectTaskDependency,
    status_code=status.HTTP_201_CREATED,
    tags=["Projects PRO"],
)
def create_task_dependency(
    project_id: str,
    payload: schemas.ProjectTaskDependencyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Crea una dependencia (FS, SS, FF) entre dos tareas."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    if str(payload.predecessor_id) == str(payload.successor_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Una tarea no puede depender de sí misma (ciclo detectado)",
        )
    _ensure_task_in_project(db, project_id, str(payload.predecessor_id))
    _ensure_task_in_project(db, project_id, str(payload.successor_id))
    try:
        dep = crud.create_task_dependency(db, _to_uuid(project_id), payload)
    except crud.CircularDependencyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        msg = str(exc)
        if "circular" in msg.lower() or "ciclo" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=msg,
            ) from exc
        # Defensa adicional ante cambios concurrentes entre la validación y el insert.
        raise HTTPException(status_code=404, detail="Dependency tasks not found in project") from exc
    _normalize_dates(dep)
    return dep


@router.delete(
    "/{project_id}/dependencies/{dependency_id}",
    response_model=dict,
    tags=["Projects PRO"],
)
def delete_task_dependency(
    project_id: str,
    dependency_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Elimina una dependencia entre tareas."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    ok = crud.delete_task_dependency(db, _to_uuid(project_id), _to_uuid(dependency_id))
    if not ok:
        raise HTTPException(status_code=404, detail="Dependencia no encontrada")
    return {"ok": True, "deleted": dependency_id}


# ── EXPENSES & BUDGET (SUPER-PRO FASE 1) ───────────────────────────────────────


@router.get(
    "/{project_id}/expenses",
    response_model=List[schemas.ProjectExpense],
    tags=["Projects Super-PRO"],
)
def list_project_expenses(
    project_id: str,
    status: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista las partidas de gastos de un proyecto con filtros opcionales."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    expenses = crud.get_project_expenses(db, _to_uuid(project_id), status=status, category=category)
    for exp in expenses:
        _normalize_dates(exp)
    return expenses


@router.post(
    "/{project_id}/expenses",
    response_model=schemas.ProjectExpense,
    status_code=status.HTTP_201_CREATED,
    tags=["Projects Super-PRO"],
)
def create_project_expense(
    project_id: str,
    payload: schemas.ProjectExpenseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Crea una partida de gasto y recalcula el presupuesto gastado."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    persona_id = get_user_persona_id(db, current_user.id)
    expense = crud.create_project_expense(
        db,
        project_id=_to_uuid(project_id),
        expense_in=payload,
        created_by=_to_uuid(persona_id) if persona_id else None,
    )
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "expense_created",
        f"Gasto registrado: ${payload.amount:.2f} en '{payload.category}' ({payload.description or 'Sin descripción'})",
    )
    db.commit()
    _normalize_dates(expense)
    return expense


@router.get(
    "/{project_id}/expenses/{expense_id}",
    response_model=schemas.ProjectExpense,
    tags=["Projects Super-PRO"],
)
def get_project_expense(
    project_id: str,
    expense_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Obtiene el detalle de un gasto específico."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    expense = crud.get_project_expense(db, _to_uuid(project_id), _to_uuid(expense_id))
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    _normalize_dates(expense)
    return expense


@router.patch(
    "/{project_id}/expenses/{expense_id}",
    response_model=schemas.ProjectExpense,
    tags=["Projects Super-PRO"],
)
def update_project_expense(
    project_id: str,
    expense_id: str,
    payload: schemas.ProjectExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Actualiza una partida de gasto y recalcula el presupuesto del proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    expense = crud.update_project_expense(
        db,
        project_id=_to_uuid(project_id),
        expense_id=_to_uuid(expense_id),
        expense_in=payload,
    )
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "expense_updated",
        f"Gasto '{expense.id}' actualizado",
    )
    db.commit()
    _normalize_dates(expense)
    return expense


@router.delete(
    "/{project_id}/expenses/{expense_id}",
    response_model=dict,
    tags=["Projects Super-PRO"],
)
def delete_project_expense(
    project_id: str,
    expense_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Elimina (soft-delete) una partida de gasto y recalcula el presupuesto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    ok = crud.delete_project_expense(db, _to_uuid(project_id), _to_uuid(expense_id))
    if not ok:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "expense_deleted",
        f"Gasto '{expense_id}' eliminado",
    )
    db.commit()
    return {"ok": True, "deleted": expense_id}


@router.get(
    "/{project_id}/budget-summary",
    response_model=schemas.ProjectBudgetSummary,
    tags=["Projects Super-PRO"],
)
def get_project_budget_summary(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Obtiene el resumen financiero y de quema presupuestaria del proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    summary = crud.get_project_budget_summary(db, _to_uuid(project_id))
    if not summary:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return summary


# ── RISKS / RAID MATRIX (Super-PRO Fase 2) ───────────────────────────────────


@router.get(
    "/{project_id}/risks",
    response_model=List[schemas.ProjectRisk],
    tags=["Projects Super-PRO"],
)
def list_project_risks(
    project_id: str,
    status: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista todos los riesgos registrados de la matriz RAID del proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    risks = crud.get_project_risks(
        db, _to_uuid(project_id), status=status, category=category
    )
    for r in risks:
        _normalize_dates(r)
    return risks


@router.post(
    "/{project_id}/risks",
    response_model=schemas.ProjectRisk,
    status_code=status.HTTP_201_CREATED,
    tags=["Projects Super-PRO"],
)
def create_project_risk(
    project_id: str,
    payload: schemas.ProjectRiskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Registra un nuevo riesgo en la matriz RAID del proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    project = _ensure_project(db, project_id, user_sede=user_sede)
    _assert_assignee_in_sede(db, payload.owner_id, project.sede_id)
    risk = crud.create_project_risk(
        db,
        project_id=_to_uuid(project_id),
        risk_in=payload,
    )
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "risk_created",
        f"Riesgo registrado: '{payload.title}' (Severidad: {payload.probability * payload.impact}/25, Categoría: {payload.category})",
    )
    db.commit()
    _normalize_dates(risk)
    return risk


@router.get(
    "/{project_id}/risks/{risk_id}",
    response_model=schemas.ProjectRisk,
    tags=["Projects Super-PRO"],
)
def get_project_risk(
    project_id: str,
    risk_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Obtiene el detalle de un riesgo específico."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    risk = crud.get_project_risk(db, _to_uuid(project_id), _to_uuid(risk_id))
    if not risk:
        raise HTTPException(status_code=404, detail="Riesgo no encontrado")
    _normalize_dates(risk)
    return risk


@router.patch(
    "/{project_id}/risks/{risk_id}",
    response_model=schemas.ProjectRisk,
    tags=["Projects Super-PRO"],
)
def update_project_risk(
    project_id: str,
    risk_id: str,
    payload: schemas.ProjectRiskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Actualiza la probabilidad, impacto, estado o planes de mitigación de un riesgo."""
    user_sede = get_user_sede_id(db, current_user.id)
    project = _ensure_project(db, project_id, user_sede=user_sede)
    _assert_assignee_in_sede(db, payload.owner_id, project.sede_id)
    risk = crud.update_project_risk(
        db,
        project_id=_to_uuid(project_id),
        risk_id=_to_uuid(risk_id),
        risk_in=payload,
    )
    if not risk:
        raise HTTPException(status_code=404, detail="Riesgo no encontrado")
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "risk_updated",
        f"Riesgo '{risk.title}' actualizado (Severidad: {risk.severity_score}/25, Estado: {risk.status})",
    )
    db.commit()
    _normalize_dates(risk)
    return risk


@router.delete(
    "/{project_id}/risks/{risk_id}",
    response_model=dict,
    tags=["Projects Super-PRO"],
)
def delete_project_risk(
    project_id: str,
    risk_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Elimina (soft-delete) un riesgo de la matriz RAID."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    ok = crud.delete_project_risk(db, _to_uuid(project_id), _to_uuid(risk_id))
    if not ok:
        raise HTTPException(status_code=404, detail="Riesgo no encontrado")
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "risk_deleted",
        f"Riesgo '{risk_id}' eliminado de la matriz",
    )
    db.commit()
    return {"ok": True, "deleted": risk_id}


@router.post(
    "/{project_id}/risks/{risk_id}/convert-to-task",
    response_model=schemas.ProjectTask,
    status_code=status.HTTP_201_CREATED,
    tags=["Projects Super-PRO"],
)
def convert_risk_to_task(
    project_id: str,
    risk_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Convierte un riesgo ocurrido/materializado en una tarea de contingencia inmediata."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    persona_id = get_user_persona_id(db, current_user.id)
    task = crud.convert_risk_to_task(
        db,
        project_id=_to_uuid(project_id),
        risk_id=_to_uuid(risk_id),
        actor_id=_to_uuid(persona_id) if persona_id else None,
    )
    if not task:
        raise HTTPException(status_code=404, detail="Riesgo no encontrado")
    _normalize_dates(task)
    return task


@router.get(
    "/{project_id}/risks-summary",
    response_model=schemas.ProjectRiskSummary,
    tags=["Projects Super-PRO"],
)
def get_project_risks_summary(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Obtiene la matriz 5x5 agregada y métricas de severidad para el proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    summary = crud.get_project_risks_summary(db, _to_uuid(project_id))
    if not summary:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return summary


# ── WORKLOAD PLANNING & TEAM CAPACITY (Super-PRO Fase 3) ─────────────────────


@router.get(
    "/{project_id}/workload",
    response_model=schemas.ProjectWorkloadSummary,
    tags=["Projects Super-PRO"],
)
def get_project_workload(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Calcula la matriz de carga de trabajo, balance de equipo y saturación operativa."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    workload = crud.get_project_workload(db, _to_uuid(project_id))
    if not workload:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return workload


@router.patch(
    "/{project_id}/tasks/{task_id}/reassign",
    response_model=schemas.ProjectTask,
    tags=["Projects Super-PRO"],
)
def reassign_project_task(
    project_id: str,
    task_id: str,
    payload: schemas.TaskReassignPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Reasigna rápidamente una tarea entre miembros con validación multi-tenant y auditoría."""
    user_sede = get_user_sede_id(db, current_user.id)
    project = _ensure_project(db, project_id, user_sede=user_sede)
    task = _ensure_task_in_project(db, project_id, task_id)

    if payload.new_assignee_id is not None:
        _assert_assignee_in_sede(db, payload.new_assignee_id, user_sede)

    previous_assignee_id = getattr(task, "assignee_id", None)
    new_uuid = _to_uuid(payload.new_assignee_id) if payload.new_assignee_id else None

    updated_task = crud.reassign_project_task(
        db,
        project_id=_to_uuid(project_id),
        task_id=_to_uuid(task_id),
        new_assignee_id=new_uuid,
    )
    if not updated_task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    # Registro de bitácora ministerial y notificación
    if _assignment_changed(previous_assignee_id, new_uuid):
        assignee_name = "Sin Asignar"
        if new_uuid:
            p = db.query(models.Persona).filter(models.Persona.id == new_uuid).first()
            if p:
                assignee_name = p.nombre_completo

        _log_project_activity(
            db,
            project_id,
            current_user.id,
            "task_reassigned",
            f"Tarea '{task.title}' reasignada a {assignee_name}",
        )
        if new_uuid:
            notify_task_assigned(
                db,
                task=updated_task,
                project=project,
                assigned_by_user_id=current_user.id,
                previous_assignee_id=previous_assignee_id,
            )

    db.commit()
    _prepare_task_for_response(updated_task)
    return updated_task


# ── CRITICAL PATH METHOD (CPM) & BASELINE TRACKING (Super-PRO Fase 4) ────────


@router.get(
    "/{project_id}/critical-path",
    response_model=schemas.ProjectCriticalPathSummary,
    tags=["Projects Super-PRO"],
)
def get_project_critical_path(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Calcula el Método de la Ruta Crítica (CPM): Early/Late Start/Finish, Holgura y Tareas Críticas."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    cpm = crud.calculate_critical_path(db, _to_uuid(project_id))
    if not cpm:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return cpm


@router.post(
    "/{project_id}/baseline",
    response_model=schemas.ProjectBaseline,
    tags=["Projects Super-PRO"],
)
def create_project_baseline_endpoint(
    project_id: str,
    payload: schemas.ProjectBaselineCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Congela el cronograma planificado del proyecto en una nueva instantánea de línea base."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    try:
        baseline = crud.create_project_baseline(
            db,
            project_id=_to_uuid(project_id),
            baseline_in=payload,
            user_id=current_user.id,
        )
        _log_project_activity(
            db,
            project_id,
            current_user.id,
            "baseline_created",
            f"Línea base '{baseline.name}' congelada con éxito",
        )
        baseline_summary = crud.get_project_latest_baseline(db, _to_uuid(project_id))
        return baseline_summary or baseline
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creando línea base: {str(e)}")


@router.get(
    "/{project_id}/baseline",
    response_model=Optional[schemas.ProjectBaseline],
    tags=["Projects Super-PRO"],
)
def get_project_latest_baseline_endpoint(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Obtiene la última línea base y la comparación de varianza contra el cronograma real."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    baseline_summary = crud.get_project_latest_baseline(db, _to_uuid(project_id))
    return baseline_summary


@router.get(
    "/{project_id}/baselines",
    response_model=List[schemas.ProjectBaseline],
    tags=["Projects Super-PRO"],
)
def list_project_baselines_endpoint(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista el historial de líneas base congeladas del proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    baselines = crud.list_project_baselines(db, _to_uuid(project_id))
    return baselines


# ---------------------------------------------------------------------------
# TIME TRACKING & WORKLOGS (Super-PRO Fase 5)
# ---------------------------------------------------------------------------

@router.get(
    "/{project_id}/time-logs",
    response_model=List[schemas.ProjectTimeLog],
    tags=["Projects Super-PRO"],
)
def list_project_time_logs(
    project_id: str,
    task_id: Optional[str] = None,
    persona_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista los registros de tiempo de un proyecto con filtros opcionales."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    logs = crud.get_project_time_logs(
        db,
        project_id=_to_uuid(project_id),
        task_id=_to_uuid(task_id) if task_id else None,
        persona_id=_to_uuid(persona_id) if persona_id else None,
    )
    for time_log in logs:
        _normalize_dates(time_log)
    return logs


@router.post(
    "/{project_id}/time-logs",
    response_model=schemas.ProjectTimeLog,
    status_code=status.HTTP_201_CREATED,
    tags=["Projects Super-PRO"],
)
def create_project_time_log(
    project_id: str,
    payload: schemas.ProjectTimeLogCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Registra tiempo para el actor o para otra persona de la misma sede."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    if payload.task_id:
        _ensure_task_in_project(db, project_id, str(payload.task_id))

    actor_persona_id = get_user_persona_id(db, current_user.id)
    persona_id = payload.persona_id or actor_persona_id
    if not persona_id:
        raise HTTPException(status_code=400, detail="No se pudo determinar la persona asociada al registro")
    _assert_assignee_in_sede(db, persona_id, user_sede)

    try:
        time_log = crud.create_project_time_log(
            db,
            project_id=_to_uuid(project_id),
            log_in=payload,
            persona_id=_to_uuid(persona_id),
            created_by=current_user.id,
        )
        task_info = f" en la tarea {payload.task_id}" if payload.task_id else ""
        _log_project_activity(
            db,
            project_id,
            current_user.id,
            "time_logged",
            f"Registro de tiempo: {payload.hours:.2f}h{task_info} ({payload.description or 'Sin descripción'})",
        )
        _normalize_dates(time_log)
        return time_log
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al registrar tiempo: {str(e)}")


@router.delete(
    "/{project_id}/time-logs/{log_id}",
    tags=["Projects Super-PRO"],
)
def delete_project_time_log(
    project_id: str,
    log_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Elimina (soft-delete) un registro de tiempo."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    deleted = crud.delete_project_time_log(db, _to_uuid(project_id), _to_uuid(log_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Registro de tiempo no encontrado")
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "time_log_deleted",
        f"Registro de tiempo {log_id} eliminado",
    )
    return {"ok": True, "message": "Registro de tiempo eliminado correctamente"}


@router.get(
    "/{project_id}/tasks/{task_id}/time-logs",
    response_model=List[schemas.ProjectTimeLog],
    tags=["Projects Super-PRO"],
)
def list_task_time_logs(
    project_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Obtiene los registros de tiempo específicos de una tarea de un proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    _ensure_task_in_project(db, project_id, task_id)
    logs = crud.get_project_time_logs(db, _to_uuid(project_id), task_id=_to_uuid(task_id))
    for time_log in logs:
        _normalize_dates(time_log)
    return logs


@router.get(
    "/{project_id}/time-tracking-summary",
    response_model=schemas.ProjectTimeTrackingSummary,
    tags=["Projects Super-PRO"],
)
def get_project_time_tracking_summary(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Devuelve el resumen consolidado de horas registradas, facturables vs no facturables y desglose por tarea y miembro."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    summary = crud.get_project_time_tracking_summary(db, _to_uuid(project_id))
    return summary


# ---------------------------------------------------------------------------
# PROJECT AUTOMATIONS & TRIGGERS (Super-PRO Fase 7)
# ---------------------------------------------------------------------------

@router.get(
    "/{project_id}/automations",
    response_model=List[schemas.ProjectAutomationRule],
    tags=["Projects Automations Super-PRO"],
)
def list_project_automations(
    project_id: str,
    is_active: Optional[bool] = None,
    trigger_event: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Obtiene las reglas de automatización asociadas a un proyecto y las de alcance general."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    rules = crud.get_project_automation_rules(
        db,
        project_id=_to_uuid(project_id),
        user_sede_id=user_sede,
        is_active=is_active,
        trigger_event=trigger_event,
    )
    for r in rules:
        _normalize_dates(r)
    return rules


@router.post(
    "/{project_id}/automations",
    response_model=schemas.ProjectAutomationRule,
    status_code=status.HTTP_201_CREATED,
    tags=["Projects Automations Super-PRO"],
)
def create_project_automation(
    project_id: str,
    payload: schemas.ProjectAutomationRuleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Crea una nueva regla de automatización reactiva para el proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    project = _ensure_project(db, project_id, user_sede=user_sede)

    # Los dos campos de alcance se derivan del recurso autenticado, no del body.
    payload.project_id = str(_to_uuid(project_id))
    payload.sede_id = str(project.sede_id) if project.sede_id is not None else None
    rule = crud.create_project_automation_rule(
        db,
        payload,
        creator_persona_id=current_user.id,
        user_sede_id=user_sede,
    )
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "automation_rule_created",
        f"Regla de automatización '{rule.name}' creada (Disparador: {rule.trigger_event})",
    )
    _normalize_dates(rule)
    return rule


@router.get(
    "/{project_id}/automations/{rule_id}",
    response_model=schemas.ProjectAutomationRule,
    tags=["Projects Automations Super-PRO"],
)
def get_project_automation(
    project_id: str,
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Obtiene el detalle de una regla de automatización específica."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    rule = crud.get_project_automation_rule(db, _to_uuid(rule_id), user_sede_id=user_sede)
    if not rule or (rule.project_id and str(rule.project_id) != str(_to_uuid(project_id))):
        raise HTTPException(status_code=404, detail="Regla de automatización no encontrada")
    _normalize_dates(rule)
    return rule


@router.patch(
    "/{project_id}/automations/{rule_id}",
    response_model=schemas.ProjectAutomationRule,
    tags=["Projects Automations Super-PRO"],
)
def update_project_automation(
    project_id: str,
    rule_id: str,
    payload: schemas.ProjectAutomationRuleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Actualiza una regla de automatización (cambiar disparador, acción, estado activo/inactivo)."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    rule = crud.get_project_automation_rule(db, _to_uuid(rule_id), user_sede_id=user_sede)
    can_manage_global = _has_role_based_project_access(db, current_user, "manage")
    if (
        not rule
        or (rule.project_id is not None and str(rule.project_id) != str(_to_uuid(project_id)))
        or (rule.project_id is None and not can_manage_global)
    ):
        raise HTTPException(status_code=404, detail="Regla de automatización no encontrada")

    updated = crud.update_project_automation_rule(
        db,
        _to_uuid(rule_id),
        payload,
        user_sede_id=user_sede,
        can_manage_global=can_manage_global,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Regla de automatización no encontrada")
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "automation_rule_updated",
        f"Regla de automatización '{updated.name}' actualizada",
    )
    _normalize_dates(updated)
    return updated


@router.delete(
    "/{project_id}/automations/{rule_id}",
    tags=["Projects Automations Super-PRO"],
)
def delete_project_automation(
    project_id: str,
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Elimina (soft-delete) una regla de automatización."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    rule = crud.get_project_automation_rule(db, _to_uuid(rule_id), user_sede_id=user_sede)
    can_manage_global = _has_role_based_project_access(db, current_user, "manage")
    if (
        not rule
        or (rule.project_id is not None and str(rule.project_id) != str(_to_uuid(project_id)))
        or (rule.project_id is None and not can_manage_global)
    ):
        raise HTTPException(status_code=404, detail="Regla de automatización no encontrada")

    deleted = crud.delete_project_automation_rule(
        db,
        _to_uuid(rule_id),
        user_sede_id=user_sede,
        can_manage_global=can_manage_global,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Regla de automatización no encontrada")
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "automation_rule_deleted",
        f"Regla de automatización '{rule.name}' eliminada",
    )
    return {"ok": True, "message": "Regla de automatización eliminada correctamente"}


@router.post(
    "/{project_id}/automations/evaluate",
    response_model=List[schemas.AutomationExecutionResult],
    tags=["Projects Automations Super-PRO"],
)
def evaluate_project_automations_endpoint(
    project_id: str,
    payload: schemas.EvaluateAutomationPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Previsualiza reglas; ejecutar efectos requiere enviar ``dry_run=false`` explícitamente."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    if not payload.dry_run and not _has_role_based_project_access(db, current_user, "manage"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="projects:manage is required to execute automation effects",
        )

    context = dict(payload.context_data or {})
    requested_task_id = payload.task_id or context.get("task_id")
    if requested_task_id:
        task = (
            db.query(models.ProjectTask)
            .filter(
                models.ProjectTask.id == _to_uuid(requested_task_id),
                models.ProjectTask.project_id == _to_uuid(project_id),
                models.ProjectTask.deleted_at.is_(None),
            )
            .first()
        )
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        context["task_id"] = str(task.id)

    results = crud.evaluate_project_automations(
        db,
        _to_uuid(project_id),
        trigger_event=payload.trigger_event,
        context=context,
        actor_persona_id=current_user.id,
        user_sede_id=user_sede,
        dry_run=payload.dry_run,
    )
    return results


# ─────────────────────────────────────────────────────────────────────────────
# 16. EXPORTACIONES Y REPORTES EJECUTIVOS (Super-PRO Fase 8 - FINAL)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{project_id}/export/executive-data",
    response_model=schemas.ProjectExecutiveReportData,
    tags=["Projects Reports & Exports Super-PRO"],
)
def get_project_executive_data_endpoint(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Obtiene el conjunto de datos estructurado y métricas consolidadas para el informe ejecutivo."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)

    data = crud.get_project_executive_report_data(
        db,
        _to_uuid(project_id),
        user_sede_id=user_sede,
    )
    if not data:
        raise HTTPException(status_code=404, detail="Datos del proyecto no encontrados")
    return data


@router.get(
    "/{project_id}/export/summary-pdf",
    tags=["Projects Reports & Exports Super-PRO"],
)
def export_project_summary_pdf_endpoint(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Genera y descarga el informe ejecutivo del proyecto en formato PDF con membrete CCF."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)

    data = crud.get_project_executive_report_data(
        db,
        _to_uuid(project_id),
        user_sede_id=user_sede,
    )
    if not data:
        raise HTTPException(status_code=404, detail="Datos del proyecto no encontrados")

    pdf_bytes = crud.generate_project_summary_pdf(data)
    filename = f"reporte_ejecutivo_{project_id}.pdf"

    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "report_pdf_exported",
        f"Informe ejecutivo PDF generado y descargado para proyecto '{data.get('project', {}).get('title', project_id)}'",
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.get(
    "/{project_id}/export/tasks-csv",
    tags=["Projects Reports & Exports Super-PRO"],
)
def export_project_tasks_csv_endpoint(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Descarga el cronograma de tareas del proyecto en formato CSV (BOM UTF-8 para Excel)."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)

    csv_text = crud.generate_project_tasks_csv(
        db,
        _to_uuid(project_id),
        user_sede_id=user_sede,
    )
    filename = f"tareas_proyecto_{project_id}.csv"

    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "tasks_csv_exported",
        "Exportación de tareas CSV completada",
    )

    return Response(
        content=csv_text.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.get(
    "/{project_id}/export/expenses-csv",
    tags=["Projects Reports & Exports Super-PRO"],
)
def export_project_expenses_csv_endpoint(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Descarga el libro mayor de gastos y desembolsos del proyecto en formato CSV."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)

    csv_text = crud.generate_project_expenses_csv(
        db,
        _to_uuid(project_id),
        user_sede_id=user_sede,
    )
    filename = f"gastos_proyecto_{project_id}.csv"

    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "expenses_csv_exported",
        "Exportación de libro mayor de gastos CSV completada",
    )

    return Response(
        content=csv_text.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# 17. INDICADORES MGA / CREMA Y SEGUIMIENTO SPI (Super-PRO CREMA Fase 1)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{project_id}/advanced-indicators",
    response_model=List[schemas.ProjectIndicator],
    tags=["Projects MGA CREMA Indicators"],
)
def list_project_indicators_endpoint(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Obtiene la lista de indicadores MGA/CREMA configurados en el proyecto con su último SPI."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)

    indicators = crud.get_project_indicators(db, _to_uuid(project_id), sede_id=user_sede)
    for ind in indicators:
        _normalize_dates(ind)
        for r in getattr(ind, "records", []):
            _normalize_dates(r)
    return indicators


@router.post(
    "/{project_id}/advanced-indicators",
    response_model=schemas.ProjectIndicator,
    status_code=status.HTTP_201_CREATED,
    tags=["Projects MGA CREMA Indicators"],
)
def create_project_indicator_endpoint(
    project_id: str,
    payload: schemas.ProjectIndicatorCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Crea un nuevo indicador MGA evaluando automáticamente sus atributos bajo criterios CREMA."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)

    persona_id = _get_persona_id_for_user(db, current_user.id)
    payload.project_id = str(_to_uuid(project_id))

    indicator = crud.create_project_indicator(
        db,
        _to_uuid(project_id),
        payload,
        created_by=persona_id,
        sede_id=user_sede,
    )

    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "indicator_created",
        f"Indicador '{indicator.name}' creado (Nivel: {indicator.level}, CREMA: {indicator.crema_score}/100)",
    )

    _normalize_dates(indicator)
    return indicator


@router.get(
    "/{project_id}/advanced-indicators/{indicator_id}",
    response_model=schemas.ProjectIndicator,
    tags=["Projects MGA CREMA Indicators"],
)
def get_project_indicator_endpoint(
    project_id: str,
    indicator_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Obtiene el detalle de un indicador específico con su evaluación CREMA y desglose de avance."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)

    ind = crud.get_project_indicator(
        db,
        _to_uuid(indicator_id),
        project_id=_to_uuid(project_id),
        sede_id=user_sede,
    )
    if not ind:
        raise HTTPException(status_code=404, detail="Indicador no encontrado")

    _normalize_dates(ind)
    for r in getattr(ind, "records", []):
        _normalize_dates(r)
    return ind


@router.patch(
    "/{project_id}/advanced-indicators/{indicator_id}",
    response_model=schemas.ProjectIndicator,
    tags=["Projects MGA CREMA Indicators"],
)
def update_project_indicator_endpoint(
    project_id: str,
    indicator_id: str,
    payload: schemas.ProjectIndicatorUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Actualiza la definición de un indicador recalculando la calificación CREMA si aplica."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)

    persona_id = _get_persona_id_for_user(db, current_user.id)
    updated = crud.update_project_indicator(
        db,
        _to_uuid(indicator_id),
        payload,
        user_id=persona_id,
        sede_id=user_sede,
        project_id=_to_uuid(project_id),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Indicador no encontrado")

    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "indicator_updated",
        f"Indicador '{updated.name}' actualizado",
    )

    _normalize_dates(updated)
    return updated


@router.delete(
    "/{project_id}/advanced-indicators/{indicator_id}",
    tags=["Projects MGA CREMA Indicators"],
)
def delete_project_indicator_endpoint(
    project_id: str,
    indicator_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Elimina lógicamente (soft-delete) un indicador de proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)

    persona_id = _get_persona_id_for_user(db, current_user.id)
    success = crud.delete_project_indicator(
        db,
        _to_uuid(indicator_id),
        user_id=persona_id,
        sede_id=user_sede,
        project_id=_to_uuid(project_id),
    )
    if not success:
        raise HTTPException(status_code=404, detail="Indicador no encontrado")

    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "indicator_deleted",
        "Indicador eliminado",
    )

    return {"ok": True, "message": "Indicador eliminado exitosamente", "id": indicator_id}


@router.post(
    "/{project_id}/indicators/validate-crema",
    response_model=schemas.CremaValidationResult,
    tags=["Projects MGA CREMA Indicators"],
)
def validate_crema_indicator_endpoint(
    project_id: str,
    payload: schemas.ValidateCremaPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Microservicio validador inteligente de criterios C, R, E, M, A (Metodología MGA/BID)."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)

    result = crud.validate_crema_indicator(payload)
    return result


@router.post(
    "/{project_id}/indicators/{indicator_id}/records",
    response_model=schemas.ProjectIndicatorRecord,
    status_code=status.HTTP_201_CREATED,
    tags=["Projects MGA CREMA Indicators"],
)
def create_project_indicator_record_endpoint(
    project_id: str,
    indicator_id: str,
    payload: schemas.ProjectIndicatorRecordCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Registra una medición periódica calculando automáticamente el SPI (Schedule/Performance Index)."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)

    persona_id = _get_persona_id_for_user(db, current_user.id)
    payload.indicator_id = str(_to_uuid(indicator_id))
    if not crud.get_project_indicator(
        db,
        _to_uuid(indicator_id),
        project_id=_to_uuid(project_id),
        sede_id=user_sede,
    ):
        raise HTTPException(status_code=404, detail="Indicador no encontrado")

    try:
        record = crud.create_project_indicator_record(
            db,
            _to_uuid(indicator_id),
            payload,
            reported_by=persona_id,
            sede_id=user_sede,
            project_id=_to_uuid(project_id),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "indicator_record_created",
        f"Medición registrada en período '{record.period}' (Meta: {record.target_value}, Real: {record.actual_value}, SPI: {record.spi})",
    )

    _normalize_dates(record)
    return record


@router.get(
    "/{project_id}/indicators/{indicator_id}/records",
    response_model=List[schemas.ProjectIndicatorRecord],
    tags=["Projects MGA CREMA Indicators"],
)
def list_project_indicator_records_endpoint(
    project_id: str,
    indicator_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista el historial cronológico de mediciones y cálculo de SPI de un indicador."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)

    try:
        if not crud.get_project_indicator(
            db,
            _to_uuid(indicator_id),
            project_id=_to_uuid(project_id),
            sede_id=user_sede,
        ):
            raise HTTPException(status_code=404, detail="Indicador no encontrado")
        records = crud.get_project_indicator_records(
            db,
            _to_uuid(indicator_id),
            sede_id=user_sede,
            project_id=_to_uuid(project_id),
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    for r in records:
        _normalize_dates(r)
    return records


# ─────────────────────────────────────────────────────────────────────────────
# 18. FAVORITOS DE USUARIO Y FIJACIÓN DE COMENTARIOS (Super-PRO Files Fase 1)
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/{project_id}/tasks/{task_id}/toggle-favorite",
    response_model=schemas.ProjectUserFavoriteToggleResponse,
    tags=["Projects Favorites & Pins Super-PRO"],
)
def toggle_task_favorite_endpoint(
    project_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Alterna el estado favorito de una tarea para el usuario autenticado (Axioma 3)."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)

    persona_id = _get_persona_id_for_user(db, current_user.id)

    try:
        result = crud.toggle_task_favorite(
            db,
            _to_uuid(project_id),
            _to_uuid(task_id),
            persona_id,
            sede_id=user_sede,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return result


@router.get(
    "/{project_id}/favorites",
    response_model=List[str],
    tags=["Projects Favorites & Pins Super-PRO"],
)
def get_project_favorites_endpoint(
    project_id: str,
    entity_type: str = Query("task", description="Tipo de entidad (task, doc)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Obtiene la lista de identificadores favoritos del usuario en el proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)

    persona_id = _get_persona_id_for_user(db, current_user.id)

    try:
        fav_ids = crud.get_project_user_favorites(
            db,
            _to_uuid(project_id),
            persona_id,
            entity_type=entity_type,
            sede_id=user_sede,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return fav_ids


@router.post(
    "/{project_id}/tasks/{task_id}/comments/{comment_id}/pin",
    response_model=schemas.ProjectCommentItem,
    tags=["Projects Favorites & Pins Super-PRO"],
)
def pin_task_comment_endpoint(
    project_id: str,
    task_id: str,
    comment_id: str,
    payload: Optional[schemas.ProjectPinCommentPayload] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Fija o desfija un comentario en la cabecera del hilo de discusión."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)

    persona_id = _get_persona_id_for_user(db, current_user.id)

    try:
        comment = crud.pin_project_comment(
            db,
            _to_uuid(project_id),
            _to_uuid(comment_id),
            persona_id,
            task_id=_to_uuid(task_id),
            is_pinned=payload.is_pinned if payload else None,
            sede_id=user_sede,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    persona = (
        db.query(models.Persona).filter(models.Persona.id == comment.author_id).first()
        if comment.author_id
        else None
    )
    return _project_comment_to_schema(comment, persona)


# ══════════════════════════════════════════════════════════════════════════════
# 19. BÓVEDA DOCUMENTAL Y VISOR UNIVERSAL EMBEBIDO (SUPER-PRO FILES FASE 2)
# ══════════════════════════════════════════════════════════════════════════════

def _project_file_to_schema(file_obj: models.ProjectFile) -> schemas.ProjectFile:
    embed_url = file_obj.file_url
    if file_obj.file_source == "drive" or file_obj.drive_file_id:
        _, emb, _ = crud.normalize_drive_embed_url(file_obj.file_url)
        if emb:
            embed_url = emb

    uploader_name = None
    if file_obj.uploader:
        uploader_name = (
            getattr(file_obj.uploader, "nombre_completo", None)
            or f"{getattr(file_obj.uploader, 'nombre', '')} {getattr(file_obj.uploader, 'apellido', '')}".strip()
            or "Usuario"
        )

    task_title = getattr(file_obj.task, "title", None) if file_obj.task else None
    phase_name = getattr(file_obj.phase, "name", None) if file_obj.phase else None

    return schemas.ProjectFile(
        id=str(file_obj.id),
        project_id=str(file_obj.project_id),
        name=file_obj.name,
        description=file_obj.description,
        category=file_obj.category,
        file_source=file_obj.file_source,
        file_url=file_obj.file_url,
        embed_url=embed_url,
        file_type=file_obj.file_type,
        file_size=file_obj.file_size,
        drive_file_id=file_obj.drive_file_id,
        task_id=str(file_obj.task_id) if file_obj.task_id else None,
        task_title=task_title,
        phase_id=str(file_obj.phase_id) if file_obj.phase_id else None,
        phase_name=phase_name,
        uploaded_by=str(file_obj.uploaded_by) if file_obj.uploaded_by else None,
        uploader_name=uploader_name,
        created_at=file_obj.created_at,
        updated_at=file_obj.updated_at,
    )


@router.post(
    "/{project_id}/files/upload",
    response_model=schemas.ProjectFile,
    tags=["Projects Boveda Documental Super-PRO"],
)
async def upload_project_file_endpoint(
    project_id: str,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form("general"),
    task_id: Optional[str] = Form(None),
    phase_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Sube un archivo local a la bóveda documental del proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    if task_id:
        _ensure_task_in_project(db, project_id, task_id)
    if phase_id:
        _ensure_phase_in_project(db, project_id, phase_id)

    filename = sanitize_filename(file.filename or "archivo")
    contents = await file.read()

    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="El archivo excede el tamaño máximo permitido")

    url = storage_service.save_file(contents, filename, subfolder="projects/boveda")
    persona_id = _get_persona_id_for_user(db, current_user.id)

    doc_name = name.strip() if name and name.strip() else filename

    try:
        new_file = crud.create_project_file(
            db,
            _to_uuid(project_id),
            name=doc_name,
            file_url=url,
            file_source="local",
            category=category or "general",
            description=description,
            file_type=file.content_type,
            file_size=len(contents),
            task_id=_to_uuid(task_id) if task_id else None,
            phase_id=_to_uuid(phase_id) if phase_id else None,
            uploaded_by=persona_id,
            sede_id=user_sede,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "file_uploaded",
        f"Archivo '{doc_name}' subido a la bóveda documental",
    )
    return _project_file_to_schema(new_file)


@router.post(
    "/{project_id}/files/link-drive",
    response_model=schemas.ProjectFile,
    tags=["Projects Boveda Documental Super-PRO"],
)
def link_project_drive_file_endpoint(
    project_id: str,
    payload: schemas.ProjectFileLinkDrivePayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Vincula un documento o recurso de Google Drive a la bóveda del proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    if payload.task_id:
        _ensure_task_in_project(db, project_id, payload.task_id)
    if payload.phase_id:
        _ensure_phase_in_project(db, project_id, payload.phase_id)

    persona_id = _get_persona_id_for_user(db, current_user.id)

    try:
        drive_file = crud.link_drive_file(
            db,
            _to_uuid(project_id),
            drive_url=payload.drive_url,
            name=payload.name,
            description=payload.description,
            category=payload.category or "general",
            task_id=_to_uuid(payload.task_id) if payload.task_id else None,
            phase_id=_to_uuid(payload.phase_id) if payload.phase_id else None,
            uploaded_by=persona_id,
            sede_id=user_sede,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "drive_file_linked",
        f"Documento de Google Drive '{drive_file.name}' vinculado a la bóveda",
    )
    return _project_file_to_schema(drive_file)


@router.get(
    "/{project_id}/files",
    response_model=List[schemas.ProjectFile],
    tags=["Projects Boveda Documental Super-PRO"],
)
def list_project_files_endpoint(
    project_id: str,
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    file_source: Optional[str] = Query(None, description="Filtrar por origen (local, drive, etc.)"),
    task_id: Optional[str] = Query(None, description="Filtrar por tarea"),
    phase_id: Optional[str] = Query(None, description="Filtrar por fase"),
    search: Optional[str] = Query(None, description="Término de búsqueda"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Obtiene el listado de archivos de la bóveda documental del proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    if task_id:
        _ensure_task_in_project(db, project_id, task_id)
    if phase_id:
        _ensure_phase_in_project(db, project_id, phase_id)

    try:
        files = crud.get_project_files(
            db,
            _to_uuid(project_id),
            category=category,
            file_source=file_source,
            task_id=_to_uuid(task_id) if task_id else None,
            phase_id=_to_uuid(phase_id) if phase_id else None,
            search=search,
            sede_id=user_sede,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return [_project_file_to_schema(f) for f in files]


@router.get(
    "/{project_id}/files/summary",
    response_model=schemas.ProjectFilesSummary,
    tags=["Projects Boveda Documental Super-PRO"],
)
def get_project_files_summary_endpoint(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Obtiene el resumen consolidado de la bóveda documental del proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)

    try:
        summary = crud.get_project_files_summary(
            db,
            _to_uuid(project_id),
            sede_id=user_sede,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return schemas.ProjectFilesSummary(
        project_id=str(project_id),
        total_files=summary["total_files"],
        total_size_bytes=summary["total_size_bytes"],
        by_source=summary["by_source"],
        by_category=summary["by_category"],
        files=[_project_file_to_schema(f) for f in summary["files"]],
    )


@router.delete(
    "/{project_id}/files/{file_id}",
    response_model=dict,
    tags=["Projects Boveda Documental Super-PRO"],
)
def delete_project_file_endpoint(
    project_id: str,
    file_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Elimina (soft-delete) un archivo de la bóveda documental del proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)

    try:
        success = crud.delete_project_file(
            db,
            _to_uuid(file_id),
            project_id=_to_uuid(project_id),
            user_id=current_user.id,
            sede_id=user_sede,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not success:
        raise HTTPException(status_code=404, detail="Archivo no encontrado en este proyecto")

    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "file_deleted",
        f"Archivo '{file_id}' eliminado de la bóveda documental",
    )
    return {"deleted": True, "file_id": file_id}
